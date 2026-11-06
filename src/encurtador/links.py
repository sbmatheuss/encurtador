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
    partes = urlsplit(url)
    if partes.scheme.lower() not in {"http", "https"} or not partes.netloc:
        raise UrlInvalida("URL inválida: ela precisa começar com http:// ou https:// e ter um domínio")
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
