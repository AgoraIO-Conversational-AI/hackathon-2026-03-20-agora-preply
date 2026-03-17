# Preply x Agora Hackathon: AI Agents for NextGen Language Learning - Judging Rubric

## Overview

This rubric provides a structured framework for evaluating hackathon submissions. Each project will be scored across multiple categories on a scale of 1-5, with specific criteria for each score level.

---

## Judging Panel

### TBD

**TBD** | Preply  
_Expertise: Language learning and EdTech_

### TBD

**TBD** | Agora  
_Expertise: Real-time communication and Conversational AI_

### TBD

**TBD** | TBD  
_Expertise: AI and machine learning_

---

## Project Requirements

### Required Technologies

All submissions **must** integrate **at least one** of the following Agora products:

| Technology                  | Description                                             | Documentation                                                                |
| --------------------------- | ------------------------------------------------------- | ---------------------------------------------------------------------------- |
| **Agora Conversational AI** | Voice AI agents with real-time STT → LLM → TTS pipeline | [Docs](https://docs.agora.io/en/conversational-ai/overview/product-overview) |
| **Agora RTC SDK**           | Real-time audio/video calling and streaming             | [Docs](https://docs.agora.io/en/video-calling/overview/product-overview)     |
| **Agora RTM (Signaling)**   | Real-time messaging, presence, and data channels        | [Docs](https://docs.agora.io/en/signaling/overview/product-overview)         |
| **Agora App Builder**       | No-code video calling experiences                       | [App Builder](https://appbuilder.agora.io/)                                  |
| **Agora Cloud Recording**   | Record calls and streams in the cloud                   | [Docs](https://docs.agora.io/en/cloud-recording/overview/product-overview)   |

### Project Rules

- All projects must integrate at least one Agora product

- Projects must address a language learning use case

- Code must be original work created during the hackathon

- Teams may use pre-existing libraries, frameworks, and APIs (with proper attribution)

- Teams must submit a working demo and source code via pull request

### Bonus Point Opportunities

- Integration of third-party APIs (Anam avatars, Thymia biomarkers, OpenAI, etc.)

- Use of multiple Agora products together

- Features that increase learner engagement

- **AI Craftsmanship** — Documented AI development process including planning, prompting strategies, model choices, testing workflows, and iteration logs (via `HOW_WE_BUILT.md`)

---

## Evaluation Process

Projects will be evaluated through a structured multi-phase process combining technical review, live demonstrations, and deliberation among judges.

### Evaluation Phases

**Submission Review**  
Judges independently review code, documentation, and demo videos

**Live Demonstrations**  
Teams present their projects and answer technical questions from judges

**Scoring & Deliberation**  
Judges complete individual scoring, then meet to calibrate and finalize rankings

**Results Announcement**  
Winners announced with feedback highlights for all teams

### Scoring Methodology

Each criterion is scored on a 1-5 scale:

- 5 (Exceptional): Exceeds expectations, innovative approach, could be production-ready
- 4 (Very Good): Strong implementation with minor areas for improvement
- 3 (Good): Meets requirements with solid execution
- 2 (Basic): Functional but lacks polish or depth
- 1 (Needs Work): Incomplete or significant issues

Final scores are calculated as weighted averages. Bonus points (up to +1 total) may be awarded for: exceptional use of partner technologies (Anam, Thymia), use of multiple Agora products, features that increase learner engagement, and **AI Craftsmanship** (documented AI development process via `HOW_WE_BUILT.md`).

---

## Scoring Categories

### Innovation (15%)

_Originality of the language learning concept and creative use of AI agent capabilities_

| Score | Criteria    | Description                                                                                                              |
| ----- | ----------- | ------------------------------------------------------------------------------------------------------------------------ |
| 5     | Exceptional | Novel approach not seen in existing language learning tools; creative combination of technologies that unlocks new possibilities |
| 4     | Very Good   | Fresh take on language learning with a distinctive angle; goes beyond obvious use cases                                  |
| 3     | Good        | Solid concept with some original elements; applies existing ideas in a reasonable new context                             |
| 2     | Basic       | Straightforward application of the starter template with minimal creative extension                                       |
| 1     | Needs Work  | No meaningful differentiation from the default starter project                                                            |

### Functionality (20%)

_How well the language learning agent works — conversation quality, accuracy, and reliability_

| Score | Criteria    | Description                                                                                                              |
| ----- | ----------- | ------------------------------------------------------------------------------------------------------------------------ |
| 5     | Exceptional | Agent handles multi-turn conversations flawlessly; graceful error recovery; works reliably across target languages         |
| 4     | Very Good   | Conversations feel natural with minor rough edges; core features work consistently                                         |
| 3     | Good        | Main learning flow works end-to-end; occasional issues but recoverable                                                    |
| 2     | Basic       | Core conversation works but breaks on edge cases; limited error handling                                                  |
| 1     | Needs Work  | Agent frequently fails, doesn't respond, or produces incorrect/incoherent output                                          |

### Impact (5%)

_Potential to improve real-world language learning outcomes_

| Score | Criteria    | Description                                                                                                              |
| ----- | ----------- | ------------------------------------------------------------------------------------------------------------------------ |
| 5     | Exceptional | Addresses a genuine gap in language learning; clear path to real learner improvement; could change how people practice    |
| 4     | Very Good   | Targets a real learner need with a compelling approach; would meaningfully help a specific audience                        |
| 3     | Good        | Useful for language practice with clear learning value; incremental improvement over existing tools                        |
| 2     | Basic       | Some learning value but the connection to real outcomes is thin                                                            |
| 1     | Needs Work  | No clear path to improving language learning; feels like a tech demo without educational purpose                           |

### Technical Execution (20%)

_Code quality, architecture decisions, and effective integration of Agora_

| Score | Criteria    | Description                                                                                                              |
| ----- | ----------- | ------------------------------------------------------------------------------------------------------------------------ |
| 5     | Exceptional | Clean architecture; effective use of Agora APIs; well-structured code; thoughtful error handling and edge cases            |
| 4     | Very Good   | Solid code organization; good Agora integration; minor areas where structure could improve                                 |
| 3     | Good        | Working integration with reasonable code structure; some rough spots but fundamentally sound                                |
| 2     | Basic       | Code works but is disorganized; Agora integration is minimal or uses only basic features                                   |
| 1     | Needs Work  | Broken or incomplete integration; significant code quality issues; copy-paste without understanding                         |

### Documentation and Ease of Testing (20%)

_Quality of documentation and how easily judges can test the language learning experience_

| Score | Criteria    | Description                                                                                                              |
| ----- | ----------- | ------------------------------------------------------------------------------------------------------------------------ |
| 5     | Exceptional | Judges can test in under 2 minutes; comprehensive README; clear setup steps; demo video shows key features                |
| 4     | Very Good   | Well-documented with minor gaps; judges can get it running with minimal troubleshooting                                    |
| 3     | Good        | README covers setup and usage; judges can test but may need to figure out a few steps                                      |
| 2     | Basic       | Some documentation exists but missing key setup steps or environment details; testing requires guesswork                   |
| 1     | Needs Work  | No README, no demo, or documentation is too incomplete to test without contacting the team                                 |

### User Experience (20%)

_Quality of the learner experience — natural conversation flow, helpful feedback, and engaging interaction_

| Score | Criteria    | Description                                                                                                              |
| ----- | ----------- | ------------------------------------------------------------------------------------------------------------------------ |
| 5     | Exceptional | Conversation feels natural and engaging; learner gets helpful, timely feedback; UI is polished and intuitive               |
| 4     | Very Good   | Good conversational flow with useful feedback; UI is clean with minor polish opportunities                                 |
| 3     | Good        | Functional learner experience; feedback is present but could be more natural or timely                                     |
| 2     | Basic       | Interaction works but feels robotic or confusing; limited feedback to the learner                                          |
| 1     | Needs Work  | Poor or broken user flow; no meaningful feedback; learner wouldn't know what to do                                         |

### Bonus. AI Craftsmanship (up to +1)

_How intentionally and skillfully the team used AI as a development tool, as documented in their `HOW_WE_BUILT.md`_

| Score | Criteria    | Description                                                                                                                                          |
| ----- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| +1.0  | Exceptional | Comprehensive build log with specific prompts, clear model selection rationale, evidence of test-driven or documentation-driven AI workflow, and honest reflection on what didn't work. Judges can learn from this team's process. |
| +0.75 | Very Good   | Solid documentation of AI workflow — covers planning, prompting, and iteration with concrete examples. Shows intentional model/tool choices.          |
| +0.5  | Good        | Includes a HOW_WE_BUILT.md with useful detail on AI tools used and general approach, but lacks specific examples or iteration history.                |
| +0.25 | Basic       | Brief mention of AI tools used with minimal detail on process or decision-making.                                                                    |
| +0    | Not Present | No HOW_WE_BUILT.md or no meaningful documentation of AI development process.                                                                         |

---

## Scoring Sheet

| Team Name | Innovation (15%) | Functionality (20%) | Impact (5%) | Technical Execution (20%) | Documentation and Ease of Testing (20%) | User Experience (20%) | AI Craftsmanship Bonus | Total Score | Notes |
| --------- | ---------------- | ------------------- | ----------- | ------------------------- | --------------------------------------- | --------------------- | ---------------------- | ----------- | ----- |
|           |                  |                     |             |                           |                                         |                       |                        |             |       |

## Final Score Calculation

- Each category score (1-5) is multiplied by its percentage weight
- The weighted scores are summed to calculate the final score (maximum 5 points)
- A single bonus pool of up to **+1 point total** is shared across all bonus criteria: AI Craftsmanship, use of multiple Agora products, third-party API integrations, and learner engagement features
- Judges award one combined bonus score (0 to +1) considering all bonus factors together
- Maximum possible score: **6/5** (5 base + 1 bonus)

## Feedback Section

For each submission, judges should provide:

1. **Strengths**: Key positive aspects of the project
2. **Areas for Improvement**: Constructive feedback on how the project could be enhanced
3. **Additional Comments**: Any other relevant observations or suggestions
