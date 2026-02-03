---
name: code-review-security
description: >-
  Security-focused code review checklist and automated scanning patterns. Use when
  reviewing pull requests for security issues, auditing authentication/authorization code,
  checking for OWASP Top 10 vulnerabilities, or validating input sanitization. Covers
  SQL injection prevention, XSS protection, CSRF tokens, authentication flow review,
  secrets detection, dependency vulnerability scanning, and secure coding patterns for
  Python (FastAPI) and React. Does NOT cover deployment security (use docker-best-practices)
  or incident handling (use incident-response).
license: MIT
compatibility: 'Python 3.12+, FastAPI 0.115+, React 18+, bandit, safety, eslint-plugin-security'
metadata:
  author: platform-team
  version: '1.0.0'
  sdlc-phase: code-review
allowed-tools: Read Grep Glob Bash(bandit:*) Bash(safety:*) Bash(npm:audit)
context: fork
---

# Code Review Security

Security-focused code review skill for Python (FastAPI) and React applications. Provides
a systematic checklist based on the OWASP Top 10 (2021), language-specific vulnerability
patterns, automated scanning integration, and structured reporting. Every finding includes
severity, evidence, and a concrete fix recommendation.

See `scripts/security-scan.py` for automated scanning.

## When to Use

Use this skill when:

- **Reviewing a pull request** that touches authentication, authorization, user input handling, database queries, or external API integrations
- **Auditing authentication and authorization code** for correctness and completeness
- **Checking for OWASP Top 10 vulnerabilities** during scheduled security reviews or pre-release audits
- **Validating input sanitization** on new API endpoints or form handlers
- **Scanning for hardcoded secrets** before code reaches the main branch
- **Evaluating dependency security** for newly added or updated packages

Do **NOT** use this skill for:

- Container or infrastructure security hardening -- use `docker-best-practices` instead
- Production incident investigation or response -- use `incident-response` instead
- General code quality checks (linting, formatting, tests) -- use `pre-merge-checklist` instead
- Writing security tests -- use `pytest-patterns` or `e2e-testing` instead

## Instructions

### OWASP Top 10 Checklist

Walk through each applicable OWASP Top 10 (2021) category for every security review. See `references/owasp-checklist.md` for the quick-reference version.

#### A01: Broken Access Control

**Python / FastAPI checks:**

- Every endpoint serving user-specific data has `Depends(get_current_user)` or equivalent authentication dependency.
- Resource ownership is validated: the authenticated user owns the requested resource, or has an admin role.
- IDOR (Insecure Direct Object Reference) is prevented by filtering queries with `current_user.id`, not trusting client-supplied IDs alone.
- Path traversal is blocked: any user-supplied filename is resolved with `Path.resolve()` and checked with `is_relative_to()`.

```python
# VULNERABLE: No ownership check (IDOR)
@router.get("/orders/{order_id}")
async def get_order(order_id: int, db: Session = Depends(get_db)):
    return db.query(Order).get(order_id)

# SECURE: Ownership verified
@router.get("/orders/{order_id}")
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == current_user.id).first()
    if not order:
        raise HTTPException(status_code=404)
    return order
```

**React checks:** Protected routes must use an auth guard component. Client-side role checks must be backed by server-side enforcement. Admin panels must derive roles from the auth context, never from URL parameters or local storage.

#### A02: Cryptographic Failures

- Passwords hashed with bcrypt (cost >= 12), scrypt, or Argon2. Never MD5, SHA-1, or plain SHA-256.
- Tokens and nonces use `secrets.token_urlsafe()`, not `random`.
- No hardcoded secrets -- all credentials from environment variables or a secrets manager.
- All external communications use HTTPS. Flag any `http://` URL in production config.

#### A03: Injection

Covered in detail under SQL Injection Prevention and XSS Prevention sections below. Additional vectors: command injection (`shell=True`), template injection, `eval()`/`exec()`.

#### A04: Insecure Design

- Rate limiting on authentication, password reset, and resource-creation endpoints.
- Business logic limits: max file upload size, max records per request, cooldowns on sensitive actions.

#### A05: Security Misconfiguration

- `DEBUG=True` never set in production. CORS restricted to specific origins (no wildcard with credentials). Default/placeholder secrets flagged. Security headers present (HSTS, CSP, X-Content-Type-Options, X-Frame-Options).

#### A06: Vulnerable Components

- Run `safety check` (Python) and `npm audit` (JavaScript) on every review. Flag HIGH/CRITICAL CVEs.
- Dependencies pinned with lockfiles. Unmaintained or outdated dependencies flagged.

#### A07-A10: Authentication, Integrity, Logging, SSRF

- **A07**: See Authentication Review section. **A08**: CSRF protection for cookie-based auth; safe deserialization only. **A09**: No secrets in logs; auth events logged with user ID and IP. **A10**: User-supplied URLs validated against domain allowlist; internal IPs blocked.

### SQL Injection Prevention

**Safe patterns (always use these):**

```python
# SQLAlchemy ORM (automatically parameterized)
user = db.query(User).filter(User.email == email).first()

# SQLAlchemy text() with bind parameters
result = db.execute(text("SELECT * FROM users WHERE email = :email"), {"email": email})

# SQLAlchemy Core expressions
stmt = select(User).where(User.email == email)
```

**Dangerous patterns (flag immediately):**

```python
# CRITICAL: f-string, .format(), concatenation, or % formatting in SQL
db.execute(text(f"SELECT * FROM users WHERE email = '{email}'"))
db.execute(text("SELECT * FROM users WHERE email = '{}'".format(email)))
```

### XSS Prevention

