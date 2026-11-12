"""Teste de ponta a ponta: executa o lote com o dados_processamento.json real."""
import json
import logging
import os

from database import buscar_transacao_por_id
from main import main

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_REAL = os.path.join(RAIZ, "dados_processamento.json")

APROVADOS = {"TX1001": 150.00, "TX1002": 72.00, "TX1003": 425.00, "TX1004": 200.00,
             "TX1007": 850.00, "TX1009": 350.50, "TX10010": 102.00}
REJEITADOS = {"TX1005": "maior que 0", "TX1006": "CPF", "TX1008": "maior que 0"}


def test_json_real_resultado_esperado(tmp_path, capsys):
    db = str(tmp_path / "e2e.db")
    codigo = main(JSON_REAL, db, str(tmp_path / "app.log"))
    saida = capsys.readouterr().out

    assert codigo == 0
    assert "Total de Registros Processados : 10" in saida
    assert "Registros Aprovados            : 7" in saida
    assert "Registros Rejeitados           : 3" in saida
    assert "Tempo Total de Processamento" in saida

    for id_tx, valor_final in APROVADOS.items():
        reg = buscar_transacao_por_id(id_tx, db)
        assert reg["status"] == "APROVADO"
        assert reg["valor_final"] == valor_final
    for id_tx, trecho in REJEITADOS.items():
        reg = buscar_transacao_por_id(id_tx, db)
        assert reg["status"] == "REJEITADO"
        assert trecho in reg["motivo_rejeicao"]


def test_logs_info_e_warning(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    main(JSON_REAL, str(tmp_path / "log.db"), str(tmp_path / "app.log"))
    niveis = [r.levelname for r in caplog.records]
    assert niveis.count("INFO") >= 8
    assert niveis.count("WARNING") == 3
    assert any("TX1005 REJEITADA" in r.getMessage() for r in caplog.records)


def test_arquivo_inexistente_retorna_erro_e_loga_error(tmp_path, caplog):
    codigo = main(str(tmp_path / "nao_existe.json"), str(tmp_path / "x.db"), str(tmp_path / "app.log"))
    assert codigo == 1
    assert any(r.levelname == "ERROR" for r in caplog.records)


def test_json_que_nao_e_lista_retorna_erro(tmp_path):
    arq = tmp_path / "ruim.json"
    arq.write_text('{"a": 1}', encoding="utf-8")
    assert main(str(arq), str(tmp_path / "x.db"), str(tmp_path / "app.log")) == 1


def test_registro_corrompido_nao_derruba_o_lote(tmp_path, caplog, capsys):
    arq = tmp_path / "misto.json"
    arq.write_text(json.dumps([
        "isto nao e um dict",
        {"id_transacao": "OK1", "cliente": "Ana Souza", "cpf": "12345678901",
         "idade": 30, "valor_bruto": 100.0, "categoria": "livros"},
    ]), encoding="utf-8")
    db = str(tmp_path / "misto.db")
    codigo = main(str(arq), db, str(tmp_path / "app.log"))
    assert codigo == 1  # houve erro, mas o item válido foi processado
    assert buscar_transacao_por_id("OK1", db)["valor_final"] == 90.0
    assert any(r.levelname == "ERROR" for r in caplog.records)
    assert "Registros com Erro             : 1" in capsys.readouterr().out
