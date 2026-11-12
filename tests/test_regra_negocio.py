"""Testes unitários: Particionamento de Equivalência + Análise de Valores-Limite."""
import pytest

from regra_negocio import calcular_desconto_e_final, separar_nome, validar_transacao


def tx_base(**alteracoes):
    base = {
        "id_transacao": "TX0001",
        "cliente": "Carlos Silva",
        "cpf": "12345678901",
        "idade": 25,
        "valor_bruto": 150.00,
        "categoria": "vestuario",
    }
    base.update(alteracoes)
    return base


# ---------- validar_transacao ----------
def test_transacao_valida():
    assert validar_transacao(tx_base()) == (True, "OK")


@pytest.mark.parametrize("idade, esperado", [
    (-1, False), (0, True), (1, True), (17, True), (18, True),
    (59, True), (60, True), (119, True), (120, True), (121, False),
])
def test_limites_de_idade(idade, esperado):
    valido, _ = validar_transacao(tx_base(idade=idade, categoria="livros"))
    assert valido is esperado


@pytest.mark.parametrize("valor, esperado", [
    (-50.0, False), (-0.01, False), (0, False), (0.0, False), (0.01, True), (1, True), (150.0, True),
])
def test_limites_de_valor_bruto(valor, esperado):
    valido, motivo = validar_transacao(tx_base(valor_bruto=valor))
    assert valido is esperado
    if not esperado:
        assert "maior que 0" in motivo


@pytest.mark.parametrize("cpf, esperado", [
    ("12345678901", True),    # 11 dígitos
    ("1234567890", False),    # 10 dígitos
    ("123456789012", False),  # 12 dígitos
    ("123", False),           # curto (caso TX1006)
    ("", False),
    ("1234567890a", False),   # letra
    ("123.456.789-0", False),  # pontuação
    ("１２３４５６７８９０１", False),  # dígitos unicode não-ASCII
])
def test_particoes_de_cpf(cpf, esperado):
    valido, motivo = validar_transacao(tx_base(cpf=cpf))
    assert valido is esperado
    if not esperado:
        assert "CPF" in motivo


@pytest.mark.parametrize("campo", ["id_transacao", "cliente", "cpf", "idade", "valor_bruto", "categoria"])
def test_campo_ausente_ou_nulo(campo):
    ausente = tx_base()
    del ausente[campo]
    assert validar_transacao(ausente)[0] is False
    assert campo in validar_transacao(tx_base(**{campo: None}))[1]


@pytest.mark.parametrize("alteracao", [
    {"valor_bruto": "abc"}, {"valor_bruto": True},
    {"idade": 25.5}, {"idade": "30"}, {"idade": True},
])
def test_tipos_invalidos(alteracao):
    assert validar_transacao(tx_base(**alteracao))[0] is False


@pytest.mark.parametrize("idade, categoria, esperado", [
    (17, "eletronicos", False),
    (16, "eletronicos", False),
    (18, "eletronicos", True),
    (17, "livros", True),
    (17, "ELETRONICOS ", False),   # normalização de caixa/espaços
])
def test_menor_de_idade_e_eletronicos(idade, categoria, esperado):
    valido, motivo = validar_transacao(tx_base(idade=idade, categoria=categoria))
    assert valido is esperado
    if not esperado:
        assert "Menores de 18 anos" in motivo


# ---------- calcular_desconto_e_final ----------
@pytest.mark.parametrize("idade, categoria, bruto, desc, final", [
    (59, "vestuario", 200.0, 0.0, 200.0),     # limite: 59 NÃO tem desconto de idoso
    (60, "vestuario", 200.0, 30.0, 170.0),    # limite: 60 tem 15%
    (30, "livros", 100.0, 10.0, 90.0),        # só categoria: 10%
    (59, "livros", 100.0, 10.0, 90.0),
    (60, "livros", 100.0, 25.0, 75.0),        # 15% + 10% = teto de 25%
    (70, "livros", 100.0, 25.0, 75.0),
    (25, "eletronicos", 150.0, 0.0, 150.0),   # sem desconto
    (70, "alimentos", 1000.0, 150.0, 850.0),
    (62, "vestuario", 500.0, 75.0, 425.0),
    (60, "vestuario", 120.0, 18.0, 102.0),
    (30, "LIVROS ", 100.0, 10.0, 90.0),       # normalização
    (25, "eletronicos", 350.50, 0.0, 350.50),
])
def test_calculo_de_desconto(idade, categoria, bruto, desc, final):
    assert calcular_desconto_e_final(bruto, idade, categoria) == (desc, final)


def test_desconto_nunca_passa_de_25_por_cento():
    desc, _ = calcular_desconto_e_final(1000.0, 90, "livros")
    assert desc <= 250.0


# ---------- separar_nome ----------
@pytest.mark.parametrize("entrada, esperado", [
    ("Carlos Eduardo Silva", ("Carlos", "Eduardo Silva")),
    ("Ana Souza", ("Ana", "Souza")),
    ("  Beatriz   Castro  ", ("Beatriz", "Castro")),
    ("Madonna", ("Madonna", "")),
    ("", ("Desconhecido", "")),
    (None, ("Desconhecido", "")),
    (123, ("Desconhecido", "")),
])
def test_separar_nome(entrada, esperado):
    assert separar_nome(entrada) == esperado
