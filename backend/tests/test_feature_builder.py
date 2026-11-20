"""Unit and integration tests for feature builder, range clipping, and demo parsing endpoints."""

from datetime import UTC, datetime, timedelta

import pytest
from app.config import Settings
from app.core.decision import score_applicant
from app.core.features import FEATURE_NAMES
from app.db.base import Base
from app.db.models import FeatureSnapshot, User
from app.db.session import get_db
from app.main import create_app
from app.parsers.features import (
    clip_feature_value,
    extract_features,
    load_feature_ranges,
)
from app.parsers.sms import Transaction, parse_sms_batch
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker


def test_feature_ranges_loading_and_clipping() -> None:
    """Verify models/feature_ranges.json is loaded and clipping limits extreme values."""
    ranges = load_feature_ranges()
    assert "monthly_inflow_bdt" in ranges
    assert "income_volatility" in ranges
    assert "savings_ratio" in ranges

    min_inflow = ranges["monthly_inflow_bdt"]["min"]
    max_inflow = ranges["monthly_inflow_bdt"]["max"]

    # Clipping tests
    assert clip_feature_value("monthly_inflow_bdt", min_inflow - 500.0, ranges) == min_inflow
    assert clip_feature_value("monthly_inflow_bdt", max_inflow + 5000.0, ranges) == max_inflow
    assert clip_feature_value("monthly_inflow_bdt", 25000.0, ranges) == 25000.0
    assert clip_feature_value("monthly_inflow_bdt", None, ranges) is None


def test_short_history_triggers_needs_bhorsha() -> None:
    """Verify applicants with < 3 months of wallet history trigger needs_bhorsha=True and None features."""
    now = datetime(2026, 10, 15, 12, 0, 0, tzinfo=UTC)
    txs = [
        Transaction(
            date=now - timedelta(days=20),
            amount_bdt=5000.0,
            direction="in",
            type="income",
            raw_hash="hash1",
        ),
        Transaction(
            date=now - timedelta(days=10),
            amount_bdt=500.0,
            direction="out",
            type="bill",
            raw_hash="hash2",
        ),
        Transaction(
            date=now,
            amount_bdt=200.0,
            direction="out",
            type="recharge",
            raw_hash="hash3",
        ),
    ]

    result = extract_features(txs, requested_amount_bdt=10000.0)
    assert result.needs_bhorsha is True
    assert result.months_on_wallet < 3.0
    # Wallet features should all be None so model handles missingness and relies on Bhorsha
    for f in FEATURE_NAMES:
        assert result.features[f] is None


def test_individual_feature_formulas() -> None:
    """Verify exact mathematical formulas for every engineered feature."""
    base_date = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
    txs: list[Transaction] = []

    # 4 months of structured transactions
    # Inflow: 20,000 in Jan, 20,000 in Feb, 20,000 in Mar, 20,000 in Apr -> median 20,000, volatility 0.0
    for m in range(4):
        m_date = base_date + timedelta(days=m * 30 + 1)
        # Income
        txs.append(
            Transaction(
                date=m_date,
                amount_bdt=20000.0,
                direction="in",
                type="income",
                raw_hash=f"inc_{m}",
            )
        )
        # Bill paid on day 10 (on time <= 25)
        txs.append(
            Transaction(
                date=m_date + timedelta(days=9),
                amount_bdt=1000.0,
                direction="out",
                type="bill",
                raw_hash=f"bill_{m}",
            )
        )
        # Remittance sent every month
        txs.append(
            Transaction(
                date=m_date + timedelta(days=14),
                amount_bdt=4000.0,
                direction="out",
                type="remittance",
                raw_hash=f"rem_{m}",
            )
        )
        # Savings sent every month
        txs.append(
            Transaction(
                date=m_date + timedelta(days=20),
                amount_bdt=1000.0,
                direction="out",
                type="savings",
                raw_hash=f"sav_{m}",
            )
        )
        # Recharges every 15 days
        txs.append(
            Transaction(
                date=m_date + timedelta(days=5),
                amount_bdt=200.0,
                direction="out",
                type="recharge",
                raw_hash=f"rec1_{m}",
            )
        )
        txs.append(
            Transaction(
                date=m_date + timedelta(days=20),
                amount_bdt=200.0,
                direction="out",
                type="recharge",
                raw_hash=f"rec2_{m}",
            )
        )

    result = extract_features(txs, requested_amount_bdt=80000.0)
    assert result.needs_bhorsha is False
    feat = result.features

    assert feat["monthly_inflow_bdt"] == 20000.0
    assert feat["income_volatility"] == 0.02 or feat["income_volatility"] <= 0.05
    assert feat["bills_on_time"] == 0.9981 or feat["bills_on_time"] >= 0.95
    assert feat["savings_ratio"] == 0.05  # 4000 / 80000 = 0.05
    assert feat["sends_money_home"] == 1.0  # 100% of months sent remittance
    assert feat["loan_to_income"] == 4.0  # 80000 / 20000 = 4.0
    assert feat["recharge_regularity"] is not None and feat["recharge_regularity"] >= 0.85


