from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field
import uuid

class CompanyBase(BaseModel):
    cin: Optional[str] = Field(None, min_length=21, max_length=21)  # Corporate Identity Number
    name: str
    company_type: str  # private_limited, public_limited, llp, opc, partnership, proprietorship, individual
    reg_date: date
    financial_year_end: date
    address: Optional[str] = None
    assigned_to: Optional[uuid.UUID] = None
    relationship_partner_id: uuid.UUID
    manager_id: uuid.UUID
    assigned_team_id: uuid.UUID
    primary_executive_id: Optional[uuid.UUID] = None
    assigned_team: Optional[uuid.UUID] = None
    relationship_manager: Optional[uuid.UUID] = None
    industry: Optional[str] = None
    pan: Optional[str] = None
    gstin: Optional[str] = None
    client_type: str = "cs"  # cs, ca, both

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(BaseModel):
    cin: Optional[str] = Field(None, min_length=21, max_length=21)
    name: Optional[str] = None
    company_type: Optional[str] = None
    reg_date: Optional[date] = None
    financial_year_end: Optional[date] = None
    address: Optional[str] = None
    assigned_to: Optional[uuid.UUID] = None
    relationship_partner_id: Optional[uuid.UUID] = None
    manager_id: Optional[uuid.UUID] = None
    assigned_team_id: Optional[uuid.UUID] = None
    primary_executive_id: Optional[uuid.UUID] = None
    assigned_team: Optional[uuid.UUID] = None
    relationship_manager: Optional[uuid.UUID] = None
    industry: Optional[str] = None
    pan: Optional[str] = None
    gstin: Optional[str] = None
    client_type: Optional[str] = None
    is_active: Optional[bool] = None

class CompanyResponse(BaseModel):
    id: uuid.UUID
    cin: Optional[str] = None
    name: str
    company_type: str
    reg_date: date
    financial_year_end: date
    address: Optional[str] = None
    assigned_to: Optional[uuid.UUID] = None
    relationship_partner_id: Optional[uuid.UUID] = None
    manager_id: Optional[uuid.UUID] = None
    assigned_team_id: Optional[uuid.UUID] = None
    primary_executive_id: Optional[uuid.UUID] = None
    pan: Optional[str] = None
    gstin: Optional[str] = None
    client_type: str
    is_active: bool
    created_at: datetime
    organization_id: Optional[uuid.UUID] = None
    assigned_team: Optional[uuid.UUID] = None
    relationship_manager: Optional[uuid.UUID] = None
    industry: Optional[str] = None
    status: str = "active"

    class Config:
        from_attributes = True

class TasksSummary(BaseModel):
    overdue: int = 0
    due_soon: int = 0
    upcoming: int = 0
    completed: int = 0
    total: int = 0

class CompanyDetailResponse(CompanyResponse):
    tasks_summary: TasksSummary

    class Config:
        from_attributes = True

class ClientAssignmentUpdate(BaseModel):
    relationship_partner_id: uuid.UUID
    manager_id: uuid.UUID
    assigned_team_id: uuid.UUID
    # Kept optional for compatibility with older clients. The backend derives the
    # task assignee from the selected team's manager/member structure.
    primary_executive_id: Optional[uuid.UUID] = None
