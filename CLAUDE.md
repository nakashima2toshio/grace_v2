# CLAUDE.md

このファイルは Claude Code（claude.ai/code）が本リポジトリで作業するときの指針です。

---

## ⚠️ ファイル書き込みポリシー

### GitHub ブランチ操作：全許可
- ブランチへのコミット・プッシュ・PR作成・master へのマージを確認なしで実行してよい。
- **指定ブランチ以外への push や force push は事前に確認すること。**

### ローカルファイル操作：作業範囲内許可
- タスクに関連するファイルの新規作成・編集は確認なしで実行してよい。
- タスクと無関係なファイルへの書き込みは事前に確認すること。
- **ファイルの削除など不可逆的な操作は事前に確認すること。**

---

## ⚠️ 作業原則（最重要）

- **必ずコードをよく読んでから判断する。** 「現状コード＋慎重さ」を優先して**読まずに**進めると、
  バグにバグを重ねることになる（実際にそれで 1 日溶かした事例あり）。
- 修正・調査の前に、関連する実コード（クライアント生成・既定モデル・呼び出し経路・
  プロバイダ解決）を実際に追って確認すること。「たぶん意図的」で確認を打ち切らない。
- **やっていない検証を「やった」と書かない。** テストが落ちたら落ちたと出力付きで報告する。
- 回帰修正を入れるときは、**修正前のコードに当ててテストが fail することを確認**する。
  fail しないテストは回帰を捕まえていない。

---

## 1. プロジェクト概要

**GRACE** — 業界特化・自律型エージェント基盤。日本語 RAG（Retrieval-Augmented Generation）に
根拠検証（groundedness）・Web 裏取り・HITL（Human-In-The-Loop）アクションを組み合わせる。

### ⚠️ エージェントは 2 つある

| エージェント | 情報の流れ | コア関数 | 画面 |
|---|---|---|---|
| **GRACE-Support** | 問い合わせ → **回答** | `backend/app/core/support_agent.py::run_support_agent_core` | 「基本版」「GRACE-Support」タブ |
| **GRACE-Review** | 文書 → **指摘** | `backend/app/core/review_agent.py::run_review_agent_core` | 「GRACE-Review」タブ |

**Support だけ見て作業しない。** `tests` の約 1/4（72 ファイル中 18 ファイル・2026-09-25 実測）が
Review 系である。中核部品（`GroundednessVerifier` / `InterventionBridge` /
`support_actions.py` の `ActionBackend`）は**両者で共用**しているので、
Support のつもりで触った変更が Review を壊す。

| 層 | 実体 |
|---|---|
| フロントエンド | `frontend/` — Vite + React 18 + TypeScript（dev: `:5173`） |
| Web API | `backend/app/` — FastAPI（dev: `:8000`）。SSE でステップ進捗を配信 |
| Support コア | `backend/app/core/support_agent.py`、ゲートは `core/gates.py`、業界定義は `core/verticals.py` |
| Review コア | `backend/app/core/review_agent.py`、ゲートは `core/review_gates.py`、ルール定義は `core/rulesets.py` |
| 自律エージェント基盤 | `grace/` — planner / executor / confidence / intervention / replan / tools |
| ツール・検索 | `agent_tools.py`, `qdrant_client_wrapper.py`（Legacy ReAct 経路専用だった `agent_parallel_search.py` / `agent_cache.py` は 2026-10-10 に削除・§9.4） |
| アクション実行 | `support_actions.py`（`ActionBackend`。**Support / Review 共用**） |
| データ準備（CLI） | `chunking/`, `qa_generation/`, `qa_qdrant/` |
| データ準備（Web） | `backend/app/api/data.py` / `api/qdrant.py`、`backend/app/core/data_jobs.py`、`services/data_pipeline_service.py` |
| ベクトルDB | Qdrant（`docker-compose/docker-compose.yml`） |

### 画面は 4 タブ（`frontend/src/App.tsx`）

| タブ id | ラベル | 中身 |
|---|---|---|
| `basic` | 基本版 | `SupportPanel variant="basic"` — 業界プロファイル**セレクタを出さない** |
| `support` | GRACE-Support | `SupportPanel variant="vertical"` — 業界プロファイルを選ぶ |
| `review` | GRACE-Review | `ReviewPanel` — 文書 textarea → 指摘一覧（左右 2 ペイン） |
| `data` | データ管理 | `DataPanel` — チャンク化 / Q&A 作成 / Qdrant 登録 / コレクション管理 |

`basic` と `support` は**同じ `SupportPanel`** に `variant` を渡しているだけである
（別コンポーネントではない）。タブ切替はアンマウント方式。

### 業界プロファイル（vertical）— Support 用
`backend/app/core/verticals.py` に `gov` / `saas` / `ec` を定義。各プロファイルが
許可コレクション・エスカレーションキーワード・アクションマップ・閾値・プロンプト追記を持つ。

### ルールセット（ruleset）— Review 用
`backend/app/core/rulesets.py` に `ec_ad`（EC広告表示）を定義。`VerticalProfile` と役割は
似るが「1 プロファイル = N 個の検査ルール」を持つため**型を分けている**
（`RuleSet` / `RuleItem`）。現在 23 ルール（景表法 / 薬機法 / 特商法 / 社内方針）。
`GET /api/rulesets` と ① S1 の解決に使う。

### パイプライン 1 周（Support）
```
0-(A) 入力・質問分析（複数質問の検知 → 選択 → 再構成）
 → 0-(B) 業界プロファイル適用
 → ① Plan（planner）
 → ② Execute（内部RAG → reasoning）
 → ③ Confidence（GroundednessVerifier で根拠検証）
 → ④ 回答ゲート（＋強制エスカレ＋救済）
 → ⑤ Web フォールバック
 → ④' 情報なし回答の検知
 → ⑥ Action（本人確認 → HITL CONFIRM → 実行）
```
`support_rate = supported / (supported + contradicted)` — neutral は分母から除外する
（＝答えていない内容を減点しない）。

### パイプライン 1 周（Review）
`REVIEW_STEP_IDS` の順に実行する。番号は Support との**対応を示す呼称**であり、
実行順とは一致しない。
```
S1 ruleset   RuleSet 適用（検索スコープ・しきい値・重大リスク語）
 → ① segment  文書を検査単位へ分割（決定的・原文オフセット保持）
 → ② retrieve セグメントごとに規程を RAG 検索
 → ③ detect   二段判定で違反候補を検出
 → ④ ground   GroundednessVerifier で「指摘が規程で裏付けられるか」を検証
 → ④' suppress 誤検知抑止 + 救済
 → ⑥ web      法改正の裏取り（任意・信頼度を下げる方向にのみ使う）
 → ⑤ severity 重大度の確定（＋重大リスク語による強制 high）
 → ⑦ action   レポート → HITL CONFIRM → バックエンド実行
```
Review の新規実装は **Segment / Detect / Severity の 3 つだけ**で、
Retrieve・Ground・誤検知抑止・Action は Support と同じ機構の再利用である。
設計は `backend/docs/review_flow.md`。

