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

---

## POST /api/auth/login

Authenticate a user and return a JWT access token.

- Path: `/api/auth/login`
- Method: `POST`
- Authentication: none (public)

Request

- Content-Type: `application/json`
- Body schema:
  - `email` (string): valid email address
  - `password` (string): user's password

Example request payload

```
{
  "email": "user@example.com",
  "password": "MyStrongPass123"
}
```

Example curl

```
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"MyStrongPass123"}'
```

Success Response

- HTTP Status: `200 OK`
- Body (application/json):
  - `access_token` (string): JWT access token
  - `token_type` (string): `bearer`

Example

```
{
  "access_token": "<JWT_TOKEN>",
  "token_type": "bearer"
}
```

Error Responses

- `401 Unauthorized` — incorrect email or password

  Example:
  ```json
  {
    "detail": "Incorrect email or password"
  }
  ```

- `500 Internal Server Error` — server error while authenticating or creating token


## GET /api/auth/me

Return basic information about the authenticated user.

- Path: `/api/auth/me`
- Method: `GET`
- Authentication: Bearer token required (protected endpoint)

Headers

```
Authorization: Bearer <access_token>
```

Success Response

- HTTP Status: `200 OK`
- Body:
```
{
  "id": 1,
  "email": "user@example.com"
}
```


## Authentication / Protected Endpoints

How to authenticate requests:

1. Obtain an access token by POSTing valid credentials to `/api/auth/login`.
2. Include the token in the `Authorization` header for protected requests:

```
Authorization: Bearer <access_token>
```

Expected behavior:

- Valid token: the request will succeed and the authenticated user is injected into the request handler (e.g., `/api/auth/me`).
- Expired token: the API returns `401 Unauthorized`. The response includes the header `WWW-Authenticate: Bearer`.
- Invalid/tampered token: the API returns `401 Unauthorized`.
- Token containing a `user_id` that does not exist in the database: the API returns `401 Unauthorized`.

Notes:
- Tokens are signed with `JWT_SECRET` using algorithm `JWT_ALGORITHM` and include an `exp` claim controlled by `JWT_EXP_HOURS`.
- The implementation uses FastAPI's OAuth2PasswordBearer scheme and raises appropriate `401` responses for invalid credentials or tokens.
