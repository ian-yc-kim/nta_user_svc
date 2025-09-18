# API Reference

## POST /api/users/register

Register a new user.

- Path: `/api/users/register`
- Method: `POST`
- Authentication: none (public endpoint)

Request

- Content-Type: `application/json`
- Body schema:
  - `email` (string): valid email address (validated using pydantic / email-validator).
  - `password` (string): password meeting service requirements.

Password validation rules (exact rules enforced by the service):
- Minimum 8 characters
- Must contain at least one letter
- Must contain at least one number

Example request payload

{
  "email": "user@example.com",
  "password": "MyStrongPass123"
}

Example curl

curl -X POST "http://localhost:8000/api/users/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"MyStrongPass123"}'

Success Response

- HTTP Status: `201 Created`
- Body (application/json):
  - `id` (int): newly created user id
  - `email` (string)
  - `created_at` (string, optional ISO datetime)

Example

{
  "id": 1,
  "email": "user@example.com",
  "created_at": "2025-09-18T12:34:56.789Z"
}

Notes:
- The API intentionally does not return passwords or hashed passwords.
- Internally the password is hashed using bcrypt; the number of rounds is controlled by `PASSWORD_HASH_ROUNDS` (see README).

Error Responses

1) `400 Bad Request` — validation error (invalid email or weak password)

- Example when password is too short:

Status: 400
Body:
{
  "detail": "Password must be at least 8 characters long."
}

- Example when password has no letter:

Status: 400
Body:
{
  "detail": "Password must contain at least one letter."
}

- Example when password has no number:

Status: 400
Body:
{
  "detail": "Password must contain at least one number."
}

Note: FastAPI may also return standard validation errors for malformed requests with the usual `detail` validation structure.

2) `409 Conflict` — duplicate email

- Returned when an account with the provided email already exists.

Example:

Status: 409
Body:
{
  "detail": "Email already registered."
}

3) `500 Internal Server Error` — server-side errors

- Example: failure while hashing the password or unexpected DB error. The body will contain a general error detail, e.g.:

Status: 500
Body:
{
  "detail": "Internal server error"
}

Implementation details

- Password strength is validated by the service before hashing. Exact validation rules are listed above and implemented in the codebase.
- Password hashing uses bcrypt and the work factor is set by the `PASSWORD_HASH_ROUNDS` environment variable (see README).