> **⚠️ CLI 入口は Support / Review とも存在しない（2026-09-19 以降）。**
> 唯一の入口は Web API（`uvicorn backend.app.main:app` → `run_support_agent_core` /
> `run_review_agent_core`）である。かつて Support には CLI
> （`agent_support_example.py`）と S0〜S9 のステップ別トレース（`grace/step_trace/s*.py`）が
> あったが、いずれも機能確認用の薄いラッパだったため削除した（実装は git 履歴に残る）。
> 挙動確認は `./run_dev.sh` か `tests/`（`test_support_agent_core.py` /
> `test_review_agent_core.py`）で行う。

---

## 2. 開発コマンド

### 起動
```bash
# 前提: .env に ANTHROPIC_API_KEY / GOOGLE_API_KEY、Qdrant 起動済み
docker compose -f docker-compose/docker-compose.yml up -d

# 開発サーバ一括起動（backend :8000 + frontend :5173）
./run_dev.sh

# バックエンド単体
uvicorn backend.app.main:app --reload --port 8000
```

> ⚠️ **エージェント実行の CLI は無い。** `agent_support_example.py` と
> `grace/step_trace/s*.py` は 2026-09-19 に削除した（§1 の注記）。
> 挙動確認は `./run_dev.sh`（:5173）か `tests/` で行う。
> 下の「データ準備」の CLI は現役である。

### データ準備（3段階）
```bash
# 1. チャンク化
python -m chunking.csv_text_to_chunks_text_csv

# 2-3. Q/A 生成 + Qdrant 登録
python qa_qdrant/make_qa_register_qdrant.py
#   登録のみ: python qa_qdrant/register_to_qdrant.py
```

上の 3 工程（チャンク化 → Q/A 生成 → Qdrant 登録）とコレクション管理は、
**アプリの「データ管理」タブ**からも実行できる（`./run_dev.sh` → :5173）。
サブタブは ① チャンキング / ② Q/A 作成 / ③ Qdrant 登録 / ④ コレクション管理。
CLI と同じ関数（`QAPipeline` など）を呼ぶので挙動は同一。
設計は `backend/docs/data_pipeline.md` を参照。

> `--resume` つきの大規模バッチは引き続き CLI の方が適している。

### 検証（CI と同じゲート）

**初回のみ**、テスト用の依存を入れる（`[project] dependencies` の 221 行は**入れない**。
テストはスタブベースで実行時依存を必要としない）:

```bash
uv venv
uv pip install -r requirements-test.txt   # CI と共有する唯一の正本（18 パッケージ）
```

```bash
uv run ruff check . --no-cache             # lint
uv run --no-sync pytest tests -q -rs   # backend テスト
python -m compileall -q -x '\.venv|/\.git/|/logs/' .   # 構文ゲート
cd frontend && npm run lint && npm test && npm run build   # frontend
```

> ⚠️ **`--no-sync` を付ける。** 付けないと `uv run` が `pyproject.toml` の
> `[project] dependencies`（221 行・spacy/matplotlib 等を含む）で環境を同期し直し、
> `requirements-test.txt` で作った軽い環境が上書きされる。
>
> ⚠️ **`tests` が import するパッケージを足したら `requirements-test.txt` に追記する。**
> CI（`.github/workflows/ci.yml`）はこのファイルを読むので、YAML 側を直す必要は無い。
> 理由と過去の事故例（`openai` が `tqdm` を落として無関係な PR が落ちた）は同ファイルの冒頭に書いてある。

### 結合テスト（実 Qdrant / Redis）とクラウド VM

`tests/integration/` は**スタブを使わず** docker-compose の Qdrant / Redis に接続する
（API キーは不要。Embedding は固定ベクトル、LLM は固定応答で代用）。**未起動なら skip** するので
CI とは無関係。除外は `-m "not integration"`、強制 skip は `GRACE_SKIP_INTEGRATION=1`。

```bash
uv run --no-sync pytest tests/integration -q -rs
```

- **クラウド VM（Claude Code on the web）でも Docker は動く。** `.claude/hooks/session-start.sh`
  （SessionStart hook）がセッション開始時に テスト依存の導入 → `dockerd` 起動 → `docker compose up -d`
  を行う。結果は 1 行（`[grace session-start] ... qdrant:localhost:6333 redis:localhost:6379`）で出る。
  ローカル（Mac）では何もしない（`CLAUDE_CODE_REMOTE` が無いため）。
- VM の Qdrant は既定では**空**で、API キーも無い。実データ・実 LLM を使う E2E は次の節。
- 結合テストは共用 Qdrant を壊さないよう `grace_it_<乱数>` のコレクションだけを作って消し、
  Redis は **db 15** を使う（Mac の常駐ワーカーは db 0）。詳細は `backend/docs/testing.md` §1.1。
- ⚠️ **`dockerd` をバックグラウンドで起こすときは `setsid nohup` で切り離す。** ツール呼び出しの
  終了で子プロセスごと落ちる（2026-10-03 実測）。

### E2E（実 LLM・実 Embedding・実データ）

`tests/e2e/` は画面の例文（Support 3 業界・Review 3 例文）を**本物の API と実データ**で流す。
**課金される**ので `GRACE_E2E=1` のときだけ走る（CI は skip）。詳細は `backend/docs/testing.md` §1.2。

```bash
uv pip install -r requirements-e2e.txt          # 初回（fastembed / ddgs）
GRACE_E2E=1 uv run --no-sync pytest tests/e2e -m e2e -rs   # 結果は logs/e2e/*.json
GRACE_E2E=1 GRACE_E2E_REPEAT=3 uv run --no-sync pytest tests/e2e -m e2e -rs   # LLM の揺れを測る（合格率・出現率が summary に出る。課金 3 倍）
```

- **実データは Mac の Qdrant からスナップショットで運ぶ**: Mac で `python scripts/qdrant_snapshot.py export`
  → 非公開の保存先に置いて署名付き URL → クラウド環境の設定で `GRACE_E2E_SNAPSHOT_URL`・
  `ANTHROPIC_API_KEY`・`GOOGLE_API_KEY` を環境変数に入れる → 新しいセッションで hook が復元する。
  `restore` は既存コレクションを上書きせず、Embedding モデルが違うものは拒否する。
- ⚠️ **API が失敗してもパイプラインは安全側の結果を返して例外を出さない。** 素朴な期待値だと
  キーが無効でも合格する（実測: 6 件中 4 件）。E2E は事前の疎通確認と API エラーのログ監視で
  これを防いでいる。**E2E に期待値を足すときも `api_errors` の確認を外さないこと。**
