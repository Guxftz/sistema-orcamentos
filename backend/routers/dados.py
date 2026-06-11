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
    preco_sp: Optional[float] = None


@router.get("/servicos")
def listar_servicos(user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, nome, tipo, preco, precos_cidade FROM servicos ORDER BY nome")
        rows = cur.fetchall()
    return [dict(r) for r in rows]


@router.post("/servicos")
def criar_servico(body: ServicoCreate, user=Depends(get_current_user)):
    precos_cidade = None
    if body.preco_sp is not None:
        precos_cidade = json.dumps({"default": body.preco, "São Paulo": body.preco_sp})
    with get_db() as conn:
        cur = conn.cursor()
        if precos_cidade:
            cur.execute("""
                INSERT INTO servicos (nome, tipo, preco, precos_cidade) VALUES (%s, %s, %s, %s::jsonb)
                ON CONFLICT (nome) DO UPDATE SET tipo=EXCLUDED.tipo, preco=EXCLUDED.preco, precos_cidade=EXCLUDED.precos_cidade
                RETURNING id
            """, (body.nome.strip().upper(), body.tipo, body.preco, precos_cidade))
        else:
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
    numero_inicial_orc: Optional[str] = None


@router.get("/settings")
def obter_settings(user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT key, value FROM settings")
        rows = cur.fetchall()
        cur.execute("SELECT ultimo_numero FROM orc_sequence WHERE id = 1")
        seq = cur.fetchone()
    result = {r["key"]: r["value"] for r in rows}
    result["proximo_numero"] = (seq["ultimo_numero"] + 1) if seq else 1
    return result


@router.put("/settings")
def salvar_settings(body: SettingsUpdate, user=Depends(get_current_user)):
    updates = body.dict(exclude_none=True)
    if "ocultar_valor_itens_pdf" in updates:
        updates["ocultar_valor_itens_pdf"] = "true" if updates["ocultar_valor_itens_pdf"] else "false"
    numero_inicial = updates.pop("numero_inicial_orc", None)
    with get_db() as conn:
        cur = conn.cursor()
        for key, value in updates.items():
            cur.execute("""
                INSERT INTO settings (key, value) VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """, (key, str(value)))
        if numero_inicial is not None:
            n = max(0, int(numero_inicial) - 1)
            cur.execute("UPDATE orc_sequence SET ultimo_numero = %s WHERE id = 1", (n,))
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
    return {"ok": True, "size": len(content)}


@router.get("/settings/logo")
def obter_logo(user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key = 'logo_base64'")
        row = cur.fetchone()
    logo = row["value"] if row else ""
    return {"logo_base64": logo, "has_logo": bool(logo)}


# =================== SEED (importar dados padrão) ===================

@router.post("/seed")
def seed_dados(user=Depends(get_current_user)):
    materiais = [
        ("GRANITOS - PRETO SÃO GABRIEL", 600.0),
        ("GRANITOS - PRETO ABSOLUTO", 500.0),
        ("GRANITOS - CAFÉ IMPERIAL", 1000.0),
        ("GRANITOS - BRANCO PARANÁ", 1950.0),
        ("GRANITOS - BRANCO DALLAS", 0.0),
        ("GRANITOS - BRANCO ITAÚNAS", 500.0),
        ("GRANITOS - BRANCO SIENA", 1000.0),
        ("GRANITOS - CINZA ANDORINHA", 700.0),
        ("GRANITOS - CINZA CORUMBÁ", 300.0),
        ("GRANITOS - VERDE UBATUBA", 500.0),
        ("GRANITOS - VERDE BUTTERFLY", 0.0),
        ("GRANITOS - AMARELO SANTA CECÍLIA", 0.0),
        ("GRANITOS - GIALLO FIORITO", 500.0),
        ("GRANITOS - MARROM ABSOLUTO", 700.0),
        ("MARMORES - BRANCO CARRARA", 0.0),
        ("MARMORES - CREMA MARFIL", 0.0),
        ("MARMORES - TRAVERTINO", 0.0),
        ("MARMORES - BEGE BAHIA", 0.0),
        ("MARMORES - NERO MARQUINA", 0.0),
        ("MARMORES - CALACATTA", 0.0),
        ("MARMORES - STATUARIO", 0.0),
        ("MARMORES - GRIS ARMANI", 0.0),
        ("MARMORES - BOTTICINO", 0.0),
        ("QUARTZOS - BRANCO PRIME", 600.0),
        ("QUARTZOS - CALACATTA GOLD", 0.0),
        ("QUARTZOS - CALACATTA CLASSIC", 0.0),
        ("QUARTZOS - STATUARIO", 0.0),
        ("QUARTZOS - SUPER WHITE", 0.0),
        ("QUARTZOS - BRANCO PURO", 0.0),
        ("QUARTZOS - GRIGIO", 0.0),
        ("QUARTZOS - PRETO CLASSIC", 0.0),
        ("NANOGLASS - NANOGLASS 15MM", 0.0),
        ("NANOGLASS - NANOGLASS 20MM", 0.0),
        ("NANOGLASS - NANOGLASS 30MM", 0.0),
        ("NANOGLASS - SUPER NANO", 0.0),
        ("NANOGLASS - MARMOGlass", 0.0),
        ("NANOGLASS - CRYSTAL NANO", 0.0),
    ]

    servicos_data = [
        {"nome": "SERVIÇO DE ACABAMENTO 45°", "tipo": "ml", "precos_cidade": {"default": 80, "São Paulo": 120}},
        {"nome": "SERVIÇO DE INSTALAÇÃO", "tipo": "ml", "precos_cidade": {"default": 95, "São Paulo": 150}},
        {"nome": "ABERTURA E COLAGEM DE CUBA", "tipo": "fixo", "precos_cidade": {"default": 200, "São Paulo": 200}},
        {"nome": "ABERTURA DE COOKTOP", "tipo": "fixo", "precos_cidade": {"default": 200, "São Paulo": 200}},
        {"nome": "FURO DE TORNEIRA", "tipo": "fixo", "precos_cidade": {"default": 50, "São Paulo": 50}},
        {"nome": "SUPORTE DE SUSTENTAÇÃO", "tipo": "fixo", "preco": 30},
        {"nome": "SERVIÇO DE ACABAMENTO RETO", "tipo": "ml", "precos_cidade": {"default": 60, "São Paulo": 90}},
        {"nome": "SERVIÇO DE ACABAMENTO BOLEADO", "tipo": "ml", "preco": 150.0},
    ]

    with get_db() as conn:
        cur = conn.cursor()
        for nome, preco in materiais:
            cur.execute("""
                INSERT INTO materiais (nome, preco) VALUES (%s, %s)
                ON CONFLICT (nome) DO UPDATE SET preco = EXCLUDED.preco
            """, (nome, preco))
        for s in servicos_data:
            precos = s.get("precos_cidade")
            preco = precos.get("default", 0) if precos else s.get("preco", 0)
            precos_json = json.dumps(precos) if precos else None
            if precos_json:
                cur.execute("""
                    INSERT INTO servicos (nome, tipo, preco, precos_cidade) VALUES (%s, %s, %s, %s::jsonb)
                    ON CONFLICT (nome) DO UPDATE SET tipo=EXCLUDED.tipo, preco=EXCLUDED.preco, precos_cidade=EXCLUDED.precos_cidade
                """, (s["nome"], s["tipo"], preco, precos_json))
            else:
                cur.execute("""
                    INSERT INTO servicos (nome, tipo, preco) VALUES (%s, %s, %s)
                    ON CONFLICT (nome) DO UPDATE SET tipo=EXCLUDED.tipo, preco=EXCLUDED.preco
                """, (s["nome"], s["tipo"], preco))
        conn.commit()
    return {"ok": True, "materiais": len(materiais), "servicos": len(servicos_data)}


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
