# Encurtador de URLs (v1) — Plano de Implementação

> **Para agentes:** SUB-SKILL OBRIGATÓRIA: use superpowers:subagent-driven-development (recomendado) ou superpowers:executing-plans para implementar este plano tarefa por tarefa. Os passos usam checkbox (`- [ ]`) para acompanhamento.

**Objetivo:** Um encurtador de URLs local em Flask, com página web e API JSON sobre as mesmas regras, contador de cliques e código personalizado.

**Arquitetura:** Application factory + dois blueprints (`web`, `api`) que só traduzem requisições para as regras de `links.py`. `links.py` é Python puro, recebe a conexão SQLite como parâmetro e sinaliza erros com exceções próprias. SQLite acessado com `sqlite3` e SQL escrito à mão.

**Stack:** Python 3.12+, Flask, Jinja2, sqlite3 (biblioteca padrão), pytest.

**Spec:** [spec.md](spec.md) · decisões técnicas em [plan.md](plan.md) · princípios em [constitution.md](constitution.md)

## Restrições globais

- Python **3.12+**. Dependências: apenas `flask` (execução) e `pytest` (desenvolvimento).
- Layout `src/`: pacote em `src/encurtador/`, testes em `tests/`, instalado com `pip install -e .`.
- `links.py` **não importa Flask**.
- Código personalizado: `re.fullmatch(r"[A-Za-z0-9]{5,30}", codigo)`. O formato é checado **antes** dos reservados.
- Códigos reservados (sem distinção de maiúsculas): `static`, `login`, `logout`, `admin`. Recusa = `CodigoEmUso`.
- Código gerado: 6 caracteres de `[A-Za-z0-9]` via `secrets.choice`, no máximo 10 tentativas.
- URL: esquema `http`/`https`, `netloc` não vazio, no máximo 2048 caracteres.
- Mensagens fixadas pela spec: `"esse código já está em uso"` e `"link não encontrado"`. As demais ficam a critério de quem implementa, em português.
- Redirecionamento: status **302** e `Cache-Control: no-store`.
- Status: dado inválido → 400 · código em uso/reservado → 409 · inexistente → 404 (na página e na API).
- Erros da API: `{"erro": "<mensagem>"}`.
- Nomes do domínio em português.

## Foco da revisão

Entradas que a spec não cita, mas que uma pessoa usando o sistema vai encontrar. Cada uma tem um teste na tarefa indicada.

1. **URL ou código colados com espaços nas pontas** (`"  https://exemplo.com  "`) → aceitos após remover os espaços. *(Tarefa 2)*
2. **Código com acento ou dígitos "largos" do Unicode** (`"açaí1"`, `"１２３４５"`) → recusado. `str.isalnum()` aceitaria esses casos, a regex ASCII não. *(Tarefa 2)*
3. **Esquemas perigosos ou URL sem domínio** (`"javascript:alert(1)"`, `"https://"`), e esquema em maiúsculas (`"HTTPS://Exemplo.com"`) → os dois primeiros são recusados, o último é aceito. *(Tarefa 2)*
4. **URL com HTML exibida na página** (`https://exemplo.com/?q=<script>`) → aparece escapada (`&lt;script&gt;`), nunca executada. *(Tarefa 5)*
5. **JSON que não é um objeto, ou campos com tipo errado** (`[]`, `{"url": 123}`, `{"codigo": null}`) → 400 para os dois primeiros. `codigo: null` é tratado como "não informado". *(Tarefa 6)*

---

### Task 1: Esqueleto do projeto, factory e banco

**Arquivos:**
- Criar: `pyproject.toml`, `.gitignore`
- Criar: `src/encurtador/__init__.py`, `src/encurtador/db.py`, `src/encurtador/schema.sql`
- Criar: `tests/conftest.py`, `tests/test_app.py`