- ⚠️ 既定のネットワーク設定では `huggingface.co`（sparse モデル）に届かず、VM では dense 検索だけになる。
- ⚠️ **`use_web=False`（Web フォールバック OFF）は「内部 RAG のみ」**。⑤ だけでなく executor の Web 検索
  （動的挿入・計画済みステップ・並列プリフェッチ・fallback・ReAct の 5 経路）も `Executor._web_search_allowed`
  で止める。2026-10-04 までは ⑤ しか止まらず、OFF でも無関係な URL が出典に並んだ。
  executor に Web 検索の経路を足すときは、必ずこの判定を通すこと（`test_web_search_toggle.py`）。

> `pyproject.toml` に `pythonpath` 指定は無い。CI は素の `pytest` を使うので
> `PYTHONPATH=.` を env で与えている（`uv run` 経由ならプロジェクトルートが通るので不要）。
> `python tests/x.py` を直接叩くと `ModuleNotFoundError: No module named 'backend'`
> になる → `uv run python -m tests.x` を使う。

---

## 3. プロバイダ方針（恒久ルール）

| 用途 | プロバイダ | 既定 | APIキー |
|---|---|---|---|
| **Embedding（検索）のみ** | **Gemini** | `gemini-embedding-001`（3072次元） | `GOOGLE_API_KEY` |
| **それ以外の全 LLM 用途**（Q&A生成・Plan/Execute/Reasoning/Confidence/Replan/ReAct 等） | **Anthropic** | `claude-sonnet-5-5`（軽量 `claude-haiku-5-5`） | `ANTHROPIC_API_KEY` |

- LLM クライアントは `helper.helper_llm.create_llm_client("anthropic")` /
  `grace.llm_compat.create_chat_client`。
- `config.GeminiConfig` は **Embedding 用途（`EMBEDDING_MODEL` / `EMBEDDING_DIMS`）に限って**参照可。
- **Embedding のモデル名・次元・入力上限・単価の定義は `config.py::ModelConfig` の
  `EMBEDDING_MODEL` / `EMBEDDING_DIMS` / `EMBEDDING_MAX_INPUT_TOKENS` / `EMBEDDING_PRICING` の 1 箇所だけ**
  （LLM のモデルと同じクラス）。`GeminiConfig` / `QdrantConfig` / `grace/config.py::EmbeddingConfig` /
  `helper/helper_embedding.py` などはそこを参照する。**他のファイル（`config/grace_config.yml` を含む）に
  モデル名を書かない**（`tests/test_embedding_model_single_source.py` が検査する）。
- ⚠️ **Embedding モデルを変えると既存 Qdrant コレクションは使えない。** 次元が同じでもベクトルの
  意味が合わず、**エラーにならずに検索結果だけが壊れる**。全コレクションを再登録し、RAG スコアの
  しきい値（`reasoning_min_rag_score` / `rag_sufficient_score`。後者は前者以下にする）も測り直すこと（`python scripts/measure_rag_threshold.py --vertical each` が LLM を呼ばずに範囲内・範囲外の質問のスコア分布と、今のしきい値での振る舞いを出す。grace_v2_local にも同じものがある）。2026-09-26 に一度 `gemini-embedding-2` へ
  変えたが、同日 `gemini-embedding-001` に戻した（既存コレクションと、同じ Qdrant を共用する
  grace_v2_local をそのまま使うため。しきい値 0.64 は 001 での実測値なので有効）。
- ⚠️ **`embed_content` に文字列のリストをそのまま渡さない。** `gemini-embedding-2` は
  リストを 1 入力として扱い、N 件送っても 1 本しか返さない（001 は件数どおり返すが、
  モデルを切り替えても壊れないよう常にこうする）。`helper_embedding.separate_contents()` で
  1 件 = 1 Content に包む。
- **Embedding 文脈の `provider="gemini"` / `GOOGLE_API_KEY` は正しい**ので変更しない。
- 本リポジトリは Gemini 由来コードから Anthropic へ移植した経緯があり、コードに残る
  Gemini 系の **LLM** 既定は「設計上の意図」ではなく **移植漏れ（負債）**とみなす。
  発見次第 Anthropic へ是正する。「現存コード＝意図」と推論しないこと。

### 3.1 ⚠️ モデル名の解決経路は 5 本ある

「既定モデルを変える」ときに 1 箇所だけ直すと**取り残しが出る**。
必ず 5 本とも確認すること。

| # | 経路 | 実体 | 誰が読むか |
|---|---|---|---|
| 1 | **設定ファイル（正）** | `config/grace_config.yml` の `llm.model` / `llm.light_model` | `grace/config.py::ConfigLoader` 経由で planner / reasoning / groundedness / ReAct |
| 2 | **モジュール定数** | `backend/app/core/verticals.py::INTENT_MODEL`（リテラル） | 判定系（意図分類・情報なし判定）。**yml を一切見ない** |
| 3 | **Python 定数** | `config.py::ModelConfig.DEFAULT_MODEL` | 上記以外（Q&A 生成の CLI・`QAPipeline`・`SmartQAGenerator`・`helper_rag_qa` の生成器の既定）。**ここでは文字列を直書きせず `ModelConfig.DEFAULT_MODEL` を参照する**（2026-10-08 まで旧既定 `claude-sonnet-5` が直書きで残り、画面と CLI で Q&A 生成のモデルが割れていた。`tests/test_qa_default_model.py` が検査）。**チャンキングは分けて `ModelConfig.CHUNKING_MODEL`（`claude-haiku-5-5`）** を参照する（`ChunkingRequest` / `ChunkingParams` / `chunks_all_async` / チャンク化 CLI の `--model` / `CHUNK_DEFAULT_MODEL` / `AsyncAPIClient`。`tests/test_chunking_default_model.py` が検査）。`DEFAULT_MODEL` を変えてもチャンキングは変わらない |
| 4 | **リクエスト単位の上書き** | UI のモデルセレクタ → `QueryRequest.model` / `ReviewRequest.model` → コアが `config.llm.model` を差し替え | その 1 リクエストの生成・推論・根拠検証・③ Detect |
| 5 | **直下 `config.yml`** | `config.yml` の `models.default`（`services/config_service.py` が読める） | **読むコードは無い**（唯一の読み手だった `services/agent_service.py`〔Legacy ReAct〕は 2026-10-10 に削除）。読んだ人が旧モデルを既定と誤解しないよう、値は経路 3 とそろえておく（`tests/test_model_selection.py` が一致を検査）。2026-09-24 まで `claude-sonnet-4-6` のまま残っていた |

**経路 4 は経路 1 を「そのリクエストだけ」上書きする**（`copy.deepcopy(get_config())` の
コピーに対して行うので、他のジョブへは漏れない）。選択肢は
`config.py::ModelConfig.SELECTABLE_MODELS`（= `get_selectable_models()`）の 1 箇所で決まり、
スキーマのバリデータ・`GET /api/models`・コアの再検証がすべてそこを読む。
**`light_model` は上書きしない**（判定系は軽量モデルのまま。理由は
`backend/docs/config_and_providers.md` §3.1）。

