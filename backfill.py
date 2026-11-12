"""Script de Backfill (Expand-Contract, fase 2).

Preenche primeiro_nome/sobrenome dos registros antigos a partir de 'cliente'.
É idempotente: pode ser executado várias vezes sem efeitos colaterais.

Uso:  python backfill.py [caminho_do_banco]
"""
import logging
import sys

from database import DB_NAME, _colunas_da_tabela, obter_conexao
from regra_negocio import separar_nome


def executar_backfill(db_path=DB_NAME) -> int:
    conn = obter_conexao(db_path)
    try:
        if "cliente" not in _colunas_da_tabela(conn):
            return 0  # Contract já aplicado: nada a fazer
        pendentes = conn.execute(
            "SELECT id_transacao, cliente FROM transacoes WHERE primeiro_nome IS NULL"
        ).fetchall()
        for linha in pendentes:
            primeiro, sobrenome = separar_nome(linha["cliente"])
            conn.execute(
                "UPDATE transacoes SET primeiro_nome = ?, sobrenome = ? WHERE id_transacao = ?",
                (primeiro, sobrenome, linha["id_transacao"]),
            )
        conn.commit()
        return len(pendentes)
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    caminho = sys.argv[1] if len(sys.argv) > 1 else DB_NAME
    total = executar_backfill(caminho)
    logging.info("Backfill concluído: %d registro(s) atualizado(s).", total)
