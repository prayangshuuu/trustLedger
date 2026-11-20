"""Run every offline evaluation and enforce the quality gates.

    uv run python evals/run_all.py                 # writes training_files/eval_report.json + evals/EVAL_REPORT.md
    uv run python evals/run_all.py --update-golden # refresh prompt-regression goldens after a reviewed change

Exit code 1 when any gate fails (CI uses this). Live-only checks (LLM-as-judge, RAGAS with a
real LLM) run when LLM_MODE=live and DEEPSEEK_API_KEY is set; otherwise they are reported as skipped.
"""

import argparse
import contextlib
import io
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from app.agents.explainer import explain_decision
from app.core.decision import score_applicant
from app.core.model import load_meta, load_model
from app.llm.client import get_llm_client, is_live
from sklearn.metrics import brier_score_loss, roc_auc_score, roc_curve

from federated.data import FEATURES, load_dataset

GOLDEN_DIR = ROOT / "evals" / "prompts" / "golden"
TEST_SPLIT = ROOT / "evals" / "data" / "test_split.csv.gz"
REPORT_JSON = ROOT / "training_files" / "eval_report.json"
REPORT_MD = ROOT / "evals" / "EVAL_REPORT.md"
MAX_GAP = 0.05


# ---------------------------------------------------------------- model + fairness


def test_split() -> tuple[pd.DataFrame, str]:
    """The notebook's held-out test split (20,000 rows, seed 42)."""
    from sklearn.model_selection import train_test_split

    from federated.data import DATA_PATH

    if DATA_PATH.exists():
        df = load_dataset()
        _, rest = train_test_split(df, test_size=0.4, stratify=df.repaid, random_state=42)
        _, te = train_test_split(rest, test_size=0.5, stratify=rest.repaid, random_state=42)
        return te.reset_index(
            drop=True
        ), "datasets/trustledger_synthetic_bd.csv (notebook test split)"
    # CI: datasets/ is git-ignored, so the same synthetic test split is committed
    return pd.read_csv(TEST_SPLIT), "evals/data/test_split.csv.gz (notebook test split)"


def group_gaps(y: np.ndarray, approved: np.ndarray, groups: np.ndarray) -> dict[str, Any]:
    d = pd.DataFrame({"y": y, "a": approved, "g": groups})
    by = {}
    for g, gd in d.groupby("g"):
        by[str(g)] = {
            "n": len(gd),
            "approval_rate": round(float(gd.a.mean()), 4),
            "tpr": round(float(gd[gd.y == 1].a.mean()), 4),
            "fpr": round(float(gd[gd.y == 0].a.mean()), 4),
        }

    def spread(k: str) -> float:
        vals = [v[k] for v in by.values()]
        return round(max(vals) - min(vals), 4)

    return {
        "by_group": by,
        "approval_rate_gap": spread("approval_rate"),
        "equalized_odds_gap": max(spread("tpr"), spread("fpr")),
    }


def fairlearn_check(y: np.ndarray, approved: np.ndarray, groups: np.ndarray) -> dict[str, Any]:
    """Independent cross-check of our gap computation with Fairlearn's metrics."""
    from fairlearn.metrics import demographic_parity_difference, equalized_odds_difference

    return {
        "demographic_parity_difference": round(
            float(demographic_parity_difference(y, approved, sensitive_features=groups)), 4
        ),
        "equalized_odds_difference": round(
            float(equalized_odds_difference(y, approved, sensitive_features=groups)), 4
        ),
    }


def model_eval(thresholds: dict[str, float] | None = None) -> dict[str, Any]:
    te, source = test_split()
    meta = load_meta()
    thresholds = thresholds or meta["group_thresholds"]
    p = load_model().predict_proba(te[FEATURES].astype(float))[:, 1]
    y = te.repaid.to_numpy()
    fpr, tpr, _ = roc_curve(y, p)
    bins = np.clip((p * 10).astype(int), 0, 9)
    ece = sum(
        abs(p[bins == b].mean() - y[bins == b].mean()) * (bins == b).mean()
        for b in range(10)
        if (bins == b).any()
    )
    calibration = [
        {
            "bin": b,
            "mean_pred": round(float(p[bins == b].mean()), 4),
            "observed": round(float(y[bins == b].mean()), 4),
        }
        for b in range(10)
        if (bins == b).sum() >= 20
    ]
    out: dict[str, Any] = {
        "data": source,
        "n_test": len(te),
        "auc": round(float(roc_auc_score(y, p)), 4),
        "ks": round(float(np.max(tpr - fpr)), 4),
        "brier": round(float(brier_score_loss(y, p)), 4),
        "ece": round(float(ece), 4),
        "calibration": calibration,
    }
    single = (p >= meta["threshold"]).astype(int)
    fair = np.array([int(pi >= thresholds[g]) for pi, g in zip(p, te.group, strict=True)])
    before = group_gaps(y, single, te.group.to_numpy())
    after = group_gaps(y, fair, te.group.to_numpy())
    bank = (
        (te.has_bank_account == 1) & ((te.has_salary_slip == 1) | (te.monthly_inflow_bdt >= 25000))
    ).to_numpy()
    out["fairness"] = {
        "before": {k: before[k] for k in ("approval_rate_gap", "equalized_odds_gap")},
        "after": after,
        "gate_ok": after["approval_rate_gap"] <= MAX_GAP and after["equalized_odds_gap"] <= MAX_GAP,
        "fairlearn": fairlearn_check(y, fair, te.group.to_numpy()),
    }
    out["inclusion"] = {
        "bank_rule_approval": round(float(bank.mean()), 4),
        "trustledger_approval": round(float(fair.mean()), 4),
        "newly_included": round(float(((fair == 1) & ~bank).mean()), 4),
    }
    return out


