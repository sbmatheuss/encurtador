"""Rotas da API JSON (blueprint "api", prefixo /api)."""

from flask import Blueprint, jsonify, request

from . import links
from .db import get_db

api = Blueprint("api", __name__, url_prefix="/api")


def erro(mensagem: str, status: int):
    return jsonify({"erro": mensagem}), status


def para_json(link: links.Link) -> dict:
    return {
        "codigo": link.codigo,
        "url": link.url,
        "curto": links.url_curta(request.host_url, link.codigo),
        "cliques": link.cliques,
    }


@api.post("/links")
def criar():
    # silent=True: corpo ausente ou JSON inválido vira None em vez de exceção.
    corpo = request.get_json(silent=True)
    if not isinstance(corpo, dict):
        return erro("o corpo precisa ser um objeto JSON, ex.: {\"url\": \"https://...\"}", 400)

    url = corpo.get("url")
    codigo = corpo.get("codigo")
    if not isinstance(url, str):
        return erro("o campo \"url\" é obrigatório e deve ser texto", 400)
    if codigo is not None and not isinstance(codigo, str):
        return erro("o campo \"codigo\" deve ser texto", 400)

    try:
        link = links.criar_link(get_db(), url, codigo)
    except (links.UrlInvalida, links.CodigoInvalido) as e:
        return erro(str(e), 400)
    except links.CodigoEmUso as e:
        return erro(str(e), 409)

    return jsonify(para_json(link)), 201


@api.get("/links/<codigo>")
def consultar(codigo: str):
    try:
        link = links.buscar_link(get_db(), codigo)
    except links.LinkNaoEncontrado as e:
        return erro(str(e), 404)
    return jsonify(para_json(link)), 200
