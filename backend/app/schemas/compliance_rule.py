from pydantic import BaseModel
from typing import Optional, List
import uuid

class ComplianceRuleBase(BaseModel):
    name: str
    form_number: Optional[str] = None
    company_types: List[str]
    frequency: str  # annual, quarterly, monthly, event_based
    due_days_from_trigger: int
    description: Optional[str] = None
    is_active: bool = True

class ComplianceRuleCreate(ComplianceRuleBase):
    pass

class ComplianceRuleUpdate(BaseModel):
    name: Optional[str] = None
    form_number: Optional[str] = None
    company_types: Optional[List[str]] = None
    min_paid_up_capital: Optional[float] = None
    min_annual_turnover: Optional[float] = None
    min_bank_loan_amount: Optional[float] = None
    frequency: Optional[str] = None
    due_days_from_trigger: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class ComplianceRuleResponse(ComplianceRuleBase):
    id: uuid.UUID

    class Config:
        from_attributes = True