**Interfaces:**
- Produz:
  - `encurtador.create_app(test_config: dict | None = None) -> Flask`. A config padrão é `DATABASE = os.path.join(app.instance_path, "encurtador.sqlite")`, e `test_config` sobrescreve. Cria a pasta `instance`. Chama `db.init_app(app)`. Os blueprints são registrados nas Tarefas 4 e 6.
  - `db.criar_tabelas(conexao: sqlite3.Connection) -> None`: executa `schema.sql` (lido via `importlib.resources`).
  - `db.get_db() -> sqlite3.Connection`: uma conexão por requisição em `g`, com `row_factory = sqlite3.Row`.
  - `db.close_db(e=None) -> None`, `db.init_db() -> None`, `db.init_app(app) -> None` (registra o teardown e o comando `flask init-db`, que imprime `Banco inicializado.`).
  - Fixtures em `conftest.py`: `app` (banco em `tmp_path`, `TESTING=True`, tabelas criadas), `client`, e `conexao` (SQLite `:memory:` com `row_factory = sqlite3.Row` e `criar_tabelas` aplicado, **sem Flask**, para testar `links.py`).

- [ ] **Passo 1: Commitar os documentos de spec já aprovados**

```bash
git add specs/
git commit -m "docs: constituição, spec, plano e tarefas do encurtador v1"
```

- [ ] **Passo 2: Criar `pyproject.toml`, `.gitignore` e o ambiente virtual**

`pyproject.toml`: projeto `encurtador`, `requires-python = ">=3.12"`, `dependencies = ["flask"]`, extra opcional `dev = ["pytest"]`, pacote em `src/`, `schema.sql` e `templates/` incluídos como dados do pacote. Em `[tool.pytest.ini_options]`, defina `testpaths = ["tests"]`.
`.gitignore`: `.venv/`, `instance/`, `__pycache__/`, `*.egg-info/`, `.pytest_cache/`.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```
Esperado: a instalação termina sem erro, e `python -c "import flask"` funciona.

- [ ] **Passo 3: Escrever os testes que falham** (`tests/test_app.py`)

```python
def test_create_app_aceita_config_de_teste(app):
    assert app.testing is True

def test_init_db_cria_tabela_links(app):
    with app.app_context():
        from encurtador.db import get_db
        colunas = [r["name"] for r in get_db().execute("PRAGMA table_info(links)")]
    assert colunas == ["id", "codigo", "url", "cliques", "criado_em"]

def test_comando_init_db(app):
    resultado = app.test_cli_runner().invoke(args=["init-db"])
    assert "Banco inicializado." in resultado.output

def test_fixture_conexao_tem_tabela_sem_flask(conexao):
    assert conexao.execute("SELECT COUNT(*) FROM links").fetchone()[0] == 0
```

- [ ] **Passo 4: Rodar e confirmar que falham**

Rodar: `python -m pytest tests/test_app.py -v`
Esperado: FALHA (`ModuleNotFoundError: encurtador` ou fixture `app` inexistente)

- [ ] **Passo 5: Implementar `__init__.py`, `db.py`, `schema.sql` e `conftest.py`**

`schema.sql` é exatamente o `CREATE TABLE links` do [plan.md](plan.md#modelo-de-dados), precedido de `DROP TABLE IF EXISTS links;`.

- [ ] **Passo 6: Rodar e confirmar que passam**

Rodar: `python -m pytest -v`
Esperado: 4 testes PASSAM

- [ ] **Passo 7: Commit**

```bash
git add pyproject.toml .gitignore src/ tests/
git commit -m "feat: esqueleto do projeto com application factory e SQLite"
```

---

### Task 2: Regras de criação de links (`links.py`)

**Arquivos:**
- Criar: `src/encurtador/links.py`
- Criar: `tests/test_links.py`

**Interfaces:**
- Consome: a fixture `conexao` (Tarefa 1).
- Produz (todos em `encurtador.links`):
  - `CODIGOS_RESERVADOS: frozenset[str] = frozenset({"static", "login", "logout", "admin"})`
  - Exceções: `ErroLink(Exception)` e as subclasses `UrlInvalida`, `CodigoInvalido`, `CodigoEmUso`, `LinkNaoEncontrado`, `FalhaAoGerarCodigo`. `str(exc)` é a mensagem para o usuário. `CodigoEmUso` usa `"esse código já está em uso"` e `LinkNaoEncontrado` usa `"link não encontrado"`.
  - `@dataclass(frozen=True) class Link: codigo: str; url: str; cliques: int`
  - `validar_url(url: str) -> str`: devolve a URL sem espaços nas pontas, ou lança `UrlInvalida`.
  - `validar_codigo(codigo: str) -> str`: devolve o código sem espaços nas pontas. Lança `CodigoInvalido` (formato) ou `CodigoEmUso` (reservado), nessa ordem.
  - `_sortear_codigo() -> str`: 6 caracteres aleatórios. É separado para que os testes possam substituí-lo.
  - `gerar_codigo(conexao: sqlite3.Connection) -> str`: até 10 sorteios, pulando os existentes e os reservados. Se esgotar, lança `FalhaAoGerarCodigo`.
  - `criar_link(conexao: sqlite3.Connection, url: str, codigo: str | None = None) -> Link`: um `codigo` que é `None` ou só espaços faz o sistema gerar um. Faz `INSERT` e `commit`. Um `sqlite3.IntegrityError` vira `CodigoEmUso`.
  - `url_curta(base: str, codigo: str) -> str`: `base.rstrip("/") + "/" + codigo`.

- [ ] **Passo 1: Escrever os testes que falham** (`tests/test_links.py`)

```python
import re, pytest
from encurtador import links
from encurtador.links import (Link, criar_link, url_curta, gerar_codigo,
    UrlInvalida, CodigoInvalido, CodigoEmUso, FalhaAoGerarCodigo)

