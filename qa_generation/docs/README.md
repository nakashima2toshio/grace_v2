# qa_generation/docs/ 棚卸し

**Version 1.13** | 最終更新: 2026-09-26

> 📎 **姉妹版**: [`docs/README.md`](../../docs/README.md)（直下・配置の境界） /
> [`grace/docs/README.md`](../../grace/docs/README.md) /
> [`backend/docs/README.md`](../../backend/docs/README.md) /
> [`chunking/docs/README.md`](../../chunking/docs/README.md) /
> [`qa_qdrant/docs/README.md`](../../qa_qdrant/docs/README.md) /
> [`services/docs/README.md`](../../services/docs/README.md)

`qa_generation/docs/` 配下のドキュメントを一覧化する。**目的から入口を引ける**ようにするのが狙い。
新しく文書を書く／直す前に、まずここを見る。

> 📌 **データ準備 3 工程のうち ② にあたるパッケージ。**
> ① チャンク化は [`chunking/`](../../chunking/docs/README.md)、③ Qdrant 登録は [`qa_qdrant/`](../../qa_qdrant/docs/README.md)。
> 運用手順の入口は [`README_DATA.md`](../../README_DATA.md)。

> ⚠️ **本リポジトリは Anthropic 版。** LLM は `claude-sonnet-5`（`create_llm_client("anthropic")`）、
> Embedding のみ Gemini `gemini-embedding-001`（3072 次元）。
> 姉妹リポジトリ `grace_v2_local` は Ollama 版で、**プロバイダ表記はあちらと逆**である。
> 「Anthropic と書いてあるから誤記」ではない（CLAUDE.md §3）。

---

## 目次

