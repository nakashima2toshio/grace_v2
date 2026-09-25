# chunking/docs/ 棚卸し

**Version 1.0** | 最終更新: 2026-09-25

> 📎 **姉妹版**: [`docs/README.md`](../../docs/README.md)（直下・配置の境界） /
> [`qa_generation/docs/README.md`](../../qa_generation/docs/README.md) /
> [`qa_qdrant/docs/README.md`](../../qa_qdrant/docs/README.md) /
> [`services/docs/README.md`](../../services/docs/README.md)

`chunking/docs/` 配下のドキュメントを一覧化する。**目的から入口を引ける**ようにするのが狙い。
新しく文書を書く／直す前に、まずここを見る。

> 📌 **データ準備 3 工程のうち ① にあたるパッケージ。**
> ② Q/A 生成は [`qa_generation/`](../../qa_generation/docs/README.md)、
> ③ Qdrant 登録は [`qa_qdrant/`](../../qa_qdrant/docs/README.md)。
> 運用手順の入口は [`README_DATA.md`](../../README_DATA.md)。

> ⚠️ **本リポジトリは Anthropic 版。** チャンク化の LLM は Anthropic Claude
> （CLI の `--model` 既定は `claude-haiku-4-5`・日付なしエイリアス）。
> 姉妹リポジトリ `grace_v2_local` は Ollama 版で、`usage.md` / `timing.md` などこちらに無い文書を持つ。
> **索引をコピーで持ち込まないこと**（中身が別物。CLAUDE.md §5）。

---

## 目次