**経路 1 が正。** 経路 2 は `backend/app/core/gates.py::judge_model()` が
「config から解決できないときだけ `INTENT_MODEL` へフォールバックする」形に是正済みなので、
**`INTENT_MODEL` を直接使うコードを新たに書かない**こと（詳細は同関数の docstring）。
経路 1 と 2 は現在たまたま同じ値（`claude-haiku-5-5`。2026-10-08 までは `claude-haiku-4-5-20251001`）なので、
**取り残しはテストでは表面化しない**。

設定は yml → 環境変数（接頭辞 `GRACE_`）→ `GraceConfig`（pydantic）で検証、の 3 段。

> ⚠️ トップレベルの **`config.py`（モジュール）** と **`config/`（ディレクトリ）** は別物。
> `config/` に入っているのは `grace_config.yml` だけで、`import config` は `config.py` を指す。

### 3.2 実在するモデル名（勝手に「修正」しない）

`config.py::ModelConfig` が定義する 9 つはすべて実在し、**すべて正しい**。

| モデル名 | 用途 | UI の選択肢 |
|---|---|:--:|
| `claude-fable-5-1` | 最上位（難しい推論・長時間のエージェント処理） | ✅ |
| `claude-opus-5-5` | 上位（`claude-opus-5` の後継・単価も安い） | ✅ |
| `claude-sonnet-5-5` | **既定**（推論・生成）。**思考を無効化できない**（`ALWAYS_THINKING_MODELS`） | ✅ |
| `claude-haiku-5-5` | **軽量**（Claude Haiku 5.5）。`llm.light_model` / `INTENT_MODEL` / チャンキングの既定値（`ModelConfig.CHUNKING_MODEL`。2026-10-08〜） | ✅ |
| `claude-opus-5` | 旧上位（後方互換。`llm.heavy_model` 等の既存設定用） | ❌ |
| **`claude-haiku-4-5`** | 旧軽量（Haiku 4.5）。**日付なしエイリアス**。2026-10-08 までチャンキングの既定値 | ❌ |
| `claude-haiku-4-5-20251001` | 上記の日付指定。2026-10-08 まで `llm.light_model` / `INTENT_MODEL` の値 | ❌ |
| `claude-sonnet-5` | 旧既定（後方互換。既存設定の読み込み用） | ❌ |
| `claude-sonnet-4-6` | 旧々既定（後方互換。既存設定の読み込み用） | ❌ |

**`claude-haiku-4-5` を「日付が抜けている」と判断して書き換えないこと。**
意図的なエイリアスであり、`MODEL_PRICING` / `MODEL_LIMITS` にも 9 つとも登録されている。
これは R1（モデル名のマッピングを作らない）と同種の事故である。

> ⚠️ **「UI の選択肢 ❌」は「使えない」という意味ではない。** 下 5 つは有効な
> モデル名で、設定ファイルからは指定できる。**同じモデルが 2 行（日付あり／なし）
> 並ぶのを避けるため、また旧世代を選ばせないため、セレクタに出していないだけ**である
> （`ModelConfig.AVAILABLE_MODELS` ⊃ `SELECTABLE_MODELS`）。
>
> ⚠️ **モデル世代で API への送り方が違う。** `ModelConfig` の
> `NO_TEMPERATURE_MODELS`（temperature は 400）/ `ADAPTIVE_THINKING_MODELS`
> （`budget_tokens` は 400・`adaptive` を送る）/ `ALWAYS_THINKING_MODELS`
> （`{"type": "disabled"}` も 400）を `grace/llm_compat.py` と
> `helper/helper_llm.py` が読む。**選択肢にモデルを足すときはこの 3 表も確認する**
> （詳細は `backend/docs/config_and_providers.md` §3.1）。
>
> ⚠️ **Haiku 5.5 は Haiku 4.5 と送り方が違う**（2026-10-08 に軽量モデルを切り替えた）。
> `temperature` は 400・`budget_tokens` も 400 なので `NO_TEMPERATURE_MODELS` と
> `ADAPTIVE_THINKING_MODELS` に入れてある。thinking を省略すると思考が既定で ON になり
> `max_tokens` を食うため、`llm_compat.py` も `helper_llm.py` も `{"type": "disabled"}` を明示する
> （effort high 以下なら受け付けるので `ALWAYS_THINKING_MODELS` には入れない）。
> 同じ文章でトークン数が約 30% 増える。
>
> ⚠️ **Sonnet 5.5 は `stop_reason` も見る。** `grace/llm_compat.py` は `refusal` を
> `LLMRefusalError`、JSON 応答の `max_tokens` 打ち切りを 1 回再試行のうち
> `LLMTruncatedError` にする（以前は握りつぶされ、「本文が空の成功」や「途中で切れた JSON」に
> なっていた）。effort は現在すべて `low` 固定で、呼び出しごとの調整は**未実装・要評価**
> （`backend/docs/config_and_providers.md` §3.1 の補足）。

### 3.3 調査済み・触らなくてよい残置コード

- `config.py::GeminiConfig.DEFAULT_MODEL = "gemini-2.5-flash"` と `AVAILABLE_MODELS` —
  **参照ゼロ**（リポジトリ全体 grep 済み）。クラス docstring に「後方互換」と明記されている。
  §3 の「Gemini 系 LLM 既定は負債」に**該当しない**（死んでいるので実害が無い）。
  毎回調べ直さないよう、ここに結論を残す。
- 直下 `config.yml` の `gemini:` セクション（LLM 既定 `gemini-2.5-flash`・`available_models`・`thinking`）と
  `provider:` セクション（`default_llm: "gemini"`）— **読み手ゼロ**（2026-09-25 grep 実測）。`config.yml` を読むのは
  `services/config_service.py` だけで、コードが引くキーは `models.default` / `agent.*` / `cache.*` / `api.*` のみ
  （`model_pricing:` / `samples:` / `audio:` も同様に未参照）。上と同じ理由で**触らなくてよい**。
  経路 5（`models.default`）も 2026-10-10 以降は読み手が無いが、値は §3.1 の検査対象として残している。

---

## 4. CI と ブランチ運用

### 必須ゲートは 4 つ（すべて blocking）

| ジョブ | 内容 |
|---|---|
| `compile (syntax gate)` | `python -m compileall` |
| `ruff` | `ruff check .`（`ruff==0.12.11` 固定） |
| `pytest (backend)` | `pytest tests -q -rs`（実 API キー・Qdrant 不要） |
| `frontend (tsc + vitest + build)` | `npm run lint` → `npm test` → `npm run build` |

`auto-merge` は `needs: [build, lint, backend-tests, frontend]`。4 つ緑になれば
`claude/*` ブランチの PR を Ready 化して master へマージする（`hold` ラベルで抑止）。

> ⚠️ **frontend ゲートを忘れない。** Python 側が全部緑でも `frontend/src/types.ts` の
> 型エラー 1 個でマージは止まる。バックエンドの API スキーマを変えたら
> `frontend/src/types.ts` も必ず追随させる。

### ruff 設定の要点

