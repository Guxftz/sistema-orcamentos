import os
import psycopg2
import psycopg2.extras
from contextlib import contextmanager

DATABASE_URL = os.environ.get("DATABASE_URL", "")


@contextmanager
def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS orcamentos (
                id SERIAL PRIMARY KEY,
                numero INTEGER,
                data TEXT,
                cliente TEXT,
                endereco TEXT,
                total REAL DEFAULT 0,
                forma_pagamento TEXT DEFAULT 'A definir',
                mostrar_nota BOOLEAN DEFAULT TRUE,
                rt_pct REAL DEFAULT 0,
                itens_json JSONB DEFAULT '[]'::jsonb,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS orcamentos_montador (
                id SERIAL PRIMARY KEY,
                data TEXT,
                cliente TEXT,
                total REAL DEFAULT 0,
                itens_json JSONB DEFAULT '[]'::jsonb,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id SERIAL PRIMARY KEY,
                nome TEXT NOT NULL,
                telefone TEXT,
                endereco TEXT,
                observacoes TEXT,
                criado_em TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS cobrancas (
                id SERIAL PRIMARY KEY,
                data TEXT,
                cliente TEXT,
                telefone TEXT,
                descricao TEXT,
                valor REAL DEFAULT 0,
                status TEXT DEFAULT 'Pendente',
                mensagem TEXT,
                origem TEXT,
                origem_id INTEGER,
                criado_em TEXT,
                atualizado_em TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS materiais (
                id SERIAL PRIMARY KEY,
                nome TEXT UNIQUE NOT NULL,
                preco REAL NOT NULL DEFAULT 0
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS ambientes (
                id SERIAL PRIMARY KEY,
                nome TEXT UNIQUE NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS servicos (
                id SERIAL PRIMARY KEY,
                nome TEXT UNIQUE NOT NULL,
                tipo TEXT DEFAULT 'fixo',
                preco REAL DEFAULT 0,
                precos_cidade JSONB
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS orc_sequence (
                id INTEGER PRIMARY KEY DEFAULT 1,
                ultimo_numero INTEGER DEFAULT 0
            )
        """)

        cur.execute("""
            INSERT INTO orc_sequence (id, ultimo_numero)
            VALUES (1, 0)
            ON CONFLICT (id) DO NOTHING
        """)

        defaults = [
            ("empresa", "EBZ Mármores"),
            ("whatsapp_template", "Olá, {cliente}! Tudo bem? Aqui é da {empresa}. Estou entrando em contato sobre a cobrança '{descricao}' no valor de {valor}. Data de referência: {vencimento}."),
            ("company_name", "EBZ Mármores"),
            ("rt_padrao", "0"),
            ("ocultar_valor_itens_pdf", "false"),
            ("logo_base64", ""),
        ]
        for key, value in defaults:
            cur.execute("""
                INSERT INTO settings (key, value) VALUES (%s, %s)
                ON CONFLICT (key) DO NOTHING
            """, (key, value))

        ambientes_padrao = [
            "COZINHA", "COZINHA GOURMET", "LAVANDERIA", "W.C SOCIAL",
            "W.C SUÍTE", "W.C MASTER", "CHURRASQUEIRA", "ÁREA GOURMET",
            "BANHEIRO", "LAVABO", "PISCINA"
        ]
        for amb in ambientes_padrao:
            cur.execute("""
                INSERT INTO ambientes (nome) VALUES (%s)
                ON CONFLICT (nome) DO NOTHING
            """, (amb,))

        conn.commit()
