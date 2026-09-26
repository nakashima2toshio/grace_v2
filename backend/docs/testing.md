# backend テストの地図 ドキュメント

**Version 1.2** | 最終更新: 2026-09-26

---

## 目次

- [概要](#概要)
- [1. 実行方法](#1-実行方法)
- [2. テストの地図](#2-テストの地図)
- [3. どこを触ったらどれを流すか](#3-どこを触ったらどれを流すか)
- [4. 設計方針](#4-設計方針)
- [5. CI の 4 ゲート](#5-ci-の-4-ゲート)
- [6. 変更履歴](#6-変更履歴)

---

## 概要

> **本書の位置づけ**: `backend/tests` に何があり、**どこを触ったらどれを流すか**をまとめる。
> テストの書式（SAE 形式）は `.claude/skills/grace-agent-tests/a_test_md_format.md`、
> CI の設定は `.github/workflows/ci.yml` が正本。

> **関連ドキュメント**
> - [`architecture.md`](./architecture.md) — どのモジュールが何を担うか
> - [`pitfalls.md`](./pitfalls.md) — 共用部品を壊さないための注意
> - [`install_and_setup.md`](./install_and_setup.md) — 実行環境の準備

### 結論

- 実行は `uv run --no-sync pytest backend/tests -q -rs`（§1）。実 API キー・Qdrant は不要
- **どこを触ったらどれを流すか**は §3。共有基盤（`jobs.py` ほか）と共用部品を触ったら全体を流す
- CI の必須ゲートは 4 つ（§5）

### 対象モジュール

| # | モジュール | 関係 |
|---|---|---|
| 1 | `backend/tests/` | テスト本体（§2 の地図） |
| 2 | `requirements-test.txt` | テスト用依存の正本（CI と共有） |
| 3 | `.github/workflows/ci.yml` | 4 ゲートの定義 |

---

## 1. 実行方法

**実 API キー・実 Qdrant は不要**（外部依存は `conftest.py` がスタブへ差し替える）。

> ⚠️ **キーが「無くてよい」だけでなく、「あっても結果が変わらない」ことを保つ。**
> `RAGSearchTool.execute` は候補コレクションが 2 つ以上あると `_embed_query_once` で
> クエリを実 Embedding API（Gemini）に 1 回だけ埋め込み、検索関数へ `precomputed_*` を渡す。
> キーが無い環境（CI）では埋め込みが失敗して `None` になるため表に出ないが、
> `GOOGLE_API_KEY` がある環境では**単体テストから実 API を呼び**、`lambda _q, col: ...` の
> ような 2 引数スタブが例外になって 0 件になる（2026-09-26 に 8 件の失敗として実測）。
> **`execute` を回すテストは `_embed_query_once` を `(None, None)` に差し替える**
> （`test_rag_adoption.py` / `test_memory_exclusion.py` / `test_collection_selection.py` の補助関数）。
> 埋め込みの再利用そのものは `test_query_vector_reuse.py` が `embed_query` を差し替えて検証している。

```bash
# 初回のみ: テスト用の依存（CI と共有する唯一の正本）
uv venv
uv pip install -r requirements-test.txt

# 実行
uv run --no-sync pytest backend/tests -q -rs
```

> ⚠️ **`--no-sync` を付ける。** 付けないと `uv run` が `pyproject.toml` の
> `[project] dependencies`（221 行・spacy / matplotlib 等）で環境を同期し直し、
> `requirements-test.txt` で作った軽い環境が上書きされる。

> ⚠️ **`backend/tests` が import するパッケージを足したら `requirements-test.txt` に追記する。**
> CI はこのファイルを読むので、YAML 側を直す必要は無い。

**実測（2026-09-16）**: `978 passed, 1 skipped, 3 warnings in 9.51s`。
スキップ 1 件は `test_config_file_and_memory.py`（`logs/` が無い環境では対象外）。

---

## 2. テストの地図

実測 2026-09-16: `test_*.py` が **58 ファイル**、`def test_` が **867 個**
（パラメータ化を展開した実行数が上の 978）。

### 2.1 GRACE-Review 系（18 ファイル）

**`backend/tests` の約 1/3 が Review 系**である。共用部品を触ったら必ず流す。

| テスト | 対象 |
|---|---|
| `test_review_agent_core.py` | パイプライン S1・①〜⑦ の配線と KPI カウンタ |
| `test_review_gates.py` | しきい値による status 判定・救済・severity 調整・強制 high |
| `test_review_api.py` | submit / stream / confirm / result の応答、422 ガード |
| `test_rulesets.py` | `RuleSet` / `RuleItem` の整合（`always_check` と `keywords` の排他ほか） |
| `test_review_evidence_threshold.py` / `test_review_evidence_top_ratio.py` | ② Retrieve の根拠採用しきい値 |
| `test_review_document_scope.py` / `test_review_document_excerpt.py` / `test_review_absence_excerpt.py` | 文書全体スコープ（`always_check`）の扱い |
| `test_review_detect_criteria_in_prompt.py` / `test_review_detect_failure_status.py` | ③ Detect のプロンプトと判定失敗時の安全側 |
| `test_review_ground_sources.py` / `test_review_undecided_groundedness.py` | ④ Ground の出典と「判定できていない」の扱い |
| `test_review_rule_subject_scope.py` / `test_review_multi_item_rules.py` / `test_review_no_duplicate_findings.py` | ルール主題の限定・重複指摘の抑止 |
| `test_review_policy_evidence.py` / `test_review_safety_claim.py` / `test_review_yakki_product_scope.py` | 個別ルールの回帰 |
| `test_export_ruleset_to_csv.py` | ルールセットの書き出し |

> 📝 **設計時の想定と実装は一致していない。** 旧 `review_spec.md` §9 は
> `test_review_segment.py` を挙げていたが、そのファイルは**存在しない**（実測 2026-09-16）。
> ① Segment の検証は `test_review_agent_core.py`（`split_segments` を直接呼ぶ）にある。

**過検知の回帰テスト**を重視している（`backend/tests/data/` の 3 サンプル）。

| サンプル | 期待 |
|---|---|
| `ec_ad_ng_sample.txt` | 意図的に違反を仕込んだ LP（各カテゴリ 1 件以上） |
| `ec_ad_ok_sample.txt` | 適正表記の LP → **指摘 0 件**（過検知テスト） |
| `ec_ad_edge_sample.txt` | 否定文脈の「No.1」等 → **強制 high にしない**（誤検知抑止テスト） |

### 2.2 GRACE-Support 系

| テスト | 対象 |
|---|---|
| `test_support_agent_core.py` | パイプライン 0-(A)〜⑥ の配線（14 件） |
| `test_multi_question.py` / `test_multi_question_pipeline.py` | 0-(A) 複数質問の分析・選択・再構成（85 件） |
| `test_no_info_judge.py` / `test_no_info_prediction.py` | ④' 情報なし回答検知 |
| `test_vertical_scope.py` | 業界プロファイルによる検索スコープ限定 |
| `test_policy_claims.py` / `test_source_attribution.py` / `test_rag_adoption.py` | 出典・根拠の扱い |

### 2.3 共有基盤・API・データ準備

| テスト | 対象 |
|---|---|
| `test_jobs_generic.py` | **ジョブ基盤の汎用化（Support の既存挙動が変わらないことの回帰・18 件）** |
| `test_intervention_bridge.py` | HITL 承認の橋渡し（タイムアウト＝実行しない） |
| `test_job_logs.py` | ログ転送（スレッド絞り込み・level の参照カウント） |
| `test_done_event_timing.py` | `done` 番兵の `ts` / `started_at` |
| `test_api.py` | Support API の応答 |
| `test_data_jobs.py` / `test_data_pipeline.py` / `test_chunking_abort.py` / `test_collection_selection.py` | データ準備 4 ジョブ |
| `test_config_isolation.py` / `test_config_file_and_memory.py` / `test_scope_and_models.py` / `test_model_table_coverage.py` | 設定・モデル解決 |

---

## 3. どこを触ったらどれを流すか

| 触った場所 | 最低限流すもの |
|---|---|
| `core/jobs.py` / `intervention_bridge.py` / `job_logs.py`（**共有基盤**） | 全体（`pytest backend/tests`）。特に `test_jobs_generic.py` |
| `core/gates.py`（Support の判定） | `test_support_agent_core.py` `test_multi_question*.py` `test_no_info_*.py` ＋ **Review 系 18 本**（`_match_keyword` / `judge_model` を共用） |
| `core/review_*.py` / `rulesets.py` | `test_review_*.py` `test_rulesets.py` |
| `grace.confidence` / `support_actions.py`（**Support / Review 共用**） | 全体 |
| `schemas.py` / `api/*.py` | `test_api.py` `test_review_api.py` ＋ **frontend ゲート**（`types.ts` の追随） |
| `core/data_jobs.py` | `test_data_jobs.py` `test_data_pipeline.py` |

---

## 4. 設計方針

1. **外部依存はスタブで差し替える。** `conftest.py` が planner / executor / verifier /
   tools / LLM 分類器を置き換えるため、API キー・Qdrant・実 LLM なしで
   「イベント・HITL・判定の流れ（配線）」を検証できる。
2. **判定は純関数として固定する。** `gates.py` / `review_gates.py` の純関数は
   スタブなしで直接テストできる。判断ロジックをコアへ埋め込まない理由でもある。
3. **回帰は「修正前のコードで fail すること」を確認してから入れる。**
   fail しないテストは回帰を捕まえていない（`CLAUDE.md` 作業原則）。
4. **過検知（false positive）を最優先で固定する。** Review では「指摘が多すぎて
   読まれない」が実用上の失敗であり、`ec_ad_ok_sample.txt` が 0 件であることを守る。

> フロントエンドは `vitest`（`frontend/src/**/*.test.ts`）。**`.test.tsx` は収集されない**ため、
> 判断ロジックは `frontend/src/state/` の純関数へ出す（`CLAUDE.md` §6）。

---

## 5. CI の 4 ゲート

すべて blocking。4 つ緑になると `claude/*` ブランチの PR は auto-merge が Ready 化して master へマージする。

| ジョブ | 内容 |
|---|---|
| `compile (syntax gate)` | `python -m compileall` |
| `ruff` | `ruff check .`（`ruff==0.12.11` 固定。再現は `uvx ruff@0.12.11 check . --no-cache`） |
| `pytest (backend)` | `pytest backend/tests -q -rs` |
| `frontend (tsc + vitest + build)` | `npm run lint` → `npm test` → `npm run build` |

> ⚠️ **frontend ゲートを忘れない。** Python 側が全部緑でも `frontend/src/types.ts` の
> 型エラー 1 個でマージは止まる。

---

## 6. 変更履歴

| Version | 日付 | 変更内容 |
|---|---|---|
| 1.0 | 2026-09-16 | 新規作成。`review_spec.md` §9（テスト方針）を取り込み、`backend/tests` の実測（58 ファイル / 867 関数 / 978 passed・1 skipped）から地図を書き起こした |
| 1.1 | 2026-09-24 | `a_cross_doc_md_format.md` v1.1（種別 B）に準拠（2026-09-24）。概要（結論・対象モジュール）を追加し、冒頭の説明文を概要へ移した。本文の章番号は変えていない |
| 1.2 | 2026-09-26 | §1 に「`GOOGLE_API_KEY` があっても結果が変わらないこと」の注意を追記。`RAGSearchTool.execute` を回す 3 ファイルがキーのある環境で実 Embedding API を呼び、8 件落ちていたのを是正したのに合わせた |
