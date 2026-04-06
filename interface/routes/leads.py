"""Leads CRUD and export routes."""

from __future__ import annotations

import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from interface.database import (
    get_engine,
    init_db,
    create_lead,
    get_leads,
    delete_lead,
    Lead,
)

router = APIRouter()

# Module-level engine (overridden in tests via dependency injection)
_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = get_engine()
        init_db(_engine)
    return _engine


def get_session():
    """FastAPI dependency that yields a database session."""
    with Session(_get_engine()) as session:
        yield session


class LeadIn(BaseModel):
    linkedin_url: str
    name: Optional[str] = None
    role: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    about: Optional[str] = None
    raw_json: str


class LeadOut(BaseModel):
    id: int
    linkedin_url: str
    name: Optional[str]
    role: Optional[str]
    company: Optional[str]
    location: Optional[str]
    about: Optional[str]
    saved_at: Optional[str]


@router.post("/api/leads", response_model=LeadOut)
def save_lead(body: LeadIn, session: Session = Depends(get_session)):
    lead = create_lead(
        session,
        linkedin_url=body.linkedin_url,
        name=body.name,
        role=body.role,
        company=body.company,
        location=body.location,
        about=body.about,
        raw_json=body.raw_json,
    )
    if lead is None:
        # Duplicate — return existing
        lead = session.query(Lead).filter_by(linkedin_url=body.linkedin_url).first()
    return LeadOut(**lead.to_dict())


@router.get("/api/leads", response_model=list[LeadOut])
def list_leads(
    name: Optional[str] = None,
    company: Optional[str] = None,
    role: Optional[str] = None,
    location: Optional[str] = None,
    session: Session = Depends(get_session),
):
    leads = get_leads(session, name=name, company=company, role=role, location=location)
    return [LeadOut(**l.to_dict()) for l in leads]


@router.delete("/api/leads/{lead_id}")
def remove_lead(lead_id: int, session: Session = Depends(get_session)):
    if not delete_lead(session, lead_id):
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"deleted": lead_id}


@router.get("/api/export")
def export_csv(
    name: Optional[str] = None,
    company: Optional[str] = None,
    role: Optional[str] = None,
    location: Optional[str] = None,
    session: Session = Depends(get_session),
):
    leads = get_leads(session, name=name, company=company, role=role, location=location)

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["id", "name", "role", "company", "location", "linkedin_url", "about", "saved_at"],
    )
    writer.writeheader()
    for lead in leads:
        d = lead.to_dict()
        writer.writerow({k: d.get(k, "") or "" for k in writer.fieldnames})

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads.csv"},
    )
