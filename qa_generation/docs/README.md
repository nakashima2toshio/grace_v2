# qa_generation/docs/ 棚卸し

**Version 1.1** | 最終更新: 2026-09-24

> 📎 **姉妹版**: [`docs/README.md`](../../docs/README.md)（直下・配置の境界） /
> [`grace/docs/README.md`](../../grace/docs/README.md) /
> [`backend/docs/README.md`](../../backend/docs/README.md)

`qa_generation/docs/` 配下のドキュメントを一覧化する。**目的から入口を引ける**ようにするのが狙い。
新しく文書を書く／直す前に、まずここを見る。

> 📌 **データ準備 3 工程のうち ② にあたるパッケージ。**
> ① チャンク化は `chunking/`、③ Qdrant 登録は `qa_qdrant/`。
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
>
> 7 文書はすべて**種別 E**（IPO 形式・`a_class_method_md_format.md` 準拠。使用例は IPO 詳細の冒頭）。
> 本索引自体は種別 C（`a_cross_doc_md_format.md` §7.1）。

| 文書 | 対象実装 | 実装行数 | 文書行数 | Ver | 重要度 |
|---|---|---:|---:|---|:--:|
| [`pipeline.md`](pipeline.md) | `pipeline.py` — `QAPipeline`（Web / CLI 共通の実体） | 549 | 802 | 1.2 | ★★★ |
| [`smart_qa_generator.md`](smart_qa_generator.md) | `smart_qa_generator.py` — `SmartQAGenerator`（構造化出力 1 回） | 300 | 572 | 1.2 | ★★★ |
| [`semantic.md`](semantic.md) | `semantic.py` — `SemanticCoverage`（Embedding によるカバレージ） | 542 | 778 | 1.1 | ★★☆ |
| [`evaluation.md`](evaluation.md) | `evaluation.py` — `analyze_coverage()` ほか | 316 | 820 | 1.1 | ★★☆ |
| [`data_io.md`](data_io.md) | `data_io.py` — 入力 CSV の読み込みと結果 4 ファイルの保存 | 162 | 478 | 1.0 | ★★☆ |
| [`models.md`](models.md) | `models.py` — Pydantic モデル 8 クラス | 155 | 368 | 1.0 | ★☆☆ |
| [`__init__.md`](__init__.md) | `__init__.py` — 公開 API（再エクスポート 11 件） | 65 | 290 | 1.0 | ★☆☆ |

---

## 3. 実装カバレッジ

`qa_generation/*.py` は **7 件**（`__init__.py` を含む）、対応する `<module>.md` も **7 件**。
**2026-09-24 に欠落 3 件（`data_io` / `models` / `__init__`）を作成し、1:1 対応が揃った**（§6 の残タスク 1）。

> 3 件は姉妹リポジトリ `grace_v2_local` の同名文書を構成の参考にしたが、実装（`data_io.py` / `__init__.py` は
> 同一、`models.py` は docstring のみ差あり）を読み直し、**本リポジトリの実測値で書き起こした**。
> とくに `__init__.md` の import 副作用は、あちらは解消済み・こちらは未解消なので内容が逆になっている。

---

## 4. 棚卸しで分かったこと

2026-09-24 に実装を読んで確認した。いずれも**機能上の不具合ではない**が、誤解や無駄を生む。

