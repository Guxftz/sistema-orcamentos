import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import get_db
from auth import get_current_user

router = APIRouter(prefix="/cobrancas", tags=["cobrancas"])


class CobrancaCreate(BaseModel):
    data: str
    cliente: str
    telefone: Optional[str] = ""
    descricao: str
    valor: float
    status: Optional[str] = "Pendente"
    mensagem: Optional[str] = ""
    origem: Optional[str] = "manual"
    origem_id: Optional[int] = None


@router.get("")
def listar_cobrancas(filtro: Optional[str] = None, user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        if filtro:
            cur.execute("""
                SELECT id, data, cliente, telefone, descricao, valor, status, origem, origem_id
                FROM cobrancas WHERE cliente ILIKE %s ORDER BY id DESC
            """, (f"%{filtro}%",))
        else:
            cur.execute("""
                SELECT id, data, cliente, telefone, descricao, valor, status, origem, origem_id
                FROM cobrancas ORDER BY id DESC
            """)
        rows = cur.fetchall()
    return [dict(r) for r in rows]


@router.get("/dashboard")
def dashboard_cobrancas(user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(SUM(valor), 0) AS total FROM cobrancas WHERE status = 'Pendente'")
        total_pendente = float(cur.fetchone()["total"] or 0)
        cur.execute("SELECT COALESCE(SUM(valor), 0) AS total FROM cobrancas WHERE status = 'Pago'")
        total_pago = float(cur.fetchone()["total"] or 0)
        cur.execute("""
            SELECT cliente, telefone, descricao, valor, data
            FROM cobrancas WHERE status = 'Pendente'
            ORDER BY data ASC, cliente ASC
        """)
        pendentes = [dict(r) for r in cur.fetchall()]
    return {"total_pendente": total_pendente, "total_pago": total_pago, "pendentes": pendentes}


@router.post("")
def criar_cobranca(body: CobrancaCreate, user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        criado_em = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        cur.execute("""
            INSERT INTO cobrancas (data, cliente, telefone, descricao, valor, status, mensagem, origem, origem_id, criado_em)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """, (body.data, body.cliente, body.telefone, body.descricao, body.valor,
              body.status, body.mensagem, body.origem, body.origem_id, criado_em))
        row = cur.fetchone()
        conn.commit()
    return {"id": row["id"]}


@router.put("/{cobranca_id}")
def atualizar_cobranca(cobranca_id: int, body: CobrancaCreate, user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        cur.execute("""
            UPDATE cobrancas SET data=%s, cliente=%s, telefone=%s, descricao=%s,
            valor=%s, status=%s, mensagem=%s, atualizado_em=%s
            WHERE id=%s
        """, (body.data, body.cliente, body.telefone, body.descricao,
              body.valor, body.status, body.mensagem, agora, cobranca_id))
        conn.commit()
    return {"ok": True}


@router.patch("/{cobranca_id}/status")
def toggle_status(cobranca_id: int, user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT status FROM cobrancas WHERE id = %s", (cobranca_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404)
        novo_status = "Pago" if row["status"] == "Pendente" else "Pendente"
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        cur.execute("UPDATE cobrancas SET status=%s, atualizado_em=%s WHERE id=%s",
                    (novo_status, agora, cobranca_id))
        conn.commit()
    return {"status": novo_status}


@router.delete("/{cobranca_id}")
def deletar_cobranca(cobranca_id: int, user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM cobrancas WHERE id = %s", (cobranca_id,))
        conn.commit()
    return {"ok": True}
