"""Shared factories for all tests."""

from datetime import date

import factory
from django.utils import timezone

from apps.accounts.models import Student, Teacher
from apps.classtime_sessions.models import (
    ClasstimeSession,
    PracticeQuestion,
    PracticeResult,
    SessionParticipant,
)
from apps.learning_progress.models import ErrorPattern, LessonLevelAssessment
from apps.lessons.models import Lesson, LessonStudent
from apps.skill_results.models import ErrorRecord, LessonTheme, SkillExecution
from apps.tutoring.models import TutoringRelationship


class TeacherFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Teacher

    name = factory.Sequence(lambda n: f"Teacher {n}")
    email = factory.LazyAttribute(lambda o: f"{o.name.lower().replace(' ', '.')}@test.com")


class StudentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Student

    name = factory.Sequence(lambda n: f"Student {n}")
    email = factory.LazyAttribute(lambda o: f"{o.name.lower().replace(' ', '.')}@test.com")


class LessonFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Lesson

    teacher = factory.SubFactory(TeacherFactory)
    subject_type = "language"
    date = factory.LazyFunction(date.today)
    duration_minutes = 50


class LessonStudentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LessonStudent

    lesson = factory.SubFactory(LessonFactory)
    student = factory.SubFactory(StudentFactory)


class TutoringRelationshipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TutoringRelationship

    teacher = factory.SubFactory(TeacherFactory)
    student = factory.SubFactory(StudentFactory)
    subject_type = "language"
    status = "active"


class SkillExecutionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SkillExecution

    teacher = factory.SubFactory(TeacherFactory)
    lesson = factory.SubFactory(LessonFactory)
    student = factory.SubFactory(StudentFactory)
    skill_name = "analyze-lesson-errors"
    status = "completed"
    output_data = factory.LazyFunction(dict)


class ErrorRecordFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ErrorRecord

    skill_execution = factory.SubFactory(SkillExecutionFactory)
    lesson = factory.LazyAttribute(lambda o: o.skill_execution.lesson)
    student = factory.LazyAttribute(lambda o: o.skill_execution.student)
    error_type = "grammar"
    error_subtype = "verb_tense"
    severity = "moderate"
    original_text = "I go yesterday"
    corrected_text = "I went yesterday"
    explanation = "Past simple required"
    source_error_index = factory.Sequence(lambda n: n + 1)


class LessonThemeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LessonTheme

    skill_execution = factory.SubFactory(SkillExecutionFactory)
    lesson = factory.LazyAttribute(lambda o: o.skill_execution.lesson)
    student = factory.LazyAttribute(lambda o: o.skill_execution.student)
    topic = factory.Sequence(lambda n: f"Theme {n}")


class ErrorPatternFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ErrorPattern

    student = factory.SubFactory(StudentFactory)
    teacher = factory.SubFactory(TeacherFactory)
    pattern_key = factory.Sequence(lambda n: f"grammar:verb_tense:pattern_{n}")
    label = factory.Sequence(lambda n: f"Pattern {n}")
    error_type = "grammar"
    error_subtype = "verb_tense"
    status = "new"
    first_seen_at = factory.LazyFunction(timezone.now)
    last_seen_at = factory.LazyFunction(timezone.now)


class LessonLevelAssessmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LessonLevelAssessment

    skill_execution = factory.SubFactory(SkillExecutionFactory)
    lesson = factory.LazyAttribute(lambda o: o.skill_execution.lesson)
    student = factory.LazyAttribute(lambda o: o.skill_execution.student)
    overall_level = "B1"


class ClasstimeSessionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ClasstimeSession

    teacher = factory.SubFactory(TeacherFactory)
    session_code = factory.Sequence(lambda n: f"SESSION-{n:04d}")
    status = "created"


class SessionParticipantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SessionParticipant

    session = factory.SubFactory(ClasstimeSessionFactory)
    student = factory.SubFactory(StudentFactory)


class PracticeQuestionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PracticeQuestion

    session = factory.SubFactory(ClasstimeSessionFactory)
    question_index = factory.Sequence(lambda n: n)
    question_type = "gap"
    stem = factory.Sequence(lambda n: f"Question {n}")


class PracticeResultFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PracticeResult

    participant = factory.SubFactory(SessionParticipantFactory)
    practice_question = factory.SubFactory(PracticeQuestionFactory)
    is_correct = True
