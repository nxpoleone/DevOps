"""Camada de persistência (SQLite).

O schema é criado e evoluído SOMENTE pelo Alembic (fonte única de verdade).
`salvar_transacao` implementa o Dual Write: detecta quais colunas existem e
grava no formato legado (cliente) e no novo (primeiro_nome/sobrenome),
mantendo compatibilidade N-1 durante o Expand-Contract.
"""
import os
import sqlite3
from datetime import datetime

from alembic import command
from alembic.config import Config

from regra_negocio import separar_nome

DB_NAME = "sistema.db"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def obter_conexao(db_path=DB_NAME):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _config_alembic(db_path) -> Config:
    cfg = Config(os.path.join(BASE_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BASE_DIR, "alembic").replace("%", "%%"))
    url = "sqlite:///" + os.path.abspath(db_path)
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    cfg.attributes["configure_logger"] = False  # não mexe no logging do app
    return cfg


def migrar(db_path=DB_NAME, revisao="head"):
    """Aplica as migrações do Alembic até a revisão informada."""
    command.upgrade(_config_alembic(db_path), revisao)


def reverter(db_path=DB_NAME, revisao="-1"):
    """Reverte migrações (downgrade)."""
    command.downgrade(_config_alembic(db_path), revisao)


def inicializar_banco(db_path=DB_NAME):
    """Garante que o banco está na versão mais recente do schema."""
    migrar(db_path, "head")


def _colunas_da_tabela(conn) -> set:
    return {linha["name"] for linha in conn.execute("PRAGMA table_info(transacoes)")}


def salvar_transacao(dados: dict, db_path=DB_NAME):
    primeiro_nome = dados.get("primeiro_nome")
    sobrenome = dados.get("sobrenome")
    if not primeiro_nome:
        primeiro_nome, sobrenome_calc = separar_nome(dados.get("cliente"))
        sobrenome = sobrenome if sobrenome is not None else sobrenome_calc
    sobrenome = sobrenome or ""

    cliente_legado = dados.get("cliente") or f"{primeiro_nome} {sobrenome}".strip()

    valores = {
        "id_transacao": dados.get("id_transacao"),
        "cliente": cliente_legado,            # legado (só gravado se a coluna existir)
        "primeiro_nome": primeiro_nome,
        "sobrenome": sobrenome,
        "cpf": dados.get("cpf"),
        "idade": dados.get("idade"),
        "valor_bruto": dados.get("valor_bruto"),
        "valor_final": dados.get("valor_final", 0.0),
        "status": dados.get("status"),
        "motivo_rejeicao": dados.get("motivo_rejeicao"),
        "data_processamento": dados.get("data_processamento", datetime.now().isoformat()),
    }

    conn = obter_conexao(db_path)
    try:
        existentes = _colunas_da_tabela(conn)
        colunas = [c for c in valores if c in existentes]  # Dual Write / N-1
        sql = "INSERT OR REPLACE INTO transacoes ({}) VALUES ({})".format(
            ", ".join(colunas), ", ".join("?" for _ in colunas)
        )
        conn.execute(sql, [valores[c] for c in colunas])
        conn.commit()
    finally:
        conn.close()


def buscar_transacao_por_id(id_transacao: str, db_path=DB_NAME):
    conn = obter_conexao(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM transacoes WHERE id_transacao = ?", (id_transacao,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None
    registro = dict(row)
    nome = f"{registro.get('primeiro_nome') or ''} {registro.get('sobrenome') or ''}".strip()
    registro["cliente"] = nome or registro.get("cliente")
    return registro
