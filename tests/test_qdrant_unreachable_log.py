"""Qdrant 未起動時のログが、原因の分かる 1 行になることを守るテスト。

## なぜ必要か

Qdrant を起動せずにエージェントを動かすと、RAG 検索のたびに
`httpx.ConnectError` → `ResponseHandlingException` の **100 行超のトレースバックが
2 回**（コレクション取得と検索）× 再計画の回数だけ出て、本当の原因
（Qdrant が起動していない）が埋もれていた（2026-09-29 実機）。
接続エラーだけは 1 行＋起動コマンドに畳み、それ以外の例外は従来どおり
トレースバックを残す。
"""

import logging

import httpx
from qdrant_client.http.exceptions import ResponseHandlingException

import agent_tools
from qdrant_client_wrapper import QDRANT_START_HINT, is_qdrant_unreachable


def _wrapped_connect_error() -> ResponseHandlingException:
    """qdrant-client が実際に投げる形（ConnectError を包んだ例外）を再現する。"""
    try:
        try:
            raise ConnectionRefusedError(61, "Connection refused")
        except ConnectionRefusedError as inner:
            raise httpx.ConnectError("[Errno 61] Connection refused") from inner
    except httpx.ConnectError as mid:
        wrapped = ResponseHandlingException(mid)
        wrapped.__cause__ = mid
        return wrapped


def test_wrapped_connection_refused_is_detected():
    assert is_qdrant_unreachable(_wrapped_connect_error())


def test_plain_connection_error_is_detected():
    assert is_qdrant_unreachable(ConnectionRefusedError(61, "Connection refused"))


def test_unrelated_errors_are_not_treated_as_unreachable():
    assert not is_qdrant_unreachable(ValueError("bad payload"))
    assert not is_qdrant_unreachable(KeyError("x"))


def test_rag_tool_logs_one_line_without_traceback_when_qdrant_is_down(monkeypatch, caplog):
    def boom():
        raise _wrapped_connect_error()

    monkeypatch.setattr(agent_tools, "get_existing_collections_cached", boom)

    with caplog.at_level(logging.ERROR, logger=agent_tools.logger.name):
        result = agent_tools.search_rag_knowledge_base_structured(
            query="q", collection_name="c"
        )

    # 呼び出し側（executor）がフォールバック判定に使う戻り値は従来どおり
    assert isinstance(result, str) and result.startswith("[[RAG_TOOL_ERROR]]")
    records = [r for r in caplog.records if "RAGツールエラー" in r.getMessage()]
    assert len(records) == 1
    assert records[0].exc_info is None, "接続エラーでトレースバックを出してはいけない"
    assert QDRANT_START_HINT in records[0].getMessage()


def test_rag_tool_keeps_traceback_for_other_errors(monkeypatch, caplog):
    def boom():
        raise RuntimeError("something else")

    monkeypatch.setattr(agent_tools, "get_existing_collections_cached", boom)

    with caplog.at_level(logging.ERROR, logger=agent_tools.logger.name):
        agent_tools.search_rag_knowledge_base_structured(query="q", collection_name="c")

    records = [r for r in caplog.records if "RAGツールエラー" in r.getMessage()]
    assert len(records) == 1
    assert records[0].exc_info is not None