- [1. 目的別の入口](#1-目的別の入口)
- [2. 一覧](#2-一覧)
- [3. 実装カバレッジ](#3-実装カバレッジ)
- [4. 書き分けの約束](#4-書き分けの約束)
- [5. 残タスク](#5-残タスク)
- [6. テスト件数（実測）](#6-テスト件数実測)
- [7. 変更履歴](#7-変更履歴)

---

## 1. 目的別の入口

| やりたいこと | 読む文書 |
|---|---|
| **コマンドをすぐ打ちたい** | [`memo.txt`](memo.txt) — 早見表（正本は `--help` と下の IPO） |
| **関数の入出力・3 段階パイプラインを知る** | [`csv_text_to_chunks_text_csv.md`](csv_text_to_chunks_text_csv.md) |
| **並列制御・リトライ・中断の仕組みを知る** | [`async_api_client.md`](async_api_client.md) |
| **出力ファイル名の決まり** | CLAUDE.md §8.2（常に固定名 `<入力名>_chunks.csv`。`--timestamp` は存在しない） |

---

## 2. 一覧

> 行数・Ver は **2026-09-25 の実測値**（`wc -l` と各文書の Version ヘッダー）。

> 形式の「IPO」は**種別 E**（`a_class_method_md_format.md`。使用例は IPO 詳細の冒頭 `### 4.1`）、
> 「資材」は**種別 D**（`a_cross_doc_md_format.md` §7.2・書式自由）。本索引は種別 C。

| ファイル | 形式 | 内容 | 行数 | Ver | 重要度 |
|---|---|---|---:|---|:--:|
| [`csv_text_to_chunks_text_csv.md`](csv_text_to_chunks_text_csv.md) | IPO | 主モジュールのクラス・関数仕様。アーキテクチャ図・モジュール構成図・3 段階パイプライン・CLI 関数を含む | 1076 | 1.6 | ★★★ |
| [`async_api_client.md`](async_api_client.md) | IPO | `AsyncAPIClient` の仕様。並列制御（Semaphore）・リトライ・連続失敗での中断 | 475 | 2.1 | ★★☆ |
| [`memo.txt`](memo.txt) | 資材 | CLI の早見表（2026-09-24 に現行 CLI へ書き直し済み）。オプション・既定値は 2026-09-25 に実装と突き合わせて一致を確認 | 37 | — | ★☆☆ |

---

## 3. 実装カバレッジ

`chunking/*.py` は **8 件**（`__init__.py` を含む）。専用の IPO 文書があるのは **2 件**。

| 実装 | 行数 | 文書 | 備考 |
|---|---:|---|---|
| `csv_text_to_chunks_text_csv.py` | 1000 | ✅ `csv_text_to_chunks_text_csv.md` | CLI の入口（`python -m chunking.csv_text_to_chunks_text_csv`） |
| `async_api_client.py` | 210 | ✅ `async_api_client.md` |  |
| `checkpoint_manager.py` | 237 | ⚠️ 専用文書なし | `csv_text_to_chunks_text_csv.md` が依存として触れる（`--resume` の仕組み） |
| `regex_string.py` | 182 | ⚠️ 専用文書なし | 同上（依存として名前が出るのみ） |
| `utils.py` | 187 | ⚠️ 専用文書なし | 同上 |
| `__init__.py` | 101 | ⚠️ 専用文書なし | `async_api_client.md` が再エクスポートとして触れる |
| `prompts.py` | 100 | ⚠️ 専用文書なし | 同上（依存として名前が出るのみ） |
| `models.py` | 50 | ⚠️ 専用文書なし | 同上 |

> 小さな補助モジュールまで 1 対 1 で文書を持つ必要は無い。**欠落を把握しておくこと**が目的
> （§5 の残タスク 2）。

---

## 4. 書き分けの約束

| 置き場所 | 書くもの | 書かないもの |
|---|---|---|
| `<module>.md` | IPO（入出力・副作用・使用例） | 運用判断・他モジュールの仕様 |
| `memo.txt` | コマンドの早見表（最小限） | 仕様の説明（IPO へリンク） |
| モジュール docstring | 最小の実行例 | 詳細な手順 |
| 直下 `README_DATA.md` | 3 工程を通した運用手順 | 1 モジュールの IPO |

> IPO 形式の仕様は `.claude/skills/grace-agent-docs/a_class_method_md_format.md`。
> **重複禁止ルールと正本の一覧は [`docs/README.md`](../../docs/README.md) §4 が持つ。**
>
> ⚠️ `memo.txt` は CLI を変えると**真っ先に古くなる**。オプションを変えたら同じコミットで直すこと
> （姉妹リポジトリでは旧コマンドのまま放置され、2026-09-24 に削除された）。

---

## 5. 残タスク

| # | 内容 | 優先 |
|---|---|:--:|
| 1 | `async_api_client.md` が既定モデルを旧既定の `claude-sonnet-4-6` と書いている（**5 箇所**）。実装（`async_api_client.py` の `default_model`）は `claude-sonnet-5`。2026-09-25 に grep で発見 | 中 |
| 2 | 専用 IPO 文書の無い補助モジュールが 6 件ある（§3）。必要になったものから書く | 低 |

---

## 6. テスト件数（実測）

**2026-09-25 に `pytest --collect-only` で数えた値。記憶で書かないこと。**

| テストファイル | 件数 | 対象 |
|---|---:|---|
| `backend/tests/test_chunking_abort.py` | 5 | `async_api_client`（連続失敗での中断） |
| `backend/tests/test_data_jobs.py` | 43 | データ管理タブのジョブ全体。うちチャンク化ジョブの runner・入力検証を含む（**間接**） |
| `backend/tests/test_model_table_coverage.py` | 5 | CLI `--model` 既定が単価・上限表に載っていること（**間接**） |

```bash
uv run --no-sync pytest backend/tests/test_chunking_abort.py -q
```

> ⚠️ `csv_text_to_chunks_text_csv.py`（1,000 行）の 3 段階パイプラインを**直接**検証するテストは無い。
> 実 LLM を要する処理が多いためだが、カバレッジの空白として認識しておくこと。

---

## 7. 変更履歴

| Version | 日付 | 変更 |
|---|---|---|
| 1.0 | 2026-09-25 | 新規作成。`chunking/docs/` には棚卸し索引が無かった（姉妹リポジトリ `grace_v2_local` にはある）。本リポジトリの実ファイルから、文書一覧・実装カバレッジ・テスト件数（実測）・残タスクを記載。`memo.txt` のオプション・既定値を実装と突き合わせて一致を確認し、`async_api_client.md` の既定モデルが旧既定のままであることを残タスク 1 に記録した |
