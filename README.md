	# Projeto Final: Integração e Entrega Contínua (DevOps)

![CI](https://github.com/nxpoleone/DevOps/actions/workflows/ci.yml/badge.svg)

Aplicação CLI em Python para processamento em lote de transações, com banco SQLite, aplicando:
**testes (pytest)**, **Database DevOps com Expand-Contract (Alembic)**, **CI/CD (GitHub Actions)** e **observabilidade (logs + tempo de execução)**.

> **Grupo:** _(AntonioCampello,EduardoGalvao,JoaoPedroNapoleone,LucasVinicius,MariannaGhiraldelli)_

---

## 📁 Estrutura

```text
.github/workflows/ci.yml        # Esteira CI/CD
alembic/versions/
  001_initial_v1.py             # Schema inicial (coluna 'cliente')
  002_expand_contract_v2.py     # EXPAND: + primeiro_nome/sobrenome, cliente opcional
  003_contract_v3.py            # CONTRACT: remove 'cliente'
tests/
  test_regra_negocio.py         # Unitários (equivalência + valores-limite)
  test_database.py              # Integração (SQLite + Alembic + Dual Write)
  test_migracoes.py             # Expand -> Backfill -> Contract
  test_main.py                  # Ponta a ponta com o JSON real
backfill.py                     # Script de preenchimento dos registros antigos
database.py                     # Persistência (Dual Write, compatibilidade N-1)
main.py                         # CLI + logs + tempo de execução
regra_negocio.py                # Lógica pura (validação e descontos)
dados_processamento.json        # 10 casos de teste
pytest.ini / .flake8 / .gitignore / requirements.txt
```

## 🚀 Como executar

```bash
pip install -r requirements.txt
python -m pytest -v --cov=.     # testes + cobertura
flake8 .                        # linter
python -m alembic upgrade head  # migrações (v1 -> v2 -> v3)
python main.py                  # processa o lote e gera app.log
```

> Se existir um `sistema.db` antigo (de versões anteriores do projeto), apague-o antes: `del sistema.db` (Windows) ou `rm sistema.db`.

---

## 📏 Regras de negócio

| Regra | Comportamento |
|---|---|
| Valor bruto | deve ser > 0 |
| Idade | entre 0 e 120 |
| CPF | exatamente 11 dígitos numéricos (ASCII) |
| Menor de 18 anos + `eletronicos` | transação **rejeitada** |
| Idoso (>= 60) | 15% de desconto |
| Categoria `livros` | 10% de desconto |
| Acúmulo | descontos somam, limitados a **25%** |

**Resultado esperado com o `dados_processamento.json`:** 10 processados, **7 aprovados**, **3 rejeitados** (TX1005 valor negativo, TX1006 CPF curto, TX1008 valor zero).

---

## 🗄️ Database DevOps: Expand-Contract (Zero Downtime)

Objetivo: dividir a coluna `cliente` em `primeiro_nome` + `sobrenome` **sem parar a aplicação**.

| Fase | O que acontece | Onde |
|---|---|---|
| **1. Expand** | Adiciona `primeiro_nome` e `sobrenome` (nulos) e torna `cliente` opcional. A versão antiga (N-1) continua funcionando. | `alembic/versions/002_expand_contract_v2.py` |
| **2. Dual Write** | A aplicação grava no campo legado **e** nos novos (detecta as colunas existentes via `PRAGMA table_info`). | `database.salvar_transacao` |
| **3. Backfill** | Preenche os registros antigos a partir de `cliente`. Idempotente. | `python backfill.py` |
| **4. Contract** | Remove `cliente` e torna as colunas novas `NOT NULL`. Repete o backfill em SQL antes, como rede de segurança. | `alembic/versions/003_contract_v3.py` |

O schema é criado **somente pelo Alembic** (`database.inicializar_banco()` apenas executa `upgrade head`), evitando duas fontes de verdade.
Todas as fases (inclusive `downgrade`) são cobertas por `tests/test_migracoes.py`.

Demonstração manual das fases:

```bash
python -m alembic upgrade 001_initial_v1   # schema antigo
python -m alembic upgrade 002_expand_contract_v2
python backfill.py
python -m alembic upgrade 003_contract_v3  # contract
```

---

## ⚙️ CI/CD (GitHub Actions)

Disparado em todo `push` e `pull_request` para `main` (`.github/workflows/ci.yml`):

1. Checkout + Python 3.10 (com cache de pip)
2. `pip install -r requirements.txt`
3. `flake8` (linter)
4. `pytest` com cobertura
5. `alembic upgrade head`
6. `python main.py` (simulação ponta a ponta)
7. Verificação do banco: 10 registros / 7 aprovados / 3 rejeitados
8. Upload do `app.log` como artefato

Se qualquer etapa falhar, o merge do PR é bloqueado (configurar *branch protection* em `main`).

---

## 🔭 Observabilidade

- Logs no console **e** em `app.log` (`INFO`, `WARNING`, `ERROR`).
- `INFO`: início do lote, cada transação aprovada, conclusão com totais e tempo.
- `WARNING`: cada transação rejeitada, com o motivo.
- `ERROR`: falha ao migrar o banco, ao ler o JSON ou ao processar um registro (o lote continua e o programa termina com *exit code* 1).
- Tempo total medido com `time.perf_counter()` e exibido em milissegundos.

Exemplo de `app.log`:

```text
2026-11-12 14:50:32,061 [WARNING] Transação TX1005 REJEITADA. Motivo: Valor bruto deve ser maior que 0
2026-11-12 14:50:32,096 [INFO] Processamento concluído. Total: 10, Aprovados: 7, Rejeitados: 3, Erros: 0, Tempo: 91.34ms
```

## 🧪 Estratégia de testes

- **Unitários:** particionamento de equivalência e valores-limite (idade 17/18, **59/60**, 0, 120, 121; valor 0 / 0,01; CPF com 10/11/12 dígitos, letras e pontuação).
- **Integração:** `database.py` com SQLite real, Alembic e Dual Write.
- **Migração:** Expand -> Backfill -> Contract e downgrade.
- **Ponta a ponta:** `main.py` com o JSON real e verificação de cada registro.
