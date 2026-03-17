# Preply x Agora Hackathon: AI Agents for NextGen Language Learning [March 20-21, 2026]

Welcome to the Preply x Agora Hackathon in Barcelona! Join us for two days of building AI-powered language learning experiences. With a prize pool of €17,500, this hackathon brings together developers, designers, and AI enthusiasts to reimagine how people learn languages using real-time voice AI agents, video avatars, and voice biomarkers.

**Prizes:**

- 🥇 1st Place: €10,000 + Preply fast-track opportunity
- 🥈 2nd Place: €5,000
- 🥉 3rd Place: €2,500

**Tech Partners:** Agora, OpenAI, AWS, Anam, Thymia

---

## 📖 **Coding Guide: for AI and humans**

Everything you need to get an Agora Conversational voice or video AI agent running in minutes — setup with AI coding assistants (Claude Code, Codex CLI, Gemini CLI, and more), API credentials, Anam avatars, Thymia biomarkers, and vibe coding platforms (Lovable, v0).

📖 **[Hackathon Coding Guide](docs/guide.md)**

---

## 🎯 **Theme: AI Agents for NextGen Language Learning**

Build AI-powered language learning experiences using Agora's Conversational AI Engine. Create voice AI agents that help people learn languages through real-time conversation, pronunciation practice, cultural immersion, and personalized feedback — optionally enhanced with video avatars (Anam) and voice biomarkers (Thymia).

### Focus Areas

- Visualizing Learning Progress — Track and display learner advancement with AI-driven analytics
- Accelerating Learning with Agents — Build AI tutors that adapt to individual learning styles and pace
- Live Learning & Real-Time Context — Create immersive conversational experiences with real-time feedback

💡 Need inspiration? Check out the [Thought Starters](./Thought_Starters.md) for project ideas.

### Recommended Technologies

- Agora Conversational AI Engine
- Agora RTC SDK
- OpenAI API
- Anam Video Avatars
- Thymia Voice Biomarkers
- AWS

---

## 🔧 **Project Requirements & Constraints**

### Required Technologies

All submissions **must** integrate **at least one** of the following Agora products:

