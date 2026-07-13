from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  registers all models on Base
from app.core.security import hash_password
from app.db.database import Base, get_db
from app.main import app
from app.models.policy import Policy, PolicyStatus
from app.models.user import User, UserRole


@pytest.fixture()
def db_sessionmaker():
    """A fresh in-memory SQLite DB per test — isolated from storage/app.db."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    yield sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_sessionmaker):
    def override_get_db():
        db = db_sessionmaker()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # Deliberately not using `with TestClient(...)` — that runs the app's real
    # lifespan/startup event, which calls init_db() against the production
    # SQLite file. Every route here reaches the DB only via Depends(get_db),
    # which is overridden above to the in-memory test database instead.
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


def register(client: TestClient, email: str, password: str = "testpass123") -> dict:
    """Public self-service registration — always produces a CUSTOMER account,
    matching the real /auth/register contract (role is not caller-selectable)."""
    resp = client.post(
        "/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_staff(db_sessionmaker, client: TestClient, email: str, role: UserRole, password: str = "testpass123") -> dict:
    """Staff (adjuster/admin) accounts aren't self-service — seed one directly
    in the DB, the way POST /admin/users would, then log in for a real token."""
    db = db_sessionmaker()
    try:
        db.add(User(email=email, hashed_password=hash_password(password), full_name="Staff User", role=role))
        db.commit()
    finally:
        db.close()

    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def register_user(client):
    def _register(email: str, password: str = "testpass123") -> dict:
        return register(client, email, password=password)

    return _register


@pytest.fixture()
def customer_auth(client):
    return register(client, "customer@test.example.com")


@pytest.fixture()
def adjuster_auth(client, db_sessionmaker):
    return create_staff(db_sessionmaker, client, "adjuster@test.example.com", UserRole.ADJUSTER)


@pytest.fixture()
def admin_auth(client, db_sessionmaker):
    return create_staff(db_sessionmaker, client, "admin@test.example.com", UserRole.ADMIN)


@pytest.fixture()
def active_policy(db_sessionmaker):
    db = db_sessionmaker()
    try:
        policy = Policy(
            policy_number="POL-TEST-1",
            holder_name="Test Holder",
            vehicle_vin="1HGCM82633A004352",
            vehicle_make="Honda",
            vehicle_model="Accord",
            vehicle_year=2021,
            coverage_type="full",
            coverage_limit=25000.0,
            deductible=500.0,
            effective_date=date.today() - timedelta(days=30),
            expiration_date=date.today() + timedelta(days=335),
            status=PolicyStatus.ACTIVE,
        )
        db.add(policy)
        db.commit()
        return policy.policy_number
    finally:
        db.close()