# ---------------------------------------------------------------- explanations


def explanation_eval(n: int = 300) -> dict[str, Any]:
    te, _ = test_split()
    sample = te.sample(min(n, len(te)), random_state=7)
    violations = 0
    weak = 0
    checked = 0
    for _, row in sample.iterrows():
        feats = {f: (None if pd.isna(row[f]) else float(row[f])) for f in FEATURES}
        group = row["group"] if row["group"] in load_meta()["group_thresholds"] else "F_urban"
        decision = score_applicant(feats, group)
        out = explain_decision(None, decision)
        shap_feats = {r.feature for r in decision.reasons}
        violations += not set(out.mentioned_features) <= shap_feats
        weak += any(abs(r.impact) < 0.02 or feats.get(r.feature) is None for r in decision.reasons)
        checked += 1
    result: dict[str, Any] = {
        "checked": checked,
        "summary_mentions_only_shap_features": checked - violations,
        "violations": violations,
        "reasons_respect_min_impact_and_missing": checked - weak,
        "llm_judge": "skipped (mock mode)",
    }
    if is_live():
        result["llm_judge"] = llm_judge_explanations(sample.head(20))
    return result


def llm_judge_explanations(rows: pd.DataFrame) -> dict[str, Any]:
    from pydantic import BaseModel

    class Verdict(BaseModel):
        faithful: bool

    ok = 0
    for _, row in rows.iterrows():
        feats = {f: (None if pd.isna(row[f]) else float(row[f])) for f in FEATURES}
        d = score_applicant(feats, row["group"])
        out = explain_decision(None, d)
        reasons = "; ".join(f"{r.feature} {r.kind} {r.impact:+.3f}" for r in d.reasons)
        v = get_llm_client().chat(
            [
                {
                    "role": "system",
                    "content": 'Judge if the Bangla summary is faithful to the SHAP reasons (no other factors, correct direction). JSON {"faithful": bool}',
                },
                {
                    "role": "user",
                    "content": f"<shap>{reasons}</shap>\n<summary>{out.summary_bn}</summary>",
                },
            ],
            schema=Verdict,
        )
        ok += v.faithful
    return {"judged": len(rows), "faithful_rate": round(ok / len(rows), 4)}


# ---------------------------------------------------------------- Bhorsha

RESPONSIBLE = "আমি মাসের শুরুতে বাজেট করি, সঞ্চয় আলাদা রাখি, ঝুঁকি বুঝে সিদ্ধান্ত নিই এবং কিস্তি সময়মতো দিই {i}"
CARELESS = "টাকা হাতে আসলেই খরচ করে ফেলি, লটারি খেলি আর পরে ধার করি {i}"


def bhorsha_eval() -> dict[str, Any]:
    from app.bhorsha.scorer import compute_bhorsha_score, evaluate_single_answer, load_question_bank

    qs = load_question_bank()

    def run(template: str) -> float:
        evals: list[Any] = []
        answers: list[str] = []
        for i, q in enumerate(qs):
            a = template.format(i=i)
            evals.append(evaluate_single_answer(q, a, elapsed_seconds=12, previous_answers=answers))
            answers.append(a)
        return compute_bhorsha_score(evals, qs).bhorsha_score

    r1, r2, c1 = run(RESPONSIBLE), run(RESPONSIBLE), run(CARELESS)
    return {
        "responsible": r1,
        "careless": c1,
        "stable": r1 == r2,
        "ordering_ok": r1 > c1 + 20,
    }


# ---------------------------------------------------------------- prompt regression