def test_criar_link_com_codigo_personalizado(conexao):
    assert criar_link(conexao, "https://exemplo.com", "MeuLink1") == Link("MeuLink1", "https://exemplo.com", 0)

@pytest.mark.parametrize("codigo", [None, "", "   "])
def test_sem_codigo_gera_6_caracteres(conexao, codigo):
    assert re.fullmatch(r"[A-Za-z0-9]{6}", criar_link(conexao, "https://exemplo.com", codigo).codigo)

def test_mesma_url_gera_links_diferentes(conexao):
    assert criar_link(conexao, "https://exemplo.com").codigo != criar_link(conexao, "https://exemplo.com").codigo

@pytest.mark.parametrize("url", ["", "exemplo.com", "ftp://exemplo.com", "https://",
                                 "javascript:alert(1)", "https://exemplo.com/" + "a" * 2029])
def test_url_invalida_e_recusada_sem_salvar(conexao, url):
    with pytest.raises(UrlInvalida):
        criar_link(conexao, url)
    assert conexao.execute("SELECT COUNT(*) FROM links").fetchone()[0] == 0

@pytest.mark.parametrize("url, salva", [
    ("http://exemplo.com", "http://exemplo.com"),
    ("HTTPS://Exemplo.com/a?b=1", "HTTPS://Exemplo.com/a?b=1"),
    ("  https://exemplo.com  ", "https://exemplo.com"),
    ("https://exemplo.com/" + "a" * 2028, "https://exemplo.com/" + "a" * 2028),  # exatamente 2048
])
def test_url_valida_e_aceita(conexao, url, salva):
    assert criar_link(conexao, url).url == salva

@pytest.mark.parametrize("codigo", ["abcd", "a" * 31, "meu-link", "meu_link", "meu link", "açaí1", "１２３４５"])
def test_codigo_com_formato_invalido(conexao, codigo):
    with pytest.raises(CodigoInvalido):
        criar_link(conexao, "https://exemplo.com", codigo)

@pytest.mark.parametrize("codigo", ["abcde", "a" * 30, "  abcde  "])
def test_codigo_nos_limites_e_aceito(conexao, codigo):
    assert criar_link(conexao, "https://exemplo.com", codigo).codigo == codigo.strip()

@pytest.mark.parametrize("codigo", ["login", "Login", "ADMIN", "static", "logout"])
def test_codigo_reservado_e_recusado(conexao, codigo):
    with pytest.raises(CodigoEmUso, match="esse código já está em uso"):
        criar_link(conexao, "https://exemplo.com", codigo)

