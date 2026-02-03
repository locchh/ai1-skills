# OWASP Top 10 (2021) Quick-Reference Checklist

Security review checklist with Python (FastAPI) and React specific mitigations.
Use this as a rapid go/no-go reference during pull request reviews.

## A01: Broken Access Control

- [ ] Every endpoint has authentication (`Depends(get_current_user)` or middleware)
- [ ] Resource ownership is validated (queries filter by `current_user.id`)
- [ ] IDOR prevented: IDs in URLs are cross-checked against the authenticated user
- [ ] Role-based access control enforced on admin and privileged endpoints
- [ ] Path traversal blocked: user filenames resolved with `Path.resolve()` + `is_relative_to()`
- [ ] React: protected routes use an auth guard component; server enforces access

## A02: Cryptographic Failures

- [ ] Passwords hashed with bcrypt (cost >= 12), scrypt, or Argon2 -- never MD5/SHA
- [ ] Tokens and nonces generated with `secrets.token_urlsafe()`, not `random`
- [ ] No hardcoded secrets: API keys, passwords, tokens loaded from env vars
- [ ] Sensitive data at rest encrypted where required
- [ ] All external communication over HTTPS; no `http://` URLs in production config
- [ ] TLS certificates valid and not near expiration

## A03: Injection

- [ ] SQL queries use parameterized statements or ORM (no f-strings, `.format()`, `%` in SQL)
- [ ] `subprocess.run()` uses list arguments, never `shell=True` with user input
- [ ] No `eval()`, `exec()`, or `__import__()` with external input
- [ ] No `pickle.loads()` or `yaml.load()` on untrusted data (`yaml.safe_load()` is acceptable)
- [ ] React: no `dangerouslySetInnerHTML` without DOMPurify sanitization
- [ ] React: no `javascript:` URLs; validate URL scheme before rendering links
- [ ] Template engines receive user input as variables, not as template source

## A04: Insecure Design

- [ ] Rate limiting on login, password reset, registration, and search endpoints
- [ ] Input length and format validated with Pydantic `Field()` constraints
- [ ] File uploads restricted by extension allowlist, MIME validation, and size limit
- [ ] Business logic limits enforced (max items, cooldowns, confirmation for destructive actions)

## A05: Security Misconfiguration

- [ ] `DEBUG=False` in production; no verbose error messages returned to clients
- [ ] CORS restricted to specific origins; no `allow_origins=["*"]` with credentials
- [ ] Default/placeholder secrets (`changeme`, `secret`, `xxx`) replaced
- [ ] Security headers present: HSTS, CSP, X-Content-Type-Options, X-Frame-Options
- [ ] Internal endpoints (health, metrics, admin) protected or not publicly exposed

## A06: Vulnerable and Outdated Components

- [ ] `safety check` or `pip-audit` run on Python dependencies -- no HIGH/CRITICAL CVEs
- [ ] `npm audit` run on JavaScript dependencies -- no HIGH/CRITICAL CVEs
- [ ] Dependencies pinned with lockfiles (`package-lock.json`, `requirements.txt`)
- [ ] No dependency more than 2 major versions behind latest
- [ ] No unmaintained dependency (12+ months without commits)

## A07: Identification and Authentication Failures

- [ ] JWT tokens include `exp`, `iat`, and `jti` claims
- [ ] JWT decode pins the algorithm (`algorithms=["HS256"]`)
- [ ] Session ID rotated after login; session invalidated on logout
- [ ] Session cookies have `HttpOnly`, `Secure`, and `SameSite` attributes
- [ ] Password requirements enforce minimum length (>= 8) and complexity
- [ ] Brute-force protection via rate limiting or account lockout on auth endpoints

## A08: Software and Data Integrity Failures

- [ ] CSRF protection in place for cookie-based auth (tokens or SameSite cookies)
- [ ] Server-side validation of all client-modifiable data (cookies, URL params, hidden fields)
- [ ] Deserialization uses safe methods: Pydantic, `json.loads()`, `yaml.safe_load()`
- [ ] CI/CD pipeline integrity: dependencies pulled from trusted registries, lockfiles verified

## A09: Security Logging and Monitoring Failures

- [ ] No secrets, passwords, or tokens in log output
- [ ] Authentication events logged (login, logout, failed login) with user ID and IP
- [ ] Authorization failures logged
- [ ] Logs include request ID for traceability
- [ ] Alerting configured for anomalous patterns (burst of 401s, unusual traffic)

## A10: Server-Side Request Forgery (SSRF)

- [ ] User-supplied URLs validated against a domain allowlist
- [ ] URL scheme restricted to `https://`
- [ ] Internal/private IP ranges blocked (10.x, 172.16-31.x, 192.168.x, 127.x, 169.254.x)
- [ ] Redirect following disabled or limited when fetching external URLs
- [ ] DNS rebinding mitigated by resolving and re-validating the IP before connecting

---

**Usage:** Copy this checklist into your PR review comment and check off each item.
Items left unchecked are potential findings that need investigation.
