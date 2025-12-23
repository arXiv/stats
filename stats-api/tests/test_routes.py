from stats_api.routes import stats_ui, stats_api


def test_ui_route_error_on_template_render(app):
    with app.app_context():
        pass


def test_api_route_internal_server_error(app):
    with app.app_context():
        pass
