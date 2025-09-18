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

---

# Profile Management Endpoints

This section documents the Profile CRUD endpoints provided by the user service. Schemas referenced below are defined in `src/nta_user_svc/schemas/profile.py` (ProfileCreate, ProfileUpdate, ProfileOut, ProfilePublic).

Common profile fields (from ProfileCreate/ProfileUpdate):
- name: string (optional)
- phone: string (optional) - expected format: "+<country_code><number>" (e.g. "+1234567890")
- bio: string (optional)
- hobby: string (optional)
- occupation: string (optional)
- location: string (optional)

Common error body format (examples):
- HTTPException-based errors use: { "detail": "<message>" }
- Validation errors from FastAPI/Pydantic produce 422 responses with a `detail` array (see `test_validation_errors_for_post_and_put`).

Security (general):
- All profile endpoints require JWT authentication via the Authorization header unless otherwise noted.
- Header format: Authorization: Bearer <JWT_TOKEN>
- JWT settings are described in the README (JWT_SECRET, JWT_ALGORITHM, JWT_EXP_HOURS).

---

## POST /api/profiles

Path: /api/profiles
Method: POST
Security: Requires Authorization: Bearer <JWT>

Description:
Create a profile for the authenticated user. Each user may only have one profile. If a profile already exists a 409 Conflict is returned.

Request (application/json) - body schema: ProfileCreate
Example:
{
  "name": "Alice",
  "phone": "+100200300",
  "bio": "Hello, I like hiking.",
  "hobby": "hiking",
  "occupation": "Engineer",
  "location": "San Francisco"
}

Success Response (201 Created) - schema: ProfileOut
Example:
{
  "id": 1,
  "user_id": 42,
  "email": "alice@example.com",
  "name": "Alice",
  "phone": "+100200300",
  "bio": "Hello, I like hiking.",
  "hobby": "hiking",
  "occupation": "Engineer",
  "location": "San Francisco",
  "profile_photo_path": null,
  "created_at": "2025-01-01T00:00:00",
  "updated_at": "2025-01-01T00:00:00"
}

Common Error Responses:
- 400 Bad Request: Invalid input (e.g., phone format). Example: { "detail": "Invalid phone format; expected +<country_code><number>" }
- 401 Unauthorized: Missing or invalid token. Example: { "detail": "Not authenticated" }
- 409 Conflict: Profile already exists. Example: { "detail": "Profile already exists" }
- 500 Internal Server Error: Unexpected error. Example: { "detail": "Internal server error" }

Notes:
- The endpoint uses the current authenticated user's id as the profile owner.
- See `ProfileCreate` definition in `src/nta_user_svc/schemas/profile.py` for exact validation rules, including phone format.

---

## GET /api/users/me/profile

Path: /api/users/me/profile
Method: GET
Security: Requires Authorization: Bearer <JWT>

Description:
Retrieve the authenticated user's own profile. This returns the full `ProfileOut` view (includes the user's email).

Success Response (200 OK) - schema: ProfileOut
Example:
{
  "id": 2,
  "user_id": 42,
  "email": "alice@example.com",
  "name": "Alice",
  "phone": "+100200300",
  "bio": "Hello, I like hiking.",
  "hobby": "hiking",
  "occupation": "Engineer",
  "location": "San Francisco",
  "profile_photo_path": "uploads/42/123e4567.jpg",
  "created_at": "2025-01-01T00:00:00",
  "updated_at": "2025-01-02T12:00:00"
}

Common Error Responses:
- 401 Unauthorized: Missing or invalid token. Example: { "detail": "Not authenticated" }
- 404 Not Found: Profile not found for authenticated user. Example: { "detail": "Profile not found" }
- 500 Internal Server Error: Unexpected error. Example: { "detail": "Internal server error" }

Notes:
- Tests exercise this endpoint using `/api/users/me/profile` (see `tests/test_profiles_api.py`).

---

## GET /api/profiles/{user_id}

Path: /api/profiles/{user_id}
Method: GET
Security: Requires Authorization: Bearer <JWT>

Description:
Get the public view of a user's profile by user_id. The public view excludes the user's email address and exposes only fields in `ProfilePublic`.

Path Parameters:
- user_id (int): ID of the user whose public profile is requested.

