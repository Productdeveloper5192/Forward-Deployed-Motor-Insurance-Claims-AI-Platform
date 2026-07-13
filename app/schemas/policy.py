from datetime import date

from pydantic import BaseModel

from app.models.policy import PolicyStatus


class PolicyCreate(BaseModel):
    policy_number: str
    holder_name: str
    vehicle_vin: str
    vehicle_make: str
    vehicle_model: str
    vehicle_year: int
    coverage_type: str
    coverage_limit: float
    deductible: float
    effective_date: date
    expiration_date: date
    status: PolicyStatus = PolicyStatus.ACTIVE


class PolicyOut(PolicyCreate):
    id: int

    model_config = {"from_attributes": True}
