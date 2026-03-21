# Classtime external API integration
#
# Hybrid approach: REST API for questions, Proto API for sessions/results.
# Same teacher token, different transport.
#
# Questions (REST API):
#   from apps.classtime_sessions.services.questions import (
#       create_question_set, create_question, create_questions_batch,
#   )
#
# Sessions (Proto API):
#   from apps.classtime_sessions.services.sessions import (
#       create_practice_session, get_session_details, list_sessions,
#       end_session, get_student_url,
#   )
#
# Results (Proto API):
#   from apps.classtime_sessions.services.results import (
#       get_answers_summary, get_detailed_answers,
#       suggest_comment, save_comment, export_session,
#   )
#
# Schemas:
#   from apps.classtime_sessions.services.schemas import (
#       BooleanPayload, SingleChoicePayload, GapPayload,
#       SorterPayload, CategorizerPayload,
#   )
