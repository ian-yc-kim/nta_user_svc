## User Registration

POST /api/auth/register

Request:
{
  "email": "user@example.com",
  "password": "StrongPass123"
}

Response (201):
{
  "id": 1,
  "email": "user@example.com",
  "created_at": "2025-01-01T00:00:00"
}

Notes:
- The registration endpoint creates both a User and an associated Profile record atomically.
- Duplicate emails return 409 Conflict with detail "Email already registered.".
- Weak passwords return 400 Bad Request with a descriptive detail message explaining password requirements.

