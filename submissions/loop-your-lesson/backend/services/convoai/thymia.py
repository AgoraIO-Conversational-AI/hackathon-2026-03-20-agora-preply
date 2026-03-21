"""Thymia voice biomarker integration via Sentinel WebSocket SDK.

Uses the `thymia-sentinel` package for real-time streaming analysis
with the pre-built `student_monitor` policy that returns actionable
tutor recommendations (slow_down, take_break, check_understanding).

Architecture:
  go-audio-subscriber (sidecar) captures RTC audio
    -> our backend receives PCM chunks via callback
    -> streams to Thymia Sentinel via WebSocket
    -> receives policy results (classification + recommendations)
    -> injects into ConvoAI agent context via /update

Based on: https://github.com/thymia-ai/preply-thymia-hackathon
Agora recipe: https://github.com/AgoraIO-Conversational-AI/agent-samples/blob/main/recipes/thymia.md
"""

import logging

from django.conf import settings
from thymia_sentinel import SentinelClient

from services.convoai.schemas import BiomarkerState

logger = logging.getLogger(__name__)

# Pre-built policy for tutoring use case
STUDENT_MONITOR_POLICY = "student_monitor"


async def create_sentinel_client(student_id: str) -> SentinelClient:
    """Create and connect a Sentinel client for real-time voice analysis.

    Uses the `student_monitor` policy which provides:
    - Classification: on_track, check_in, support_needed
    - Recommendations: positive_reinforcement, slow_down, take_break,
      check_understanding, acknowledge_difficulty, switch_activity
    - Biomarker scores: stress, exhaustion, distress, emotions
    """
    api_key = getattr(settings, "THYMIA_API_KEY", "")
    if not api_key:
        logger.warning("THYMIA_API_KEY not set, Sentinel client will not connect")
        raise ValueError("THYMIA_API_KEY is required for Sentinel")

    sentinel = SentinelClient(
        api_key=api_key,
        policy=STUDENT_MONITOR_POLICY,
        user_label=student_id,
    )

    await sentinel.connect()
    logger.info("Thymia Sentinel connected for student=%s", student_id)
    return sentinel


def parse_policy_result(result: dict) -> tuple[BiomarkerState, str]:
    """Parse a Sentinel policy result into BiomarkerState and context text.

    The student_monitor policy returns:
    - classification.status: on_track | check_in | support_needed
    - classification.confidence: 0.0-1.0
    - classification.rationale: why this classification
    - tutor_recommendations: list of {action, priority, script}
    - biomarkers: {helios: {stress, exhaustion, distress, ...}}

    Returns (biomarker_state, context_text_for_prompt).
    """
    # Extract biomarker scores
    biomarkers_raw = result.get("biomarkers", {})
    helios = biomarkers_raw.get("helios", {})

    state = BiomarkerState(
        stress=helios.get("stress", {}).get("value", 0.0),
        exhaustion=helios.get("exhaustion", {}).get("value", 0.0),
        distress=helios.get("distress", {}).get("value", 0.0),
    )

    # Build context text from policy classification + recommendations
    classification = result.get("classification", {})
    status = classification.get("status", "on_track")
    rationale = classification.get("rationale", "")

    recommendations = result.get("tutor_recommendations", [])

    context = build_sentinel_context(state, status, rationale, recommendations)
    return state, context


def build_sentinel_context(
    biomarkers: BiomarkerState,
    status: str,
    rationale: str,
    recommendations: list[dict],
) -> str:
    """Build context block from Sentinel policy results.

    Uses the student_monitor policy's own classifications and recommendations
    instead of hand-coded threshold logic.
    """
    if status == "on_track" and not recommendations:
        return ""  # Student is fine, don't clutter the prompt

    lines = ["## Student Wellness (real-time from Thymia)"]
    lines.append(f"- Status: **{status.replace('_', ' ').upper()}**")

    if rationale:
        lines.append(f"- Assessment: {rationale}")

    if recommendations:
        lines.append("- Recommended actions:")
        for rec in sorted(recommendations, key=lambda r: r.get("priority", 99)):
            action = rec.get("action", "").replace("_", " ")
            script = rec.get("script", "")
            if script:
                lines.append(f"  - {action}: {script}")
            else:
                lines.append(f"  - {action}")

    # Include raw scores for transparency
    if biomarkers.stress > 0.5 or biomarkers.exhaustion > 0.5:
        lines.append(
            f"- Scores: stress={biomarkers.stress:.1f}, "
            f"exhaustion={biomarkers.exhaustion:.1f}, "
            f"distress={biomarkers.distress:.1f}"
        )

    return "\n".join(lines)


# --- Legacy REST API (kept as fallback) ---


def build_thymia_context(biomarkers: BiomarkerState) -> str:
    """Build context block from raw biomarker scores (REST API fallback).

    Prefer build_sentinel_context() with the student_monitor policy
    for richer, more accurate classifications.
    """
    if biomarkers.stress < 0.3 and biomarkers.exhaustion < 0.3:
        return ""

    instructions: list[str] = []

    if biomarkers.stress > 0.7:
        instructions.append(
            f"Student shows high stress ({biomarkers.stress:.1f}). Speak slowly, "
            "use shorter sentences, offer encouragement before corrections."
        )
    elif biomarkers.stress > 0.4:
        instructions.append(f"Moderate stress ({biomarkers.stress:.1f}). Be patient and encouraging.")

    if biomarkers.exhaustion > 0.6:
        instructions.append(
            f"Student shows fatigue ({biomarkers.exhaustion:.1f}). Consider wrapping up or switching to easier topics."
        )

    if not instructions:
        instructions.append("Student seems comfortable. Maintain current pace.")

    return "## Voice Biomarkers (real-time from Thymia)\n" + "\n".join(f"- {i}" for i in instructions)