NOVEL_SMS = {
    "novel_credit": "Dear customer, a sum of Tk 2,350.00 has been credited from Rahim Traders.",
    "novel_debit": "Your wallet was debited Tk 410 for Online Purchase XYZ.",
}


def sms_case(text: str) -> dict[str, Any]:
    from app.parsers.sms import parse_sms

    t = parse_sms(text)
    return {"type": t.type, "direction": t.direction, "amount": t.amount_bdt}


def prompt_cases() -> dict[str, Any]:
    from app.agents.prompts import prompt_versions
    from app.bhorsha.interviewer import interviewer_turn
    from app.bhorsha.scorer import load_question_bank, prompt_version, rubric_score

    shathi = {
        "monthly_inflow_bdt": 14000.0, "income_volatility": 0.10, "months_on_wallet": 30.0, "txn_per_month": 18.0,
        "bills_on_time": 0.97, "recharge_regularity": 0.90, "savings_ratio": 0.04, "sends_money_home": 1.0,
        "bhorsha_score": None, "loan_to_income": 4.0,
    }  # fmt: skip
    d = score_applicant(shathi, "F_urban")
    exp = explain_decision(None, d)
    q = load_question_bank()[0]
    cases: dict[str, Any] = {
        "prompt_versions": {
            **prompt_versions(),
            "bhorsha_scorer": prompt_version("scorer"),
            "bhorsha_interviewer": prompt_version("interviewer"),
        },
        "explainer_agent": {
            "summary_bn": exp.summary_bn,
            "mentioned": exp.mentioned_features,
            "score": d.score,
        },
        "bhorsha_rubric": {
            name: rubric_score(q, a)[0]
            for name, a in {
                "strong": "মাসের শুরুতে লিখিত বাজেট করি, বিল আগে আলাদা করি, সঞ্চয় রাখি",
                "weak": "টাকা পেলেই খরচ করে ফেলি, পরে ধার করি",
                "neutral": "যেমন দরকার তেমন খরচ করি",
            }.items()
        },
        "bhorsha_interviewer": {
            "on_topic": interviewer_turn(q, "বাজেট করে খরচ করি").off_topic,
            "off_topic": interviewer_turn(q, "কাল ক্রিকেট খেলা কে জিতবে?").off_topic,
        },
        "sms_parser_llm_fallback": {k: sms_case(v) for k, v in NOVEL_SMS.items()},
        "pipeline": pipeline_case(),
    }
    return cases


def pipeline_case() -> dict[str, Any]:
    from app.agents.graph import run_pipeline
    from app.db.base import Base
    from app.db.session import create_app_engine
    from app.demo_seed import seed_demo_personas
    from sqlalchemy.orm import sessionmaker

    engine = create_app_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    out: dict[str, Any] = {}
    with sessionmaker(bind=engine)() as db:
        for user in seed_demo_personas(db):
            user = db.merge(user)
            state = run_pipeline(db, user, 15000)
            dec = state.get("decision") or {}
            out[f"{user.gender}_{user.region}_{user.division}"] = {
                "status": state.get("status"),
                "score": dec.get("score"),
                "nodes": [t["node"] for t in state.get("trace", [])],
            }
    return out