`[tool.ruff.lint.isort] known-first-party` にトップレベルモジュールを列挙している。
**新規トップレベルモジュールを足したらここにも追記する**（現在は `scripts` /
`qdrant_delete_collection` / `tests` を含む全 19 個。`agent_support_example` は
2026-09-19、`agent_cache` / `agent_parallel_search` は 2026-10-10 の削除にあわせて外し、
`tests` は 2026-10-10 にテストを直下へ移したときに足した）。

> ⚠️ **この設定の効き目を過大評価しないこと（2026-09-13 実測）。**
> `known-first-party` を丸ごとコメントアウトして `ruff 0.12.11 check .` を回しても
> **All checks passed** だった。ruff の isort 分類は `src`（既定 `["."]`）を使った
> **ファイルシステム解決**が先に効くため、リポジトリ直下に実体があるモジュールは
> 設定が無くても first-party になる。site-packages の導入状況は見ていない。
>
> つまり「未設定だと I001 がローカル緑／CI 赤になる」という以前の記述は
> **本リポジトリでは再現しない**。この列挙は保険であって、I001 の原因ではない。
> **I001 が出たときに真っ先にこの設定を疑って時間を溶かさないこと。**
> まず `ruff check --no-cache` の実出力（どのファイルのどの import 順か）を読む。

> ⚠️ **ローカルの `ruff` が CI と同じ版とは限らない。**
> この環境の `ruff` は uv ツール管理で新しい版が入っていることがある
> （実測: `ruff --version` → 0.15.8）。CI ゲートを再現するなら版を固定して呼ぶ:
> ```bash
> uvx ruff@0.12.11 check . --no-cache
> ```

### ブランチ
- 開発は `claude/<topic>` ブランチ。**ドラフト PR** で作成（auto-merge が Ready 化する）。
- **指定ブランチの PR が既にマージ済みなら、そのブランチは使い回さない。**
  `git fetch origin master && git checkout -B <branch> origin/master` で作り直す。
- **リモート Git プロキシは ref 削除を 403 で拒否する。** `git push origin --delete` は
  この環境から実行できない → ブランチ削除は GitHub UI かユーザのローカルで行う。
  できない旨を正直に報告し、コマンドを提示すること。
- GitHub 操作は `mcp__github__*` MCP ツール（`gh` CLI はこの環境に無い）。
- **モデル識別子（`claude-opus-5` 等）をコミットメッセージ・PR 本文・コードコメントに
  書かない**（チャット返信のみ）。

---

## 5. 姉妹リポジトリ（grace_v2_local）との関係

### ⚠️ 双方向に乖離している。ファイル単位のコピーは壊れる

`grace_v2`（Anthropic 版）と `grace_v2_local`（Ollama 版）は同じ構造だが、
**両方向に片側だけの機能がある**。「local にある機能を持ってくる」つもりで
ファイルを丸ごとコピーすると、**こちらにしかない機能が消える**。

| 機能 | grace_v2 | grace_v2_local |
|---|:--:|:--:|
| `state/formMemory.ts`（タブ切替時の入力退避） | ✅ | ✅（2026-09-20 に移植） |
| `state/metaFetch.ts` / `state/timelineAnnounce.ts` | ✅ | ✅（2026-09-20 に移植） |
| `components/MetaErrorBanner.tsx` | ✅ | ✅（2026-09-20 に移植） |
| `state/documentLimit.ts`（文字数上限の判定・アナウンス文言） | ✅ | ✅（2026-09-20 に移植） |
| `state/modelLabel.ts` | ✅ | ✅（**中身は別物**） |
| `state/headerModel.ts`（モデル選択をヘッダーで行う。全タブ） | ✅（2026-09-23） | ✅（2026-09-23 に移植。**既定値の取り方が違う**） |
| `components/ModelSelect.tsx` | ❌（2026-09-23 に削除） | ❌（同日に削除） |
| `state/focusTrap.ts` / `state/selectionKeys.ts`（a11y） | ✅（2026-09-24 に移植） | ✅ |
| `state/streamWatch.ts`（SSE の張り直し）と `jobs.py::SSE_KEEPALIVE` | ✅（2026-10-08 に移植） | ✅ |
| LLM プロバイダ | Anthropic | Ollama（ローカル） |

> この表は、**ファイル単位で見た両リポジトリの差分**である。
> 実測日: 2026-09-24（`frontend/src/` のファイル一覧を両リポジトリで突き合わせ、**ファイル集合は一致**した）。
> **ファイル名が同じでも中身が同じとは限らない。** とくに次の 2 つは別物なので、
> **コピーで持ち込まない**こと。
> - `modelLabel.ts` — こちらは Anthropic の単価つきラベル、local は Ollama の
>   `supports_tool_calls` / `notes` を畳み込むラベル
> - `headerModel.ts` — データ管理タブの既定値が、こちらは `ModelInfo.chunking_model` /
>   `qa_model`、local は `ModelInfo.model`（local の `ModelInfo` にはこの 2 項目が無い）
>
> 片側にしかないフロント資産を足したら、**この表にも 1 行足す**こと。

### 共用している Qdrant と規程の雛形（2026-10-01）

両リポジトリは**同じ Qdrant** を使う（Embedding も同じ Gemini 3072 次元）。とくに規程コレクション
`ec_ad_rules_anthropic` は 1 個を両方の GRACE-Review が読む。
**その元データ `qa_output/ec_ad_rules_statutes_template.csv` はこちらにだけ置き、local へコピーしない**
（2 か所にあると片方だけに条文を足す食い違いが起き、登録するともう片方の Review も黙って変わる）。
local から登録し直すときも `--input-file ../grace_v2/qa_output/ec_ad_rules_statutes_template.csv` を指す。
理由と手順は [`docs/review_rag_rules_todo.md`](docs/review_rag_rules_todo.md) §1.1。

**実例（2026-08-25）**: 基本版タブの複数行入力を local から移植する際、
`QueryForm.tsx` を丸ごとコピーしていれば `formMemory`（外した dry-run が
タブ切替で ON へ復帰する不具合の修正・v1.1）が消えていた。
`ModelSelect` を持ち込めばビルドも壊れていた。

### 移植するときの手順

1. **必ず `diff -u` を取る。** どちらの方向に何が違うかを目で見る。
   ```bash
   diff -u grace_v2/frontend/src/components/X.tsx grace_v2_local/frontend/src/components/X.tsx
   ```
2. **目的の機能に関係する差分だけを足す。** ファイルを置き換えない。
3. 移植先にしかないモジュールの参照（import・呼び出し）が消えていないか grep で確認する。
4. 既存機能のテスト（例: `formMemory.test.ts`）が通ることで温存を担保する。

### ドキュメントは実装に遅れていることがある

`frontend/docs/*.md` や `<package>/docs/*.md` を移植元として参照する前に、
**そのドキュメントが実装に追随しているか確認する**。

