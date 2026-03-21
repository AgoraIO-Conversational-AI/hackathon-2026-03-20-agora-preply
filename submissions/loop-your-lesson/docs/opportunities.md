# Opportunities and focus areas

External research validates our core bet: the problems we're solving - dead space
between lessons, unpaid teacher admin, AI trust deficit - are the exact pain points
driving tutor attrition and student churn on Preply. This doc maps findings to
features and sharpens our hackathon focus.

For what we're building, see [architecture.md](architecture.md). For the pitch
narrative, see [pitch.md](pitch.md). For the research source, see the three Gemini
reports shared in Slack.

## Research synthesis

15,000+ words of Gemini analysis across three reports. Here's what matters for us.

### Tutor pain points we address

- **8+ hours/month unpaid admin** - tracking progress across WhatsApp, Google Docs,
  memory. Prep quality degrades. Assessment is vibes-based.
- **Lesson Insights feels like surveillance** - best tutors opt out. Reddit (Nov
  2025, 31 comments): "You allow Preply to use your hard work to train tools that
  will replace you." English-only. Other language tutors get nothing.
- **Deprofessionalization** - gamification (Super Tutor badge) tied to sales
  metrics, not teaching quality. Subjective student micro-ratings on "Clarity" and
  "Reassurance" override years of expertise.
- **Advanced learner plateau** - C1/C2 students get "expensive chatting." No
  structured curricula, no error taxonomy, no systematic progression framework.
- **Off-platform migration** - tutors teach on Zoom, WhatsApp, in-person. No
  platform acknowledges this reality. Preply pretends offline teaching doesn't exist.

### Student pain points we address

- **Dead space between lessons** - pay $25-60 for 50 minutes, then nothing for a
  week. Between-lesson practice is disconnected (Duolingo, YouTube, flashcards).
- **No structured formative assessment** - Daily Exercises reinforce vocabulary
  and Scenario Practice builds speaking confidence, but neither provides
  auto-graded assessment tied to specific lesson errors. English-only.
- **No structured progress** - lesson count is the only metric. No error trends,
  no CEFR-grounded assessment, no measurable improvement data.
- **Credit waste from disengagement** - 75% of unused credits expire. Students who
  disengage between lessons use fewer hours, lose more credits, churn faster.

### What we deliberately skip

Commissions (100% trial, 33% ongoing), subscription billing, review manipulation,
customer support failures, algorithmic visibility gaming, wage seizure on
termination. Real problems, but organizational/policy issues, not software we can
build.

## Opportunity map

| Research finding | Our feature | Demo moment | Pitch angle |
|---|---|---|---|
| 8+ hrs/month unpaid admin tracking progress | Daily briefing - automated per-student prep overnight | Teacher opens chat: "Show today's overview" → student cards with practice scores, attention flags | "Turn 8 hours of unpaid admin into zero" |
| Best tutors opt out of Lesson Insights (surveillance fear) | Trust stack - ProcessTimeline showing AI reasoning, framework citations, transcript links | Expand a thinking block: AI shows "Applied CEFR B1 descriptors → past tense marked moderate" | "We built something tutors opt IN to" |
| Students go dark between lessons (dead space) | Auto-generated Classtime practice from actual lesson errors | Open a Classtime session: fill-in-gap for conjugation error, sorter for word order | "Every lesson automatically extends itself" |
| Lesson Insights is English-only | Language-agnostic skill system with `subject_config` per language pair | Show analysis for a Spanish→English pair | "Works for any of Preply's 50+ languages" |
| Generic Daily Exercises disconnected from lessons | Question type mapping: error type → appropriate Classtime question type | Side-by-side: generic exercise vs. exercise generated from student's actual mistake at 12:45 in the transcript | "Practice that comes from YOUR lesson" |
| Advanced learners plateau - "expensive chatting" | CEFR level assessment with specific gaps and targeted suggestions | B2 student's level widget: "subjunctive mood inconsistent, conditional clause word order persists" | "Structured progression for every level" |
| Off-platform teaching is invisible | Any recording source - Preply, Zoom, in-person, phone | Upload flow: "The system doesn't care where the lesson happened" | "A tutor who gets better tools through Preply stays on Preply" |
| Value flows to students only, tutors feel exploited | Dual-mode: daily_briefing (teacher) + student_practice (student) | Same lesson data → teacher sees prep brief, student sees practice session | "Value flows to both sides equally" |
| No structured progress across sessions | Cross-session error patterns, improvement/regression tracking | Error trend: "past tense errors: 9 → 5 → 2 over three lessons" | "Each lesson builds on the last" |
| Credit waste from student disengagement | Between-lesson practice increases engagement → students use more hours | Classtime completion rates visible in daily briefing | "More engagement → fewer expired credits → less churn" |
| Lesson analysis locked in our system - no spoken practice | ConvoAI voice practice turns structured analysis into spoken conversation - students drill errors by talking, not just reading | Student finishes Classtime quiz → opens ConvoAI avatar → avatar targets the exact errors they just got wrong | "Practice speaking what you just learned" |
| Every student learns differently - one format doesn't fit all | Classtime for written practice, ConvoAI for spoken practice, text AI chat for exploration - same lesson data, three surfaces | Student picks their mode: quiz on the bus, voice practice on a walk, AI chat deep-dive at home | "Same lesson, three ways to practice" |

## Critical focus areas

### 1. Working agent loop with seeded skill data

