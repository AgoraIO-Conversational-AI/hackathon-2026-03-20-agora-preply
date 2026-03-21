# Thymia Voice Biomarkers — Technology Guide

Voice analysis for stress, fatigue, and emotion detection. Stretch goal
that strengthens our Technology Use score. Enables adaptive pacing:
stressed student → avatar slows down and encourages.

---

## 1. Overview

Thymia analyzes speech patterns to extract 30+ health/wellness signals
from as little as 15 seconds of speech. For our project, we use the
**Mental Wellness (Helios)** model for real-time signals.

### Biomarker categories

| Category | Signals | Range |
|----------|---------|-------|
| Wellness (Helios) | distress, stress, exhaustion, sleepPropensity, lowSelfEsteem, mentalStrain | 0.0–1.0 |
| Emotions | angry, disgusted, fearful, happy, neutral, sad, surprised | 0.0–1.0 |

---

## 2. Architecture (with ConvoAI)

```
ConvoAI Agent (Agora cloud)
    │
    │  RTC audio stream
    ▼
go-audio-subscriber (sidecar)
    │
    │  Captures student's audio from RTC channel
    │  Sends to Thymia API
    ▼
Thymia Sentinel API
    │
    │  Returns biomarker scores
    ▼
Custom LLM Server
    │
    │  Injects scores into LLM system prompt
    │  "Student stress: 0.72 — speak slowly, offer encouragement"
    ▼
LLM generates empathetic response
```

### go-audio-subscriber

A Go binary in the `server-custom-llm` repo that:
1. Joins the RTC channel as a subscriber
2. Captures the student's audio stream
3. Sends audio chunks to Thymia's API
4. Receives biomarker scores
5. Passes scores to Custom LLM Server

---

## 3. API Reference

### Authentication

All endpoints use `x-api-key` header:
```
x-api-key: your_thymia_api_key
```

### Run Mental Wellness Model

```
POST /v1/models/mental-wellness
Content-Type: application/json
x-api-key: <api_key>
```

Request:
```json
{
  "user": {
    "userLabel": "student_123",
    "dateOfBirth": "1995-05-15",
    "birthSex": "FEMALE"
  },
  "language": "en-GB"
}
```

Response:
```json
{
  "id": "run_uuid",
  "recordingUploadUrl": "https://..."
}
```

Then PUT the audio file to `recordingUploadUrl`.

**Recording requirements:**
- Min 10 seconds of speech
- Max 3 minutes
- Formats: FLAC, MP3, MP4, OGG, WebM, WAV
- Upload URL valid for 1 hour

### Get Results

```
GET /v1/models/mental-wellness/{model_run_id}
x-api-key: <api_key>
```

Response:
```json
{
  "id": "run_uuid",
  "status": "COMPLETE_OK",
  "results": {
    "sections": [{
      "startSecs": 0,
      "finishSecs": 15.2,
      "transcript": "I went to the store yesterday...",
      "distress": {"value": 0.65},
      "stress": {"value": 0.72},
      "exhaustion": {"value": 0.55},
      "sleepPropensity": {"value": 0.4},
      "lowSelfEsteem": {"value": 0.3},
      "mentalStrain": {"value": 0.68}
    }]
  }
}
```

**Statuses:** `CREATED`, `RUNNING`, `COMPLETE_OK`, `COMPLETE_ERROR`

---

## 4. Integration with ConvoAI

### Enable in agent-samples

Backend `.env`:
```bash
VOICE_THYMIA_API_KEY=your_thymia_key
```

Custom LLM server:
```bash
THYMIA_ENABLED=true
```

Client:
```bash
NEXT_PUBLIC_ENABLE_THYMIA=true
```

The Thymia API key is passed from the backend through `llm_config.params` —
no env var needed on the Custom LLM server itself.

### System prompt injection

```python
def build_thymia_context(biomarkers: dict) -> str:
    """Build context block from Thymia biomarker scores."""
    stress = biomarkers.get("stress", {}).get("value", 0)
    exhaustion = biomarkers.get("exhaustion", {}).get("value", 0)

    instructions = []

    if stress > 0.7:
        instructions.append(
            "Student shows high stress (%.1f). Speak slowly, use shorter sentences, "
            "offer encouragement before corrections." % stress
        )

    if exhaustion > 0.6:
        instructions.append(
            "Student shows fatigue (%.1f). Consider wrapping up the practice "
            "or switching to easier topics." % exhaustion
        )

    if not instructions:
        instructions.append("Student seems comfortable. Maintain current pace.")

    return "## Voice Biomarkers (real-time)\n" + "\n".join(f"- {i}" for i in instructions)
```

---

## 5. Pedagogical Application

| Signal | Threshold | Avatar behavior |
|--------|-----------|----------------|
| Stress > 0.7 | High | Slow down, shorter sentences, more encouragement |
| Exhaustion > 0.6 | Moderate | Suggest break, switch to easier topic |
| Low self-esteem > 0.5 | Moderate | Extra positive reinforcement on correct answers |
| Happy > 0.6 | Engaged | Increase difficulty, introduce new challenges |
| Neutral + low stress | Comfortable | Maintain pace, standard corrections |

---

## 6. Environment Variables

```bash
THYMIA_API_KEY=your_thymia_key    # Server-side only
THYMIA_ENABLED=false               # Enable in Custom LLM server
```

---

## 7. Limitations

- Requires 10+ seconds of speech per analysis
- Real-time integration requires go-audio-subscriber (Go binary)
- API base URL not clearly documented — check your API portal
- This is a stretch goal — build core ConvoAI first

---

## References

- [Thymia Docs](https://docs.thymia.ai)
- [Thymia Recipe](https://github.com/AgoraIO-Conversational-AI/agent-samples/blob/main/recipes/thymia.md)
- [go-audio-subscriber](https://github.com/AgoraIO-Conversational-AI/server-custom-llm/tree/main/go-audio-subscriber)
