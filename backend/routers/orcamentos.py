import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List, Optional
from database import get_db
from auth import get_current_user
from utils.pdf import gerar_pdf_orcamento
from utils.excel import gerar_excel_orcamento

router = APIRouter(prefix="/orcamentos", tags=["orcamentos"])


class ItemOrcamento(BaseModel):
    ambiente: str
    descricao: str
    material: Optional[str] = "-"
    qtd: Optional[float] = 1
    ml: Optional[float] = 0
    preco_ml: Optional[float] = 0
    preco_ml_base: Optional[float] = 0
    comp: Optional[float] = 0
    larg: Optional[float] = 0
    area: Optional[float] = 0
    valor_m2: Optional[float] = 0
    valor_m2_base: Optional[float] = 0
    valor_fixo: Optional[float] = 0
    valor_fixo_base: Optional[float] = 0
    total: float
    ocultar_valor_pdf: Optional[bool] = False


class OrcamentoCreate(BaseModel):
    data: str
    cliente: str
    endereco: Optional[str] = ""
    cidade: Optional[str] = ""
    forma_pagamento: Optional[str] = "A definir"
    mostrar_nota: Optional[bool] = True
    rt_pct: Optional[float] = 0
    itens: List[ItemOrcamento]


def _get_logo(conn):
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key = 'logo_base64'")
    row = cur.fetchone()
    return row["value"] if row else ""


def _get_ocultar_itens(conn):
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key = 'ocultar_valor_itens_pdf'")
    row = cur.fetchone()
    return (row["value"] or "").lower() == "true" if row else False


def _next_numero(conn):
    cur = conn.cursor()
    cur.execute("UPDATE orc_sequence SET ultimo_numero = ultimo_numero + 1 WHERE id = 1 RETURNING ultimo_numero")
    row = cur.fetchone()
    return row["ultimo_numero"] if row else 1


@router.get("")
def listar_orcamentos(user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, numero, data, cliente, endereco, total, forma_pagamento, created_at
            FROM orcamentos ORDER BY id DESC
        """)
        rows = cur.fetchall()
    return [dict(r) for r in rows]


@router.post("")
def criar_orcamento(body: OrcamentoCreate, user=Depends(get_current_user)):
    with get_db() as conn:
        numero = _next_numero(conn)
        itens_json = json.dumps([i.dict() for i in body.itens], ensure_ascii=False)
        total = sum(i.total for i in body.itens)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO orcamentos (numero, data, cliente, endereco, cidade, total, forma_pagamento, mostrar_nota, rt_pct, itens_json)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb) RETURNING id
        """, (numero, body.data, body.cliente, body.endereco, body.cidade, total,
              body.forma_pagamento, body.mostrar_nota, body.rt_pct, itens_json))
        row = cur.fetchone()
        conn.commit()
    return {"id": row["id"], "numero": numero}


@router.get("/{orc_id}")
def obter_orcamento(orc_id: int, user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM orcamentos WHERE id = %s", (orc_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")
    data = dict(row)
    if isinstance(data.get("itens_json"), str):
        data["itens_json"] = json.loads(data["itens_json"])
    return data


@router.put("/{orc_id}")
def atualizar_orcamento(orc_id: int, body: OrcamentoCreate, user=Depends(get_current_user)):
    with get_db() as conn:
        itens_json = json.dumps([i.dict() for i in body.itens], ensure_ascii=False)
        total = sum(i.total for i in body.itens)
        cur = conn.cursor()
        cur.execute("""
            UPDATE orcamentos SET data=%s, cliente=%s, endereco=%s, cidade=%s, total=%s,
            forma_pagamento=%s, mostrar_nota=%s, rt_pct=%s, itens_json=%s::jsonb
            WHERE id=%s
        """, (body.data, body.cliente, body.endereco, body.cidade, total,
              body.forma_pagamento, body.mostrar_nota, body.rt_pct, itens_json, orc_id))
        conn.commit()
    return {"ok": True}


@router.delete("/{orc_id}")
def deletar_orcamento(orc_id: int, user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM orcamentos WHERE id = %s", (orc_id,))
        conn.commit()
    return {"ok": True}


@router.get("/{orc_id}/pdf")
def download_pdf(orc_id: int, user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM orcamentos WHERE id = %s", (orc_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404)
        logo = _get_logo(conn)
        ocultar = _get_ocultar_itens(conn)

    data = dict(row)
    itens = data["itens_json"]
    if isinstance(itens, str):
        itens = json.loads(itens)

    pdf_bytes = gerar_pdf_orcamento(
        nome_cliente=data["cliente"],
        endereco_obra=data.get("endereco", ""),
        data_orcamento=data.get("data", ""),
        itens=itens,
        numero_orcamento=data.get("numero", orc_id),
        forma_pagamento=data.get("forma_pagamento", "A definir"),
        mostrar_nota=data.get("mostrar_nota", True),
        logo_base64=logo,
        ocultar_valores_itens=ocultar,
    )

    filename = f"orcamento_{data.get('numero', orc_id):03d}_{data.get('cliente','')[:20]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/{orc_id}/excel")
def download_excel(orc_id: int, user=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM orcamentos WHERE id = %s", (orc_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404)

    data = dict(row)
    itens = data["itens_json"]
    if isinstance(itens, str):
        itens = json.loads(itens)

    xlsx_bytes = gerar_excel_orcamento(
        nome_cliente=data["cliente"],
        endereco_obra=data.get("endereco", ""),
        data_orcamento=data.get("data", ""),
        itens=itens,
        numero_orcamento=data.get("numero", orc_id),
        forma_pagamento=data.get("forma_pagamento", "A definir"),
    )

    filename = f"orcamento_{data.get('numero', orc_id):03d}_{data.get('cliente','')[:20]}.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
