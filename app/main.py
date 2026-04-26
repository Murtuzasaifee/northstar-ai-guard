import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.rag.vectorstore import ingest_documents
from app.routes.auth import router as auth_router
from app.routes.chat import router as chat_router
from app.routes.documents import router as documents_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Northstar Dynamics AI Assistant",
    description="An experimental secure internal AI chatbot with 9 LLM security layers",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(documents_router)


@app.on_event("startup")
def startup():
    logger.info("Starting Northstar Dynamics AI Assistant...")
    try:
        ingest_documents()
        logger.info("Documents ingested into vector store")
    except Exception as e:
        logger.warning(f"Could not ingest documents: {e}")
    logger.info(
        f"Security config: max_input={settings.max_input_length}, "
        f"rate_limit={settings.rate_limit_per_minute}/min, "
        f"token_budget={settings.max_tokens_per_user_daily}/day"
    )


@app.get("/")
def root():
    return {
        "application": "Northstar Dynamics AI Assistant",
        "version": "0.1.0",
        "security_features": [
            "Input Validation (Pydantic)",
            "LLM Guard (Semantic Threats)",
            "Hardened System Prompt",
            "Auth + Rate Limiting",
            "Input Restructuring",
            "Token Budgets",
            "Content Moderation",
            "RAG Spotlighting",
            "Output Validation",
        ],
    }


@app.get("/health")
def health():
    return {"status": "healthy"}
