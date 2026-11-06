import sqlite3

import pytest

from encurtador import create_app
from encurtador.db import criar_tabelas, init_db


@pytest.fixture
def app(tmp_path):
    """App de teste com um banco novo em uma pasta temporária."""
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "teste.sqlite")})
    with app.app_context():
        init_db()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def conexao():
    """Conexão SQLite em memória, sem Flask, para testar as regras de links.py."""
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    criar_tabelas(con)
    yield con
    con.close()
