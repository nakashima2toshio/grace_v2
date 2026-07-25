# 複数質問クエリへの対応 — 改善設計提案書

**Version 1.0** | 最終更新: 2026-07-25 | ステータス: **提案（未実装）**

> 📌 本書は**設計提案**であり、記載の改修はまだ実装されていない。実装着手時は §8 の
> 段階導入プランに従い、フェーズごとに受け入れ基準（§9）を満たすこと。

---

## 目次

1. [概要](#概要)
2. [問題の所在（コード事実）](#1-問題の所在コード事実)
3. [改善方針（3案と推奨）](#2-改善方針3案と推奨)
4. [改善モジュール・改善内容 一覧](#3-改善モジュール改善内容-一覧)
5. [処理フロー Before / After](#4-処理フロー-before--after)
6. [データフロー（分解検索）](#5-データフロー分解検索)
7. [リスク・留意点](#6-リスク留意点)
8. [設定項目案](#7-設定項目案)
9. [段階導入プラン](#8-段階導入プラン)
10. [受け入れ基準](#9-受け入れ基準)
11. [関連ドキュメント](#10-関連ドキュメント)
12. [変更履歴](#11-変更履歴)

---

## 概要

GRACE-Support に**複数の質問を1つの入力に含むクエリ**が来たときの、検索・回答・判定の
改善方針をまとめる。

**対象例（自治体 vertical）**:

```
住民票の写しの取り方は？ また、他の市町村に住民票を移動する方法は？
```

- **Q1**: 住民票の写しの**交付申請**（窓口・郵送・コンビニ交付／手数料）
- **Q2**: 他市町村への**転出・転入届**（転出証明書／期限／窓口）

この2問は**別手続き・別担当課・別出典**であり、1つの検索・1つの回答で両立させるのが難しい。

### 結論（先に要点）

検索精度の劣化よりも、**部分回答が「高信頼」として通過してしまう評価の穴**のほうが本質的に
危険である。Q1 だけ答えた回答は、述べた主張がすべて出典に支持されるため **groundedness の
支持率はむしろ高くなり**、`_answer_gate` を `answer` で通過する。結果として **Q2 が無言で
落ちたまま、ユーザーには高信頼の回答として提示される**。

そのため本提案は、**P0（カバレッジによる安全弁）を最優先**とし、その後に検索品質（P1）・
UX（P2）を積み上げる構成をとる。

---

## 1. 問題の所在（コード事実）

現行実装を追った結果、以下の7点が複数質問クエリで問題になる。

| # | 箇所 | 現状 | 複数質問での問題 |
|---|---|---|---|
| 1 | `grace/planner.py:108` | **「質問を分解して複数の検索ステップを作らないでください」** と明示的に禁止。計画は `rag_search → reasoning` 固定、`query` は**原文完全コピー**必須（`planner.py:109-110`「要約、キーワード化、分割は一切禁止」） | 2問が1つの検索ステップに潰れる。設計上、分解の逃げ道がない |
| 2 | `agent_tools.py:330` | クエリ全文を `embed_query(query)` で**単一の Dense ベクトル**に変換 | 2トピックの**意味の重心**がボケ、どちらのトピックにも中途半端にしか当たらない |
| 3 | `config.py:486` | `RAG_SEARCH_LIMIT: int = 3` | 上位3件を**片方のトピックが占有**しやすく、もう一方の根拠が0件になり得る |
| 4 | `grace/executor.py`（reasoning ステップ） | 収集済み観測から**回答を1本**生成 | 出典が偏れば、LLM は根拠のある Q1 だけ答えて Q2 を黙って落とす |
| 5 | `backend/app/core/gates.py:208` | `_answer_gate(support_rate, verified, citation_count, notify_th, confirm_th)` — **coverage を引数に取らない** | ⚠ **最大の危険**。部分回答は support_rate が高くなり `answer` で確定。**未回答が検知されない** |
| 6 | `backend/app/core/verticals.py:21` | `Intent = Literal["question", "request", "incident"]` を**クエリ全体に1つ**割当 | Q1=question / Q2=request のような**意図の混在**を表現できず、強制エスカレ・アクション判定を取りこぼす |
| 7 | `grace/confidence.py:659`（`QueryCoverageCalculator`） | 網羅度を測る仕組みは**存在する**が、`coverage_weight = 0.15`（`grace/config.py:103`）で grace 側の `overall_confidence` にしか効かず、**backend の回答ゲートは未使用** | 「質問のすべての要素をカバーしたか」を測る資産があるのに、**回答/エスカレ判定に反映されていない** |

### 1.1 なぜ support_rate では検知できないか

`GroundednessVerifier` の支持率は次式で、**言及しなかった内容は分母に入らない**。

```
support_rate = supported / (supported + contradicted)     # neutral は分母外
```

Q1 のみを正確に答えた回答は「述べた主張がすべて supported」となり **support_rate ≒ 1.0**。
つまり **「答えなかったこと」は原理的に減点されない**。カバレッジは support_rate とは
**別軸で測る必要がある**（これが §3 の #4・#14 の根拠）。

---

## 2. 改善方針（3案と推奨）

| 案 | 内容 | 長所 | 短所 |
|---|---|---|---|
| **A. 検知＋カバレッジゲート**（安全弁） | 複数質問を検知し、**未回答があれば warning / escalate** に倒す | 実装が小さく即効。**誤答を防ぐ**。既存フロー不変 | 回答品質そのものは向上しない |
| **B. クエリ分解＋サブ検索**（本命） | サブクエリに分解し**各々で検索**（fan-out）、根拠を統合して1回答 | 両方の質問に根拠が付く。既存の並列基盤を再利用可 | LLM 1回追加＋検索 N 倍のコスト。分解ミスのリスク |
| **C. 構造化回答**（UX） | サブ質問ごとに節立てして回答＋出典を対応付け | 表示が明確。**片方だけエスカレ**が可能になる | スキーマ・フロント双方の変更が必要 |

### 推奨: **A → B → C の段階導入**

まず **A** で「黙って落とす」事故を止め、次に **B** で品質を上げ、最後に **C** で見せ方を整える。

> 💡 **追い風**: `agent_parallel_search.py` の `ParallelSearchEngine` が**そのまま使える**。
> サブクエリ × コレクションの fan-out を、既存の `ThreadPoolExecutor` 並列基盤で捌ける
> （詳細は `docs/agent_parallel_search.md`）。

---

## 3. 改善モジュール・改善内容 一覧

### 3.1 P0: 安全弁（案A）— 誤答を止める

| # | モジュール | 種別 | 改善内容 |
|---|---|:--:|---|
| 1 | `backend/app/core/gates.py` | 新規関数 | `_detect_multi_question(query)`: 「また/さらに/加えて/併せて」「？」複数、箇条書き等の**定型句判定＋軽量LLM**の二段判定（既存 `_detect_no_info_answer` と同じ設計に揃える） |
| 2 | `backend/app/core/gates.py` | 新規関数 | `_coverage_gate(coverage, decision, warning, th)`: **未回答サブ質問があれば** `answer → answer(warning)`、さらに低ければ `escalate` へ降格 |
| 3 | `backend/app/core/gates.py` | 改修 | coverage の合流。**`_answer_gate` の純関数シグネチャは温存**し、合成は呼び出し側またはラッパ関数で行う（既存テスト・ドキュメントとの整合を保つ） |
| 4 | `backend/app/core/support_agent.py` | 改修 | ③〜④の間に **`④'' サブ質問カバレッジ判定`** を追加。既存の `QueryCoverageCalculator` を backend でも利用。`step="coverage"` の SSE イベントを発行 |
| 5 | `backend/app/schemas.py` | 改修 | `SupportResult` に `sub_questions: List[str]` / `coverage: float` / `unanswered: List[str]` を追加（**すべて optional**） |
| 6 | `grace/config.py` | 改修 | `multi_question_enabled` / `coverage_gate_threshold`（例 0.7）/ `max_sub_questions`（例 4）を追加 |
| 7 | `backend/tests/` | 新規 | 例示クエリで「Q2 未回答なら `answer` にならない」回帰テスト＋**単一質問の挙動不変**テスト |

### 3.2 P1: 分解検索（案B）— 品質を上げる

| # | モジュール | 種別 | 改善内容 |
|---|---|:--:|---|
| 8 | `grace/planner.py` | **改修（要注意）** | `PLAN_GENERATION_PROMPT` の「分解禁止」を**条件付き緩和**。単一意図は現状維持（原文コピー）、**複数意図のときのみ**サブクエリを許可 |
| 9 | `grace/schemas.py` | 改修 | `Plan` / `PlanStep` に `sub_queries: List[str]` / `sub_query_id` を追加 |
| 10 | `grace/tools.py`・`agent_tools.py` | 改修 | `rag_search` を**サブクエリ × コレクションで fan-out**。`agent_parallel_search.ParallelSearchEngine` を再利用 |
| 11 | `config.py` | 改修 | `RAG_SEARCH_LIMIT`(=3) を**サブクエリ単位の予算**へ（例: `per_sub_query_limit=3`、全体上限 `8`）。**片方の枠占有を防ぐ核心** |
| 12 | `agent_tools.py` | 改修 | 統合時に**サブクエリごとの最低保証枠**（round-robin マージ）を導入。単純な score 降順だと再び片寄る |
| 13 | `grace/executor.py` | 改修 | reasoning プロンプトに「**各サブ質問に漏れなく答える**」制約を追加し、サブクエリ別に整理した観測を注入 |
| 14 | `grace/confidence.py` | 改修 | `GroundednessVerifier` の支持率を**サブ質問単位でも算出**（§1.1 の穴を塞ぐ） |

### 3.3 P2: 構造化回答・粒度制御（案C）

| # | モジュール | 種別 | 改善内容 |
|---|---|:--:|---|
| 15 | `backend/app/schemas.py` | 改修 | `SubAnswer{question, answer, citations, decision}` を導入し `SupportResult.sub_answers` に格納 |
| 16 | `backend/app/core/gates.py` | 改修 | `_should_force_escalate` / `_decide_action` を**サブ質問ごとに評価**（Q1 は自動回答・Q2 のみ有人、を可能に） |
| 17 | `backend/app/core/verticals.py` | 改修 | `Intent` 判定をサブ質問単位に（`List[Intent]`）。混在意図に対応 |
| 18 | `frontend/src/components/AnswerCard.tsx` | 改修 | サブ質問ごとの節・出典・「この件は有人対応」バッジを表示 |
| 19 | `grace/planner.py` | 改修 | 分解が曖昧なときは `ask_user`（聞き返し）へフォールバック |
| 20 | `docs/multi_question_handling.md`（本書） | 改修 | 実装完了時にステータスを更新し、確定したしきい値・運用を反映 |

---

## 4. 処理フロー Before / After

### 4.1 Before（現行）— 事故が起きる経路

```mermaid
flowchart TB
    Q["query（2問を含む）"]
    P["① Plan（分解禁止・原文コピー）"]
    R["② rag_search（単一ベクトル・top3）"]
    RE["③ reasoning（回答1本／Q1のみ回答）"]
    G["④ groundedness（support_rate 高）"]
    GATE["_answer_gate（coverage 未使用）"]
    OUT["answer で確定 ← Q2 が無言で消失"]

    Q --> P --> R --> RE --> G --> GATE --> OUT
classDef default fill:#000,stroke:#fff,color:#fff
classDef subgraphStyle fill:#1a1a1a,stroke:#fff,color:#fff
class Q,P,R,RE,G,GATE,OUT default
```

### 4.2 After（P0 + P1）— 安全弁と分解検索

```mermaid
flowchart TB
    Q["query（2問を含む）"]
    DET["① 複数質問検知（定型句＋軽量LLM）"]
    SUB["sub_questions = [Q1, Q2]"]
    FAN["② サブクエリ別 並列 rag_search（各 top3・最低保証枠でマージ）"]
    RE["③ reasoning（各サブに回答必須の制約）"]
    GND["④ groundedness（サブ単位 support_rate）"]
    COV["④'' カバレッジゲート（未回答の検出）"]
    D1["answer（全問カバー）"]
    D2["answer + warning（一部未確認）"]
    D3["escalate（未回答あり／根拠不足）"]

    Q --> DET --> SUB --> FAN --> RE --> GND --> COV
    COV --> D1
    COV --> D2
    COV --> D3
classDef default fill:#000,stroke:#fff,color:#fff
classDef subgraphStyle fill:#1a1a1a,stroke:#fff,color:#fff
class Q,DET,SUB,FAN,RE,GND,COV,D1,D2,D3 default
```

---

## 5. データフロー（分解検索）

```mermaid
%%{ init: { "theme": "base", "themeVariables": {
  "background": "#000000", "mainBkg": "#000000",
  "textColor": "#ffffff", "lineColor": "#ffffff",
  "actorBkg": "#000000", "actorTextColor": "#ffffff",
  "actorLineColor": "#ffffff", "noteBkgColor": "#000000",
  "noteTextColor": "#ffffff", "noteBorderColor": "#ffffff" } } }%%
sequenceDiagram
    participant U as "利用者"
    participant S as "support_agent（①〜⑥）"
    participant P as "planner（分解）"
    participant PE as "ParallelSearchEngine"
    participant Q as "Qdrant / Embedding"
    participant C as "confidence / gates"

    U->>S: 「住民票の写しの取り方は？ また、他市町村に移動する方法は？」
    S->>P: 複数意図か判定 → サブクエリ生成
    P-->>S: sub_queries = [Q1, Q2]（＋原文も保持）
    loop 各サブクエリ
        S->>PE: search_all_collections(sub_query, collections, search_func)
        PE->>Q: 並列ベクトル検索
        Q-->>PE: ヒット（score付き）
        PE-->>S: 統合結果（score降順）
    end
    Note over S: サブごとの最低保証枠で<br/>マージ（片寄り防止）
    S->>S: reasoning（各サブに回答必須）
    S->>C: groundedness（サブ単位）＋ coverage
    C-->>S: support_rate / coverage / unanswered
    Note over C: 未回答があれば<br/>answer→warning→escalate に降格
    S-->>U: 回答（＋未回答は有人対応へ）
```

### 5.1 データ変換の段階

| 段階 | データ形 | 説明 |
|:--:|------|------|
| 入力 | `query: str` | 複数質問を含む原文 |
| 分解 | `sub_questions: List[str]` | 意図単位に分割（原文も検索に併用） |
| 検索 | `Dict[sub_query, List[Dict]]` | サブクエリごとのヒット（`score` 付き） |
| マージ | `List[Dict]` | サブごと最低保証枠を確保しつつ統合 |
| 回答 | `answer: str`（P2 では `List[SubAnswer]`） | 各サブ質問に対応する回答 |
| 判定 | `decision` / `warning` / `unanswered` | カバレッジを加味した最終判定 |

---

## 6. リスク・留意点

- **「原文コピー」設計には理由がある**。`grace/planner.py:102-110` は、単語羅列化するとベクトル
  検索の精度が落ちるため原文維持を求めている。よって分解は**原文検索を残したまま追加**する
  （原文＋サブクエリの併用）方式が安全。**単一質問時の挙動は1ミリも変えない**こと。
- **コスト**: 分解 LLM 1回＋検索 N 倍。ただし P0 の検知だけなら定型句判定で**ほぼ無料**
  （軽量 LLM は疑わしいときのみ呼ぶ二段判定）。
- **support_rate の分母問題**（§1.1）: 「言及しなかった Q2」は分母に入らない。
  **カバレッジは別軸で測る**必要がある。
- **過剰分解の防止**: 「A と B の違いは？」は**1問**であり分解してはいけない。
  `max_sub_questions` の上限に加え、分解後に**意味が保存されているか**の検証を入れる。
- **既存互換**: 新規スキーマフィールドはすべて optional にし、旧フロントエンド・既存 API
  クライアントが壊れないようにする。SSE も新規 `step` の追加のみに留める。
- **しきい値の二重管理を避ける**: `coverage_gate_threshold` は vertical プロファイル
  （`notify_th`/`confirm_th`）と整合させ、業界別に上書き可能な形にする。

---

## 7. 設定項目案

| キー | 既定案 | 配置 | 用途 |
|-----|-------|------|------|
| `multi_question_enabled` | `True` | `grace/config.py` | 複数質問検知・カバレッジゲートの有効化 |
| `coverage_gate_threshold` | `0.7` | `grace/config.py` | この値未満なら `warning`／大幅未満なら `escalate` |
| `max_sub_questions` | `4` | `grace/config.py` | 過剰分解の上限 |
| `per_sub_query_limit` | `3` | `config.py` | サブクエリ単位の検索件数予算（現 `RAG_SEARCH_LIMIT` 相当） |
| `total_search_limit` | `8` | `config.py` | マージ後の全体上限 |
| `decompose_model` | `claude-haiku-4-5-20251001` | `grace/config.py` | 分解・検知に使う軽量モデル |

> 📝 **注意**: LLM は Anthropic Claude（既定 `claude-sonnet-4-6`／軽量
> `claude-haiku-4-5-20251001`）、Embedding は Gemini（`gemini-embedding-001`）というプロバイダ
> 方針は本提案でも維持する。分解・検知は**軽量モデル**で十分。

---

## 8. 段階導入プラン

| フェーズ | 対象 # | 概要 | 想定規模 |
|:--:|---|---|---|
| **P0** | #1–#7 | 複数質問の検知とカバレッジゲート（安全弁） | 小（backend 中心・既存資産の再利用） |
| **P1** | #8–#14 | サブクエリ分解と並列 fan-out 検索 | 中（planner/executor/tools に波及） |
| **P2** | #15–#20 | 構造化回答・サブ質問単位のエスカレ・UI | 中〜大（スキーマ＋フロント） |

**P0 を単独でリリース可能**にすることが重要。P1 以降が遅れても、**最も見つけにくい失敗
（片方の質問が黙って消え、しかも高信頼と表示される）を止められる**。

---

## 9. 受け入れ基準

| フェーズ | 受け入れ基準 |
|---|---|
| **P0** | ① 例示クエリで Q2 未回答なら **`answer` にならない**（`warning` または `escalate`）<br>② **単一質問クエリの判定結果が完全に不変**（回帰テストで担保）<br>③ `coverage` / `unanswered` が `SupportResult` に格納され SSE で観測できる |
| **P1** | ① 例示クエリで **Q1・Q2 の両方に出典が付く**<br>② 単一質問クエリのレイテンシが悪化しない（分解は複数意図時のみ発火）<br>③ マージ後に片方のサブクエリの根拠が 0 件にならない |
| **P2** | ① サブ質問ごとに回答・出典・エスカレ粒度が UI に表示される<br>② Q1 は自動回答・Q2 のみ有人、という混在ケースが成立する |

---

## 10. 関連ドキュメント

| ドキュメント | 内容 |
|---|---|
| `docs/agent_parallel_search.md` | `ParallelSearchEngine`（P1 の fan-out で再利用する並列基盤） |
| `backend/docs/core_gates.md` | `_answer_gate` 等の純関数群 IPO 詳細（P0 の改修対象） |
| `backend/docs/core_support_agent.md` | ①〜⑥ パイプライン（`④''` を挿入する箇所） |
| `backend/docs/confidence_flow_grace_vs_backend.md` | grace/ と backend/app/ の判定フロー比較（coverage 未使用の背景） |
| `grace/docs/confidence_calibration.md` | 信頼度測定・較正の処理順（support_rate / coverage の定義） |

---

## 11. 変更履歴

| バージョン | 変更内容 |
|-----------|---------|
| 1.0 | 初版作成（複数質問クエリの問題分析・3案比較・改善モジュール20項目・段階導入プランP0〜P2。**提案段階／未実装**） |
