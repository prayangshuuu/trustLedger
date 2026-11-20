"""Seed the database with synthetic demo data.

Personas (always):
1. Shathi: 24, garment worker in Ashulia, pays every bill on time, no bank account.
2. Student: 21, student and freelancer in Dhaka, regular recharges, Bhorsha done.
3. Homemaker: 28, rural homemaker in Chattogram, zero wallet history, Bhorsha only.

Optional synthetic population (``--population N``) generated with the same formulas as the
training notebook so the lender dashboard has realistic distributions. All data is synthetic.
"""

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Any

import numpy as np

backend_path = Path(__file__).resolve().parents[1]
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.core.decision import score_applicant
from app.db.models import AuditLog, Consent, FeatureSnapshot, Repayment, User
from app.db.session import get_session_factory, init_db
from app.services.decisions import fairness_check, persist_decision
from sqlalchemy import select
from sqlalchemy.orm import Session

DIVISIONS = [
    "Dhaka",
    "Chattogram",
    "Khulna",
    "Rajshahi",
    "Barishal",
    "Sylhet",
    "Rangpur",
    "Mymensingh",
]
DIVISION_WEIGHTS = [0.30, 0.18, 0.11, 0.12, 0.06, 0.07, 0.09, 0.07]

PERSONAS: list[dict[str, Any]] = [
    {
        "name": "Shathi",
        "phone": "+8801711000001",
        "gender": "F",
        "region": "urban",
        "division": "Dhaka",
        "consents": ["sms", "bills", "recharge", "ocr"],
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
        "source_summary": "Wallet SMS history + DESCO electricity bills",
        "amount": 15000.0,
        "repayments": [2500.0, 2500.0],
    },
    {
        "name": "Student",
        "phone": "+8801811000002",
        "gender": "M",
        "region": "urban",
        "division": "Dhaka",
        "consents": ["sms", "recharge", "bhorsha"],
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
        "source_summary": "Wallet SMS history + airtime recharges + Bhorsha",
        "amount": 5000.0,
        "repayments": [1000.0],
    },
    {
        "name": "Homemaker",
        "phone": "+8801911000003",
        "gender": "F",
        "region": "rural",
        "division": "Chattogram",
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
        "source_summary": "Bhorsha psychometric chat only (zero history)",
        "amount": 8000.0,
        "repayments": [],
    },
]


def hash_phone(phone: str) -> str:
    """SHA-256 fingerprint of a phone number (raw numbers are never stored)."""
    return hashlib.sha256(phone.encode("utf-8")).hexdigest()


def _create_scored_user(
    session: Session,
    phone_hash: str,
    gender: str,
    region: str,
    division: str,
    features: dict[str, Any],
    consents: list[str],
    amount: float,
    source_summary: str,
    has_bank_account: bool = False,
    has_salary_slip: bool = False,
    repayments: list[tuple[float, bool]] | None = None,
    audit_meta: dict[str, Any] | None = None,
) -> User:
    user = User(
        phone_hash=phone_hash,
        gender=gender,
        region=region,
        division=division,
        has_bank_account=has_bank_account,
        has_salary_slip=has_salary_slip,
    )
    session.add(user)
    session.flush()
    for src in consents:
        session.add(Consent(user_id=user.id, source=src))
    session.add(FeatureSnapshot(user_id=user.id, features=features, source_summary=source_summary))

    group = f"{gender}_{region}"
    decision = score_applicant(features, group=group)
    fairness = fairness_check(decision, group, features)
    record = persist_decision(
        session,
        decision,
        features=features,
        user=user,
        amount_bdt=amount,
        fairness=fairness,
        event="demo_seed_scored",
        extra_audit={"demo": True, **(audit_meta or {})},
    )
    if record.application_id and record.approved:
        for amt, on_time in repayments or []:
            session.add(
                Repayment(application_id=record.application_id, amount_bdt=amt, on_time=on_time)
            )
    return user


