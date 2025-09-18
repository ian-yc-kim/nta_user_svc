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
