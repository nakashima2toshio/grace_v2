# ドキュメント最新化・不具合除去 TODO（`./run_dev.sh` テスト前の地ならし）

**Version 1.1** | 作成日: 2026-09-12 | 最終更新: 2026-09-12 | 対象コミット: `d832a54`（master）

`./run_dev.sh` で起動する React アプリのテストに入る前に、**「ドキュメントを信じて
テストしたら、ドキュメントの方が間違っていた」を潰す**ための TODO。

> **原則**: 本書の指摘はすべて**実コードを読んで確認した事実**のみを書く。
> 推測（「たぶん古い」）は載せない。未確認のものは §7 の「要調査」に置く。

---

## 0. 現在地（実測サマリ）

| 観点 | 実測 | 判定 |
|---|---|---|
| CLAUDE.md のパイプライン記述 | 実装は 0-(A) analyze を持つが CLAUDE.md §1 に無い | ❌ 誤り |
| README.md の画像リンク | ~~30 件中 25 件がリンク切れ~~ → **誤り。24 件は意図的なコメント（撮影待ちスロット）** | ✅ **指摘を撤回**（§2 訂正） |
| README_DATA.md | v1.0 / 2026-08-05。2026-09-12 追加の「② Q/A 作成」を**一言も含まない** | ❌ 陳腐化 |
| frontend/docs | コンポーネント 18 個中 **4 個が文書なし**、1 個が実装より古い | ❌ 欠落・陳腐化 |
| Streamlit 残骸 | `services/docs/` 8 ファイル＋`qa_qdrant/docs/01_install.md` に記述あり。**実コードに streamlit の import は 0 件** | ❌ 移植漏れ |
| LLM モデル表記 | `services/docs/token_service.md` に `gpt-4o` 系、`chunking/docs/*` に `gemini-2.5-flash` | ⚠️ 要仕分け |
| grace/docs・backend/docs の棚卸し | 各 `README.md` が索引を持ち、実ファイルと一致 | ✅ 良好 |

**結論**: `grace/docs/` と `backend/docs/` は健全。**壊れているのは
README.md / README_DATA.md / frontend/docs/ / services/docs/ と CLAUDE.md 自身**。

---

## 1. P0 — CLAUDE.md の誤りを直す（他の全作業の前提）

CLAUDE.md が間違っていると、以後の修正がすべて間違った基準で行われる。最初に直す。

### T1-1 ⭐ §1「パイプライン 1 周」に 0-(A) 入力・質問分析が無い

**事実**:
- 実装: `backend/app/core/support_agent.py:86` に `"analyze",  # 0-(A) 入力・質問分析（複数質問の検知 → 選択 → 再構成）`、
  同 `:374` 以降に実処理（`looks_like_multi_question` → `analyze_questions` → `QuestionSelectModal`）。
- 他文書: `README.md`（複数質問の対話選定 ✅）、`docs/guardrails.md` の **GA**、
  `docs/multi_question_handling.md` はいずれも 0-(A) を記述済み。
- 姉妹リポジトリ `grace_v2_local/CLAUDE.md` は 0-(A) / 0-(B) を含む正しい記述を持つ。
- **grace_v2 の CLAUDE.md だけが `S1 業界プロファイル適用 → ①Plan` から始まっている。**

**やること**: CLAUDE.md §1 のパイプライン図を実装に合わせる。

```
0-(A) 入力・質問分析（複数質問の検知 → 選択 → 再構成）
 → 0-(B) 業界プロファイル適用
 → ① Plan → ② Execute → ③ Confidence → ④ 回答ゲート
 → ⑤ Web フォールバック → ④' 情報なし回答の検知 → ⑥ Action
```

### T1-2 §6 の「state/ 純関数」表に実在モジュールが 5 件欠けている

**事実**: `frontend/src/state/` の実ファイル（テストを除く）は 16 件。CLAUDE.md §6 の表に**無い**のは:

| 欠けているモジュール | 役割（実コード確認済み） |
|---|---|
| `dataParams.ts` | データ管理タブの送信ペイロード組み立て |
| `interventionKind.ts` | HITL 介入の種別判定 |
| `metaFetch.ts` | メタ取得失敗のメッセージ化（§5 の表には在るが §6 に無い） |
| `timelineAnnounce.ts` | タイムラインの読み上げ文言（同上） |
| `useJobTiming.ts` | 開始・完了時刻の保持フック（判断は `elapsed.ts` 側・**表に注記が要る**） |

