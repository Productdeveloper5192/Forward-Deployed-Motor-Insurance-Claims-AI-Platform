import enum
from datetime import date

from sqlalchemy import Date, Enum, Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class PolicyStatus(str, enum.Enum):
    ACTIVE = "active"
    LAPSED = "lapsed"
    CANCELLED = "cancelled"


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    policy_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    holder_name: Mapped[str] = mapped_column(String(255))
    vehicle_vin: Mapped[str] = mapped_column(String(32))
    vehicle_make: Mapped[str] = mapped_column(String(64))
    vehicle_model: Mapped[str] = mapped_column(String(64))
    vehicle_year: Mapped[int] = mapped_column()
    coverage_type: Mapped[str] = mapped_column(String(64))  # liability, collision, comprehensive, full
    coverage_limit: Mapped[float] = mapped_column(Float)
    deductible: Mapped[float] = mapped_column(Float)
    effective_date: Mapped[date] = mapped_column(Date)
    expiration_date: Mapped[date] = mapped_column(Date)
    status: Mapped[PolicyStatus] = mapped_column(Enum(PolicyStatus), default=PolicyStatus.ACTIVE)

    claims: Mapped[list["Claim"]] = relationship(back_populates="policy")
