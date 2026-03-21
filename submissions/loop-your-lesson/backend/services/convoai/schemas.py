"""Pydantic models for ConvoAI voice practice sessions."""

from pydantic import BaseModel, ConfigDict


class LanguagePair(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    l1: str  # Native language (e.g. "Spanish")
    l2: str  # Learning language (e.g. "English")


class ErrorDetail(BaseModel):
    """A single error from lesson analysis (Contract 1)."""

    model_config = ConfigDict(extra="forbid")

    error_type: str  # "grammar", "vocabulary", "pronunciation", "fluency"
    subtype: str  # "articles", "past_tense_irregular", etc.
    severity: str  # "minor", "moderate", "major"
    original: str  # What student said
    corrected: str  # What it should be
    explanation: str  # Human-readable correction
    l1_transfer: bool = False
    l1_transfer_explanation: str = ""
    pattern_status: str = ""  # "new", "recurring", "improving", "mastered"


class ThemeDetail(BaseModel):
    """A theme from lesson analysis (Contract 1)."""

    model_config = ConfigDict(extra="forbid")

    topic: str
    vocabulary: list[str] = []
    communicative_function: str = ""
    vocabulary_active: list[str] = []
    vocabulary_passive: list[str] = []
    chunks: list[str] = []


class QuizQuestionSummary(BaseModel):
    """Compact representation of a quiz question for the agent prompt."""

    model_config = ConfigDict(extra="forbid")

    index: int
    question_type: str  # "gap", "choice", "boolean", "categorizer", "sorter"
    title: str
    error_subtype: str
    error_type: str = ""


class LevelSummary(BaseModel):
    """Student level assessment snapshot for the agent prompt."""

    model_config = ConfigDict(extra="forbid")

    overall_level: str
    accuracy_level: str = ""
    fluency_level: str = ""
    strengths: list[str] = []
    gaps: list[str] = []


class QuizResult(BaseModel):
    """A single quiz answer event from Pusher."""

    model_config = ConfigDict(extra="forbid")

    question_id: str
    correctness: str  # "CORRECT", "PARTIALLY_CORRECT", "WRONG"
    points_centis: int = 0
    question_title: str = ""
    student_answer: str = ""
    error_type: str = ""
    error_subtype: str = ""


class MasteryError(BaseModel):
    """Per-error mastery tracking in Redis."""

    model_config = ConfigDict(extra="forbid")

    error_type: str
    subtype: str
    original: str
    corrected: str
    quiz_result: str | None = None  # None = untested, "CORRECT", "WRONG"
    quiz_answer: str = ""
    focus_level: str = "high"  # "low", "medium", "high", "critical"
    voice_practiced: bool = False


class BiomarkerState(BaseModel):
    """Student voice biomarker state from Thymia analysis."""

    model_config = ConfigDict(extra="forbid")

    stress: float = 0.0  # 0.0-1.0
    exhaustion: float = 0.0  # 0.0-1.0
    distress: float = 0.0  # 0.0-1.0


class MasteryState(BaseModel):
    """Full mastery state stored in Redis per voice session."""

    model_config = ConfigDict(extra="forbid")

    errors: list[MasteryError]
    summary: dict[str, int | list[str]] = {}
    quiz_events: list[dict] = []
    biomarkers: BiomarkerState = BiomarkerState()


class VoiceSessionStart(BaseModel):
    """Request to start a voice practice session."""

    model_config = ConfigDict(extra="forbid")

    student_id: str
    lesson_id: str
    classtime_session_code: str | None = None


class AgentResponse(BaseModel):
    """Response from ConvoAI agent API."""

    model_config = ConfigDict(extra="ignore")

    agent_id: str
    status: str
    create_ts: int | None = None


class VoiceSessionResponse(BaseModel):
    """Response after starting a voice practice session."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    channel_name: str
    rtc_token: str
    uid: int
    agent_id: str
    agora_app_id: str
    student_name: str
    student_level: str
