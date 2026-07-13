"""Integration tests for the HTTP API.

These deliberately never call POST /claims/{id}/submit — that hands off to the
LangGraph pipeline, which makes live Claude API calls. Instead, tests that need
a claim in a particular downstream status (needs_review, approved) set it
directly through the DB session fixture, the same way the background worker
would have left it.
"""

from datetime import date

from app.models.claim import Claim, ClaimStatus


def create_claim(client, auth, policy_number="POL-TEST-1"):
    resp = client.post(
        "/claims",
        json={
            "policy_number": policy_number,
            "incident_date": str(date.today()),
            "incident_description": "Rear-ended at a stop light.",
            "incident_location": "Main St & 5th Ave",
        },
        headers=auth,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def set_claim_status(db_sessionmaker, claim_id, status, **fields):
    db = db_sessionmaker()
    try:
        claim = db.get(Claim, claim_id)
        claim.status = status
        for key, value in fields.items():
            setattr(claim, key, value)
        db.commit()
    finally:
        db.close()


class TestAuth:
    def test_register_login_me(self, client):
        auth = {}
        register = client.post(
            "/auth/register",
            json={"email": "a@test.example.com", "password": "pw123456", "full_name": "A", "role": "customer"},
        )
        assert register.status_code == 201
        token = register.json()["access_token"]
        auth["Authorization"] = f"Bearer {token}"

        me = client.get("/auth/me", headers=auth)
        assert me.status_code == 200
        assert me.json()["email"] == "a@test.example.com"

    def test_duplicate_email_rejected(self, client):
        payload = {"email": "dupe@test.example.com", "password": "pw123456", "full_name": "A", "role": "customer"}
        assert client.post("/auth/register", json=payload).status_code == 201
        assert client.post("/auth/register", json=payload).status_code == 400

    def test_wrong_password_rejected(self, client):
        payload = {"email": "b@test.example.com", "password": "pw123456", "full_name": "B", "role": "customer"}
        client.post("/auth/register", json=payload)
        resp = client.post("/auth/login", json={"email": "b@test.example.com", "password": "wrong"})
        assert resp.status_code == 401

    def test_unauthenticated_request_rejected(self, client):
        assert client.get("/claims").status_code == 401

    def test_public_registration_cannot_self_assign_admin_role(self, client):
        """Regression test: /auth/register must always produce a customer
        account, even if the caller sends a role field in the request body."""
        resp = client.post(
            "/auth/register",
            json={
                "email": "wannabe-admin@test.example.com",
                "password": "pw123456",
                "full_name": "Sneaky",
                "role": "admin",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["user"]["role"] == "customer"

        me = client.get("/auth/me", headers={"Authorization": f"Bearer {resp.json()['access_token']}"})
        assert me.json()["role"] == "customer"


class TestClaimsIntake:
    def test_create_claim_requires_valid_policy_number(self, client, customer_auth):
        resp = client.post(
            "/claims",
            json={
                "policy_number": "NO-SUCH-POLICY",
                "incident_date": str(date.today()),
                "incident_description": "test",
            },
            headers=customer_auth,
        )
        assert resp.status_code == 400

    def test_customer_can_create_and_view_own_claim(self, client, customer_auth, active_policy):
        claim = create_claim(client, customer_auth, active_policy)
        assert claim["status"] == "draft"

        resp = client.get(f"/claims/{claim['id']}", headers=customer_auth)
        assert resp.status_code == 200
        assert resp.json()["id"] == claim["id"]

    def test_customer_cannot_view_other_customers_claim(self, client, register_user, active_policy):
        owner_auth = register_user("owner@test.example.com")
        other_auth = register_user("other@test.example.com")

        claim = create_claim(client, owner_auth, active_policy)
        resp = client.get(f"/claims/{claim['id']}", headers=other_auth)
        assert resp.status_code == 403

    def test_document_upload_and_submit_lock(self, client, customer_auth, active_policy):
        claim = create_claim(client, customer_auth, active_policy)
        upload = client.post(
            f"/claims/{claim['id']}/documents",
            data={"doc_type": "police_report"},
            files={"file": ("report.txt", b"a police report", "text/plain")},
            headers=customer_auth,
        )
        assert upload.status_code == 200
        assert len(upload.json()["documents"]) == 1

    def test_empty_upload_rejected(self, client, customer_auth, active_policy):
        claim = create_claim(client, customer_auth, active_policy)
        resp = client.post(
            f"/claims/{claim['id']}/documents",
            data={"doc_type": "police_report"},
            files={"file": ("empty.txt", b"", "text/plain")},
            headers=customer_auth,
        )
        assert resp.status_code == 400


class TestReviewAndPayout:
    def test_review_queue_and_decision(self, client, customer_auth, adjuster_auth, active_policy, db_sessionmaker):
        claim = create_claim(client, customer_auth, active_policy)
        set_claim_status(db_sessionmaker, claim["id"], ClaimStatus.NEEDS_REVIEW)

        queue = client.get("/review/queue", headers=adjuster_auth)
        assert queue.status_code == 200
        assert any(c["id"] == claim["id"] for c in queue.json())

        decision = client.post(
            f"/review/{claim['id']}/decision",
            json={"decision": "approved", "approved_amount": 1200.0, "notes": "Looks good"},
            headers=adjuster_auth,
        )
        assert decision.status_code == 200
        assert decision.json()["status"] == "approved"
        assert decision.json()["approved_amount"] == 1200.0

    def test_customer_cannot_submit_review_decision(self, client, customer_auth, active_policy, db_sessionmaker):
        claim = create_claim(client, customer_auth, active_policy)
        set_claim_status(db_sessionmaker, claim["id"], ClaimStatus.NEEDS_REVIEW)

        resp = client.post(
            f"/review/{claim['id']}/decision",
            json={"decision": "approved"},
            headers=customer_auth,
        )
        assert resp.status_code == 403

    def test_pay_requires_approved_status(self, client, adjuster_auth, customer_auth, active_policy, db_sessionmaker):
        claim = create_claim(client, customer_auth, active_policy)
        # still draft — paying now should be rejected
        resp = client.post(f"/claims/{claim['id']}/pay", headers=adjuster_auth)
        assert resp.status_code == 400

    def test_pay_marks_claim_paid_and_sets_paid_at(
        self, client, adjuster_auth, customer_auth, active_policy, db_sessionmaker
    ):
        claim = create_claim(client, customer_auth, active_policy)
        set_claim_status(db_sessionmaker, claim["id"], ClaimStatus.APPROVED, approved_amount=900.0)

        resp = client.post(f"/claims/{claim['id']}/pay", headers=adjuster_auth)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "paid"
        assert body["paid_at"] is not None

        # paying twice should fail — no longer approved
        again = client.post(f"/claims/{claim['id']}/pay", headers=adjuster_auth)
        assert again.status_code == 400


class TestNotifications:
    def test_review_decision_creates_a_readable_notification(
        self, client, customer_auth, adjuster_auth, active_policy, db_sessionmaker
    ):
        claim = create_claim(client, customer_auth, active_policy)
        set_claim_status(db_sessionmaker, claim["id"], ClaimStatus.NEEDS_REVIEW)
        client.post(
            f"/review/{claim['id']}/decision",
            json={"decision": "denied", "notes": "Not covered"},
            headers=adjuster_auth,
        )

        notes = client.get("/notifications", headers=customer_auth)
        assert notes.status_code == 200
        items = notes.json()
        assert len(items) >= 1
        assert items[0]["read_at"] is None

        mark = client.post(f"/notifications/{items[0]['id']}/read", headers=customer_auth)
        assert mark.status_code == 200
        assert mark.json()["read_at"] is not None

    def test_cannot_mark_another_users_notification_read(
        self, client, customer_auth, adjuster_auth, active_policy, db_sessionmaker, register_user
    ):
        claim = create_claim(client, customer_auth, active_policy)
        set_claim_status(db_sessionmaker, claim["id"], ClaimStatus.NEEDS_REVIEW)
        client.post(
            f"/review/{claim['id']}/decision",
            json={"decision": "approved", "approved_amount": 500.0},
            headers=adjuster_auth,
        )
        mine = client.get("/notifications", headers=customer_auth).json()

        stranger_auth = register_user("stranger@test.example.com")
        resp = client.post(f"/notifications/{mine[0]['id']}/read", headers=stranger_auth)
        assert resp.status_code == 404


class TestAdmin:
    def test_admin_can_create_and_list_policies(self, client, admin_auth):
        payload = {
            "policy_number": "POL-ADMIN-1",
            "holder_name": "Jane Doe",
            "vehicle_vin": "1FAFP53U16A123456",
            "vehicle_make": "Ford",
            "vehicle_model": "Focus",
            "vehicle_year": 2020,
            "coverage_type": "liability",
            "coverage_limit": 15000.0,
            "deductible": 250.0,
            "effective_date": str(date.today()),
            "expiration_date": str(date.today().replace(year=date.today().year + 1)),
        }
        created = client.post("/admin/policies", json=payload, headers=admin_auth)
        assert created.status_code == 201

        listed = client.get("/admin/policies", headers=admin_auth)
        assert any(p["policy_number"] == "POL-ADMIN-1" for p in listed.json())

    def test_non_admin_cannot_create_policy(self, client, customer_auth):
        resp = client.post("/admin/policies", json={"policy_number": "X"}, headers=customer_auth)
        assert resp.status_code in (401, 403, 422)

    def test_audit_log_records_and_filters_by_claim(
        self, client, customer_auth, adjuster_auth, admin_auth, active_policy, db_sessionmaker
    ):
        claim = create_claim(client, customer_auth, active_policy)
        set_claim_status(db_sessionmaker, claim["id"], ClaimStatus.NEEDS_REVIEW)
        client.post(
            f"/review/{claim['id']}/decision",
            json={"decision": "approved", "approved_amount": 800.0},
            headers=adjuster_auth,
        )

        all_logs = client.get("/admin/audit-log", headers=admin_auth)
        assert all_logs.status_code == 200
        assert len(all_logs.json()) >= 2  # claim_created + claim_reviewed

        scoped = client.get(f"/admin/audit-log?claim_id={claim['id']}", headers=admin_auth)
        assert scoped.status_code == 200
        assert all(entry["claim_id"] == claim["id"] for entry in scoped.json())

    def test_evaluation_endpoint_shape(self, client, admin_auth):
        resp = client.get("/admin/evaluation", headers=admin_auth)
        assert resp.status_code == 200
        body = resp.json()
        assert "total_claims" in body
        assert "claims_by_status" in body


class TestStaffProvisioning:
    def test_admin_can_create_staff_user(self, client, admin_auth):
        resp = client.post(
            "/admin/users",
            json={
                "email": "new-adjuster@test.example.com",
                "password": "pw123456",
                "full_name": "New Adjuster",
                "role": "adjuster",
            },
            headers=admin_auth,
        )
        assert resp.status_code == 201
        assert resp.json()["role"] == "adjuster"

        # the new account can actually log in and use its granted role
        login = client.post(
            "/auth/login", json={"email": "new-adjuster@test.example.com", "password": "pw123456"}
        )
        assert login.status_code == 200
        new_auth = {"Authorization": f"Bearer {login.json()['access_token']}"}
        assert client.get("/review/queue", headers=new_auth).status_code == 200

    def test_non_admin_cannot_create_staff_user(self, client, customer_auth):
        resp = client.post(
            "/admin/users",
            json={
                "email": "sneaky-staff@test.example.com",
                "password": "pw123456",
                "full_name": "Sneaky",
                "role": "admin",
            },
            headers=customer_auth,
        )
        assert resp.status_code == 403

    def test_non_admin_cannot_list_users(self, client, adjuster_auth):
        assert client.get("/admin/users", headers=adjuster_auth).status_code == 403

    def test_admin_can_list_users(self, client, admin_auth, customer_auth):
        resp = client.get("/admin/users", headers=admin_auth)
        assert resp.status_code == 200
        emails = [u["email"] for u in resp.json()]
        assert "customer@test.example.com" in emails