def test_codigo_repetido_nao_sobrescreve(conexao):
    criar_link(conexao, "https://original.com", "abcde")
    with pytest.raises(CodigoEmUso):
        criar_link(conexao, "https://outro.com", "abcde")
    assert conexao.execute("SELECT url FROM links WHERE codigo='abcde'").fetchone()[0] == "https://original.com"

def test_maiusculas_e_minusculas_sao_codigos_diferentes(conexao):
    criar_link(conexao, "https://a.com", "MeuLink")
    assert criar_link(conexao, "https://b.com", "meulink").codigo == "meulink"

def test_gerar_codigo_pula_existentes_e_reservados(conexao, monkeypatch):
    criar_link(conexao, "https://exemplo.com", "abc123")
    sorteios = iter(["abc123", "logout", "xyz789"])
    monkeypatch.setattr(links, "_sortear_codigo", lambda: next(sorteios))
    assert gerar_codigo(conexao) == "xyz789"

def test_gerar_codigo_desiste_apos_10_colisoes(conexao, monkeypatch):
    criar_link(conexao, "https://exemplo.com", "abc123")
    monkeypatch.setattr(links, "_sortear_codigo", lambda: "abc123")
    with pytest.raises(FalhaAoGerarCodigo):
        gerar_codigo(conexao)

def test_url_curta():
    assert url_curta("http://localhost:5000/", "aB3x9k") == "http://localhost:5000/aB3x9k"
```

- [ ] **Passo 2: Rodar e confirmar que falham**

Rodar: `python -m pytest tests/test_links.py -v`
Esperado: FALHA (`ImportError: cannot import name 'Link'`)

- [ ] **Passo 3: Implementar `links.py` com as interfaces acima**

A URL é validada com `urllib.parse.urlsplit`: `scheme.lower() in {"http", "https"}`, `netloc` não vazio e `len <= 2048`, contados depois do `strip()`. Os reservados são comparados com `codigo.lower()`.

- [ ] **Passo 4: Rodar e confirmar que passam**

Rodar: `python -m pytest -v`
Esperado: todos PASSAM

- [ ] **Passo 5: Commit**

```bash
git add src/encurtador/links.py tests/test_links.py
git commit -m "feat: regras de criação de links com validação e código gerado"
```

---

### Task 3: Buscar link e registrar clique

**Arquivos:**
- Modificar: `src/encurtador/links.py`
- Modificar: `tests/test_links.py`

**Interfaces:**
- Consome: `Link`, `criar_link`, `LinkNaoEncontrado` (Tarefa 2).
- Produz:
  - `buscar_link(conexao: sqlite3.Connection, codigo: str) -> Link`: lança `LinkNaoEncontrado`. **Não** altera cliques.
  - `registrar_clique(conexao: sqlite3.Connection, codigo: str) -> Link`: `UPDATE links SET cliques = cliques + 1 WHERE codigo = ?` seguido de `commit`. Se `rowcount == 0`, lança `LinkNaoEncontrado`. Devolve o link já atualizado.

- [ ] **Passo 1: Escrever os testes que falham** (acrescentar em `tests/test_links.py`)

```python
from encurtador.links import buscar_link, registrar_clique, LinkNaoEncontrado

def test_buscar_link_existente(conexao):
    criar_link(conexao, "https://exemplo.com", "abcde")
    assert buscar_link(conexao, "abcde") == Link("abcde", "https://exemplo.com", 0)

def test_buscar_diferencia_maiusculas(conexao):
    criar_link(conexao, "https://exemplo.com", "AbCdE")
    with pytest.raises(LinkNaoEncontrado, match="link não encontrado"):
        buscar_link(conexao, "abcde")

def test_registrar_clique_soma_um_por_acesso(conexao):
    criar_link(conexao, "https://exemplo.com", "abcde")
    registrar_clique(conexao, "abcde")
    assert registrar_clique(conexao, "abcde").cliques == 2

def test_buscar_nao_conta_clique(conexao):
    criar_link(conexao, "https://exemplo.com", "abcde")
    buscar_link(conexao, "abcde"); buscar_link(conexao, "abcde")
    assert buscar_link(conexao, "abcde").cliques == 0