**実例**: `grace_v2_local/frontend/docs/QueryForm.md` は Version 1.0 のまま、
複数行入力とモデルセレクタの **2 機能分**遅れていた（`useState` の個数も
「× 8」と書かれていたが実際は 9 個）。コピー元にできず、書き直しになった。

---

## 6. フロントエンドの純関数規約

### 判断ロジックは `frontend/src/state/` の純関数へ出す

`frontend/vite.config.ts` の vitest 設定は次のとおり:

```ts
test: {
  environment: 'node',
  include: ['src/**/*.test.ts'],   // ← .test.tsx は収集されない
}
```

`@testing-library/react` は未導入で、**コンポーネントのレンダリングテストは書けない**。
そのため「どう判断するか」をコンポーネント内に残すとテストできなくなる。

**判断を含むロジックは必ず `state/` 配下の純関数へ切り出す。**
React の型（`KeyboardEvent` 等）に直接依存させず、必要なフィールドだけを受ける
インターフェースを定義すると、node 環境のテストから素のオブジェクトを渡せる。

| モジュール | 切り出した判断 |
|---|---|
| `state/queryParams.ts` | 送信ペイロードの組み立て・基本版での vertical 固定・識別子の有無 |
| `state/submitKey.ts` | textarea の送信キー（Ctrl+Enter / ⌘+Enter・**IME 変換中は送信しない**） |
| `state/dataParams.ts` | データ準備フォームの入力 → API パラメータ組み立て（空欄・トリム・null 化・未選択モデルのキー省略） |
| `state/tabKeys.ts` | タブの矢印キー移動 |
| `state/formMemory.ts` | タブ切替時の入力退避と復元（モデルはヘッダー側が持つので含まない） |
| `state/headerModel.ts` | ヘッダーのモデルセレクタ（全タブ。データ管理タブは工程ごとに 2 つ）の並べ方・表示値・選択肢 |
| `state/interventionKind.ts` | 承認待ちが action（⑥ 実行承認）か question（0-(A) 主質問の選択）か |
| `state/documentLimit.ts` | 文字数上限の判定・表示文言・**アナウンス文言**（超過中は長さを含めず再読み上げを防ぐ） |
| `state/metaFetch.ts` | メタ取得失敗を対処可能な文言へ（silent failure を出さない） |
| `state/modelLabel.ts` | ヘッダーの見出し文字列・単価つき選択肢のラベル |
| `state/timelineAnnounce.ts` | 支援技術へ読み上げる 1 行の決定 |
| `state/focusTrap.ts` | `ConfirmModal` 内の Tab 移動先（端で巻き戻す。**Escape では閉じない**） |
| `state/selectionKeys.ts` | 指摘の選択キー（Enter / Space・IME 変換中は発火しない）と選択トグル |
| `state/staleResult.ts` | GRACE-Review の結果が入力欄の文書のものか（例文ボタンで差し替えて未実行なら「古い」と表示） |
| `state/streamWatch.ts` | SSE が黙って止まったか（60 秒無音）・張り直し時のリプレイ分の読み飛ばし（`seq`）。`api/client.ts::subscribeStream` が使う。⚠️ backend の keepalive は名前付きイベント（`jobs.py::SSE_KEEPALIVE`）でなければ見えない（2026-10-08 に grace_v2_local から移植） |
| `state/citations.ts` / `highlight.ts` / `elapsed.ts` / `activeJobs.ts` | 表示用の派生値 |
| `state/jobReducer.ts` / `dataReducer.ts` / `reviewReducer.ts` | ジョブ状態の遷移 |

> `state/useJobTiming.ts` は**例外的にフック**（`useState` / `useEffect` を持つ）。
> ただし判断は持たず、`Date.now()` の取得と phase の決着検知だけを行い、
> **整形・比較は `elapsed.ts` の純関数**が受け持つ（テストは `elapsed.test.ts` /
> `serverTiming.test.ts` 側にある）。ここに分岐を足さないこと。

コンポーネント側に残すのは**入力の保持と描画だけ**にする。

### コンポーネントを触ったら docs も更新する

`frontend/docs/<Component>.md` は `.claude/skills/grace-agent-docs/a_react_page_md_format.md`
の形式に従う。**Props の TypeScript コードブロックは実装の逐語コピー**なので、
prop を 1 つ足すときは他の prop が欠けていないかも確認する
（一部だけ更新すると「一見完成しているが実は誤り」になる）。

**テスト件数は実行して実測値を書く。** 記憶で書かない。

---

## 7. Mermaidダイアグラム スタイル規約

### 7.1 構文バージョン
**PyCharm Pro v9 互換構文**を使用する。

- ノードラベルにバッククォートや markdown文字列（`` `text` ``）を使用しない
- 特殊文字を含むノードラベルは必ずダブルクォート（`"..."`）で囲む
- TS の総称型（`Record<StepId, StepState>` 等）は `<` `>` がタグ解釈されうるため、
  ダブルクォートで囲んだうえで可能なら `Record[StepId, StepState]` へ置換する

### 7.2 カラーテーマ（黒背景・白文字）— **必須**

| 要素 | 設定値 |
|---|---|
| ノード背景色 | `fill:#000` |
| ノードテキスト色 | `color:#fff` |
| ノード枠線色 | `stroke:#fff` |
| サブグラフ背景色 | `fill:#1a1a1a` |
| サブグラフテキスト色 | `color:#fff` |
| サブグラフ枠線色 | `stroke:#fff` |

### 7.3 flowchart / graph の実装パターン
```
flowchart TB
    subgraph Layer["レイヤー名"]
        NodeA["ノードA"]
        NodeB["ノードB"]
    end
    NodeA --> NodeB
classDef default fill:#000,stroke:#fff,color:#fff
classDef subgraphStyle fill:#1a1a1a,stroke:#fff,color:#fff
class NodeA,NodeB default
style Layer fill:#1a1a1a,stroke:#fff,color:#fff
```

**必須ルール:**
1. `classDef default fill:#000,stroke:#fff,color:#fff` を必ずブロック末尾に追加する
2. `classDef subgraphStyle fill:#1a1a1a,stroke:#fff,color:#fff` を追加する
3. 全ノードに `class <node_ids> default` を付与する
4. 全サブグラフに `style <subgraph_name> fill:#1a1a1a,stroke:#fff,color:#fff` を付与する
5. 既存の `style`/`classDef`/`class` 行は重複しないよう整理する

### 7.4 sequenceDiagram の実装パターン
```
%%{ init: { "theme": "base", "themeVariables": {
  "background": "#000000", "mainBkg": "#000000",
  "textColor": "#ffffff", "lineColor": "#ffffff",
  "actorBkg": "#000000", "actorTextColor": "#ffffff",
  "actorLineColor": "#ffffff", "noteBkgColor": "#000000",
  "noteTextColor": "#ffffff", "noteBorderColor": "#ffffff" } } }%%
sequenceDiagram
    participant A as "参加者A"
    A->>B: メッセージ
```

