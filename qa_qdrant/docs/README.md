# qa_qdrant/docs/ 棚卸し

**Version 1.7** | 最終更新: 2026-09-26

> 📎 **姉妹版**: [`docs/README.md`](../../docs/README.md)（直下・配置の境界） /
> [`chunking/docs/README.md`](../../chunking/docs/README.md) /
> [`qa_generation/docs/README.md`](../../qa_generation/docs/README.md) /
> [`services/docs/README.md`](../../services/docs/README.md)

`qa_qdrant/docs/` 配下のドキュメントを一覧化する。**目的から入口を引ける**ようにするのが狙い。

本ディレクトリは **12 文書**あり、手順書・IPO・設計・比較検討メモが混在している。
§2 で形式を明示するので、目的に合わない形式を開かないこと。

> 📌 **データ準備 3 工程のうち ③ にあたるパッケージ。**
> ① チャンク化は [`chunking/`](../../chunking/docs/README.md)、
> ② Q/A 生成は [`qa_generation/`](../../qa_generation/docs/README.md)。
> 運用手順の入口は [`README_DATA.md`](../../README_DATA.md)。

> ⚠️ **本リポジトリは Anthropic 版。** Q/A 生成の LLM は Anthropic Claude（`--model` 既定 `claude-sonnet-5`）、
> Embedding は Gemini `gemini-embedding-001`（3072 次元）。
> 姉妹リポジトリ `grace_v2_local` は Ollama 版で、同名の文書でも**プロバイダ表記は逆**である。

---

## 目次