| Technology                  | Description                                             | Documentation                                                                |
| --------------------------- | ------------------------------------------------------- | ---------------------------------------------------------------------------- |
| **Agora Conversational AI** | Voice AI agents with real-time STT → LLM → TTS pipeline | [Docs](https://docs.agora.io/en/conversational-ai/overview/product-overview) |
| **Agora RTC SDK**           | Real-time audio/video calling and streaming             | [Docs](https://docs.agora.io/en/video-calling/overview/product-overview)     |
| **Agora RTM (Signaling)**   | Real-time messaging, presence, and data channels        | [Docs](https://docs.agora.io/en/signaling/overview/product-overview)         |
| **Agora App Builder**       | No-code video calling experiences                       | [App Builder](https://appbuilder.agora.io/)                                  |
| **Agora Cloud Recording**   | Record calls and streams in the cloud                   | [Docs](https://docs.agora.io/en/cloud-recording/overview/product-overview)   |

### Rules

- All projects must integrate at least one Agora product
- Projects must address a language learning use case
- Code must be original work created during the hackathon
- Teams may use pre-existing libraries, frameworks, and APIs (with proper attribution)
- Teams must submit a working demo and source code via pull request

### Bonus Point Opportunities

Go above and beyond for extra credit:

- ⭐ Integration of third-party APIs (Anam avatars, Thymia biomarkers, OpenAI, etc.)
- ⭐ Use of multiple Agora products together
- ⭐ Features that increase learner engagement
- ⭐ **AI Craftsmanship** — Show us *how* you built with AI. Include your planning process, prompting strategies, model choices, test-driven workflows, and iteration logs. See [How We Built This](#how-we-built-this) below.

---

## 📚 **Resources & Starter Code**

Try the voice and video AI agents live at **[convoai-demo.agora.io](https://convoai-demo.agora.io/)** — then build your own with these starter repositories:

### Starter Repositories

| Repository                                                                                  | Description                                                                              |
| ------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| [**agent-samples**](https://github.com/AgoraIO-Conversational-AI/agent-samples)             | Full-stack voice and video AI agent with Python backend and React frontends              |
| [**vibe-coding-lovable**](https://github.com/AgoraIO-Conversational-AI/vibe-coding-lovable) | Lovable-optimized starter — build a voice AI agent in your browser with zero local setup |
| [**vibe-coding-v0**](https://github.com/AgoraIO-Conversational-AI/vibe-coding-v0)           | v0-optimized starter — build a voice AI agent with Vercel hosting                        |
| [**server-custom-llm**](https://github.com/AgoraIO-Conversational-AI/server-custom-llm)     | Custom LLM middleware for RAG, tool calling, Thymia biomarkers, and conversation memory  |

### Documentation

- [**Coding Guide (for AI and humans)**](docs/guide.md)
- [Agora ConvoAI Documentation](https://docs.agora.io/en/conversational-ai/overview/product-overview)
- [Agora Console (get your App ID)](https://console.agora.io/)
- [Thymia Integration Recipe](https://github.com/AgoraIO-Conversational-AI/agent-samples/blob/main/recipes/thymia.md)

---

Follow the steps below to **fork, develop, and submit** your project.

---

## 📌 **Submission Guidelines**

### **1. Fork this Repository**

Click the Fork button on the top right to create a copy of this repository under your GitHub account.

### **2. Clone Your Forked Repository**

After forking, clone the repository to your local machine.

```bash
git clone https://github.com/YOUR-GITHUB-USERNAME/hackathon-2026-03-20-agora-preply.git
cd hackathon-2026-03-20-agora-preply
```

### **3. Create Your Team Folder**

Inside the `submissions/` directory, create a new folder using your team name.  
Example:

```
submissions/
├── team-name/
│   ├── README.md          # (Required: Describe your project)
│   ├── HOW_WE_BUILT.md    # (Recommended: Your AI development process — see below)
│   ├── demo.mp4           # (Required: A demo video)
│   ├── src/               # (Your source code)
│   └── docs/              # (Any documentation or images)
```

### **4. Work on Your Project**

- Develop your project inside your team folder.
- Include a `README.md` file explaining your project, its setup, and usage. Include any special instructions to run it.
- Include a short demo video or screenshots in the `docs/` folder.
- Include a `HOW_WE_BUILT.md` documenting your AI development process (see [How We Built This](#how-we-built-this) below).

### **5. Commit and Push Changes**

```bash
git add .
git commit -m "Submission commit - Team [Your Team Name]"
git push
```

### **6. Submit via Pull Request**

1. Go to your forked repo on GitHub.
2. Click the **"New Pull Request"** button.
3. Set the base repository to `AgoraIO-Community/hackathon-2026-03-20-agora-preply` and compare it with your forked branch.
4. In the PR description, include:
   - Team Name
   - Project Name
   - A brief summary of the project
   - Any special instructions of features to focus on or to avoid because they may not be finished. (If applicable)
5. Click **"Create Pull Request"** to submit your project.

---

<a id="how-we-built-this"></a>

## 🤖 **How We Built This (HOW_WE_BUILT.md)**

We want to see *how* you work with AI, not just what you built. Include a `HOW_WE_BUILT.md` in your team folder covering any of the following:

- **Planning** — How did you use AI to plan your architecture, break down tasks, or explore approaches?
- **Model choices** — Which AI models/tools did you use for development and why? (Claude Code, Codex CLI, Gemini CLI, Copilot, Lovable, v0, etc.)
- **Prompting strategies** — What prompting techniques worked well? What didn't? Share example prompts that led to breakthroughs.
- **Testing & iteration** — How did you verify AI-generated code? Did you use test-driven development, manual testing, or AI-assisted debugging?
- **Challenges & pivots** — Where did AI struggle? How did you course-correct?

This doesn't need to be long — a few paragraphs with concrete examples is enough. Screenshots of prompts, conversation logs, or before/after iterations are great. This feeds into the **AI Craftsmanship** bonus when judging.

---

## 🏆 **Judging Criteria**

Projects will be evaluated based on:

✅ **Innovation** (15%) – Originality of the language learning concept and creative use of AI agent capabilities
✅ **Functionality** (20%) – How well the language learning agent works — conversation quality, accuracy, and reliability
✅ **Impact** (5%) – Potential to improve real-world language learning outcomes
✅ **Technical Execution** (20%) – Code quality, architecture decisions, and effective integration of Agora
✅ **Documentation and Ease of Testing** (20%) – Quality of documentation and how easily judges can test the language learning experience
✅ **User Experience** (20%) – Quality of the learner experience — natural conversation flow, helpful feedback, and engaging interaction
⭐ **AI Craftsmanship** (bonus, up to +1) – Documented AI development process via `HOW_WE_BUILT.md` (see above)

### Judging Panel

- **TBD** – TBD, Preply
- **TBD** – TBD, Agora
- **TBD** – TBD, TBD

📋 See the full [Judging Rubric](./hackathon-rating-rubric.md) for detailed scoring criteria and evaluation process.

---

## ❓ **Need Help?**

For any questions, join our [Discord](https://discord.gg/kS7etQFKC).

For urgent matters during the event, reach out to the organizers directly at the venue.

**Happy hacking and good luck!** 🚀
