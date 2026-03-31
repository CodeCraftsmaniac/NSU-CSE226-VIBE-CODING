# Fix GitHub Actions Deployment Permissions

## Problem
The GitHub Actions service account `github-actions@galvanic-deck-478816-u9.iam.gserviceaccount.com` is missing required permissions to deploy to Cloud Run.

## Solution
Add the following IAM role to the service account:

### Go to GCP Console:
1. Open: https://console.cloud.google.com/iam-admin/iam?project=galvanic-deck-478816-u9
2. Find the service account: `github-actions@galvanic-deck-478816-u9.iam.gserviceaccount.com`
3. Click "Edit" (pencil icon)
4. Click "ADD ANOTHER ROLE"
5. Add this role: **Cloud Build Service Account** (`roles/cloudbuild.builds.builder`)
6. Click "SAVE"

### Alternative: Use gcloud command
```bash
gcloud projects add-iam-policy-binding galvanic-deck-478816-u9 \
  --member="serviceAccount:github-actions@galvanic-deck-478816-u9.iam.gserviceaccount.com" \
  --role="roles/cloudbuild.builds.builder"
```

## Current Roles (should have all of these):
- ✅ Cloud Run Admin (`roles/run.admin`)
- ✅ Service Account User (`roles/iam.serviceAccountUser`)
- ❌ Cloud Build Service Account (`roles/cloudbuild.builds.builder`) - **MISSING - ADD THIS**

## After Adding Permission
The next push to main will automatically deploy successfully.
