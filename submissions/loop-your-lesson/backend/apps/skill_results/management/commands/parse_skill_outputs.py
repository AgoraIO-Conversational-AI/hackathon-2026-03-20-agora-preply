"""Parse all completed but unparsed SkillExecution records into structured models."""

from django.core.management.base import BaseCommand

from apps.skill_results.models import SkillExecution, SkillExecutionStatus
from apps.skill_results.services.parsers import parse_skill_output


class Command(BaseCommand):
    help = "Parse completed SkillExecution output_data into structured models (ErrorRecord, LessonTheme, etc.)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--skill",
            type=str,
            help="Only parse executions for this skill name (e.g. analyze-lesson-errors)",
        )
        parser.add_argument(
            "--reparse",
            action="store_true",
            help="Re-parse already parsed executions (clears parsed_at first)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be parsed without actually parsing",
        )

    def handle(self, *args, **options):
        qs = SkillExecution.objects.filter(status=SkillExecutionStatus.COMPLETED)

        if options["skill"]:
            qs = qs.filter(skill_name=options["skill"])

        if options["reparse"]:
            count = qs.count()
            if not options["dry_run"]:
                qs.update(parsed_at=None)
            self.stdout.write(f"Reset parsed_at for {count} executions")
        else:
            qs = qs.filter(parsed_at__isnull=True)

        executions = list(qs.order_by("completed_at"))
        self.stdout.write(f"Found {len(executions)} unparsed executions")

        if options["dry_run"]:
            for ex in executions:
                self.stdout.write(f"  Would parse: {ex.skill_name} (id={ex.id}, lesson={ex.lesson_id})")
            return

        parsed = 0
        failed = 0
        for ex in executions:
            try:
                parse_skill_output(ex)
                parsed += 1
                self.stdout.write(f"  Parsed: {ex.skill_name} (id={ex.id})")
            except Exception as e:
                failed += 1
                self.stderr.write(f"  Failed: {ex.skill_name} (id={ex.id}): {e}")

        self.stdout.write(self.style.SUCCESS(f"Done: {parsed} parsed, {failed} failed"))