**必須ルール:**
- `sequenceDiagram` の前に必ず `%%{ init: ... }%%` ヘッダーを挿入する
- `classDef` / `class` 行は `sequenceDiagram` では使用しない（非対応）
- ⚠️ **Note 背景の変数名は `noteBkgColor`（`noteBkg` ではない）。**
  `noteBkg` は Mermaid に認識されず既定の黄色（`#fff5ad`）になる

### 7.5 stateDiagram-v2
`classDef` / `class` に非対応 → **スタイル指定を付けない。**

### 7.6 検証（grep）
各ファイルで `flowchart|graph` の数 == `classDef default fill:#000` の数、
`sequenceDiagram` の数 == `%%{ init` の数。

---

## 8. コーディング規約

### 8.1 型ヒント
```python
# ❌ 誤り
def func(callback: Optional[callable] = None): ...

# ✅ 正しい
from typing import Optional, Callable
def func(callback: Optional[Callable] = None): ...
```

### 8.2 出力ファイル命名（チャンク分割）
```bash
# ✅ 出力は常に固定ファイル名（後続バッチとの連携のため）
cc_news_1per.csv  →  output_chunked/cc_news_1per_chunks.csv
                     output_chunked/cc_news_1per_chunks_simple.csv   # Text 列のみの簡易版

python -m chunking.csv_text_to_chunks_text_csv \
  --input-file OUTPUT/cc_news_1per.csv \
  --output output_chunked
```

> ⚠️ **`--timestamp` オプションは存在しない**（2026-09-25 に CLI の引数定義と git 履歴で確認。
> 以前ここに「付けると日時サフィックスが付く」と書かれていたが、実装されたことは一度も無い）。
> 同じ入力で再実行すると**上書き**される。残したいときは `--output` で出力先を分ける。

---

## 9. ドキュメント規約

### 9.1 所在は `docs`（複数形）に統一

| 領域 | 所在 |
|---|---|
| Python モジュール（IPO） | `<package>/docs/<module>.md` — `chunking/docs/`, `qa_generation/docs/`, `qa_qdrant/docs/`, `services/docs/`, `grace/docs/` |
| backend | `backend/docs/` |
| React コンポーネント | `frontend/docs/<Component>.md` |
| 横断/設計メモ | リポジトリ直下 `docs/` |

**単数形 `doc/` は使わない。** 新規ディレクトリも必ず `docs/` で切る。

> 📁 **Python のディレクトリ（`chunking/` / `grace/` / `qa_qdrant/` / `services/` / `helper/` 等）は、`<dir>/docs/` に
> `README_<dir>.md`（概要＋モジュール索引＋使い方）・`<module>.md`（`.py` と 1 対 1。`__init__.py` は除く）・
> 必要なときだけ `<dir>_process_flow.md` / `<dir>_data_flow.md` を置き、ほかの文書はこれらへ統合する**
> （2026-10-10 に規則化。`a_cross_doc_md_format.md` §1.1〜§1.4）。**`backend/` は `backend/app/docs/`・`backend/app/api/docs/`・
> `backend/app/core/docs/` に分け**、`backend/docs/` には backend 全体にまたがる文書と索引だけを残す（同 §1.1.2）。
> リポジトリ直下の `*.py`（直下 `docs/`）・`frontend/`・`config/`・テスト（直下 `tests/`。2026-10-10 に `backend/tests/` から移した）は対象外。
> **既存文書の移行は `grace/` だけ済んでいる**（2026-10-10。`grace/docs/README_grace.md` / `grace_process_flow.md` / `grace_data_flow.md`）。
> ほかのディレクトリはまだで、`check_docs.py --layout` が要対応の一覧を出す。移行が済むまでは下の索引 `README.md` も有効。

**各領域の棚卸し README を先に読む。** どこに何があるか・何が欠落しているかは索引が持つ。
**全 8 領域に索引がある**（2026-09-25 時点）: [`docs/README.md`](docs/README.md)（直下・配置の境界と重複禁止ルール）/
`backend/docs/README.md` / `grace/docs/README_grace.md` / `frontend/docs/README.md` /
`chunking/docs/README.md` / `qa_generation/docs/README.md` / `qa_qdrant/docs/README.md` / `services/docs/README.md`。
**文書を足したら該当する索引にも行を足すこと。**

### 9.2 フォーマット仕様（書く前に該当仕様を実際に読むこと）

| 対象 | 仕様書（`.claude/skills/` 配下） |
|---|---|
| Python モジュール | `grace-agent-docs/a_class_method_md_format.md`（IPO 形式） |
| React コンポーネント | `grace-agent-docs/a_react_page_md_format.md` |
| 横断文書・調査メモ・手順書・TODO・索引（直下 `docs/`、および各領域の `docs/` にある IPO 以外の文書） | `grace-agent-docs/a_cross_doc_md_format.md` |
| 単体テスト | `grace-agent-tests/a_test_md_format.md`（SAE 形式） |

> 📐 **基本フォーマットは `a_class_method_md_format.md`。** React / 横断文書の各仕様はその派生で、
> 同書 §1.4 の**共通骨格**（概要の「主な責務」→「各責務対応のモジュール」〔行数 1:1〕、
> **3 層のアーキテクチャ構成図**、変更履歴と一致する Version ヘッダー、Mermaid 黒背景）を必ず持つ。
> 変更履歴は全仕様共通で `バージョン | 日付 | 変更内容` の 3 列・昇順（全文書を 2026-10-10 に一括移行済み。検証スクリプトが 2 列・降順を NG にする）。
> 種別 B（調査メモ・手順書）は「主な責務」の代わりに「結論」「対象モジュール」を持つ。
> 書いたら `a_cross_doc_md_format.md` §10 の検証スクリプトを流す。
>
> 🧪 **使用例**: クラスと主要な関数には使用例を必ず付け、**処理パターン（ブロッキング / ジェネレータ / コールバック / 本番の入口と同じ組み立て方 など）が
> 複数あれば主要なパターンごとに 1 本ずつ**書く。例は動かして確かめる（必要ならスタブで）。見本は `grace/docs/executor.md` §4.1
> （`a_class_method_md_format.md` §6.1・§9.4・§9.5）。

> Streamlit 用の `a_pages_md_format.md` は 2026-10-10 に削除した（**本リポジトリに Streamlit は存在しない**）。

### 9.3 技術スタック表記の統一

| 用途 | ✅ 正しい表記 | ❌ 禁止表記 |
|---|---|---|
| LLM全般 | `Anthropic Claude` | `OpenAI GPT`, `Gemini`（LLM 用途） |
| デフォルトモデル | `claude-sonnet-5-5`（最上位 `claude-fable-5-1` / 上位 `claude-opus-5-5` / 軽量 `claude-haiku-5-5`。旧軽量 `claude-haiku-4-5`・日付指定 `claude-haiku-4-5-20251001` は後方互換） | `gpt-4o-mini`, `gemini-2.5-flash` |
| Embedding | `Gemini` `gemini-embedding-001`（3072次元。定義は `config.py::ModelConfig.EMBEDDING_MODEL`） | `text-embedding-3-*`（本番 Embedding 用途）、`gemini-3.1-flash-lite` 等の生成モデル（`embedContent` 非対応） |
| LLMクライアント | `create_llm_client("anthropic")` | `"openai"` / `"gemini"`（LLM 用途） |
| LLM用APIキー | `ANTHROPIC_API_KEY` | `OPENAI_API_KEY` |
| エージェント名 | `GRACE-Support` / `GRACE-Review` | `GRACE` 単独で Support だけを指すこと |
| フロントエンド | `Vite + React 18 + TypeScript` | `Streamlit`, `Next.js` |

