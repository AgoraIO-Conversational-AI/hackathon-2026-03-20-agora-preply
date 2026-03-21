# Lesson lifecycle: create, transcript storage, student linking
#
# Functions planned:
#   create_lesson(teacher, subject_type, date, transcript) → Lesson
#   link_students(lesson, student_ids) → list[LessonStudent]
#   get_transcript(lesson_id) → dict
#
# Auto-creates TutoringRelationship when students are linked.
#
# See: docs/development-plan.md (Contract 2: Transcript JSON)
