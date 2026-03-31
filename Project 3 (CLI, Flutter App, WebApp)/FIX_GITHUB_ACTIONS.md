# Fix GitHub Actions Deployment Permissions

## Problem
The GitHub Actions service account `github-actions@galvanic-deck-478816-u9.iam.gserviceaccount.com` is missing required permissions to deploy to Cloud Run.

## Solution - Add ALL Required Roles

### Go to GCP Console:
1. Open: https://console.cloud.google.com/iam-admin/iam?project=galvanic-deck-478816-u9
2. Find the service account: `github-actions@galvanic-deck-478816-u9.iam.gserviceaccount.com`
3. Click "Edit" (pencil icon)
4. Click "ADD ANOTHER ROLE" for each missing role below
5. Click "SAVE"

### Required Roles for github-actions Service Account:
```bash
# Add all these roles to github-actions@galvanic-deck-478816-u9.iam.gserviceaccount.com

# 1. Cloud Run Admin - deploy and manage Cloud Run services
gcloud projects add-iam-policy-binding galvanic-deck-478816-u9 \
  --member="serviceAccount:github-actions@galvanic-deck-478816-u9.iam.gserviceaccount.com" \
  --role="roles/run.admin"

# 2. Service Account User - act as service accounts
gcloud projects add-iam-policy-binding galvanic-deck-478816-u9 \
  --member="serviceAccount:github-actions@galvanic-deck-478816-u9.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# 3. Cloud Build Service Account - trigger builds
gcloud projects add-iam-policy-binding galvanic-deck-478816-u9 \
  --member="serviceAccount:github-actions@galvanic-deck-478816-u9.iam.gserviceaccount.com" \
  --role="roles/cloudbuild.builds.builder"

# 4. Artifact Registry Writer - push container images
gcloud projects add-iam-policy-binding galvanic-deck-478816-u9 \
  --member="serviceAccount:github-actions@galvanic-deck-478816-u9.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

# 5. Service Usage Consumer - use GCP services (CRITICAL - CURRENTLY MISSING)
gcloud projects add-iam-policy-binding galvanic-deck-478816-u9 \
  --member="serviceAccount:github-actions@galvanic-deck-478816-u9.iam.gserviceaccount.com" \
  --role="roles/serviceusage.serviceUsageConsumer"
```

### Required Roles for Cloud Build Service Account:
```bash
# Add these roles to 656129640010@cloudbuild.gserviceaccount.com

# 1. Cloud Run Admin - deploy services
gcloud projects add-iam-policy-binding galvanic-deck-478816-u9 \
  --member="serviceAccount:656129640010@cloudbuild.gserviceaccount.com" \
  --role="roles/run.admin"

# 2. Service Account User - act as service accounts
gcloud projects add-iam-policy-binding galvanic-deck-478816-u9 \
  --member="serviceAccount:656129640010@cloudbuild.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
```

## Checklist - Verify All Roles Are Added:

### github-actions service account:
- [x] Cloud Run Admin (`roles/run.admin`)
- [x] Service Account User (`roles/iam.serviceAccountUser`)
- [x] Cloud Build Service Account (`roles/cloudbuild.builds.builder`)
- [x] Artifact Registry Writer (`roles/artifactregistry.writer`)
- [x] Service Usage Consumer (`roles/serviceusage.serviceUsageConsumer`)
- [x] Storage Admin (`roles/storage.admin`)

### Cloud Build service account (656129640010@cloudbuild.gserviceaccount.com):
- [x] Cloud Run Admin (`roles/run.admin`)
- [x] Service Account User (`roles/iam.serviceAccountUser`)

## Status
✅ All permissions have been added. Deployment should now succeed.
