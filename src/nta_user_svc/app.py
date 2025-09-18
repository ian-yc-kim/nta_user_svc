from fastapi import FastAPI
import logging

from nta_user_svc.routers import users_router, auth_router, photos_router

from nta_user_svc.services import init_profile_photo_cleanup_listeners

app = FastAPI(debug=True)

# include routers
app.include_router(users_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(photos_router, prefix="/api")


@app.on_event("startup")
def _startup_event() -> None:
    try:
        init_profile_photo_cleanup_listeners()
    except Exception as e:
        # Log but do not prevent application startup
        logging.error("Failed to init profile photo cleanup listeners on startup", exc_info=True)
