# SiteGuard AI — demo video narration (3:00)

Team Ceylon InnovAI · Maniesha Abeysekera · Ashen Weerasinghe
Google AI Hackathon 2026 · Manufacturing: Intelligent Operations & Industrial Efficiency

About 470 words at ~150 words per minute. Leave a short beat of silence between
cues. Timecodes match the reel in `safeguard-demo-reel.html` exactly, so you can
record voice-over against the reel's own clock and caption bar.

The four things judges are scoring are stated explicitly in the narration:
multimodal input in one call (0:49), calibrated uncertainty (1:21), a human
approving every state change (0:19, 1:50), and AI before/after closure
verification (2:12). The register-wide read at 2:32 is the Manufacturing theme's
"operational insight" wording.

---

## 01 · The problem — 0:00–0:11
Black frame, "39%" counts up, supporting stats slide in.

**0:00** Falls, blocked walkways and missing PPE still kill more workers than anything else on a site.

**0:06** And most are still caught on paper — if they're caught at all.

## 02 · Sign in — 0:11–0:23
Logo and wordmark, then the sign-in card.

**0:11** This is SiteGuard AI.

**0:13** Every reviewer signs in, so every decision in the system carries a name and a timestamp.

**0:19** The AI proposes. A human approves every state change.

## 03 · Dashboard — 0:23–0:36
Counters count up; recent observations, actions due, 14-day trend.

**0:23** One screen shows what's open, what's overdue, and what's waiting on a person right now.

**0:29** High risk first, then the corrective actions coming due.

**0:33** Nothing sits in a binder nobody can query.

## 04 · Capture → Gemini — 0:36–1:10
Capture step 1, then the multimodal pipeline and the JSON typing out.

**0:36** It starts with a photo.

**0:38** A reviewer captures the hazard on a phone, adds a voice note, and tags the location and time.

**0:44** Loading Dock B. Boxes stacked in front of a fire extinguisher.

**0:49** The image, the audio and the typed note go to Gemini 3.5 Flash in a single multimodal call.

**0:55** One model, one call — not three separate pipelines stitched together.

**1:00** A response schema forces the answer back as structured JSON.

**1:04** Category, confidence, risk inputs, suggested actions. Nothing is scraped out of prose.

## 05 · The proposal — 1:10–1:32
AI Analysis Result; confidence bar fills to 86%; the inconclusive card slides in.

**1:10** What comes back is a proposal, never a verdict.

**1:14** A hazard category, a calibrated confidence score, the likely impact, and the team that should own the fix.

**1:21** And when the angle, the lighting or the audio won't support a read, inconclusive is a valid answer.

**1:27** The model says so, instead of guessing.

## 06 · Review & confirm — 1:32–1:55
Likelihood and severity change, the matrix cell moves, actions tick, record created.

**1:32** Now the reviewer takes the record.

**1:35** Edit the finding, set likelihood and severity.

**1:38** Risk is computed on a deterministic matrix in plain Python, isolated from the model — so any score can be defended line by line.

**1:46** Tick the corrective actions, name the owner, set the target date.

**1:50** Nothing is written to the register until a human clicks confirm.

## 07 · Register & audit trail — 1:55–2:12
Register rows, then the history timeline builds entry by entry.

**1:55** Every confirmed hazard lands in a Firestore register with its evidence attached.

**2:00** And an append-only audit trail: flagged, confirmed, assigned — every change timestamped and attributed.

**2:07** The notification feed is built from that same trail, so it can never drift from the record.

## 08 · Verify & close — 2:12–2:32
Before/after wipe, verification summary, approve closure, report.

**2:12** On a later visit, new evidence is compared against the original finding.

**2:17** Not re-scanned — compared, against this hazard specifically.

**2:21** Gemini recommends closure. The reviewer decides.

**2:25** Approve, and the record closes under your name — with the report written for you.

## 09 · Site Insights — 2:32–2:50
Computed counters, then the generated briefing: focus areas and blind spots.

**2:32** One call doesn't have to read one photo. It can read the whole register.

**2:38** Site Insights asks Gemini where hazards recur and which teams are slipping.

**2:43** The counts are computed in Python — the model only interprets them, and names its own blind spots.

## 10 · Live now — 2:50–3:00
Closing card: logo, stack, team, links.

**2:50** Gemini, Firestore, Cloud Storage and Cloud Run — live today, inside the free tier.

**2:56** SiteGuard AI. Every hazard seen. Every fix verified.

---

## Recording the reel

1. Open the reel, click **Fullscreen**, then **Play**. It runs itself for exactly 3:00.
2. Capture with OBS Studio (free), the Xbox Game Bar (`Win`+`G`), or Loom. 1920×1080, 30 fps.
3. Turn **Captions** off if you are recording voice-over; leave them on if you are
   submitting without narration.
4. Record the voice-over separately and lay it under the video — the timecodes
   above line up with the reel's clock. The caption bar doubles as a teleprompter.

See `CAPTURE-PLAN.md` for intercutting real screen capture of the live app.