> 軽量の既定は `claude-haiku-5-5`（Claude Haiku 5.5・2026-10-08〜）。旧軽量の
> `claude-haiku-4-5`（日付なし）は**実在するエイリアス**なので、日付付きへ「統一」しないこと（§3.2）。
> 履歴・変更履歴では当時の値（`claude-haiku-4-5` / `claude-haiku-4-5-20251001`）として残す。
>
> `claude-sonnet-4-6` は**旧既定**。履歴・変更履歴の記述では当時の値として残す
> （現在の既定を述べる箇所だけ `claude-sonnet-5-5` にする）。

### 9.4 参照してはいけない廃止ファイル
grace_v2 に**存在しない**: `setup.py` / `server.py` / a-prefixed scripts
（`a30_qdrant_registration.py` 等）/ `agent_rag.py` / `ui/` /
**`backend/tests/`**（2026-10-10 に直下 `tests/` へ移した）/ `test_celery_integration.py` /
**`agent_support_example.py`** / **`grace/step_trace/`**
（`agent_support_example.py` と `grace/step_trace/s0_arg.py`〜`s9_render.py` は 2026-09-19 に削除。§1・§2 の注記を参照。
残っていた `benchmark.py` を含む `grace/step_trace/` 全体は 2026-10-10 に削除）。
**`services/agent_service.py`**（`ReActAgent`）/ **`agent_parallel_search.py`** / **`agent_cache.py`** も存在しない
（Legacy ReAct 経路。2026-10-10 に削除。経緯は `services/docs/README.md` §4）。

> ⚠️ **`start_celery.sh` は存在する**（2026-09-12 訂正）。以前この一覧に
> 入っていたが、Q/A 生成の Celery 並列（CLI の `--use-celery` / データ管理タブの
> 「② Q/A 作成」）を使うときのワーカー起動口として追加した。手順は
> `qa_qdrant/docs/celery_quick_start.md`。
>
> ⚠️ **Celery のキュー名に `qa_generation` は無い。** `celery_config.py` が定義
> するのは `celery`（既定）/ `high_priority` / `normal_priority` / `low_priority`
> の 4 つで、`qa_generation` は `Celery('qa_generation')` の**アプリ名**である。
> `-Q qa_generation` で起動したワーカーは何も消費しない。`-A` に渡すのは
> `celery_config`。

---

# ⚠️ CRITICAL RULES - MUST READ BEFORE ANY MODIFICATION ⚠️

## R1. モデル名のマッピングを絶対に作らない

**以下はすべて実在する有効なモデル名:**
- `claude-fable-5-1`, `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`, `claude-sonnet-5`, `claude-opus-5`, `claude-haiku-4-5`, `claude-haiku-4-5-20251001`, `claude-sonnet-4-6`
- `gpt-5-nano`, `gpt-5-mini`, `gpt-5` ← 実在する GPT-5 系
- `gpt-4.1`, `gpt-4.1-mini` ← 実在する GPT-4.1 系
- `o3`, `o3-mini`, `o4`, `o4-mini` ← 実在する O 系

**❌ こういうマッピングを作ってはならない:**
```python
MODEL_MAPPING = {"gpt-5-nano": "gpt-4o-mini"}  # ← WRONG! DO NOT DO THIS
```

モデル名は定義済みのものをそのまま使う。

## R2. OpenAI API のメソッドは 2 つとも正しい

```python
# Structured Outputs API（Q/A 生成向け・型安全）
response = client.responses.parse(
    input=combined_input, model=model,
    text_format=QAPairsResponse, max_output_tokens=1000,
)

# Responses API（標準のテキスト生成）
response = client.responses.create(
    input=input_messages, model=model, max_output_tokens=1000,
)
```

**⚠️ `.parse()` と `.create()` は両方 CORRECT。用途に応じて使い分ける。**
片方をもう片方へ「修正」しない。

## R3. よくある間違い

| ❌ 誤り | ✅ 事実 |
|---|---|
| 「`gpt-5-nano` はエラーになるから存在しないモデルだ」 | 実在する。**本当のエラー原因**を調べること |
| 「`responses.parse()` は存在しないから `create()` に直そう」 | 両方存在する |
| 「旧モデル名を新モデル名に翻訳するマッピングを作ってあげよう」 | モデル名は既に正しい。マッピングを作らない |

## R4. エラーが出たときの手順

「model not found」「API error」を見たら:

1. ❌ モデル名が間違っているせいでは**ない**
2. ❌ API メソッド名が間違っているせいでは**ない**
3. ✅ 確認する: API キー、ネットワーク、Qdrant 起動状態、Celery/Redis 接続
4. ✅ 確認する: 実際のエラーメッセージとスタックトレース
5. ✅ **モデル名や API メソッド名を「直す」ことを最初の対応にしない**

## R5. コミット前チェックリスト

- [ ] MODEL_MAPPING を作っていないか？（作っていたら → 削除）
- [ ] `responses.parse()` を `responses.create()` に変えていないか？（変えていたら → 戻す）
- [ ] 4 つの CI ゲート（ruff / pytest backend / compileall / frontend）をローカルで通したか？
- [ ] API スキーマを変えたなら `frontend/src/types.ts` を追随させたか？
- [ ] **grace_v2_local から移植したなら**、こちらにしかない機能（`formMemory` 等）を
      消していないか？（§5・ファイルを丸ごとコピーしていないか）
- [ ] フロントの判断ロジックをコンポーネント内に書いていないか？
      （§6・`state/` の純関数へ出さないとテストできない）
- [ ] コンポーネントを変えたなら `frontend/docs/<Component>.md` を追随させたか？
- [ ] ドキュメントに書いたテスト件数は**実行して数えた値**か？（記憶で書かない）
- [ ] **Review 側**（`review_agent.py` / `review_gates.py` / `rulesets.py` /
      `ReviewPanel` 系）を壊していないか？ 共用部品（`GroundednessVerifier` /
      `InterventionBridge` / `support_actions.py`）を触ったなら
      `tests/test_review_*.py`（18 本）も通したか？（§1）
- [ ] モデル既定を変えたなら**5 本の解決経路すべて**を確認したか？（§3.1）
      新しい既定を `SELECTABLE_MODELS` と `MODEL_PRICING` / `MODEL_LIMITS` へ入れたか？
- [ ] 確信が持てない → **ユーザーに聞く**
