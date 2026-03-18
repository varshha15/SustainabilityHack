from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from database.db import connect_db, close_db
from routes.energy_routes import router as energy_router
from routes.waste_routes import router as waste_router
from routes.sustainability_routes import router as sustainability_router
from routes.prediction_routes import router as prediction_router
from routes.alerts_routes import router as alerts_router


# ── Startup / Shutdown ────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()


# ── App ───────────────────────────────────────────

app = FastAPI(
    title="Sustainability Platform API",
    description=(
        "Backend for the Smart Building Sustainability Platform.\n\n"
        "**Member 3 — Platform Backend & System Integration**\n\n"
        "Connects:\n"
        "- MongoDB (Member 1 data layer)\n"
        "- ML service on port 8001 (Member 2 AI engine)\n"
        "- React dashboard (Member 4 frontend)\n\n"
        "Open `/docs` for full interactive API documentation."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS (allow Member 4 frontend to connect) ─────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # React CRA dev server
        "http://localhost:5173",   # Vite dev server
        "https://your-frontend.vercel.app",  # ← replace with real URL after deploy
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────

app.include_router(energy_router)
app.include_router(waste_router)
app.include_router(sustainability_router)
app.include_router(prediction_router)
app.include_router(alerts_router)


# ── Health ────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "Sustainability Platform Backend",
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
