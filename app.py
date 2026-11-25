from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
import json
import database

app = FastAPI(title="Gestão de Buffet")


@app.on_event("startup")
def on_startup():
    database.init_db()


class ClienteCreate(BaseModel):
    nome: str
    cpf: Optional[str] = ""
    telefone: Optional[str] = ""
    endereco: Optional[str] = ""
    email: Optional[str] = ""
    observacoes: Optional[str] = ""


class FuncionarioCreate(BaseModel):
    nome: str
    cpf: Optional[str] = ""
    endereco: Optional[str] = ""
    telefone: Optional[str] = ""
    chave_pix: Optional[str] = ""


class CardapioItemCreate(BaseModel):
    nome: str
    categoria: str
    detalhe: Optional[str] = ""


class PacoteCreate(BaseModel):
    nome: str
    tipo_evento: Optional[str] = ""
    descricao: Optional[str] = ""
    secoes: List[str] = ["Entradas", "Principal", "Bebidas"]
    item_ids: List[int] = []


class EventoCreate(BaseModel):
    cliente_id: int
    titulo: str
    tipo_evento: Optional[str] = ""
    data_evento: str
    horario: str
    horario_profissional: Optional[str] = ""
    local_evento: Optional[str] = ""
    paleta_cores: Optional[str] = ""
    qtd_convidados: int
    valor_por_pessoa: float
    valor_extras: float = 0.0
    status: str = "Orçamento"
    pacote: Optional[str] = ""
    entradas: Optional[str] = ""
    principal: Optional[str] = ""
    finger_food: Optional[str] = ""
    bebidas: Optional[str] = ""
    profissionais: Optional[str] = ""
    cardapio_obs: Optional[str] = ""


class FinanceiroCreate(BaseModel):
    evento_id: int
    descricao: str
    tipo: str
    valor: float
    data_vencimento: Optional[str] = ""
    status: str = "Pendente"


def _normalizar_linha(row: dict) -> dict:
    item = dict(row)
    for k, v in item.items():
        if hasattr(v, "isoformat") and k in ("data_evento", "data_vencimento"):
            item[k] = v.isoformat()
        elif k in ("valor_por_pessoa", "valor_extras", "valor_total", "valor") and v is not None:
            item[k] = float(v)
    return item


# --- ROTAS DE CLIENTES ---
@app.get("/api/clientes")
def listar_clientes():
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM clientes ORDER BY nome")
            return [_normalizar_linha(r) for r in cur.fetchall()]


@app.post("/api/clientes")
def criar_cliente(cliente: ClienteCreate):
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO clientes (nome, cpf, telefone, endereco, email, observacoes)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (cliente.nome, cliente.cpf, cliente.telefone, cliente.endereco, cliente.email, cliente.observacoes),
            )
            novo_id = cur.fetchone()["id"]
        conn.commit()
    return {"id": novo_id, "mensagem": "Cliente cadastrado com sucesso"}


# --- ROTAS DE FUNCIONÁRIOS ---
@app.get("/api/funcionarios")
def listar_funcionarios():
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM funcionarios ORDER BY nome")
            return [_normalizar_linha(r) for r in cur.fetchall()]


@app.post("/api/funcionarios")
def criar_funcionario(func: FuncionarioCreate):
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO funcionarios (nome, cpf, endereco, telefone, chave_pix)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (func.nome, func.cpf, func.endereco, func.telefone, func.chave_pix),
            )
            novo_id = cur.fetchone()["id"]
        conn.commit()
    return {"id": novo_id, "mensagem": "Funcionário cadastrado com sucesso"}


@app.delete("/api/funcionarios/{func_id}")
def excluir_funcionario(func_id: int):
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM funcionarios WHERE id = %s", (func_id,))
        conn.commit()
    return {"mensagem": "Funcionário removido"}


# --- ROTAS DE CARDÁPIO E PACOTES ---
@app.get("/api/cardapio-itens")
def listar_cardapio_itens():
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM cardapio_itens ORDER BY categoria, nome")
            return [_normalizar_linha(r) for r in cur.fetchall()]


@app.post("/api/cardapio-itens")
def criar_cardapio_item(item: CardapioItemCreate):
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO cardapio_itens (nome, categoria, detalhe)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (item.nome.strip(), item.categoria.strip(), (item.detalhe or "").strip()),
            )
            novo_id = cur.fetchone()["id"]
        conn.commit()
    return {"id": novo_id, "mensagem": "Item adicionado ao cardápio"}


@app.delete("/api/cardapio-itens/{item_id}")
def excluir_cardapio_item(item_id: int):
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM cardapio_itens WHERE id = %s", (item_id,))
        conn.commit()
    return {"mensagem": "Item removido do cardápio"}


@app.get("/api/pacotes")
def listar_pacotes():
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM pacotes ORDER BY nome")
            pacotes = cur.fetchall()
            resultado = []
            for p in pacotes:
                p_dict = _normalizar_linha(p)
                secoes_raw = p_dict.get("secoes")
                if isinstance(secoes_raw, str):
                    try:
                        p_dict["secoes"] = json.loads(secoes_raw)
                    except Exception:
                        p_dict["secoes"] = ["Entradas", "Principal", "Bebidas"]
                elif not isinstance(secoes_raw, list) or not secoes_raw:
                    p_dict["secoes"] = ["Entradas", "Principal", "Finger Food", "Bebidas"]

                cur.execute(
                    """
                    SELECT ci.*
                    FROM pacote_itens pi
                    JOIN cardapio_itens ci ON pi.item_id = ci.id
                    WHERE pi.pacote_id = %s
                    ORDER BY ci.categoria, ci.nome
                    """,
                    (p["id"],),
                )
                itens = [_normalizar_linha(i) for i in cur.fetchall()]
                p_dict["itens"] = itens
                p_dict["item_ids"] = [i["id"] for i in itens]
                resultado.append(p_dict)
    return resultado


