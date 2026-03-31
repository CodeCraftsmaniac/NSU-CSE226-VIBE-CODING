# Deployment Setup Guide

## GitHub Secrets Configuration

To enable auto-deployment from GitHub to Google Cloud Run, you need to configure the following secrets in your GitHub repository.

### How to Add Secrets

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret below

---

## Required GitHub Secrets

### Google Cloud Platform

**GCP_PROJECT_ID**
```
Your Google Cloud Project ID (e.g., nsu-audit-123456)
```

**GCP_SA_KEY**
```
Service Account JSON key with Cloud Run Admin and Storage Admin roles
```

To create the service account key:
```bash
# Create service account
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions Deployer"

# Grant necessary roles
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-actions@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-actions@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-actions@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Create and download key
gcloud iam service-accounts keys create key.json \
  --iam-account=github-actions@YOUR_PROJECT_ID.iam.gserviceaccount.com

# Copy the entire contents of key.json and paste as GCP_SA_KEY secret
```

---

### Supabase Configuration

**SUPABASE_URL**
```
https://kmbltplmjdkjlbungbbh.supabase.co
```

**SUPABASE_KEY** (Anon/Public Key)
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImttYmx0cGxtamRramxidW5nYmJoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njc2Mjc1MDksImV4cCI6MjA4MzIwMzUwOX0.IRoQ306ElYZh8WoTN1dXMVr9mSd20-RPxwKYZ6M6Lcg
```

**SUPABASE_SERVICE_ROLE_KEY**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImttYmx0cGxtamRramxidW5nYmJoIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NzYyNzUwOSwiZXhwIjoyMDgzMjAzNTA5fQ.CCtw4HCNIXB95TW4Ry1mAtB3__XoL1W8s49kXKHDzdI
```

**SUPABASE_JWT_SECRET**
```
fL9VMiHQL7fJmg0MmleW+JkIIECI1GqLnUTvfzG3gs3h2HjSGXVfmZ5wmdOk8KwlHJCoh3VI5gBxxSA/Tv2WIA==
```

---

### Google OAuth Configuration

**GOOGLE_CLIENT_ID**
```
656129640010-k1f9dl8cbadngqdm8dnribi9doon67ko.apps.googleusercontent.com
```

**GOOGLE_CLIENT_SECRET**
```
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
```

---

### OCR API Keys

**OCR_SPACE_API_KEY**
```
K86084037488957
```

**GOOGLE_CLOUD_VISION_KEY**
```
AIzaSyA5YsERnW7V9UzpsqkgdFhldqY8LtpJPes
```

---

## Verification

After adding all secrets:

1. Push any change to the `main` branch
2. Go to **Actions** tab in GitHub
3. Watch the "Deploy Backend to Cloud Run" workflow
4. Once complete, verify at: https://ocrapi.nsunexus.app/health

---

## Manual Deployment (if needed)

If you need to deploy manually:

```bash
# Build and push
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/nsu-audit-api

# Deploy with all env vars
gcloud run deploy nsu-audit-api \
  --image gcr.io/YOUR_PROJECT_ID/nsu-audit-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "SUPABASE_URL=https://kmbltplmjdkjlbungbbh.supabase.co" \
  --set-env-vars "SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImttYmx0cGxtamRramxidW5nYmJoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njc2Mjc1MDksImV4cCI6MjA4MzIwMzUwOX0.IRoQ306ElYZh8WoTN1dXMVr9mSd20-RPxwKYZ6M6Lcg" \
  --set-env-vars "SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImttYmx0cGxtamRramxidW5nYmJoIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NzYyNzUwOSwiZXhwIjoyMDgzMjAzNTA5fQ.CCtw4HCNIXB95TW4Ry1mAtB3__XoL1W8s49kXKHDzdI" \
  --set-env-vars "GOOGLE_CLIENT_ID=656129640010-k1f9dl8cbadngqdm8dnribi9doon67ko.apps.googleusercontent.com" \
  --set-env-vars "GOOGLE_CLIENT_SECRET=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" \
  --set-env-vars "OCR_SPACE_API_KEY=K86084037488957" \
  --set-env-vars "GOOGLE_CLOUD_VISION_KEY=AIzaSyA5YsERnW7V9UzpsqkgdFhldqY8LtpJPes"
```

---

## Current Deployment Status

- **Backend API**: https://ocrapi.nsunexus.app (Google Cloud Run)
- **Frontend**: https://ocr.nsunexus.app (Vercel)
- **Database**: Supabase (kmbltplmjdkjlbungbbh.supabase.co)

---

## Troubleshooting

### Backend returns empty config values
- Check that all secrets are added in GitHub Settings → Secrets
- Verify secret names match exactly (case-sensitive)
- Re-run the deployment workflow after adding secrets

### OAuth not working
- Verify callback URL in Google Cloud Console: https://kmbltplmjdkjlbungbbh.supabase.co/auth/v1/callback
- Check that Google OAuth is enabled in Supabase dashboard
- Ensure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are set

### Database connection fails
- Verify SUPABASE_SERVICE_ROLE_KEY is set correctly
- Check Supabase project is active
- Verify database schema is created (run backend/supabase/schema.sql)
