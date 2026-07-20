# backend/ ドキュメント整備インデックス

**Version 1.3** | 最終更新: 2026-07-15

> ✅ **本インデックス掲載のモジュール仕様（IPO）9 ファイルはすべて作成済み**（§2 参照）。

`backend/`（GRACE-Support Web API: FastAPI + コアサービス）配下のモジュールについて、
ドキュメント作成対象・出力先・進捗を一覧化した資料。個別モジュールの詳細ドキュメントは
IPO 形式（`.claude/skills/grace-agent-docs/a_class_method_md_format.md`）で作成し、
`backend/app/doc/<module>.md` に配置する。

---

## 0. アプリの実行方法（クイックスタート）

GRACE-Support は **FastAPI（バックエンド, :8000）＋ Vite + React（フロントエンド, :5173）** の
2 プロセス構成。**画面は :5173 で開く**（:8000 は API 専用で、`/` は 404 が正常）。

> 📦 初回のインストール・環境構築（uv / Node / Docker / `.env` / トラブルシュート）は
> **[`install_and_setup.md`](./install_and_setup.md)** を参照。以下は導入済み前提の起動手順。

**前提**: リポジトリルートの `.env` に `ANTHROPIC_API_KEY`（LLM）と `GOOGLE_API_KEY`（Embedding）、
Python 3.11+ / `uv` / Node.js / Docker が導入済み。

### 最短（推奨・1 コマンドで起動）

```bash
# 1) Qdrant（ベクトルDB）を起動（別実行・初回/停止後のみ）
docker-compose -f docker-compose/docker-compose.yml up -d

# 2) backend + frontend を 1 コマンドで起動（依存の用意も自動）
./run_dev.sh
#   → backend:  http://localhost:8000（/docs）
#   → frontend: http://localhost:5173  ← ブラウザで開くのはこちら
#   停止は Ctrl+C（両方まとめて停止）
```

`run_dev.sh` は `uv sync --extra dev` → frontend 依存の用意 → uvicorn(:8000) と
Vite(:5173) の同時起動までを行う（リポジトリルートの `run_dev.sh`）。

### 手動（プロセスを分けて起動）

```bash
# 1) Qdrant（ベクトルDB）を起動
docker-compose -f docker-compose/docker-compose.yml up -d

# 2) バックエンド（FastAPI）★リポジトリルートで実行
uv sync --extra dev
uv run uvicorn backend.app.main:app --reload --port 8000
#   → API: http://localhost:8000 、自動ドキュメント: http://localhost:8000/docs

# 3) フロントエンド（別ターミナル）
cd frontend
npm install
npm run dev
#   → UI: http://localhost:5173（/api は :8000 へ proxy）
```

ブラウザで **http://localhost:5173** を開く。フロントの `/api/*` は Vite の proxy
（`frontend/vite.config.ts`）で :8000 の FastAPI へ中継される（SSE 進捗も同経路）。

**CLI 版**（従来どおり・コア共有）:

```bash
uv run python agent_support_example.py --vertical ec "返品したい"
```

**動作確認だけ**したい場合: `http://localhost:8000/api/health`（APIキー設定の有無を返す）。

---

## 1. 対象範囲と方針

- **対象**: `backend/app/` 配下の Python モジュール（FastAPI 起動・API 層・コア層・スキーマ）。
- **フォーマット**:
  - モジュール（クラス/関数）… IPO 形式（`a_class_method_md_format.md`）
  - 単体テスト … SAE 形式（`a_test_md_format.md`、`grace-agent-tests` スキル担当）
- **出力先**: モジュールドキュメントは既存規約 `<package>/doc/<module>.md` に合わせ
  **`backend/app/doc/<module>.md`**。本インデックスは `backend/docs/README.md`。
- **技術スタック表記**: LLM = Anthropic Claude（既定 `claude-sonnet-4-6`）／
  Embedding = Gemini（`gemini-embedding-001`, 3072次元）。

---

## 2. モジュール仕様（IPO 形式）作成対象

