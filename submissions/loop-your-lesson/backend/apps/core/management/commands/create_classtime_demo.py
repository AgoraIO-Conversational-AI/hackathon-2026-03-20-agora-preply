# ruff: noqa: E501
"""Create real Classtime question sets + sessions for demo.

Usage: uv run python manage.py create_classtime_demo
"""

from django.core.management.base import BaseCommand

from apps.classtime_sessions.services.questions import (
    create_question_set,
    create_questions_batch,
)
from apps.classtime_sessions.services.schemas import (
    BooleanPayload,
    Gap,
    GapPayload,
    SingleChoiceOption,
    SingleChoicePayload,
    SorterPayload,
)
from apps.classtime_sessions.services.sessions import (
    create_practice_session,
    create_solo_practice,
    get_student_url,
)


def _german_b1_questions():
    """Klaus Weber's cooking lesson - articles, false friends, tenses."""
    return [
        GapPayload(
            title="Gerund after 'enjoy'",
            template_text="I really enjoy {0} .",
            gaps=[Gap(type="blank", solution="cooking")],
            explanation="'Enjoy' takes a gerund (-ing form), not 'to + infinitive'.",
        ),
        SingleChoicePayload(
            title="Articles with general nouns",
            choices=[
                SingleChoiceOption(text="the", is_correct=False),
                SingleChoiceOption(text="a", is_correct=False),
                SingleChoiceOption(text="(no article)", is_correct=True),
            ],
            content="You need ___ pork and breadcrumbs for Schnitzel.",
            explanation="No article needed when talking about ingredients in general.",
        ),
        SingleChoicePayload(
            title="False friend: become vs get",
            choices=[
                SingleChoiceOption(text="become", is_correct=False),
                SingleChoiceOption(text="get", is_correct=True),
                SingleChoiceOption(text="am becoming", is_correct=False),
            ],
            content="When people ruin my food, I ___ very angry.",
            explanation="'Get angry' for temporary states. 'Become' means to change permanently. German 'bekommen' = English 'get/receive'.",
        ),
        GapPayload(
            title="Irregular past: teach",
            template_text="My grandmother {0} me the recipe when I was young.",
            gaps=[Gap(type="blank", solution="taught")],
            explanation="Teach is irregular: teach -> taught -> taught. Not 'teached'.",
        ),
        SingleChoicePayload(
            title="Relative pronoun: that vs what",
            choices=[
                SingleChoiceOption(text="what", is_correct=False),
                SingleChoiceOption(text="that", is_correct=True),
                SingleChoiceOption(text="which it", is_correct=False),
            ],
            content="The best food ___ exists is Schnitzel.",
            explanation="Use 'that' or 'which' for relative clauses, not 'what' (German 'was').",
        ),
        BooleanPayload(
            title="Progressive vs simple present for habits",
            is_correct=False,
            content="'Who is eating beans for breakfast?' is correct for talking about a general habit.",
            explanation="Use present simple for habits: 'Who eats beans for breakfast?' Progressive is for now.",
        ),
        SorterPayload(
            title="Adverb placement",
            items=["I", "also", "make", "a", "very", "good", "potato", "salad"],
            content="Put the words in the correct order.",
            explanation="Adverbs like 'also' go before the main verb: 'I also make...'",
        ),
        GapPayload(
            title="Simple past with time markers",
            template_text="Last week I {0} two goals in football!",
            gaps=[Gap(type="blank", solution="scored")],
            explanation="Use simple past (not present perfect) with 'last week'. Not 'have scored'.",
        ),
        SingleChoicePayload(
            title="Modal + bare infinitive",
            choices=[
                SingleChoiceOption(text="should", is_correct=True),
                SingleChoiceOption(text="should to", is_correct=False),
                SingleChoiceOption(text="should will", is_correct=False),
            ],
            content="My friend said I ___ try yoga.",
            explanation="After modal verbs (should, must, can), use the bare infinitive without 'to'.",
        ),
        GapPayload(
            title="Preposition: put on",
            template_text="She put the dressing {0} the salad.",
            gaps=[Gap(type="blank", solution="on")],
            explanation="'Put something ON something' - the preposition 'on' is needed.",
        ),
    ]


