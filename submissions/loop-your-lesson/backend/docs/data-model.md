# Data model

## Entity relationships

```
Teacher (accounts)
  |-- 1:N --> Lesson
  |-- 1:N --> TutoringRelationship --> Student
  |-- 1:N --> SkillExecution
  |-- 1:N --> ClasstimeSession
  |-- 1:N --> Conversation
  |-- 1:N --> DailyBriefing
  |-- 1:N --> ErrorPattern (as teacher tracking student patterns)

Student (accounts)
  |-- M:N --> Lesson (via LessonStudent)
  |-- 1:N --> TutoringRelationship --> Teacher
  |-- 1:N --> SkillExecution
  |-- 1:N --> ErrorRecord
  |-- 1:N --> ErrorPattern
  |-- 1:N --> LessonLevelAssessment
  |-- 1:N --> LessonTheme
  |-- 1:N --> Conversation

Lesson (lessons)
  |-- N:1 --> Teacher
  |-- M:N --> Student (via LessonStudent)
  |-- 1:N --> SkillExecution
  |-- 1:N --> ClasstimeSession
  |-- 1:N --> ErrorRecord
  |-- 1:N --> LessonTheme
  |-- 1:N --> LessonLevelAssessment
  |-- 1:N --> Conversation

SkillExecution (skill_results)
  |-- N:1 --> Teacher, Lesson?, Student?
  |-- 1:N --> ErrorRecord       (parsed output)
  |-- 1:N --> LessonTheme       (parsed output)
  |-- 1:N --> LessonLevelAssessment (parsed output)
  |-- 1:N --> ClasstimeSession  (via question_skill_execution)

ErrorRecord (skill_results) - one per error per lesson
  |-- N:1 --> SkillExecution, Lesson, Student
  |-- 1:N --> ErrorPatternOccurrence --> ErrorPattern
  |-- 1:N --> PracticeQuestion

ErrorPattern (learning_progress) - cross-lesson pattern tracking
  |-- N:1 --> Student, Teacher
  |-- 1:N --> ErrorPatternOccurrence --> ErrorRecord
  |-- 1:N --> PracticeQuestion
  Status: new -> recurring -> improving -> mastered

ClasstimeSession (classtime_sessions)
  |-- N:1 --> Teacher, Lesson?, Student?, SkillExecution?
  |-- 1:N --> SessionParticipant --> Student
  |-- 1:N --> PracticeQuestion

PracticeQuestion (classtime_sessions) - links question to error
  |-- N:1 --> ClasstimeSession
  |-- N:1 --> ErrorRecord? (source error)
  |-- N:1 --> ErrorPattern? (source pattern)
  |-- 1:N --> PracticeResult

PracticeResult (classtime_sessions)
  |-- N:1 --> SessionParticipant, PracticeQuestion
```

## Data flow

```
1. Lesson recorded -> Transcript stored in Lesson.transcript (JSON)

2. Skills run on transcript:
   analyze-lesson-errors   -> SkillExecution.output_data (raw JSON)
   analyze-lesson-themes   -> SkillExecution.output_data
   analyze-lesson-level    -> SkillExecution.output_data
   generate-classtime-questions -> SkillExecution.output_data

3. Parsers extract structured data (strict order):
   _parse_error_output  -> ErrorRecord rows + ErrorPattern + ErrorPatternOccurrence
   _parse_level_output  -> LessonLevelAssessment + TutoringRelationship.latest_level
   _parse_theme_output  -> LessonTheme rows
   _parse_question_output -> PracticeQuestion rows (linked to ErrorRecord + ErrorPattern)

4. Practice session created -> ClasstimeSession + PracticeQuestion.classtime_question_id populated

5. Student completes practice -> sync_session_results():
   -> PracticeResult rows created
   -> ErrorPattern.mastery_score updated
   -> ErrorPattern status transitions (recurring -> improving -> mastered)

6. Teacher briefing queries structured models:
   ErrorPattern.objects.filter(teacher=T, status__in=["new","recurring"])
   LessonLevelAssessment.objects.filter(student=S).order_by("-created_at")
   PracticeResult.objects.filter(participant__student=S)
```

## Key models

### TutoringRelationship (tutoring)

Denormalized progress fields for fast briefing queries:
- `latest_level` - mirrors most recent LessonLevelAssessment
- `latest_level_assessed_at` - when level was last assessed
- `active_error_patterns` - count of new + recurring ErrorPatterns
- `mastered_error_patterns` - count of mastered ErrorPatterns

### ErrorPattern state machine

```
new       -- first occurrence (1 lesson)
recurring -- seen in 2+ lessons, or mastered but reappeared
improving -- tested with mastery 0.5-0.8
mastered  -- tested 3+ times, mastery > 0.8
```

Status updates happen at two points:
1. **Parser** (`_parse_error_output`): new -> recurring when lesson_count >= 2, mastered -> recurring when pattern reappears
2. **Practice results** (`update_mastery_after_result`): recurring -> improving -> mastered based on practice scores

### SkillExecution lifecycle

```
create_execution()   -> PENDING
start_execution()    -> RUNNING (started_at set)
complete_execution() -> COMPLETED (output_data stored, parser called, parsed_at set)
fail_execution()     -> FAILED (error stored)
```

## Query patterns

| Query | ORM |
|-------|-----|
| All errors for student X | `ErrorRecord.objects.filter(student=X)` |
| Errors by type across lessons | `ErrorRecord.objects.filter(student=X, error_type="grammar")` |
| Persistent patterns | `ErrorPattern.objects.filter(student=X, status="recurring")` |
| Level progression | `LessonLevelAssessment.objects.filter(student=X).order_by("-created_at")` |
| Practice mastery | `ErrorPattern.objects.filter(student=X, times_tested__gt=0)` |
| Teacher briefing | `ErrorPattern.objects.filter(teacher=T, status__in=["new","recurring"])` |
| Lesson analysis | `ErrorRecord.objects.filter(lesson=L)` + `LessonTheme.objects.filter(lesson=L)` |

## Files

| App | Models file | Services |
|-----|-------------|----------|
| accounts | `apps/accounts/models.py` | - |
| lessons | `apps/lessons/models.py` | `apps/lessons/services.py` (stub) |
| tutoring | `apps/tutoring/models.py` | - |
| skill_results | `apps/skill_results/models.py` | `apps/skill_results/services/` (state machine + parsers) |
| learning_progress | `apps/learning_progress/models.py` | `apps/learning_progress/services.py` (pattern status) |
| classtime_sessions | `apps/classtime_sessions/models.py` | `apps/classtime_sessions/services/` (sessions, results, questions) |
| conversations | `apps/conversations/models.py` | `apps/conversations/services/` (agent, tools, modes) |
| daily_briefings | `apps/daily_briefings/models.py` | `apps/daily_briefings/services.py` (stub) |
