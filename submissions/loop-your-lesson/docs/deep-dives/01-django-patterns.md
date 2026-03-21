# Django patterns

> Inspired by [PostHog's production codebase](https://github.com/PostHog/posthog).
> Source: [`posthog/models/utils.py`](https://github.com/PostHog/posthog/blob/master/posthog/models/utils.py), [`ee/models/assistant.py`](https://github.com/PostHog/posthog/blob/master/ee/models/assistant.py), [`products/llm_analytics/backend/models/`](https://github.com/PostHog/posthog/blob/master/products/llm_analytics/backend/models/), [`products/visual_review/backend/logic.py`](https://github.com/PostHog/posthog/blob/master/products/visual_review/backend/logic.py)

## At a glance

**What this covers**: Django model conventions, service layer organization, custom exceptions, and Pydantic validation patterns borrowed from PostHog's production codebase.

**Why it matters**: Consistent patterns make the codebase predictable. A new contributor knows where to put a model, how to write a service function, and what exceptions to raise.

**Key terms**:

| Term | Meaning |
|------|---------|
| TimeStampedModel | Base model with auto `created` and `modified` timestamps |
| TextChoices | Django enum pattern for status fields (e.g. `SubjectType`, `SkillExecutionStatus`) |
| JSONField | Flexible storage for subject_config, output_data, transcript_data |
| Service layer | Business logic in `backend/services/` functions, not in views or models |
| Domain exceptions | Custom errors like `LessonNotFoundError` instead of generic `ValueError` |
| Pydantic validation | Strict input validation at service boundaries (`extra="forbid"`) |

**Prerequisites**: None (standalone reference)

---

## What PostHog does

### UUID7 primary keys via base model

Every new model inherits from `UUIDModel`, which replaces Django's auto-increment integer PK with a UUID7. UUID7 is time-sortable (encodes millisecond timestamp), so it works as a natural creation-order index without leaking business volume info the way sequential integers do.

```python
# posthog/models/utils.py

def uuid7(unix_ms_time=None, random=None) -> uuid.UUID:
    unix_ms_time_int = time_ns() // (10**6) if unix_ms_time is None else unix_ms_time
    rand_bytes = int.from_bytes(secrets.token_bytes(10), byteorder="little")
    rand_a = rand_bytes & 0x0FFF
    rand_b = (rand_bytes >> 12) & 0x03FFFFFFFFFFFFFFF
    ver = 7
    var = 0b10
    uuid_int = (unix_ms_time_int & 0x0FFFFFFFFFFFF) << 80
    uuid_int |= ver << 76
    uuid_int |= rand_a << 64
    uuid_int |= var << 62
    uuid_int |= rand_b
    return uuid.UUID(int=uuid_int)


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    class Meta:
        abstract = True
```

### Mixin composition for metadata fields

Rather than one monolithic base model, PostHog uses composable abstract mixins. Models pick exactly the fields they need:

```python
# posthog/models/utils.py

class CreatedMetaFields(models.Model):
    created_by = models.ForeignKey("posthog.User", on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        abstract = True

class UpdatedMetaFields(models.Model):
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    class Meta:
        abstract = True

class DeletedMetaFields(models.Model):
    deleted = models.BooleanField(null=True, blank=True, default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        abstract = True
```

A model composes what it needs:

```python
# products/llm_analytics/backend/models/datasets.py

class Dataset(UUIDModel, CreatedMetaFields, UpdatedMetaFields, DeletedMetaFields):
    name = models.CharField(max_length=400)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    description = models.TextField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
```

### TextChoices for all enums

No raw strings anywhere. Every status/type field uses `models.TextChoices`:

```python
# ee/models/assistant.py

class Conversation(UUIDTModel):
    class Status(models.TextChoices):
        IDLE = "idle", "Idle"
        IN_PROGRESS = "in_progress", "In progress"
        CANCELING = "canceling", "Canceling"

    class Type(models.TextChoices):
        ASSISTANT = "assistant", "Assistant"
        TOOL_CALL = "tool_call", "Tool call"
        DEEP_RESEARCH = "deep_research", "Deep research"
        SLACK = "slack", "Slack"

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IDLE)
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.ASSISTANT)
```

### JSONField for flexible config

Instead of adding columns for every configuration knob, PostHog uses `JSONField` with typed validation at the application layer:

```python
# products/llm_analytics/backend/models/evaluations.py

class Evaluation(UUIDTModel):
    evaluation_type = models.CharField(max_length=50, choices=EvaluationType.choices)
    evaluation_config = models.JSONField(default=dict)
    output_type = models.CharField(max_length=50, choices=OutputType.choices)
    output_config = models.JSONField(default=dict)
    conditions = models.JSONField(default=list)
```

### Indexes on (team, -created_at) for multi-tenant queries

Every list query is scoped to a team, sorted by recency. PostHog indexes accordingly:

```python
# products/llm_analytics/backend/models/datasets.py

class Dataset(UUIDModel, CreatedMetaFields, UpdatedMetaFields, DeletedMetaFields):
    class Meta:
        ordering = ["-created_at", "id"]
        indexes = [
            models.Index(fields=["team", "-created_at", "id"]),
            models.Index(fields=["team", "-updated_at", "id"]),
        ]
```

### Service layer: functions in logic.py

Business logic lives in plain functions, not in model methods or viewset code. Custom domain exceptions replace generic `ValueError`/`404` responses:

```python
# products/visual_review/backend/logic.py

class RepoNotFoundError(Exception):
    pass

class RunNotFoundError(Exception):
    pass

class StaleRunError(Exception):
    """Approval blocked because a newer run exists for this PR."""
    pass

def get_repo(repo_id: UUID, team_id: int) -> Repo:
    try:
        return Repo.objects.get(id=repo_id, team_id=team_id)
    except Repo.DoesNotExist as e:
        raise RepoNotFoundError(f"Repo {repo_id} not found") from e

def list_repos_for_team(team_id: int) -> list[Repo]:
    return list(Repo.objects.filter(team_id=team_id).order_by("-created_at"))

@transaction.atomic
def create_run(repo_id, team_id, run_type, commit_sha, branch, pr_number, snapshots, baseline_hashes, metadata=None):
    repo = get_repo(repo_id, team_id)
    # ... business logic, not in the view
    return run, uploads
```

### structlog for structured logging

```python
# products/visual_review/backend/logic.py

import structlog
logger = structlog.get_logger(__name__)

logger.info("visual_review.repo_renamed", repo_id=str(repo.id), old_name=repo.repo_full_name, new_name=new_full_name)
logger.warning("visual_review.status_check_failed", run_id=str(run.id), status_code=response.status_code)
```

---

## What we take

Our adaptation for Preply Lesson Intelligence keeps the spirit of these patterns but simplifies for hackathon scope.

### TimeStampedModel base

We use `django-model-utils` TimeStampedModel instead of composing `CreatedMetaFields` + `UpdatedMetaFields`. It gives us `created` and `modified` auto-fields on every model with one inheritance:

```python
# backend/models/base.py

from model_utils.models import TimeStampedModel

# All our models inherit from TimeStampedModel:
# - created  = DateTimeField(auto_now_add=True)
# - modified = DateTimeField(auto_now=True)
```

### TextChoices for all enums

Same pattern as PostHog. We define TextChoices at the module level when shared, or nested in the model when scoped:

```python
# backend/models/choices.py

class SubjectType(models.TextChoices):
    LANGUAGE = "language"
    MATH = "math"
    ART = "art"
    MUSIC = "music"
    OTHER = "other"

class TutoringStatus(models.TextChoices):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"

class SkillExecutionStatus(models.TextChoices):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class ClasstimeSessionType(models.TextChoices):
    SOLO = "solo"
    GROUP = "group"
    ANONYMOUS = "anonymous"
```

### JSONField for flexible data

We follow PostHog's pattern of pairing a `CharField` discriminator with a `JSONField` body. The discriminator (`subject_type`, `skill_name`, `session_type`) is indexed for filtering; the JSON blob holds the variable payload:

```python
# Typed discriminator + flexible payload
class TutoringRelationship(TimeStampedModel):
    subject_type = CharField(max_length=20, choices=SubjectType.choices, db_index=True)
    subject_config = JSONField(default=dict)  # {"native_language": "uk", "target_language": "en"}

class Lesson(TimeStampedModel):
    subject_type = CharField(max_length=20, choices=SubjectType.choices, db_index=True)
    subject_config = JSONField(default=dict)
    transcript_data = JSONField(null=True, blank=True)

class SkillExecution(TimeStampedModel):
    skill_name = CharField(max_length=100, db_index=True)
    input_data = JSONField(default=dict)
    output_data = JSONField(default=dict)  # Query tools read from this

class ClasstimeSession(TimeStampedModel):
    questions_data = JSONField(default=list)

class SessionParticipant(TimeStampedModel):
    results_data = JSONField(null=True, blank=True)

class DailyBriefing(TimeStampedModel):
    briefing_data = JSONField(default=dict)
```

### Indexes scoped to access patterns

PostHog indexes on `(team, -created_at)` because every query is team-scoped. Our equivalent is teacher-scoped or student-scoped:

```python
class Lesson(TimeStampedModel):
    class Meta:
        indexes = [
            Index(fields=["teacher", "-date"]),          # Teacher's lesson list
            Index(fields=["subject_type", "-date"]),     # Filter by subject
        ]

class SkillExecution(TimeStampedModel):
    class Meta:
        indexes = [
            Index(fields=["status", "-created"]),               # Pipeline queue
            Index(fields=["student", "skill_name", "status"]),  # Student skill lookup
            Index(fields=["lesson", "skill_name"]),             # Lesson skill results
            Index(fields=["teacher", "skill_name", "-created"]),# Teacher dashboard
        ]

class TutoringRelationship(TimeStampedModel):
    class Meta:
        unique_together = [("teacher", "student", "subject_type")]
        indexes = [
            Index(fields=["teacher", "status"]),         # Active students list
            Index(fields=["student", "status"]),         # Student's tutors
            Index(fields=["teacher", "next_lesson_at"]), # Schedule view
        ]
```

### Constraints for data integrity

PostHog uses `UniqueConstraint` with conditions. We do the same:

```python
class SessionParticipant(TimeStampedModel):
    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["session", "student"],
                name="unique_student_per_session",
                condition=Q(student__isnull=False),
            ),
            UniqueConstraint(
                fields=["session", "classtime_participant_id"],
                name="unique_ct_participant_per_session",
                condition=Q(classtime_participant_id__isnull=False),
            ),
        ]

class SkillExecution(TimeStampedModel):
    class Meta:
        constraints = [
            CheckConstraint(
                check=Q(lesson__isnull=False) | Q(student__isnull=False),
                name="skill_exec_requires_lesson_or_student",
            ),
        ]
```

### Service layer with domain exceptions

We follow PostHog's `logic.py` pattern: plain functions, custom exceptions, no business logic in views:

```python
# backend/services/skill_service.py

class SkillExecutionError(Exception):
    pass

class LessonNotFoundError(Exception):
    pass

def start_skill_execution(teacher_id: int, lesson_id: int, skill_name: str) -> SkillExecution:
    try:
        lesson = Lesson.objects.get(id=lesson_id, teacher_id=teacher_id)
    except Lesson.DoesNotExist as e:
        raise LessonNotFoundError(f"Lesson {lesson_id} not found for teacher") from e

    return SkillExecution.objects.create(
        teacher_id=teacher_id,
        lesson=lesson,
        skill_name=skill_name,
        status=SkillExecutionStatus.PENDING,
    )

def complete_skill_execution(execution_id: int, output_data: dict) -> SkillExecution:
    execution = SkillExecution.objects.get(id=execution_id)
    execution.status = SkillExecutionStatus.COMPLETED
    execution.output_data = output_data
    execution.completed_at = timezone.now()
    execution.save(update_fields=["status", "output_data", "completed_at"])
    return execution
```

### Pydantic validation at service boundary

PostHog validates JSONField contents at the application layer. We use Pydantic (strict mode, `extra=forbid`) at the service boundary:

```python
# backend/services/schemas.py

from pydantic import BaseModel, ConfigDict

class SubjectConfig(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    native_language: str
    target_language: str

class SkillOutput(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    summary: str
    details: dict
    confidence: float
```

---

## What we skip (and why)

| PostHog pattern | Our decision | Reason |
|---|---|---|
| UUID7 as primary key | Auto-increment integer | Simpler for hackathon; no volume-leaking concern with a demo |
| `DeletedMetaFields` soft-delete | Hard delete | No audit trail needed; data is disposable in demo |
| `@validated_request` decorator | Standard DRF serializers | Fewer moving parts; Pydantic handles service-level validation |
| `post_save` signal receivers | Explicit service calls | Signals hide control flow; explicit calls are easier to debug |
| Multi-tenant `RootTeamMixin` | Single teacher per deployment | Demo targets one teacher; no team isolation needed |
| `structlog` structured logging | Python stdlib `logging` | One less dependency; can add structlog later if needed |
| `sane_repr` utility | Default `__str__` | Not worth the abstraction for a small model set |

---

## Implementation notes

### File layout

```
backend/
  models/
    __init__.py          # Re-export all models
    base.py              # TimeStampedModel (from django-model-utils)
    teacher.py           # Teacher, Student
    tutoring.py          # TutoringRelationship
    lesson.py            # Lesson, LessonStudent
    skill.py             # SkillExecution
    classtime.py         # ClasstimeSession, SessionParticipant
    briefing.py          # DailyBriefing
  services/
    __init__.py
    schemas.py           # Pydantic models for validation
    skill_service.py     # Skill execution lifecycle
    classtime_service.py # Classtime API integration
    briefing_service.py  # Daily briefing generation
    exceptions.py        # Shared domain exceptions
  views/
    ...                  # Thin DRF views that delegate to services
```

### Model base class

```python
# backend/models/base.py

from model_utils.models import TimeStampedModel

# Provides: created (auto_now_add), modified (auto_now)
# All models inherit from this instead of django.db.models.Model
```

### Service pattern

Each service file follows the same structure:

1. Domain exceptions at the top
2. Query functions (`get_*`, `list_*`)
3. Command functions (`create_*`, `update_*`, `complete_*`)
4. `@transaction.atomic` on multi-step writes

Views call services, never ORM directly. Services raise domain exceptions. Views catch them and return appropriate HTTP responses.

### Exception hierarchy

```python
# backend/services/exceptions.py

class LessonNotFoundError(Exception):
    """Lesson does not exist or is not accessible to this teacher."""
    pass

class SkillExecutionError(Exception):
    """Skill execution failed or is in an invalid state."""
    pass

class ClasstimeAPIError(Exception):
    """Classtime API returned an error or is unreachable."""
    pass

class BriefingGenerationError(Exception):
    """Failed to generate daily briefing."""
    pass
```

Views map these to HTTP status codes:

```python
# backend/views/skill_views.py

from backend.services.exceptions import LessonNotFoundError, SkillExecutionError

class SkillExecutionView(APIView):
    def post(self, request):
        try:
            execution = start_skill_execution(
                teacher_id=request.user.teacher.id,
                lesson_id=request.data["lesson_id"],
                skill_name=request.data["skill_name"],
            )
            return Response(SkillExecutionSerializer(execution).data, status=201)
        except LessonNotFoundError:
            return Response({"error": "Lesson not found"}, status=404)
        except SkillExecutionError as e:
            return Response({"error": str(e)}, status=400)
```
