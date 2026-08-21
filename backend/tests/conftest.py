"""
Shared fixtures for the security test suite. Uses an in-memory SQLite
database with Postgres-only column types swapped for portable
equivalents (JSON, etc.) — this exercises the actual ORM query logic
(the thing we're testing: does every query filter by clinic_id
correctly) without needing a live Postgres instance. It does NOT
exercise Postgres-specific behavior like RLS itself (RLS enforcement
can only be verified against real Postgres — see
docs/security/SECURITY_TESTING.md for what that gap means and how to
close it).
"""
import os
import sys
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, JSON
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://user:pass@localhost/db")
os.environ.setdefault("DATABASE_URL_ADMIN", "postgresql+psycopg2://admin:pass@localhost/db")
os.environ.setdefault("SUPABASE_URL", "https://x.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "x")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "x")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret-for-pytest-only")
os.environ.setdefault("GROQ_API_KEY", "x")
os.environ.setdefault("TWILIO_ACCOUNT_SID", "x")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "x")
os.environ.setdefault("TWILIO_PHONE_NUMBER", "x")
os.environ.setdefault("META_VERIFY_TOKEN", "test-verify-token")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models import Base, KnowledgeBaseArticle, Patient, Escalation  # noqa: E402

# Swap Postgres-only types for SQLite-compatible equivalents, same
# pattern used throughout manual testing this build.
KnowledgeBaseArticle.__table__.c.embedding.type = JSON()
Patient.__table__.c.tags.type = JSON()
Patient.__table__.c.external_ids_json.type = JSON()
Escalation.__table__.c.notified_staff_ids.type = JSON()


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture()
def two_clinics(db_session):
    """Two separate clinics with one patient each — the baseline fixture for every cross-tenant test."""
    from app.models import Clinic, Patient as PatientModel

    clinic_a = Clinic(id=uuid.uuid4(), name="Clinic A", slug="clinic-a")
    clinic_b = Clinic(id=uuid.uuid4(), name="Clinic B", slug="clinic-b")
    db_session.add_all([clinic_a, clinic_b])

    patient_a = PatientModel(id=uuid.uuid4(), clinic_id=clinic_a.id, first_name="Alice", phone="555-0001")
    patient_b = PatientModel(id=uuid.uuid4(), clinic_id=clinic_b.id, first_name="Bob", phone="555-0002")
    db_session.add_all([patient_a, patient_b])
    db_session.commit()

    return {"clinic_a": clinic_a, "clinic_b": clinic_b, "patient_a": patient_a, "patient_b": patient_b}