def test_registrar_clique_em_codigo_inexistente(conexao):
    with pytest.raises(LinkNaoEncontrado):
        registrar_clique(conexao, "naoexiste")
```

- [ ] **Passo 2: Rodar e confirmar que falham**

Rodar: `python -m pytest tests/test_links.py -v`
Esperado: FALHA (`ImportError: cannot import name 'buscar_link'`)

- [ ] **Passo 3: Implementar `buscar_link` e `registrar_clique` em `links.py`**

- [ ] **Passo 4: Rodar e confirmar que passam**

Rodar: `python -m pytest -v`
Esperado: todos PASSAM

- [ ] **Passo 5: Commit**

```bash
git add src/encurtador/links.py tests/test_links.py
git commit -m "feat: buscar link e registrar cliques"
```

---

### Task 4: Redirecionamento e página 404

**Arquivos:**
- Criar: `src/encurtador/web.py`
- Criar: `src/encurtador/templates/base.html`, `src/encurtador/templates/404.html`
- Modificar: `src/encurtador/__init__.py` (registrar o blueprint `web`)
- Criar: `tests/test_web.py`

**Interfaces:**
- Consome: `db.get_db()`, `links.registrar_clique`, `links.LinkNaoEncontrado`, `links.criar_link`.
- Produz:
  - Blueprint `web = Blueprint("web", __name__)`, registrado sem prefixo.
  - `GET /<codigo>` → endpoint `web.redirecionar`: 302 para `link.url`, com `Cache-Control: no-store`.
  - `404.html`: estende `base.html` e mostra "link não encontrado". É renderizado com status 404. As Tarefas 5 e 6 reutilizam o mesmo comportamento.
  - `base.html`: layout com o bloco `{% block conteudo %}`, que as Tarefas 5 e 6 usam.

- [ ] **Passo 1: Escrever os testes que falham** (`tests/test_web.py`)

```python
from encurtador.db import get_db
from encurtador.links import criar_link, buscar_link

def criar(app, url, codigo):
    with app.app_context():
        return criar_link(get_db(), url, codigo)

def cliques(app, codigo):
    with app.app_context():
        return buscar_link(get_db(), codigo).cliques

def test_redireciona_com_302_sem_cache(app, client):
    criar(app, "https://exemplo.com/destino", "abcde")
    resposta = client.get("/abcde")
    assert resposta.status_code == 302
    assert resposta.headers["Location"] == "https://exemplo.com/destino"
    assert "no-store" in resposta.headers["Cache-Control"]

def test_cada_acesso_soma_um_clique(app, client):
    criar(app, "https://exemplo.com", "abcde")
    client.get("/abcde"); client.get("/abcde")
    assert cliques(app, "abcde") == 2

def test_codigo_inexistente_mostra_404(client):
    resposta = client.get("/naoexiste")
    assert resposta.status_code == 404
    assert "link não encontrado" in resposta.get_data(as_text=True)
```

- [ ] **Passo 2: Rodar e confirmar que falham**

Rodar: `python -m pytest tests/test_web.py -v`
Esperado: FALHA (404 genérico do Flask ou `Location` ausente)

- [ ] **Passo 3: Implementar `web.py` (rota `redirecionar`), os templates e o registro do blueprint**

- [ ] **Passo 4: Rodar e confirmar que passam**

Rodar: `python -m pytest -v`
Esperado: todos PASSAM

- [ ] **Passo 5: Commit**

```bash
git add src/ tests/test_web.py
git commit -m "feat: redirecionamento do link curto com contagem de cliques"
```

---

### Task 5: Página inicial (formulário) e página de informações

**Arquivos:**
- Modificar: `src/encurtador/web.py`
- Criar: `src/encurtador/templates/index.html`, `src/encurtador/templates/info.html`
- Modificar: `tests/test_web.py`

**Interfaces:**
- Consome: `links.criar_link`, `links.buscar_link`, `links.url_curta`, as exceções de `links` e `base.html`/`404.html` (Tarefa 4).
- Produz:
  - `GET /` → `web.index`: formulário com `<input name="url">` e `<input name="codigo">`.
  - `POST /` → `web.index`: em caso de sucesso, 200 com a URL curta completa (`url_curta(request.host_url, codigo)`) e um link para `url_for("web.info", codigo=...)`. Em caso de erro, mostra o formulário de novo com `str(exc)` e os valores digitados: 400 para `UrlInvalida`/`CodigoInvalido` e 409 para `CodigoEmUso`. Se o campo `codigo` não vier no formulário, é tratado como `None`.
  - `GET /info/<codigo>` → `web.info`: URL original, link curto e total de cliques. Usa `buscar_link`, então **não** conta clique. Para código inexistente, mostra `404.html` com status 404.

- [ ] **Passo 1: Escrever os testes que falham** (acrescentar em `tests/test_web.py`)

```python
def test_pagina_inicial_tem_formulario(client):
    html = client.get("/").get_data(as_text=True)
    assert 'name="url"' in html and 'name="codigo"' in html

