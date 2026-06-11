import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List, Optional
from database import get_db
from auth import get_current_user
from utils.pdf import gerar_pdf_montador
from utils.excel import gerar_excel_montador

router = APIRouter(prefix="/montador", tags=["montador"])


class ItemMontador(BaseModel):
    descricao: str
    qtd: Optional[float] = 1
    ml: Optional[float] = 0
    valor_ml: Optional[float] = 0
    valor_fixo: Optional[float] = 0
    total: float


class OrcamentoMontadorCreate(BaseModel):
    data: str
    cliente: str
    itens: List[ItemMontador]


@router.get("")
def listar_montador(user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, data, cliente, total, created_at FROM orcamentos_montador ORDER BY id DESC")
        rows = cur.fetchall()
    return [dict(r) for r in rows]


@router.post("")
def criar_montador(body: OrcamentoMontadorCreate, user=Depends(get_current_user)):
    with get_db() as conn:
        itens_json = json.dumps([i.dict() for i in body.itens], ensure_ascii=False)
        total = sum(i.total for i in body.itens)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO orcamentos_montador (data, cliente, total, itens_json)
            VALUES (%s,%s,%s,%s::jsonb) RETURNING id
        """, (body.data, body.cliente, total, itens_json))
        row = cur.fetchone()
        conn.commit()
    return {"id": row["id"]}


@router.get("/{orc_id}")
def obter_montador(orc_id: int, user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM orcamentos_montador WHERE id = %s", (orc_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404)
    data = dict(row)
    if isinstance(data.get("itens_json"), str):
        data["itens_json"] = json.loads(data["itens_json"])
    return data


@router.put("/{orc_id}")
def atualizar_montador(orc_id: int, body: OrcamentoMontadorCreate, user=Depends(get_current_user)):
    with get_db() as conn:
        itens_json = json.dumps([i.dict() for i in body.itens], ensure_ascii=False)
        total = sum(i.total for i in body.itens)
        cur = conn.cursor()
        cur.execute("""
            UPDATE orcamentos_montador SET data=%s, cliente=%s, total=%s, itens_json=%s::jsonb
            WHERE id=%s
        """, (body.data, body.cliente, total, itens_json, orc_id))
        conn.commit()
    return {"ok": True}


@router.delete("/{orc_id}")
def deletar_montador(orc_id: int, user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM orcamentos_montador WHERE id = %s", (orc_id,))
        conn.commit()
    return {"ok": True}


@router.get("/{orc_id}/pdf")
def download_pdf_montador(orc_id: int, user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM orcamentos_montador WHERE id = %s", (orc_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404)
        cur.execute("SELECT value FROM settings WHERE key = 'logo_base64'")
        logo_row = cur.fetchone()
        logo = logo_row["value"] if logo_row else ""

    data = dict(row)
    itens = data["itens_json"]
    if isinstance(itens, str):
        itens = json.loads(itens)

    pdf_bytes = gerar_pdf_montador(
        nome_cliente=data["cliente"],
        data_orcamento=data.get("data", ""),
        itens=itens,
        total_geral=data["total"],
        logo_base64=logo,
    )
    filename = f"montador_{orc_id}_{data.get('cliente','')[:20]}.pdf"
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/{orc_id}/excel")
def download_excel_montador(orc_id: int, user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM orcamentos_montador WHERE id = %s", (orc_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404)

    data = dict(row)
    itens = data["itens_json"]
    if isinstance(itens, str):
        itens = json.loads(itens)

    xlsx_bytes = gerar_excel_montador(
        nome_cliente=data["cliente"],
        data_orcamento=data.get("data", ""),
        itens=itens,
        total_geral=data["total"],
    )
    filename = f"montador_{orc_id}_{data.get('cliente','')[:20]}.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
