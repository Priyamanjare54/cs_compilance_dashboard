from beanie import Document
from pydantic import Field
import uuid
from datetime import datetime, date

class Company(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    cin: str | None = None
    organization_id: uuid.UUID | None = None
    name: str
    company_type: str  # private_limited, public_limited, llp, opc, partnership, proprietorship, individual
    reg_date: date
    financial_year_end: date
    address: str | None = None
    paid_up_capital: float | None = None
    annual_turnover: float | None = None
    bank_loan_amount: float | None = None
    assigned_to: uuid.UUID | None = None
    relationship_partner_id: uuid.UUID | None = None
    manager_id: uuid.UUID | None = None
    assigned_team_id: uuid.UUID | None = None
    primary_executive_id: uuid.UUID | None = None
    assigned_team: uuid.UUID | None = None
    relationship_manager: uuid.UUID | None = None
    industry: str | None = None
    status: str = "active"
    pan: str | None = None
    gstin: str | None = None
    client_type: str = "cs"  # cs, ca, both
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "companies"
        indexes = ["organization_id"]
