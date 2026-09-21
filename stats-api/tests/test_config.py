from stats_api.config.app import Config, Database, DevConfig, ProdConfig
from stats_api.config.app import TestConfig as _TestConfig  # not a pytest test class
from stats_api.config.urls import _URLS

_DB = Database(drivername="sqlite", database=":memory:")


def _urls(config: Config) -> dict[str, str]:
    assert config.URLS is not None
    return config.URLS


def test_every_url_is_constructed():
    urls = _urls(_TestConfig())

    assert set(urls) == {url["name"] for url in _URLS}


def test_urls_use_the_configured_scheme_and_rel_path():
    config = _TestConfig()
    urls = _urls(config)

    for url in _URLS:
        constructed = urls[url["name"]]

        assert constructed.startswith(f"{config.PREFERRED_URL_SCHEME}://")
        assert constructed.endswith(url["rel_path"])


def test_urls_map_to_the_domain_of_their_group():
    urls = _urls(ProdConfig(ENV="PROD", DB=_DB))

    assert urls["home"] == "https://arxiv.org/"  # base
    assert urls["help"] == "https://info.arxiv.org/help"  # help
    assert urls["login"] == "https://arxiv.org/login"  # auth


def test_dev_urls_use_the_dev_help_server():
    urls = _urls(DevConfig(ENV="DEV", DB=_DB))

    assert urls["help"] == "https://info.dev.arxiv.org/help"
    assert urls["a11y"] == "https://info.dev.arxiv.org/help/web_accessibility.html"
