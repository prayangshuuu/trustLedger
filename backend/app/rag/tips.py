"""Ground Bangla tips in the knowledge base: each tip may cite one retrieved source."""

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.rag.retrieve import retrieve

# Retrieval query per feature (Bangla + English keeps BM25 and embeddings both useful)
FEATURE_QUERIES: dict[str, str] = {
    "bills_on_time": "সময়মতো বিল পরিশোধ bills on time due date",
    "savings_ratio": "নিয়মিত সঞ্চয় আয়ের ৫% savings ratio",
    "recharge_regularity": "রিচার্জের নিয়মিততা recharge regularity",
    "income_volatility": "আয়ের স্থিতিশীলতা income volatility",
    "loan_to_income": "ঋণ-আয়ের অনুপাত ছোট ঋণ loan to income",
    "months_on_wallet": "ওয়ালেট ইতিহাস তিন মাস wallet history",
    "bhorsha_score": "ভরসা মূল্যায়ন bhorsha assessment",
    "monthly_inflow_bdt": "মাসিক আয় monthly income",
    "txn_per_month": "মাসিক লেনদেন transactions per month",
    "sends_money_home": "পরিবারে টাকা পাঠানো remittance",
}


class TipSource(BaseModel):
    title: str
    url: str
    excerpt: str


class GroundedTip(BaseModel):
    feature: str
    text: str
    source: TipSource | None = None


def ground_tips(db: Session | None, tips: list[tuple[str, str]]) -> list[GroundedTip]:
    """Attach at most one source per (feature, tip). Without a DB or chunks, tips are uncited."""
    grounded: list[GroundedTip] = []
    for feature, text in tips:
        source: TipSource | None = None
        if db is not None:
            try:
                hits = retrieve(db, FEATURE_QUERIES.get(feature, feature), k=1)
            except Exception:  # noqa: BLE001 - grounding is best-effort, tips stay valid
                hits = []
            if hits:
                h = hits[0]
                source = TipSource(title=h.title, url=h.source_url, excerpt=h.content[:220])
        grounded.append(GroundedTip(feature=feature, text=text, source=source))
    return grounded
