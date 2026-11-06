"""Rotas da página web (blueprint "web")."""

from flask import Blueprint, redirect, render_template

from . import links
from .db import get_db

web = Blueprint("web", __name__)


def pagina_nao_encontrada():
    return render_template("404.html"), 404


@web.get("/<codigo>")
def redirecionar(codigo: str):
    try:
        link = links.registrar_clique(get_db(), codigo)
    except links.LinkNaoEncontrado:
        return pagina_nao_encontrada()

    # 302 (temporário) + no-store: o navegador não memoriza o redirecionamento,
    # então todo acesso passa pelo servidor e o clique é contado.
    resposta = redirect(link.url, code=302)
    resposta.headers["Cache-Control"] = "no-store"
    return resposta