def _remove_existing(session: Session, phone_hash: str) -> None:
    existing = session.scalars(select(User).where(User.phone_hash == phone_hash)).first()
    if existing:
        session.delete(existing)
        session.flush()


def seed_demo_personas(session: Session | None = None) -> list[User]:
    """Seed the 3 demo personas. Idempotent: existing personas are replaced."""
    should_close = session is None
    if session is None:
        init_db()
        session = get_session_factory()()
    try:
        users: list[User] = []
        for p in PERSONAS:
            p_hash = hash_phone(p["phone"])
            _remove_existing(session, p_hash)
            users.append(
                _create_scored_user(
                    session,
                    phone_hash=p_hash,
                    gender=p["gender"],
                    region=p["region"],
                    division=p["division"],
                    features=p["features"],
                    consents=p["consents"],
                    amount=p["amount"],
                    source_summary=p["source_summary"],
                    repayments=[(a, True) for a in p["repayments"]],
                    audit_meta={"persona": p["name"]},
                )
            )
            session.add(
                AuditLog(
                    user_id=users[-1].id,
                    event="demo_persona_seeded",
                    entity_type="user",
                    entity_id=users[-1].id,
                    details={"persona": p["name"], "demo": True},
                )
            )
        session.commit()
        for u in users:
            session.refresh(u)
        session.expunge_all()
        return users
    finally:
        if should_close:
            session.close()


def _sig(x: np.ndarray) -> np.ndarray:
    return np.asarray(1.0 / (1.0 + np.exp(-x)))


def generate_population(n: int, seed: int = 7) -> list[dict[str, Any]]:
    """Synthetic applicants using the notebook's generator formulas (simplified occupations)."""
    rng = np.random.default_rng(seed)
    occ_income = {
        "garment_worker": 13000,
        "gig_rider": 18000,
        "student": 6000,
        "homemaker": 4000,
        "small_trader": 20000,
        "farmer": 12000,
        "salaried": 30000,
    }
    occ_vol = {
        "garment_worker": 0.12,
        "gig_rider": 0.40,
        "student": 0.30,
        "homemaker": 0.35,
        "small_trader": 0.35,
        "farmer": 0.60,
        "salaried": 0.08,
    }
    rows: list[dict[str, Any]] = []
    for i in range(n):
        gender = str(rng.choice(["F", "M"]))
        region = str(rng.choice(["rural", "urban"], p=[0.6, 0.4]))
        division = str(rng.choice(DIVISIONS, p=DIVISION_WEIGHTS))
        if gender == "F":
            occ_p = {
                "garment_worker": 0.30,
                "homemaker": 0.25,
                "student": 0.12,
                "small_trader": 0.10,
                "salaried": 0.10,
                "farmer": 0.08,
                "gig_rider": 0.05,
            }
        else:
            occ_p = {
                "garment_worker": 0.15,
                "homemaker": 0.01,
                "student": 0.12,
                "small_trader": 0.20,
                "salaried": 0.17,
                "farmer": 0.15,
                "gig_rider": 0.20,
            }
        if region == "rural":
            occ_p["farmer"] *= 2.5
            occ_p["salaried"] *= 0.5
            occ_p["gig_rider"] *= 0.5
        w = np.array(list(occ_p.values()))
        occ = str(rng.choice(list(occ_p), p=w / w.sum()))
        trait = float(rng.normal())
        income = (
            occ_income[occ] * float(rng.lognormal(0, 0.35)) * (0.78 if region == "rural" else 1)
        )
        months = float(rng.integers(0, 25 if occ == "homemaker" else 61))
        months = float(np.floor(months * (0.8 if region == "rural" else 1)))
        no_history = months < 3
        loan_income = float(rng.uniform(2, 8))
        feats: dict[str, Any] = {
            "monthly_inflow_bdt": round(income),
            "income_volatility": round(
                float(np.clip(occ_vol[occ] + rng.normal(0, 0.06), 0.02, 1.2)), 3
            ),
            "months_on_wallet": months,
            "txn_per_month": float(rng.poisson(max(1.0, 4 + income / 2500 + months / 10))),
            "bills_on_time": round(
                float(_sig(np.array(1.3 + 1.1 * trait + rng.normal(0, 0.5)))), 3
            ),
            "recharge_regularity": round(
                float(_sig(np.array(0.8 + 0.7 * trait + rng.normal(0, 0.6)))), 3
            ),
            "savings_ratio": round(
                float(np.clip(0.06 + 0.04 * trait + rng.normal(0, 0.03), 0, 0.6)), 3
            ),
            "sends_money_home": float(
                rng.random() < float(_sig(np.array(-0.6 + 0.5 * trait + (occ == "garment_worker"))))
            ),
            "bhorsha_score": None,
            "loan_to_income": round(loan_income, 2),
        }
        if no_history:
            for k in (
                "txn_per_month",
                "bills_on_time",
                "recharge_regularity",
                "savings_ratio",
                "sends_money_home",
            ):
                feats[k] = None
        if no_history or rng.random() < 0.3:
            feats["bhorsha_score"] = round(
                float(np.clip(50 + 13 * trait + rng.normal(0, 8), 0, 100)), 1
            )
        p_bank = float(
            _sig(
                np.array(
                    -1.2
                    + 2.2 * (occ == "salaried")
                    + 0.9 * (region == "urban")
                    + 0.6 * (gender == "M")
                    + 0.4 * np.log(income / 15000)
                )
            )
        )
        slip_p = 0.9 if occ == "salaried" else 0.2 if occ == "garment_worker" else 0.02
        logit = (
            -1.75
            - 1.15 * trait
            + 1.3 * feats["income_volatility"]
            + 0.22 * (loan_income - 5)
            - 0.35 * np.log(income / 15000)
            + rng.normal(0, 0.4)
        )
        repaid = not (rng.random() < float(_sig(np.array(logit))))
        rows.append(
            {
                "phone_hash": hashlib.sha256(f"synthetic-{seed}-{i}".encode()).hexdigest(),
                "gender": gender,
                "region": region,
                "division": division,
                "features": feats,
                "has_bank_account": bool(rng.random() < p_bank),
                "has_salary_slip": bool(rng.random() < slip_p),
                "repaid": repaid,
                "amount": round(loan_income * income / 100) * 100,
            }
        )
    return rows


