def test_create_app_aceita_config_de_teste(app):
    assert app.testing is True


def test_init_db_cria_tabela_links(app):
    with app.app_context():
        from encurtador.db import get_db
        colunas = [r["name"] for r in get_db().execute("PRAGMA table_info(links)")]
    assert colunas == ["id", "codigo", "url", "cliques", "criado_em"]


def test_comando_init_db(app):
    resultado = app.test_cli_runner().invoke(args=["init-db"])
    assert "Banco inicializado." in resultado.output


def test_fixture_conexao_tem_tabela_sem_flask(conexao):
    assert conexao.execute("SELECT COUNT(*) FROM links").fetchone()[0] == 0
