# SafeGuard AI — demo video narration (3:00)

457 words · ~152 words per minute · leave a short beat of silence between cues.
Timecodes match the reel in `safeguard-demo-reel.html` exactly, so you can record
voice-over against the reel's on-screen timecode and caption bar.

---

## 01 · The problem — 0:00–0:12
Black frame, "39%" counts up, supporting stats slide in.

**0:00** Falls, blocked walkways and missing PPE still kill more workers than anything else on a site.

**0:06** And most are still caught on paper — if they're caught at all.

## 02 · Sign in — 0:12–0:25
Logo and wordmark, then the sign-in card.

**0:12** This is SafeGuard AI.

**0:14** Every reviewer signs in, so every decision in the system carries a name and a timestamp.

**0:20** The AI proposes. A human approves every state change.

## 03 · Dashboard — 0:25–0:40
Counters count up; recent observations, actions due, 14-day trend.

**0:25** One screen shows what's open, what's overdue, and what's waiting on a person right now.

**0:31** High risk first, then the corrective actions coming due.

**0:36** Nothing sits in a binder nobody can query.

## 04 · Capture → Gemini — 0:40–1:18
Step 1 of the capture flow, then the multimodal pipeline and the JSON typing out.

**0:40** It starts with a photo.

**0:42** A reviewer captures the hazard on a phone, adds a voice note, and tags the location and time.

**0:49** Loading Dock B. Boxes stacked in front of a fire extinguisher.

**0:54** The image, the audio and the typed note go to Gemini 3.5 Flash in a single multimodal call.

**1:01** One model, one call — not three separate pipelines stitched together.

**1:06** A response schema forces the answer back as structured JSON.

**1:11** Category, confidence, risk inputs, suggested actions. Nothing is scraped out of prose.

## 05 · The proposal — 1:18–1:42
AI Analysis Result; confidence bar fills to 86%; the inconclusive card slides in.

**1:18** What comes back is a proposal, never a verdict.

**1:22** A hazard category, a calibrated confidence score, the likely impact, suggested corrective actions, and the team that should own them.

**1:31** And when the angle, the lighting or the audio won't support a read, inconclusive is a valid answer.

**1:37** The model says so, instead of guessing.

## 06 · Review & confirm — 1:42–2:08
Likelihood and severity change, the matrix cell moves 4·Medium → 9·High, actions tick, record created.

**1:42** Now the reviewer takes the record.

**1:45** Edit the finding, set likelihood and severity.

**1:48** Risk is computed on a deterministic matrix in plain Python, isolated from the model — so any score can be defended line by line.

**1:57** Tick the corrective actions, name the owner, set the target date.

**2:01** Nothing is written to the register until a human clicks confirm.

## 07 · Register & audit trail — 2:08–2:28
Register rows, then the history timeline builds entry by entry; notifications and reports.

**2:08** Every confirmed hazard lands in a Firestore register with its evidence attached.

**2:14** And an append-only audit trail: flagged, confirmed, assigned — every change timestamped and attributed.

**2:21** The notification feed is built from that same trail, so it can never drift from the record.

## 08 · Verify & close — 2:28–2:50
Before/after wipe, verification summary, approve closure, report.

**2:28** On a later visit, new evidence is compared against the original finding.

**2:33** Not re-scanned — compared, against this hazard specifically.

**2:38** Gemini recommends closure. The reviewer decides.

**2:42** Approve, and the record closes under your name — with the report written for you.

## 09 · Live now — 2:50–3:00
Closing card: logo, stack, links.

**2:50** Gemini, Firestore, Cloud Storage and Cloud Run — live today, inside the free tier.

**2:56** SafeGuard AI. Every hazard seen. Every fix verified.

---

## Recording the reel

1. Open the reel, click **Fullscreen**, then **Play**. It runs itself for exactly 3:00.
2. Capture the screen with OBS Studio (free), the Xbox Game Bar (`Win`+`G`), or
   Loom/ScreenPal. Record at 1920×1080, 30 fps.
3. Turn **Captions** off if you are recording voice-over; leave them on if you are
   submitting without narration.
4. Record the voice-over separately and lay it under the video in your editor —
   the timecodes above line up with the reel's own clock. Recording VO live while
   watching works too; the caption bar doubles as a teleprompter.

## Making it stronger: intercut real app footage

The reel's app screens are faithful recreations, not screen captures. Judges
respond to seeing the real thing, so the strongest version intercuts both:

- Keep the reel for beats **01, 04 (pipeline half), 09** — the stat open, the
  Gemini multimodal explanation and the closing card. These show things a screen
  capture cannot.
- Replace beats **03, 05, 06, 07, 08** with screen capture of the live app at
  https://siteguard-ai-463547683061.us-central1.run.app, following the same cues.

Before capturing the live app: sign in as `demo` / `Safeguard@123`, run
**Settings → Load demo data**, and seed one hazard already in **In Progress** so
the closure beat has something to close without waiting on a Gemini call on camera.
Swap the synthetic images in `assets/test-images/` for real site photos first.

If Gemini is slow or rate-limited on camera, restart with
`SITEGUARD_BACKEND=local` and `SITEGUARD_MOCK_AI=1` for an offline run — the UI
labels it **Demo AI (mock)**, so it stays honest.
