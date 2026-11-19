"""Seed script to populate database with synthetic demo personas.

Personas:
1. Shathi: 24yo garment worker in Ashulia, Dhaka. High bills timeliness, excellent repayment habits.
2. Student: 21yo tech student & freelancer in Dhaka. High recharge regularity, moderate income volatility.
3. Homemaker: 28yo rural homemaker in Chittagong. Zero bank/wallet history, relies on Bhorsha psychometric score.
"""

import hashlib
import sys
from pathlib import Path
from typing import Any

# Ensure backend root is on sys.path
backend_path = Path(__file__).resolve().parents[1]
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.core.decision import score_applicant
from app.db.models import (
    Application,
    AuditLog,
    Consent,
    DecisionRecord,
    FeatureSnapshot,
    Repayment,
    User,
)
from app.db.session import get_session_factory, init_db
from sqlalchemy.orm import Session


def hash_phone(phone: str) -> str:
    """Compute SHA-256 fingerprint for phone number."""
    return hashlib.sha256(phone.encode("utf-8")).hexdigest()


def seed_demo_personas(session: Session | None = None) -> list[User]:
    """Seed the 3 demo personas into the database.

    Idempotent: removes existing records with matching phone hashes before recreating.
    """
    should_close = False
    if session is None:
        init_db()
        factory = get_session_factory()
        session = factory()
        should_close = True

    try:
        personas_data: list[dict[str, Any]] = [
            {
                "name": "Shathi",
                "phone": "+8801711000001",
                "gender": "F",
                "region": "urban",
                "division": "Dhaka",
                "consents": ["sms", "bills", "recharge"],
                "features": {
                    "monthly_inflow_bdt": 14000.0,
                    "income_volatility": 0.10,
                    "months_on_wallet": 30.0,
                    "txn_per_month": 18.0,
                    "bills_on_time": 0.97,
                    "recharge_regularity": 0.90,
                    "savings_ratio": 0.04,
                    "sends_money_home": 1.0,
                    "bhorsha_score": None,
                    "loan_to_income": 4.0,
                },
                "source_summary": "bKash wallet history + DESCO electricity bills",
                "application_amount": 15000.0,
                "repayment_amount": 2500.0,
                "audit_meta": {"persona": "Shathi", "occupation": "garment_worker", "demo": True},
            },
            {
                "name": "Student",
                "phone": "+8801811000002",
                "gender": "M",
                "region": "urban",
                "division": "Dhaka",
                "consents": ["sms", "recharge"],
                "features": {
                    "monthly_inflow_bdt": 8500.0,
                    "income_volatility": 0.20,
                    "months_on_wallet": 14.0,
                    "txn_per_month": 22.0,
                    "bills_on_time": 0.88,
                    "recharge_regularity": 0.95,
                    "savings_ratio": 0.02,
                    "sends_money_home": 0.0,
                    "bhorsha_score": 72.0,
                    "loan_to_income": 2.0,
                },
                "source_summary": "Nagad wallet history + airtime micro-recharges",
                "application_amount": 5000.0,
                "repayment_amount": 1000.0,
                "audit_meta": {
                    "persona": "Student",
                    "occupation": "university_freelancer",
                    "demo": True,
                },
            },
            {
                "name": "Homemaker",
                "phone": "+8801911000003",
                "gender": "F",
                "region": "rural",
                "division": "Chittagong",
                "consents": ["bhorsha"],
                "features": {
                    "monthly_inflow_bdt": None,
                    "income_volatility": None,
                    "months_on_wallet": None,
                    "txn_per_month": None,
                    "bills_on_time": None,
                    "recharge_regularity": None,
                    "savings_ratio": None,
                    "sends_money_home": None,
                    "bhorsha_score": 78.0,
                    "loan_to_income": None,
                },
                "source_summary": "Bangla psychometric conversational chat (Bhorsha)",
                "application_amount": 8000.0,
                "repayment_amount": 1200.0,
                "audit_meta": {
                    "persona": "Homemaker",
                    "occupation": "rural_homemaker",
                    "demo": True,
                },
            },
        ]

        seeded_users: list[User] = []

        for p in personas_data:
            p_hash = hash_phone(p["phone"])

            # Clean existing user if re-seeding
            existing = session.query(User).filter(User.phone_hash == p_hash).first()
            if existing:
                session.delete(existing)
                session.commit()

            # 1. Create user
            user = User(
                phone_hash=p_hash,
                gender=p["gender"],
                region=p["region"],
                division=p["division"],
            )
            session.add(user)
            session.flush()

            # 2. Add consents
            for src in p["consents"]:
                consent = Consent(
                    user_id=user.id,
                    source=src,
                )
                session.add(consent)

            # 3. Add feature snapshot
            snapshot = FeatureSnapshot(
                user_id=user.id,
                features=p["features"],
                source_summary=p["source_summary"],
            )
            session.add(snapshot)

            # 4. Create credit application
            application = Application(
                user_id=user.id,
                amount_bdt=p["application_amount"],
                status="approved",
            )
            session.add(application)
            session.flush()

            # 5. Score applicant using core model
            demographic_group = f"{user.gender}_{user.region}"
            decision_result = score_applicant(p["features"], group=demographic_group)

            decision_record = DecisionRecord(
                application_id=application.id,
                user_id=user.id,
                p_repay=decision_result.p_repay,
                score=decision_result.score,
                band=decision_result.band,
                approved=decision_result.approved,
                reasons=[r.model_dump() for r in decision_result.reasons],
                tips=decision_result.tips,
                group=demographic_group,
                threshold_used=decision_result.threshold_used,
                model_version=decision_result.model_version,
                fairness_ok=True,
            )
            session.add(decision_record)

            # 6. Add repayment
            repayment = Repayment(
                application_id=application.id,
                amount_bdt=p["repayment_amount"],
                on_time=True,
            )
            session.add(repayment)

            # 7. Add audit log
            audit = AuditLog(
                user_id=user.id,
                event="demo_persona_seeded",
                entity_type="user",
                entity_id=user.id,
                details=p["audit_meta"],
            )
            session.add(audit)

            seeded_users.append(user)

        session.commit()
        for u in seeded_users:
            session.refresh(u)
        session.expunge_all()
        return seeded_users

    finally:
        if should_close:
            session.close()


if __name__ == "__main__":
    users = seed_demo_personas()
    print(f"Successfully seeded {len(users)} demo personas.")
    for u in users:
        print(f"  - User {u.id}: gender={u.gender}, region={u.region}, division={u.division}")
