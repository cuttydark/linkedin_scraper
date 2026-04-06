"""SQLAlchemy Lead model and CRUD helpers for the web interface."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Text, DateTime, create_engine, Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session


class Base(DeclarativeBase):
    pass


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    linkedin_url: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(200))
    role: Mapped[Optional[str]] = mapped_column(String(200))
    company: Mapped[Optional[str]] = mapped_column(String(200))
    location: Mapped[Optional[str]] = mapped_column(String(200))
    about: Mapped[Optional[str]] = mapped_column(Text)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "linkedin_url": self.linkedin_url,
            "name": self.name,
            "role": self.role,
            "company": self.company,
            "location": self.location,
            "about": self.about,
            "raw_json": self.raw_json,
            "saved_at": self.saved_at.isoformat() if self.saved_at else None,
        }


def get_engine(db_path: str = "leads.db") -> Engine:
    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def create_lead(
    session: Session,
    *,
    linkedin_url: str,
    name: Optional[str],
    role: Optional[str],
    company: Optional[str],
    location: Optional[str],
    about: Optional[str],
    raw_json: str,
) -> Optional[Lead]:
    """Create a lead. Returns None if linkedin_url already exists (duplicate ignored)."""
    if lead_exists(session, linkedin_url):
        return None
    lead = Lead(
        linkedin_url=linkedin_url,
        name=name,
        role=role,
        company=company,
        location=location,
        about=about,
        raw_json=raw_json,
        saved_at=datetime.now(timezone.utc),
    )
    session.add(lead)
    session.commit()
    session.refresh(lead)
    return lead


def get_leads(
    session: Session,
    *,
    name: Optional[str] = None,
    company: Optional[str] = None,
    role: Optional[str] = None,
    location: Optional[str] = None,
) -> list[Lead]:
    """List leads with optional case-insensitive filters."""
    query = session.query(Lead)
    if name:
        query = query.filter(Lead.name.ilike(f"%{name}%"))
    if company:
        query = query.filter(Lead.company.ilike(f"%{company}%"))
    if role:
        query = query.filter(Lead.role.ilike(f"%{role}%"))
    if location:
        query = query.filter(Lead.location.ilike(f"%{location}%"))
    return query.order_by(Lead.saved_at.desc()).all()


def lead_exists(session: Session, linkedin_url: str) -> bool:
    return session.query(Lead).filter_by(linkedin_url=linkedin_url).first() is not None


def delete_lead(session: Session, lead_id: int) -> bool:
    lead = session.get(Lead, lead_id)
    if not lead:
        return False
    session.delete(lead)
    session.commit()
    return True
