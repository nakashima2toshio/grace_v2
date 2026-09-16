# データ管理（チャンキング / Q&A 生成 / Qdrant CRUD） — 移転のお知らせ

**Version 2.0** | 最終更新: 2026-09-12

---

> # 📦 本書の内容は `backend/docs/` へ移転しました
>
> v1.0（2,313 行・2026-08-05）は、データ管理機能の IPO 詳細をこの 1 ファイルに
> まとめていました。その後 `backend/docs/` に**モジュール単位の文書が整備され、
> 記述対象が完全に重複**したため、本書は**索引**に役割を変えます。
>
> **v1.0 の内容は git 履歴に残っています**（`git show HEAD~1:README_DATA.md`）。

---

## なぜ移転したか

| 観点 | v1.0 の状態 |
|---|---|
| 陳腐化 | **2026-09-12 に追加された「② Q/A 作成」の記述が 0 件**だった（`QaGenerationParams` / `_qa_runner` / `POST /api/qa/generate` のいずれも未記載） |
| 重複 | 記述していた **18 個のクラス・関数すべてが `backend/docs/` 側にも存在**していた（2026-09-12 実測） |
| 参照 | ルート `README.md` からの参照が **1 箇所だけ**（§8 の関連文書表） |
| 分量 | 2,313 行。同じ領域を `backend/docs/data_pipeline.md`（563 行）ほか 3 文書が扱っていた |

**1 つの内容を 2 箇所で保守すると、必ず片方が腐る。** 実際に v1.0 は
「② Q/A 作成」を丸ごと落としていました。

---

## どこを読めばよいか

### 全体像から入る

| 知りたいこと | 文書 |
|---|---|
| **データ準備 3 工程の設計全体**（チャンク化 → Q/A 生成 → Qdrant 登録） | [`backend/docs/data_pipeline.md`](./backend/docs/data_pipeline.md) |
| 画面から何ができるか・操作と実装の対応 | [`README.md`](./README.md) §4.5「データ管理画面」 |
| 環境構築（MeCab / Docker / Celery） | [`qa_qdrant/docs/01_install.md`](./qa_qdrant/docs/01_install.md) |
| Celery 並列の起動手順 | [`qa_qdrant/docs/celery_quick_start.md`](./qa_qdrant/docs/celery_quick_start.md) |

### モジュール単位で読む

| 実装 | 文書 |
|---|---|
| `backend/app/api/data.py` — ジョブ起動・SSE・HITL | [`backend/docs/reference/api_data.md`](./backend/docs/reference/api_data.md) |
| `backend/app/api/qdrant.py` — Qdrant 参照 API（読み取り専用） | [`backend/docs/reference/api_qdrant.md`](./backend/docs/reference/api_qdrant.md) |
| `backend/app/core/data_jobs.py` — 3 種の runner・ステップ定義・CONFIRM の要否 | [`backend/docs/reference/core_data_jobs.md`](./backend/docs/reference/core_data_jobs.md) |
| `backend/app/core/job_logs.py` — 既存パッケージの `logging` を進捗イベントへ転送 | [`backend/docs/reference/core_job_logs.md`](./backend/docs/reference/core_job_logs.md) |
| `services/data_pipeline_service.py` — パス検証・Qdrant 操作・データ変換 | [`services/docs/data_pipeline_service.md`](./services/docs/data_pipeline_service.md) |
| `services/qdrant_service.py` — Qdrant クライアント・ヘルスチェック | [`services/docs/qdrant_service.md`](./services/docs/qdrant_service.md) |
| `qa_generation/pipeline.py` — `QAPipeline` | [`qa_generation/docs/pipeline.md`](./qa_generation/docs/pipeline.md) |
| `chunking/csv_text_to_chunks_text_csv.py` — セマンティックチャンキング | [`chunking/docs/csv_text_to_chunks_text_csv.md`](./chunking/docs/csv_text_to_chunks_text_csv.md) |

### React 側

| コンポーネント | 文書 |
|---|---|
| `DataPanel.tsx` — データ管理タブの枠（サブタブ 4 つ） | [`frontend/docs/DataPanel.md`](./frontend/docs/DataPanel.md) |
| `DataJobPanel.tsx` — 3 種のジョブ（チャンキング / Q/A 作成 / Qdrant 登録） | [`frontend/docs/DataJobPanel.md`](./frontend/docs/DataJobPanel.md) |
| `CollectionPanel.tsx` — コレクション管理 | [`frontend/docs/CollectionPanel.md`](./frontend/docs/CollectionPanel.md) |

---

## v1.0 が記述していたシンボルの移転先

2026-09-12 に 18 件すべての移転先を確認した（欠落なし）。

| シンボル | 移転先 |
|---|---|
| `JobLogHandler` / `capture_logs` / `_acquire_level` / `_release_level` | `backend/docs/reference/core_job_logs.md` |
| `ChunkingParams` / `RegisterParams` / `DeleteParams` / `QaGenerationParams` | `backend/docs/reference/api_data.md`・`core_data_jobs.md` |
| `_chunking_runner` / `_register_runner` / `_qa_runner` / `_ask_confirmation` | `backend/docs/reference/core_data_jobs.md` |
| `resolve_allowed_dir` / `list_input_files` / `resolve_input_file` | `backend/docs/data_pipeline.md`・`api_qdrant.md` |
| `delete_collection` / `collection_exists` | `backend/docs/reference/api_data.md`・`api_qdrant.md` |
| `dataframe_to_records` / `collection_columns` | `backend/docs/reference/api_qdrant.md` |
| `run_chunking_sync` / `load_input_text` | `backend/docs/reference/core_data_jobs.md` |
| `PathNotAllowedError` | `services/docs/data_pipeline_service.md` |

> 📌 **v1.0 に無く、移転先にはあるもの**: `QaGenerationParams` / `_qa_runner` /
> `POST /api/qa/generate`（②Q/A 作成、2026-09-12 追加）。
> **移転先の方が新しい。**

---

## 変更履歴

| 版 | 日付 | 変更内容 |
|---|---|---|
| 2.0 | 2026-09-12 | **索引へ変更。** 記述対象 18 件がすべて `backend/docs/` 側にも存在し（実測）、かつ v1.0 は「② Q/A 作成」を一切含まない陳腐化状態だったため、内容の二重保守をやめて移転先を示す形にした。v1.0 の本文は git 履歴（`git show <この commit>~1:README_DATA.md`）で参照できる |
| 1.0 | 2026-08-05 | 初版作成（2,313 行・IPO 形式） |
