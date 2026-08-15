import logging
from typing import Literal, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user, require_same_organization
from app.models.company import Company
from app.models.user import User
from app.services.assistant_generation import generate_answer, generate_email_draft
from app.services.assistant_search import find_relevant_records
from app.services.regulatory_library import load_regulatory_updates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["compliance assistant"])

MAX_SOURCE_TITLE_LENGTH = 90
MAX_CONTEXT_RECORDS = 3


def _short_text(value: str, max_length: int) -> str:
    text = " ".join(value.split())
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 3].rsplit(' ', 1)[0]}..."


def _source_title(value: str) -> str:
    return _short_text(value, MAX_SOURCE_TITLE_LENGTH)


class AssistantRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)


class AssistantSource(BaseModel):
    title: str
    url: str
    date: str


class AssistantResponse(BaseModel):
    answer: str
    sources: list[AssistantSource]
    confidence: str
    assistant_label: str = "Regulatory Library Assistant"


class EmailDraftRequest(BaseModel):
    client_id: uuid.UUID
    prompt: str = Field(min_length=10, max_length=2000)
    tone: Literal["professional", "friendly", "urgent", "concise"] = "professional"
    recipient_name: Optional[str] = Field(default=None, max_length=100)


class EmailDraftResponse(BaseModel):
    subject: str
    body: str
    client_name: str
    assistant_label: str = "Client Email Drafting Assistant"


@router.get("/health")
async def assistant_health(current_user: User = Depends(get_current_user)):
    records = load_regulatory_updates()
    return {"status": "ok", "records_indexed": len(records)}


@router.post("/chat", response_model=AssistantResponse)
async def assistant_chat(
    request: AssistantRequest,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    matches = find_relevant_records(request.question, category=category)
    
    if not matches:
        return {
            "answer": "I could not find a sufficiently relevant publication in the current regulatory library. Try including a form number, regulator, circular number, or obligation name.",
            "sources": [],
            "confidence": "not_found",
        }

    context_records = matches[:MAX_CONTEXT_RECORDS]
    try:
        answer = await generate_answer(request.question, context_records)
    except Exception as exc:
        logger.exception("Failed to generate regulatory answer: %s", exc)
        return {
            "answer": "I found relevant publications but could not generate a response right now. Please try again shortly.",
            "sources": [],
            "confidence": "error",
        }

    return {
        "answer": answer,
        "sources": [
            {
                "title": _source_title(item["title"]),
                "url": item["url"],
                "date": item["publication_date"],
            }
            for item in matches
        ],
        "confidence": "answered",
        "assistant_label": "Regulatory Library Assistant",
    }


@router.post("/email-draft", response_model=EmailDraftResponse)
async def assistant_email_draft(
    request: EmailDraftRequest,
    current_user: User = Depends(get_current_user),
):
    work_role = (current_user.designation or current_user.role or "").lower().replace(" ", "_")
    if work_role in {"executive", "intern", "staff"}:
        raise HTTPException(status_code=403, detail="Email drafting requires manager or partner access")

    company = await require_same_organization(await Company.get(request.client_id), current_user)
    records = find_relevant_records(request.prompt)[:MAX_CONTEXT_RECORDS]
    sender_name = current_user.full_name or current_user.email
    try:
        draft = await generate_email_draft(
            instruction=request.prompt,
            client_name=company.name,
            sender_name=sender_name,
            tone=request.tone,
            recipient_name=request.recipient_name,
            records=records,
        )
    except Exception as exc:
        logger.exception("Failed to generate email draft: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="The email drafting assistant is unavailable. Check the Gemini configuration and try again.",
        )

    return {**draft, "client_name": company.name}