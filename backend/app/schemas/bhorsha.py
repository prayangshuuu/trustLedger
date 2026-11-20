"""Schemas for Bhorsha psychometric chat assessment."""

from pydantic import BaseModel, Field


class BhorshaStartRequest(BaseModel):
    """Payload to initiate a Bhorsha assessment session."""

    user_id: str = Field(..., description="Registered applicant identifier")


class BhorshaStartResponse(BaseModel):
    """Response returned upon starting a session with the initial question."""

    session_id: str
    question_id: str
    dimension: str
    question_text: str
    english_translation: str
    turn: int
    total_turns: int


class BhorshaAnswerRequest(BaseModel):
    """Applicant's answer to the current scenario."""

    answer: str = Field(
        ..., min_length=1, max_length=2000, description="Bengali or English conversational response"
    )
    elapsed_seconds: float = Field(
        default=10.0, ge=0.0, description="Response latency in seconds for anti-gaming detection"
    )


class BhorshaAnswerResponse(BaseModel):
    """Next scenario question or completion status."""

    completed: bool
    off_topic: bool = False
    turn: int
    total_turns: int | None = None
    acknowledgement: str | None = None
    message: str | None = None
    question_id: str | None = None
    dimension: str | None = None
    question_text: str | None = None
    english_translation: str | None = None


class BhorshaResultResponse(BaseModel):
    """Calculated Bhorsha psychometric outcome."""

    session_id: str
    bhorsha_score: float = Field(..., ge=0.0, le=100.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    dimension_scores: dict[str, float]
    anti_gaming_flags: list[str]
    is_consistent: bool
    snapshot_updated: bool = True
