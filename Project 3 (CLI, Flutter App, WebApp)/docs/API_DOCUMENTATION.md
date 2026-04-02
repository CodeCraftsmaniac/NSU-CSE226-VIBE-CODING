# NSU Degree Audit - API Documentation

Complete API reference for the NSU Degree Audit backend.

**Base URL:** `https://ocrapi.nsunexus.app`

## Authentication

The API uses Bearer token authentication from Supabase.

```javascript
// Get auth headers
const headers = {
  'Authorization': `Bearer ${accessToken}`,
  'Content-Type': 'application/json'
};
```

## Endpoints

### Health Check

```http
GET /health
```

Returns API status, OCR engine availability, and system info.

**Example Response:**
```json
{
  "status": "healthy",
  "version": "2.3.1",
  "database": {
    "enabled": true,
    "connected": true
  },
  "ocr_engines": {
    "google_vision": { "configured": true },
    "ocr_space": { "configured": true }
  }
}
```

---

### Upload & Scan Transcript

```http
POST /upload
Content-Type: multipart/form-data
```

Upload a transcript file for OCR and analysis.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| file | File | PDF, PNG, JPG, or CSV file |
| source | string | Optional: "web", "cli", "flutter", "mcp" |

**Example (JavaScript):**
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('source', 'web');

const response = await fetch('https://ocrapi.nsunexus.app/upload', {
  method: 'POST',
  body: formData,
  headers: await getAuthHeaders()
});

const result = await response.json();
if (result.success) {
  console.log('Analysis:', result.data);
}
```

**Example (Python):**
```python
import requests

with open('transcript.pdf', 'rb') as f:
    files = {'file': ('transcript.pdf', f, 'application/pdf')}
    data = {'source': 'cli'}
    headers = {'Authorization': f'Bearer {token}'}
    
    response = requests.post(
        'https://ocrapi.nsunexus.app/upload',
        files=files,
        data=data,
        headers=headers
    )
    
result = response.json()
print(f"CGPA: {result['data']['level2']['cgpa']}")
```

**Example (cURL):**
```bash
curl -X POST https://ocrapi.nsunexus.app/upload \
  -F "file=@transcript.pdf" \
  -F "source=cli" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response Structure:**
```json
{
  "success": true,
  "data": {
    "level1": {
      "total_entries": 45,
      "unique_courses": 43,
      "earned_credits": 120,
      "failed_credits": 3,
      "progress_130": 92.3,
      "retakes": []
    },
    "level2": {
      "cgpa": 3.45,
      "standing": "Good Standing",
      "stars": "★★★★",
      "gpa_credits": 117,
      "waiver": {
        "name": "Dean's Scholarship",
        "level": "25%"
      }
    },
    "level3": {
      "program_name": "BSc in Computer Science",
      "mandatory_completed": 18,
      "mandatory_total": 22,
      "mandatory_progress": 81.8,
      "graduation_ready": false,
      "mandatory_missing": ["CSE400", "CSE499", "CSE489", "CSE498"]
    },
    "courses": [...],
    "semesters": [...]
  }
}
```

---

### Auth Config (for frontend)

```http
GET /auth/config
```

Get Supabase configuration for frontend OAuth.

**Response:**
```json
{
  "success": true,
  "config": {
    "supabase_url": "https://xxx.supabase.co",
    "supabase_key": "eyJ...",
    "google_client_id": "xxx.apps.googleusercontent.com"
  }
}
```

---

### Google/CLI Auth

```http
POST /auth/google
Content-Type: application/json
```

Simple email-based authentication (for CLI/mobile).

**Body:**
```json
{
  "email": "user@example.com",
  "name": "User Name",
  "provider": "cli"
}
```

**Response:**
```json
{
  "success": true,
  "token": "abc123...",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "User Name"
  }
}
```

---

### Get Current User

```http
GET /auth/user
Authorization: Bearer {token}
```

Get current user info and sync to database.

