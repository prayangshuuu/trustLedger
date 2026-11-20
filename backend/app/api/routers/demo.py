"""Demo helpers (DEMO_MODE only): list and reseed the synthetic personas."""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import ApiKeyAuth, DbSession
from app.config import get_settings
from app.db.models import User

router = APIRouter(prefix="/demo", tags=["Demo"])

PERSONA_PHONES = {
    "moon": "+8801711000001",
    "student": "+8801811000002",
    "homemaker": "+8801911000003",
    "newcomer": "+8801611000004",
}
PERSONA_INFO = {
    "moon": "Moon, 24, garment worker in Ashulia. Wallet SMS + bills.",
    "student": "Rafi, 21, student and freelancer in Dhaka. Wallet + Bhorsha.",
    "homemaker": "Rina, 28, homemaker in Chattogram. No wallet, Bhorsha done.",
    "newcomer": "Mitu, 19, new to phones and wallets. No history: takes Bhorsha.",
}


def _require_demo() -> None:
    if not get_settings().DEMO_MODE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Demo endpoints need DEMO_MODE=true")


@router.get("/personas", summary="Demo persona user IDs")
def personas(db: DbSession, _api_key: ApiKeyAuth = None) -> list[dict[str, Any]]:
    _require_demo()
    from app.demo_seed import hash_phone

    out = []
    for key, phone in PERSONA_PHONES.items():
        user = db.scalars(select(User).where(User.phone_hash == hash_phone(phone))).first()
        if user:
            out.append(
                {
                    "key": key,
                    "user_id": user.id,
                    "group": f"{user.gender}_{user.region}",
                    "division": user.division,
                    "description": PERSONA_INFO[key],
                }
            )
    return out


@router.post("/reset", summary="Re-seed the 3 demo personas")
def reset(db: DbSession, _api_key: ApiKeyAuth = None) -> list[dict[str, Any]]:
    _require_demo()
    from app.demo_seed import seed_demo_personas

    seed_demo_personas(db)
    return personas(db)
