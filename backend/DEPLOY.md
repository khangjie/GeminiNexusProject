# Deploy Backend to Cloud Run

## Prerequisites
- Google Cloud CLI (`gcloud`) installed and authenticated
- Docker installed
- GCP project created with billing enabled
- APIs enabled: Cloud Run, Artifact Registry, Cloud SQL, Cloud Vision, Vertex AI

## 1. Set environment variables
```bash
export PROJECT_ID=your-gcp-project-id
export REGION=us-central1
export SERVICE_NAME=nexushub-backend
export REPO_NAME=nexushub
```

## 2. Create Artifact Registry repository
```bash
gcloud artifacts repositories create $REPO_NAME \
  --repository-format=docker \
  --location=$REGION \
  --project=$PROJECT_ID
```

## 3. Build and push Docker image
```bash
# From the project root (required so top-level /agents is included)
docker build -f backend/Dockerfile -t $REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$SERVICE_NAME:latest .

# Authenticate docker to Artifact Registry
gcloud auth configure-docker $REGION-docker.pkg.dev --project $PROJECT_ID

# Push image
docker push $REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$SERVICE_NAME:latest
```

## 4. Deploy to Cloud Run
```bash
gcloud run deploy $SERVICE_NAME \
  --image $REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$SERVICE_NAME:latest \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "GCP_PROJECT_ID=$PROJECT_ID,GCP_REGION=$REGION,FIREBASE_PROJECT_ID=your-firebase-id,GEMINI_MODEL=gemini-1.5-flash" \
  --set-secrets "GOOGLE_API_KEY=google-api-key:latest,SECRET_KEY=jwt-secret-key:latest" \
  --add-cloudsql-instances $PROJECT_ID:$REGION:nexushub-db \
  --set-env-vars "DATABASE_URL=postgresql+pg8000://USER:PASSWORD@/nexushub?host=/cloudsql/$PROJECT_ID:$REGION:nexushub-db" \
  --project $PROJECT_ID
```

## 5. Set up Cloud SQL (PostgreSQL)
```bash
gcloud sql instances create nexushub-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=$REGION \
  --project=$PROJECT_ID

gcloud sql databases create nexushub --instance=nexushub-db --project=$PROJECT_ID
```

## 6. Store secrets in Secret Manager
```bash
echo -n "your-google-api-key" | gcloud secrets create google-api-key --data-file=- --project=$PROJECT_ID
echo -n "your-long-random-jwt-secret" | gcloud secrets create jwt-secret-key --data-file=- --project=$PROJECT_ID
```

## 7. Grant Cloud Run service account access to secrets
```bash
SERVICE_ACCOUNT=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(spec.template.spec.serviceAccountName)' --project=$PROJECT_ID)
gcloud secrets add-iam-policy-binding google-api-key \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor" \
  --project=$PROJECT_ID
```

## Notes
- The backend auto-creates SQLite tables on first local run (`dev.db`)
- For production, switch `DATABASE_URL` to Cloud SQL PostgreSQL
- Cloud Run scales to zero when idle — no cost when not in use
- Update `ALLOWED_ORIGINS` with your deployed frontend URL