| # | ソースファイル | 行数 | クラス/関数 | 役割 | ドキュメント出力先 | 優先度 | 状態 |
|---|---|---:|---:|---|---|:--:|:--:|
| 1 | `backend/app/main.py` | 49 | 0（モジュール構成のみ） | FastAPI 起動・CORS・ルーター結線 | `backend/app/doc/main.md` | ★ | ✅ 作成済 |
| 2 | `backend/app/schemas.py` | 106 | 9 | Pydantic リクエスト/レスポンス/イベント型 | `backend/app/doc/schemas.md` | 高 | ✅ 作成済 |
| 3 | `backend/app/api/support.py` | 83 | 4 | `/api/support/*`（query / stream(SSE) / confirm / result） | `backend/app/doc/api_support.md` | 高 | ✅ 作成済 |
| 4 | `backend/app/api/meta.py` | 42 | 2 | `/api/verticals`・`/api/health` | `backend/app/doc/api_meta.md` | 中 | ✅ 作成済 |
| 5 | `backend/app/core/support_agent.py` | 534 | 5 | ★コア（イベント発行型パイプライン） | `backend/app/doc/core_support_agent.md` | 最高 | ✅ 作成済 |
| 6 | `backend/app/core/gates.py` | 371 | 14 | 回答ゲート/強制エスカレ/情報なし検知/救済（純関数群） | `backend/app/doc/core_gates.md` | 高 | ✅ 作成済 |
| 7 | `backend/app/core/jobs.py` | 168 | 3 | ジョブ管理（インメモリ） | `backend/app/doc/core_jobs.md` | 中 | ✅ 作成済 |
| 8 | `backend/app/core/intervention_bridge.py` | 125 | 2 | HITL ↔ フロント承認の非同期ブリッジ | `backend/app/doc/core_intervention_bridge.md` | 中 | ✅ 作成済 |
| 9 | `backend/app/core/verticals.py` | 84 | 2 | VerticalProfile 定義（業界プロファイル） | `backend/app/doc/core_verticals.md` | 中 | ✅ 作成済 |

---

## 3. テスト仕様（SAE 形式）で扱うファイル

> 本インデックスの担当外（`grace-agent-tests` スキル・別フォーマット）。参考として掲載。

| ソースファイル | 行数 | 内容 |
|---|---:|---|
| `backend/tests/test_support_agent_core.py` | 214 | CLI とコアの同等性テスト |
| `backend/tests/test_api.py` | 163 | API エンドポイントのテスト |
| `backend/tests/test_intervention_bridge.py` | 105 | HITL ブリッジのテスト |
| `backend/tests/conftest.py` | 119 | pytest フィクスチャ（スタブベース・API キー不要） |

---

## 4. ドキュメント不要（対象外）

いずれも空ファイル（0 行）:

- `backend/__init__.py`
- `backend/app/__init__.py`
- `backend/app/api/__init__.py`
- `backend/app/core/__init__.py`
- `backend/tests/__init__.py`

---

## 5. backend/ 構成（参考）

```
backend/
├── app/
│   ├── main.py                     # FastAPI 起動・CORS（ドキュメント: app/doc/main.md）
│   ├── schemas.py                  # Pydantic: リクエスト/レスポンス/イベント
│   ├── api/
│   │   ├── support.py              # POST /api/support/query, GET /stream(SSE), POST /confirm, GET /result
│   │   └── meta.py                 # GET /api/verticals, GET /api/health
│   ├── core/
│   │   ├── support_agent.py        # ★コアサービス（イベント発行型パイプライン）
│   │   ├── gates.py                # 回答ゲート/強制エスカレ/情報なし検知/救済（純関数）
│   │   ├── intervention_bridge.py  # HITL ↔ フロント承認の非同期ブリッジ
│   │   ├── jobs.py                 # ジョブ管理（インメモリ）
│   │   └── verticals.py            # VerticalProfile 定義
│   └── doc/                        # ← モジュールドキュメント（IPO形式）の出力先
└── tests/                          # pytest（スタブベース・API キー不要）
```

---

## 6. 進行順（実績）

モジュール仕様（IPO）9 ファイルは以下の順で作成済み:

1. ✅ `core/support_agent.py`（最高・コア） → `core_support_agent.md`
2. ✅ `schemas.py` → `schemas.md`
3. ✅ `api/support.py` → `api_support.md`
4. ✅ `core/gates.py` → `core_gates.md`
5. ✅ `core/jobs.py` → `core_jobs.md`
6. ✅ `core/intervention_bridge.py` → `core_intervention_bridge.md`
7. ✅ `core/verticals.py` → `core_verticals.md`
8. ✅ `api/meta.py` → `api_meta.md`
9. ✅ `main.py` → `main.md`（既出）

次段: テスト仕様（SAE 形式・§3）の整備は `grace-agent-tests` スキルで別途対応予定。

---

## 7. 変更履歴

| バージョン | 変更内容 |
|-----------|---------|
| 1.0 | 初版作成（backend/ ドキュメント整備の対象一覧・出力先・進捗をまとめたインデックス。`main.py` を作成済としてマーク） |
| 1.1 | モジュール仕様（IPO）残り 8 ファイル（schemas / api_support / api_meta / core_support_agent / core_gates / core_jobs / core_intervention_bridge / core_verticals）を作成し、状態列を全て「作成済」に更新 |
| 1.2 | 先頭に「§0 アプリの実行方法（クイックスタート）」を追加し、`install_and_setup.md`（インストール・環境設定）へのリンクを追記 |
| 1.3 | §0 に「最短（1 コマンド `./run_dev.sh`）」の起動方法を追加（backend + frontend を一括起動） |