**やること**: §6 の表に 5 件を追記する。`useJobTiming.ts` は「フックであって純関数ではない
（判断は `elapsed.ts`）」と明記する — これを書かないと §6 の規約に反して見える。

### T1-3 §1 の層の表に「データ準備（Web）」の行が無い

**事実**: 2026-09-12 に「② Q/A 作成」を追加し、Web からの実行口は
`backend/app/api/data.py` / `backend/app/core/data_jobs.py` / `services/data_pipeline_service.py`。
CLAUDE.md §1 の表は「データ準備 | `chunking/`, `qa_generation/`, `qa_qdrant/`」（＝CLI 側）だけ。
`grace_v2_local/CLAUDE.md` は「データ準備（CLI）」「データ準備（Web）」の 2 行に分けている。

**やること**: §1 の表を 2 行に分ける。

### T1-4 §9.4「参照してはいけない廃止ファイル」の検証 — ✅ 修正不要

実在チェック済み: `setup.py` / `server.py` / `a30_qdrant_registration.py` / `agent_rag.py` /
`ui/` / 直下 `tests/` / `test_celery_integration.py` は**すべて不在**、`start_celery.sh` は**実在**。
記述は正しい。**この項は直さない**（誤って「直す」と二重に壊れる）。

---

## 2. ~~P0 — README.md のリンク切れ~~ → ⚠️ **v1.0 の指摘は誤りだった（訂正）**

### T2-1 ❌ 訂正: リンク切れ 25 件は存在しない

**v1.0 で「画像リンク 25 件が壊れている」と書いたのは誤りである。** 撤回する。

