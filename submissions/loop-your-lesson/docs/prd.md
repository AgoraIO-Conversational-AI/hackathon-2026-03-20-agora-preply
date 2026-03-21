# Problem space and research

Research backing for [the pitch](pitch.md). Pre-hackathon research for the
Preply x Agora hackathon, March 20-21 2026.

Technical docs:
[Architecture](architecture.md) ·
[Scaffolding](scaffolding.md) ·
[Skills](skill-system.md) ·
[Conversational UX](conversational-ux.md) ·
[Classtime API](classtime-api-guide.md)

## The opportunity

A lot happens between lessons - students practice, teachers prep, progress is
tracked. But most of it happens outside Preply, in scattered tools that don't
talk to each other. Preply has little visibility into what happens after the
session ends.

The opportunity: own the space between lessons and make Preply a superpower for
both teachers and students.

## What happens today

**Students between lessons:** Those who practice use disconnected tools
(Duolingo, YouTube, flashcard apps) that have zero relationship to what their
tutor is teaching. Those who don't - there's nothing lesson-specific to come
back to. Either way, the tutor has no visibility into what happened.

**Teachers between lessons:** With 15-20 students, teachers track progress in
platform notes, WhatsApp, Google Docs, and memory. 8+ unpaid hours/month on
admin. Prep quality degrades, lessons become generic, and the thing that makes
private tutoring worth paying for - personalization - erodes. Assessment is
vibes-based.

Teachers also have offline lessons - in-person, Zoom, WhatsApp calls. No
platform acknowledges this. Like Granola did for meeting notes, we work with
how teachers already teach: record however you want, upload when ready. A tutor
who gets better tools through Preply stays on Preply.

## Preply's trajectory

Preply launched three AI features in August 2025, designed in collaboration
with tutors and learners:

- **Lesson Insights** - AI-generated lesson summaries with personalized feedback
  on vocabulary, grammar, and speaking. Works by transcribing lesson audio (both
  tutor and learner must opt in). Provides tailored exercise suggestions. Helps
  tutors track progress and prepare for the next lesson.
- **Daily Exercises** - bite-sized, AI-powered self-learning activities that
  connect content from lessons and learner focus areas. Designed to build
  consistent habits between sessions and reinforce vocabulary.
- **Scenario Practice** - short (~3 min) AI-powered speaking tasks based on
  real-life situations (ordering food, giving directions, workplace conversations).
  8 ready-made scenarios plus tutor-created custom scenarios assignable as
  homework. Real-time voice interaction, not written chat. Students can share
  feedback with their tutor afterward. Accessible via Teaching Assistant in the
  messaging panel.

All three are currently available to a portion of English learners and tutors,
with broader rollout and additional languages planned. Strategic narrative:
"human-led, AI-enabled" - the anti-Duolingo. This is a good trajectory.

Community feedback suggests an opportunity to go further. Tutors report concerns
about recording feeling like surveillance rather than a tool. Value flows
primarily to the student; tutors haven't received actionable outputs like error
reports or prep briefs in return. The best tutors - the ones whose lessons would
produce the richest data - may be the least likely to opt in.

We don't know the full current picture, but the pattern points to a clear
opening: make recording feel like unlocking a superpower for both sides.

## What we add

| Dimension | Preply today | Our approach |
|-----------|-------------|-------------|
| Trust | Recording feels like surveillance | Recording feels like a tool - tutor sees clear value for opting in |
| Value flow | Value goes to student + Preply | Value flows to tutor AND student equally |
| **For students** | | |
| Practice | Daily Exercises (vocabulary reinforcement) + Scenario Practice (AI speaking tasks, ~3 min, voice-based) | Formative assessment from actual lesson errors, mapped to [Classtime](https://www.classtime.com/en/) question types with auto-grading |
| Learning formats | None | Agora ConvoAI voice practice: AI avatar conversation adapted from lesson errors, quiz results feed in real-time |
| Language | English-only | Any language pair |
| **For teachers** | | |
| Lesson analysis | AI summaries, vocab highlights (student-facing) | Structured error taxonomy with severity, transcript position, teacher-facing insights |
| Teacher tools | Notes + objectives carry-forward | Cross-session error patterns, prep briefs, student progress tracking |
| Progress | Lesson count, basic metrics | Error trends, improvement/regression per category, exercise completion |
| **Scope** | | |
| Platform | Preply lessons only, requires opt-in | Any recording - Preply, Zoom, in-person, offline |

## Competitive landscape

Nobody is doing the full session-to-practice-to-progress loop:
- Preply Lesson Insights: summaries only, student-facing, trust issues
- Chatterbug: SRS + live sessions but SRS is generic, not from lesson content
- Praktika ($160M raised): AI conversation practice, no lesson analysis
- Twee/Sapere: generate exercises from topics but disconnected from actual lessons
- Granola/Otter: transcription + summaries but designed for business meetings


## Hackathon fit

Where we see opportunity:
1. Extend Lesson Insights beyond English
2. Add structured formative assessment grounded in specific lesson errors, with auto-grading and score tracking
3. Address the tutor trust problem (best tutors opt out)
4. An empathetic story for tutors who teach across platforms and offline
5. B2B value - structured assessment + progress tracking for enterprise clients
6. Adaptive learning formats - each student consumes analysis in the format
   through voice practice with an AI avatar via Agora ConvoAI

All three challenge tracks covered:
- Accelerating learning with agents - transcript to Classtime in one AI workflow
- Visualizing learning progress - cross-session error trends, teacher dashboard
- Live learning & real-time context - every lesson feeds the loop
