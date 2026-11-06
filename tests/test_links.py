import re

import pytest

from encurtador import links
from encurtador.links import (
    CodigoEmUso,
    CodigoInvalido,
    FalhaAoGerarCodigo,
    Link,
    UrlInvalida,
    criar_link,
    gerar_codigo,
    url_curta,
)


def test_criar_link_com_codigo_personalizado(conexao):
    assert criar_link(conexao, "https://exemplo.com", "MeuLink1") == Link("MeuLink1", "https://exemplo.com", 0)


@pytest.mark.parametrize("codigo", [None, "", "   "])
def test_sem_codigo_gera_6_caracteres(conexao, codigo):
    assert re.fullmatch(r"[A-Za-z0-9]{6}", criar_link(conexao, "https://exemplo.com", codigo).codigo)


def test_mesma_url_gera_links_diferentes(conexao):
    assert criar_link(conexao, "https://exemplo.com").codigo != criar_link(conexao, "https://exemplo.com").codigo


@pytest.mark.parametrize(
    "url",
    ["", "exemplo.com", "ftp://exemplo.com", "https://", "javascript:alert(1)", "https://exemplo.com/" + "a" * 2029],
)
def test_url_invalida_e_recusada_sem_salvar(conexao, url):
    with pytest.raises(UrlInvalida):
        criar_link(conexao, url)
    assert conexao.execute("SELECT COUNT(*) FROM links").fetchone()[0] == 0


@pytest.mark.parametrize(
    "url, salva",
    [
        ("http://exemplo.com", "http://exemplo.com"),
        ("HTTPS://Exemplo.com/a?b=1", "HTTPS://Exemplo.com/a?b=1"),
        ("  https://exemplo.com  ", "https://exemplo.com"),
        ("https://exemplo.com/" + "a" * 2028, "https://exemplo.com/" + "a" * 2028),  # exatamente 2048
    ],
)
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
