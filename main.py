"""Ponto de entrada CLI: processamento em lote + observabilidade."""
import json
import logging
import sys
import time
from datetime import datetime

from database import DB_NAME, inicializar_banco, salvar_transacao
from regra_negocio import calcular_desconto_e_final, separar_nome, validar_transacao

ARQUIVO_DADOS = "dados_processamento.json"


def configurar_logging(log_path="app.log"):
    logging.getLogger("alembic").setLevel(logging.WARNING)  # evita ruído do Alembic no app.log
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def carregar_transacoes(caminho):
    with open(caminho, "r", encoding="utf-8") as f:
        dados = json.load(f)
    if not isinstance(dados, list):
        raise ValueError("o JSON deve conter uma lista de transações")
    return dados


def processar_transacao(tx: dict, db_path) -> bool:
    """Valida, calcula e salva uma transação. Retorna True se APROVADA."""
    id_tx = tx.get("id_transacao", "DESCONHECIDO")
    cliente_nome = tx.get("cliente", "")
    primeiro, sobrenome = separar_nome(cliente_nome)
    valido, motivo = validar_transacao(tx)

    registro = {
        "id_transacao": id_tx,
        "primeiro_nome": primeiro,
        "sobrenome": sobrenome,
        "cliente": cliente_nome,
        "cpf": tx.get("cpf", "N/A"),
        "idade": tx.get("idade", 0),
        "valor_bruto": tx.get("valor_bruto", 0.0),
        "data_processamento": datetime.now().isoformat(),
    }

    if valido:
        _, valor_final = calcular_desconto_e_final(tx["valor_bruto"], tx["idade"], tx["categoria"])
        registro.update(valor_final=valor_final, status="APROVADO", motivo_rejeicao=None)
        salvar_transacao(registro, db_path=db_path)
        logging.info(f"Transação {id_tx} APROVADA. Cliente: {primeiro} {sobrenome} | "
                     f"Valor Final: R$ {valor_final:.2f}")
        return True

    registro.update(valor_final=0.0, status="REJEITADO", motivo_rejeicao=motivo)
    salvar_transacao(registro, db_path=db_path)
    logging.warning(f"Transação {id_tx} REJEITADA. Motivo: {motivo}")
    return False


def main(caminho_json=ARQUIVO_DADOS, db_path=DB_NAME, log_path="app.log") -> int:
    """Executa o lote. Retorna 0 em sucesso e 1 em falha (usado como exit code no CI)."""
    configurar_logging(log_path)
    logging.info("Iniciando processamento em lote de transações...")
    inicio = time.perf_counter()

    try:
        inicializar_banco(db_path)
    except Exception as e:
        logging.error(f"Erro ao inicializar/migrar o banco de dados: {e}")
        return 1

    try:
        transacoes = carregar_transacoes(caminho_json)
    except Exception as e:
        logging.error(f"Erro ao carregar o arquivo {caminho_json}: {e}")
        return 1

    aprovados = rejeitados = erros = 0
    for tx in transacoes:
        try:
            if processar_transacao(tx, db_path):
                aprovados += 1
            else:
                rejeitados += 1
        except Exception as e:  # um registro ruim não derruba o lote inteiro
            erros += 1
            id_tx = tx.get("id_transacao", "DESCONHECIDO") if isinstance(tx, dict) else "DESCONHECIDO"
            logging.error(f"Falha inesperada ao processar a transação {id_tx}: {e}")

    tempo_ms = (time.perf_counter() - inicio) * 1000
    total = len(transacoes)

    print("=" * 50)
    print("           SUMÁRIO DE PROCESSAMENTO EM LOTE           ")
    print("=" * 50)
    print(f"Total de Registros Processados : {total}")
    print(f"Registros Aprovados            : {aprovados}")
    print(f"Registros Rejeitados           : {rejeitados}")
    if erros:
        print(f"Registros com Erro             : {erros}")
    print(f"Tempo Total de Processamento   : {tempo_ms:.2f} ms")
    print("=" * 50)

    logging.info(f"Processamento concluído. Total: {total}, Aprovados: {aprovados}, "
                 f"Rejeitados: {rejeitados}, Erros: {erros}, Tempo: {tempo_ms:.2f}ms")
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main())
