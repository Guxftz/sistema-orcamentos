import json
import base64
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List
from database import get_db
from auth import get_current_user

router = APIRouter(tags=["dados"])


# =================== MATERIAIS ===================

class MaterialCreate(BaseModel):
    nome: str
    preco: float


@router.get("/materiais")
def listar_materiais(user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, nome, preco FROM materiais ORDER BY nome")
        rows = cur.fetchall()
    return [dict(r) for r in rows]


@router.post("/materiais")
def criar_material(body: MaterialCreate, user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO materiais (nome, preco) VALUES (%s, %s)
            ON CONFLICT (nome) DO UPDATE SET preco = EXCLUDED.preco
            RETURNING id
        """, (body.nome.strip(), body.preco))
        row = cur.fetchone()
        conn.commit()
    return {"id": row["id"]}


@router.delete("/materiais/{mat_id}")
def deletar_material(mat_id: int, user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM materiais WHERE id = %s", (mat_id,))
        conn.commit()
    return {"ok": True}


# =================== AMBIENTES ===================

class AmbienteCreate(BaseModel):
    nome: str


@router.get("/ambientes")
def listar_ambientes(user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, nome FROM ambientes ORDER BY nome")
        rows = cur.fetchall()
    return [dict(r) for r in rows]


@router.post("/ambientes")
def criar_ambiente(body: AmbienteCreate, user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO ambientes (nome) VALUES (%s)
            ON CONFLICT (nome) DO NOTHING RETURNING id
        """, (body.nome.strip().upper(),))
        row = cur.fetchone()
        conn.commit()
    return {"id": row["id"] if row else None}


@router.delete("/ambientes/{amb_id}")
def deletar_ambiente(amb_id: int, user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM ambientes WHERE id = %s", (amb_id,))
        conn.commit()
    return {"ok": True}


# =================== SERVIÇOS ===================

class ServicoCreate(BaseModel):
    nome: str
    tipo: Optional[str] = "fixo"
    preco: Optional[float] = 0


@router.get("/servicos")
def listar_servicos(user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, nome, tipo, preco FROM servicos ORDER BY nome")
        rows = cur.fetchall()
    return [dict(r) for r in rows]


@router.post("/servicos")
def criar_servico(body: ServicoCreate, user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO servicos (nome, tipo, preco) VALUES (%s, %s, %s)
            ON CONFLICT (nome) DO UPDATE SET tipo=EXCLUDED.tipo, preco=EXCLUDED.preco
            RETURNING id
        """, (body.nome.strip().upper(), body.tipo, body.preco))
        row = cur.fetchone()
        conn.commit()
    return {"id": row["id"]}


@router.delete("/servicos/{srv_id}")
def deletar_servico(srv_id: int, user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM servicos WHERE id = %s", (srv_id,))
        conn.commit()
    return {"ok": True}


# =================== SETTINGS ===================

class SettingsUpdate(BaseModel):
    empresa: Optional[str] = None
    rt_padrao: Optional[str] = None
    ocultar_valor_itens_pdf: Optional[bool] = None
    whatsapp_template: Optional[str] = None
    company_name: Optional[str] = None


@router.get("/settings")
def obter_settings(user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT key, value FROM settings")
        rows = cur.fetchall()
    return {r["key"]: r["value"] for r in rows}


@router.put("/settings")
def salvar_settings(body: SettingsUpdate, user=Depends(get_current_user)):
    updates = body.dict(exclude_none=True)
    if "ocultar_valor_itens_pdf" in updates:
        updates["ocultar_valor_itens_pdf"] = "true" if updates["ocultar_valor_itens_pdf"] else "false"
    with get_db() as conn:
        cur = conn.cursor()
        for key, value in updates.items():
            cur.execute("""
                INSERT INTO settings (key, value) VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """, (key, str(value)))
        conn.commit()
    return {"ok": True}


@router.post("/settings/logo")
async def upload_logo(file: UploadFile = File(...), user=Depends(get_current_user)):
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Logo muito grande (máx 2MB)")
    logo_b64 = base64.b64encode(content).decode()
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO settings (key, value) VALUES ('logo_base64', %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """, (logo_b64,))
        conn.commit()
    return {"ok": True}


# =================== AUTH ROUTES ===================

class LoginRequest(BaseModel):
    username: str
    password: str


class PasswordChange(BaseModel):
    username: str
    new_password: str


@router.post("/auth/login")
def login(body: LoginRequest):
    from auth import verify_password, create_access_token
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, username, password_hash FROM users WHERE username = %s", (body.username,))
        user = cur.fetchone()
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos")
    token = create_access_token(body.username)
    return {"access_token": token, "token_type": "bearer", "username": body.username}


@router.post("/auth/change-password")
def change_password(body: PasswordChange, user=Depends(get_current_user)):
    from auth import hash_password
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET password_hash = %s WHERE username = %s",
                    (hash_password(body.new_password), body.username))
        conn.commit()
    return {"ok": True}