def test_encurtar_pelo_formulario(client):
    resposta = client.post("/", data={"url": "https://exemplo.com", "codigo": "MeuLink1"})
    html = resposta.get_data(as_text=True)
    assert resposta.status_code == 200
    assert "http://localhost/MeuLink1" in html
    assert "/info/MeuLink1" in html

def test_formulario_sem_campo_codigo_gera_codigo(client):
    assert client.post("/", data={"url": "https://exemplo.com"}).status_code == 200

def test_url_invalida_mantem_o_que_foi_digitado(client):
    resposta = client.post("/", data={"url": "exemplo.com", "codigo": "MeuLink1"})
    html = resposta.get_data(as_text=True)
    assert resposta.status_code == 400
    assert 'value="exemplo.com"' in html and 'value="MeuLink1"' in html

def test_codigo_em_uso_pelo_formulario(app, client):
    criar(app, "https://exemplo.com", "abcde")
    resposta = client.post("/", data={"url": "https://outro.com", "codigo": "abcde"})
    assert resposta.status_code == 409
    assert "esse código já está em uso" in resposta.get_data(as_text=True)

def test_pagina_info_mostra_dados_e_nao_conta_clique(app, client):
    criar(app, "https://exemplo.com/destino", "abcde")
    client.get("/abcde")
    html = client.get("/info/abcde").get_data(as_text=True)
    assert "https://exemplo.com/destino" in html and "http://localhost/abcde" in html
    assert cliques(app, "abcde") == 1

def test_info_codigo_inexistente(client):
    assert client.get("/info/naoexiste").status_code == 404

def test_info_escapa_html_da_url(app, client):
    criar(app, "https://exemplo.com/?q=<script>", "abcde")
    html = client.get("/info/abcde").get_data(as_text=True)
    assert "<script>" not in html and "&lt;script&gt;" in html
```

- [ ] **Passo 2: Rodar e confirmar que falham**

Rodar: `python -m pytest tests/test_web.py -v`
Esperado: os testes novos FALHAM. Os da Tarefa 4 continuam passando.

- [ ] **Passo 3: Implementar as rotas `index` e `info` e os templates `index.html` e `info.html`**

- [ ] **Passo 4: Rodar e confirmar que passam**

Rodar: `python -m pytest -v`
Esperado: todos PASSAM

- [ ] **Passo 5: Commit**

```bash
git add src/ tests/test_web.py
git commit -m "feat: página para encurtar links e página de informações"
```

---

### Task 6: API JSON e verificação final

**Arquivos:**
- Criar: `src/encurtador/api.py`
- Modificar: `src/encurtador/__init__.py` (registrar o blueprint `api`)
- Criar: `tests/test_api.py`

**Interfaces:**
- Consome: `db.get_db()`, `links.criar_link`, `links.buscar_link`, `links.url_curta`, as exceções de `links`.
- Produz:
  - Blueprint `api = Blueprint("api", __name__, url_prefix="/api")`.
  - `POST /api/links`: lê o corpo com `request.get_json(silent=True)`. O corpo precisa ser um objeto, `url` precisa ser texto, e `codigo` precisa ser texto ou estar ausente/`null`; caso contrário, 400. Em caso de sucesso, 201 com `{"codigo", "url", "curto", "cliques"}`. `UrlInvalida`/`CodigoInvalido` → 400 e `CodigoEmUso` → 409, todos como `{"erro": str(exc)}`.
  - `GET /api/links/<codigo>` → 200 com os mesmos 4 campos. Para código inexistente, 404 com `{"erro": "link não encontrado"}`. Não conta clique.

- [ ] **Passo 1: Escrever os testes que falham** (`tests/test_api.py`)

```python
import pytest

