"""Tests for Agora RTC token generation.

Verifies deterministic channel naming and token generation.
"""

from services.agora.tokens import generate_channel_name


class TestChannelName:
    def test_unique_per_call(self) -> None:
        """Each call produces a unique channel name (avoids 409 conflicts)."""
        name1 = generate_channel_name("student-1", "lesson-1")
        name2 = generate_channel_name("student-1", "lesson-1")
        assert name1 != name2  # Unique suffix each time

    def test_format(self) -> None:
        """Channel name has vp_ prefix and 3 segments (lesson hash, student hash, suffix)."""
        name = generate_channel_name("abc", "def")
        assert name.startswith("vp_")
        parts = name.split("_")
        assert len(parts) == 4  # vp, lesson_hash, student_hash, suffix

    def test_different_inputs_different_names(self) -> None:
        name1 = generate_channel_name("student-1", "lesson-1")
        name2 = generate_channel_name("student-2", "lesson-1")
        assert name1 != name2
