# Plano — Encurtador de URLs (v1)

Este documento descreve **como** construir o que está em [spec.md](spec.md).
Esta primeira parte reúne as decisões técnicas. Os passos de implementação
serão adicionados abaixo e quebrados em tarefas no [task.md](task.md).

## Stack

| Item | Escolha | Motivo |
|---|---|---|
| Linguagem | Python 3.12+ | Objetivo de aprendizado |
| Framework web | Flask | Objetivo de aprendizado |
| Banco de dados | SQLite via `sqlite3` (biblioteca padrão) | Já vem com Python, é um arquivo só, SQL escrito à mão |
| Templates | Jinja2 (incluso no Flask) | Padrão do Flask |
| Testes | pytest | Padrão da comunidade, simples |
| Dependências | `pyproject.toml` + ambiente virtual (`venv`) | Forma atual e padrão de projetos Python |

## Abordagens consideradas

| Abordagem | Prós | Contras | Decisão |
|---|---|---|---|
| **A. Arquivo único (`app.py`)** | Rápido de começar, igual aos tutoriais | Mistura página, API e regras, o que viola "uma regra, duas portas". Cresce desorganizado e dificulta o login futuro. | Descartada |
| **B. Application factory + blueprints + SQL puro** | Padrão do tutorial oficial do Flask. Separa regras, página e API. Testes fáceis com banco temporário. Ensina SQL de verdade. | Um pouco mais de estrutura no início | **Escolhida** |
| **C. Igual à B + SQLAlchemy + Flask-WTF** | Comum em projetos reais | Duas bibliotecas a mais para aprender junto, e elas escondem o que acontece por baixo | Descartada (pode virar exercício futuro: trocar o `db.py` por SQLAlchemy) |

## Estrutura de pastas

```
encurtador/
├── pyproject.toml
├── specs/                  ← constitution, spec, plan, task
├── src/
│   └── encurtador/
│       ├── __init__.py     ← create_app(): cria e configura o app
│       ├── db.py           ← conexão SQLite, schema, comando `flask init-db`
│       ├── schema.sql      ← CREATE TABLE
│       ├── links.py        ← regras de negócio (sem Flask)
│       ├── web.py          ← blueprint da página
│       ├── api.py          ← blueprint da API (/api)
│       └── templates/
│           ├── base.html
│           ├── index.html
│           ├── info.html
│           └── 404.html
└── tests/
    ├── conftest.py         ← fixtures: app com banco temporário, client
    ├── test_links.py       ← regras de negócio
    ├── test_web.py         ← rotas da página
    └── test_api.py         ← rotas da API
```

## Camadas

```
 Navegador ──► web.py ─┐
                       ├──► links.py ──► db.py ──► SQLite
 curl/API  ──► api.py ─┘
```

- **`links.py`** contém todas as regras da spec (R1–R3). Não importa nada do
  Flask e recebe a conexão do banco como parâmetro, o que facilita testar.
  Sinaliza erros com exceções próprias (ex.: `UrlInvalida`, `CodigoInvalido`,
  `CodigoEmUso`, `LinkNaoEncontrado`), e cada porta traduz essas exceções do
  seu jeito: a página mostra uma mensagem, a API devolve 400, 404 ou 409.
- **`web.py`** e **`api.py`** só fazem a "tradução": leem a requisição, chamam
  `links.py` e montam a resposta (HTML ou JSON).
- **`db.py`** abre e fecha a conexão por requisição (padrão `g` do Flask) e
  cria as tabelas.

## Modelo de dados

```sql
CREATE TABLE links (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo     TEXT    NOT NULL UNIQUE,
    url        TEXT    NOT NULL,
    cliques    INTEGER NOT NULL DEFAULT 0,
    criado_em  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

- O `UNIQUE` em `codigo` é a garantia final contra duplicados, mesmo que duas
  requisições cheguem ao mesmo tempo.
- O SQLite compara texto com distinção entre maiúsculas e minúsculas por padrão,
  o que atende ao R1.6.
- **Login futuro:** basta adicionar uma coluna `usuario_id` (opcional) e uma
  tabela `usuarios`. Nada na v1 impede isso.

## Decisões técnicas importantes

| Decisão | Motivo | Requisito |
|---|---|---|
| Redirecionamento com **302** (temporário), nunca 301, e cabeçalho `Cache-Control: no-store` | O navegador memoriza um 301 e para de passar pelo servidor, e aí os cliques deixam de ser contados | R2.3 |
| Se as 10 tentativas de gerar código colidirem, `links.py` lança um erro, que vira 500 | Na prática não acontece. Um erro explícito é melhor que um laço infinito. | R1.10 |
| A página devolve status **400** quando mostra o formulário com erro (409 para código em uso) | Mesmos status da API, o que também facilita testar | P2 |
| Contar clique com `UPDATE links SET cliques = cliques + 1 WHERE codigo = ?` | Soma atômica no banco, sem ler e reescrever o valor | R2.2 |
| Gerar código com `secrets.choice` sobre `[A-Za-z0-9]`, até 10 tentativas em caso de colisão | Aleatório de verdade, da biblioteca padrão. Com 62⁶ combinações, a colisão é raríssima. | R1.9, R1.10 |
| Validar código com `re.fullmatch(r"[A-Za-z0-9]{5,30}", codigo)` | Uma linha cobre R1.4 e R1.5. `fullmatch` evita que `$` deixe passar uma quebra de linha no final. | R1.4, R1.5 |
| Validar URL com `urllib.parse`: esquema `http`/`https` e `netloc` não vazio | Biblioteca padrão, sem regex complicado | R1.1 |
| Link curto montado com `request.host_url` + código | Funciona em qualquer porta ou host local, sem configuração | P2, A1 |
| Banco em `instance/encurtador.sqlite` (pasta instance do Flask) | Padrão do Flask. A pasta fica fora do Git. | — |
| Testes criam o app com um banco temporário (`tmp_path`) | Cada teste começa limpo e não afeta o banco real | Princípio 3 |
| Nomes do domínio em português (`codigo`, `cliques`, `encurtar`) | Combina com a spec e com os campos da API | — |

## Fica a critério de quem implementa

- Estilo visual da página (CSS simples, ou nenhum).
- Texto exato das mensagens de erro, desde que claras e em português.
- Nomes de funções internas.

---

## Passos de implementação

O passo a passo detalhado, com testes, comandos e commits, está em [task.md](task.md). Resumo:

| # | Tarefa | Entrega | Requisitos |
|---|---|---|---|
| 1 | Esqueleto, factory e banco | App sobe, `flask init-db` cria a tabela | — |
| 2 | Regras de criação (`links.py`) | Validação, código gerado, reservados, duplicados | R1 |
| 3 | Buscar e registrar clique | Consulta e contador atômico | R2.2, R3 |
| 4 | Redirecionamento e 404 | `/<codigo>` com 302 e `no-store` | R2 |
| 5 | Página inicial e de informações | Formulário e `/info/<codigo>` | P1–P3, R3 |
| 6 | API JSON e verificação final | `POST/GET /api/links` e critérios de aceite | A1, A2 |