def test_criar_link_com_codigo(client):
    resposta = client.post("/api/links", json={"url": "https://exemplo.com", "codigo": "MeuLink1"})
    assert resposta.status_code == 201
    assert resposta.get_json() == {"codigo": "MeuLink1", "url": "https://exemplo.com",
                                   "curto": "http://localhost/MeuLink1", "cliques": 0}

@pytest.mark.parametrize("corpo", [{"url": "https://exemplo.com"}, {"url": "https://exemplo.com", "codigo": None}])
def test_criar_link_sem_codigo(client, corpo):
    resposta = client.post("/api/links", json=corpo)
    assert resposta.status_code == 201 and len(resposta.get_json()["codigo"]) == 6

@pytest.mark.parametrize("corpo", [{"url": "exemplo.com"}, {"url": "https://exemplo.com", "codigo": "meu-link"},
                                   {}, [], "texto", {"url": 123}, {"url": "https://exemplo.com", "codigo": 12345}])
def test_dados_invalidos_retornam_400(client, corpo):
    resposta = client.post("/api/links", json=corpo)
    assert resposta.status_code == 400 and "erro" in resposta.get_json()

def test_corpo_que_nao_e_json_retorna_400(client):
    resposta = client.post("/api/links", data="url=https://exemplo.com", content_type="text/plain")
    assert resposta.status_code == 400 and "erro" in resposta.get_json()

@pytest.mark.parametrize("codigo", ["abcde", "login"])
def test_codigo_em_uso_ou_reservado_retorna_409(client, codigo):
    client.post("/api/links", json={"url": "https://exemplo.com", "codigo": "abcde"})
    resposta = client.post("/api/links", json={"url": "https://outro.com", "codigo": codigo})
    assert resposta.status_code == 409
    assert resposta.get_json() == {"erro": "esse código já está em uso"}

def test_consultar_link_mostra_cliques_sem_contar(client):
    client.post("/api/links", json={"url": "https://exemplo.com", "codigo": "abcde"})
    client.get("/abcde")
    client.get("/api/links/abcde")
    resposta = client.get("/api/links/abcde")
    assert resposta.status_code == 200 and resposta.get_json()["cliques"] == 1

def test_consultar_inexistente_retorna_404(client):
    resposta = client.get("/api/links/naoexiste")
    assert resposta.status_code == 404
    assert resposta.get_json() == {"erro": "link não encontrado"}
```

- [ ] **Passo 2: Rodar e confirmar que falham**

Rodar: `python -m pytest tests/test_api.py -v`
Esperado: FALHA (404 para `/api/links`)

- [ ] **Passo 3: Implementar `api.py` e registrar o blueprint**

- [ ] **Passo 4: Rodar a suíte completa**

Rodar: `python -m pytest -v`
Esperado: todos PASSAM, sem avisos de erro

- [ ] **Passo 5: Verificação manual (critérios de aceite da spec)**

```powershell
flask --app encurtador init-db
flask --app encurtador run
```
Em outro terminal:
```powershell
curl.exe -s -X POST http://localhost:5000/api/links -H "Content-Type: application/json" -d '{\"url\": \"https://exemplo.com\", \"codigo\": \"teste1\"}'
curl.exe -s -o NUL -w "%{http_code}\n" http://localhost:5000/teste1
curl.exe -s http://localhost:5000/api/links/teste1
```
Esperado: 201 com `"curto": "http://localhost:5000/teste1"`, depois `302`, depois `"cliques": 1`. Depois, abra `http://localhost:5000/` no navegador, encurte uma URL, clique no link curto e veja o contador na página de info.

- [ ] **Passo 6: Commit**

```bash
git add src/ tests/test_api.py
git commit -m "feat: API JSON para criar e consultar links"
```
