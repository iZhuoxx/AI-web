import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import HTTPException as StarletteHTTPException
from .routes import responses as responses_router
from .routes import files as files_router
from .routes import audio as audio_router
from .routes import auth as auth_router
from .routes import notebooks as notebooks_router
from .routes import attachments as attachments_router
from .routes import notebook_folders as notebook_folders_router
from .routes import flashcards as flashcards_router
from .routes import flashcard_folders as flashcard_folders_router
from .routes import quizzes as quizzes_router
from .routes import mindmaps as mindmaps_router

SERVE_SPA = os.getenv("SERVE_SPA", "false").lower() == "true"

app = FastAPI(title="AI Web API", docs_url="/docs", redoc_url=None)

@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except StarletteHTTPException as http_exc:
        # Preserve the original status code from Starlette HTTP exceptions.
        return JSONResponse(
            status_code=http_exc.status_code,
            content={"error": {"message": http_exc.detail}},
        )
    except Exception as exc:
        # Only unexpected exceptions fall back to a 500.
        return JSONResponse(
            status_code=500,
            content={"error": {"message": f"{type(exc).__name__}: {exc}"}},
        )

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Important: include router objects, not the modules.
app.include_router(responses_router.router, prefix="/api")
app.include_router(files_router.router, prefix="/api")
app.include_router(audio_router.router, prefix="/api")
app.include_router(auth_router.router, prefix="/api")
app.include_router(notebooks_router.router, prefix="/api")
app.include_router(attachments_router.router, prefix="/api")
app.include_router(notebook_folders_router.router, prefix="/api")
app.include_router(flashcard_folders_router.router, prefix="/api")
app.include_router(flashcards_router.router, prefix="/api")
app.include_router(quizzes_router.router, prefix="/api")
app.include_router(mindmaps_router.router, prefix="/api")

if SERVE_SPA:
    FRONTEND_DIST = (Path(__file__).resolve().parent.parent / "web" / "dist").resolve()
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="spa")
else:
    @app.get("/")
    async def root():
        return {"status": "ok", "message": "API only (dev). Frontend runs on Vite :5173."}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.app:app", host="0.0.0.0", port=8000, reload=True)
