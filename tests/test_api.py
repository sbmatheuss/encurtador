import pytest


def test_criar_link_com_codigo(client):
    resposta = client.post("/api/links", json={"url": "https://exemplo.com", "codigo": "MeuLink1"})
    assert resposta.status_code == 201
    assert resposta.get_json() == {
        "codigo": "MeuLink1",
        "url": "https://exemplo.com",
        "curto": "http://localhost/MeuLink1",
        "cliques": 0,
    }


@pytest.mark.parametrize("corpo", [{"url": "https://exemplo.com"}, {"url": "https://exemplo.com", "codigo": None}])
def test_criar_link_sem_codigo(client, corpo):
    resposta = client.post("/api/links", json=corpo)
    assert resposta.status_code == 201 and len(resposta.get_json()["codigo"]) == 6


@pytest.mark.parametrize(
    "corpo",
    [
        {"url": "exemplo.com"},
        {"url": "https://exemplo.com", "codigo": "meu-link"},
        {},
        [],
        "texto",
        {"url": 123},
        {"url": "https://exemplo.com", "codigo": 12345},
    ],
)
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