@app.post("/api/pacotes")
def criar_pacote(pacote: PacoteCreate):
    secoes_limpas = [s.strip() for s in pacote.secoes if s and s.strip()] or ["Entradas", "Principal", "Bebidas"]
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pacotes (nome, tipo_evento, descricao, secoes)
                VALUES (%s, %s, %s, %s::jsonb)
                RETURNING id
                """,
                (
                    pacote.nome.strip(),
                    (pacote.tipo_evento or pacote.nome).strip(),
                    (pacote.descricao or "").strip(),
                    json.dumps(secoes_limpas, ensure_ascii=False),
                ),
            )
            pacote_id = cur.fetchone()["id"]

            for item_id in set(pacote.item_ids):
                cur.execute(
                    """
                    INSERT INTO pacote_itens (pacote_id, item_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (pacote_id, item_id),
                )
        conn.commit()
    return {"id": pacote_id, "mensagem": "Pacote criado com sucesso"}


@app.delete("/api/pacotes/{pacote_id}")
def excluir_pacote(pacote_id: int):
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM pacotes WHERE id = %s", (pacote_id,))
        conn.commit()
    return {"mensagem": "Pacote removido"}


# --- ROTAS DE EVENTOS ---
@app.get("/api/eventos")
def listar_eventos():
    query = """
        SELECT e.*,
               c.nome AS cliente_nome,
               c.cpf AS cliente_cpf,
               c.telefone AS cliente_telefone,
               c.endereco AS cliente_endereco
        FROM eventos e
        JOIN clientes c ON e.cliente_id = c.id
        ORDER BY e.data_evento ASC, e.horario ASC
    """
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return [_normalizar_linha(r) for r in cur.fetchall()]


@app.post("/api/eventos")
def criar_evento(evento: EventoCreate):
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, titulo, horario FROM eventos WHERE data_evento = %s AND status != 'Cancelado'",
                (evento.data_evento,),
            )
            conflito = cur.fetchone()

            valor_total = (evento.qtd_convidados * evento.valor_por_pessoa) + evento.valor_extras
            tipo_efetivo = (evento.tipo_evento or evento.pacote or "Pacote").strip()

            cur.execute(
                """
                INSERT INTO eventos (
                    cliente_id, titulo, tipo_evento, data_evento, horario,
                    horario_profissional, local_evento, paleta_cores,
                    qtd_convidados, valor_por_pessoa, valor_extras, valor_total,
                    status, pacote, entradas, principal, finger_food, bebidas,
                    profissionais, cardapio_obs
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s
                )
                RETURNING id
                """,
                (
                    evento.cliente_id,
                    evento.titulo,
                    tipo_efetivo,
                    evento.data_evento,
                    evento.horario,
                    evento.horario_profissional,
                    evento.local_evento,
                    evento.paleta_cores,
                    evento.qtd_convidados,
                    evento.valor_por_pessoa,
                    evento.valor_extras,
                    valor_total,
                    evento.status,
                    evento.pacote,
                    evento.entradas,
                    evento.principal,
                    evento.finger_food,
                    evento.bebidas,
                    evento.profissionais,
                    evento.cardapio_obs,
                ),
            )
            novo_id = cur.fetchone()["id"]
        conn.commit()

    aviso = None
    if conflito:
        aviso = f"Atenção: Já existe o evento '{conflito['titulo']}' às {conflito['horario']} nesta data."

    return {"id": novo_id, "valor_total": valor_total, "aviso": aviso}


@app.patch("/api/eventos/{evento_id}/status")
def atualizar_status_evento(evento_id: int, status: str):
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE eventos SET status = %s WHERE id = %s", (status, evento_id))
        conn.commit()
    return {"mensagem": "Status atualizado"}


# --- ROTAS FINANCEIRAS ---
@app.get("/api/financeiro")
def listar_financeiro():
    query = """
        SELECT f.*, e.titulo AS evento_titulo
        FROM financeiro f
        JOIN eventos e ON f.evento_id = e.id
        ORDER BY f.id DESC
    """
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return [_normalizar_linha(r) for r in cur.fetchall()]


@app.post("/api/financeiro")
def criar_lancamento(item: FinanceiroCreate):
    data_venc = item.data_vencimento if item.data_vencimento else None
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO financeiro (evento_id, descricao, tipo, valor, data_vencimento, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (item.evento_id, item.descricao, item.tipo, item.valor, data_venc, item.status),
            )
            novo_id = cur.fetchone()["id"]
        conn.commit()
    return {"id": novo_id, "mensagem": "Lançamento registrado"}


@app.delete("/api/financeiro/{lanc_id}")
def excluir_lancamento(lanc_id: int):
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM financeiro WHERE id = %s", (lanc_id,))
        conn.commit()
    return {"mensagem": "Lançamento removido"}


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def root():
    return FileResponse("static/index.html")