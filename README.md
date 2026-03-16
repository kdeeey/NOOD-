# NOOD — AI-Powered Soft Skills Coach for Moroccan Students

> *"A pocket AI coach that watches you speak and helps you get better — in Darija, in 3 minutes, on your phone."*

---

## Overview

**NOOD** is a mobile-first AI coaching application designed to help Moroccan students develop the soft skills they are rarely taught in school — public speaking, communication, interview readiness, and self-expression.

Moroccan students often graduate technically competent but unprepared for the communication demands of university presentations, thesis defenses, and job interviews. NOOD addresses this gap through short daily practice sessions, AI-powered feedback, and a gamified experience built for Gen Z.

Think of it as **Duolingo for confidence** — localized for Morocco, available in Darija/French/Arabic, and accessible on any phone.

---

## The Problem

Students in Morocco's secondary and higher education system receive virtually no formal training in:

- Speaking confidently in front of an audience
- Structuring answers in interviews or oral exams
- Managing presentation anxiety
- Developing tone, clarity, and communication habits

When they reach university, they are suddenly expected to deliver PFE defenses, group presentations, and job interviews — with no preparation. Existing self-help resources are too long, too theoretical, and not localized to the Moroccan context.

---

## The Solution

NOOD gives students a private AI coach available on their phone at any time.

**Core flow:**
1. The app sends a daily reminder with a speaking prompt
2. The student records a short 1–3 minute audio response
3. The AI analyzes their speech: filler words, speaking speed, tone, clarity, and structure
4. The student receives a confidence score, specific feedback, and improvement tips
5. Progress is tracked over time through a gamified dashboard

---

## Target Users

| Segment | Age | Context | Priority |
|---|---|---|---|
| University students | 18–25 | Presentations, PFE defenses, internship/job interviews | MVP |
| High school students (lycée/bac) | 15–18 | Oral baccalaureate, building early confidence | V2 |
| Young professionals / bootcamp graduates | 22–30 | Career growth, interview preparation | V2 |

---

## MVP Features (Version 1.0)

### 1. AI Communication Coach
- Student records a short speaking video based on a daily prompt
- AI analyzes audio: filler word count, speaking speed (WPM), pause frequency, volume consistency
- Returns a confidence score (1–10) and 3 actionable improvement tips
- Stores history so students can track progress over time

### 2. AI Interview Simulator
- Conversational interview practice (text or audio)
- Student selects a scenario (e.g., "internship interview", "PFE defense", "first job")
- AI asks questions one at a time and evaluates responses on clarity, structure, and relevance
- Returns per-answer feedback and an overall session score

### 3. Gamification
- Daily streak counter
- XP points and 5 progression levels (Beginner → Confident Speaker)
- Badges (e.g., "First Recording", "7-Day Streak", "Interview Ready")
- Progress dashboard with score trends

### 4. Student Profile
- Target career field and language preference (Darija / French / Arabic)
- Progress view: exercises completed, scores over time, streaks
- Push notification reminders for daily practice

---

## Planned Future Features (V2+)

| Feature | Reason for V2 |
|---|---|
| Video analysis (posture, eye contact, gestures) | Requires pose-estimation ML models and significant compute |
| AI Personal Coach with personalized daily plans | Requires sufficient user history to personalize meaningfully |
| Weekly Soft Skills Progress Report | Requires calibrated scoring models based on real user data |
| AI Interviewer Personas (HR, technical, startup founder) | Straightforward prompt engineering — polish the base simulator first |
| WhatsApp reminder integration | High-impact for Morocco but adds complexity |
| Darija speech-to-text (production-grade) | No production-ready Darija ASR exists yet; use French STT in V1 |
| University/institution dashboards (B2B) | Requires institutional partnerships and separate product surface |

---

## Technical Stack

### Mobile Application
- **React Native** with **Expo SDK** (TypeScript)
- Expo provides built-in camera, audio recording, push notifications, and over-the-air updates
- Cross-platform iOS and Android from a single codebase

### Backend
- **Supabase** — authentication, PostgreSQL database, file storage, edge functions
- **FastAPI** (Python) microservice for all AI processing, hosted on Railway

### AI & Machine Learning
| Capability | Tool | Notes |
|---|---|---|
| Speech-to-text | OpenAI Whisper API | Best multilingual support; Darija ~70–80% accuracy in V1 |
| Filler word detection | Post-transcription text analysis | String matching on Whisper word-level timestamps |
| Speaking speed | Word count / duration calculation | Pure arithmetic on Whisper output |
| Confidence & tone analysis | GPT-4o (transcript + metrics prompt) | ~$0.01–0.03 per session |
| Interview conversation | GPT-4o with structured system prompts | ~$0.02–0.05 per full session |
| Video/posture analysis | MediaPipe | **Deferred to V2** |

### Infrastructure
| Layer | Tool |
|---|---|
| Database | PostgreSQL via Supabase |
| Storage | Supabase Storage (S3-compatible) |
| AI Microservice Hosting | Railway (~$5–7/month) |
| Push Notifications | Expo Push Notifications |
| Analytics | PostHog |
| Error Tracking | Sentry |
| CI/CD | GitHub Actions + Expo EAS |
| Design | Figma |

---

## System Architecture

```
Mobile App (React Native / Expo)
        │
        ├── Supabase
        │     ├── Auth (email + Google)
        │     ├── PostgreSQL Database
        │     ├── File Storage (video/audio)
        │     └── Edge Functions
        │
        └── AI Microservice (FastAPI / Railway)
              ├── OpenAI Whisper API  →  Transcript + word timestamps
              ├── Filler Word Detector  →  Count + mapped timestamps
              ├── Speaking Speed Analyzer  →  WPM per segment
              └── GPT-4o  →  Confidence score + feedback + interview evaluation
```

**Core data flow:**
1. Student records video/audio in the app
2. File uploads to Supabase Storage
3. Edge function triggers the AI microservice
4. Microservice runs Whisper → filler detection → speed analysis → GPT-4o
5. Results saved to PostgreSQL and returned to the app via Supabase Realtime
6. Student sees score, feedback, and gamification updates

---

## Estimated Costs at Scale

| Item | Cost |
|---|---|
| Whisper STT | ~$0.006/min of audio |
| GPT-4o feedback per session | ~$0.01–0.03 |
| GPT-4o interview session (5–8 turns) | ~$0.02–0.05 |
| Railway (AI microservice) | ~$5–7/month |
| Supabase (free tier) | $0 up to 500MB / 50,000 MAU |
| **Total per 1,000 daily active users** | **~$50–100/day** |

---

## Team

This MVP is designed to be buildable by **2 technical co-founders** in 14–16 weeks.

| Role | Owner |
|---|---|
| Product + UX | Co-founder 1 |
| React Native mobile app | Co-founder 1 |
| Python AI microservice + backend | Co-founder 2 |
| Figma design system | Freelance (optional, ~2,000–4,000 MAD one-time) |

---

## Important: What We Will NOT Build in V1

> Video analysis (posture, eye contact, gesture detection) will **not** be in the MVP.

It requires frame-by-frame processing, GPU compute ($50–200/month), MediaPipe integration, and custom ML models — adding an estimated 6–8 weeks of development with unreliable results on phone-quality video. Audio analysis alone delivers 80% of the value at 20% of the complexity.

**Ship audio-first. Add video as a premium V2 feature.**
