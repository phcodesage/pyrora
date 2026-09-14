from __future__ import annotations

import pytest

from pyrora import Config, ConfigurationError, Container, ServiceNotFoundError


def test_config_precedence_casting_attributes_and_namespace(tmp_path):
    dotenv = tmp_path / ".env"
    dotenv.write_text("ANSWER=from-dotenv\nAPP_DEBUG=no\nBILLING_CURRENCY=EUR\n", encoding="utf-8")
    config = Config(
        {"ANSWER": "from-default", "FALLBACK": "yes"},
        env_file=dotenv,
        environ={"ANSWER": "from-env", "APP_DEBUG": "true"},
    )
    assert config.ANSWER == "from-env"
    assert config.get("FALLBACK", cast=bool) is True
    assert config.get("APP_DEBUG", cast=bool) is True
    assert config.plugin("billing").get("currency") == "EUR"
    config.add_defaults({"BILLING_TIMEOUT": 10})
    assert config.namespace("billing").get("timeout", cast=int) == 10


def test_config_require_errors(tmp_path):
    config = Config(env_file=tmp_path / ".env", environ={})
    with pytest.raises(ConfigurationError, match="SECRET_KEY"):
        config.require("SECRET_KEY")
    with pytest.raises(ConfigurationError, match="bool"):
        Config(env_file=tmp_path / ".env", environ={"VALUE": "perhaps"}).get("VALUE", cast=bool)


def test_container_transient_singleton_instance_and_missing_service():
    class Mailer:
        pass

    container = Container()
    container.bind("mailer", Mailer)
    container.singleton("cache", Mailer)
    settings = {"name": "test"}
    container.instance("settings", settings)
    assert container.resolve("mailer") is not container.resolve("mailer")
    assert container.resolve("cache") is container.resolve("cache")
    assert container.resolve("settings") is settings
    with pytest.raises(ServiceNotFoundError, match="unknown"):
        container.resolve("unknown")
