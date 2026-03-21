"""Run the Temporal worker for chat agent workflows."""

import asyncio
import signal

from django.conf import settings
from django.core.management.base import BaseCommand
from temporalio.client import Client
from temporalio.worker import Worker

from workflows.chat_agent import ChatAgentWorkflow, run_chat_agent

TASK_QUEUE = "loop-your-lesson"


class Command(BaseCommand):
    help = "Run the Temporal worker for AI chat workflows"

    def handle(self, *args, **options):
        host = f"{settings.TEMPORAL_HOST}:{settings.TEMPORAL_PORT}"
        self.stdout.write(f"Starting Temporal worker (host: {host}, queue: {TASK_QUEUE})")

        try:
            asyncio.run(self._run_worker(host))
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS("\nWorker stopped."))

    async def _run_worker(self, host: str):
        api_key = getattr(settings, "TEMPORAL_API_KEY", "")
        if api_key:
            client = await Client.connect(
                host,
                namespace=settings.TEMPORAL_NAMESPACE,
                api_key=api_key,
                tls=True,
            )
        else:
            client = await Client.connect(host)
        self.stdout.write(self.style.SUCCESS(f"Connected to Temporal at {host}"))

        worker = Worker(
            client,
            task_queue=TASK_QUEUE,
            workflows=[ChatAgentWorkflow],
            activities=[run_chat_agent],
        )

        self.stdout.write(self.style.SUCCESS("Worker started. Press Ctrl+C to stop."))
        self.stdout.write("Registered: ChatAgentWorkflow, run_chat_agent")

        shutdown_event = asyncio.Event()

        def signal_handler():
            self.stdout.write("\nShutting down...")
            shutdown_event.set()

        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler)

        async with worker:
            await shutdown_event.wait()
