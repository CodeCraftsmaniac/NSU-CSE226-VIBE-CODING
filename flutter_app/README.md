# NSU Degree Audit Flutter App

Premium Android client for the NSU Degree Audit Engine. The app keeps the website's backend logic by calling the same `/upload` API and renders the result in a more polished mobile-first experience.

## What It Includes

- PDF and image picker for transcript uploads
- Premium landing, upload, and processing UI
- Level 1 credit tally, Level 2 CGPA analysis, and Level 3 degree audit views
- OCR metadata, CGPA mismatch warnings, semester breakdowns, and retake summaries
- Configurable backend endpoint so you can target local Flask, emulator-hosted Flask, or the deployed Vercel URL

## Run It

```bash
cd flutter_app
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:5000
```

## Backend URL Notes

- Android emulator to local Flask app: `http://10.0.2.2:5000`
- Physical device to local Flask app: use your computer's LAN IP, for example `http://192.168.0.10:5000`
- Deployed web backend: pass the Vercel URL with `--dart-define=API_BASE_URL=...`

You can also update the endpoint from inside the app using the `API Endpoint` action.