def seed_population(session: Session, n: int = 400, seed: int = 7) -> int:
    """Add n synthetic applicants (replacing a previous run with the same seed)."""
    rows = generate_population(n, seed)
    for row in rows:
        _remove_existing(session, row["phone_hash"])
        consents = ["sms", "bills", "recharge"] if row["features"]["months_on_wallet"] >= 3 else []
        if row["features"]["bhorsha_score"] is not None:
            consents.append("bhorsha")
        _create_scored_user(
            session,
            phone_hash=row["phone_hash"],
            gender=row["gender"],
            region=row["region"],
            division=row["division"],
            features=row["features"],
            consents=consents,
            amount=float(row["amount"]),
            source_summary="Synthetic population (notebook generator)",
            has_bank_account=row["has_bank_account"],
            has_salary_slip=row["has_salary_slip"],
            repayments=[(row["amount"] / 6, row["repaid"])],
            audit_meta={"synthetic_population": True},
        )
    session.commit()
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed TrustLedger demo data")
    parser.add_argument("--population", type=int, default=0, help="Synthetic applicants to add")
    args = parser.parse_args()
    users = seed_demo_personas()
    print(f"Seeded {len(users)} demo personas.")
    for u in users:
        print(f"  - {u.id}: group={u.gender}_{u.region} division={u.division}")
    if args.population:
        init_db()
        with get_session_factory()() as session:
            count = seed_population(session, args.population)
        print(f"Seeded {count} synthetic applicants.")


if __name__ == "__main__":
    main()
