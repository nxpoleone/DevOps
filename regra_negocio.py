"""Lógica pura de negócio (sem acesso a banco de dados)."""

CAMPOS_OBRIGATORIOS = ["id_transacao", "cliente", "cpf", "idade", "valor_bruto", "categoria"]
DESCONTO_IDOSO = 0.15
DESCONTO_LIVROS = 0.10
DESCONTO_MAXIMO = 0.25


def _eh_numero(valor) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def validar_transacao(transacao: dict) -> tuple[bool, str]:
    for campo in CAMPOS_OBRIGATORIOS:
        if campo not in transacao or transacao[campo] is None:
            return False, f"Campo obrigatório ausente ou nulo: {campo}"

    valor_bruto = transacao["valor_bruto"]
    idade = transacao["idade"]
    cpf = str(transacao["cpf"])
    categoria = str(transacao["categoria"]).lower().strip()

    if not _eh_numero(valor_bruto) or valor_bruto <= 0:
        return False, "Valor bruto deve ser maior que 0"

    if not isinstance(idade, int) or isinstance(idade, bool) or not (0 <= idade <= 120):
        return False, "Idade inválida (deve estar entre 0 e 120 anos)"

    if not (cpf.isascii() and cpf.isdigit() and len(cpf) == 11):
        return False, "CPF inválido (deve conter exatamente 11 dígitos numéricos)"

    if idade < 18 and categoria == "eletronicos":
        return False, "Menores de 18 anos não podem comprar na categoria 'eletronicos'"

    return True, "OK"


def calcular_desconto_e_final(valor_bruto: float, idade: int, categoria: str) -> tuple[float, float]:
    desconto_percentual = 0.0
    categoria = categoria.lower().strip()

    if idade >= 60:
        desconto_percentual += DESCONTO_IDOSO

    if categoria == "livros":
        desconto_percentual += DESCONTO_LIVROS

    desconto_percentual = min(desconto_percentual, DESCONTO_MAXIMO)

    valor_desconto = round(valor_bruto * desconto_percentual, 2)
    valor_final = round(valor_bruto - valor_desconto, 2)
    return valor_desconto, valor_final


def separar_nome(nome_completo) -> tuple[str, str]:
    """Divide 'Carlos Eduardo Silva' em ('Carlos', 'Eduardo Silva').

    Usada no Dual Write e no Backfill (padrão Expand-Contract).
    """
    if not nome_completo or not isinstance(nome_completo, str) or not nome_completo.strip():
        return "Desconhecido", ""
    partes = nome_completo.strip().split()
    return partes[0], " ".join(partes[1:])
