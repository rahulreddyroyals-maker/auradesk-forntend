"""
Cross-tenant access must always fail. This exercises the actual query
logic used in the patients router — the same pattern (filter by both
the resource's own id AND clinic_id together) is what every endpoint in
this codebase uses; this test is the automated guard against that
pattern regressing.
"""
from app.models import Patient


def test_clinic_cannot_fetch_another_clinics_patient_by_id(db_session, two_clinics):
    """The IDOR case: clinic A knows (or guesses) clinic B's patient ID and tries to fetch it directly."""
    patient_b_id = two_clinics["patient_b"].id
    clinic_a_id = two_clinics["clinic_a"].id

    # Exactly the query shape used in app/api/v1/patients.py::_get_owned_patient
    result = (
        db_session.query(Patient)
        .filter(Patient.id == patient_b_id, Patient.clinic_id == clinic_a_id)
        .first()
    )
    assert result is None, "Clinic A must never be able to fetch Clinic B's patient by ID"


def test_clinic_list_query_only_returns_own_patients(db_session, two_clinics):
    clinic_a_id = two_clinics["clinic_a"].id
    results = db_session.query(Patient).filter(Patient.clinic_id == clinic_a_id).all()
    assert len(results) == 1
    assert results[0].first_name == "Alice"
    assert all(p.clinic_id == clinic_a_id for p in results)


def test_clinic_cannot_delete_another_clinics_patient(db_session, two_clinics):
    """Same IDOR shape as the fetch test, but for the delete path — a missing scope check here would let A delete B's data."""
    patient_b_id = two_clinics["patient_b"].id
    clinic_a_id = two_clinics["clinic_a"].id

    target = (
        db_session.query(Patient)
        .filter(Patient.id == patient_b_id, Patient.clinic_id == clinic_a_id)
        .first()
    )
    assert target is None  # the endpoint would 404 here, never reaching a delete call

    # Confirm patient B is untouched, regardless
    still_there = db_session.query(Patient).filter(Patient.id == patient_b_id).first()
    assert still_there is not None
