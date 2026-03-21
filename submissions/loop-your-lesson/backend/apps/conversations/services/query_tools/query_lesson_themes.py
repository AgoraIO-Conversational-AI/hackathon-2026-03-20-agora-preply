from asgiref.sync import sync_to_async
from pydantic import BaseModel

from apps.conversations.services.tools import PreplyTool, register_tool
from apps.skill_results.models import LessonTheme


class QueryLessonThemesArgs(BaseModel):
    pass


@sync_to_async
def _fetch_themes(lesson_id, student_id=None):
    qs = LessonTheme.objects.filter(lesson_id=lesson_id)
    if student_id:
        qs = qs.filter(student_id=student_id)

    themes = []
    for t in qs.order_by("created_at"):
        themes.append(
            {
                "topic": t.topic,
                "communicative_function": t.communicative_function,
                "initiated_by": t.initiated_by,
                "vocabulary_active": t.vocabulary_active,
                "vocabulary_passive": t.vocabulary_passive,
                "chunks": t.chunks,
                "transcript_range": {
                    "start": t.transcript_range_start,
                    "end": t.transcript_range_end,
                },
            }
        )
    return themes


@register_tool
class QueryLessonThemesTool(PreplyTool):
    @property
    def name(self):
        return "query_lesson_themes"

    @property
    def description(self):
        return (
            "Get lesson themes and vocabulary clusters."
            " Returns topics covered with associated vocabulary and transcript positions."
        )

    @property
    def args_schema(self):
        return QueryLessonThemesArgs

    async def execute(self, *, conversation=None):
        themes = None

        if conversation and conversation.lesson_id:
            themes = await _fetch_themes(conversation.lesson_id, conversation.student_id)

        if not themes:
            themes = self._mock_themes()

        data = {
            "widget_type": "theme_map",
            "themes": themes,
        }

        message = f"Identified {len(themes)} themes: {', '.join(t.get('topic', 'unknown') for t in themes)}."
        return message, data

    def _mock_themes(self):
        return [
            {
                "topic": "Travel planning",
                "vocabulary_active": ["itinerary", "accommodation", "departure", "layover", "destination"],
                "vocabulary_passive": [],
                "chunks": [],
                "transcript_range": {"start": "02:00", "end": "15:30"},
            },
            {
                "topic": "Restaurant and food",
                "vocabulary_active": ["reservation", "appetizer", "dietary", "bill", "tip"],
                "vocabulary_passive": [],
                "chunks": [],
                "transcript_range": {"start": "16:00", "end": "28:45"},
            },
            {
                "topic": "Giving directions",
                "vocabulary_active": ["intersection", "roundabout", "pedestrian", "shortcut", "landmark"],
                "vocabulary_passive": [],
                "chunks": [],
                "transcript_range": {"start": "30:00", "end": "42:00"},
            },
        ]
