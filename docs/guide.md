# Build Voice & Video AI Agents in Minutes — A Hackathon Starter Guide

Whether you're joining the Preply x Agora hackathon or just exploring conversational AI for the first time, this guide gets you from zero to a working AI agent you can talk to. The entire setup takes one prompt to an AI coding assistant.

> **Note:** This guide focuses on Agora Conversational AI — the most popular path for this hackathon. However, the hackathon accepts **any Agora product** (RTC, RTM, App Builder, Cloud Recording). See the [hackathon README](../README.md) for the full list of accepted technologies.

## Contents

- [What You'll Build (with this guide)](#what-youll-build-with-this-guide)
- [Three Ways to Build](#three-ways-to-build)
  - [Terminal AI Coding Agents](#terminal-ai-coding-agents-local-most-capable)
  - [Lovable](#lovable-browser-zero-local-setup)
  - [v0](#v0-browser-vercel-hosted)
- [What You'll Need](#what-youll-need)
  - [Agora Credentials](#agora-credentials-always-required)
  - [Pipeline Mode](#fastest-path-pipeline-mode-3-values)
  - [Inline Config](#full-control-inline-config)
- [How It Works](#how-it-works)
- [Adding a Video Avatar with Anam](#adding-a-video-avatar-with-anam)
- [Adding Voice Biomarkers with Thymia](#adding-voice-biomarkers-with-thymia)
- [Hackathon Ideas](#hackathon-ideas)
- [Terminal Basics](#terminal-basics-if-youre-new)
- [Resources](#resources)

## What You'll Build (with this guide)

A real-time voice AI agent running in your browser. You speak, the agent listens, thinks, and talks back — with sub-second latency, interruption handling, and live transcription. If you want to go further, add a video avatar face (powered by Anam) or real-time voice biomarker analysis (powered by Thymia). Building with a different Agora product? You'll still need [Agora credentials](#agora-credentials-always-required) — then head to the [Agora docs](https://docs.agora.io/) for your product. If you're using Claude Code, the [Agora skill](#install-the-agora-skill) covers all Agora products, not just ConvoAI.

Try it now at **[convoai-demo.agora.io](https://convoai-demo.agora.io/)** — no setup required.

Everything runs on [Agora's Conversational AI platform](https://docs.agora.io/en/conversational-ai/overview/product-overview). The open-source [agent-samples](https://github.com/AgoraIO-Conversational-AI/agent-samples) repo gives you a Python backend and React frontends that work out of the box.

## Three Ways to Build

You don't need to write code. Pick the approach you're comfortable with:

### Terminal AI Coding Agents (Local, Most Capable)

A terminal-based AI coding agent can clone the repo, read the instructions, install dependencies, configure environment variables, and start the servers — all from a single prompt. The repo includes an `AGENT.md` file written specifically for AI coding assistants, so any capable agent can follow it.

We recommend **[Claude Code](https://docs.anthropic.com/en/docs/claude-code)** — it handles the full agent-samples architecture well and has excellent support for large codebases. But any terminal-based coding agent will work:

| Agent                                                         | Description                                                               |
| ------------------------------------------------------------- | ------------------------------------------------------------------------- |
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | Anthropic's CLI agent. Deep reasoning, large context window (Recommended) |
| [Codex CLI](https://github.com/openai/codex)                  | OpenAI's terminal agent. Fast, lightweight                                |
| [Gemini CLI](https://github.com/google-gemini/gemini-cli)     | Google's CLI agent. Generous free tier                                    |
| [OpenCode](https://github.com/opencode-ai/opencode)           | Model-agnostic. Works with any LLM provider                               |
| [Aider](https://aider.chat)                                   | Git-focused. Auto-commits with clear messages                             |

**Example prompt** (works with any of the above):

```
Clone https://github.com/AgoraIO-Conversational-AI/agent-samples
and then I want to run the React Voice AI Agent here on my laptop.
Be sure to read the AGENT.md before you begin building.
```

For video with avatar:

```
Clone https://github.com/AgoraIO-Conversational-AI/agent-samples
and then I want to run the Video AI Agent with Avatar Sample here
on my laptop. Be sure to read the AGENT.md before you begin building.
```

The agent reads `AGENT.md`, installs dependencies, asks for your API keys, configures `.env`, and starts both servers. Within minutes you have a working agent in your browser.

**Install Claude Code:**

You need a Claude Pro, Max, Teams, or Enterprise subscription ($20/month+), or an Anthropic API account with credits.

Option 1 — **Claude Desktop app** (easiest, no terminal required): Download from [claude.ai/download](https://claude.ai/download). Claude Code is built into the desktop app. Open it, paste the prompt above, and go.

Option 2 — **Terminal install** (Mac / Windows / Linux):

```bash
# Mac / Linux
curl -fsSL https://claude.ai/install.sh | bash

# Windows (PowerShell)
irm https://claude.ai/install.ps1 | iex
```

#### Install the Agora Skill

Optional — gives Claude Code built-in knowledge of all Agora products (RTC, RTM, ConvoAI, Cloud Recording), token generation, and more:

```bash
npx skills add github:AgoraIO-Conversational-AI/agora-skills
```

### Lovable (Browser, Zero Local Setup)

[Lovable](https://lovable.dev) generates full-stack React apps in your browser. It uses Vite + React with Supabase Edge Functions for the backend — nothing to install locally.

```
Import https://github.com/AgoraIO-Conversational-AI/vibe-coding-lovable
and read AGENT.md then set it up
```

**Repo:** [AgoraIO-Conversational-AI/vibe-coding-lovable](https://github.com/AgoraIO-Conversational-AI/vibe-coding-lovable)

### v0 (Browser, Vercel-Hosted)

[v0](https://v0.dev) is Vercel's AI coding platform. It generates Next.js apps with API routes for the backend.

```
Import https://github.com/AgoraIO-Conversational-AI/vibe-coding-v0
and read AGENT.md then set it up
```

**Repo:** [AgoraIO-Conversational-AI/vibe-coding-v0](https://github.com/AgoraIO-Conversational-AI/vibe-coding-v0)

### Why Different Repos?

Lovable and v0 have platform constraints (no GitHub package installs, can't read into `node_modules`, sandboxed builds) so they need self-contained repos with all code inlined. Terminal agents have no such limitations — they work directly with agent-samples' full architecture.

## What You'll Need

### Agora Credentials (Always Required)

Every path starts with an Agora App ID and App Certificate:

1. Sign up at the [Agora Console](https://console.agora.io)
2. Create a project under [Project Management](https://console.agora.io/project-management)
3. Enable the **App Certificate** in your project's Security settings

```bash
APP_ID=your_agora_app_id
APP_CERTIFICATE=your_agora_app_certificate
```

The App Certificate enables token-based authentication. The backend generates secure tokens automatically — no separate REST API key needed.

### Fastest Path: Pipeline Mode (3 Values)

If you've built a pipeline in [Agora Agent Builder](https://console.agora.io), that's all you need. The pipeline already has your LLM, TTS, and ASR settings configured — the backend just references it by ID.

```bash
APP_ID=your_agora_app_id
APP_CERTIFICATE=your_agora_app_certificate
PIPELINE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

No OpenAI key. No TTS vendor. No voice ID. Three environment variables and you have a working agent.

### Full Control: Inline Config

For complete control over every provider, you'll need additional keys:

**LLM** — An API key from [OpenAI](https://platform.openai.com/settings/organization/api-keys) or any compatible provider.

**TTS** — Pick a text-to-speech vendor and get an API key + voice ID:

- [Rime](https://rime.ai/) — Fast, high-quality
- [ElevenLabs](https://elevenlabs.io/) — Wide voice library
- [OpenAI TTS](https://platform.openai.com/) — Same key as your LLM
- [Cartesia](https://cartesia.ai/) — Low-latency

```bash
APP_ID=your_agora_app_id
APP_CERTIFICATE=your_agora_app_certificate

LLM_API_KEY=your_openai_api_key
TTS_VENDOR=rime
TTS_KEY=your_tts_api_key
TTS_VOICE_ID=astra
```

## How It Works

Four components, two local and two cloud:

```
Your Browser (React client)
    ↕ audio/video via Agora SD-RTN
AI Agent Instance (cloud, managed by Agora)
    ↕ STT → LLM → TTS pipeline
Your Backend (Python, local)
    → calls Agora REST API to start/stop agents
```

**Your Backend** (local) — A Python server that generates Agora tokens and calls the REST API to spin up agents with your LLM/TTS configuration.

**The Client** (local) — A React app that captures your mic audio and plays back the agent's voice. The repo includes a polished voice client, a video avatar client, and simpler HTML versions.

**Agora SD-RTN** (cloud) — Agora's global real-time network. Routes audio bidirectionally between you and the agent. No WebRTC complexity to manage.

**The AI Agent** (cloud) — A managed agent that joins the channel as a participant. Your speech is transcribed (STT), sent to your LLM, and the response is synthesized (TTS) and streamed back. It handles interruptions — start talking and the agent stops to listen.

## Adding a Video Avatar with Anam

The video avatar client gives your AI agent a face. [Anam](https://www.anam.ai/) provides real-time avatar rendering — the avatar's lips move in sync with the agent's speech and it shows natural idle animations.

To enable Anam, add these to your `.env`:

```bash
VIDEO_AVATAR_VENDOR=anam
VIDEO_AVATAR_API_KEY=your_anam_api_key      # From Anam dashboard
VIDEO_AVATAR_ID=your_avatar_id              # From Anam dashboard
```

Then run the video client instead of the voice client:

```
Clone https://github.com/AgoraIO-Conversational-AI/agent-samples
and then I want to run the Video AI Agent with Avatar Sample here
on my laptop. Be sure to read the AGENT.md before you begin building.
```

The backend supports both [HeyGen](https://www.heygen.com/) and Anam avatars. Set `VIDEO_AVATAR_VENDOR=anam` and the backend builds the correct payload automatically.

## Adding Voice Biomarkers with Thymia

[Thymia](https://thymia.ai/) provides real-time voice biomarker analysis — stress, burnout, fatigue, and emotion scores computed from vocal patterns during a live conversation. This is where hackathon projects get interesting.

### What It Does

While the user speaks to the AI agent, their audio is analyzed in real-time by the Thymia Sentinel API. Biomarker scores are:

- **Injected into the LLM system prompt** — the agent can reference them ("I notice your stress levels have come down since we started talking")
- **Displayed in the client UI** — a dedicated Thymia tab shows wellness, clinical, and emotion scores
- **Used for safety analysis** — if concerns are detected, guidance appears for the operator

### Architecture

Thymia runs through a [Custom LLM server](https://github.com/AgoraIO-Conversational-AI/server-custom-llm) that sits between Agora and your LLM provider:

```
react-video-client-avatar → simple-backend → Agora ConvoAI → server-custom-llm
                                                                  ├── go-audio-subscriber (captures RTC audio)
                                                                  ├── Thymia module → Thymia Sentinel API
                                                                  └── RTM → Client (live biomarker scores)
```

The existing backend and client work unchanged — Thymia is enabled purely through environment variables and the Custom LLM server.

### Keys Required

| Key                            | Where to Get It                                 |
| ------------------------------ | ----------------------------------------------- |
| Agora APP_ID + APP_CERTIFICATE | [Agora Console](https://console.agora.io)       |
| Thymia API Key                 | Contact [Thymia](https://thymia.ai/)            |
| OpenAI API Key                 | [OpenAI Platform](https://platform.openai.com/) |
| TTS Key (Rime recommended)     | [Rime](https://rime.ai/)                        |

### Quick Setup

Full step-by-step instructions are in the [Thymia recipe](https://github.com/AgoraIO-Conversational-AI/agent-samples/blob/main/recipes/thymia.md). The short version:

1. Build the Go audio subscriber (one-time): `cd server-custom-llm/go-audio-subscriber && make`
2. Start the Custom LLM server: `PORT=8100 THYMIA_ENABLED=true THYMIA_API_KEY=<key> node custom_llm.js`
3. Add a `THYMIA` profile to `simple-backend/.env` pointing `LLM_URL` at your Custom LLM server
4. Start the backend and React video client
5. Enter `THYMIA` in the Server Profile field and start a conversation

Within 30-60 seconds of speaking, biomarker scores start appearing. The AI therapist (Bella) uses them to guide a wellness conversation — celebrating low stress scores and gently exploring elevated areas.

### What You'll See

- **0-10s:** Agent greets user, audio subscriber connects
- **10-30s:** Progress indicators appear (speech seconds counting up)
- **30-60s:** First biomarker scores arrive — emotions, wellness (Helios), clinical (Apollo)
- **60s+:** Agent starts referencing biomarker data in conversation
- **Safety analysis:** If concerns detected, alert appears at top of Thymia tab

## Hackathon Ideas

See the [Thought Starters](../Thought_Starters.md) for project ideas covering language anxiety coaching, pronunciation practice, avatar tutors, mock interview prep, cultural conversation partners, progress dashboards, and group language exchange.

**Custom LLM middleware** — The Custom LLM server pattern lets you intercept every LLM call. Add RAG, tool calling, conversation memory, or any custom processing without touching the backend or client code.

## Terminal Basics (If You're New)

If you're using a terminal-based coding agent and are new to the terminal, here's all you need:

```bash
pwd                    # Where am I?
ls                     # What's in this folder?
cd Projects            # Go into a folder
mkdir my-hackathon     # Create a new folder
claude                 # Launch Claude Code (or your agent of choice)
```

That's it. Once your coding agent is running, you communicate in plain English.

## Resources

| Resource                      | Link                                                                                                                         |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| **Agent Samples (main repo)** | [github.com/AgoraIO-Conversational-AI/agent-samples](https://github.com/AgoraIO-Conversational-AI/agent-samples)             |
| **Lovable Starter**           | [github.com/AgoraIO-Conversational-AI/vibe-coding-lovable](https://github.com/AgoraIO-Conversational-AI/vibe-coding-lovable) |
| **v0 Starter**                | [github.com/AgoraIO-Conversational-AI/vibe-coding-v0](https://github.com/AgoraIO-Conversational-AI/vibe-coding-v0)           |
| **Custom LLM Server**         | [github.com/AgoraIO-Conversational-AI/server-custom-llm](https://github.com/AgoraIO-Conversational-AI/server-custom-llm)     |
| **Thymia Recipe**             | [recipes/thymia.md](https://github.com/AgoraIO-Conversational-AI/agent-samples/blob/main/recipes/thymia.md)                  |
| **Agora Console**             | [console.agora.io](https://console.agora.io)                                                                                 |
| **Agora ConvoAI Docs**        | [docs.agora.io/en/conversational-ai](https://docs.agora.io/en/conversational-ai/overview/product-overview)                   |
| **Claude Code**               | [docs.anthropic.com/en/docs/claude-code](https://docs.anthropic.com/en/docs/claude-code)                                     |
| **Codex CLI**                 | [github.com/openai/codex](https://github.com/openai/codex)                                                                   |
| **Gemini CLI**                | [github.com/google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli)                                           |
| **OpenCode**                  | [github.com/opencode-ai/opencode](https://github.com/opencode-ai/opencode)                                                   |
| **Aider**                     | [aider.chat](https://aider.chat)                                                                                             |
| **Anam**                      | [anam.ai](https://www.anam.ai/)                                                                                              |
| **Thymia**                    | [thymia.ai](https://thymia.ai/)                                                                                              |
| **OpenAI API Keys**           | [platform.openai.com](https://platform.openai.com/settings/organization/api-keys)                                            |
| **TTS Providers**             | [Rime](https://rime.ai/) / [ElevenLabs](https://elevenlabs.io/) / [Cartesia](https://cartesia.ai/)                           |
