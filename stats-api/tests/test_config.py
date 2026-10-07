from stats_api.config.app import Config
from stats_api.config.urls import _URLS
from tests.conftest import make_test_config


def _urls(config: Config) -> dict[str, str]:
    assert config.URLS is not None
    return config.URLS


def test_every_url_is_constructed():
    urls = _urls(make_test_config())

    assert set(urls) == {url["name"] for url in _URLS}


def test_urls_use_the_configured_scheme_and_rel_path():
    config = make_test_config()
    urls = _urls(config)

    for url in _URLS:
        constructed = urls[url["name"]]

        assert constructed.startswith(f"{config.PREFERRED_URL_SCHEME}://")
        assert constructed.endswith(url["rel_path"])


def test_urls_map_to_the_domain_of_their_group():
    urls = _urls(make_test_config())

    assert urls["home"] == "https://arxiv.org/"  # base
    assert urls["help"] == "https://info.arxiv.org/help"  # help
    assert urls["login"] == "https://arxiv.org/login"  # auth


def test_dev_urls_use_the_dev_servers():
    urls = _urls(
        make_test_config(
            SERVER_NAME="dev.arxiv.org",
            BASE_SERVER="dev.arxiv.org",
            AUTH_SERVER="dev.arxiv.org",
            HELP_SERVER="info.dev.arxiv.org",
        )
    )

    assert urls["home"] == "https://dev.arxiv.org/"
    assert urls["login"] == "https://dev.arxiv.org/login"
    assert urls["help"] == "https://info.dev.arxiv.org/help"
    assert urls["a11y"] == "https://info.dev.arxiv.org/help/web_accessibility.html"