| # | 内容 | 根拠（実測） | 扱い |
|---|---|---|---|
| 1 | **`import qa_generation` が Celery を連れてくる** | `pipeline.py` がモジュール先頭で `from celery_tasks import …` しているため、`qa_generation` 配下のどのモジュールを import しても `celery_tasks` と `celery` 一式が読み込まれ、**+117 モジュール**になる（`data_io` の依存だけとの比較。`celery_config` のログも出る。詳細は [`__init__.md`](__init__.md) §3）。Celery を使うのは `QAPipeline._generate_with_celery()` だけ | 残タスク 2 |
| 2 | **`QAPair` が 3 箇所に別定義で存在する** | 直下 `models.py`／`qa_generation/models.py`／`helper/helper_rag_qa.py`。`qa_generation/models.py` の `QAPair` は `__init__.py` の再エクスポート以外に import 元が無い（grep 実測） | 残タスク 3 |
| 3 | **死んだ引数 `provider="anthropic"`** | `QAPipeline._generate_with_celery()` が `submit_unified_qa_generation(..., provider="anthropic")` と渡すが、受け側（`celery_tasks.py`）は「互換性のために残すが使用しない」。プロバイダはワーカー側の `SmartQAGenerator` が解決する | 残タスク 4 |
| 4 | ~~`smart_qa_generator.md` の既定モデルが旧既定のまま~~ | 使用例・IPO・設定表の 3 箇所が旧既定だった。実装（`SmartQAGenerator.__init__`）は現行既定 | ✅ 本書作成時に是正（`smart_qa_generator.md` v1.2） |
| 5 | **`load_uploaded_file()` で、テキスト候補列の空セルが文字列 `"nan"` として残る** | `clean_text(str(x))` と先に `str()` をかけるため、`NaN` が `clean_text()` の欠損判定に届かない。空白行の除外もすり抜け、`"nan"` から Q/A が生成されうる。実測: `text` 列に空セル → `['hello', 'nan', 'world']`（[`data_io.md`](data_io.md) §8 の 7） | 残タスク 5 |

> 姉妹リポジトリ `grace_v2_local` では 1・3 を 2026-09-21 に解消済み（1 は `celery_tasks` の
> import を `_generate_with_celery()` 内へ移す遅延 import、3 は受け側の引数ごと削除）。
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
| 2 | `pipeline.py` の `celery_tasks` import を `_generate_with_celery()` 内へ移し、import 副作用を無くす（§4 の 1）。回帰テストも足す | 中 |
| 3 | `QAPair` の 3 重定義の扱いを決める（§4 の 2）。公開 API なので削除・寄せ替えは破壊的変更になる | 低 |
| 4 | 死んだ `provider` 引数を、呼び出し元と受け側の両方から外す（§4 の 3） | 低 |
| 5 | `load_uploaded_file()` の `"nan"` 混入を直す（§4 の 5）。`str()` を先にかけず `clean_text(x)` に渡せば欠損判定が効く。回帰テストも足す | 中 |

---

## 7. テスト

**`qa_generation/` のモジュールを直接対象にしたテストは無い**（2026-09-24、`backend/tests` を grep して確認）。

| テストファイル | 関わり方 |
|---|---|
| `backend/tests/test_data_jobs.py` | データ管理タブの Q/A 生成ジョブを検証する。`run_qa_generation_sync` を**スタブへ差し替える**ので、`QAPipeline` 自体は実行されない |
| `backend/tests/test_model_table_coverage.py` | 各所の既定モデル（`QAPipeline` / `SmartQAGenerator` の既定を含む）が `ModelConfig` の料金表・上限表に登録されていることを検査する。**既定値はテスト内の一覧に手で列挙したもの**で、`QAPipeline` のコードから読み取ってはいない |

> ⚠️ **`QAPipeline.run()` は Web / CLI 共通の実体なのに、直接のテストが無い。**
> カバレッジの空白として認識しておくこと。

---

## 8. 変更履歴

| Version | 日付 | 変更 |
|---|---|---|
| 1.1 | 2026-09-24 | 残タスク 1 を完了（`data_io.md` / `models.md` / `__init__.md` を新規作成し、実装 7 件との 1:1 対応が揃った）。§4 の 1 のモジュール数を「+1,505」（`import qa_generation` の総数）から Celery 由来の差分「+117」へ訂正。文書化の過程で見つけた `load_uploaded_file()` の `"nan"` 混入を §4 の 5・残タスク 5 に登録 |
| 1.0 | 2026-09-24 | 新規作成。`qa_generation/docs/` には棚卸し索引が無かった。文書一覧（行数・Ver は実測）・実装カバレッジ（**文書の欠落 3 件**）・棚卸しで分かったこと 4 件・残タスク 4 件・テストの有無を記載。あわせて `smart_qa_generator.md` の既定モデルの記述を実装へ合わせた（v1.2） |