def prompt_regression(update: bool) -> dict[str, Any]:
    if is_live():
        return {"skipped": "live mode output is not deterministic; goldens are for mock mode"}
    cases = prompt_cases()
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    mismatches = []
    for name, value in cases.items():
        path = GOLDEN_DIR / f"{name}.json"
        current = json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True))
        if update or not path.exists():
            path.write_text(
                json.dumps(current, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            )
            continue
        if json.loads(path.read_text()) != current:
            mismatches.append(name)
    return {"cases": len(cases), "mismatches": mismatches, "ok": not mismatches}


# ---------------------------------------------------------------- runner


def quiet(fn: Any, *args: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args)


def run(update_golden: bool = False) -> dict[str, Any]:
    from evals.ocr.evaluate import run_evaluation as ocr_eval
    from evals.rag.evaluate import run as rag_eval
    from evals.sms.evaluate import run as sms_eval

    metrics = json.loads((ROOT / "training_files" / "metrics.json").read_text())["trustledger"]
    report: dict[str, Any] = {"mode": "live" if is_live() else "mock"}
    report["model"] = model_eval()
    report["sms_parser"] = sms_eval()
    report["ocr"] = {
        "field_f1": round(float(quiet(ocr_eval)), 4),
        "note": "mock mode returns labelled fields; measures the pipeline, not OCR accuracy",
    }
    report["rag"] = rag_eval()
    report["explanations"] = explanation_eval()
    report["bhorsha"] = bhorsha_eval()
    report["prompt_regression"] = prompt_regression(update_golden)

    m = report["model"]
    gates = {
        "model_auc_not_below_notebook": m["auc"] >= metrics["auc"] - 0.01,
        "fairness_gaps_le_0.05": m.get("fairness", {}).get("gate_ok", True),
        "fairlearn_agrees": abs(
            m["fairness"]["fairlearn"]["demographic_parity_difference"]
            - m["fairness"]["after"]["approval_rate_gap"]
        )
        <= 0.005
        and abs(
            m["fairness"]["fairlearn"]["equalized_odds_difference"]
            - m["fairness"]["after"]["equalized_odds_gap"]
        )
        <= 0.005,
        "sms_type_f1_ge_0.95": report["sms_parser"]["type_macro_f1"] >= 0.95,
        "ocr_field_f1_ge_0.90": report["ocr"]["field_f1"] >= 0.90,
        "rag_hit_rate_ge_0.90": report["rag"]["hit_rate"] >= 0.90,
        "explanations_only_shap_features": report["explanations"]["violations"] == 0,
        "bhorsha_stable_and_ordered": report["bhorsha"]["stable"]
        and report["bhorsha"]["ordering_ok"],
        "prompt_regression": report["prompt_regression"].get("ok", True),
    }
    report["gates"] = gates
    report["all_gates_pass"] = all(gates.values())
    return report


def write_markdown(r: dict[str, Any]) -> str:
    m = r["model"]
    lines = [
        "# Evaluation report",
        "",
        f"Mode: **{r['mode']}** · generated by `uv run python evals/run_all.py` · all gates: **{'PASS' if r['all_gates_pass'] else 'FAIL'}**",
        "",
        "## Gates",
        "",
        "| Gate | Result |",
        "|---|---|",
        *[f"| {k} | {'PASS' if v else 'FAIL'} |" for k, v in r["gates"].items()],
        "",
        "## Model (held-out test set)",
        "",
        f"Data: {m['data']} · n = {m['n_test']}",
        "",
        "| AUC | KS | Brier | ECE |",
        "|---|---|---|---|",
        f"| {m['auc']} | {m['ks']} | {m['brier']} | {m['ece']} |",
    ]
    if "fairness" in m:
        f = m["fairness"]
        lines += [
            "",
            "## Fairness",
            "",
            "| | Approval-rate gap | Equalized-odds gap |",
            "|---|---|---|",
            f"| Single threshold | {f['before']['approval_rate_gap']} | {f['before']['equalized_odds_gap']} |",
            f"| Group thresholds | {f['after']['approval_rate_gap']} | {f['after']['equalized_odds_gap']} |",
            "",
            (
                f"Fairlearn cross-check: demographic parity {f['fairlearn']['demographic_parity_difference']}, "
                f"equalized odds {f['fairlearn']['equalized_odds_difference']}"
            ),
            "",
            f"Inclusion: bank rule {m['inclusion']['bank_rule_approval']:.1%} · TrustLedger {m['inclusion']['trustledger_approval']:.1%} · newly included {m['inclusion']['newly_included']:.1%}",
        ]
    s, o, g, e, b = r["sms_parser"], r["ocr"], r["rag"], r["explanations"], r["bhorsha"]
    lines += [
        "",
        "## AI components",
        "",
        "| Component | Metric | Value |",
        "|---|---|---|",
        f"| SMS parser ({s['fixtures']} fixtures) | type macro-F1 / direction / amount | {s['type_macro_f1']} / {s['direction_accuracy']} / {s['amount_accuracy']} |",
        f"| OCR (10 synthetic images) | field F1 | {o['field_f1']} ({o['note']}) |",
        f"| RAG (30 questions, k={g['k']}) | context precision / recall / hit rate / faithfulness | {g['context_precision']} / {g['context_recall']} / {g['hit_rate']} / {g['faithfulness']} |",
        f"| Explanations ({e['checked']} test applicants) | summary mentions only SHAP features | {e['summary_mentions_only_shap_features']}/{e['checked']} |",
        f"| Explanations | LLM-as-judge | {e['llm_judge']} |",
        f"| Bhorsha | responsible / careless score, stable | {b['responsible']} / {b['careless']}, {b['stable']} |",
        f"| Prompt regression | goldens matched | {r['prompt_regression']} |",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--update-golden", action="store_true")
    args = parser.parse_args()
    report = run(args.update_golden)
    REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    REPORT_MD.write_text(write_markdown(report))
    print(write_markdown(report))
    sys.exit(0 if report["all_gates_pass"] else 1)


if __name__ == "__main__":
    main()
