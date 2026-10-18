# SiteGuard AI — intercut capture plan

How to build the 3:00 submission video from two sources: the animated reel
(`safeguard-demo-reel.html`) and screen capture of the live app at
https://siteguard-ai-463547683061.us-central1.run.app

Narration and cue times are in `NARRATION.md` and are identical in both sources,
so nothing needs re-timing.

---

## The cut

| # | Window | Length | Source | What's on screen |
|---|---|---|---|---|
| 01 | 0:00–0:11 | 11s | **Reel** | "39%" statistic animation |
| 02 | 0:11–0:23 | 12s | Capture | Login card → sign in → dashboard lands |
| 03 | 0:23–0:36 | 13s | Capture | Home dashboard |
| 04a | 0:36–0:49 | 13s | Capture | New Observation step 1 → Analyze with AI |
| 04b | 0:49–1:10 | 21s | **Reel** | Multimodal call + response schema JSON |
| 05 | 1:10–1:32 | 22s | Capture | AI Analysis Result (+ inconclusive example) |
| 06 | 1:32–1:55 | 23s | Capture | Review & Confirm → record created |
| 07 | 1:55–2:12 | 17s | Capture | Hazard Register + history |
| 08 | 2:12–2:32 | 20s | Capture | Follow-ups → approve closure → report |
| 09 | 2:32–2:50 | 18s | Capture | Site Insights → generate → focus areas |
| 10 | 2:50–3:00 | 10s | **Reel** | Closing card, team, stack, links |

Reel total 42s · capture total 138s.

Reel total 47s · capture total 133s.

Segment 04 splits at 0:49 because the reel cross-fades from the app mock to the
pipeline graphic there. Capture ends on the Analyze click; the reel takes over
for the explanation of what that click does.

---

## Before you capture anything

1. Sign in as `demo` / `Safeguard@123`.
2. **Settings → Load demo data.** Without it the dashboard, register, analytics
   and notifications are empty and segments 03 and 07 have nothing to show.
3. Seed one hazard into **In Progress** with its before-photo already on it, so
   segment 08 has something to close without waiting on a live Gemini call.
4. Swap `assets/test-images/` for real site photos. The synthetic ones are flat
   coloured blocks — they will read as placeholder art on camera.
5. Set the browser to 1920×1080, zoom 100%, and hide bookmarks. Use a clean
   profile so no personal tabs or extensions are visible.
6. Clear the record you create during the shoot afterwards, or accept that it
   stays in the register judges will open.

If Gemini is slow or rate-limited mid-shoot, restart with
`SITEGUARD_BACKEND=local` and `SITEGUARD_MOCK_AI=1`. The UI labels itself
**Demo AI (mock)**, which is honest and still demonstrates the full flow.

---

## Capture segments, shot by shot

Record each as its own clip, a few seconds longer at each end than the window
needs. Trim to length in the editor.

### 02 · Sign in — 13s
Start **logged out**. Type `demo` into Username, the password into Password,
click **Sign in**, hold until the dashboard has fully rendered. Do not show the
password in plain text.

### 03 · Dashboard — 15s
Hold still on Home for 3s. Slow scroll down past the four counters, Recent
observations and Actions due, then back up. Keep the cursor still while reading.

### 04a · Capture the hazard — 13s
New Observation. Upload the photo (drag-drop reads better than the file dialog —
or pre-stage the dialog off camera). Record or attach the voice note. Type the
location: `Loading Dock B / Block C, Level 4`. Click **Analyze with AI**.
End the clip on the click, before the result appears.

### 05 · AI analysis result — 24s
Start on the finished result. Hold 4s on the confidence pill and score bar, then
scroll the right-hand card through category, risk, impact, suggested actions and
model reasoning. In the last 6s, cut to a second clip: an `_ambiguous` image
flagged **Inconclusive** with its warning callout.

### 06 · Review & confirm — 26s
Step 3. Change **Likelihood** and **Severity** on camera so the risk level
visibly recalculates — this is the beat that proves risk is not a model output.
Tick a suggested action, pick the team, set the target date, click
**Confirm & Create Record**, hold on the `SG-YYYY-NNNNN` confirmation screen.

### 07 · Register & audit trail — 20s
Hazard Register. Type the record ID into search, switch between the All / Open /
In Progress / Closed tabs so the counts change, open the record, scroll to
**History** and hold while the entries read. Flash Notifications for the last 2s.

### 09 · Site Insights — 18s
Site Insights. Hold 4s on the four computed counters and the "computed, not
generated" note. Click **Generate site insights**, wait for the briefing, then
scroll slowly through the focus areas and the blind-spots panel. This is the
beat that answers the Manufacturing theme's "operational insight" wording, so
let the recommendations be readable rather than rushing the scroll.

### 08 · Verify & close — 22s
Follow-ups. Pick the hazard, upload the after photo, **Submit for Verification**.
Cut to the Verify & Close screen: before and after side by side, the AI
Verification Summary, then **Approve closure**. End on the Hazard Closed screen
with **Download Report** visible.

---

## Assembling it

1. Open the reel, turn **Slate mode** on, go fullscreen, and record the whole
   3:00 in one take. The yellow-taped slates mark every capture window and count
   down inside it.
2. Drop that recording on the timeline as your base layer.
3. Lay each capture clip on the track above, starting exactly at its slate. The
   slate's own timecode is burned into the frame, so alignment is visual.
4. Record the voice-over against the base layer — the captions act as a
   teleprompter — then turn **Captions** off and re-record the reel segments
   clean, or keep captions on throughout for accessibility.
5. Export 1920×1080, 30fps, H.264, under 3:00.

Tools: OBS Studio for capture, DaVinci Resolve or CapCut for the edit. Both free.

### Faster alternative

If editing time is short, record the reel with Slate mode **off** and submit it
as-is — it is a complete 3:00 video. Then record a separate unlisted
walkthrough of the live app and link it in the submission notes. Judges can open
the live app themselves; the video's job is to make them want to.
