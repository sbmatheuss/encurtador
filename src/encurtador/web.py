"""Rotas da página web (blueprint "web")."""

from flask import Blueprint, redirect, render_template, request, url_for

from . import links
from .db import get_db

web = Blueprint("web", __name__)


def pagina_nao_encontrada():
    return render_template("404.html"), 404


@web.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html")

    url = request.form.get("url", "")
    codigo = request.form.get("codigo")  # None se o campo não vier no formulário
    try:
        link = links.criar_link(get_db(), url, codigo)
    except (links.UrlInvalida, links.CodigoInvalido) as erro:
        return render_template("index.html", erro=str(erro), url=url, codigo=codigo or ""), 400
    except links.CodigoEmUso as erro:
        return render_template("index.html", erro=str(erro), url=url, codigo=codigo or ""), 409

    return render_template(
        "index.html",
        curto=links.url_curta(request.host_url, link.codigo),
        info=url_for("web.info", codigo=link.codigo),
    )


@web.get("/info/<codigo>")
def info(codigo: str):
    try:
        link = links.buscar_link(get_db(), codigo)  # buscar não conta clique
    except links.LinkNaoEncontrado:
        return pagina_nao_encontrada()
    return render_template("info.html", link=link, curto=links.url_curta(request.host_url, link.codigo))


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
