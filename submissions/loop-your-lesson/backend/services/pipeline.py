# Pipeline orchestration: lesson → skills → Classtime session
#
# Cross-domain: coordinates apps/lessons, apps/skill_results,
# apps/classtime_sessions. This is the only service that genuinely
# spans multiple apps.
#
# Functions planned:
#   process_lesson(lesson) → ClasstimeSession
#   queue_skills(lesson) → list[SkillExecution]
#
# See: docs/classtime-api-guide.md (section 12: End-to-end pipeline)
# See: docs/development-plan.md (Phase 2)