**Response:**
```json
{
  "success": true,
  "user": {
    "id": "supabase-user-id",
    "db_id": "database-user-id",
    "email": "user@example.com",
    "name": "User Name",
    "stats": {
      "total_scans": 5,
      "avg_cgpa": 3.52
    }
  }
}
```

---

### Scan History

```http
GET /history
Authorization: Bearer {token}
```

Get user's scan history.

**Query Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| limit | int | 50 | Max scans to return |

**Response:**
```json
{
  "success": true,
  "count": 3,
  "history": [
    {
      "id": "scan-uuid",
      "filename": "transcript.pdf",
      "total_courses": 45,
      "total_credits": 120,
      "cgpa": 3.45,
      "source": "web",
      "created_at": "2026-03-31T12:00:00Z"
    }
  ]
}
```

---

### Get Scan Details

```http
GET /history/{scan_id}
Authorization: Bearer {token}
```

Get full analysis data for a specific scan.

**Response:**
```json
{
  "success": true,
  "scan": {
    "id": "scan-uuid",
    "filename": "transcript.pdf",
    "analysis_data": {
      "level1": {...},
      "level2": {...},
      "level3": {...}
    }
  }
}
```

---

### Delete Scan

```http
DELETE /history/{scan_id}
Authorization: Bearer {token}
```

Delete a scan from history (only owner can delete).

**Response:**
```json
{
  "success": true,
  "message": "Scan deleted"
}
```

---

## Code Examples

### Complete JavaScript Example

```javascript
class NSUDegreeAuditClient {
  constructor() {
    this.baseUrl = 'https://ocrapi.nsunexus.app';
    this.token = null;
  }

  async login(email, name) {
    const response = await fetch(`${this.baseUrl}/auth/google`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, name, provider: 'api' })
    });
    const data = await response.json();
    if (data.success) {
      this.token = data.token;
      return data.user;
    }
    throw new Error(data.error);
  }

  async scanTranscript(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${this.baseUrl}/upload`, {
      method: 'POST',
      body: formData,
      headers: this.token ? { 'Authorization': `Bearer ${this.token}` } : {}
    });
    
    return response.json();
  }

  async getHistory() {
    const response = await fetch(`${this.baseUrl}/history`, {
      headers: { 'Authorization': `Bearer ${this.token}` }
    });
    return response.json();
  }
}

// Usage
const client = new NSUDegreeAuditClient();
await client.login('user@nsu.edu', 'Student Name');
const result = await client.scanTranscript(pdfFile);
console.log('CGPA:', result.data.level2.cgpa);
```

### Complete Python Example

```python
import requests

class NSUDegreeAuditClient:
    def __init__(self):
        self.base_url = 'https://ocrapi.nsunexus.app'
        self.token = None
    
    def login(self, email, name='API User'):
        response = requests.post(
            f'{self.base_url}/auth/google',
            json={'email': email, 'name': name, 'provider': 'api'}
        )
        data = response.json()
        if data.get('success'):
            self.token = data['token']
            return data['user']
        raise Exception(data.get('error', 'Login failed'))
    
    def scan_transcript(self, file_path):
        headers = {}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(
                f'{self.base_url}/upload',
                files=files,
                headers=headers
            )
        return response.json()
    
    def get_history(self, limit=50):
        response = requests.get(
            f'{self.base_url}/history',
            params={'limit': limit},
            headers={'Authorization': f'Bearer {self.token}'}
        )
        return response.json()

# Usage
client = NSUDegreeAuditClient()
client.login('user@nsu.edu', 'Student Name')
result = client.scan_transcript('transcript.pdf')
print(f"CGPA: {result['data']['level2']['cgpa']}")
print(f"Graduation Ready: {result['data']['level3']['graduation_ready']}")
```

---

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad request (invalid file, missing parameters) |
| 401 | Authentication required |
| 403 | Access denied (not owner) |
| 404 | Resource not found |
| 500 | Server error |
| 503 | Database unavailable |

## Rate Limits

- OCR.space: 500 requests/month (free tier)
- Google Vision: 1000 requests/month (free tier)
- No limit on API requests (fair use policy)