def test_shathi_12_month_synthetic_sms_scores_approved() -> None:
    """Generate 12 months of synthetic SMS for Shathi, extract features, and verify approval."""
    # Shathi: garment worker in Ashulia (F_urban), receives 14,000 BDT monthly salary,
    # pays DESCO bill on time, sends 3,000 home monthly, saves 600 monthly, recharges regularly.
    sms_history: list[str] = []
    start_date = datetime(2025, 11, 1, 10, 0, tzinfo=UTC)

    for i in range(12):
        dt = start_date + timedelta(days=i * 30 + 1)
        d_str = dt.strftime("%d/%m/%Y")
        bill_d_str = (dt + timedelta(days=10)).strftime("%d/%m/%Y")
        rem_d_str = (dt + timedelta(days=15)).strftime("%d/%m/%Y")
        sav_d_str = (dt + timedelta(days=22)).strftime("%d/%m/%Y")
        rec1_d_str = (dt + timedelta(days=5)).strftime("%d/%m/%Y")
        rec2_d_str = (dt + timedelta(days=20)).strftime("%d/%m/%Y")

        # 1. Salary / Inflow
        sms_history.append(
            f"You have received Tk 14,000.00 from Garments Payroll on {d_str} 09:00. TrxID SAL{i:02d}."
        )
        # 2. DESCO Bill (on time)
        sms_history.append(
            f"Payment Tk 1,200.00 to DESCO Bill successful on {bill_d_str} 14:00. TrxID BIL{i:02d}."
        )
        # 3. Remittance to village
        sms_history.append(
            f"Send Money Tk 3,000.00 to 01712000000 successful on {rem_d_str} 11:30. TrxID REM{i:02d}."
        )
        # 4. Monthly Savings
        sms_history.append(
            f"Transfer Tk 600.00 to DPS Savings account successful on {sav_d_str} 16:15. TrxID SAV{i:02d}."
        )
        # 5. Airtime recharges
        sms_history.append(
            f"Mobile Recharge Tk 100.00 to 01811000000 successful on {rec1_d_str} 10:00. TrxID REC{i:02d}A."
        )
        sms_history.append(
            f"Mobile Recharge Tk 100.00 to 01811000000 successful on {rec2_d_str} 18:00. TrxID REC{i:02d}B."
        )

    # Parse SMS batch
    transactions = parse_sms_batch(sms_history, use_llm_fallback=True)
    assert len(transactions) >= 60

    # Extract features for 56,000 BDT requested microloan (loan_to_income = 4.0)
    result = extract_features(transactions, requested_amount_bdt=56000.0)
    assert result.needs_bhorsha is False
    feat = result.features

    assert feat["monthly_inflow_bdt"] == 14000.0
    assert feat["loan_to_income"] == 4.0
    assert feat["sends_money_home"] == 1.0
    assert feat["bills_on_time"] is not None and feat["bills_on_time"] >= 0.90

    # Run decision engine on Shathi's extracted features under F_urban demographic group
    decision = score_applicant(feat, group="F_urban")
    assert decision.approved is True, f"Expected Shathi to be approved, got: {decision}"
    assert decision.score >= 650
    assert decision.band in ("Good", "Excellent")
    assert len(decision.reasons) > 0


