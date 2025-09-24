# api/app.py
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .routes import responses as responses_router

SERVE_SPA = os.getenv("SERVE_SPA", "false").lower() == "true"  # dev=false, prod=true

app = FastAPI(
    title="AI Web API",
    docs_url="/docs",
    redoc_url=None,
)

# ---- Error -> JSON ----
@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"code": 500, "error": {"message": f"{type(exc).__name__}: {exc}"}},
        )

# ---- No-cache for API & HTML (good for dev and streaming) ----
@app.middleware("http")
async def no_cache_middleware(request: Request, call_next):
    resp: Response = await call_next(request)
    path = request.url.path
    if path.startswith("/api/"):
        resp.headers.setdefault("Cache-Control", "no-store")
    if SERVE_SPA and (path == "/" or path.endswith(".html")):
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
    return resp

# ---- CORS (allow Vite dev origin) ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        # add more if needed
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- APIs under /api (your router has /responses inside) ----
app.include_router(responses_router.router, prefix="/api")

# ---- Serve SPA only in production (optional) ----
if SERVE_SPA:
    FRONTEND_DIST = (Path(__file__).resolve().parent.parent / "web" / "dist").resolve()
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="spa")
else:
    # In dev, do NOT serve the SPA. Provide a tiny root for sanity.
    @app.get("/")
    async def root():
        return {"status": "ok", "message": "API only (dev). Frontend runs on Vite :5173."}

# ---- Health ----
@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.app:app", host="0.0.0.0", port=8000, reload=True)