**何を間違えたか**: リンク抽出に使った grep が **HTML コメント（`<!-- ... -->`）と
コードブロックを除外していなかった**。README.md は §画面ショット挿入位置 で
**「撮影前のスロットはコメントのまま置く」様式を明文化**しており、24 件は
その様式どおりの**撮影待ちプレースホルダ**だった。残る 1 件（`x-00-example.png`）は
様式を説明する ```markdown コードブロック内のサンプル記述である。

**実際に壊れているリンクは 0 件。** README には「撮影の進捗」表（撮影済み 5 / 未撮影 24）
まで用意されていた。**この文書の方が README より状況を正しく把握できていなかった。**

> 📌 **教訓**: リンクチェックは HTML コメントとコードブロックを除外してから行う。
> 「壊れている」と判定する前に、その記法が**意図された様式でないか**を確認する。

### T2-1' ✅ 実施済み: スクリーンショット 11 枚を撮影（2026-09-12）

`./run_dev.sh` 相当（backend :8000 + Vite :5173）を起動して撮影し、コメントを外した。

| 撮影できた（11 枚） | 備考 |
|---|---|
| `H-01` / `H-02a` / `H-02b` | H-02a/b はタブ往復の 2 枚 1 組。**`formMemory` が効いていることを実機で確認**（往復後も dry-run OFF と入力が保持） |
| `R-01` / `R-02` | R-02 は例文チップ「NG 例（優良誤認・薬機法）」押下後 |
| `D-01` / `D-02` / `D-04` | D-02 にモデル既定値が写っている（§6.5 の発見につながった） |
| **`D-09`（新設）** | **② Q/A 作成にスロットが無かった**ため新設。全 29 枚 → 30 枚 |
| `E-01` / `E-02` | **キーが無い環境だからこそ正確に再現できた**（下記） |

| 撮影できなかった（14 枚） | 理由 |
|---|---|
| `S-03`〜`S-05` / `R-03`〜`R-06` / `C-01` / `D-03` / `T-01` | `ANTHROPIC_API_KEY` が無く LLM 実行ができない |
| `D-05` / `D-06` / `D-07` / `D-08` | Qdrant 未起動（この環境は docker デーモンが使えない） |

> ⚠️ **撮れなかったものを「それらしい画面」で代用しない。** 初回の撮影では
> `D-06`（コレクション一覧）に **Qdrant 停止時の 0 件表示**を、`S-03`（実行中）に
> **実行前の待機画面**を当ててしまい、いずれも破棄した。スロットの説明文が
> 「何を写すか」を明記しているので、**撮る前に必ず読むこと**。

### T2-2 README.md のバージョンヘッダが実態と合っていない

**事実**: ヘッダは `Version 2.9 | 最終更新: 2026-08-14`。しかし本文には
2026-09-12 追加の「② Q/A 作成」（§4.5.3）と `JobClock.tsx`（§対応表 1175 行目）が既に入っている。
**中身は更新済みなのにヘッダだけ古い。**

**やること**: ヘッダを更新し、§8 変更履歴に 09-02 / 09-12 の 3 コミット分
（3 文書対応列の追加 / ② Q/A 作成 / start_celery.sh 是正）を追記する。

---

## 3. P1 — README_DATA.md の扱いを決める（重複 2,313 行）

### T3-1 ⭐ 陳腐化の実測

- `README_DATA.md` = **2,313 行 / v1.0 / 2026-08-05**。最終コミットは 2026-08-18。
- 「② Q/A 作成」「`/api/qa/generate`」の出現回数は **0**。
- 同じ領域を扱う文書が他に 3 つある:
  `backend/docs/data_pipeline.md`（563 行・v1.2・09-12 更新）、
  `backend/docs/core_data_jobs.md`、`backend/docs/api_data.md`。
- README.md からの参照は **1 箇所だけ**（1415 行）。

### T3-2 方針案（要判断・§8 で確認）

| 案 | 内容 | 所要 |
|---|---|---|
| **A（推奨）** | README_DATA.md を**廃止**。生き残っている内容（IPO 詳細）を `backend/docs/data_pipeline.md` に統合し、README.md の参照を差し替える | 中 |
| B | README_DATA.md を最新化し、`backend/docs/*` 側を「詳細は README_DATA へ」に寄せる | 大 |
| C | 現状維持＋冒頭に「⚠️ 2026-08-05 時点。最新は data_pipeline.md」の但し書き | 小 |

> **⚠️ 削除は不可逆**。案 A を採るなら CLAUDE.md のファイル書き込みポリシーに従い
> **削除前にユーザー確認**を取る（§8 の確認事項 Q1）。

---

## 4. P1 — frontend/docs の欠落・陳腐化（テスト対象そのもの）

### T4-1 ⭐ SupportPanel.md が**修正前のコード**を載せている（最も危険）

**事実**: `frontend/docs/SupportPanel.md`（v1.2 / 2026-08-05、最終コミット 08-29）の
コードブロックは:

```tsx
fetchVerticals()
  .then(setVerticals)
  .catch(() => setVerticals([]));      // ← 実装から消えたコード
```

一方 `frontend/src/components/SupportPanel.tsx`（最終コミット **2026-09-12**）は
`verticalsError` / `MetaErrorBanner` / `loadVerticals` を持ち、ソース中のコメントで
**「⚠️ 握りつぶさない。以前は空配列に倒すだけで原因がユーザーに伝わらなかった」**と
明示している。つまり**ドキュメントが「直したはずの不具合」を正解として載せている**。

**やること**: SupportPanel.md を実装に追随（`variant` / `useJobTiming` / `MetaErrorBanner` /
`QuestionSelectModal` / `interventionKind` の 5 点が未反映）。v1.3 へ。

### T4-2 文書が存在しないコンポーネント 4 件

| コンポーネント | 実装の最終更新 | 状態 |
|---|---|---|
| `ReviewPanel.tsx` | 2026-09-12 | **文書なし**（`review_ui.md` が部分的に触れるのみ） |
| `ReviewForm.tsx` | 2026-08-20 | **文書なし**（単体テスト `ReviewForm.examples.test.ts` は在る） |
| `JobClock.tsx` | 2026-08-18 | **文書なし**（README §対応表に 1 行だけ） |
| `MetaErrorBanner.tsx` | 2026-08-18 | **文書なし** |

**やること**: `.claude/skills/grace-agent-docs/a_react_page_md_format.md` に従って 4 本作成。
`review_ui.md` は `ReviewPanel.md` / `ReviewForm.md` と重複するので、**索引・横断文書**の
位置づけに書き換える（対応する `.tsx` が無いため、現状は命名規則から外れている）。

### T4-3 バージョンヘッダが実装より古い 5 件

| 文書 | ヘッダ日付 | 実装の最終更新 |
|---|---|---|
| `CollectionPanel.md` | 2026-08-05 | 2026-08-18 |
| `ConfirmModal.md` | 2026-08-01 | 2026-08-18 |
| `DocumentView.md` | 2026-08-01 | 2026-08-18 |
| `FindingList.md` | 2026-08-01 | 2026-08-18 |
| `ReviewTimeline.md` / `StepTimeline.md` | 2026-08-01 | 2026-08-18 |

**やること**: 各文書の Props ブロックを実装と 1 行ずつ突き合わせる。
**CLAUDE.md §6 の警告どおり、Props の TS ブロックは逐語コピーなので
「一部だけ合っている」状態が最も危険**。差分が無ければ日付だけ更新する。

### T4-4 `frontend/docs/README.md`（索引）が無い

`grace/docs/README.md` と `backend/docs/README.md` は棚卸し表を持ち、実ファイルと一致していた。
**frontend/docs だけ索引が無い**ため、T4-2 のような欠落が検知できなかった。

**やること**: 同形式の `frontend/docs/README.md` を作る（コンポーネント / state 純関数 /
テスト件数の 3 表）。**テスト件数は `npm test` を実行して実測値を書く**（記憶で書かない）。

---

## 5. P2 — Streamlit 残骸の除去（旧アプリからの移植漏れ）

### T5-1 ⭐ 事実確認

- **実コードに `streamlit` の import は 1 件も無い**（`services/*.py` を grep して 0 件）。
- にもかかわらず、以下の文書が Streamlit を現役の呼び出し元として記述している:

| ファイル | 出現 | 内容 |
|---|---|---|
| `services/docs/agent_service.md` | 4 | 「**`ui/pages/agent_chat_page.py`** がリアルタイム表示」← §9.4 の廃止パス |
| `services/docs/dataset_service.md` | 4 | `import streamlit as st` を含む使用例、`file_uploader` 前提の説明 |
| `services/docs/log_service.md` | 3 | §6.2「応用的なワークフロー（Streamlit UI連携）」＋ `import streamlit as st` |
| `services/docs/file_service.md` | 2 | Mermaid 図のノード `ST["Streamlit UI"]` |
| `services/docs/config_service.md` | 1 | 同上 `UI["Streamlit UI"]` |
| `services/docs/qdrant_service.md` | 1 | `ST["Streamlit Dashboard"]` |
| `services/docs/__init__.md` | 1 | `UI["Streamlit UI"]` |
| `qa_qdrant/docs/01_install.md` | **17** | 手順全体が Streamlit 前提 |

- `services/docs/qa_service.md` は v1.1（09-12）で**既に Streamlit 記述を削除済み** → **これが手本**。

**やること**: 呼び出し元を `React UI（frontend/）+ FastAPI（backend/app/api/）` へ置換。
Mermaid ノードは `UI["React UI (frontend/)"]` とし、**CLAUDE.md §7.2 の黒背景スタイル
（`classDef default fill:#000,stroke:#fff,color:#fff`）を維持**すること。
使用例の `import streamlit as st` は CLI / FastAPI 依存注入の例へ書き換える。

### T5-2 `qa_qdrant/docs/01_install.md`（17 件）は単独タスクにする

最終コミットは 2026-09-12（Celery 関連の是正）だが Streamlit 記述が残っている。
分量が大きいので T5-1 とは別コミットに分ける。

---

## 6. P2 — LLM / モデル表記の仕分け

**⚠️ ここは CLAUDE.md R1〜R4 が効く領域。「モデル名を直す」を安易にやらない。**
以下は**文書の記述と実コードの対応を確認したうえでの仕分け**である。

### T6-1 `services/docs/token_service.md` の `gpt-4o` / `text-embedding-3-*` — ✅ 修正しない

**事実**: `services/token_service.py:34-93` に `gpt-4o` / `gpt-4o-mini` /
`text-embedding-3-small` / `text-embedding-3-large` / `gemini-2.0-flash` の
**tiktoken エンコーディング表・価格表・上限表が実在する**。文書はそれを正しく写している。

**やること**: **表そのものは直さない。** ただし文書冒頭に
「本モジュールは**トークン計算の互換テーブル**であり、本プロジェクトの
**既定 LLM は `claude-sonnet-4-6`**（CLAUDE.md §3）」と 1 行の位置づけを足す。
これが無いと読者が「このプロジェクトは GPT-4o を使う」と誤読する。

### T6-2 `chunking/docs/*` の `gemini-2.5-flash`（14＋4 件）— ⚠️ 要是正の可能性

**事実**: `chunking/docs/csv_text_to_chunks_text_csv.md` に 14 件、
`chunking/docs/check_async.md` に 4 件。一方 `chunking/docs/async_api_client.md` は
`claude-sonnet-4-6`（5 件）で**同じパッケージ内で表記が割れている**。

**やること**: `chunking/*.py` の実装を読み、LLM 用途のプロバイダ解決を確認してから是正する。
CLAUDE.md §3 の「LLM 用途の Gemini 既定は移植漏れ（負債）」に該当するなら
**コード側も含めて** Anthropic へ寄せる。**文書だけ書き換えて実装を放置しない。**

### T6-3 `qa_qdrant/docs/*` の `gemini-2.0-flash`（12 件）— 同上

`make_qa_qapipeline.md`（8）/ `qa_qdrant_architecture.md`（4）/ `make_qa.md`（2, 2.5-flash）。
Q/A 生成は CLAUDE.md §3 で **Anthropic 必須**の用途。T6-2 と同じ手順で確認・是正。

### T6-5 ⭐ 実機で発見: チャンキングの既定モデルが価格表に無い（2026-09-12）

**事実**（`./run_dev.sh` の「データ管理 → ① チャンキング」画面で確認）:

| 箇所 | 値 |
|---|---|
| 画面のモデル欄の既定値 | **`claude-haiku-4-5`** |
| `frontend/src/components/DataJobPanel.tsx:67` | `useState('claude-haiku-4-5')` |
| `backend/app/core/data_jobs.py:106`（`ChunkingParams`） | `model: str = "claude-haiku-4-5"` |
| `config.py` の `SUPPORTED` / `MODEL_PRICING` / `MODEL_LIMITS` | **`claude-haiku-4-5-20251001` のみ**。`claude-haiku-4-5` は無い |

**影響**: 参照はすべて `.get(model, <既定>)` なので**落ちない**が、
`claude-haiku-4-5` は表に無いため**汎用の既定値へ静かにフォールバックする**
（`config.py:69` → `{"max_tokens": 128000, "max_output": 4096}`、
`config.py:74` → `{"input": 0.00015, "output": 0.0006}`）。
つまり**このモデルのコストとトークン上限が実態と違う値で計算される**。

> ⚠️ **CLAUDE.md R1/R4 に従い、「モデル名を直す」ことを最初の対応にしない。**
> `claude-haiku-4-5` と `claude-haiku-4-5-20251001` は**どちらも実在しうる**
> （エイリアス / 日付付き）。問題は「名前が間違っている」ことではなく
> **価格表・上限表に片方しか載っていない**ことである。

**取りうる対応（要判断・Q3）**:

| 案 | 内容 |
|---|---|
| A | `config.py` の 3 つの表に `claude-haiku-4-5` の行を足す（既定値を変えない・影響が最小） |
| B | チャンキングの既定を `claude-haiku-4-5-20251001` に揃える（表を変えない） |

**どちらもコードの変更**なので、Q3 の回答を得てから着手する。

### T6-4 `config.py` の後方互換ブロック — 文書に位置づけを書く

`config.py:411-450` の `GeminiConfig` は LLM モデル一覧（`gemini-2.5-flash` 等）を持つが、
ソース中に「**LLM の既定は Anthropic Claude=ModelConfig。下記 LLM モデルは後方互換**」と
明記済み。`grace/docs/config.md` / `services/docs/config_service.md` にも同じ但し書きを入れる。

---

## 7. P3 — 索引・重複の整理

### T7-1 完了済み TODO 文書の扱い

| 文書 | 状態 |
|---|---|
| `docs/qa_tab_port_todo.md` | 冒頭に「✅ 2026-09-12 に V1〜V6 を実装済み。調査記録として残す」と明記済み → **そのままでよい**（手本） |
| `docs/review_false_positive_todo.md` | §0 で 4 項目すべて「解消」。**完了表記が冒頭に無い** → 同じ形式の但し書きを足す |

### T7-2 `grace/docs` の横断文書 — ✅ 修正不要

`grace.md` / `grace_core.md` / `grace_core_flow.md` / `confidence_calibration.md` は
対応する `.py` を持たないが、`grace/docs/README.md` §2.2 に**横断文書として明記**されており
命名規則違反ではない。`benchmark.md` も `grace/step_trace/benchmark.py` 対応と索引にある。
**「孤児ファイル」と誤認して消さないこと。**

### T7-3 README.md の API 一覧に未記載のエンドポイント

実ルートと README の突き合わせ結果、README に出てこないのは
`/api/qa/generate`・`/api/data/result/{job_id}`・`/api/qdrant/health`・
`/api/qdrant/collections/{name}/points` の 4 本。§4.5 の対応表に追記する。

---

## 8. 着手前に確認したいこと

| # | 確認事項 | 既定（返事が無ければこれで進める） |
|---|---|---|
| Q1 | `README_DATA.md`（2,313 行）を**廃止**して `backend/docs/data_pipeline.md` へ統合してよいか（§3） | **案 C**（但し書きのみ・削除しない）で進める |
| Q2 | ~~スクリーンショット 25 枚~~ → **11 枚を撮影済み（2026-09-12）。残り 14 枚は API キーと Qdrant が要る** | キーと Qdrant のある環境で撮る |
| Q3 | T6-2 / T6-3 で**コード側の既定モデルまで**是正してよいか（＝文書だけでなく実装も触る） | 調査結果を報告してから着手（勝手に変えない） |

---

## 9. 推奨する実行順序

```
① T1-1〜T1-3（CLAUDE.md 修正）          ← 全作業の基準を正す
② T2-2 / T4-1（明白な「誤った記述」）    ← 読むと間違えるものを最優先で消す
③ T4-4（frontend/docs/README.md 索引）  ← 以後の欠落を検知できるようにする
④ ./run_dev.sh 起動テスト ＋ T2-1（撮影） ← 本来の目的。docs 修正と同時に進む
⑤ T4-2 / T4-3（frontend/docs 補完）     ← ④ で見た実画面を根拠に書ける
⑥ T5-1 / T5-2（Streamlit 除去）
⑦ T6-2 / T6-3（モデル表記の調査 → 是正） ← Q3 の回答待ち
⑧ T3（README_DATA）/ T7（索引・重複）
```

**①〜③ はテスト前に、④ 以降はテストと並行**。④ を先にやると、②③ の未修正ドキュメントを
基準にテストしてしまい「実装のバグ」と「ドキュメントの誤り」の切り分けができなくなる。

---

## 10. 完了条件（チェックリスト）

- [ ] CLAUDE.md §1 が 0-(A) から始まっている
- [ ] CLAUDE.md §6 の表に state/ の 16 モジュールが漏れなく載っている
- [x] `README.md` の `![...]` が**すべて実在ファイルを指す**（もともと切れ 0 件。T2-1 の指摘は誤りだった）
- [ ] 残り 14 枚のスクリーンショット（`ANTHROPIC_API_KEY` ＋ Qdrant のある環境で撮影）
- [ ] `frontend/docs/` にコンポーネント数ぶんの `.md` と索引 `README.md` がある
- [x] `SupportPanel.md` の**本文**に `.catch(() => setVerticals([]))` が現行コードとして残っていない
      （**不具合の説明と変更履歴には残してよい**。過去の誤りを消すと再発時に追えなくなる）
- [ ] `grep -ril streamlit --include='*.md' .`（`.claude/` 除く）が 0 件
- [ ] 索引に書いたテスト件数が `npm test` / `uv run pytest backend/tests -q` の**実測値**
- [ ] 4 つの CI ゲート（compileall / ruff / pytest / frontend）が緑

---

## 11. 変更履歴

| Version | 内容 |
|---|---|
| 1.1 | ①〜④ の実施結果を反映（2026-09-12）。**T2-1「リンク切れ 25 件」を誤りとして撤回**（HTML コメントを除外せず判定していた）。スクリーンショット 11 枚を撮影し `D-09` を新設。T1-1〜T1-3 / T4-1 / T4-4 を完了。§6 に実機で見つかったモデル名の不一致（T6-5）を追記 |
| 1.0 | 初版。実測ベースで P0〜P3 を整理（2026-09-12） |
