# make_qa_register_qdrant.py - Q/A 生成 → Qdrant 登録 統合 CLI ドキュメント

**Version 1.5** | 最終更新: 2026-09-26

---

## 目次

1. [概要](#概要)
2. [アーキテクチャ構成図](#1-アーキテクチャ構成図)
3. [モジュール構成図](#2-モジュール構成図)
4. [入力の振り分けと既知の問題（重点解説）](#3-入力の振り分けと既知の問題重点解説)
5. [クラス・関数一覧表](#4-クラス関数一覧表)
6. [クラス・関数 IPO詳細](#5-クラス関数-ipo詳細)
7. [設定・定数](#6-設定定数)
8. [エクスポート](#7-エクスポート)
9. [変更履歴](#8-変更履歴)
10. [付録: 依存関係図](#付録-依存関係図)

---

## 概要

`qa_qdrant/make_qa_register_qdrant.py` は、チャンク済み CSV・テキストファイル（`.txt`・先にチャンク化する）・
事前定義データセットのいずれかから Q/A ペアを生成し（Phase 1）、その Q/A を Embedding して Qdrant コレクションへ登録する（Phase 2）
**統合 CLI** です。Q/A 生成は `qa_generation.pipeline.QAPipeline`（Anthropic Claude・既定 `claude-sonnet-5`）に、
Embedding と Qdrant 操作は `services/qdrant_service.py`（Gemini `gemini-embedding-001`・3072 次元）に委譲し、
本モジュールは**入力の振り分け・`.txt` のチャンク化の呼び出し・2 フェーズの順序制御・登録ループ・UI 用 CSV の出力**を受け持ちます。

> 📎 **使い方（運用手順）は [`make_qa_register_qdrant.md`](make_qa_register_qdrant.md)（種別 B・手順書）**、
> 本書はモジュール仕様（IPO）です。同名の手順書が先にあったため、本書はファイル名に `_ipo` を付けています。
>
> 📌 **データ管理タブ（Web）はこの CLI を呼ばない。** Q/A 生成は `services/data_pipeline_service.py::run_qa_generation_sync()`、
> 登録は `qa_qdrant/register_to_qdrant.py` を通る。Phase 1 は同じ `QAPipeline` なので生成結果は変わらない。
>
> 📌 [§3.3 既知の問題](#33-既知の問題2026-09-25-実測) の 5 件は **2026-09-25 にすべて修正済み**（修正前の挙動の記録として残している）。

### 主な責務

- 入力ソース（`--dataset` / `--input-file`）の排他検証と、ファイル種別・カラムによる処理の振り分け
- `.txt` 入力の事前チャンク化（チャンク化 CLI・データ管理タブと同じ経路）
- Q/A 生成（Phase 1）の `QAPipeline` への委譲と、生成された Q/A CSV の特定
- Q/A の `question` 列のバッチ Embedding と Qdrant へのアップサート（Phase 2）
- UI 用に `question` / `answer` だけを持つ CSV を、日時サフィックスを外した固定名で出力する
- ファイル名から日時サフィックスを除いた正規化名の生成（Qdrant の `source` と UI 用 CSV 名に使う）

### 各責務対応のモジュール

| # | 責務 | 対応モジュール | 説明 |
|---|------|--------------|------|
| 1 | 入力の排他検証と振り分け | `make_qa_register_qdrant.py` | `main()` が引数を解析し、`.txt` / `.csv`（Q/A 列あり・本文列あり）/ データセットで分岐（§3） |
| 2 | `.txt` の事前チャンク化 | `services/data_pipeline_service.py` | `chunk_text_file()` が `run_chunking_sync()`（`chunking.csv_text_to_chunks_text_csv.chunks_all_async` の同期版）で `<入力名>_chunks.csv` を作る |
| 3 | Q/A 生成の委譲 | `qa_generation/pipeline.py` | `QAPipeline.run()` が `SmartQAGenerator` で生成し、`saved_files["qa_csv"]` を返す |
| 4 | Embedding と Qdrant 登録 | `services/qdrant_service.py` | `run_registration()` が `embed_texts_for_qdrant()` / `build_points_for_qdrant()` / `upsert_points_to_qdrant()` を呼ぶ |
| 5 | UI 用 CSV の出力 | `make_qa_register_qdrant.py` | `run_registration()` の末尾で `question` / `answer` 列だけを `--ui-output` へ書く |
| 6 | ファイル名の正規化 | `make_qa_register_qdrant.py` | `normalize_source_filename()` が `_YYYYMMDD_HHMMSS` を除去 |

### 主要機能一覧

| 機能 | 説明 |
|------|------|
| `main()` | CLI エントリーポイント。引数解析 → 入力検証 → Phase 1 → Phase 2 |
| `chunk_text_file()` | `.txt` をセマンティックチャンク化し、チャンク CSV のパスを返す |
| `run_registration()` | Q/A CSV を Embedding して Qdrant へ登録し、UI 用 CSV を書く（Phase 2） |
| `normalize_source_filename()` | ファイル名から日時サフィックス（`_YYYYMMDD_HHMMSS`）を除去 |

---

## 1. アーキテクチャ構成図

### 1.1 システム全体構成

```mermaid
flowchart TB
    subgraph CLIENT["呼び出し側"]
        USER["利用者の端末（python qa_qdrant/make_qa_register_qdrant.py）"]
        WORKER["Celery ワーカー（start_celery.sh・--use-celery 時）"]
    end

    subgraph MODULE["make_qa_register_qdrant.py"]
        MAIN["main()"]
        CHUNK["chunk_text_file()（.txt のみ）"]
        REG["run_registration()"]
        NORM["normalize_source_filename()"]
    end

    subgraph EXTERNAL["外部サービス層"]
        CHK["run_chunking_sync（services.data_pipeline_service → chunking）"]
        PIPE["QAPipeline（qa_generation）"]
        CLAUDE["Anthropic Claude（Q/A 生成）"]
        QSVC["services.qdrant_service"]
        GEMINI["Gemini gemini-embedding-001（3072 次元）"]
        QDRANT["Qdrant"]
        FS["ファイルシステム（output_chunked/・qa_output/）"]
    end

    USER --> MAIN
    MAIN --> CHUNK
    CHUNK --> CHK
    CHK --> CLAUDE
    CHK --> FS
    MAIN --> PIPE
    PIPE --> CLAUDE
    PIPE --> WORKER
    MAIN --> REG
    REG --> NORM
    REG --> QSVC
    QSVC --> GEMINI
    QSVC --> QDRANT
    PIPE --> FS
    REG --> FS
classDef default fill:#000,stroke:#fff,color:#fff
classDef subgraphStyle fill:#1a1a1a,stroke:#fff,color:#fff
class USER,WORKER,MAIN,CHUNK,REG,NORM,CHK,PIPE,CLAUDE,QSVC,GEMINI,QDRANT,FS default
style CLIENT fill:#1a1a1a,stroke:#fff,color:#fff
style MODULE fill:#1a1a1a,stroke:#fff,color:#fff
style EXTERNAL fill:#1a1a1a,stroke:#fff,color:#fff
```

### 1.2 データフロー

1. `main()` が引数を解析し、`--dataset` / `--input-file` のどちらか 1 つだけが指定されていること、`GOOGLE_API_KEY` があることを確かめる（Q/A を生成する経路では、生成・チャンク化の前に `ANTHROPIC_API_KEY` も確かめる）
2. `.txt` 入力なら、まず `chunk_text_file()` が `<--chunk-output>/<入力名>_chunks.csv` を作る（チャンク化にも Anthropic Claude を使う）
3. **Phase 1**: 入力に応じて `QAPipeline.run()` で Q/A を生成し、`<--output>/qa_pairs_<種別>_<日時>.csv` を得る
   （入力 CSV が既に `question` / `answer` 列を持つ場合は生成を飛ばし、その CSV をそのまま使う）
4. **Phase 2**: `run_registration()` が Q/A CSV を読み、`question` 列だけを `--batch-size` 件ずつ Embedding する
5. 各バッチを Qdrant のポイントに組み立て、`source` をファイル名の正規化名に揃えてアップサートする
6. 最後に `question` / `answer` 列だけの CSV を `<--ui-output>/<正規化名>` へ書き出す

---

## 2. モジュール構成図

### 2.1 内部モジュール構成

```mermaid
flowchart TB
    subgraph ENTRY["エントリーポイント"]
        MAIN["main()"]
        ARGS["argparse（入力 / CSV / チャンク化 / Q/A 生成 / Qdrant 登録 / 出力）"]
    end

    subgraph PHASE1["Phase 1: Q/A 生成"]
        ROUTE["入力の振り分け（§3）"]
        CHUNK["chunk_text_file()（.txt のみ）"]
        PIPE["QAPipeline(...).run(...)"]
    end

    subgraph PHASE2["Phase 2: Qdrant 登録"]
        REG["run_registration()"]
        NORM["normalize_source_filename()"]
        UICSV["UI 用 CSV の書き出し"]
    end

    MAIN --> ARGS
    ARGS --> ROUTE
    ROUTE --> CHUNK
    CHUNK --> PIPE
    ROUTE --> PIPE
    ROUTE --> REG
    PIPE --> REG
    REG --> NORM
    REG --> UICSV
classDef default fill:#000,stroke:#fff,color:#fff
classDef subgraphStyle fill:#1a1a1a,stroke:#fff,color:#fff
class MAIN,ARGS,ROUTE,CHUNK,PIPE,REG,NORM,UICSV default
style ENTRY fill:#1a1a1a,stroke:#fff,color:#fff
style PHASE1 fill:#1a1a1a,stroke:#fff,color:#fff
style PHASE2 fill:#1a1a1a,stroke:#fff,color:#fff
```

### 2.2 外部依存関係

| ライブラリ | 用途 |
|-----------|------|
| `pandas` | 入力 CSV の判定・Q/A CSV の読み込み・UI 用 CSV の書き出し |
| `argparse` / `logging` / `re` / `pathlib`（標準） | 引数解析・ログ・日時サフィックスの除去・拡張子判定 |

### 2.3 内部依存モジュール

| モジュール | 用途 |
|-----------|------|
| `config.DATASET_CONFIGS` | `--dataset` の選択肢（`wikipedia_ja` / `wikipedia_ja_5per` / `japanese_text` / `fineweb_edu_ja` / `cc_news` / `livedoor`） |
| `services.data_pipeline_service.run_chunking_sync` | `.txt` のチャンク化（`chunks_all_async()` を `asyncio.run()` で同期実行。データ管理タブのチャンク化ジョブと同じ関数） |
| `chunking.csv_text_to_chunks_text_csv.generate_output_filename` | チャンク CSV のパス（`<出力先>/<入力名>_chunks.csv`）を決める |
| `qa_generation.pipeline.QAPipeline` | Phase 1 の Q/A 生成（`SmartQAGenerator`・Celery 並列対応） |
| `qdrant_client_wrapper.create_qdrant_client` | Qdrant クライアントの生成 |
| `services.qdrant_service.create_or_recreate_collection_for_qdrant` | コレクションの作成・再作成（既定 3072 次元） |
| `services.qdrant_service.embed_texts_for_qdrant` | Gemini Embedding（`gemini-embedding-001`） |
| `services.qdrant_service.build_points_for_qdrant` | DataFrame → `PointStruct`（payload: `domain` / `question` / `answer` / `source` / `created_at` / `schema` ほか） |
| `services.qdrant_service.upsert_points_to_qdrant` | ポイントのアップサート |

---

## 3. 入力の振り分けと既知の問題（重点解説）

### 3.1 入力ごとの処理

`main()` は入力の種類で Phase 1 を切り替えます。**判定はこの順に行われる**（上から最初に当てはまった行）。

| # | 入力 | 判定条件 | Phase 1 | Phase 2 に渡す CSV |
|---|------|---------|---------|-------------------|
| 1 | `--dataset <名前>` | — | `QAPipeline(dataset_name=...)` で生成 | 生成した Q/A CSV |
| 2 | `--input-file *.txt` | 拡張子 `.txt` | `chunk_text_file()` で `<--chunk-output>/<入力名>_chunks.csv` を作ってから `QAPipeline(input_file=<チャンク CSV>)` で生成。本文が空・`ANTHROPIC_API_KEY` が無ければ終了コード 1 | 生成した Q/A CSV |
| 3 | `--input-file *.csv` | `question` 列と `answer` 列が両方ある | **生成しない**（Q/A 済みとみなす） | 入力 CSV そのもの |
| 4 | `--input-file *.csv` | `--text-column`（既定 `text`）列、または `Combined_Text` 列がある | `QAPipeline(input_file=..., text_column=<判定に使った列>)` で生成（`--text-column` の列があればそれ、無ければ `Combined_Text`） | 生成した Q/A CSV |
| 5 | `--input-file *.csv` | 上のどれにも当てはまらない | エラー（必要なカラムを表示）・終了コード 1 | — |
| 6 | `--input-file` のその他の拡張子 | — | エラー（「未対応のファイル形式」）・終了コード 1 | — |

```mermaid
flowchart TB
    START["main()"]
    DS{"--dataset ?"}
    EXT{"拡張子"}
    COLS{"カラム"}
    CHUNK["chunk_text_file() でチャンク化"]
    GEN["QAPipeline で生成（Phase 1）"]
    SKIP["生成しない（入力をそのまま使う）"]
    FAIL["エラー終了（終了コード 1）"]
    REG["run_registration()（Phase 2）"]

    START --> DS
    DS -->|"はい"| GEN
    DS -->|"いいえ（--input-file）"| EXT
    EXT -->|".txt"| CHUNK
    CHUNK --> GEN
    EXT -->|".csv"| COLS
    EXT -->|"その他"| FAIL
    COLS -->|"question + answer"| SKIP
    COLS -->|"text / Combined_Text"| GEN
    COLS -->|"どれも無い"| FAIL
    GEN --> REG
    SKIP --> REG
classDef default fill:#000,stroke:#fff,color:#fff
classDef subgraphStyle fill:#1a1a1a,stroke:#fff,color:#fff
class START,DS,EXT,COLS,CHUNK,GEN,SKIP,FAIL,REG default
```

> 📌 `.txt` のチャンク化はチャンク化 CLI（`python -m chunking.csv_text_to_chunks_text_csv`）と同じ処理で、
> 出力も同じ `<入力名>_chunks.csv`（CLAUDE.md §8.2・同名があれば上書き）。ワーカー数 8・ブロックサイズ 1000 字は
> 固定なので、変えたいときや `--resume` で再開したいときは、チャンク化 CLI で先に作ってから CSV を渡す。

### 3.2 出力ファイル

| 出力 | 場所・名前 | 中身 |
|------|-----------|------|
| チャンク CSV（`.txt` 入力のみ） | `<--chunk-output>/<入力名>_chunks.csv` と `<入力名>_chunks_simple.csv`（既定 `output_chunked/`） | セマンティックチャンク。**同じ入力なら上書き** |
| Q/A CSV（Phase 1） | `<--output>/qa_pairs_<種別>_<YYYYMMDD_HHMMSS>.csv`（`qa_generation/data_io.py::save_results`） | 生成した Q/A と付随列。**実行ごとに新しいファイル** |
| Q/A JSON（Phase 1） | `<--output>/qa_pairs_<種別>_<YYYYMMDD_HHMMSS>.json` | 同上の JSON 版 |
| UI 用 CSV（Phase 2） | `<--ui-output>/<Q/A CSV 名から日時を除いた名前>`（例 `qa_output/qa_pairs_cc_news_1per_chunks.csv`） | `question` / `answer` の 2 列だけ。**同じ入力なら上書き** |
| Qdrant | コレクション `--collection` | Q/A 1 件 = 1 ポイント。`source` payload は UI 用 CSV と同じ正規化名 |

`<種別>` は `--input-file` のときは入力ファイル名の拡張子を除いた部分（`.txt` 入力ではチャンク CSV の名前なので `<入力名>_chunks`）、`--dataset` のときは**データセット名**（例 `cc_news`）です。
`config.DATASET_CONFIGS` の各エントリには `type` キーが無いため、`QAPipeline._load_config()` がデータセット名で補います。
2026-09-26 までは補っておらず（v1.4 までの本書の「データセット設定の `type`」という記述も誤り）、`self.config.get("type", "unknown")` の既定値へ倒れて
**どのデータセットでも `unknown`** になっていました。UI 用 CSV（`qa_pairs_unknown.csv`）が上書きされるだけでなく、チャンク ID（`unknown_chunk_<n>`）と
途中経過ファイル（`qa_progress_unknown.jsonl`）もデータセット間で共有され、途中で落ちたデータセットの途中経過を別のデータセットの再開が読んでいました
（`backend/tests/test_qa_pipeline_dataset_type.py`。修正前の実装で fail することを確認）。

### 3.3 既知の問題（2026-09-25 実測）

本書を書く際に実装を読み、ダミーの API キー（外部 API へは届かない）で CLI を実行して確かめたものです。
v1.0 では挙動を記録するだけでコードは変えなかった。**5 件とも 2026-09-25 に修正済み**。

| # | 問題 | 実測・根拠 | 影響 |
|---|------|-----------|------|
| 1 | ~~**`.txt` 入力は必ず失敗する。**~~ ✅ **修正済み（2026-09-25）** | 修正前は `.txt` をそのまま `QAPipeline` へ渡し、`QAPipeline.load_data()` が `.csv` しか受け付けないため `ValueError: 未対応のファイル形式: .txt` → **終了コード 1** だった。現在は `chunk_text_file()` で先にチャンク化する（§3.1 の 2。`backend/tests/test_make_qa_register_qdrant_txt_input.py` で固定。修正前の実装で fail することを確認） | —（解消） |
| 2 | ~~**Qdrant 登録が失敗しても終了コードは 0。**~~ ✅ **修正済み（2026-09-25）** | 修正前は `run_registration()` が `False` を返しても `main()` はエラーログを出すだけで、Q/A 列ありの CSV を Qdrant 未起動の環境で渡すと**終了コード 0** だった。現在は `sys.exit(1)` で止まる（`backend/tests/test_make_qa_register_qdrant_exit_code.py` で固定。修正前の実装で fail することを確認） | —（解消） |
| 3 | ~~**`--provider` は効かない。**~~ ✅ **修正済み（2026-09-25）** | 修正前は `run_registration(provider=...)` が受け取るだけで使わず、`embed_texts_for_qdrant()` は常に Gemini で Embedding していた（`--provider openai` でも黙って Gemini・3072 次元）。Embedding は Gemini だけという方針（CLAUDE.md §3）に合わせ、`choices=["gemini"]` にして他の値は argparse が**終了コード 2** で拒否する。`provider` は登録開始ログに出すだけ（`backend/tests/test_make_qa_register_qdrant_startup_checks.py` で固定。修正前の実装で fail することを確認） | —（解消） |
| 4 | ~~**`--text-column` は Q/A 生成に渡らない。**~~ ✅ **修正済み（2026-09-25）** | 修正前は `main()` が判定にだけ使い、`QAPipeline` は `text` → `Combined_Text` → `content` → `chunk_text` の順で**自分で**列を探していた（独自の列名だけの CSV は生成で ValueError、`text` もある CSV は指定を無視）。`QAPipeline` に `text_column` 引数を足し、判定に使った列を渡す。`QAPipeline` の既定 `None` は従来の自動検出なので、データ管理タブ・`make_qa.py` は変わらない（`backend/tests/test_qa_pipeline_text_column.py` で固定。修正前の実装で fail することを確認） | —（解消） |
| 5 | ~~起動時に `ANTHROPIC_API_KEY` を確かめない。~~ ✅ **修正済み（2026-09-25）** | 修正前は `.txt` 入力のチャンク化の前だけ確かめ、チャンク済み CSV・`--dataset` からの Q/A 生成は LLM を最初に呼ぶまで失敗しなかった。現在は Q/A を生成する経路（§3.1 の 1・2・4）で `require_anthropic_key()` が生成の前に確かめ、無ければ**終了コード 1**。Q/A 済み CSV の登録（§3.1 の 3）では確かめない（`backend/tests/test_make_qa_register_qdrant_startup_checks.py` で固定。修正前の実装で fail することを確認） | —（解消） |

> 📝 `normalize_source_filename()` の docstring は「UI（agent_rag.py）での参照を安定させるため」と書くが、
> `agent_rag.py` は本リポジトリに存在しない（CLAUDE.md §9.4）。現在は、データ管理タブの「③ Qdrant 登録」の
> 選択肢（`backend/app/core/data_jobs.py::list_input_files()`）が `qa_output/` **直下**のファイルを列挙するので、
> UI 用 CSV（既定 `qa_output/`）はそこに現れる。一方、本 CLI の Q/A CSV の既定出力先 `qa_output/pipeline/` は
> サブディレクトリなので列挙されない（同関数は `iterdir()` で入れ子を見ない）。

---

## 4. クラス・関数一覧表

### 4.1 クラス一覧

本モジュールはクラスを定義しません。

### 4.2 関数一覧（カテゴリ別）

#### エントリーポイント

| 関数名 | 概要 |
|-------|------|
| `main()` | CLI エントリーポイント（引数解析 → 入力検証 → Phase 1 → Phase 2） |

#### Qdrant 登録

| 関数名 | 概要 |
|-------|------|
| `run_registration(csv_path, collection_name, recreate, batch_size, provider, ui_output_dir="qa_output")` | Q/A CSV を Embedding して Qdrant へ登録し、UI 用 CSV を書く |

#### チャンク化

| 関数名 | 概要 |
|-------|------|
| `chunk_text_file(txt_path, output_dir, model)` | `.txt` をチャンク化し、チャンク CSV のパスを返す |
| `require_anthropic_key(purpose)` | LLM を呼ぶ工程（チャンク化・Q/A 生成）の前に `ANTHROPIC_API_KEY` を確かめ、無ければ終了コード 1 |

#### ユーティリティ

| 関数名 | 概要 |
|-------|------|
| `normalize_source_filename(filename)` | ファイル名から `_YYYYMMDD_HHMMSS` を除去 |

---

## 5. クラス・関数 IPO詳細

### 5.1 使用例

#### 5.1.1 基本的なワークフロー（チャンク済み CSV → Q/A 生成 → 登録）

```bash
# 前提: .env に ANTHROPIC_API_KEY（Q/A 生成）と GOOGLE_API_KEY（Embedding）、Qdrant 起動済み

# 1. チャンク化（生 CSV から始める場合。.txt なら 5.1.2 のとおり本 CLI がチャンク化まで行う）
python -m chunking.csv_text_to_chunks_text_csv \
  --input-file OUTPUT/cc_news_1per.csv --output output_chunked

# 2. Q/A 生成 → Qdrant 登録（Celery 不使用・同期）
python qa_qdrant/make_qa_register_qdrant.py \
  --input-file output_chunked/cc_news_1per_chunks.csv \
  --collection cc_news_1per \
  --recreate

# 出力例（ログの末尾）:
# 🎉 統合処理が正常に完了しました！
#    コレクション: cc_news_1per
#    データ件数  : 1234 件
#    Q/A CSV     : qa_output/pipeline/qa_pairs_cc_news_1per_chunks_20260925_101500.csv
#    UI用CSV     : qa_output/qa_pairs_cc_news_1per_chunks.csv
```

#### 5.1.2 テキストファイル（.txt）からチャンク化も含めて一気に回す（Celery 並列）

```bash
# 1. ワーカーを起動（別ターミナル）。-A は celery_config、キュー名に qa_generation は無い（CLAUDE.md §9.4）
./start_celery.sh restart -c 8 --flower

# 2. .txt を渡すと、先に output_chunked/document_chunks.csv を作ってから Q/A 生成・登録する。
#    -c / --concurrency はワーカーの -c と同じ値にそろえる
python qa_qdrant/make_qa_register_qdrant.py \
  --input-file data/document.txt \
  --collection my_collection \
  --use-celery -c 8 \
  --recreate

# 出力例（抜粋）:
# 📝 テキストファイル検出 - チャンク作成 + Q/A生成を実行します
# ✂️ チャンク化: data/document.txt → output_chunked/document_chunks.csv（model=claude-haiku-4-5）
# ✅ チャンク作成完了: 42 チャンク
```

#### 5.1.3 生成済みの Q/A CSV を登録だけする

```bash
# question / answer 列を持つ CSV を渡すと Phase 1 を飛ばす（§3.1 の 3）
python qa_qdrant/make_qa_register_qdrant.py \
  --input-file qa_output/pipeline/qa_pairs_cc_news_1per_chunks_20260925_101500.csv \
  --collection cc_news_1per

# 出力例:
# ✅ Q/Aカラムが存在します - Q/A生成をスキップして登録へ
```

> 📌 登録だけなら `qa_qdrant/register_to_qdrant.py`（[`register_to_qdrant.md`](register_to_qdrant.md)）が本来の口。

### 5.2 エントリーポイント

#### `main`

**概要**: CLI エントリーポイント。引数を解析・検証し、Phase 1（Q/A 生成）と Phase 2（Qdrant 登録）を順に実行する。

```python
def main() -> None
```

| パラメータ | 型 | デフォルト | 説明 |
|------------|------|-----------|------|
| （なし） | — | — | `sys.argv` から CLI 引数を読む（§6.1） |

| 項目 | 内容 |
|------|------|
| **Input** | CLI 引数（§6.1）、環境変数 `GOOGLE_API_KEY` |
| **Process** | 1. `argparse` で引数を解析（`--collection` は必須）<br>2. `--dataset` と `--input-file` がちょうど 1 つであることを確かめる（0 個・2 個ならエラー終了）<br>3. `GOOGLE_API_KEY` が無ければエラー終了（`--provider` に `gemini` 以外を渡すと手順 1 で argparse が終了コード 2）<br>4. 入力の種類で Phase 1 を振り分け（§3.1）。Q/A を生成する経路では生成（`.txt` はチャンク化）の前に `require_anthropic_key()` で `ANTHROPIC_API_KEY` を確かめ、無ければ終了コード 1。`.txt` なら先に `chunk_text_file()` でチャンク CSV を作る。生成する場合は `QAPipeline(...).run(use_celery, celery_workers, concurrency, batch_chunks, analyze_coverage=True)` を呼び、`result["saved_files"]["qa_csv"]` を Q/A CSV とする<br>5. Q/A CSV が作られていなければエラー終了<br>6. `run_registration()` で Phase 2 を実行<br>7. 成功なら件数・Q/A CSV・UI 用 CSV のパスをログに出す。失敗ならエラーログを出して終了コード 1<br>8. 途中の例外は「致命的なエラー」としてトレースバックを出して終了コード 1 |
| **Output** | `None`。副作用として Q/A CSV / JSON・UI 用 CSV・Qdrant のポイントを作る。**終了コード**: 成功で `0`、入力・カラム・キー不備・Phase 1 の例外・**Phase 2（Qdrant 登録）の失敗で `1`** |

**戻り値例**:
```python
None  # 戻り値は使わない。結果はログ・ファイル・Qdrant・終了コードで確かめる
```

```python
# 使用例（Python から呼ぶ場合。通常は CLI として実行する）
import sys
from qa_qdrant.make_qa_register_qdrant import main

sys.argv = [
    "make_qa_register_qdrant.py",
    "--input-file", "output_chunked/cc_news_1per_chunks.csv",
    "--collection", "cc_news_1per",
]
main()
```

> ⚠️ **注意**: import した時点で `logging.basicConfig()`（`%(asctime)s - %(levelname)s - %(message)s`）と
> `sys.path.insert(0, <プロジェクトルート>)` が走る（§7）。

### 5.3 Qdrant 登録関数

#### `run_registration`

**概要**: Q/A CSV の `question` 列を Embedding して Qdrant コレクションへアップサートし、UI 用 CSV を書き出す（Phase 2）。

```python
def run_registration(
        csv_path: str,
        collection_name: str,
        recreate: bool,
        batch_size: int,
        provider: str,
        ui_output_dir: str = "qa_output"
) -> bool
```

| パラメータ | 型 | デフォルト | 説明 |
|------------|------|-----------|------|
| `csv_path` | str | - | Q/A CSV のパス（`question` / `answer` 列が必要） |
| `collection_name` | str | - | 登録先コレクション名。payload の `domain` にも入る |
| `recreate` | bool | - | `True` ならコレクションを作り直す（既存ポイントは消える） |
| `batch_size` | int | - | 1 回の Embedding・アップサートで扱う行数 |
| `provider` | str | - | Embedding プロバイダ名。**ログ表示にだけ使う**（Embedding は常に Gemini。CLI は `gemini` しか受け付けない・§3.3 の 3） |
| `ui_output_dir` | str | `"qa_output"` | UI 用 CSV の出力先ディレクトリ |

| 項目 | 内容 |
|------|------|
| **Input** | `csv_path`, `collection_name`, `recreate`, `batch_size`, `provider`, `ui_output_dir = "qa_output"` |
| **Process** | 1. `csv_path` が無ければ `False`<br>2. CSV を読む（失敗なら `False`）<br>3. `question` と `answer` の両列が無ければ `False`。ベクトル化の対象は **`question` 列だけ**（検索クエリとの対称性を保つため。`question + answer` を結合すると類似度が下がる）<br>4. `create_qdrant_client()` → `create_or_recreate_collection_for_qdrant(recreate=...)`（接続失敗なら `False`）<br>5. `batch_size` 行ずつ `embed_texts_for_qdrant()` → `build_points_for_qdrant(domain=collection_name, source_file=正規化名, start_index=i)` → payload の `source` を正規化名で上書き → `upsert_points_to_qdrant()`。ベクトルが空のバッチは警告を出して**飛ばす**<br>6. ループ中の例外は `False`<br>7. `question` / `answer` 列だけを `<ui_output_dir>/<正規化名>` へ書く（失敗しても警告のみで結果は変えない） |
| **Output** | `bool`: 登録まで終われば `True`。入力・接続・登録のいずれかで失敗すれば `False`（例外は投げない） |

**戻り値例**:
```python
True
```

```python
# 使用例
from qa_qdrant.make_qa_register_qdrant import run_registration

ok = run_registration(
    csv_path="qa_output/pipeline/qa_pairs_cc_news_1per_chunks_20260925_101500.csv",
    collection_name="cc_news_1per",
    recreate=False,
    batch_size=100,
    provider="gemini",
    ui_output_dir="qa_output",
)
print(ok)
# True
# （qa_output/qa_pairs_cc_news_1per_chunks.csv が作られる）
```

> ⚠️ **注意**: ベクトル生成に失敗したバッチはスキップされ、それでも `True` が返る。登録件数はログの
> `✅ 進捗: N / M 件完了` で確かめること。

### 5.4 チャンク化関数

#### `chunk_text_file`

**概要**: テキストファイルをセマンティックチャンク化し、チャンク CSV のパスを返す。`.txt` 入力のときだけ `main()` が呼ぶ。

```python
def chunk_text_file(txt_path: Path, output_dir: str, model: str) -> str
```

| パラメータ | 型 | デフォルト | 説明 |
|------------|------|-----------|------|
| `txt_path` | Path | - | 入力テキストファイル（UTF-8） |
| `output_dir` | str | - | チャンク CSV の出力先（CLI の `--chunk-output`・既定 `output_chunked`） |
| `model` | str | - | チャンク化に使う LLM（CLI の `--chunk-model`・既定 `claude-haiku-4-5`） |

| 項目 | 内容 |
|------|------|
| **Input** | `txt_path: Path`, `output_dir: str`, `model: str` |
| **Process** | 1. `require_anthropic_key(".txt のチャンク化")` — `ANTHROPIC_API_KEY` が無ければエラーログを出して終了コード 1<br>2. 本文を読み、空白だけなら終了コード 1<br>3. `generate_output_filename()` で `<output_dir>/<入力名>_chunks.csv` を決める（ディレクトリは作る）<br>4. `run_chunking_sync(text, model, max_workers=8, block_size=1000, output_file, dataset_type=<入力名>, source_file=<ファイル名>)` でチャンク化し CSV を書く<br>5. チャンクが 0 件、または CSV ができていなければ終了コード 1 |
| **Output** | `str`: チャンク CSV のパス。チャンク化中の例外（連続失敗による `ChunkingAbortedError` など）はそのまま呼び出し側へ伝わり、`main()` が「致命的なエラー」として終了コード 1 にする |

**戻り値例**:
```python
"output_chunked/document_chunks.csv"
```

```python
# 使用例（ANTHROPIC_API_KEY が必要）
from pathlib import Path
from qa_qdrant.make_qa_register_qdrant import chunk_text_file

csv_path = chunk_text_file(Path("data/document.txt"), output_dir="output_chunked", model="claude-haiku-4-5")
print(csv_path)
# output_chunked/document_chunks.csv
```

#### `require_anthropic_key`

**概要**: LLM を呼ぶ工程（`.txt` のチャンク化・Q/A 生成）の前に `ANTHROPIC_API_KEY` を確かめる。Q/A 済み CSV を登録するだけの経路では呼ばない（Embedding は Gemini なので要らない）。

```python
def require_anthropic_key(purpose: str) -> None
```

| 項目 | 内容 |
|------|------|
| **Input** | `purpose: str` — エラーログに出す用途（例 `"Q/A 生成"`、`".txt のチャンク化"`） |
| **Process** | 環境変数 `ANTHROPIC_API_KEY` が空・未設定なら `ANTHROPIC_API_KEYが設定されていません（<purpose>に必要）` をログに出して `sys.exit(1)` |
| **Output** | `None`（キーがあれば何もしない） |

### 5.5 ユーティリティ関数

#### `normalize_source_filename`

**概要**: ファイル名に含まれる日時サフィックス `_YYYYMMDD_HHMMSS` を取り除き、実行のたびに変わらない名前にする。

```python
def normalize_source_filename(filename: str) -> str
```

| パラメータ | 型 | デフォルト | 説明 |
|------------|------|-----------|------|
| `filename` | str | - | ファイル名（パスではなく basename を想定） |

| 項目 | 内容 |
|------|------|
| **Input** | `filename: str` |
| **Process** | 正規表現 `_\d{8}_\d{6}` に一致する部分を**すべて**空文字に置き換える |
| **Output** | `str`: 正規化したファイル名（一致が無ければ入力のまま） |

**戻り値例**:
```python
"qa_pairs_cc_news_1per_chunks.csv"
```

```python
# 使用例
from qa_qdrant.make_qa_register_qdrant import normalize_source_filename

print(normalize_source_filename("qa_pairs_cc_news_1per_chunks_20260925_101500.csv"))
# qa_pairs_cc_news_1per_chunks.csv
print(normalize_source_filename("qa_pairs_livedoor.csv"))
# qa_pairs_livedoor.csv
```

---

## 6. 設定・定数

### 6.1 CLI 引数

`python qa_qdrant/make_qa_register_qdrant.py --help` が正。以下は 2026-09-25 時点の実装値。

| グループ | 引数 | 既定値 | 説明 |
|---------|------|-------|------|
| 入力（どちらか 1 つ） | `--dataset` | — | 事前定義データセット名（`config.DATASET_CONFIGS` のキー） |
| | `--input-file` | — | 入力ファイル（`.csv` / `.txt`。§3.1） |
| CSV 処理 | `--text-column` | `text` | 本文列の列名。判定に使い、`QAPipeline(text_column=...)` へ渡す（この列が無く `Combined_Text` があればそちら・§3.3 の 4） |
| チャンク化（`.txt` のみ） | `--chunk-output` | `output_chunked` | チャンク CSV の出力先 |
| | `--chunk-model` | `claude-haiku-4-5` | チャンク化に使う LLM（チャンク化 CLI・データ管理タブの既定と同じ） |
| Q/A 生成 | `--model` | `claude-sonnet-5` | `QAPipeline` に渡す LLM モデル（Anthropic Claude） |
| | `--max-docs` | `None` | 処理する最大チャンク数 |
| | `--use-celery` | off | Celery 並列で生成する |
| | `-c`, `--concurrency` | `8` | 並列タスク数。`start_celery.sh -c` と同じ値を推奨 |
| | `--celery-workers` | `1` | **非推奨**。ワーカー数チェック用（後方互換のため残っている） |
| | `--batch-chunks` | `3` | 1 回の API 呼び出しで処理するチャンク数 |
| Qdrant 登録 | `--collection` | —（**必須**） | 登録先コレクション名 |
| | `--recreate` | off | コレクションを作り直す |
| | `--batch-size` | `100` | Embedding・アップサートのバッチサイズ |
| | `--provider` | `gemini` | Embedding プロバイダ。**`gemini` のみ**（`choices`。他の値は終了コード 2・§3.3 の 3） |
| 出力 | `--output` | `qa_output/pipeline` | Q/A CSV / JSON の出力先 |
| | `--ui-output` | `qa_output` | UI 用 CSV の出力先 |

> カバレッジ分析（`analyze_coverage`）は常に `True` で `QAPipeline.run()` に渡され、CLI からは切り替えられない。

### 6.2 環境変数

| 変数 | 起動時の検査 | 用途 |
|------|:-----------:|------|
| `GOOGLE_API_KEY` | ✅（無ければ終了コード 1） | Embedding（Gemini `gemini-embedding-001`） |
| `ANTHROPIC_API_KEY` | Q/A を生成するときだけ ✅（`.txt`・チャンク済み CSV・`--dataset`。生成・チャンク化の前。無ければ終了コード 1） | チャンク化と Q/A 生成（`QAPipeline` → `SmartQAGenerator`）。Q/A 済み CSV を登録するだけなら不要 |

### 6.3 モジュール定数・副作用

| 項目 | 値 |
|------|----|
| ログ設定 | import 時に `logging.basicConfig(level=INFO, format='%(asctime)s - %(levelname)s - %(message)s')` |
| `sys.path` | import 時に先頭へプロジェクトルートを挿入 |
| 日時サフィックスの正規表現 | `_\d{8}_\d{6}`（`normalize_source_filename()`） |
| `CHUNK_DEFAULT_MODEL` / `CHUNK_DEFAULT_OUTPUT_DIR` | `claude-haiku-4-5` / `output_chunked`（`--chunk-model` / `--chunk-output` の既定） |
| `CHUNK_WORKERS` / `CHUNK_BLOCK_SIZE` | `8` / `1000`（`.txt` のチャンク化の並列数・ブロック文字数。CLI からは変えられない） |

---

## 7. エクスポート

`__all__` の定義はありません。外部から使える要素は次の 5 つです（`__main__` 実行時は `main()` を呼ぶ）。

```python
main                        # CLI エントリーポイント
chunk_text_file             # .txt のチャンク化
require_anthropic_key       # LLM を呼ぶ工程の前の ANTHROPIC_API_KEY 確認
run_registration            # Phase 2（Embedding → Qdrant 登録 → UI 用 CSV）
normalize_source_filename   # 日時サフィックスの除去
```

> 📌 本モジュールを直接 import しているコードはリポジトリ内に無い（2026-09-25 grep。参照はコメント・docstring のみ）。
> テストは `backend/tests/test_make_qa_register_qdrant_exit_code.py`（2 件・登録の成否と終了コード）、
> `backend/tests/test_make_qa_register_qdrant_txt_input.py`（3 件・`.txt` のチャンク化とその失敗系）、
> `backend/tests/test_make_qa_register_qdrant_startup_checks.py`（4 件・`ANTHROPIC_API_KEY` の事前確認と `--provider` の拒否）、
> `backend/tests/test_qa_pipeline_text_column.py`（6 件・`--text-column` が `QAPipeline` へ渡ること）、
> `backend/tests/test_model_table_coverage.py`（CLI `--model` の既定値が単価・上限表に載っているか）がある。

---

## 8. 変更履歴

| バージョン | 変更内容 |
|-----------|---------|
| 1.0 | 初版作成（2026-09-25）。`qa_qdrant/docs/README.md` の残タスク（本モジュールの IPO 文書が無い）を解消。実装を読み、ダミーキーで CLI を実行して、`.txt` 入力が必ず失敗すること・Qdrant 登録失敗でも終了コード 0 になることを確認し、`--provider` / `--text-column` が効かないことと合わせて §3.3 に記録した（コードは未変更） |
| 1.1 | §3.3 の 2（Qdrant 登録が失敗しても終了コード 0）の修正に追随（2026-09-25）。`main()` は Phase 2 の失敗で `sys.exit(1)` するようになった。§5.2 の Output・§5.1.3 の注記・§7 のテストの記述を更新 |
| 1.2 | §3.3 の 1（`.txt` 入力が必ず失敗する）の修正に追随（2026-09-25）。`.txt` は `chunk_text_file()` で先にチャンク化してから Q/A 生成するようになった。概要・責務表・構成図 3 枚・§3.1 の判定表と図・§3.2 の出力・§5.4（`chunk_text_file` の IPO を新設。旧 §5.4 は §5.5 へ）・§5.1.2 の使用例・§6 の CLI 引数／環境変数／定数・§7 を更新。あわせて §5.2 の Process 7 に残っていた「登録失敗時はエラーログだけ」（v1.1 の取り残し）を「終了コード 1」へ直した |
| 1.3 | §3.3 の 3（`--provider` が効かない）と 5（`ANTHROPIC_API_KEY` を起動時に確かめない）の修正に追随（2026-09-25）。`--provider` は `choices=["gemini"]`、Q/A を生成する経路では新設の `require_anthropic_key()` が生成前に確かめる。概要の注記・§1.2・§3.3・§4.2・§5.2・§5.3 の `provider`・§5.4（`require_anthropic_key` の IPO を追加）・§6.1／§6.2・§7 を更新 |
| 1.4 | §3.3 の 4（`--text-column` が Q/A 生成に渡らない）の修正に追随（2026-09-25）。これで §3.3 の 5 件はすべて解消。概要の注記・§3.1 の 4・§3.3・§6.1・§7 を更新 |
| 1.5 | §3.2 の `<種別>` の記述を是正（2026-09-26）。「`--dataset` のときはデータセット設定の `type`」は誤りで、`type` キーが無いため一律 `unknown` になっていた。`QAPipeline._load_config()` がデータセット名で補うよう直したのに合わせ、出力名・チャンク ID・途中経過ファイルがデータセット間で共有されていたことも記録 |

---

## 付録: 依存関係図

```mermaid
flowchart LR
    MQR["make_qa_register_qdrant.py"]

    subgraph STD["標準ライブラリ・pandas"]
        ARGP["argparse"]
        PD["pandas"]
        RE["re"]
    end

    subgraph QAGEN["qa_generation"]
        PIPE["QAPipeline"]
        SMART["SmartQAGenerator"]
    end

    subgraph SVC["services.qdrant_service"]
        COLL["create_or_recreate_collection_for_qdrant"]
        EMB["embed_texts_for_qdrant"]
        PTS["build_points_for_qdrant"]
        UPS["upsert_points_to_qdrant"]
    end

    subgraph CHUNKPKG["チャンク化"]
        RCS["services.data_pipeline_service.run_chunking_sync"]
        GOF["chunking.generate_output_filename"]
    end

    subgraph OTHER["その他"]
        CONF["config.DATASET_CONFIGS"]
        QCW["qdrant_client_wrapper.create_qdrant_client"]
    end

    MQR --> ARGP
    MQR --> PD
    MQR --> RE
    MQR --> PIPE
    PIPE --> SMART
    MQR --> COLL
    MQR --> EMB
    MQR --> PTS
    MQR --> UPS
    MQR --> CONF
    MQR --> QCW
    MQR --> RCS
    MQR --> GOF
classDef default fill:#000,stroke:#fff,color:#fff
classDef subgraphStyle fill:#1a1a1a,stroke:#fff,color:#fff
class MQR,ARGP,PD,RE,PIPE,SMART,COLL,EMB,PTS,UPS,CONF,QCW,RCS,GOF default
style STD fill:#1a1a1a,stroke:#fff,color:#fff
style QAGEN fill:#1a1a1a,stroke:#fff,color:#fff
style SVC fill:#1a1a1a,stroke:#fff,color:#fff
style OTHER fill:#1a1a1a,stroke:#fff,color:#fff
style CHUNKPKG fill:#1a1a1a,stroke:#fff,color:#fff
```