- [1. 目的別の入口](#1-目的別の入口)
- [2. 一覧](#2-一覧)
- [3. 実装カバレッジ](#3-実装カバレッジ)
- [4. 棚卸しで分かったこと](#4-棚卸しで分かったこと)
- [5. 書き分けの約束](#5-書き分けの約束)
- [6. 残タスク](#6-残タスク)
- [7. テスト](#7-テスト)
- [8. 変更履歴](#8-変更履歴)

---

## 1. 目的別の入口

| やりたいこと | 読む文書 |
|---|---|
| **パイプライン全体の流れを知る** | [`pipeline.md`](pipeline.md) |
| **Q/A をどう生成しているか** | [`smart_qa_generator.md`](smart_qa_generator.md) |
| **カバレージをどう測るか** | [`semantic.md`](semantic.md) / [`evaluation.md`](evaluation.md) |
| **CLI から動かす** | [`../../qa_qdrant/docs/01_install.md`](../../qa_qdrant/docs/01_install.md) §6 |
| **Web（データ管理タブ）から動かす** | [`../../backend/docs/data_pipeline.md`](../../backend/docs/data_pipeline.md) |
| **入力 CSV の読み方・出力ファイルの仕様を知る** | [`data_io.md`](data_io.md) |
| **Q/A のスキーマ（Pydantic）を知る** | [`models.md`](models.md) |
| **パッケージの公開 API・import 副作用を知る** | [`__init__.md`](__init__.md) |

---

## 2. 一覧

> 行数は **2026-09-24 の実測値**（`wc -l`）。
> 2026-09-26 に Embedding の記述を改訂した文書（`gemini-embedding-2` への変更と、同日の `gemini-embedding-001` への戻し）の行は、同日に再実測した。
>
> 7 文書はすべて**種別 E**（IPO 形式・`a_class_method_md_format.md` 準拠。使用例は IPO 詳細の冒頭）。
> 本索引自体は種別 C（`a_cross_doc_md_format.md` §7.1）。

| 文書 | 対象実装 | 実装行数 | 文書行数 | Ver | 重要度 |
|---|---|---:|---:|---|:--:|
| [`pipeline.md`](pipeline.md) | `pipeline.py` — `QAPipeline`（Web / CLI 共通の実体） | 569 | 812 | 1.5 | ★★★ |
| [`smart_qa_generator.md`](smart_qa_generator.md) | `smart_qa_generator.py` — `SmartQAGenerator`（構造化出力 1 回） | 300 | 572 | 1.2 | ★★★ |
| [`semantic.md`](semantic.md) | `semantic.py` — `SemanticCoverage`（Embedding によるカバレージ） | 543 | 780 | 1.3 | ★★☆ |
| [`evaluation.md`](evaluation.md) | `evaluation.py` — `analyze_coverage()` ほか | 316 | 822 | 1.3 | ★★☆ |
| [`data_io.md`](data_io.md) | `data_io.py` — 入力 CSV の読み込みと結果 4 ファイルの保存 | 168 | 481 | 1.2 | ★★☆ |
| [`models.md`](models.md) | `models.py` — Pydantic モデル 8 クラス（`QAPair` / `QAPairsList` は直下 `models.py` から再エクスポート） | 149 | 422 | 1.4 | ★☆☆ |
| [`__init__.md`](__init__.md) | `__init__.py` — 公開 API（再エクスポート 11 件） | 65 | 302 | 1.5 | ★☆☆ |

---

## 3. 実装カバレッジ

`qa_generation/*.py` は **7 件**（`__init__.py` を含む）、対応する `<module>.md` も **7 件**。
**2026-09-24 に欠落 3 件（`data_io` / `models` / `__init__`）を作成し、1:1 対応が揃った**（§6 の残タスク 1）。

> 3 件は姉妹リポジトリ `grace_v2_local` の同名文書を構成の参考にしたが、実装（作成時点で `data_io.py` / `__init__.py` は
> 同一、`models.py` は docstring のみ差あり）を読み直し、**本リポジトリの実測値で書き起こした**。
> 作成時点では `__init__.md` の import 副作用だけ「あちらは解消済み・こちらは未解消」で内容が逆だったが、
> 2026-09-24 にこちらも解消した（§4 の 1）。
> その後 `data_io.py` は本リポジトリ側だけ `"nan"` 混入を修正した（§4 の 5）ので、**今は同一ではない**。

---

## 4. 棚卸しで分かったこと

2026-09-24 に実装を読んで確認した。いずれも**機能上の不具合ではない**が、誤解や無駄を生む。

| # | 内容 | 根拠（実測） | 扱い |
|---|---|---|---|
| 1 | ~~`import qa_generation` が Celery を連れてくる~~ | `pipeline.py` がモジュール先頭で `from celery_tasks import …` していたため、`qa_generation` 配下のどのモジュールを import しても `celery_tasks` と `celery` 一式が読み込まれ、**+117 モジュール**になっていた（詳細は [`__init__.md`](__init__.md) §3） | ✅ 修正済み（2026-09-24・残タスク 2） |
| 2 | ~~`QAPair` が 3 箇所に別定義で存在する~~ | 直下 `models.py`／`qa_generation/models.py`／`helper/helper_rag_qa.py`。`qa_generation/models.py` の `QAPair` は `__init__.py` の再エクスポート以外に import 元が無かった（grep 実測）。取り違えると `difficulty="hard"` などが**エラーも出ずに消える** | ✅ **一本化**（2026-09-25・残タスク 3）。`qa_generation/models.py` と `helper_rag_qa.py` の定義を削除し、直下 `models.py` の正本を import する形へ。**定義は 1 つだけ**（[`models.md`](models.md) §3） |
| 3 | ~~死んだ引数 `provider="anthropic"`~~ | `QAPipeline._generate_with_celery()` が `submit_unified_qa_generation(..., provider="anthropic")` と渡すが、受け側（`celery_tasks.py`）は「互換性のために残すが使用しない」。プロバイダはワーカー側の `SmartQAGenerator` が解決する | ✅ 削除済み（2026-09-25・残タスク 4） |
| 4 | ~~`smart_qa_generator.md` の既定モデルが旧既定のまま~~ | 使用例・IPO・設定表の 3 箇所が旧既定だった。実装（`SmartQAGenerator.__init__`）は現行既定 | ✅ 本書作成時に是正（`smart_qa_generator.md` v1.2） |
| 5 | ~~`load_uploaded_file()` で、テキスト候補列の空セルが文字列 `"nan"` として残る~~ | `clean_text(str(x))` と先に `str()` をかけるため、`NaN` が `clean_text()` の欠損判定に届かない。空白行の除外もすり抜け、`"nan"` から Q/A が生成されうる。実測: `text` 列に空セル → `['hello', 'nan', 'world']`（[`data_io.md`](data_io.md) §8 の 7） | ✅ 修正済み（2026-09-24・残タスク 5） |

> 姉妹リポジトリ `grace_v2_local` では 1・3 を 2026-09-21 に解消済み（1 は `celery_tasks` の
> import を `_generate_with_celery()` 内へ移す遅延 import、3 は受け側の引数ごと削除）。
> 本リポジトリでも 1 を 2026-09-24、2・3 を 2026-09-25 に同じ方法・同じ判断で解消した。
> 2 は「統合しない」と決着し、差分をテストで固定している。移植するなら `diff -u` で差分だけを取ること。

---

## 5. 書き分けの約束

| 置き場所 | 書くもの | 書かないもの |
|---|---|---|
| `<module>.md` | IPO（入出力・副作用・使用例） | 運用手順（`qa_qdrant/docs/01_install.md` へリンク） |
| `qa_qdrant/docs/` | CLI の実行手順・環境構築 | `qa_generation/` 内部の実装 |
| `backend/docs/` | Web（データ管理タブ）からの呼び出し経路 | `qa_generation/` 内部の実装 |
| 直下 `docs/` | 2 領域以上にまたがる横断文書 | 1 モジュールの IPO |

> IPO 形式の仕様は `.claude/skills/grace-agent-docs/a_class_method_md_format.md`。
> **重複禁止ルールと正本の一覧は [`docs/README.md`](../../docs/README.md) が持つ。**

---

## 6. 残タスク

| # | 内容 | 優先 |
|---|---|:--:|
| 1 | ~~`data_io.md` / `models.md` / `__init__.md` を作成する（§3）~~ | ✅ **完了**（2026-09-24） |
| 2 | ~~`pipeline.py` の `celery_tasks` import を `_generate_with_celery()` 内へ移し、import 副作用を無くす（§4 の 1）~~ | ✅ **完了**（2026-09-24）。`import qa_generation.data_io` は 1,733 → 1,623 モジュール。`celery_tasks` の `sys.path` 挿入に頼っていた `helper/` 配下の裸 import 4 モジュールも同時に是正。回帰は `test_qa_generation_import_side_effects.py`（3 件・修正前は 3 件とも fail） |
| 3 | ~~`QAPair` の 3 重定義の扱いを決める（§4 の 2）~~ | ✅ **決着**（2026-09-25）。いったん「統合しない」としたが、同日に**直下 `models.py` へ一本化**した。`qa_generation/models.py` と `helper/helper_rag_qa.py` の別定義を削除し、どちらも正本を import する（`helper_rag_qa.py` の LLM プロンプトの項目名も正本へ揃えた）。関係を `test_qa_pair_definitions.py`（4 件）で固定した |
| 4 | ~~死んだ `provider` 引数を、呼び出し元と受け側の両方から外す（§4 の 3）~~ | ✅ **完了**（2026-09-25）。呼び出し元が `QAPipeline._generate_with_celery` の 1 箇所だけだったので、受け側（`celery_tasks.submit_unified_qa_generation`）の引数ごと削除した。**残タスク 0 件** |
| 5 | ~~`load_uploaded_file()` の `"nan"` 混入を直す（§4 の 5）~~ | ✅ **完了**（2026-09-24）。欠損判定ヘルパー `_is_missing()` を足し、候補列と全列連結の両方で欠損を空文字／除外として扱う。回帰は `test_data_io_missing_text.py`（3 件・修正前は 2 件 fail） |

---

## 7. テスト

`qa_generation/` を直接対象にしたテストは **4 件**（2026-09-25、`backend/tests` を grep して確認）。

| テストファイル | 関わり方 |
|---|---|
| `backend/tests/test_qa_pair_definitions.py` | **6 件**。`qa_generation.QAPair` / `QAPairsList` が直下 `models.py` の正本そのものであること・`qa_generation/models.py` と `helper_rag_qa.py` に別定義を書き戻していないこと（§4 の 2）。`helper_rag_qa.py` は `spacy` 依存を避けて `ast` で読む |
| `backend/tests/test_qa_generation_import_side_effects.py` | **3 件**。`import qa_generation.data_io` で Celery が載らないこと・Celery は必要時に読めること・`helper/` 配下に裸 import が無いこと（§4 の 1） |
| `backend/tests/test_qa_pipeline_text_column.py` | **6 件**。`QAPipeline(text_column=...)` が指定列を優先すること・指定列が無ければ `ValueError`・未指定なら従来の自動検出順のままであることと、`make_qa_register_qdrant.py` の `--text-column` が `QAPipeline` へ渡ること |
| `backend/tests/test_data_io_missing_text.py` | **3 件**。`load_uploaded_file()` が欠損セルを `"nan"` にしないこと（候補列・全列連結）と、数値など欠損でない値は従来どおり残ることを検証する（§4 の 5） |
| `backend/tests/test_data_jobs.py` | データ管理タブの Q/A 生成ジョブを検証する。`run_qa_generation_sync` を**スタブへ差し替える**ので、`QAPipeline` 自体は実行されない |
| `backend/tests/test_model_table_coverage.py` | 各所の既定モデル（`QAPipeline` / `SmartQAGenerator` の既定を含む）が `ModelConfig` の料金表・上限表に登録されていることを検査する。**既定値はテスト内の一覧に手で列挙したもの**で、`QAPipeline` のコードから読み取ってはいない |

> ⚠️ **`QAPipeline.run()` は Web / CLI 共通の実体なのに、直接のテストが無い。**
> カバレッジの空白として認識しておくこと。

---

## 8. 変更履歴

| Version | 日付 | 変更 |
|---|---|---|
| 1.13 | 2026-09-26 | Embedding を `gemini-embedding-001` に戻したのに追随（2026-09-26。同日に一度 `gemini-embedding-2` へ変えたが、既存の Qdrant コレクションと grace_v2_local（同じ Qdrant を共用）をそのまま使うため戻した。定義は `config.py::ModelConfig.EMBEDDING_MODEL`）。同じ改訂の 2 文書の行数・Ver を再実測 |
| 1.12 | 2026-09-26 | 現在の Embedding の記述を `gemini-embedding-001` から `gemini-embedding-2` へ是正（2026-09-26 に変更。定義は `config.py::ModelConfig.EMBEDDING_MODEL` の 1 箇所）。あわせて `semantic.md` v1.2 / `evaluation.md` v1.2 の行数・Ver と、PR #216 で変わった `semantic.py` の実装行数（543）を再実測 |
| 1.11 | 2026-09-26 | `pipeline.md` v1.5（`--dataset` の種別の補完）に追随して §2 の行数・Ver を更新 |
| 1.10 | 2026-09-25 | `QAPipeline` に `text_column` 引数を追加したのに追随。§2 の `pipeline.md` 行（実装 565 行・文書 811 行・v1.4）と §7 のテスト一覧（`test_qa_pipeline_text_column.py`）を更新 |
| 1.9 | 2026-09-25 | `chunking/docs/` / `qa_qdrant/docs/` / `services/docs/` に棚卸し索引を新設したのにあわせ、姉妹版リンクと冒頭の ①・③ からリンクを張った |
| 1.8 | 2026-09-25 | `QAPairsList` も直下 `models.py` の定義（`QAPairsResponse` の別名）へ一本化。`qa_generation/models.py` と `helper/helper_rag_qa.py` の同名クラスを削除し、`test_qa_pair_definitions.py` に 2 件を追加（計 6 件）。§2 の行数・版を更新 |
| 1.7 | 2026-09-25 | §2 の `__init__.md` 行を更新（`qa_qdrant/__init__.py` の整理を §4 に記録） |
| 1.6 | 2026-09-25 | `helper/helper_rag_qa.py` の旧 `QAPair` も削除し、`QAPair` の定義は直下 `models.py` の 1 つだけになった。§4 の 2・§6 の 3・§7 を更新 |
| 1.5 | 2026-09-25 | 残タスク 3 の決着を「統合しない」から**「直下 `models.py` へ一本化」**へ変更（`qa_generation/models.py` の `QAPair` 別定義を削除）。§2・§4 の 2・§6 の 3・§7 を更新 |
| 1.4 | 2026-09-25 | 残タスク 3・4 を完了し、**残タスク 0 件**。3 は「統合しない」で決着（docstring の相互参照＋`test_qa_pair_definitions.py` 4 件）、4 は死んだ `provider` 引数を受け側ごと削除。§4 の 2・3、§6、§7 を更新 |
| 1.3 | 2026-09-24 | 残タスク 2 を完了（`qa_generation` の import で Celery が読み込まれる副作用を、`pipeline.py` の遅延 import 化で解消）。§4 の 1、§6、§7 のテスト一覧を更新 |
| 1.2 | 2026-09-24 | 残タスク 5 を完了（`load_uploaded_file()` の `"nan"` 混入を修正）。§2 の `data_io` 行（実装 168 行・文書 v1.1）、§3 の「両リポジトリで同一」の注記、§7 のテスト一覧を更新 |
| 1.1 | 2026-09-24 | 残タスク 1 を完了（`data_io.md` / `models.md` / `__init__.md` を新規作成し、実装 7 件との 1:1 対応が揃った）。§4 の 1 のモジュール数を「+1,505」（`import qa_generation` の総数）から Celery 由来の差分「+117」へ訂正。文書化の過程で見つけた `load_uploaded_file()` の `"nan"` 混入を §4 の 5・残タスク 5 に登録 |
| 1.0 | 2026-09-24 | 新規作成。`qa_generation/docs/` には棚卸し索引が無かった。文書一覧（行数・Ver は実測）・実装カバレッジ（**文書の欠落 3 件**）・棚卸しで分かったこと 4 件・残タスク 4 件・テストの有無を記載。あわせて `smart_qa_generator.md` の既定モデルの記述を実装へ合わせた（v1.2） |