React auto-escapes string values in JSX by default. The primary risks are bypassing this escaping:

```tsx
// HIGH: dangerouslySetInnerHTML without sanitization
<div dangerouslySetInnerHTML={{ __html: userContent }} />

// SECURE: Sanitize first
import DOMPurify from 'dompurify';
<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(userContent) }} />

// SECURE: Let React auto-escape (preferred)
<div>{userContent}</div>
```

Flag `javascript:` URL schemes and validate all user-provided URLs with a scheme check. Verify Content Security Policy headers are configured -- flag `'unsafe-eval'` in `script-src`.

### Authentication Review

**JWT validation:**

```python
# VULNERABLE: No expiration, no algorithm restriction on decode
payload = {"sub": user_id}
token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
data = jwt.decode(token, SECRET_KEY)

# SECURE: Expiration, issued-at, unique ID, algorithm pinned
payload = {
    "sub": str(user_id),
    "exp": datetime.utcnow() + timedelta(minutes=30),
    "iat": datetime.utcnow(),
    "jti": str(uuid4()),
}
token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
```

**Session management:** Rotate session IDs after login. Expire sessions after idle timeout. Invalidate server-side on logout. Set `HttpOnly`, `Secure`, `SameSite` on session cookies.

**Password hashing:** Use bcrypt with cost factor >= 12. Never `hashlib.sha256()` for passwords.

### Authorization Review

**RBAC pattern:**

```python
def require_role(required_role: str):
    def dependency(current_user: User = Depends(get_current_user)):
        if current_user.role != required_role and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return dependency
```

**IDOR prevention checklist:** All queries for user-owned resources filter by `current_user.id`. Return 404 (not 403) when resource does not belong to user. Bulk operations filtered to authenticated user's scope.

### Input Validation

**Pydantic validation (FastAPI):**

```python
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=100, pattern=r'^[\w\s\-]+$')
    bio: str = Field(default="", max_length=500)
```

**File upload security:** Extension allowlist, size limit, MIME validation with `python-magic`, UUID-based storage filename. Never use user-supplied filename for storage.

**Rate limiting:** Apply `slowapi` or equivalent to login (`5/minute`), password reset (`3/hour`), and search endpoints.

### Secrets Management

```python
# CRITICAL: Hardcoded secret
SECRET_KEY = "my-super-secret-key-2024"

# SECURE: Environment variables or Pydantic settings
SECRET_KEY = os.environ["SECRET_KEY"]
```

Grep patterns: `grep -rn 'SECRET.*=.*"' --include="*.py" | grep -v 'os.environ\|os.getenv\|settings\.'`

Verify `.env` is in `.gitignore`. Run `git ls-files .env` to confirm it is not tracked.

### Dependency Scanning

```bash
# Python
safety check --full-report
pip-audit --strict --desc

# JavaScript
npm audit --audit-level=high
```

**Decision framework:** Critical + exploitable = block merge. Critical + not exploitable = fix within 48h. High + exploitable = block merge. Medium/Low = track in backlog.

## Examples

### Security Review of a Sample PR

```markdown
# Security Review: PR #287 - Add File Upload and User Search

## Summary
Reviewed 6 files. Found 4 issues (1 Critical, 1 High, 1 Medium, 1 Low).
Merge BLOCKED until Critical and High are resolved.

## Finding 1: SQL Injection in User Search
- **File**: `src/repositories/user_repo.py:89`
- **Type**: A03 Injection - SQL Injection
- **Severity**: Critical
- **Description**: f-string inside `text()` allows SQL injection via search parameter.
- **Fix**: Use bind parameters: `text("... WHERE name LIKE :name"), {"name": f"%{name}%"}`

## Finding 2: Unrestricted File Upload
- **File**: `src/routers/uploads.py:15`
- **Severity**: High
- **Fix**: Add extension allowlist, size limit, MIME validation, safe filename.

## Finding 3: Missing Rate Limit on Search
- **File**: `src/routers/users.py:34`
- **Severity**: Medium
- **Fix**: Add `@limiter.limit("30/minute")`.

## Finding 4: Stack Trace in Error Response
- **File**: `src/routers/uploads.py:22`
- **Severity**: Low
- **Fix**: Return generic error message; log exception server-side.
```

### Running the Automated Scanner

```bash
python scripts/security-scan.py src/
bandit -r src/ -ll --format json
safety check --full-report
cd frontend && npm audit --audit-level=high
```

## Edge Cases

### Third-Party Integrations

- **OAuth callback URLs** must be validated against a whitelist to prevent authorization code leakage via open redirect.
- **Webhook endpoints** must validate signatures. Never trust incoming webhooks without verification.
- **API keys for third-party services** must be in environment variables, not source code, and never logged.
- **External API responses** must be validated before use. Do not assume structure or safety.

```python
# SECURE: Validate webhook signature
def verify_webhook(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

### File Uploads

Defense in depth: (1) extension allowlist, (2) MIME validation with `python-magic`, (3) size limit at web server and application level, (4) UUID-based storage filename, (5) storage outside web root or in S3, (6) antivirus scanning for high-risk apps.

### WebSocket Security

- Authenticate during handshake (JWT in query parameter or first message).
- Validate every incoming message with a schema (Pydantic).
- Apply rate limiting on message frequency and enforce max message size.

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    try:
        user = verify_jwt_token(token)
    except InvalidTokenError:
        await websocket.close(code=4001, reason="Invalid token")
        return
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        if len(data) > MAX_MESSAGE_SIZE:
            await websocket.close(code=4002, reason="Message too large")
            return
        message = validate_ws_message(data)
        await handle_message(user, message)
```
