from encurtador.db import get_db
from encurtador.links import buscar_link, criar_link


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
    client.get("/abcde")
    client.get("/abcde")
    assert cliques(app, "abcde") == 2


def test_codigo_inexistente_mostra_404(client):
    resposta = client.get("/naoexiste")
    assert resposta.status_code == 404
    assert "link não encontrado" in resposta.get_data(as_text=True)


# --- Tarefa 5: formulário e página de informações ---


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
