# nta_user_svc

## Configuration / Environment Variables

This service reads configuration from environment variables. Important configuration for password security:

- `PASSWORD_HASH_ROUNDS` (int): Number of bcrypt log rounds (the bcrypt "cost") used to hash user passwords.
  - Default: `12` (used when the environment variable is not set or invalid).
  - Recommendation: `12` or higher for production. Increasing this value strengthens password hashing at the cost of CPU/time. Choose based on your hardware and throughput requirements.

Behavioral notes:
- The application attempts to parse `PASSWORD_HASH_ROUNDS` as an integer. If the value is missing or invalid, the application logs an error and falls back to `12`.
- After changing this environment variable, restart the service so the new value is used.

Examples

Example .env file:

PASSWORD_HASH_ROUNDS=12
# other env variables...

Example docker-compose snippet:

services:
  nta_user_svc:
    image: nta_user_svc:latest
    environment:
      - PASSWORD_HASH_ROUNDS=14

Security note

- Passwords are hashed using bcrypt. Higher `PASSWORD_HASH_ROUNDS` increases security but also CPU cost during registration and authentication. Test and tune the value for your deployment.

### JWT Configuration

This service uses JSON Web Tokens (JWT) for authentication. The following environment variables control JWT behavior (these are required/used by `src/nta_user_svc/config.py`):

- `JWT_SECRET` (string) — REQUIRED
  - Secret key used to sign and verify JWTs. The application fails fast and raises an error at startup if this variable is not set.
  - Recommendation: Use a long, random secret (at least 32 bytes) and protect it using your platform's secret management (do not commit it to version control).

- `JWT_ALGORITHM` (string) — Optional, default: `HS256`
  - Signing algorithm used by PyJWT. Default is HS256.

- `JWT_EXP_HOURS` (int) — Optional, default: `24`
  - Token expiration time in hours. Tokens include an `exp` claim set to the current time plus this value.

Example `.env` (development only — do NOT commit real secrets):

```
# Development example
JWT_SECRET=test-secret-key
JWT_ALGORITHM=HS256
JWT_EXP_HOURS=24
```

Example docker-compose snippet:

```
services:
  nta_user_svc:
    environment:
      - JWT_SECRET=${JWT_SECRET}
      - JWT_ALGORITHM=HS256
      - JWT_EXP_HOURS=24
```

Security guidance:
- Use a dedicated secret management solution in production (e.g., AWS Secrets Manager, HashiCorp Vault, Kubernetes Secrets).
- Rotate `JWT_SECRET` periodically and plan rolling restarts for services that validate tokens.
- Keep `JWT_EXP_HOURS` as low as practical for your use case; shorter lifetimes reduce risk from leaked tokens.

Notes:
- The application performs a fail-fast check for `JWT_SECRET` in `src/nta_user_svc/config.py` to avoid insecure runs without a signing key.

### Profile photo storage

This service supports storing user profile photos on disk. The storage and upload behavior is controlled by two environment variables:

- `PROFILE_PHOTO_DIR` (string) — directory where uploaded profile photos are stored.
  - Default: `/var/lib/nta_user_svc_uploads`
  - Purpose: Root directory under which per-user subdirectories are created. Files are stored under `{PROFILE_PHOTO_DIR}/{user_id}/{uuid}.{ext}`.

- `MAX_PHOTO_SIZE_BYTES` (int) — maximum allowed file size in bytes for uploaded profile photos.
  - Default: `1048576` (1 MiB)
  - Purpose: Prevent excessively large uploads. If a file exceeds this size the API will return `400 Bad Request`.

Example `.env` entries (development):

```
PROFILE_PHOTO_DIR=/var/lib/nta_user_svc_uploads
MAX_PHOTO_SIZE_BYTES=1048576
```

Docker-compose snippet:

```yaml
services:
  nta_user_svc:
    environment:
      - PROFILE_PHOTO_DIR=${PROFILE_PHOTO_DIR}
      - MAX_PHOTO_SIZE_BYTES=${MAX_PHOTO_SIZE_BYTES}
```

Notes and behavior:

- Allowed image formats: JPEG (.jpg/.jpeg), PNG (.png), and WEBP (.webp). The service validates both the reported MIME type and the actual image content using Pillow.
- Files are stored under a per-user directory: `{PROFILE_PHOTO_DIR}/{user_id}/` and file names are a generated UUID with the appropriate extension (e.g. `123e4567abcd.jpg`).
- Uploads are performed with atomic semantics: the new file is saved to disk first, then the database is updated. If the DB update fails the newly saved file is removed. If the DB update succeeds the previous file is removed (failures deleting the old file are logged but do not fail the request).
- The service attempts to create the directory if it does not exist and set restrictive permissions (0o700) where the platform supports it. On some platforms (e.g., Windows) chmod may be ineffective.
- The service prevents path traversal and only exposes files that are descendants of `PROFILE_PHOTO_DIR`.
- Size limits are enforced by `MAX_PHOTO_SIZE_BYTES`. Increasing this value in production requires considering storage and bandwidth implications.

Developer notes / Running tests:

- The file-storage tests live in `tests/test_file_storage.py` and `tests/test_photos.py`. They use pytest fixtures and monkeypatch `PROFILE_PHOTO_DIR` to a `tmp_path`.
- To run only the photo-related tests:

```
poetry install
poetry run pytest tests/test_file_storage.py tests/test_photos.py -q
```

- Ensure dependencies (Pillow, python-multipart) are installed — they are declared in `pyproject.toml`.

- Tests use the provided fixtures in `tests/conftest.py`; do not create separate DB or TestClient fixtures when running tests locally.


## Profile Management

This service exposes Profile CRUD endpoints for managing user profiles. Full API documentation for the profile endpoints (including request/response examples and errors) is available in `API.md` under the "Profile Management Endpoints" section.

Quick summary of endpoints:
- Create profile: POST /api/profiles (requires JWT)
- Get own profile: GET /api/users/me/profile (requires JWT)
- Get public profile: GET /api/profiles/{user_id} (requires JWT, returns public view excluding email)
- Update profile: PUT /api/profiles/me (requires JWT)
- Delete profile: DELETE /api/profiles/me (requires JWT)

Developer notes for profile features:
- Environment variables affecting profile/photo features:
  - PROFILE_PHOTO_DIR: directory for profile photo storage (default `/var/lib/nta_user_svc_uploads`). Tests override this to a tmp path.
  - MAX_PHOTO_SIZE_BYTES: maximum photo upload size (default 1048576 bytes).
- Authentication: All profile endpoints require a valid JWT. Configure `JWT_SECRET` and related JWT env variables before running integration tests.
- Running profile-related tests:

```
poetry install
poetry run pytest tests/test_profiles_api.py -q
```

- When modifying `PROFILE_PHOTO_DIR` for local development, ensure the directory is writable by the test/process user and that you update Docker compose or .env accordingly.

- Note on "public profile": currently, the public profile endpoint requires authentication (it returns `ProfilePublic` which excludes email). If you need truly unauthenticated access to public profiles, update the router dependency and document the change in `API.md` and README.


