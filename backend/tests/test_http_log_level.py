"""`httpx` の INFO ログ抑制（コンソールが 1 リクエスト 1 行で埋まるのを防ぐ）のテスト。"""

import logging

import pytest

import config


@pytest.fixture(autouse=True)
def _restore_levels():
    saved = {n: logging.getLogger(n).level for n in ("httpx", "httpcore")}
    yield
    for n, lv in saved.items():
        logging.getLogger(n).setLevel(lv)


def test_httpx_is_quiet_by_default(monkeypatch):
    monkeypatch.delenv("GRACE_HTTP_LOG_LEVEL", raising=False)
    logging.getLogger("httpx").setLevel(logging.INFO)

    config.quiet_noisy_loggers()

    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING


def test_info_requests_are_not_emitted_but_warnings_are(monkeypatch, caplog):
    monkeypatch.delenv("GRACE_HTTP_LOG_LEVEL", raising=False)
    config.quiet_noisy_loggers()

    with caplog.at_level(logging.DEBUG):
        logging.getLogger("httpx").info("HTTP Request: GET http://localhost:6333 200")
        logging.getLogger("httpx").warning("接続に失敗")

    assert "HTTP Request" not in caplog.text
    assert "接続に失敗" in caplog.text


def test_env_var_restores_http_logs(monkeypatch):
    monkeypatch.setenv("GRACE_HTTP_LOG_LEVEL", "info")

    config.quiet_noisy_loggers()

    assert logging.getLogger("httpx").level == logging.INFO


def test_invalid_env_value_falls_back_to_warning(monkeypatch):
    monkeypatch.setenv("GRACE_HTTP_LOG_LEVEL", "not-a-level")

    config.quiet_noisy_loggers()

    assert logging.getLogger("httpx").level == logging.WARNING
