from datetime import date, datetime
from typing import Optional, List, Literal
from pydantic import BaseModel
import uuid

class CompanyMinResponse(BaseModel):
    id: uuid.UUID
    name: str
    cin: Optional[str] = None
    company_type: str

    class Config:
        from_attributes = True

class RuleMinResponse(BaseModel):
    id: uuid.UUID
    name: str
    form_number: Optional[str] = None

    class Config:
        from_attributes = True

class UserMinResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: Optional[str] = None
    role: str

    class Config:
        from_attributes = True

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: date
    status: str = "pending"
    assigned_to: Optional[uuid.UUID] = None
    assigned_team: Optional[uuid.UUID] = None
    assigned_user: Optional[uuid.UUID] = None
    reviewer: Optional[uuid.UUID] = None
    approver: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    reference_doc: Optional[str] = None
    category: str = "cs"  # cs, ca

class TaskCreate(TaskBase):
    company_id: uuid.UUID
    rule_id: Optional[uuid.UUID] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[date] = None
    # Lifecycle states are changed only through /transition, never by a generic edit.
    status: Optional[Literal["pending", "in_progress", "completed_by_executive", "waiting_for_review", "approved", "closed", "returned_with_comments"]] = None
    current_stage: Optional[str] = None
    assigned_to: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    reference_doc: Optional[str] = None
    category: Optional[str] = None
    assigned_team: Optional[uuid.UUID] = None
    assigned_user: Optional[uuid.UUID] = None
    reviewer: Optional[uuid.UUID] = None
    approver: Optional[uuid.UUID] = None
    assigned_team_id: Optional[uuid.UUID] = None
    assigned_user_id: Optional[uuid.UUID] = None
    reviewer_id: Optional[uuid.UUID] = None
    approver_id: Optional[uuid.UUID] = None

class TaskAssignmentUpdate(BaseModel):
    assigned_team_id: uuid.UUID
    assigned_user_id: uuid.UUID
    reviewer_id: uuid.UUID
    approver_id: uuid.UUID

class TaskResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    rule_id: Optional[uuid.UUID] = None
    title: str
    description: Optional[str] = None
    due_date: date
    status: str
    current_stage: Optional[str] = "executive"
    assigned_to: Optional[uuid.UUID] = None
    completed_by: Optional[uuid.UUID] = None
    completed_at: Optional[datetime] = None
    reference_doc: Optional[str] = None
    notes: Optional[str] = None
    category: str = "cs"
    created_at: datetime
    updated_at: datetime
    organization_id: Optional[uuid.UUID] = None
    created_by: Optional[uuid.UUID] = None
    assigned_team_id: Optional[uuid.UUID] = None
    assigned_user_id: Optional[uuid.UUID] = None
    reviewer_id: Optional[uuid.UUID] = None
    approver_id: Optional[uuid.UUID] = None
    # Nested objects — populated when using selectinload in the router
    company: Optional[CompanyMinResponse] = None
    assigned_user: Optional[UserMinResponse] = None

    class Config:
        from_attributes = True

class AuditLogMinResponse(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[uuid.UUID] = None
    action_metadata: Optional[dict] = None
    created_at: datetime
    user: Optional[UserMinResponse] = None

    class Config:
        from_attributes = True

class TaskCommentCreate(BaseModel):
    content: str

class TaskCommentResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    user_id: uuid.UUID
    user_name: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

class TaskDetailResponse(TaskResponse):
    company: CompanyMinResponse
    rule: Optional[RuleMinResponse] = None
    assigned_user: Optional[UserMinResponse] = None
    completed_user: Optional[UserMinResponse] = None
    audit_logs: List[AuditLogMinResponse] = []
    comments: List[TaskCommentResponse] = []
    remarks: List[TaskCommentResponse] = []

    class Config:
        from_attributes = True
