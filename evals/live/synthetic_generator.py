"""Synthetic user profile generator for live AI pipeline evaluation.

Generates 20 realistic applicant profiles with known ground-truth features,
rendered SMS message histories (bKash, Nagad, Rocket, Bank), and OCR bill records.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from app.core.decision import score_applicant
from app.parsers.features import extract_features
from app.parsers.sms import Transaction


def generate_synthetic_cohort() -> list[dict[str, Any]]:
    """Generate 20 diverse synthetic users with known ground truth."""
    profiles: list[dict[str, Any]] = [
        # 1-5: High-performing urban & rural borrowers (steady salary, on-time bills, savings)
        {
            "id": "live_user_01",
            "name": "Nasreen Akhtar",
            "gender": "F",
            "region": "urban",
            "group": "F_urban",
            "months": 8,
            "monthly_inflow": 28000.0,
            "has_bills": True,
            "bill_provider": "DESCO",
            "bill_amount": 1650.0,
            "bill_on_time": True,
            "savings_monthly": 2000.0,
            "sends_home": 0.0,
            "bhorsha": None,
        },
        {
            "id": "live_user_02",
            "name": "Tariqul Islam",
            "gender": "M",
            "region": "urban",
            "group": "M_urban",
            "months": 12,
            "monthly_inflow": 35000.0,
            "has_bills": True,
            "bill_provider": "DPDC",
            "bill_amount": 2200.0,
            "bill_on_time": True,
            "savings_monthly": 3500.0,
            "sends_home": 5000.0,
            "bhorsha": None,
        },
        {
            "id": "live_user_03",
            "name": "Rasheda Begum",
            "gender": "F",
            "region": "rural",
            "group": "F_rural",
            "months": 6,
            "monthly_inflow": 18000.0,
            "has_bills": True,
            "bill_provider": "BREB",
            "bill_amount": 750.0,
            "bill_on_time": True,
            "savings_monthly": 1500.0,
            "sends_home": 0.0,
            "bhorsha": 78.0,
        },
        {
            "id": "live_user_04",
            "name": "Anisur Rahman",
            "gender": "M",
            "region": "rural",
            "group": "M_rural",
            "months": 10,
            "monthly_inflow": 22000.0,
            "has_bills": True,
            "bill_provider": "NESCO",
            "bill_amount": 950.0,
            "bill_on_time": True,
            "savings_monthly": 1800.0,
            "sends_home": 3000.0,
            "bhorsha": None,
        },
        {
            "id": "live_user_05",
            "name": "Shirin Sultana",
            "gender": "F",
            "region": "urban",
            "group": "F_urban",
            "months": 7,
            "monthly_inflow": 24000.0,
            "has_bills": True,
            "bill_provider": "DESCO",
            "bill_amount": 1400.0,
            "bill_on_time": True,
            "savings_monthly": 1200.0,
            "sends_home": 0.0,
            "bhorsha": None,
        },
        # 6-10: Moderate risk profiles (fluctuating cash-in, occasional late bills)
        {
            "id": "live_user_06",
            "name": "Kamal Hossain",
            "gender": "M",
            "region": "urban",
            "group": "M_urban",
            "months": 9,
            "monthly_inflow": 19000.0,
            "has_bills": True,
            "bill_provider": "TITAS",
            "bill_amount": 1080.0,
            "bill_on_time": False,
            "savings_monthly": 500.0,
            "sends_home": 4000.0,
            "bhorsha": None,
        },
        {
            "id": "live_user_07",
            "name": "Parveen Banu",
            "gender": "F",
            "region": "rural",
            "group": "F_rural",
            "months": 5,
            "monthly_inflow": 14000.0,
            "has_bills": True,
            "bill_provider": "BREB",
            "bill_amount": 620.0,
            "bill_on_time": True,
            "savings_monthly": 400.0,
            "sends_home": 0.0,
            "bhorsha": 65.0,
        },
        {
            "id": "live_user_08",
            "name": "Zahid Hasan",
            "gender": "M",
            "region": "rural",
            "group": "M_rural",
            "months": 6,
            "monthly_inflow": 16000.0,
            "has_bills": True,
            "bill_provider": "BREB",
            "bill_amount": 800.0,
            "bill_on_time": False,
            "savings_monthly": 600.0,
            "sends_home": 2500.0,
            "bhorsha": None,
        },
        {
            "id": "live_user_09",
            "name": "Meherun Nesa",
            "gender": "F",
            "region": "urban",
            "group": "F_urban",
            "months": 11,
            "monthly_inflow": 21000.0,
            "has_bills": True,
            "bill_provider": "WASA",
            "bill_amount": 950.0,
            "bill_on_time": True,
            "savings_monthly": 800.0,
            "sends_home": 0.0,
            "bhorsha": None,
        },
        {
            "id": "live_user_10",
            "name": "Biplob Chandra",
            "gender": "M",
            "region": "urban",
            "group": "M_urban",
            "months": 7,
            "monthly_inflow": 23000.0,
            "has_bills": True,
            "bill_provider": "DPDC",
            "bill_amount": 1750.0,
            "bill_on_time": True,
            "savings_monthly": 1000.0,
            "sends_home": 3000.0,
            "bhorsha": None,
        },
        # 11-15: Thin-file / Bhorsha psychometric users (short history, reliance on Bhorsha)
        {
            "id": "live_user_11",
            "name": "Sabina Yeasmin",
            "gender": "F",
            "region": "rural",
            "group": "F_rural",
            "months": 2,  # < 3 months => requires Bhorsha
            "monthly_inflow": 12000.0,
            "has_bills": False,
            "bill_provider": None,
            "bill_amount": 0.0,
            "bill_on_time": False,
            "savings_monthly": 0.0,
            "sends_home": 0.0,
            "bhorsha": 82.0,
        },
        {
            "id": "live_user_12",
            "name": "Asaduzzaman Noor",
            "gender": "M",
            "region": "rural",
            "group": "M_rural",
            "months": 2,
            "monthly_inflow": 15000.0,
            "has_bills": False,
            "bill_provider": None,
            "bill_amount": 0.0,
            "bill_on_time": False,
            "savings_monthly": 0.0,
            "sends_home": 0.0,
            "bhorsha": 74.0,
        },
        {
            "id": "live_user_13",
            "name": "Farzana Haque",
            "gender": "F",
            "region": "urban",
            "group": "F_urban",
            "months": 4,
            "monthly_inflow": 17000.0,
            "has_bills": True,
            "bill_provider": "DESCO",
            "bill_amount": 1100.0,
            "bill_on_time": True,
            "savings_monthly": 500.0,
            "sends_home": 0.0,
            "bhorsha": 85.0,
        },
        {
            "id": "live_user_14",
            "name": "Shahidul Alam",
            "gender": "M",
            "region": "urban",
            "group": "M_urban",
            "months": 4,
            "monthly_inflow": 26000.0,
            "has_bills": True,
            "bill_provider": "DPDC",
            "bill_amount": 1900.0,
            "bill_on_time": True,
            "savings_monthly": 1500.0,
            "sends_home": 4000.0,
            "bhorsha": 70.0,
        },
        {
            "id": "live_user_15",
            "name": "Jannatul Ferdous",
            "gender": "F",
            "region": "rural",
            "group": "F_rural",
            "months": 5,
            "monthly_inflow": 16000.0,
            "has_bills": True,
            "bill_provider": "BREB",
            "bill_amount": 550.0,
            "bill_on_time": True,
            "savings_monthly": 800.0,
            "sends_home": 0.0,
            "bhorsha": 79.0,
        },
        # 16-20: Higher risk / low income / irregular profiles
        {
            "id": "live_user_16",
            "name": "Alamin Sheikh",
            "gender": "M",
            "region": "rural",
            "group": "M_rural",
            "months": 6,
            "monthly_inflow": 8500.0,
            "has_bills": True,
            "bill_provider": "BREB",
            "bill_amount": 750.0,
            "bill_on_time": False,
            "savings_monthly": 0.0,
            "sends_home": 0.0,
            "bhorsha": 42.0,
        },
        {
            "id": "live_user_17",
            "name": "Ruma Pal",
            "gender": "F",
            "region": "rural",
            "group": "F_rural",
            "months": 5,
            "monthly_inflow": 9000.0,
            "has_bills": True,
            "bill_provider": "BREB",
            "bill_amount": 680.0,
            "bill_on_time": False,
            "savings_monthly": 0.0,
            "sends_home": 0.0,
            "bhorsha": 48.0,
        },
        {
            "id": "live_user_18",
            "name": "Sujon Mia",
            "gender": "M",
            "region": "urban",
            "group": "M_urban",
            "months": 7,
            "monthly_inflow": 11000.0,
            "has_bills": True,
            "bill_provider": "TITAS",
            "bill_amount": 1080.0,
            "bill_on_time": False,
            "savings_monthly": 0.0,
            "sends_home": 1000.0,
            "bhorsha": None,
        },
        {
            "id": "live_user_19",
            "name": "Kohinoor Begum",
            "gender": "F",
            "region": "urban",
            "group": "F_urban",
            "months": 8,
            "monthly_inflow": 12500.0,
            "has_bills": True,
            "bill_provider": "DESCO",
            "bill_amount": 1350.0,
            "bill_on_time": False,
            "savings_monthly": 200.0,
            "sends_home": 0.0,
            "bhorsha": 55.0,
        },
        {
            "id": "live_user_20",
            "name": "Manik Hossain",
            "gender": "M",
            "region": "rural",
            "group": "M_rural",
            "months": 6,
            "monthly_inflow": 10500.0,
            "has_bills": True,
            "bill_provider": "BREB",
            "bill_amount": 820.0,
            "bill_on_time": False,
            "savings_monthly": 100.0,
            "sends_home": 500.0,
            "bhorsha": None,
        },
    ]

    base_time = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    cohort: list[dict[str, Any]] = []

    for p in profiles:
        months = p["months"]
        monthly_inflow = p["monthly_inflow"]
        raw_sms_lines: list[str] = []
        ground_truth_txs: list[Transaction] = []
        bill_records: list[dict[str, Any]] = []

        # Generate month-by-month financial events
        for m in range(months):
            m_date = base_time - timedelta(days=30 * (months - 1 - m))

            # 1. Salary / Inflow (bKash Cash In / Transfer)
            inf_date = m_date.replace(day=5)
            trx_inf = f"TX{p['id'][-2:]}{m:02d}INF"
            sms_inf = f"You have received Tk {monthly_inflow:,.2f} from Employer Co. Ref: Salary. Fee Tk 0.00. Balance Tk {monthly_inflow * 1.2:,.2f}. TrxID {trx_inf} at {inf_date.strftime('%d/%m/%Y %H:%M')}"
            raw_sms_lines.append(sms_inf)
            ground_truth_txs.append(
                Transaction(
                    date=inf_date,
                    amount_bdt=monthly_inflow,
                    direction="in",
                    type="income",
                    counterparty="Employer Co",
                    txn_id=trx_inf,
                    raw_hash=f"hash_{trx_inf}",
                    confidence=1.0,
                )
            )

            # 2. Mobile Recharge
            rec_date = m_date.replace(day=12)
            trx_rec = f"TX{p['id'][-2:]}{m:02d}REC"
            rec_amt = 250.0
            sms_rec = f"Mobile Recharge of Tk {rec_amt:.2f} to 01712345678 is successful. Fee Tk 0.00. Balance Tk {monthly_inflow:,.2f}. TrxID {trx_rec} at {rec_date.strftime('%d/%m/%Y %H:%M')}"
            raw_sms_lines.append(sms_rec)
            ground_truth_txs.append(
                Transaction(
                    date=rec_date,
                    amount_bdt=rec_amt,
                    direction="out",
                    type="recharge",
                    counterparty="Grameenphone",
                    txn_id=trx_rec,
                    raw_hash=f"hash_{trx_rec}",
                    confidence=1.0,
                )
            )

            # 3. Utility Bill Payment
            if p["has_bills"] and p["bill_amount"] > 0:
                bill_date = m_date.replace(day=18 if p["bill_on_time"] else 28)
                trx_bill = f"TX{p['id'][-2:]}{m:02d}BIL"
                b_amt = p["bill_amount"]
                b_prov = p["bill_provider"]
                sms_bill = f"Payment of Tk {b_amt:.2f} to {b_prov} is successful. Fee Tk 5.00. Balance Tk {monthly_inflow * 0.7:,.2f}. TrxID {trx_bill} at {bill_date.strftime('%d/%m/%Y %H:%M')}"
                raw_sms_lines.append(sms_bill)
                ground_truth_txs.append(
                    Transaction(
                        date=bill_date,
                        amount_bdt=b_amt,
                        direction="out",
                        type="bill",
                        counterparty=b_prov,
                        txn_id=trx_bill,
                        raw_hash=f"hash_{trx_bill}",
                        confidence=1.0,
                    )
                )

            # 4. Sends Money Home
            if p["sends_home"] > 0:
                sm_date = m_date.replace(day=10)
                trx_sm = f"TX{p['id'][-2:]}{m:02d}SM"
                sm_amt = p["sends_home"]
                sms_sm = f"Send Money of Tk {sm_amt:.2f} to 01899887766 is successful. Fee Tk 5.00. Balance Tk {monthly_inflow * 0.5:,.2f}. TrxID {trx_sm} at {sm_date.strftime('%d/%m/%Y %H:%M')}"
                raw_sms_lines.append(sms_sm)
                ground_truth_txs.append(
                    Transaction(
                        date=sm_date,
                        amount_bdt=sm_amt,
                        direction="out",
                        type="transfer",
                        counterparty="Village Family",
                        txn_id=trx_sm,
                        raw_hash=f"hash_{trx_sm}",
                        confidence=1.0,
                    )
                )

            # 5. Monthly Savings
            if p["savings_monthly"] > 0:
                sav_date = m_date.replace(day=22)
                trx_sav = f"TX{p['id'][-2:]}{m:02d}SAV"
                sav_amt = p["savings_monthly"]
                sms_sav = f"DPS deposit of Tk {sav_amt:.2f} to BRAC Bank DPS is successful. TrxID {trx_sav} at {sav_date.strftime('%d/%m/%Y %H:%M')}"
                raw_sms_lines.append(sms_sav)
                ground_truth_txs.append(
                    Transaction(
                        date=sav_date,
                        amount_bdt=sav_amt,
                        direction="out",
                        type="savings",
                        counterparty="BRAC Bank DPS",
                        txn_id=trx_sav,
                        raw_hash=f"hash_{trx_sav}",
                        confidence=1.0,
                    )
                )

        # Sort ground truth transactions chronologically by date
        ground_truth_txs.sort(key=lambda t: t.date)

        # Generate OCR Bill record if applicant has bill
        if p["has_bills"] and p["bill_amount"] > 0:
            bill_records.append(
                {
                    "document_type": "utility_bill",
                    "provider": p["bill_provider"],
                    "amount_bdt": float(p["bill_amount"]),
                    "due_date": f"{base_time.year}-{base_time.month:02d}-25",
                    "bill_month": f"{base_time.strftime('%B %Y')}",
                    "confidence": 0.98,
                }
            )

        # Compute true features directly from ground-truth transactions
        extracted = extract_features(
            transactions=ground_truth_txs,
            requested_amount_bdt=15000.0,
            ocr_bills=bill_records or None,
            default_due_day=25,
        )
        true_features = dict(extracted.features)
        if p["bhorsha"] is not None:
            true_features["bhorsha_score"] = float(p["bhorsha"])

        # Ground truth decision
        try:
            true_decision = score_applicant(true_features, group=p["group"])
            approved = true_decision.approved
            score_val = true_decision.score
        except Exception:  # noqa: BLE001
            approved = False
            score_val = 450

        cohort.append(
            {
                "user_id": p["id"],
                "name": p["name"],
                "group": p["group"],
                "gender": p["gender"],
                "region": p["region"],
                "months": months,
                "sms_messages": raw_sms_lines,
                "bill_records": bill_records,
                "ground_truth_transactions": [t.model_dump(mode="json") for t in ground_truth_txs],
                "ground_truth_features": true_features,
                "ground_truth_approved": approved,
                "ground_truth_score": score_val,
                "needs_bhorsha": extracted.needs_bhorsha or (months < 3),
            }
        )

    return cohort


if __name__ == "__main__":
    users = generate_synthetic_cohort()
    print(f"Generated {len(users)} synthetic profiles.")
    with open("evals/live/synthetic_cohort.json", "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)
    print("Saved cohort to evals/live/synthetic_cohort.json")