- [1. 目的別の入口](#1-目的別の入口)
- [2. 一覧](#2-一覧)
- [3. 実装カバレッジ](#3-実装カバレッジ)
- [4. `qa_qdrant/__init__.py` は docstring だけ](#4-qa_qdrant__init__py-は-docstring-だけ)
- [5. 書き分けの約束](#5-書き分けの約束)
- [6. 残タスク](#6-残タスク)
- [7. テスト件数（実測）](#7-テスト件数実測)
- [8. 変更履歴](#8-変更履歴)

---

## 1. 目的別の入口

| やりたいこと | 読む文書 |
|---|---|
| **環境を作る**（MeCab / Docker / Celery / API キー） | [`01_install.md`](01_install.md) — **唯一の入口** |
| **Celery 並列を動かす** | [`celery_quick_start.md`](celery_quick_start.md) |
| **生成 → 登録を 1 本で回す** | [`make_qa_register_qdrant.md`](make_qa_register_qdrant.md)（手順）/ [`make_qa_register_qdrant_ipo.md`](make_qa_register_qdrant_ipo.md)（仕様・既知の問題） |
| **既存 CSV を登録するだけ** | [`register_to_qdrant.md`](register_to_qdrant.md) |
| **コレクションを消す** | [`qdrant_delete_collection.md`](qdrant_delete_collection.md) |
| **システム全体の設計を知る** | [`qa_qdrant_architecture.md`](qa_qdrant_architecture.md) |
| **なぜ Celery なのか / なぜスマート生成なのか** | [`asyncio_vs_celery.md`](asyncio_vs_celery.md) / [`generation_vs_SmartGeneration.md`](generation_vs_SmartGeneration.md) |

---

## 2. 一覧

> 行数・Ver は **2026-09-25 の実測値**（`wc -l` と各文書の Version ヘッダー）。

### 2.1 手順書

**種別 B**（`a_cross_doc_md_format.md` §6。概要に状態・結論・対象モジュール）。

| 文書 | 内容 | 行数 | Ver | 重要度 |
|---|---|---:|---|:--:|
| [`01_install.md`](01_install.md) | 環境構築。MeCab・Docker（Qdrant / Redis）・Celery・API キー。**運用の唯一の入口** | 859 | 2.3 | ★★★ |
| [`celery_quick_start.md`](celery_quick_start.md) | Celery ワーカーの起動手順（`-A celery_config`。キュー名に `qa_generation` は無い・CLAUDE.md §9.4） | 523 | 2.3 | ★★☆ |
| [`make_qa_register_qdrant.md`](make_qa_register_qdrant.md) | `make_qa_register_qdrant.py`（Q/A 生成 → Qdrant 登録の統合 CLI）の使い方。**IPO ではない**。冒頭で「一部古い（2025-01 の改修時の記述を含む）」と明示している | 948 | 1.6 | ★★★ |

### 2.2 IPO（モジュール仕様）

**種別 E**（`a_class_method_md_format.md`。使用例は IPO 詳細の冒頭 `### 4.1`）。

| 文書 | 対象実装 | 実装行数 | 文書行数 | Ver | 重要度 |
|---|---|---:|---:|---|:--:|
| [`register_to_qdrant.md`](register_to_qdrant.md) | `register_to_qdrant.py` — 既存 CSV → Qdrant | 587 | 586 | 2.1 | ★★★ |
| [`make_qa.md`](make_qa.md) | `make_qa.py` — Q/A 生成のみの CLI | 265 | 448 | 3.3 | ★★☆ |
| [`qdrant_delete_collection.md`](qdrant_delete_collection.md) | **`qdrant_delete_collection.py`（リポジトリ直下）** — コレクション削除 CLI | 73 | 304 | 1.1 | ★★☆ |
| [`make_qa_register_qdrant_ipo.md`](make_qa_register_qdrant_ipo.md) | `make_qa_register_qdrant.py` — Q/A 生成 → Qdrant 登録の統合 CLI。§3.3 の既知の問題 5 件は修正済み | 708 | 693 | 1.4 | ★★★ |
| [`make_qa_qapipeline.md`](make_qa_qapipeline.md) | `QAPipeline` ＋ `SmartQAGenerator` の連携（**実体は `qa_generation/`**） | — | 936 | 1.2 | ★★☆ |

> ⚠️ **`qdrant_delete_collection.md` の対象はこのパッケージの外にある**（リポジトリ直下の
> `qdrant_delete_collection.py`）。関連が深いためここに置いているが、探すときは注意。
>
> ⚠️ **`make_qa_qapipeline.md` は `qa_generation/` の実装を説明している。**
> モジュール単位の IPO は [`qa_generation/docs/pipeline.md`](../../qa_generation/docs/pipeline.md) /
> [`smart_qa_generator.md`](../../qa_generation/docs/smart_qa_generator.md) が正本。
> 本書は**両者の連携**を扱う横断文書として読むこと。

### 2.3 設計・比較検討

`qa_qdrant_architecture.md` は**種別 A**（横断文書）、ほかの 4 件は**種別 B**（比較検討・改修の記録。
本文は当時のまま残し、概要で現在の状態を示す）。

| 文書 | 内容 | 行数 | Ver | 重要度 |
|---|---|---:|---|:--:|
| [`qa_qdrant_architecture.md`](qa_qdrant_architecture.md) | Q/A 生成 & Qdrant 登録システムの設計書（v3.0） | 797 | 3.2 | ★★☆ |
| [`asyncio_vs_celery.md`](asyncio_vs_celery.md) | 並列方式の比較分析（なぜ Celery か） | 693 | 1.1 | ★☆☆ |
| [`generation_vs_SmartGeneration.md`](generation_vs_SmartGeneration.md) | Q/A 生成方式の比較（なぜ SmartGeneration 一本化か） | 691 | 1.1 | ★☆☆ |
| [`smart_generation_upgrade.md`](smart_generation_upgrade.md) | スマート生成デフォルト化の改修サマリー | 503 | 1.1 | ★☆☆ |
| [`00_learning.md`](00_learning.md) | 学習順の構成比較メモ ＋ カテゴリー別一覧 | 373 | 1.1 | ★☆☆ |

> 📌 **比較検討メモ（種別 B）に出てくる `gemini-2.0-flash` などは当時の記録**である。
> 意思決定の経緯として残しているので、現在の既定へ書き換えない。

### 2.4 資材

| ファイル | 内容 |
|---|---|
| `img_make_qa_register_qdrant.png` | 統合 CLI（`make_qa_register_qdrant.py`）の全体像を 1 枚にまとめた図。Phase 1（Q/A 生成）→ Phase 2（Qdrant 登録）と、入力形式（.txt / Q/A あり CSV / 本文のみ CSV）ごとの処理の違い。**どの文書からも参照されていない**（2026-09-25 grep） |

---

## 3. 実装カバレッジ

`qa_qdrant/*.py` は **4 件**（`__init__.py` を含む）。

| 実装 | 行数 | 文書 | 備考 |
|---|---:|---|---|
| `make_qa_register_qdrant.py` | 708 | ✅ `make_qa_register_qdrant_ipo.md`（IPO）＋ `make_qa_register_qdrant.md`（手順書） | 同名の手順書が先にあったため IPO は `_ipo` 付きの名前 |
| `register_to_qdrant.py` | 587 | ✅ `register_to_qdrant.md` | データ管理タブの Qdrant 登録ジョブも使う |
| `make_qa.py` | 265 | ✅ `make_qa.md` |  |
| `__init__.py` | 26 | — | **docstring のみ**（§4）。処理を書かないこと |

---

## 4. `qa_qdrant/__init__.py` は docstring だけ

2026-09-25 まで、`__init__.py` には **`make_qa.py` の古い写し（236 行・`main()` まで含む）**が入っていた。

- `backend/app/core/data_jobs.py` の Qdrant 登録ジョブは `from qa_qdrant.register_to_qdrant import ...` を実行する。
  パッケージの `__init__.py` はパッケージ内のどのモジュールを import しても先に実行されるため、
  登録ジョブのたびに `config` と `qa_generation.pipeline` まで読み込まれていた
  （`import qa_qdrant` だけで **1,406 モジュール → 整理後 35**）。
- `main` / `PROJECT_ROOT` / `logger` を `qa_qdrant` から参照するコードは無かった（grep 実測）。

整理後は docstring だけにし、`backend/tests/test_qa_qdrant_package_init.py`（2 件）で
「docstring 以外を書き戻していない」「`import qa_qdrant` で `qa_generation` / `config` が載らない」を固定した。
経緯は [`qa_generation/docs/__init__.md`](../../qa_generation/docs/__init__.md) §4
（姉妹リポジトリ `grace_v2_local` は 2026-09-21 に同じ整理を実施済み）。

---

## 5. 書き分けの約束

**運用手順は `01_install.md` にだけ書く。** 同じ手順を複数箇所に書くと、
片方だけ直したときに食い違う。

| 置き場所 | 書くもの | 書かないもの |
|---|---|---|
| `01_install.md` | 環境構築・前提・起動手順 | モジュールの内部実装 |
| `celery_quick_start.md` | Celery 固有の起動・監視 | 環境構築全般（`01_install.md` へリンク） |
| `<module>.md` | IPO（入出力・副作用・CLI 引数） | 環境構築手順 |
| 比較検討メモ | **なぜその方式を選んだか**（意思決定の記録） | 現在の仕様（`<module>.md` が正本） |

> IPO 形式の仕様は `.claude/skills/grace-agent-docs/a_class_method_md_format.md`。
> **重複禁止ルールと正本の一覧は [`docs/README.md`](../../docs/README.md) §4 が持つ。**

---

## 6. 残タスク

2026-09-25 に、CLAUDE.md §9.3 の表記（現在の既定は `claude-sonnet-5`）と実装値を突き合わせて見つけたもの。
**種別 B の比較検討メモ（§2.3）は当時の記録なので対象外。**

| # | 内容 | 優先 |
|---|---|:--:|
| 1 | ~~現在の既定モデルを旧既定 `claude-sonnet-4-6` と書いている（`make_qa.md` 3・`qa_qdrant_architecture.md` 4・`01_install.md` 3 箇所）~~ | ✅ **完了**（2026-09-25）。実装どおり `claude-sonnet-5` へ是正（make_qa v3.3 / architecture v3.2 / 01_install v2.3） |
| 2 | ~~`make_qa_register_qdrant.md` の `--model` 既定（`gemini-2.0-flash`）と `qa_qdrant_architecture.md` の環境変数例~~ | ✅ **完了**（2026-09-25）。前者は概要で現在の既定 `claude-sonnet-5` を明示（v1.2）し、2026-09-26 に §7 の本文の値も `claude-sonnet-5` へ直した（v1.6）。後者は §9 を実装が読む環境変数（`ANTHROPIC_API_KEY` 必須・`REDIS_URL`）へ書き直した |
| 3 | ~~`make_qa_register_qdrant.py` の IPO 文書が無い~~ | ✅ **完了**（2026-09-25）。[`make_qa_register_qdrant_ipo.md`](make_qa_register_qdrant_ipo.md) を新設 |
| 4 | `make_qa_register_qdrant.py` の既知の問題（IPO 文書 §3.3・2026-09-25 実測）。~~① `.txt` 入力は必ず失敗する~~（✅ 2026-09-25 修正・先にチャンク化する）~~② Qdrant 登録が失敗しても終了コード 0~~（✅ 2026-09-25 修正） ~~③ `--provider` が効かない~~（✅ 2026-09-25 修正・`gemini` 以外は終了コード 2）~~④ `--text-column` が Q/A 生成に渡らない~~（✅ 2026-09-25 修正・`QAPipeline(text_column=...)` へ渡す）~~⑤ 起動時に `ANTHROPIC_API_KEY` を確かめない~~（✅ 2026-09-25 修正・Q/A 生成の前に確かめる）。**5 件とも完了** | ✅ |

> 📌 **誤りではないもの（直さない）**:
> - `register_to_qdrant.md` の `openai` / `OPENAI_API_KEY` — `register_to_qdrant.py` の `--provider` が
>   `gemini` / `openai` を実際に受け付ける（Embedding の選択肢）。
> - `qdrant_delete_collection.md` の `*_anthropic` — **実際のコレクション名**である
>   （`backend/app/core/verticals.py` などで使用）。

---

## 7. テスト件数（実測）

**2026-09-25 に `pytest --collect-only` で数えた値。記憶で書かないこと。**

| テストファイル | 件数 | 対象 |
|---|---:|---|
| `backend/tests/test_qa_qdrant_package_init.py` | 2 | `__init__.py` が docstring だけであること・import 副作用が無いこと（§4） |
| `backend/tests/test_make_qa_register_qdrant_txt_input.py` | 3 | `make_qa_register_qdrant.py` の `.txt` 入力（先にチャンク化してから Q/A 生成へ渡すこと・空の本文／`ANTHROPIC_API_KEY` 無しで終了コード 1） |
| `backend/tests/test_make_qa_register_qdrant_startup_checks.py` | 4 | `make_qa_register_qdrant.py` の起動時チェック（Q/A 生成の前に `ANTHROPIC_API_KEY` が無ければ終了コード 1・Q/A 済み CSV の登録では不要・`--provider` の `gemini` 以外は終了コード 2） |
| `backend/tests/test_qa_pipeline_text_column.py` | 6 | `--text-column` が `QAPipeline(text_column=...)` へ渡ること（CLI 3 件）と、`QAPipeline` 側の指定列の優先・欠落時の ValueError・未指定時の自動検出（3 件） |
| `backend/tests/test_make_qa_register_qdrant_exit_code.py` | 2 | `make_qa_register_qdrant.py` の `main()` が、Qdrant 登録の失敗で終了コード 1・成功で正常終了すること |
| `backend/tests/test_data_jobs.py` | 43 | データ管理タブのジョブ全体。うち Qdrant 登録ジョブの runner（`register_to_qdrant` を呼ぶ）を含む（**間接**） |
| `backend/tests/test_model_table_coverage.py` | 5 | CLI `--model` 既定が単価・上限表に載っていること（**間接**） |

```bash
uv run --no-sync pytest backend/tests/test_qa_qdrant_package_init.py -q
```

> ⚠️ **テストは薄い。** `register_to_qdrant.py`（587 行）・`make_qa.py`（265 行）・
> `make_qa_register_qdrant.py`（708 行）は終了コード・`.txt` 入力・起動時チェック・`--text-column` の受け渡しの 12 件だけで、Q/A 生成・登録の中身を**直接**検証するテストは無い。
> 実 Qdrant・実 LLM を要する処理が多いためだが、カバレッジの空白として認識しておくこと。

---

## 8. 変更履歴

| Version | 日付 | 変更 |
|---|---|---|
| 1.7 | 2026-09-26 | `make_qa_register_qdrant.md` v1.6（§7 の `--model` 既定を `claude-sonnet-5` へ是正）に追随。§2 の行数・Ver と残タスク 2 の注記を更新 |
| 1.6 | 2026-09-25 | 残タスク 4 の④（`--text-column` が Q/A 生成に渡らない）を修正し、残タスク 4 を完了。§2・§3 の行数・Ver と §7 に `test_qa_pipeline_text_column.py` を追加 |
| 1.5 | 2026-09-25 | 残タスク 4 の③（`--provider` が効かない）と⑤（`ANTHROPIC_API_KEY` を起動時に確かめない）を修正したのに追随。§2・§3 の行数・Ver と §7 に `test_make_qa_register_qdrant_startup_checks.py` を追加 |
| 1.4 | 2026-09-25 | 残タスク 4 の①（`.txt` 入力が必ず失敗する）を修正したのに追随。§2・§3 の行数・Ver（§3 の実装行数は v1.3 で 609 のまま取り残していた）と §7 に `test_make_qa_register_qdrant_txt_input.py` を追加 |
| 1.3 | 2026-09-25 | 残タスク 4 の②（登録失敗でも終了コード 0）を修正したのに追随。§2.2・§7 に `test_make_qa_register_qdrant_exit_code.py` を追加 |
| 1.2 | 2026-09-25 | 残タスク 3 を完了（`make_qa_register_qdrant_ipo.md` を新設し §1・§2.2・§3 に追加）。仕様書の作成時に実測した既知の問題 5 件を残タスク 4 として記録 |
| 1.1 | 2026-09-25 | 残タスク 1・2（既定モデルの記述・環境変数例）を完了し、§2 の行数・Ver を更新 |
| 1.0 | 2026-09-25 | 新規作成。`qa_qdrant/docs/` には棚卸し索引が無かった（姉妹リポジトリ `grace_v2_local` にはある）。本リポジトリの実ファイルから 12 文書を形式別（手順書 / IPO / 設計・比較）に整理し、実装カバレッジ・`__init__.py` の整理の経緯・テスト件数（実測）を記載。既定モデルの表記と実装値を突き合わせ、残タスク 3 件を記録した |
