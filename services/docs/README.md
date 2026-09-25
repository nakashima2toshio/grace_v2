# services/docs/ 棚卸し

**Version 1.0** | 最終更新: 2026-09-25

> 📎 **姉妹版**: [`docs/README.md`](../../docs/README.md)（直下・配置の境界） /
> [`backend/docs/README.md`](../../backend/docs/README.md) /
> [`grace/docs/README.md`](../../grace/docs/README.md) /
> [`chunking/docs/README.md`](../../chunking/docs/README.md) /
> [`qa_qdrant/docs/README.md`](../../qa_qdrant/docs/README.md)

`services/docs/` 配下のドキュメントを一覧化する。**目的から入口を引ける**ようにするのが狙い。
新しく文書を書く／直す前に、まずここを見る。

> ⚠️ **本リポジトリは Anthropic 版。** 姉妹リポジトリ `grace_v2_local`（Ollama 版）にも同じ構成の
> `services/docs/` と索引があるが、**`agent_service` の位置づけ（§4）とテストの揃い方（§6）が違う**。
> 索引をコピーで持ち込まないこと（CLAUDE.md §5）。

---

## 目次

- [1. 目的別の入口](#1-目的別の入口)
- [2. 一覧](#2-一覧)
- [3. 実装カバレッジ](#3-実装カバレッジ)
- [4. `agent_service.py` は Legacy ReAct 経路である](#4-agent_servicepy-は-legacy-react-経路である)
- [5. 書き分けの約束](#5-書き分けの約束)
- [6. テスト件数（実測）](#6-テスト件数実測)
- [7. 残タスク](#7-残タスク)
- [8. 変更履歴](#8-変更履歴)

---

## 1. 目的別の入口

| やりたいこと | 読む文書 |
|---|---|
| **パッケージ全体の構造を知る** | [`__init__.md`](__init__.md) — 再エクスポート対応表つき |
| **Qdrant を操作する** | [`qdrant_service.md`](qdrant_service.md) |
| **データ管理タブの裏側を知る** | [`data_pipeline_service.md`](data_pipeline_service.md) |
| **設定・ロガーを取り回す**（直下 `config.yml` を読む唯一のモジュール） | [`config_service.md`](config_service.md) |
| **トークン数・コストを数える** | [`token_service.md`](token_service.md) |

---

## 2. 一覧

> 行数・Ver は **2026-09-25 の実測値**（`wc -l` と各文書の Version ヘッダー）。

> 11 文書はすべて**種別 E**（IPO 形式・`a_class_method_md_format.md` 準拠。使用例は IPO 詳細の冒頭 `### 4.1`）。本索引は種別 C。

| 文書 | 対象実装 | 実装行数 | 文書行数 | Ver | 重要度 |
|---|---|---:|---:|---|:--:|
| [`__init__.md`](__init__.md) | `__init__.py` — 再エクスポート（`__all__` **50 件**） | 146 | 468 | 1.4 | ★★★ |
| [`qdrant_service.md`](qdrant_service.md) | `qdrant_service.py` — Qdrant CRUD・ヘルスチェック・Embedding 登録 | 1103 | 1542 | 2.2 | ★★★ |
| [`data_pipeline_service.md`](data_pipeline_service.md) | `data_pipeline_service.py` — データ準備の Web 向けラッパ層 | 351 | 513 | 1.1 | ★★★ |
| [`config_service.md`](config_service.md) | `config_service.py` — YAML / 環境変数・ロガー | 289 | 884 | 1.3 | ★★☆ |
| [`token_service.md`](token_service.md) | `token_service.py` — トークンカウント・コスト推定 | 353 | 878 | 1.2 | ★★☆ |
| [`json_service.md`](json_service.md) | `json_service.py` — 安全な JSON 入出力 | 283 | 676 | 1.1 | ★★☆ |
| [`cache_service.md`](cache_service.md) | `cache_service.py` — TTL 付きメモリキャッシュ | 258 | 888 | 1.1 | ★★☆ |
| [`qa_service.md`](qa_service.md) | `qa_service.py` — Q/A 生成（サブプロセス実行） | 174 | 527 | 1.2 | ★★☆ |
| [`log_service.md`](log_service.md) | `log_service.py` — 未回答質問ログ | 89 | 461 | 1.2 | ★☆☆ |
| [`prompts.md`](prompts.md) | `prompts.py` — 共通プロンプト定義 | 32 | 318 | 1.1 | ★☆☆ |
| [`agent_service.md`](agent_service.md) | `agent_service.py` — **Legacy ReAct**（§4 を先に読むこと） | 538 | 619 | 2.3 | ★☆☆ |

> 📌 **`token_service.md` に `gpt-4o` などが並ぶのは誤りではない。** `token_service.py` が持つ
> トークナイザ・単価の**互換辞書**であり、このプロジェクトが使う LLM ではない（同書の冒頭注記）。
> `config_service.md` の `api.openai_api_key` も実装（`config_service.py` の既定設定）どおりである。

---

## 3. 実装カバレッジ

`services/*.py` は **11 件**（`__init__.py` を含む）、対応する `<module>.md` も **11 件**。**欠落は無い**。

> 📌 Streamlit 版アプリ（`ui/`）の名残だった `dataset_service.py` / `file_service.py` は削除済みで、
> 対応する IPO 文書も無い（経緯は [`__init__.md`](__init__.md) の変更履歴 v1.3）。

---

## 4. `agent_service.py` は Legacy ReAct 経路である

Web 経路（`run_support_agent_core` / `run_review_agent_core`）の計画実行は `grace/executor.py` の
通常ステップ（`rag_search` / `web_search` / `reasoning` / `ask_user`）で完結し、`ReActAgent` を通らない。
`agent_parallel_search.py` / `agent_cache.py` と同じ位置づけである（CLAUDE.md §1）。

ただし**コード上の呼び出し元は残っている**（2026-09-25 に `grep -rn "ReActAgent"` で確認）。

| 呼び出し元 | 条件 |
|---|---|
| `grace/executor.py::_execute_legacy_agent_step` | 計画ステップの `action` が `run_legacy_agent` のとき。**プランナのプロンプト（`grace/planner.py::PLAN_GENERATION_PROMPT`）は上の 4 アクションしか提示しない**ので通常は通らないが、スキーマ（`grace/schemas.py::PlanStep.action`）上は許されている |
| `grace/step_trace/benchmark.py` | ベンチマーク計測用 |

> ⚠️ 「本番から 1 件も呼ばれない」と書いた姉妹リポジトリ `grace_v2_local` の索引とは**事情が違う**。
> 引き写さないこと。
>
> 📌 `agent_service.py` の既定モデルは直下 `config.yml` の `models.default`（CLAUDE.md §3.1 の**経路 5**）で決まる。
> `backend/tests/test_model_selection.py::test_top_level_config_yml_default_matches_model_config` が
> `ModelConfig.DEFAULT_MODEL` との一致を検査している。

---

## 5. 書き分けの約束

| 置き場所 | 書くもの | 書かないもの |
|---|---|---|
| `<module>.md` | IPO（入出力・副作用・使用例） | 運用手順・他モジュールの仕様 |
| `__init__.md` | 再エクスポート対応表・パッケージ全体の構造 | 各モジュールの IPO（リンクで参照） |
| `backend/docs/` | `backend/app/**` 側からの呼び出し方 | `services/` 内部の実装 |
| 直下 `docs/` | 2 領域以上にまたがる横断文書 | 1 モジュールの IPO |

> IPO 形式の仕様は `.claude/skills/grace-agent-docs/a_class_method_md_format.md`。
> **重複禁止ルールと正本の一覧は [`docs/README.md`](../../docs/README.md) §4 が持つ。**

---

## 6. テスト件数（実測）

**2026-09-25 に `pytest --collect-only` で数えた値。記憶で書かないこと。**

| テストファイル | 件数 | 対象 |
|---|---:|---|
| `backend/tests/test_data_pipeline.py` | 30 | `data_pipeline_service`・`qdrant_service` |
| `backend/tests/test_data_jobs.py` | 43 | データ管理タブのジョブ全体（`data_pipeline_service` / `qdrant_service` 経由・**間接**） |
| `backend/tests/test_model_selection.py` | 30 | モデル解決の 5 経路。うち 1 件が `config_service` の読む直下 `config.yml`（§4） |

```bash
uv run --no-sync pytest backend/tests/test_data_pipeline.py -q
```

> ⚠️ **本リポジトリには `backend/tests/services/` が無い。** 姉妹リポジトリ `grace_v2_local` は
> `json_service` / `config_service` / `token_service` / `cache_service` / `agent_service` / `qa_service` /
> `log_service` / `qdrant_service` の単体テストをここに持つが、こちらでは上の 3 ファイル以外に
> `services/` を直接検証するテストが無い（§7 の残タスク 1）。

---

## 7. 残タスク

| # | 内容 | 優先 |
|---|---|:--:|
| 1 | `services/` の単体テストが薄い（§6）。姉妹リポジトリの `backend/tests/services/` から、**プロバイダに依存しないもの**（`json_service` / `cache_service` / `token_service` など）を差分を見ながら移植できる。ファイル丸ごとのコピーはしない（CLAUDE.md §5） | 中 |

> 📌 2026-09-25 に 11 文書を CLAUDE.md §9.3 の表記（`OpenAI GPT` / `gemini-2.5-flash` / 現在の既定としての
> `claude-sonnet-4-6` など）で grep した。ヒットは変更履歴の記述と §2 の注記のもの（互換辞書・実装どおりの設定キー）
> だけで、**是正が必要な箇所は無かった**。

---

## 8. 変更履歴

| Version | 日付 | 変更 |
|---|---|---|
| 1.0 | 2026-09-25 | 新規作成。`services/docs/` には棚卸し索引が無かった（姉妹リポジトリ `grace_v2_local` にはある）。本リポジトリの実ファイルから、文書一覧・実装カバレッジ・テスト件数（実測）・残タスクを記載。`ReActAgent` の呼び出し元を grep し、`grace/executor.py` の `run_legacy_agent` 分岐が残っていること（プランナは提示しない）を §4 に記録した |
