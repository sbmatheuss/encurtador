"""Regras de negócio do encurtador.

Este módulo é Python puro: não importa nada do Flask. Recebe a conexão do
banco como parâmetro e sinaliza problemas com exceções próprias. A página
(web.py) e a API (api.py) traduzem essas exceções cada uma do seu jeito.
"""

import re
import secrets
import sqlite3
import string
from dataclasses import dataclass
from urllib.parse import urlsplit

CODIGOS_RESERVADOS: frozenset[str] = frozenset({"static", "login", "logout", "admin"})

TAMANHO_MAXIMO_URL = 2048
TAMANHO_CODIGO_GERADO = 6
TENTATIVAS_GERAR_CODIGO = 10
ALFABETO = string.ascii_letters + string.digits  # A-Z, a-z, 0-9 (só ASCII)


class ErroLink(Exception):
    """Base de todos os erros de links. str(erro) é a mensagem para o usuário."""


class UrlInvalida(ErroLink):
    pass


class CodigoInvalido(ErroLink):
    pass


class CodigoEmUso(ErroLink):
    def __init__(self, mensagem: str = "esse código já está em uso"):
        super().__init__(mensagem)


class LinkNaoEncontrado(ErroLink):
    def __init__(self, mensagem: str = "link não encontrado"):
        super().__init__(mensagem)


class FalhaAoGerarCodigo(ErroLink):
    pass


@dataclass(frozen=True)
class Link:
    codigo: str
    url: str
    cliques: int


def validar_url(url: str) -> str:
    """Devolve a URL sem espaços nas pontas, ou lança UrlInvalida."""
    url = url.strip()
    mensagem = "URL inválida: ela precisa começar com http:// ou https:// e ter um domínio"

    # urlsplit ignora silenciosamente \t, \r e \n, mas a URL salva continuaria
    # com eles e quebraria o redirecionamento. Por isso recusamos antes.
    if any(c.isspace() or not c.isprintable() for c in url):
        raise UrlInvalida(mensagem)

    try:
        partes = urlsplit(url)
        partes.port  # lança ValueError se a porta não for um número entre 0 e 65535
    except ValueError:  # ex.: "https://[::1" ou "https://exemplo.com:abc"
        raise UrlInvalida(mensagem) from None

    # hostname (e não netloc): "http://:80" tem netloc ":80", mas nenhum domínio.
    if partes.scheme.lower() not in {"http", "https"} or not partes.hostname:
        raise UrlInvalida(mensagem)
    if len(url) > TAMANHO_MAXIMO_URL:
        raise UrlInvalida(f"URL muito longa: o máximo é {TAMANHO_MAXIMO_URL} caracteres")
    return url


def validar_codigo(codigo: str) -> str:
    """Devolve o código sem espaços nas pontas.

    Primeiro checa o formato (CodigoInvalido), depois os reservados (CodigoEmUso).
    """
    codigo = codigo.strip()
    # fullmatch exige que a string inteira case; [A-Za-z0-9] é só ASCII,
    # então acentos e dígitos Unicode ("１") ficam de fora.
    if not re.fullmatch(r"[A-Za-z0-9]{5,30}", codigo):
        raise CodigoInvalido("código inválido: use de 5 a 30 letras ou números, sem caracteres especiais")
    if codigo.lower() in CODIGOS_RESERVADOS:
        raise CodigoEmUso()
    return codigo


def _sortear_codigo() -> str:
    return "".join(secrets.choice(ALFABETO) for _ in range(TAMANHO_CODIGO_GERADO))


def _codigo_existe(conexao: sqlite3.Connection, codigo: str) -> bool:
    return conexao.execute("SELECT 1 FROM links WHERE codigo = ?", (codigo,)).fetchone() is not None


def gerar_codigo(conexao: sqlite3.Connection) -> str:
    """Sorteia um código livre, com até TENTATIVAS_GERAR_CODIGO tentativas."""
    for _ in range(TENTATIVAS_GERAR_CODIGO):
        codigo = _sortear_codigo()
        if codigo.lower() not in CODIGOS_RESERVADOS and not _codigo_existe(conexao, codigo):
            return codigo
    raise FalhaAoGerarCodigo("não foi possível gerar um código livre; tente novamente")


def criar_link(conexao: sqlite3.Connection, url: str, codigo: str | None = None) -> Link:
    """Valida e salva um novo link. Código None ou só espaços é gerado automaticamente."""
    url = validar_url(url)
    if codigo is None or not codigo.strip():
        codigo = gerar_codigo(conexao)
    else:
        codigo = validar_codigo(codigo)

    try:
        conexao.execute("INSERT INTO links (codigo, url) VALUES (?, ?)", (codigo, url))
        conexao.commit()
    except sqlite3.IntegrityError:
        # O UNIQUE do banco é a garantia final contra códigos repetidos.
        raise CodigoEmUso() from None
    return Link(codigo=codigo, url=url, cliques=0)


def url_curta(base: str, codigo: str) -> str:
    """Monta o link curto completo, ex.: url_curta("http://localhost:5000/", "aB3x9k")."""
    return base.rstrip("/") + "/" + codigo


def buscar_link(conexao: sqlite3.Connection, codigo: str) -> Link:
    """Devolve o link do código, sem alterar os cliques. Lança LinkNaoEncontrado."""
    linha = conexao.execute(
        "SELECT codigo, url, cliques FROM links WHERE codigo = ?", (codigo,)
    ).fetchone()
    if linha is None:
        raise LinkNaoEncontrado()
    return Link(codigo=linha["codigo"], url=linha["url"], cliques=linha["cliques"])


def registrar_clique(conexao: sqlite3.Connection, codigo: str) -> Link:
    """Soma 1 clique ao link e devolve o link atualizado. Lança LinkNaoEncontrado."""
    # A soma acontece dentro do banco ("cliques + 1"), então dois acessos
    # simultâneos nunca se sobrescrevem.
    cursor = conexao.execute("UPDATE links SET cliques = cliques + 1 WHERE codigo = ?", (codigo,))
    conexao.commit()
    if cursor.rowcount == 0:
        raise LinkNaoEncontrado()
    return buscar_link(conexao, codigo)
