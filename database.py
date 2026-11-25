import os
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.getenv("DATABASE_URL", "")


def get_connection():
    if not DATABASE_URL:
        raise RuntimeError(
            "Variável DATABASE_URL não configurada. Adicione a Connection String do Supabase no Render (ou no ambiente local)."
        )
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init_db():
    if not DATABASE_URL:
        return

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS clientes (
                    id BIGSERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    cpf TEXT,
                    telefone TEXT,
                    endereco TEXT,
                    email TEXT,
                    observacoes TEXT,
                    criado_em TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS funcionarios (
                    id BIGSERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    cpf TEXT,
                    endereco TEXT,
                    telefone TEXT,
                    chave_pix TEXT,
                    criado_em TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS cardapio_itens (
                    id BIGSERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    categoria TEXT NOT NULL,
                    detalhe TEXT,
                    criado_em TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS pacotes (
                    id BIGSERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    tipo_evento TEXT,
                    descricao TEXT,
                    secoes JSONB DEFAULT '["Entradas", "Principal", "Bebidas"]'::jsonb,
                    criado_em TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS pacote_itens (
                    pacote_id BIGINT NOT NULL REFERENCES pacotes (id) ON DELETE CASCADE,
                    item_id BIGINT NOT NULL REFERENCES cardapio_itens (id) ON DELETE CASCADE,
                    PRIMARY KEY (pacote_id, item_id)
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS eventos (
                    id BIGSERIAL PRIMARY KEY,
                    cliente_id BIGINT NOT NULL REFERENCES clientes (id) ON DELETE RESTRICT,
                    titulo TEXT NOT NULL,
                    tipo_evento TEXT NOT NULL,
                    data_evento DATE NOT NULL,
                    horario TEXT NOT NULL,
                    horario_profissional TEXT,
                    local_evento TEXT,
                    paleta_cores TEXT,
                    qtd_convidados INTEGER DEFAULT 0,
                    valor_por_pessoa NUMERIC(12, 2) DEFAULT 0.00,
                    valor_extras NUMERIC(12, 2) DEFAULT 0.00,
                    valor_total NUMERIC(12, 2) DEFAULT 0.00,
                    status TEXT DEFAULT 'Orçamento',
                    pacote TEXT,
                    entradas TEXT,
                    principal TEXT,
                    finger_food TEXT,
                    bebidas TEXT,
                    profissionais TEXT,
                    cardapio_obs TEXT,
                    criado_em TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS financeiro (
                    id BIGSERIAL PRIMARY KEY,
                    evento_id BIGINT NOT NULL REFERENCES eventos (id) ON DELETE CASCADE,
                    descricao TEXT NOT NULL,
                    tipo TEXT NOT NULL,
                    valor NUMERIC(12, 2) NOT NULL,
                    data_vencimento DATE,
                    status TEXT DEFAULT 'Pendente',
                    criado_em TIMESTAMPTZ DEFAULT NOW()
                )
            """)
        conn.commit()