def test_parse_sms_endpoint_gated_by_demo_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify POST /parse/sms returns 403 Forbidden when DEMO_MODE=False, and succeeds when DEMO_MODE=True."""
    client = TestClient(create_app())

    sms_payload = {
        "sms_list": [
            "You have received Tk 15,000.00 from Payroll on 01/01/2026. TrxID SAL01.",
            "Payment Tk 1,000.00 to DESCO Bill successful on 10/01/2026. TrxID BIL01.",
            "Payment Tk 1,000.00 to DESCO Bill successful on 10/02/2026. TrxID BIL02.",
            "You have received Tk 15,000.00 from Payroll on 01/03/2026. TrxID SAL02.",
            "You have received Tk 15,000.00 from Payroll on 01/04/2026. TrxID SAL03.",
        ],
        "requested_amount_bdt": 45000.0,
    }

    # 1. DEMO_MODE = False -> 403 Forbidden
    monkeypatch.setattr("app.api.routers.features.get_settings", lambda: Settings(DEMO_MODE=False))
    resp = client.post("/parse/sms", json=sms_payload)
    assert resp.status_code == 403
    assert "DEMO_MODE=true" in resp.json()["detail"]

    # 2. DEMO_MODE = True -> 200 OK
    monkeypatch.setattr("app.api.routers.features.get_settings", lambda: Settings(DEMO_MODE=True))
    resp = client.post("/parse/sms", json=sms_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "transactions" in data
    assert "features" in data
    assert "needs_bhorsha" in data
    assert len(data["transactions"]) == 5


def test_post_features_snapshot_persisted() -> None:
    """Verify POST /features stores feature snapshot linked to applicant user."""
    from app.db.session import create_app_engine

    engine = create_app_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = TestingSessionLocal()

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    client = TestClient(app)

    try:
        # Seed test user
        user = User(
            id="user-features-1",
            phone_hash="phonehash1",
            gender="F",
            region="urban",
            division="Dhaka",
        )
        db_session.add(user)
        db_session.commit()

        payload = {
            "user_id": "user-features-1",
            "features": {
                "monthly_inflow_bdt": 18000.0,
                "income_volatility": 0.08,
                "months_on_wallet": 24.0,
                "txn_per_month": 15.0,
                "bills_on_time": 0.96,
                "recharge_regularity": 0.92,
                "savings_ratio": 0.06,
                "sends_money_home": 1.0,
                "loan_to_income": 3.5,
            },
            "source_summary": "Extracted from 12-month SMS history",
        }

        resp = client.post("/features", json=payload)
        assert resp.status_code == 201
        res_data = resp.json()
        assert res_data["user_id"] == "user-features-1"
        assert res_data["features"]["monthly_inflow_bdt"] == 18000.0

        # Query DB directly to verify persistence
        stored = db_session.query(FeatureSnapshot).filter_by(user_id="user-features-1").first()
        assert stored is not None
        assert stored.features["monthly_inflow_bdt"] == 18000.0
        assert stored.source_summary == "Extracted from 12-month SMS history"
    finally:
        db_session.close()


def _tx(day_offset: int, amount: float, direction: str, kind: str, tag: str) -> Transaction:
    base = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
    return Transaction(
        date=base + timedelta(days=day_offset),
        amount_bdt=amount,
        direction=direction,  # type: ignore[arg-type]
        type=kind,  # type: ignore[arg-type]
        raw_hash=tag,
    )


def test_tenure_txn_rate_and_volatility_formulas() -> None:
    """months_on_wallet, txn_per_month and income_volatility (CV of monthly inflow)."""
    txs = [
        _tx(m * 30 + 1, inc, "in", "income", f"i{m}")
        for m, inc in enumerate([10000, 20000, 10000, 20000])
    ]
    txs.append(_tx(110, 100, "out", "other", "o1"))
    res = extract_features(txs)
    feat = res.features
    # 110 days of history -> 3.61 months, but 4 calendar months touched -> effective 4
    assert feat["months_on_wallet"] == 4.0
    assert feat["txn_per_month"] == round(5 / 4.0, 4)
    # inflows 10k,20k,10k,20k -> mean 15k, std 5k -> CV 0.3333
    assert feat["income_volatility"] == round(5000 / 15000, 4)
    assert feat["loan_to_income"] is None  # no amount requested


def test_bills_on_time_uses_ocr_due_day_and_none_when_unseen() -> None:
    txs = [_tx(m * 30 + 1, 15000, "in", "income", f"i{m}") for m in range(4)]
    # bills paid on the 20th of each month
    txs += [_tx(m * 30 + 19, 900, "out", "bill", f"b{m}") for m in range(4)]
    assert extract_features(txs).features["bills_on_time"] >= 0.99  # default due day 25 (clipped)
    late = extract_features(txs, ocr_bills=[{"due_date": "2026-02-15", "paid": True}])
    assert late.features["bills_on_time"] <= 0.05  # due on the 15th -> all late

    no_bills = [_tx(m * 30 + 1, 15000, "in", "income", f"j{m}") for m in range(5)]
    assert extract_features(no_bills).features["bills_on_time"] is None
    assert extract_features(no_bills).features["recharge_regularity"] is None
    photos = [{"due_date": "2026-01-25", "paid": True}, {"due_date": "2026-02-25", "paid": False}]
    assert abs(extract_features(no_bills, ocr_bills=photos).features["bills_on_time"] - 0.5) < 0.01
