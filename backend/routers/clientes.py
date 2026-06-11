from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import get_db
from auth import get_current_user

router = APIRouter(prefix="/clientes", tags=["clientes"])


class ClienteCreate(BaseModel):
    nome: str
    telefone: Optional[str] = ""
    endereco: Optional[str] = ""
    observacoes: Optional[str] = ""


@router.get("")
def listar_clientes(user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, nome, telefone, endereco, observacoes, criado_em FROM clientes ORDER BY nome")
        rows = cur.fetchall()
    return [dict(r) for r in rows]


@router.post("")
def criar_cliente(body: ClienteCreate, user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        criado_em = datetime.now().strftime("%d/%m/%Y")
        cur.execute("""
            INSERT INTO clientes (nome, telefone, endereco, observacoes, criado_em)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
        """, (body.nome, body.telefone, body.endereco, body.observacoes, criado_em))
        row = cur.fetchone()
        conn.commit()
    return {"id": row["id"]}


@router.put("/{cliente_id}")
def atualizar_cliente(cliente_id: int, body: ClienteCreate, user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE clientes SET nome=%s, telefone=%s, endereco=%s, observacoes=%s
            WHERE id=%s
        """, (body.nome, body.telefone, body.endereco, body.observacoes, cliente_id))
        conn.commit()
    return {"ok": True}


@router.delete("/{cliente_id}")
def deletar_cliente(cliente_id: int, user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM clientes WHERE id = %s", (cliente_id,))
        conn.commit()
    return {"ok": True}