The entire demo depends on the AI chat working end-to-end. Frontend SSE consumer
is built. Backend needs the agent loop calling Claude, query tools reading from
`SkillExecution.output_data`, and seeded data for 3-5 students.

**Why**: Without this, every other feature is a static mockup. With this, the
frontend comes alive - widgets render, trust timeline shows reasoning, suggestion
chips work.

**Done when**: Teacher sends "Show me today's overview" → gets a real AI response
with ScheduleWidget populated from database records.

### 2. Daily briefing as hero demo

This is what no competitor has. The demo flow: teacher opens chat → overview of
today's students → drill into one student → see errors with reasoning → see
practice completion status → get actionable focus suggestion.

**Why**: Directly addresses the 8+ hrs/month unpaid admin finding. Quantifiable,
tangible, immediately understandable by judges.

**Done when**: Full 3-turn conversation showing overview → student detail →
actionable recommendation, with real widgets at each step.

### 3. One working Classtime session

Demonstrate the full loop: skill output → question generation → live Classtime
session URL that someone can actually open and answer.

**Why**: Proves the "dead space" claim isn't theoretical. A real practice session
with auto-graded questions from actual lesson errors is the tangible artifact judges
can interact with.

**Done when**: A shareable URL opens a Classtime session with 5-6 real questions
mapped from error types.

### 4. Trust stack polish

The ProcessTimeline is built but needs real data flowing through it. Thinking
blocks, tool call indicators, reasoning fields - this is what differentiates us
from "surveillance AI."

**Why**: The research is unambiguous - trust is the adoption bottleneck. If it
looks like surveillance, the best tutors won't use it. The transparency UX must
feel natural, not performative.

**Done when**: A conversation turn shows collapsible thinking → tool call with
args → widget result → AI response referencing specific findings. All smooth.

### 5. Agora ConvoAI as voice practice layer

Our pipeline produces structured analysis. Classtime tests it in writing.
ConvoAI lets students practice it in speech. The tight feedback loop -
quiz results feeding avatar behavior in real-time - is the key innovation.

**Why**: Research shows students go dark between lessons. Written exercises
help but speaking is where language lives. An avatar that knows your
specific errors and adapts to your quiz performance closes the loop in
a way generic conversation AI cannot.

**Done when**: Student finishes Classtime quiz → opens ConvoAI avatar →
avatar references specific errors from the quiz → Thymia detects stress
on a topic → avatar adapts. Full real-time loop visible.


## What we're NOT building

| Opportunity | Why we skip |
|---|---|
| Community forums / social learning | Different product category entirely - weeks of work, not a hackathon feature |
| Group classes | Classtime supports groups but our pipeline is 1:1 focused - adding groups dilutes the demo |
| On-demand instant tutoring | Irrelevant to between-lesson intelligence |
| Billing/subscription reform | Platform policy, not software |
| Review system reform | Moderation policy, not our domain |
| Real-time in-lesson assistance | We analyze after the lesson. Real-time is a different architecture and trust dynamic |
| Full pipeline automation | Seed data for the demo. Automation is post-hackathon |
| Full Thymia clinical-grade analysis | We use biomarkers as soft signals for pacing, not diagnostic tools |

## Pitch sharpening

### Narrative arc

1. **Problem** (research-backed): "Students pay $25-60 for 50 minutes. Then
   nothing. Teachers spend 8 unpaid hours monthly tracking progress across
   WhatsApp, Google Docs, and memory. Lesson Insights was supposed to help - but
   the best tutors opt out because it feels like surveillance and gives them
   nothing back."

2. **Insight**: "The space between lessons is where Preply's impact can grow the
   most. Not by adding features to the lesson itself, but by making every lesson
   automatically feed the next one."

3. **Demo**: Daily briefing → student drill-down → Classtime practice session →
   student AI chat. Show the full loop.

4. **Business case**: "More engaged students between lessons → higher credit
   utilization → lower churn. A tutor who gets better tools through Preply stays
   on Preply."

### Three angles for three tracks

| Track | Our angle | Research backing |
|---|---|---|
| Accelerating learning with agents | Transcript → AI skill pipeline → Classtime practice, fully automated | Dead space + generic exercises |
| Visualizing learning progress | Error trends, CEFR assessment, cross-session patterns via AI chat | Advanced learner plateau + vibes-based assessment |
| Live learning & real-time context | Every lesson feeds the loop. Chrome extension reads context. Daily briefing precomputed overnight. | 8+ hours unpaid admin + off-platform invisibility |

### Language guidance

**Use**: "the system analyzes", "teachers own the flow", "value flows to both
sides", "works with any recording", "shows its reasoning"

**Avoid**: "we track", "monitors quality", "AI learns from tutors", "training
data", "compliance", "replaces". The research shows these are the exact triggers
for tutor backlash - the association with surveillance and replacement anxiety is
immediate and visceral.

## Open questions

1. **Which hackathon track do we submit to?** All three are covered. Do we pick
   one primary or pitch as cross-track?
2. **Do we demo the Chrome extension?** It adds visual context ("AI lives inside
   Preply") but requires setup. Worth the risk?
3. **Classtime dependency** - do we have API access confirmed? If Classtime
   integration isn't ready, do we mock the session or skip it?
4. **Transcript source for demo** - do we use a real Preply transcript or a
   synthetic one? Real is more compelling but may raise privacy questions.
5. **Student practice mode** - do we demo both modes or focus entirely on the
   teacher daily briefing? Splitting may dilute impact.
