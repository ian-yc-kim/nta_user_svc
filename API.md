## POST /api/auth/register

Path: /api/auth/register
Method: POST

Request (application/json):
{
  "email": "user@example.com",
  "password": "StrongPass123"
}

Success Response (201 Created):
{
  "id": 1,
  "email": "user@example.com",
  "created_at": "2025-01-01T00:00:00"
}

Error Responses:
- 400 Bad Request: Validation failure (e.g., invalid email format) or weak password. The response detail contains a descriptive message (e.g., "Password must be at least 8 characters long.").
- 409 Conflict: Duplicate email. Example detail: "Email already registered.".

Notes:
- The registration endpoint creates both a User and an associated Profile record atomically.
- Passwords are validated using the service's password strength rules and are hashed using bcrypt before storage.

---

## POST /api/auth/login

Path: /api/auth/login
Method: POST

Request (application/json):
{
  "email": "user@example.com",
  "password": "StrongPass123"
}

Success Response (200 OK):
{
  "access_token": "<JWT_TOKEN_HERE>",
  "token_type": "bearer"
}

Error Responses:
- 401 Unauthorized: Authentication failure. The service returns a non-revealing message: "Incorrect email or password". This prevents leaking whether an account with the given email exists.
- 500 Internal Server Error: Unexpected server error (e.g., DB failure or token creation failure).

Notes:
- The login endpoint performs the following steps:
  1. Lookup user by email.
  2. Verify the provided password against the stored bcrypt hash.
  3. On success, issue a JWT access token (contains user_id and exp claim).
- Extensibility (Rate-limiting): A TODO marker is present in `src/nta_user_svc/routers/auth.py` at the start of the `login` function indicating where to integrate rate-limiting to mitigate brute-force attacks. The actual implementation is out of scope for this change. When implemented, prefer a production-grade store (e.g., Redis) for counters and consider both per-IP and per-account strategies with exponential backoff.