Success Response (200 OK) - schema: ProfilePublic
Example:
{
  "id": 2,
  "user_id": 42,
  "name": "Alice",
  "phone": "+100200300",
  "bio": "Hello, I like hiking.",
  "hobby": "hiking",
  "occupation": "Engineer",
  "location": "San Francisco",
  "profile_photo_path": "uploads/42/123e4567.jpg",
  "created_at": "2025-01-01T00:00:00",
  "updated_at": "2025-01-02T12:00:00"
}

Common Error Responses:
- 401 Unauthorized: Missing or invalid token. Example: { "detail": "Not authenticated" }
- 404 Not Found: Profile not found for the requested user_id. Example: { "detail": "Profile not found" }
- 500 Internal Server Error: Unexpected error. Example: { "detail": "Internal server error" }

Notes:
- Although this is a "public profile" view (no email), the endpoint currently requires authentication to access (see router implementation). If you require truly public access in the future, update the route dependencies accordingly and reflect this in the docs.

---

## PUT /api/profiles/me

Path: /api/profiles/me
Method: PUT
Security: Requires Authorization: Bearer <JWT>

Description:
Update the authenticated user's profile. Accepts the same fields as `ProfileUpdate`; partial updates are allowed (fields not provided are left unchanged).

Request (application/json) - body schema: ProfileUpdate
Example:
{
  "bio": "Updated bio",
  "location": "New City"
}

Success Response (200 OK) - schema: ProfileOut
Example:
{
  "id": 2,
  "user_id": 42,
  "email": "alice@example.com",
  "name": "Alice",
  "phone": "+100200300",
  "bio": "Updated bio",
  "hobby": "hiking",
  "occupation": "Engineer",
  "location": "New City",
  "profile_photo_path": null,
  "created_at": "2025-01-01T00:00:00",
  "updated_at": "2025-01-03T08:00:00"
}

Common Error Responses:
- 400 Bad Request: Invalid input (e.g., invalid phone format). Example: { "detail": "Invalid phone format; expected +<country_code><number>" }
- 401 Unauthorized: Missing or invalid token. Example: { "detail": "Not authenticated" }
- 404 Not Found: Profile not found for authenticated user. Example: { "detail": "Profile not found" }
- 500 Internal Server Error: Unexpected error. Example: { "detail": "Internal server error" }
- 422 Unprocessable Entity: Pydantic validation errors (e.g., incorrect types) - FastAPI returns a structured `detail` array.

Notes:
- Validation rules (e.g., phone format, max lengths) are enforced by Pydantic validators in `src/nta_user_svc/schemas/profile.py`.

---

## DELETE /api/profiles/me

Path: /api/profiles/me
Method: DELETE
Security: Requires Authorization: Bearer <JWT>

Description:
Delete the authenticated user's profile. The deletion also triggers cleanup of profile photo files via service listeners.

Success Response (204 No Content):
- No response body.

Common Error Responses:
- 401 Unauthorized: Missing or invalid token. Example: { "detail": "Not authenticated" }
- 404 Not Found: Profile not found for authenticated user. Example: { "detail": "Profile not found" }
- 500 Internal Server Error: Unexpected error. Example: { "detail": "Internal server error" }

Notes:
- Deletion attempts to remove associated profile photo files; file-removal errors are logged and do not cause the deletion to fail. See `src/nta_user_svc/services/profile_photo_service.py` for the cleanup behavior.

---

# Schema references
- ProfileCreate / ProfileUpdate: `src/nta_user_svc/schemas/profile.py` (fields: name, phone, bio, hobby, occupation, location)
- ProfileOut: `src/nta_user_svc/schemas/profile.py` (includes id, user_id, email, profile_photo_path, created_at, updated_at)
- ProfilePublic: `src/nta_user_svc/schemas/profile.py` (same as ProfileOut but excludes email)

# Notes for integrators
- All endpoints expect JSON bodies where applicable and return JSON responses for success/error cases (except DELETE which returns 204 No Content).
- Include Authorization header for all endpoints as documented. Tokens are produced by `/api/auth/login`.
- Use the schemas in `src/nta_user_svc/schemas/profile.py` as the canonical source of truth when building clients or generating typed SDKs.
