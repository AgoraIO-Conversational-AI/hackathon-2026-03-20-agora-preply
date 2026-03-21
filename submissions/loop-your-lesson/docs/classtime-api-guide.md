# Classtime API integration guide

How to create practice exercises from lesson analysis, deliver them to students,
and collect results. Everything here is verified against the live API (March 2026).

---

## 1. Overview

### Two API surfaces, one token

| Surface | Base URL | Auth | Use for |
|---------|----------|------|---------|
| REST API | `https://api.classtime.com/teachers-api/v2/` | Cookie: `service-jwt-0={token}` | Question sets, questions |
| Proto API | `https://www.classtime.com/service/public/{Service}/{Method}` | Header: `Authorization: JWT {token}` | Sessions, results, comments |

REST API is the production website's backend. Proto API wraps gRPC services.
Same teacher JWT works for both - different auth transport.

REST headers also need: `Origin: https://www.classtime.com`, `Referer: https://www.classtime.com/`

Rate limit: 800 req/min per user.

### Tokens

Two token types:

**Teacher/Student JWT** - per-user, 7-day validity, TEACHER or STUDENT audience.
Created via the admin token (see [section 9](#9-auth)). Used for all API
operations: question sets, questions, sessions, results. Passed as cookie
(`service-jwt-0`) for REST or header (`Authorization: JWT`) for Proto.

**SchoolAdmin JWT** (`CLASSTIME_ADMIN_TOKEN`) - server-side only. Used to
provision accounts and mint per-user tokens. See [section 9](#9-auth)).

### Student URLs

Two ways to give students a practice link:

**Solo session** (recommended - cleanest UX):
```
https://www.classtime.com/code/{SOLO_CODE}
```
Student sees a single "Start" button. No login, no nickname prompt, no UI chrome.
Created via `Session/soloSession` API after enabling solo on the question set.

**Regular session** (full control over settings):
```
https://www.classtime.com/student/login/{SESSION_CODE}
```
Student enters a nickname then starts. Teacher controls feedback mode, TTS, etc.
Created via `Session/createSession` API.

### Points system

All point values use centis (1/100th units). `{"pointsCentis": 100}` = 1 point.

### Backend implementation

Python service layer: `apps/classtime_sessions/services/`

| Module | API | Functions |
|--------|-----|-----------|
| `client.py` | Both | `rest_post`, `rest_get`, `proto_call` |
| `schemas.py` | - | Question payloads, DraftJS helpers, session presets |
| `questions.py` | REST | `create_question_set`, `create_question` |
| `sessions.py` | Proto | `create_practice_session`, `get_session_details`, `list_sessions` |
| `results.py` | Proto | `get_answers_summary`, `get_detailed_answers`, `export_session` |

---

## 2. Question types

Five priority types, all verified. The `generate-classtime-questions` skill
picks the type based on the error analysis.

### Kind values

| Type | REST `kind` | When to use |
|------|-------------|-------------|
| GAP | `"gap"` | Verb conjugation, prepositions, articles, collocations, sentence correction |
| SINGLE_CHOICE | `"choice"` | Grammar rule recognition, vocabulary, error identification |
| BOOLEAN | `"bool"` | Quick true/false rule checks |
| SORTER | `"sorter"` | Word order, sentence construction |
| CATEGORIZER | `"categorizer"` | Classification (gender, tense grouping, vocabulary sorting) |
| CLOZE | Proto only | Extended passages with multiple blanks (stretch goal) |

### Error-to-question mapping

This table drives the AI skill's question type selection.

| Error type | Subtype | Question type | Rationale | Example |
|-----------|---------|--------------|-----------|---------|
| Grammar | Verb tense/conjugation | **GAP (blank)** | Active recall of correct form | "Yesterday I ___ (go) to the store" |
| Grammar | Subject-verb agreement | **SINGLE_CHOICE** | Recognize correct pattern | "She doesn't / don't / not like..." |
| Grammar | Word order | **SORTER** | Reconstruct correct sequence | Arrange: "I / went / to / the / store" |
| Grammar | Article/preposition | **GAP (choices)** | Select from dropdown | "I went ___ the store" [to/at/in] |
| Grammar | True/false rule | **BOOLEAN** | Quick rule check | "'I have been there last year' - correct?" |
| Vocabulary | Wrong word used | **SINGLE_CHOICE** | Choose correct synonym/word | "The weather is very ___ today" |
| Vocabulary | Classification | **CATEGORIZER** | Group by semantic category | Sort: food words vs clothing words |
| Grammar | Gender/case | **CATEGORIZER** | Sort by grammatical property | Sort nouns: masculine / feminine / neuter |
| Vocabulary | Collocations | **GAP (choices)** | Correct word pairing | "make / do a mistake" |
| Grammar | Sentence transformation | **GAP (blank)** | Rewrite in different tense | "I go (past simple) -> I ___" |
| Recurring | Pattern in context | **GAP (paragraph)** | Multiple blanks testing same pattern | 4 gaps in one passage |

### GAP (fill-in-the-gap) - the primary question type

The most versatile type for language learning. Supports free-text input (blank)
and dropdowns (choices) in any combination within a single sentence or paragraph.

**Template syntax:** Use `{0}`, `{1}`, `{2}` as gap placeholders. The service
layer converts them to `[UUID]` format for the API.

**Gap types:**
- `blank` - student types free text. Auto-graded, case-insensitive.
  Best for: verb forms, spelling, production tasks.
- `choices` - student picks from dropdown. 3-4 distractors recommended.
  Best for: prepositions, articles, recognition tasks.

**Single blank** (verb conjugation):
```python
GapPayload(
    title="Past tense: irregular verb",
    template_text="Yesterday I {0} to the cinema with my friends.",
    gaps=[Gap(type="blank", solution="went")],
    explanation="went is the irregular past tense of go.",
)
```

**Single choices** (preposition):
```python
GapPayload(
    title="Choose the correct preposition",
    template_text="She is very good {0} playing the piano.",
    gaps=[Gap(type="choices", choices=[
        GapChoice(content="at", is_correct=True),
        GapChoice(content="in", is_correct=False),
        GapChoice(content="on", is_correct=False),
    ])],
)
```

**Mixed blank + choices** (two skills in one sentence):
```python
GapPayload(
    title="Complete with the correct past forms",
    template_text="Last week she {0} a cake and {1} it to her neighbor.",
    gaps=[
        Gap(type="blank", solution="baked"),
        Gap(type="choices", choices=[
            GapChoice(content="gave", is_correct=True),
            GapChoice(content="gived", is_correct=False),
            GapChoice(content="given", is_correct=False),
        ]),
    ],
)
```

**Multiple blanks** (conjugation drill):
```python
GapPayload(
    title="Fill in ALL past tense forms",
    template_text="I {0} up early, {1} breakfast, and {2} to work.",
    gaps=[
        Gap(type="blank", solution="woke"),
        Gap(type="blank", solution="had"),
        Gap(type="blank", solution="drove"),
    ],
)
```

**Paragraph-level** (cloze-style, 4 gaps):
```python
GapPayload(
    title="Complete the paragraph",
    template_text=(
        "When I {0} young, I {1} to play outside every day. "
        "My friends and I {2} ride our bikes to the park "
        "and {3} there until sunset."
    ),
    gaps=[
        Gap(type="choices", choices=[
            GapChoice(content="was", is_correct=True),
            GapChoice(content="were", is_correct=False),
        ]),
        Gap(type="choices", choices=[
            GapChoice(content="used", is_correct=True),
            GapChoice(content="use", is_correct=False),
        ]),
        Gap(type="choices", choices=[
            GapChoice(content="would", is_correct=True),
            GapChoice(content="will", is_correct=False),
        ]),
        Gap(type="blank", solution="stay"),
    ],
)
```

**Sentence correction** (show student's error, pick the fix):
```python
GapPayload(
    title="Correct the error",
    template_text="She {0} not like coffee.",
    gaps=[Gap(type="choices", choices=[
        GapChoice(content="doesn't", is_correct=True),
        GapChoice(content="don't", is_correct=False),
        GapChoice(content="not", is_correct=False),
    ])],
    content=draftjs_blocks([
        ("The student said:", None),
        ("'She don't like coffee'", [(1, 21, "ITALIC"), (5, 5, "BOLD")]),
    ]),
)
```

**REST API payload** (what the service layer sends):
```json
{
  "title": "Complete the sentence",
  "kind": "gap",
  "weight": 1, "isPoll": false, "tags": [], "isSolutionEmpty": false,
  "gapText": "Yesterday I [UUID1] to the store and [UUID2] some milk.",
  "gaps": [
    {"type": "blank", "gapLocalId": "UUID1", "solution": "went", "choices": []},
    {"type": "choices", "gapLocalId": "UUID2", "solution": "",
     "choices": [
       {"content": "bought", "isCorrect": true, "parentGapLocalId": "UUID2", "index": 0},
       {"content": "buyed", "isCorrect": false, "parentGapLocalId": "UUID2", "index": 1}
     ]}
  ],
  "categories": [], "items": [], "clozes": [], "choices": [],
  "questionSet": "UUID"
}
```

Key details:
- `gapText` uses `[UUID]` placeholders (not `___UUID___`)
- `gapLocalId` must be UUID format
- `blank` gaps: `solution` contains the correct answer
- `choices` gaps: `isCorrect` marks the right option, `parentGapLocalId` links back
- Points: 100 centis per gap (auto-calculated)

### SINGLE_CHOICE

Student picks one correct answer from options.

```python
SingleChoicePayload(
    title="Which sentence is correct?",
    choices=[
        SingleChoiceOption(text="She don't like coffee", is_correct=False),
        SingleChoiceOption(text="She doesn't like coffee", is_correct=True),
        SingleChoiceOption(text="She not like coffee", is_correct=False),
    ],
    explanation="Third person singular: doesn't (does + not).",
)
```

Distractor tips: include the student's actual error from the transcript,
common L1 transfer errors, and other forms of the same word.

### BOOLEAN

True/false statement. Simplest type.

```python
BooleanPayload(
    title="'I have been to Paris last year' is correct",
    is_correct=False,
    explanation="Use simple past with 'last year': 'I went to Paris last year.'",
)
```

### SORTER

Arrange items in correct order. Classtime shuffles for display.

```python
SorterPayload(
    title="Arrange to form a correct sentence",
    items=["I", "went", "to the store", "yesterday"],
    explanation="Subject-Verb-Object-Time word order.",
)
```

Items are listed in CORRECT order. Classtime handles the shuffling.

### CATEGORIZER

Classify items into categories.

```python
CategorizerPayload(
    title="Sort verbs by auxiliary (haben/sein)",
    categories=["haben", "sein"],
    items=[
        CategorizerItem(text="gemacht", category_index=0),
        CategorizerItem(text="gefahren", category_index=1),
        CategorizerItem(text="gegessen", category_index=0),
        CategorizerItem(text="gelaufen", category_index=1),
    ],
    explanation="Movement verbs use sein; most others use haben.",
)
```

---

## 3. Rich text formatting (DraftJS)

Classtime uses DraftJS for rich text. Formatting is done via `inlineStyleRanges`
on each block.

### Available styles

`BOLD`, `ITALIC`, `UNDERLINE` - combinable on the same range.

```json
"inlineStyleRanges": [
  {"offset": 0, "length": 4, "style": "BOLD"},
  {"offset": 0, "length": 4, "style": "ITALIC"}
]
```

### Where it applies

- `content` - question description, shown above options
- `explanation` - shown after answering
- `choices[].content` - the option text itself (SINGLE_CHOICE, SORTER)
- `categories[].content` and `items[].content` (CATEGORIZER)

### Python helpers

```python
from apps.classtime_sessions.services.schemas import (
    draftjs_struct,   # plain text
    draftjs_rich,     # text with inline styles
    draftjs_bold,     # entire text bold
    draftjs_italic,   # entire text italic
    draftjs_blocks,   # multi-paragraph
)

# Bold a keyword
draftjs_rich("went is the past tense of go.", [(0, 4, "BOLD")])

# Multi-paragraph with formatting
draftjs_blocks([
    ("Read the sentence:", None),
    ("'I goed to the store'", [(1, 19, "ITALIC")]),
    ("Is this correct?", [(8, 7, "BOLD")]),
])
```

### Best practices for language learning

- Bold the **correct form** in explanations
- Italic the **student's original error** from the transcript
- Bold+italic for **grammar terms** (e.g., *irregular verb*)
- Use `content` field for context above the question
- Multi-paragraph explanations: rule, then correct vs incorrect examples

---

## 4. Question set management

### Create question set

```python
from apps.classtime_sessions.services.questions import create_question_set

qs_id = create_question_set("Practice: Past Tense - Alex Chen")
```

REST API:
```
POST https://api.classtime.com/teachers-api/v2/question-sets/
{"title": "Practice: Past Tense - Alex Chen", "parent": "FOLDER_UUID"}
```

`parent` is optional. If set, use a folder UUID (not the string "root").

### Add questions

```python
from apps.classtime_sessions.services.questions import create_question

q_id = create_question(qs_id, GapPayload(...))
```

### List and get

```python
from apps.classtime_sessions.services.questions import list_question_sets, get_question_set

all_sets = list_question_sets()
qs_detail = get_question_set(qs_id)  # includes question list
```

---

## 5. Session lifecycle

Two session types:

### Solo session (recommended - cleanest student UX)

Student sees a clean "Start" button, no login or nickname required.
Best for 1-on-1 tutoring where we control the full experience.

```python
from apps.classtime_sessions.services.sessions import create_solo_practice

url = create_solo_practice(question_set_id)
# -> https://www.classtime.com/code/6TY8SEH5
```

**How it works:**

1. PATCH the question set to enable solo: `anonymousSoloSessionRef = "create"`
2. Call `Session/soloSession` API with the QS's `secretLink`
3. API returns `{"redirectUrl": "https://www.classtime.com/code/CODE"}`
4. Each call creates a NEW session code (not idempotent)

**Embed in iframe:**
```html
<iframe src="https://www.classtime.com/code/6TY8SEH5" style="width:100%;height:700px;border:none" />
```

**Settings:** Solo sessions are created with Classtime defaults (reflection ON,
penalty grading). Call `Session/setSessionSettings` after creation to apply
custom feedback, reflection, and grading settings. Must include `activeQuestions`
from `getSessionDetails` or questions will be deactivated.

`create_practice_for_lesson()` handles this automatically - it creates the solo
session, fetches active questions, then applies our settings.

**Step by step (low-level):**
```python
from apps.classtime_sessions.services.sessions import (
    enable_solo, create_solo_session, set_session_settings, get_session_details,
)
from apps.classtime_sessions.services.schemas import build_session_settings

# One-time: enable solo on the QS
secret_link = enable_solo(question_set_id)

# Each time student needs a fresh session:
url = create_solo_session(secret_link)
code = url.split("/")[-1]

# Apply our settings (required - solo defaults are not what we want)
settings = build_session_settings(title, feedback_mode="practice")
details = get_session_details(code)
active_qs = details["session"]["settings"]["activeQuestions"]
set_session_settings(code, settings, active_questions=active_qs)
```

### Regular session (full control)

Teacher controls feedback mode, TTS, timer, etc. Student enters a nickname.

```python
from apps.classtime_sessions.services.sessions import (
    create_practice_session, get_student_url,
)

code = create_practice_session(qs_id, "Practice: Past Tense (Alex Chen)")
url = get_student_url(code)
# -> https://www.classtime.com/student/login/ABC123
```

### Feedback presets

Three modes, applied to both solo and regular sessions. All share: no timer,
unlimited retries, no reflection, partial credit without penalty.

| Mode | Right/wrong? | Solution? | Use case |
|------|-------------|-----------|----------|
| `practice` (default) | After each answer | Hidden | Daily drills, error reinforcement |
| `after_submit` | After all answers | Hidden | Self-assessment, comprehensive review |
| `reveal_answers` | After each answer | Shown | Review mode, after student has practiced |

```python
# Default: practice mode (solutions hidden)
code = create_practice_session(qs_id, title)

# Explicit mode
code = create_practice_session(qs_id, title, feedback_mode="after_submit")

# With text-to-speech (language learning)
code = create_practice_session(qs_id, title, tts_language="en-US")

# Subset of questions
code = create_practice_session(qs_id, title, selected_question_ids=["q1", "q3"])
```

### Session settings (Proto API)

```json
{
  "playlist": [{"questionSetId": "UUID", "selectedQuestionIds": []}],
  "settings": {
    "title": "Practice: Past Tense (Alex Chen)",
    "isActive": true,
    "isConfigured": true,
    "evaluationMode": "PARTIAL_POINTS_WITHOUT_PENALTY",
    "shuffleChoices": true,
    "shuffleQuestions": false,
    "oneAttemptOnly": false,
    "hasReflection": false,
    "forceReflection": false,
    "resultsSharingSettings": {
      "questionValidation": "ON",
      "solutionWithExplanation": "OFF",
      "answerComment": "OFF",
      "totalScore": "ON",
      "sessionComment": "OFF",
      "pdfExport": "OFF"
    }
  }
}
```

Response: `{"session": {"code": "ABC123", "totalPoints": {"pointsCentis": 700}}}`

### Text-to-speech

```json
"defaultTextToSpeechConfig": {
  "isEnabled": true,
  "voice": "Female",
  "language": "en-US",
  "speed": 0.9
}
```

### Session state

```python
from apps.classtime_sessions.services.sessions import end_session, archive_session

end_session(code)       # students can no longer answer
archive_session(code)   # read-only
```

States: RUNNING, PAUSED, ENDED, ARCHIVED, DELETED, RESTORED.

### Other session operations

```python
from apps.classtime_sessions.services.sessions import (
    get_session_details,  # full session with questions map
    list_sessions,        # all teacher's sessions
    check_session_health, # validate session is ready
)
```

---

## 6. Results and feedback

### Answer summary

```python
from apps.classtime_sessions.services.results import get_answers_summary

results = get_answers_summary("ABC123")
for r in results:
    print(f"{r.correctness} {r.points_centis}/{r.max_points_centis}")
    if r.gap_results:
        print(f"  per-gap: {r.gap_results}")
```

Proto response shape:
```json
{
  "answers": [{
    "id": "answer_id",
    "participantId": "p_id",
    "questionId": "q_id",
    "evaluation": {
      "gradingPoints": {"pointsCentis": 100},
      "correctness": "CORRECT",
      "evaluationGap": [{"isCorrect": true}, {"isCorrect": false}]
    },
    "createdAt": "2026-03-17T08:34:04Z"
  }]
}
```

Correctness values: `CORRECT`, `PARTIALLY_CORRECT`, `WRONG`.

### Detailed answers

What the student actually submitted:

```python
from apps.classtime_sessions.services.results import get_detailed_answers

answers = get_detailed_answers("ABC123", question_id)
```

Response shape per question type:
- `answerBoolean`: `{"isTrue": true}`
- `answerSingleChoice`: `{"selectedChoice": 1}`
- `answerGap`: `{"gaps": [{"content": "went"}, {"choiceIndex": 0}]}`
- `answerSorter`: `{"sortedChoices": [0, 1, 2, 3]}`
- `answerCategorizer`: `{"selectedCategories": [{"categoryIndices": [0]}, ...]}`

### AI-suggested comments

```python
from apps.classtime_sessions.services.results import suggest_comment

comment_slate = suggest_comment("ABC123", answer_id)
# Returns Slate JSON or None (BOOLEAN not supported)
```

### Saving comments

Content must be Slate JSON format. Plain text is auto-wrapped.

```python
from apps.classtime_sessions.services.results import save_comment

save_comment("ABC123", participant_id, question_id, answer_id,
             "Great improvement on past tense!")
```

Both `questionRef` and `answerRef` are required.

Slate JSON format: `'[{"children":[{"text":"..."}],"type":"paragraph"}]'`

### Export

```python
from apps.classtime_sessions.services.results import export_session

url = export_session("ABC123")  # returns XLSX download URL
```

Report types: `INSIGHTS_XLSX`, `SESSION_INSIGHTS` (PDF), `PARTICIPANT_INSIGHTS` (PDF).

---

## 7. Backend service layer

### Architecture

```
REST API (questions)           Proto API (sessions/results)
  api.classtime.com              www.classtime.com/service/public/
  Cookie auth                    JWT header auth
       │                              │
       ▼                              ▼
  ClasstimeRestClient            ClasstimeProtoClient
  (rest_post, rest_get)          (proto_call)
       │                              │
       ▼                              ▼
  Pydantic schemas ──── question payloads, session presets, result parsing
       │                              │
       ▼                              ▼
  questions.py                   sessions.py, results.py
       │                              │
       ▼                              ▼
  Django models: ClasstimeSession, SessionParticipant
```

### Django models

```python
class ClasstimeSession(TimeStampedModel):
    lesson = ForeignKey("lessons.Lesson", on_delete=CASCADE)
    teacher = ForeignKey("accounts.Teacher", on_delete=CASCADE)
    session_code = CharField(max_length=50, unique=True)
    question_set_id = CharField(max_length=100, blank=True)
    session_type = CharField(choices=SessionType.choices, default="practice")
    status = CharField(max_length=50, default="created")
    results_data = JSONField(default=dict, blank=True)

class SessionParticipant(TimeStampedModel):
    session = ForeignKey(ClasstimeSession, on_delete=CASCADE)
    student = ForeignKey("accounts.Student", on_delete=CASCADE)
    joined_at = DateTimeField(null=True)
    completed_at = DateTimeField(null=True)
    results_data = JSONField(default=dict, blank=True)
```

### Pydantic question schemas

All payloads accept plain `str` or pre-built DraftJS `dict` for text fields.

```python
from apps.classtime_sessions.services.schemas import (
    BooleanPayload,
    SingleChoicePayload, SingleChoiceOption,
    GapPayload, Gap, GapChoice,
    SorterPayload,
    CategorizerPayload, CategorizerItem,
)
```

Each has `.to_rest_body(question_set_id)` that builds the full REST API payload.

---

## 8. Happy path

A teacher joins Preply, teaches a lesson, student gets practice, results flow
back. Here's every API call that happens.

### 1. Teacher onboarded (first lesson on Preply)

```python
from apps.classtime_sessions.services.auth import ensure_teacher_token

teacher = Teacher.objects.get(preply_user_id="preply-456")
token = ensure_teacher_token(teacher)
```

Under the hood (all automatic, idempotent):
```
→ Account/getOrCreateAccount {role: TEACHER, subject: "preply-teacher-456",
    email: "maria@example.com", user_profile: {first_name: "Maria", last_name: "Garcia"}}
← {accountId: "ct-maria-123"}

→ Account/associateMember {organization_id: "b47a32f4-...", account_id: "ct-maria-123"}
← {}

→ Account/createToken {classtime_id: "ct-maria-123"}
← {token: "eyJ...", validUntil: "2026-03-24T20:36:19Z"}
```

Teacher now has a 7-day JWT cached on the model. Next call to
`ensure_teacher_token` returns the cached token until it's within 1h of expiry.

### 2. Lesson analyzed, questions generated

AI skills analyze the transcript and produce question specs:

```python
skill_output = {
    "session_title": "Practice: Past Tense - Alex Chen (Mar 18)",
    "feedback_mode": "practice",
    "questions": [
        {
            "payload_type": "gap",
            "source_ref": {"error_type": "grammar", "subtype": "verb_tense"},
            "payload": {
                "title": "Past tense: irregular verb",
                "template_text": "Yesterday I {0} to the store.",
                "gaps": [{"type": "blank", "solution": "went"}],
                "explanation": "went is the irregular past tense of go.",
            },
        },
        {
            "payload_type": "choice",
            "source_ref": {"error_type": "grammar", "subtype": "subject_verb"},
            "payload": {
                "title": "Subject-verb agreement",
                "choices": [
                    {"text": "She don't like coffee", "is_correct": False},
                    {"text": "She doesn't like coffee", "is_correct": True},
                ],
                "explanation": "Third person singular: doesn't (does + not).",
            },
        },
    ],
}
```

### 3. Practice session created (on teacher's behalf)

```python
from apps.classtime_sessions.services.sessions import create_practice_for_lesson

session = create_practice_for_lesson(teacher, student, skill_output, lesson=lesson)
```

Under the hood (using Maria's teacher token):
```
→ REST POST question-sets/ {title: "Practice: Past Tense - Alex Chen (Mar 18)"}
  Cookie: service-jwt-0={maria_token}
← {id: "qs-abc"}

→ REST POST questions/ {kind: "gap", questionSet: "qs-abc", ...}
← {id: "q-1"}

→ REST POST questions/ {kind: "choice", questionSet: "qs-abc", ...}
← {id: "q-2"}

→ REST PATCH question-sets/qs-abc/ {anonymousSoloSessionRef: "create"}
← {secretLink: "secret-xyz"}

→ Proto Session/soloSession {secretLink: "secret-xyz",
    ownerAccountId: "ct-maria-123", isAnonymous: true}
← {redirectUrl: "https://www.classtime.com/code/4RMQSBCH"}
```

Result: `ClasstimeSession` saved in DB with code `4RMQSBCH`, questions mapped
to source errors.

### 4. Student gets the link

```python
session.student_url  # "https://www.classtime.com/code/4RMQSBCH"
```

Student opens the link. Classtime renders the questions, handles grading, shows
immediate feedback per the session settings.

For named student identity (progress tracking across sessions):
```python
from apps.classtime_sessions.services.auth import ensure_student_token

student_token = ensure_student_token(student)
# Set service-jwt-0 cookie via Chrome extension, then redirect to session URL
```

### 5. Results flow back

After the student completes practice:

```python
from apps.classtime_sessions.services.results import sync_session_results

results = sync_session_results(session)
```

```
→ Proto Session/getAnswersSummary {sessionCode: "4RMQSBCH"}
← {answers: [{questionId: "q-1", evaluation: {correctness: "CORRECT", ...}},
              {questionId: "q-2", evaluation: {correctness: "WRONG", ...}}]}

→ Proto Session/getSessionDetails {code: "4RMQSBCH"}
← {questions: {"q-1": {...}, "q-2": {...}}}
```

Result: `SessionParticipant.results_data` updated with per-question scores,
`ClasstimeSession.status` set to "completed".

```python
results["score"]       # 1
results["total"]       # 2
results["percentage"]  # 50
results["questions"]   # [{question_id: "q-1", correct: True, source_ref: {...}}, ...]
```

### 6. Teacher sees the briefing

The daily briefing skill reads skill outputs + practice results:

> "Alex scored 1/2 on past tense practice. Got the irregular verb right but
> still struggles with subject-verb agreement (3rd person singular). Suggest
> revisiting this pattern with more examples."

---

### Pipeline view

```
Lesson transcript
  ↓
Analysis skills (parallel): errors, themes, level
  ↓
generate-classtime-questions skill → {questions, session_title}
  ↓
create_practice_for_lesson(teacher, student, skill_output)
  → ensure_teacher_token → create QS → create questions → solo session → DB
  ↓
Student completes practice on Classtime
  ↓
sync_session_results(session) → scores in DB
  ↓
prepare-daily-briefing → teacher AI chat
```

### Skill output format

The `generate-classtime-questions` skill produces:

```json
{
  "questions": [
    {
      "source_ref": {
        "error_index": 0,
        "error_type": "grammar",
        "subtype": "verb_tense",
        "original": "I go yesterday",
        "corrected": "I went yesterday"
      },
      "payload_type": "gap",
      "payload": {
        "title": "Complete with the correct past tense",
        "template_text": "Yesterday I {0} to the store.",
        "gaps": [{"type": "blank", "solution": "went"}],
        "explanation": "went is the irregular past tense of go."
      }
    }
  ],
  "session_title": "Practice: Past Tense - Alex Chen (Mar 20)",
  "feedback_mode": "practice"
}
```

The `source_ref` is NOT sent to Classtime. It's stored in
`ClasstimeSession.questions_data` to map results back to the original errors.

---

## 9. Auth

Account provisioning uses the SchoolAdmin token to create per-user Classtime
accounts and mint short-lived JWTs. All admin operations use **snake_case**
field names.

### Flow (verified)

**Step 1: Create account** (idempotent - same `subject` returns same account)
```
POST Account/getOrCreateAccount
Authorization: JWT {CLASSTIME_ADMIN_TOKEN}

{
  "role": "TEACHER",                                    // or "STUDENT"
  "user_profile": {"first_name": "X", "last_name": "Y"},
  "subject": "preply-teacher-123",                      // unique external ID
  "email": "teacher@example.com"                        // links existing accounts
}
→ {"accountId": "4AIeB1bvemBJHzauulGx-w"}
```

Note: the method is `getOrCreateAccount`, NOT `getOrCreateExternalAccount`
(which requires a separate migration flag).

**Step 2: Associate with org** (teachers only - students skip this)
```
POST Account/associateMember
Authorization: JWT {CLASSTIME_ADMIN_TOKEN}

{
  "organization_id": "b47a32f4-8656-4c8f-9c5c-92e8a69c1d37",
  "account_id": "4AIeB1bvemBJHzauulGx-w"
}
→ {}
```

**Step 3: Mint per-user token** (7-day validity)
```
POST Account/createToken
Authorization: JWT {CLASSTIME_ADMIN_TOKEN}

{"classtime_id": "4AIeB1bvemBJHzauulGx-w"}
→ {"token": "eyJ...", "validUntil": "2026-03-24T20:36:19Z"}
```

### Key details

- **Idempotent**: same `subject` always returns the same `accountId`
- **Existing emails**: if the email belongs to an existing Classtime account,
  it links to that account (returns the existing account's ID)
- **Token validity**: 7 days. Audience is `TEACHER/` or `STUDENT/` based on role
- **Teacher tokens**: can create question sets, sessions, fetch results (both
  REST and Proto APIs)
- **Student tokens**: student-scoped operations only
- **Students don't need org association** - only teachers need `associateMember`

### Backend implementation

```python
from apps.classtime_sessions.services.auth import (
    ensure_teacher_token,   # provision + mint + cache
    ensure_student_token,
    provision_teacher,      # lower-level: create account + associate
    provision_student,
    create_user_token,      # mint a new token
)
```

`ensure_teacher_token(teacher)` handles the full lifecycle: provisions the
account if needed, mints a token if expired (1h buffer), caches on the model.

### Settings

```
CLASSTIME_ADMIN_TOKEN   # SchoolAdmin JWT (from Classtime team)
CLASSTIME_ORG_ID        # Preply organization UUID
```

### Gotchas

Methods that do NOT work with the SchoolAdmin token:

| Method | Error | Use instead |
|--------|-------|-------------|
| `Account/getOrCreateExternalAccount` | "only available with organizations enabled" (requires school migration flag) | `Account/getOrCreateAccount` |
| `Account/createAccount` | "Role mismatch! Required machine" | `Account/getOrCreateAccount` |
| `Account/getOrCreateAccounts` | "Role mismatch! Required machine" | `Account/getOrCreateAccount` |
| `School/associateTeacher` | "account's organizations []" | `Account/associateMember` |
| `Account/getAccountIdByEmail` | "Required machine, classtime_admin" | Use `getOrCreateAccount` with the email |

The admin token **cannot** do teacher operations (create question sets, sessions,
list sessions). Use per-teacher tokens minted via `createToken` for those.

The admin token **can** read:
- `Account/getMyAccountInfo` - verify token, check role/orgs
- `Account/getOrganizations` - list orgs for an account
- `Account/getOrganization` - org details and member list
- `Account/getAccountProfiles` - lookup profiles by account ID

### Constants

```
Admin account ID:  v6b9rJEQL2IqrTXkJ_YyvQ
Organization ID:   b47a32f4-8656-4c8f-9c5c-92e8a69c1d37
School ID (JWT):   3WoUh63lsg3UaOrCfQYeOt
```

---

## Appendix: Proto reference

### Question kind enum

```
BOOLEAN = 0, CATEGORIZER = 1, CATEGORIZER_MULTIPLE = 2, CLOZE = 3,
GAP = 4, HOTSPOT = 5, MULTIPLE_CHOICE = 6, SINGLE_CHOICE = 7,
SORTER = 8, TEXT = 9, ESSAY = 10
```

### Evaluation modes

| Mode | Behavior |
|------|----------|
| `FULL_OR_NO_POINTS` | All correct or 0 points |
| `PARTIAL_POINTS_WITH_PENALTY` | Partial credit minus wrong answers |
| `PARTIAL_POINTS_WITHOUT_PENALTY` | Partial credit, no deduction (recommended) |

### Results sharing settings

| Setting | Values | Effect |
|---------|--------|--------|
| `questionValidation` | ON/OFF/PER_QUESTION | Student sees correct/incorrect |
| `solutionWithExplanation` | ON/OFF/PER_QUESTION | Shows correct answer + explanation |
| `answerComment` | ON/OFF | Teacher comments visible |
| `totalScore` | ON/OFF | Student sees total score |
| `sessionComment` | ON/OFF | Overall comment visible |
| `pdfExport` | ON/OFF | Student can export PDF |

### Session states

RUNNING, PAUSED, ENDED, ARCHIVED, DELETED, RESTORED

### Proto API methods

All methods are POST to `https://www.classtime.com/service/public/{Service}/{Method}`.

| Service | Method | Purpose |
|---------|--------|---------|
| Library | createQuestionSet | Create QS (omit folder_id) |
| Library | createQuestion | Create question (camelCase, stringified DraftJS) |
| Library | getQuestionSet | Get QS info |
| Session | createSession | Create session from QS playlist |
| Session | getSessions | List all teacher's sessions |
| Session | getSessionDetails | Full session with questions map |
| Session | checkSessionHealth | Validate session ready |
| Session | changeSessionState | Change state (ENDED, ARCHIVED, etc.) |
| Session | getAnswersSummary | All answers with evaluations |
| Session | getAnswers | Detailed answer per question |
| Session | suggestComment | AI feedback (not BOOLEAN) |
| Session | createOrUpdateComments | Save feedback (Slate JSON) |
| Session | exportSession | XLSX/PDF download URL |
| Session | getPusherConfig | Real-time update credentials |
| Session | getRealtimeAuthentication | Auth signature for Pusher channel |

---

## 10. Real-time events (Pusher websockets)

Live answer events via Pusher. Verified working March 2026.

### Setup

```python
# 1. Get Pusher credentials
config = proto_call("Session", "getPusherConfig", {"sessionCode": "ABC123"})
# → {"cluster": "eu", "apiKey": "92a77cf8...", "pusherDisableWebsockets": false}

# 2. Connect to Pusher with api_key and cluster
# 3. Subscribe to teacher channel (requires auth)
channel = "private-teacher-session-{SESSION_CODE}"

# 4. Auth: call getRealtimeAuthentication with socket_id from Pusher
auth = proto_call("Session", "getRealtimeAuthentication", {
    "cluster": "EU",
    "channelName": "private-teacher-session-ABC123",
    "socketId": "260824.2588247",
})
# → {"auth": "92a77cf8...:signature", "channelData": ""}
```

### Channels

| Channel format | Auth | Events |
|----------------|------|--------|
| `private-teacher-session-{CODE}` | Required (teacher token) | `binary-answer-added`, `binary-participant-added` |
| `presence-session-{CODE}` | Required (presence auth) | `pusher_internal:member_added`, `member_removed` |
| `private-session-{CODE}` | Required | No events observed (do not use) |

### Events

**`binary-answer-added`** - fires when student submits an answer.
Data is base64-encoded protobuf (`PusherAnswerAdded` message).

Decoded structure:
```
PusherAnswerAdded (proto field numbers):
  field 4: AnswerSummary
    field 1: answer_id (string)     "raGB-SWUO0AvSNlzWNtaqg:Bg:Ag"
    field 2: participant_id (string) "raGB-SWUO0AvSNlzWNtaqg:Bg"
    field 4: question_id (string)    "raGB-SWUO0AvSNlzWNtaqg:Ag"
    field 3: content (string)        "" (empty for non-text questions)
    field 11: Evaluation
      field 9: correctness (enum)    0=CORRECT, 1=PARTIALLY_CORRECT, 2=WRONG
      field 2: grading_points
        field 1: points_centis (int) 100 = 1.0 points
      field 5: gap_evaluations[]
        field 2: is_correct (bool)
    field 13: created_at (Timestamp)
      field 1: seconds (int64)
      field 2: nanos (int32)
  field 5: created_at (Timestamp)    event timestamp
```

**`binary-participant-added`** - fires when student joins the session.
Data is base64-encoded protobuf (`PusherSessionParticipantAdded` message).

### Decoding binary events (Python)

```python
import base64

def decode_answer_event(b64_data: str) -> dict:
    """Decode binary-answer-added Pusher event to structured dict."""
    raw = base64.b64decode(b64_data)
    outer = _decode_fields(raw)

    # Field 4 = AnswerSummary
    summary = _decode_fields(outer[4][1])

    result = {
        "answer_id": summary[1][1].decode() if 1 in summary else "",
        "participant_id": summary[2][1].decode() if 2 in summary else "",
        "question_id": summary[4][1].decode() if 4 in summary else "",
        "content": summary[3][1].decode() if 3 in summary else "",
    }

    # Field 11 = Evaluation
    if 11 in summary:
        ev = _decode_fields(summary[11][1])
        correctness_map = {0: "CORRECT", 1: "PARTIALLY_CORRECT", 2: "WRONG"}
        result["correctness"] = correctness_map.get(
            ev.get(9, (None, 0))[1], "UNKNOWN"
        )
        if 2 in ev:
            gp = _decode_fields(ev[2][1])
            result["points_centis"] = gp.get(1, (None, 0))[1]

    return result


def _decode_fields(data: bytes) -> dict:
    """Minimal protobuf wire-format decoder."""
    fields = {}
    pos = 0
    while pos < len(data):
        tag, pos = _read_varint(data, pos)
        field_num = tag >> 3
        wire_type = tag & 0x7
        if wire_type == 0:
            val, pos = _read_varint(data, pos)
            fields[field_num] = ("varint", val)
        elif wire_type == 2:
            length, pos = _read_varint(data, pos)
            fields[field_num] = ("bytes", data[pos : pos + length])
            pos += length
        elif wire_type == 5:
            fields[field_num] = ("32bit", int.from_bytes(data[pos : pos + 4], "little"))
            pos += 4
        elif wire_type == 1:
            fields[field_num] = ("64bit", int.from_bytes(data[pos : pos + 8], "little"))
            pos += 8
    return fields


def _read_varint(data: bytes, pos: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while pos < len(data):
        byte = data[pos]
        result |= (byte & 0x7f) << shift
        pos += 1
        if not (byte & 0x80):
            break
        shift += 7
    return result, pos
```

### Enrichment: from event to AI context

The Pusher event only contains question_id + correctness. To give the AI
useful context, enrich with two API calls (~500ms total):

1. `getSessionDetails(code)` → question title, type, derivedFromQuestionRef
2. `getAnswers(code, question_id)` → what the student actually typed/selected

**Note:** `getSessionDetails` returns empty `kind` for BOOLEAN questions.
Infer the type from the answer shape (`answerBoolean` → `true_false`,
`answerGap` → `gap`, etc.).

```
Pusher event: binary-answer-added
    ↓ decode protobuf
{question_id, correctness, points_centis}
    ↓ getSessionDetails
{title: "Fill in the past tense", kind: "GAP", derivedFrom: "7fdd1d82-..."}
    ↓ getAnswers
{answerGap: {gaps: [{content: "went"}]}}
    ↓ map derivedFrom → questions_data → source_ref
{error_type: "grammar", subtype: "verb_tense"}
    ↓ format for AI
"[Quiz Update] Q1/2 'Fill in the past tense' (gap): CORRECT.
 Student answered: 'went'. Tests error: grammar/verb_tense."
```

### Integration with ConvoAI

The real-time answer flow for the ConvoAI practice agent:

```
Student answers Classtime question
    ↓
Pusher: binary-answer-added on private-teacher-session-{CODE}
    ↓
Decode protobuf → {question_id, correctness, points}
    ↓
Enrich: getSessionDetails + getAnswers → title, type, student answer
    ↓
Map question_id → derivedFromQuestionRef → questions_data → source_ref
    ↓
Inject into ConvoAI agent context:
    "[Quiz Update] Q1/2 'Fill in the past tense' (gap): CORRECT.
     Student answered: 'went'. Tests error: grammar/verb_tense."
    ↓
Agent reflects in conversation:
    "Nice work on that past tense! You got 'went' right.
     Let's try using it in conversation - tell me what
     you did last weekend."
```

The question_id from the event maps via `derivedFromQuestionRef` to the
library question_id stored in `ClasstimeSession.questions_data`, which
contains `source_ref` linking back to the original lesson error. This lets
the agent know WHICH error the student just practiced and adapt accordingly.

### Test script

`backend/scripts/test_pusher.py` - creates a session, connects to Pusher,
and logs events with protobuf decoding. Run with:

```bash
cd backend
uv run python -u scripts/test_pusher.py --create-session
uv run python -u scripts/test_pusher.py --session-code ABC123
```

---

### Proto definitions

Source of truth for field names: `classtime-api/classtime/service/proto/`

Key files:
- `question_entities.proto` - Question, QuestionInfo, solutions
- `session_entities.proto` - Session, SessionSettings, SessionParticipant
- `session_messages.proto` - Create/get/answer messages
- `library_messages.proto` - Question set and question creation
- `common_messages.proto` - GradingPoint, PlaylistEntry
