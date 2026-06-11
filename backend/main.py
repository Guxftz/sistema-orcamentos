import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from database import init_db
from auth import ensure_default_user
from routers import orcamentos, clientes, cobrancas, montador, dados

app = FastAPI(title="Sistema Orçamentos EBZ", version="2.0.0")

FRONTEND_URL = os.environ.get("FRONTEND_URL", "*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000", "http://localhost:5500", "http://127.0.0.1:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    init_db()
    ensure_default_user()


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(dados.router, prefix="/api")
app.include_router(orcamentos.router, prefix="/api")
app.include_router(clientes.router, prefix="/api")
app.include_router(cobrancas.router, prefix="/api")
app.include_router(montador.router, prefix="/api")
