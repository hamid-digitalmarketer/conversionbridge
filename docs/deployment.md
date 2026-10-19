# Deployment Guide for ConversionBridge

ConversionBridge is designed for serverless execution on **Firebase Cloud Functions (Python v2)**, containerized deployments on **Google Cloud Run**, or standard **Linux VM / ASGI** environments.

---

## 1. Local Development (Uvicorn)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/hamid-digitalmarketer/conversionbridge.git
   cd conversionbridge
   ```

2. **Create a Python virtual environment**:
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux / macOS:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Initialize local environment**:
   ```bash
   cp .env.example .env
   ```

5. **Start the development server**:
   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
   ```

6. **Verify health endpoint**:
   ```bash
   curl http://localhost:8080/health
   ```

---

## 2. Deploying to Firebase Cloud Functions (Python v2)

ConversionBridge exports a native Firebase Functions v2 HTTP handler in `app/main.py` (`conversionbridge_api`).

### Step 1: Install Firebase CLI & Login
```bash
npm install -g firebase-tools
firebase login
```

### Step 2: Initialize Firebase Project
```bash
cp .firebaserc.example .firebaserc
# Edit .firebaserc with your target project ID
```

### Step 3: Configure Cloud Secrets
Never commit API tokens to repository files. Use Google Cloud Secret Manager via the Firebase CLI:
```bash
firebase functions:secrets:set META_ACCESS_TOKEN
firebase functions:secrets:set GA4_API_SECRET
firebase functions:secrets:set CONVERSIONBRIDGE_API_KEY
```

### Step 4: Deploy Cloud Functions & Firestore Rules
```bash
firebase deploy --only functions,firestore
```

Upon completion, the Firebase CLI will output your live HTTPS entrypoint:
`https://us-central1-YOUR_PROJECT.cloudfunctions.net/conversionbridge_api/api/v1/events`

---

## 3. Testing with Firebase Local Emulator Suite

You can test Cloud Functions and Firestore locally without incurring cloud costs:
```bash
firebase emulators:start --only functions,firestore
```
The emulator UI will be available at `http://localhost:4000` and the functions endpoint at `http://localhost:5001`.
