"""Seed demo users and policies for local end-to-end testing.

Usage: .venv/Scripts/python.exe scripts/seed_demo_data.py
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.security import hash_password  # noqa: E402
from app.db.database import SessionLocal, init_db  # noqa: E402
from app.models.policy import Policy, PolicyStatus  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402

DEMO_USERS = [
    ("admin@example.com", "admin123", "Ada Admin", UserRole.ADMIN),
    ("adjuster@example.com", "adjuster123", "Alex Adjuster", UserRole.ADJUSTER),
    ("customer@example.com", "customer123", "Casey Customer", UserRole.CUSTOMER),
]

DEMO_POLICIES = [
    dict(
        policy_number="POL-10001",
        holder_name="Casey Customer",
        vehicle_vin="1HGCM82633A004352",
        vehicle_make="Honda",
        vehicle_model="Accord",
        vehicle_year=2021,
        coverage_type="full",
        coverage_limit=25000.0,
        deductible=500.0,
        effective_date=date(2025, 1, 1),
        expiration_date=date(2026, 12, 31),
        status=PolicyStatus.ACTIVE,
    ),
    dict(
        policy_number="POL-10002",
        holder_name="Jordan Lapsed",
        vehicle_vin="2T1BURHE0JC014595",
        vehicle_make="Toyota",
        vehicle_model="Corolla",
        vehicle_year=2019,
        coverage_type="liability",
        coverage_limit=10000.0,
        deductible=1000.0,
        effective_date=date(2023, 1, 1),
        expiration_date=date(2024, 1, 1),
        status=PolicyStatus.LAPSED,
    ),
]


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        for email, password, full_name, role in DEMO_USERS:
            if db.query(User).filter(User.email == email).first():
                continue
            db.add(User(email=email, hashed_password=hash_password(password), full_name=full_name, role=role))
        db.commit()

        for policy_kwargs in DEMO_POLICIES:
            if db.query(Policy).filter(Policy.policy_number == policy_kwargs["policy_number"]).first():
                continue
            db.add(Policy(**policy_kwargs))
        db.commit()

        print("Seeded demo users:")
        for email, password, _, role in DEMO_USERS:
            print(f"  {role.value:10s} {email}  (password: {password})")
        print("Seeded demo policies:", ", ".join(p["policy_number"] for p in DEMO_POLICIES))
    finally:
        db.close()


if __name__ == "__main__":
    main()
