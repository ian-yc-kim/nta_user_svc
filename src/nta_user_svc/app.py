from fastapi import FastAPI

from nta_user_svc.routers import users_router, auth_router

app = FastAPI(debug=True)

# include routers
app.include_router(users_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
