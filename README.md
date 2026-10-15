# SiteGuard AI

AI-assisted construction-site hazard review. A reviewer uploads a site photo and
voice note, Gemini flags potential hazards and proposes a risk level, and a human
confirms every state change -- hazard confirmed, action assigned, closure. On a
later visit, new evidence is compared against the original finding and Gemini
recommends (with human approval) whether the hazard is closed.

Non-negotiables:
- The AI proposes; a human approves every state change.
- Never "safe," "compliant," or "fixed" -- only "evidence suggests," "appears
  present," or "inconclusive."
- Every finding links back to its source photo/audio file.

## Stack

Streamlit + Gemini (`gemini-2.5-flash`, structured JSON output) + Firestore
(hazard register) + Cloud Storage (evidence) + Cloud Run (deploy).

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
app.py                  Streamlit entry, 3-view router (Capture / Hazard Register / Follow-up)
lib/gemini.py            Gemini calls + structured response schema
lib/firestore.py         Firestore read/write + Cloud Storage uploads
lib/risk.py               Deterministic risk matrix (not a Gemini call)
lib/schema.py              Shared type definitions
.streamlit/config.toml    Theme
assets/test-images/        Curated test set (placeholders -- replace with real photos)
scripts/generate_test_images.py  Generates the placeholder test set
scripts/seed_test_data.py        Seeds fabricated prior hazard records
```

## Out of scope

Live CCTV, real-time worker tracking, automatic regulatory certification, BIM
integration, automated emergency response, custom model training.
