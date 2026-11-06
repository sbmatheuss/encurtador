"""Acesso ao banco SQLite: conexão por requisição, schema e comando init-db."""

import sqlite3
from importlib import resources

import click
from flask import Flask, current_app, g
from flask.cli import with_appcontext


def criar_tabelas(conexao: sqlite3.Connection) -> None:
    """Cria (ou recria) as tabelas a partir de schema.sql. Não depende do Flask."""
    schema = resources.files("encurtador").joinpath("schema.sql").read_text(encoding="utf-8")
    conexao.executescript(schema)


def get_db() -> sqlite3.Connection:
    """Devolve a conexão da requisição atual, abrindo-a na primeira chamada."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        # Row permite acessar colunas pelo nome: linha["codigo"].
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None) -> None:
    """Fecha a conexão ao final da requisição (registrado como teardown)."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    criar_tabelas(get_db())


@click.command("init-db")
@with_appcontext
def init_db_command() -> None:
    """Apaga e recria as tabelas do banco."""
    init_db()
    click.echo("Banco inicializado.")


def init_app(app: Flask) -> None:
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
