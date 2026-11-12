"""Testes do padrão Expand-Contract: v1 -> v2 (expand) -> backfill -> v3 (contract)."""
import pytest

from backfill import executar_backfill
from database import _colunas_da_tabela, migrar, obter_conexao, reverter


def colunas(db):
    conn = obter_conexao(db)
    try:
        return _colunas_da_tabela(conn)
    finally:
        conn.close()


def inserir_legado(db, id_tx, cliente):
    conn = obter_conexao(db)
    conn.execute(
        "INSERT INTO transacoes (id_transacao, cliente, cpf, idade, valor_bruto, valor_final, status) "
        "VALUES (?, ?, '12345678901', 30, 100, 100, 'APROVADO')", (id_tx, cliente))
    conn.commit()
    conn.close()


def ler(db, id_tx):
    conn = obter_conexao(db)
    linha = conn.execute("SELECT * FROM transacoes WHERE id_transacao = ?", (id_tx,)).fetchone()
    conn.close()
    return dict(linha)


@pytest.fixture
def db_v1(tmp_path):
    caminho = str(tmp_path / "migracao.db")
    migrar(caminho, "001_initial_v1")
    inserir_legado(caminho, "A", "Carlos Eduardo Silva")
    inserir_legado(caminho, "B", "Madonna")
    return caminho


def test_expand_adiciona_colunas_sem_perder_dados(db_v1):
    migrar(db_v1, "002_expand_contract_v2")
    assert {"cliente", "primeiro_nome", "sobrenome"} <= colunas(db_v1)
    registro = ler(db_v1, "A")
    assert registro["cliente"] == "Carlos Eduardo Silva"
    assert registro["primeiro_nome"] is None  # ainda não preenchido


def test_expand_permite_cliente_nulo(db_v1):
    migrar(db_v1, "002_expand_contract_v2")
    conn = obter_conexao(db_v1)
    conn.execute("INSERT INTO transacoes (id_transacao, cpf, primeiro_nome, sobrenome) "
                 "VALUES ('C', '12345678901', 'Ana', 'Souza')")  # sem 'cliente'
    conn.commit()
    conn.close()


def test_backfill_preenche_registros_antigos_e_e_idempotente(db_v1):
    migrar(db_v1, "002_expand_contract_v2")
    assert executar_backfill(db_v1) == 2
    a = ler(db_v1, "A")
    assert (a["primeiro_nome"], a["sobrenome"]) == ("Carlos", "Eduardo Silva")
    b = ler(db_v1, "B")
    assert (b["primeiro_nome"], b["sobrenome"]) == ("Madonna", "")
    assert executar_backfill(db_v1) == 0   # segunda execução não altera nada


def test_contract_remove_coluna_legada_preservando_dados(db_v1):
    migrar(db_v1, "002_expand_contract_v2")
    executar_backfill(db_v1)
    migrar(db_v1, "003_contract_v3")
    assert "cliente" not in colunas(db_v1)
    a = ler(db_v1, "A")
    assert (a["primeiro_nome"], a["sobrenome"]) == ("Carlos", "Eduardo Silva")


def test_contract_sem_backfill_previo_nao_perde_dados(db_v1):
    """A migração 003 tem rede de segurança: faz o backfill antes de remover 'cliente'."""
    migrar(db_v1, "003_contract_v3")
    a = ler(db_v1, "A")
    assert (a["primeiro_nome"], a["sobrenome"]) == ("Carlos", "Eduardo Silva")


def test_backfill_apos_contract_nao_faz_nada(db_v1):
    migrar(db_v1, "003_contract_v3")
    assert executar_backfill(db_v1) == 0


def test_downgrade_do_contract_restaura_cliente(db_v1):
    migrar(db_v1, "003_contract_v3")
    reverter(db_v1, "002_expand_contract_v2")
    assert "cliente" in colunas(db_v1)
    assert ler(db_v1, "A")["cliente"] == "Carlos Eduardo Silva"


def test_downgrade_completo_volta_ao_schema_v1(db_v1):
    migrar(db_v1, "head")
    reverter(db_v1, "001_initial_v1")
    assert colunas(db_v1) == {"id_transacao", "cliente", "cpf", "idade", "valor_bruto", "valor_final",
                              "status", "motivo_rejeicao", "data_processamento"}
    assert ler(db_v1, "A")["cliente"] == "Carlos Eduardo Silva"
