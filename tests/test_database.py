"""Testes de integração: database.py + SQLite real (arquivo temporário) + Alembic."""
import pytest

from database import (buscar_transacao_por_id, inicializar_banco, migrar,
                      obter_conexao, salvar_transacao, _colunas_da_tabela)


@pytest.fixture
def db(tmp_path):
    caminho = str(tmp_path / "teste.db")
    inicializar_banco(caminho)
    return caminho


def dados(**alteracoes):
    base = {
        "id_transacao": "TX5001", "primeiro_nome": "Teste", "sobrenome": "da Silva",
        "cpf": "11122233344", "idade": 35, "valor_bruto": 200.00, "valor_final": 180.00,
        "status": "APROVADO", "motivo_rejeicao": None,
    }
    base.update(alteracoes)
    return base


def test_inicializar_banco_cria_schema_final(db):
    conn = obter_conexao(db)
    colunas = _colunas_da_tabela(conn)
    conn.close()
    assert {"primeiro_nome", "sobrenome"} <= colunas
    assert "cliente" not in colunas  # Contract aplicado


def test_inicializar_banco_e_idempotente(db):
    inicializar_banco(db)
    inicializar_banco(db)


def test_salvar_e_buscar_transacao(db):
    salvar_transacao(dados(), db_path=db)
    reg = buscar_transacao_por_id("TX5001", db_path=db)
    assert reg["id_transacao"] == "TX5001"
    assert reg["primeiro_nome"] == "Teste"
    assert reg["sobrenome"] == "da Silva"
    assert reg["cliente"] == "Teste da Silva"
    assert reg["status"] == "APROVADO"
    assert reg["valor_final"] == 180.00


def test_salvar_transacao_rejeitada_guarda_motivo(db):
    salvar_transacao(dados(id_transacao="TX5002", status="REJEITADO", valor_final=0.0,
                           motivo_rejeicao="CPF inválido"), db_path=db)
    reg = buscar_transacao_por_id("TX5002", db_path=db)
    assert reg["status"] == "REJEITADO"
    assert reg["motivo_rejeicao"] == "CPF inválido"
    assert reg["valor_final"] == 0.0


def test_buscar_id_inexistente_retorna_none(db):
    assert buscar_transacao_por_id("NAO_EXISTE", db_path=db) is None


def test_mesmo_id_substitui_registro(db):
    salvar_transacao(dados(valor_final=100.0), db_path=db)
    salvar_transacao(dados(valor_final=999.0), db_path=db)
    assert buscar_transacao_por_id("TX5001", db_path=db)["valor_final"] == 999.0
    conn = obter_conexao(db)
    total = conn.execute("SELECT COUNT(*) FROM transacoes").fetchone()[0]
    conn.close()
    assert total == 1


def test_salvar_separa_nome_a_partir_do_campo_cliente(db):
    d = dados()
    del d["primeiro_nome"], d["sobrenome"]
    d["cliente"] = "Maria Clara de Souza"
    salvar_transacao(d, db_path=db)
    reg = buscar_transacao_por_id("TX5001", db_path=db)
    assert (reg["primeiro_nome"], reg["sobrenome"]) == ("Maria", "Clara de Souza")


def test_dual_write_na_fase_expand_grava_os_dois_formatos(tmp_path):
    caminho = str(tmp_path / "expand.db")
    migrar(caminho, "002_expand_contract_v2")   # schema com 'cliente' E colunas novas
    d = dados()
    d["cliente"] = "Teste da Silva"
    salvar_transacao(d, db_path=caminho)
    conn = obter_conexao(caminho)
    linha = dict(conn.execute("SELECT * FROM transacoes").fetchone())
    conn.close()
    assert linha["cliente"] == "Teste da Silva"          # campo legado
    assert linha["primeiro_nome"] == "Teste"             # campos novos
    assert linha["sobrenome"] == "da Silva"
