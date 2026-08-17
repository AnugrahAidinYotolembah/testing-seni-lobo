import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from auth import router as auth_router
from collections_api import router as collections_router
from users import router as users_router
from upload import router as upload_router
from ai_api import router as ai_router

app = FastAPI(
    title="Arsip Digital Komunitas Seni Lobo Palu",
    description="API Backend for the Lobo Palu Digital Cultural Archive",
    version="1.0.0",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(collections_router)
app.include_router(users_router)
app.include_router(upload_router)
app.include_router(ai_router)



@app.get("/")
async def root():
    return {
        "name": "Arsip Digital Komunitas Seni Lobo Palu",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/api/health")
async def health():
    import os
    from config import supabase
    return {
        "status": "ok",
        "supabase_connected": supabase is not None,
        "url_len": len(os.getenv("SUPABASE_URL", "")),
        "key_len": len(os.getenv("SUPABASE_KEY", "")),
    }
