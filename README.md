# SiteGuard AI -- by Ceylon InnovAI

AI-assisted hazard review for factory floors, warehouses and industrial sites. A reviewer uploads a site photo and
voice note, Gemini flags potential hazards and proposes a risk level, and a human confirms every state change --
hazard confirmed, action assigned, closure. On a later visit, new evidence is compared against the original finding
and Gemini recommends (with human approval) whether the hazard is closed. Site Insights gives managers a
Gemini briefing across the whole register.

Non-negotiables:
- The AI proposes; a human approves every state change.
- Never "safe," "compliant," or "fixed" -- only "evidence suggests," "appears
  present," or "inconclusive."
- Every finding links back to its source photo/audio file.

## What's in the app

| Screen | What it does |
|---|---|
| Login | Username + password (salted PBKDF2 hashes), Remember me (signed 7-day token), lockout after 5 failed attempts |
| Dashboard | Greeting, hero, High-risk / Open / In-progress / Closed counts, recent observations, latest notifications, actions due |
| New Observation | 4 steps: **Capture** (photo, voice note, typed note, location, date/time) -> **AI Analysis** -> **Review & Confirm** (edit, risk matrix, tags, suggested actions, assign team / priority / date) -> **Assigned** |
| Hazard Register | Search, filters, All / Open / In Progress / Closed tabs with counts, record detail with full audit trail |
| My Tasks | Drafts to confirm, closure decisions waiting, open corrective actions by team, overdue count |
| Follow-ups | Before / After evidence, AI verification summary, reviewer approves or rejects closure |
| Closure & Report | "Hazard Closed" summary, downloadable HTML report (print to PDF) |
| Reports / Analytics | Closed-record reports, CSV export of the register, charts by status / risk / category / time |
| Notifications | Feed built from every hazard's history plus overdue / due-soon alerts, unread badge, mark all read |
| Settings | Display name, system status, load demo data |

Mandatory fields are marked with a red star (*) and validated with a clear message listing anything missing.

## Demo login

`demo` / `Safeguard@123` (or `admin` / `Admin@2026`). For real users add them to
`.streamlit/secrets.toml` (see `lib/auth.py`) with hashes from `python scripts/hash_password.py`;
the demo accounts are then disabled automatically. Set `SITEGUARD_SECRET` in production.

## Offline / backup demo mode

If Wi-Fi, Google Cloud or the Gemini free tier fails during judging, add to `.env`:

```
SITEGUARD_BACKEND=local
SITEGUARD_MOCK_AI=1
```

Records are then stored in `./data/` and the AI step uses clearly-labelled preset results
("Demo AI (mock)" badge). Use Settings -> **Load demo data** to fill every screen.

## Stack

Streamlit + Gemini (`gemini-3.5-flash`, structured JSON output) + Firestore
(hazard register) + Cloud Storage (evidence) + Cloud Run (deploy).

Note: `gemini-2.5-flash` (the model named in the original build spec) has been
retired by Google; `gemini-3.5-flash` is the current stable equivalent as of
this build. `lib/gemini.py` retries automatically on transient 503s.

## Local setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env            # then fill in GEMINI_API_KEY, GOOGLE_CLOUD_PROJECT, GCS_BUCKET
```

You'll also need Application Default Credentials for Firestore/Storage locally:

```bash
gcloud auth application-default login
```

Generate the placeholder test-image set (synthetic illustrations, not real
photos -- swap in real site photos before recording the demo):

```bash
python scripts/generate_test_images.py
```

Once Firestore and the bucket exist, seed a few fabricated "prior visit" hazards
so the Follow-up screen has something to match against:

```bash
python scripts/seed_test_data.py
```

Run it:

```bash
streamlit run app.py
```

## Cloud setup (one-time)

```bash
gcloud config set project siteguard-ai-511715
gcloud services enable run.googleapis.com firestore.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
gcloud firestore databases create --location=nam5 --type=firestore-native
gcloud storage buckets create gs://siteguard-ai-511715-evidence --location=us
gcloud storage buckets add-iam-policy-binding gs://siteguard-ai-511715-evidence --member=allUsers --role=roles/storage.objectViewer
```

The bucket is made publicly *readable* (not writable) so evidence photo URLs work
directly in `st.image()`/`st.audio()` without signed-URL plumbing. This is a
deliberate prototype simplification -- fine for hackathon demo evidence, not for
real PII at production scale.

## Deploy

```bash
gcloud run deploy siteguard-ai \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=your-key,GOOGLE_CLOUD_PROJECT=siteguard-ai-511715,GCS_BUCKET=siteguard-ai-511715-evidence
```

This builds with Cloud Build and deploys to Cloud Run in one step, inside the
Always Free allowance. Open the printed `*.run.app` URL in a fresh, logged-out
browser and walk the full workflow: upload, review, follow-up, closure.

## Repo layout

```
app.py                     Entry: login gate, navy sidebar, page router
views/                     One module per screen (login, dashboard, observe, register,
                           tasks, followup, reports, analytics, notifications_page, settings)
views/components.py        Shared rows, stat cards, notification bell
lib/store.py               Hazard workflow rules + backend selection (every change -> history)
lib/firestore.py           Firestore + Cloud Storage backend
lib/local_store.py         Local JSON backend (offline demo)
lib/gemini.py              Gemini calls + structured response schema (+ mock switch)
lib/mock_ai.py             Preset AI results for offline demos
lib/auth.py                Username/password login, remember-me tokens
lib/notifications.py       Notification feed from hazard history + due-date alerts
lib/ui.py                  Design system: theme CSS, pills, thumbnails, stepper, formatting
lib/report.py              HTML hazard report + CSV export
lib/risk.py                Deterministic risk matrix (not a Gemini call)
lib/schema.py              Shared type definitions
lib/demo_seed.py           Fabricated records covering every workflow state
assets/brand/              Logo / hero images cropped from the UI design
assets/test-images/        Real site photos from Pexels (see SOURCES.md)
scripts/seed_test_data.py  Seeds demo records (works on either backend)
scripts/hash_password.py   Creates a password hash for a new user
```

## Out of scope

Live CCTV, real-time worker tracking, automatic regulatory certification, BIM
integration, automated emergency response, custom model training.
