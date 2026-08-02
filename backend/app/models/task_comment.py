from beanie import Document
from pydantic import Field
import uuid
from datetime import datetime

class TaskComment(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    task_id: uuid.UUID
    organization_id: uuid.UUID | None = None
    user_id: uuid.UUID
    user_name: str
    content: str
    is_remark: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "task_comments"
        indexes = ["task_id", "organization_id"]
