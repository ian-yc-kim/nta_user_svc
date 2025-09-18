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
