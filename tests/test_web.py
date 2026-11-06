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