def _gap_deep_dive_questions():
    """Variety of gap questions for testing."""
    return [
        GapPayload(
            title="Third conditional",
            template_text="If I {0} known, I would have told you.",
            gaps=[Gap(type="blank", solution="had")],
            explanation="Third conditional: If + past perfect (had + past participle).",
        ),
        GapPayload(
            title="Present perfect continuous + for/since",
            template_text="She {0} been working here {1} three years.",
            gaps=[
                Gap(type="blank", solution="has"),
                Gap(type="blank", solution="for"),
            ],
            explanation="Present perfect continuous + 'for' (duration) or 'since' (start point).",
        ),
        GapPayload(
            title="Look forward to + gerund",
            template_text="I'm looking forward {0} {1} you at the party.",
            gaps=[
                Gap(type="blank", solution="to"),
                Gap(type="blank", solution="seeing"),
            ],
            explanation="'Look forward to' + gerund. 'To' here is a preposition, not part of an infinitive.",
        ),
        GapPayload(
            title="-ing vs -ed adjectives + fall asleep",
            template_text="The film was so {0} that I fell {1} .",
            gaps=[
                Gap(type="blank", solution="boring"),
                Gap(type="blank", solution="asleep"),
            ],
            explanation="-ing adjectives describe the cause. 'Fall asleep' is the correct collocation.",
        ),
        GapPayload(
            title="Third person -s",
            template_text="He {0} to the gym three times a week.",
            gaps=[Gap(type="blank", solution="goes")],
            explanation="Third person singular: he/she/it + verb-s. Habits use present simple.",
        ),
        GapPayload(
            title="Wish + could",
            template_text="I wish I {0} speak German fluently.",
            gaps=[Gap(type="blank", solution="could")],
            explanation="'Wish + could' for hypothetical abilities.",
        ),
        GapPayload(
            title="Get married + when",
            template_text="They {0} married {1} they were very young.",
            gaps=[
                Gap(type="blank", solution="got"),
                Gap(type="blank", solution="when"),
            ],
            explanation="'Get married' is the most common collocation. 'When' for simultaneous past events.",
        ),
    ]


class Command(BaseCommand):
    help = "Create real Classtime question sets and sessions for demo"

    def handle(self, *args, **options):
        self.stdout.write("Creating Classtime demo sessions...\n")

        # --- German B1 (Klaus) ---
        self.stdout.write("  Creating German B1 question set...")
        qs_id = create_question_set("Klaus B1 - Articles, false friends, tenses")
        q_ids = create_questions_batch(qs_id, _german_b1_questions())
        self.stdout.write(f"  Created {len(q_ids)} questions in QS {qs_id}")

        # Solo session (/code/ URL - clean start button, no login)
        solo_url = create_solo_practice(qs_id)
        solo_code = solo_url.split("/")[-1]
        self.stdout.write(f"  Solo: {solo_code}  {solo_url}")

        # Regular session (fallback)
        reg_code = create_practice_session(qs_id, "Klaus B1 practice", feedback_mode="practice")
        reg_url = get_student_url(reg_code)
        self.stdout.write(f"  Regular: {reg_code}  {reg_url}")

        self.stdout.write("")

        # --- GAP deep dive ---
        self.stdout.write("  Creating GAP deep dive question set...")
        qs_id2 = create_question_set("GAP deep dive - mixed grammar")
        q_ids2 = create_questions_batch(qs_id2, _gap_deep_dive_questions())
        self.stdout.write(f"  Created {len(q_ids2)} questions in QS {qs_id2}")

        solo_url2 = create_solo_practice(qs_id2)
        solo_code2 = solo_url2.split("/")[-1]
        self.stdout.write(f"  Solo: {solo_code2}  {solo_url2}")

        reg_code2 = create_practice_session(qs_id2, "GAP deep dive practice", feedback_mode="practice")
        reg_url2 = get_student_url(reg_code2)
        self.stdout.write(f"  Regular: {reg_code2}  {reg_url2}")

        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Sessions created!\n"))
        self.stdout.write(f"  German B1:     /code/{solo_code}  (solo)   /student/login/{reg_code}  (regular)")
        self.stdout.write(f"  GAP deep dive: /code/{solo_code2}  (solo)   /student/login/{reg_code2}  (regular)")
        self.stdout.write(
            f"\n  Update ShowcaseClasstime.tsx PRACTICE_SESSIONS with solo codes: {solo_code}, {solo_code2}"
        )
