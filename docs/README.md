# docs 棚卸し（リポジトリ直下 `docs/`）

**Version 3.13** | 最終更新: 2026-10-10

リポジトリ直下 `docs/` の一覧と、**どのディレクトリに何を置くかの境界**をまとめる。
各領域の棚卸しは [`backend/docs/README.md`](../backend/docs/README.md) /
[`grace/docs/README_grace.md`](../grace/docs/README_grace.md) /
[`frontend/docs/README.md`](../frontend/docs/README.md) /
[`qa_generation/docs/README.md`](../qa_generation/docs/README.md) /
[`chunking/docs/README.md`](../chunking/docs/README.md) /
[`qa_qdrant/docs/README.md`](../qa_qdrant/docs/README.md) /
[`services/docs/README_services.md`](../services/docs/README_services.md) にある（直下の本書を含め全 8 領域）。

> ⚠️ **本リポジトリは Anthropic 版。** LLM は `claude-sonnet-5-5`（軽量 `claude-haiku-5-5`）で
> `ANTHROPIC_API_KEY` が必須、Embedding のみ Gemini `gemini-embedding-001`（3072 次元・`GOOGLE_API_KEY`）。
> 姉妹リポジトリ `grace_v2_local` は Ollama 版で**表記が逆**（CLAUDE.md §3・§5）。

---

## 目次

- [1. なぜ本書が要るか](#1-なぜ本書が要るか)
- [2. 配置の境界（どこに何を置くか）](#2-配置の境界どこに何を置くか)
- [3. 文書一覧](#3-文書一覧)
- [4. 横断文書の重複禁止ルール](#4-横断文書の重複禁止ルール)
- [5. 重複の検出](#5-重複の検出)
- [6. 残タスク](#6-残タスク)
- [7. 変更履歴](#7-変更履歴)

---

## 1. なぜ本書が要るか

**直下 `docs/` だけ索引が無かった。** `backend/docs/` / `grace/docs/` / `frontend/docs/` には
棚卸しの `README.md` があるのに、直下 `docs/` には無く、7 文書＋3 ディレクトリが
並んでいるだけだった。

索引が無いと**境界が誰にも見えない**ので、同じ内容が別の場所へもう一度書かれる。実例:

| 事故 | いつ |
|---|---|
| `grace/docs/` の横断文書 4 本が同じ表・同じ Mermaid 図を重複して持ち、構成図は**バイト単位で一致**していた | 2026-09-14（`grace/docs/README.md` v1.5 で統合） |
| `backend/docs/` で同じ関数 IPO が 3〜4 重管理になっていた | 2026-09-15（`backend/docs/README.md` v1.8 で統合） |
| `docs/pipelines.md` §3 の対照表が `backend/docs/support_spec.md` §7 に**言い換えで複製**された | 2026-09-15（同日に §4 のルールで解消） |

3 件目は**新しい文書を足した当日に発生**している。ルールを書いておかないと同じことが起きる。

---

## 2. 配置の境界（どこに何を置くか）

CLAUDE.md §9.1 の表を、判断に使える形へ具体化したもの。

| 置き場所 | 置くもの | 判断の目安 |
|---|---|---|
| `<package>/docs/<module>.md` | Python モジュールの IPO | **1 ファイル = 1 文書**。`chunking/` `qa_generation/` `qa_qdrant/` `services/` `grace/` |
| `backend/docs/` | `backend/app/**` の IPO ＋ Support / Review の spec・flow | 対象が `backend/app/` に閉じているか |
| `frontend/docs/` | React コンポーネント 1 件ごと | 対象が `frontend/src/` に閉じているか |
| **直下 `docs/`** | **2 つ以上の領域にまたがる横断文書**、およびトップレベル `.py` の IPO | 「`backend/` だけ」「`grace/` だけ」で説明しきれないもの |

### 2.1 直下 `docs/` に置いてよいかの判定

```
その文書が説明する実装は、1 つの領域（backend / grace / frontend / <package>）に閉じているか？
  ├─ はい  → その領域の docs/ へ置く。直下 docs/ には置かない
  └─ いいえ → 直下 docs/ へ置く。ただし §4 の「正本」欄に同じ資産が無いか先に確認する
```

**実例**: `guardrails.md` は `backend/app/core/gates.py` ＋ `grace/confidence.py` ＋
`grace/executor.py` ＋ `support_actions.py` にまたがるので直下。
`core_gates.md` は `gates.py` 1 ファイルの IPO なので `backend/docs/`。
**両者は重複ではない** — 前者は「機構 ID（GA〜G9）で横断的に見る」、後者は「関数の仕様」。

### 2.2 書式（フォーマット仕様）

直下 `docs/` の文書は、まず**種別**を決め、種別に応じた仕様で書く
（`.claude/skills/grace-agent-docs/a_cross_doc_md_format.md` §1）。§3 の各表の「種別」列がそれである。

| 種別 | 内容 | 仕様 |
|---|---|---|
| A 横断文書 | 2 領域以上にまたがる機構の説明 | `a_cross_doc_md_format.md` §2〜§5（**概要に主な責務・各責務対応のモジュール・3 層の構成図**） |
| B 調査メモ・設計案 | 調査結果・提案 | 同 §6 |
| C TODO・索引 | 進行中タスク・本書 | 同 §7.1 |
| D 資材 | ログ・画像・外部レビュー原文 | 同 §7.2（書式不問。空ファイル・空白入りファイル名は禁止） |
| E モジュール IPO | トップレベル `.py` の IPO | `a_class_method_md_format.md` |

> ⚠️ **トップレベル `.py` の IPO は直下 `docs/` が置き場所**である
> （唯一あった `agent_parallel_search.md` は、対象のモジュールを 2026-10-10 に削除したので `archive/` へ移した。現在は無い）。パッケージに属さないため `<package>/docs/` が作れない。
> 横断文書と混ざるが、これを分けるために 1 ファイルのためのディレクトリは切らない。

---

## 3. 文書一覧

> 行数・Ver は 2026-09-24 の実測値（`wc -l` と各文書の Version ヘッダー）。
> 2026-09-26 に Embedding の記述を改訂した文書（`gemini-embedding-2` への変更と、同日の `gemini-embedding-001` への戻し）の行は、同日に再実測した。

### 3.1 横断文書（2 つ以上の領域にまたがる）

| 文書 | 種別 | 内容 | またがる領域 | 行数 | Ver |
|---|:--:|---|---|---:|---|
| `pipelines.md` | A | **3 モード対照のハブ**（基本版 / Support / Review）。ステップ対照表・実行順・基本版との差・ガードレール有効表 | backend + frontend | 249 | 1.4 |
| `guardrails.md` | A | ガードレール GA〜G9 の機構 → 実装 → **失敗時の既定** | backend + grace + ルート | 379 | 1.1 |
| `reasoning_flow.md` | A | 生成の 2 ステップ（Support の `reasoning` / Review の `detect`） | grace + backend | 389 | 2.3 |
| `performance_levers.md` | A | 回答品質・レイテンシ・コストを決めている箇所と未実装レバー | 全域 | 578 | 2.8 |
| `agent_layers.md` | A | **一般エージェント用語 → 実装の対応表**（L0〜L4）。実装を読む前の見取り図 | 全域 | 417 | 1.7 |
| `app_tabs_overview.md` | A | **処理 3 タブの入口**。基本版 / GRACE-Support / GRACE-Review を「業界特化・処理フロー・回答」の 3 点で、画面の実行例つきでまとめる。ステップ対照表は `pipelines.md` へリンク | backend + frontend + grace | 380 | 1.3 |

### 3.2 モジュール IPO（トップレベル `.py`）

| 文書 | 種別 | 対象 | 行数 | Ver |
|---|:--:|---|---:|---|

### 3.3 進行中の TODO

| 文書 | 種別 | 内容 | 行数 | Ver |
|---|:--:|---|---:|---|
| `doc_modernization_todo.md` | C | ドキュメント最新化 TODO。**①〜⑧ と §10 の残タスクはすべて完了**（スクリーンショット全 31 枚を撮影済み） | 488 | 2.6 |
| `review_rag_rules_todo.md` | C | GRACE-Review の規程 RAG 整備 TODO。条文が根拠に届かない問題は両リポジトリで解消済み。**規程の雛形は grace_v2 にだけ置く方針**、残作業（雛形の監修・Qdrant コレクションの整理・policy-01 の規程登録ほか）と課題（Web 裏取りの価値・gemma4 の判定の質など）。Sonnet 5.5 / Opus 5.5 のモデル比較（3 サンプルで指摘が完全一致・既定は Sonnet 5.5 のまま） | 245 | 3.9 |

### 3.4 資材ディレクトリ

種別はすべて D（書式不問）。

| ディレクトリ | 内容 |
|---|---|
| `images/` | README・各文書が参照するスクリーンショット 21 枚 |
| `LLM/` | モデル別の ReAct 実行ログと比較（`llm_compare.md` ほか 11 ファイル） |
| `LLM_design/` | 外部モデルによる設計レビュー（`by_gpt56sol.md`） |

### 3.5 アーカイブ（`docs/archive/`）

**削除ではなく移動**（`git mv`）。記録としての価値はあるが、実装の正ではない文書。

| 文書 | 内容 | 行数 |
|---|---|---:|
| `archive/qa_tab_port_todo.md` | 「② Q/A 作成」タブ移植の調査記録（V1〜V6 は 2026-09-12 に実装済み。現在の設計は `backend/docs/data_pipeline.md`） | 316 |

---

## 4. 横断文書の重複禁止ルール

§3.1 の 4 本は**同じ表・同じ Mermaid 図を 2 箇所に置かない**。正本は次のとおり。

| 資産 | 正本 | 他の文書での扱い |
|---|---|---|
| 3 モードのステップ対照表・実行順フロー図 | `pipelines.md` §2 / §2.1 | リンクで参照 |
| **基本版と GRACE-Support の差（9 項目）** | `pipelines.md` §3 | リンクで参照（`backend/docs/support_flow.md` §7 は設計意図のみを持つ） |
| モード別に効くガードレールの有効表 | `pipelines.md` §4 | リンクで参照 |
| ガードレール GA〜G9 の機構・実装・失敗時の既定 | `guardrails.md` §2 | リンクで参照 |
| reasoning / detect のプロンプト構造 | `reasoning_flow.md` §2 / §3 | リンクで参照 |
| 性能レバーの現況一覧 | `performance_levers.md` §2 | リンクで参照 |
| 一般用語 → 実装の対応（L0〜L4） | `agent_layers.md` §10 | リンクで参照 |
| 関数・クラスの IPO | **各領域の `docs/`**（`backend/docs/core_*.md` 等） | 横断文書は IPO を持たない |

> ⚠️ **重複は必ず片方だけ腐る。** 新しい表や図を足すときは、まずこの表の「正本」欄に
> 該当するものが無いか確認する。あれば**リンクにする**。

---

## 5. 重複の検出

同じ Mermaid ブロック・同じ表が 2 箇所に無いかを見る（リポジトリ直下で実行）。
旧 `grace/docs/README.md` §2.7 の検出（2026-10-10 に README_grace.md へ改称した際に整理）を**全 docs ディレクトリへ広げた**もの。

```bash
python3 - <<'EOF'
import re, pathlib, collections
ROOTS = ['docs', 'backend/docs', 'grace/docs', 'frontend/docs', 'services/docs',
         'chunking/docs', 'qa_generation/docs', 'qa_qdrant/docs']
files = [p for r in ROOTS for p in sorted(pathlib.Path(r).glob('*.md'))
         if 'archive' not in str(p)]

blocks = collections.defaultdict(list)
tables = collections.defaultdict(list)
for md in files:
    text = md.read_text(encoding='utf-8')
    for b in re.findall(r'```mermaid\n(.*?)```', text, re.S):
        blocks[b.strip()].append(str(md))
    cur = []
    for line in text.split('\n'):
        if line.startswith('|'):
            cur.append(line.strip())
        else:
            if len(cur) >= 4:
                tables['\n'.join(cur)].append(str(md))
            cur = []

for label, store in (('Mermaid', blocks), ('表', tables)):
    for body, fs in store.items():
        if len(set(fs)) > 1:
            print(f"{label} 重複 {len(body.splitlines())}行: {sorted(set(fs))}")
EOF
```

> 📝 **検出されても自動的に違反とは限らない。** `frontend/docs/` の各コンポーネント文書は
> **定型の枠（4〜5 行）を各ファイルが持つ設計**である（2026-09-15 時点の実測では、これと
> `grace/step_trace/docs/` の各ステップ文書の 2 種のみが検出された。後者は 2026-09-19 に
> 削除済み）。§3.1 の 4 本どうし、または横断文書と領域別 docs のあいだで出たものが
> **本当の違反**である。

---

## 6. 残タスク

| # | タスク | 内容 | 状態 |
|---|---|---|---|
| 1 | ~~スクリーンショット 10 枚~~ | `doc_modernization_todo.md` §10 の残タスク #1。LLM 実行が要る 10 枚（`S-03`〜`S-05` / `R-03`〜`R-06` / `C-01` / `D-03` / `T-01`） | ✅ 2026-09-26 撮影済み（全 31 スロット完了） |
| 2 | ~~`ReviewForm` / `ReviewPanel` のアクセシビリティ~~ | 同 #5 / #6。`<label>` の欠落・`aria-live` / `role` の欠落 | ✅ 2026-09-12 実装済み（索引への反映は 2026-09-25・v1.6） |
| 3 | `pipelines.md` / `guardrails.md` の Version ヘッダー | この 2 件だけ `**Version X.X**` ヘッダーが無かった | ✅ 2026-09-24（v1.2） |
| 4 | ~~`frontend/docs/` を React 仕様 v1.1 の共通骨格へ~~ | `a_react_page_md_format.md` v1.1 で概要に「各責務対応のモジュール」、`## 1.` に「1.1 システム全体での位置づけ（3 層）」が加わった。既存のコンポーネント文書（20 件）は未追随 | ✅ 2026-09-24（あわせて `backend/docs/` も基本フォーマット・横断文書フォーマットへ追随） |

---

## 7. 変更履歴

| バージョン | 日付 | 変更内容 |
|---|---|---|
| 1.0 | 2026-09-15 | 初版作成（2026-09-15）。直下 `docs/` だけ棚卸しの索引が無く、**どこに何を置くかの境界が明文化されていなかった**ため、同じ内容が別の場所へ書かれる事故が繰り返されていた（`grace/docs/` の 4 本重複・`backend/docs/` の IPO 3〜4 重管理・`pipelines.md` §3 の複製）。§2 に配置の判定基準、§4 に重複禁止ルールと正本の一覧、§5 に**全 docs ディレクトリを横断する検出スクリプト**を置いた。あわせて完了済みの `qa_tab_port_todo.md` を `archive/` へ移動し、`guardrails.md` §2 の表見出し「実装（ファイル:行）」を実態（行番号は書かない規則。実際に行番号は 1 つも無い）に合わせて「実装（ファイル・シンボル）」へ是正した |
| 1.1 | 2026-09-17 | `agent_layers.md`（一般エージェント用語と実装の L0〜L4 対応表）を §3.1 へ追加し、§4 の正本一覧に「一般用語 → 実装の対応」を登録（2026-09-17）。同書はステップ表・ガードレール表を持たず `pipelines.md` / `guardrails.md` へリンクする |
| 1.2 | 2026-09-24 | **`a_cross_doc_md_format.md`（横断文書フォーマット）を新設し、直下 `docs/` を準拠させた**（2026-09-24）。§2.2 に種別 A〜E と仕様の対応を追加し、§3 の各表に「種別」列を足して行数・Ver を実測へ更新。種別 A の 5 文書へ概要（主な責務／各責務対応のモジュール／3 層のアーキテクチャ構成図）を追加（本文の章番号は不変）、`pipelines.md` / `guardrails.md` の Version ヘッダーを追加（§6 残タスク 3 を完了）。本書のヘッダーが 1.0 のまま変更履歴だけ 1.1 に進んでいた不一致も解消した。§6 に残タスク 4（`frontend/docs/` の React 仕様 v1.1 追随）を追加 |
| 1.3 | 2026-09-24 | §6 残タスク 4（`frontend/docs/` の React 仕様 v1.1 追随）を完了（2026-09-24）。`backend/docs/` も `reference/` は基本フォーマット（IPO 冒頭の使用例）、それ以外は `a_cross_doc_md_format.md` v1.1 の種別 A / B / C へ追随させた |
| 1.4 | 2026-09-24 | 冒頭の「各領域の棚卸し」に `qa_generation/docs/README.md`（新設）を追加（2026-09-24） |
| 1.5 | 2026-09-25 | 冒頭の「各領域の棚卸し」に `chunking/docs/README.md` / `qa_qdrant/docs/README.md` / `services/docs/README.md`（いずれも新設）を追加し、全 8 領域に索引がそろった（2026-09-25） |
| 1.6 | 2026-09-25 | §6 残タスク 2（`ReviewForm` / `ReviewPanel` のアクセシビリティ）を完了へ訂正（2026-09-25）。2026-09-12 に実装済み（ラベル・`aria-live`・`role="alert"`）だったのに ⏳ のまま残っていた。§3.3 の `doc_modernization_todo.md` の行数・Ver も更新 |
| 1.7 | 2026-09-26 | 現在の Embedding の記述を `gemini-embedding-001` から `gemini-embedding-2` へ是正（2026-09-26 に変更。定義は `config.py::ModelConfig.EMBEDDING_MODEL` の 1 箇所）。あわせて同じ改訂の `performance_levers.md` v2.2 / `reasoning_flow.md` v2.2 / `pipelines.md` v1.2 の行数・Ver を再実測 |
| 1.8 | 2026-09-26 | Embedding を `gemini-embedding-001` に戻したのに追随（2026-09-26。同日に一度 `gemini-embedding-2` へ変えたが、既存の Qdrant コレクションと grace_v2_local（同じ Qdrant を共用）をそのまま使うため戻した。定義は `config.py::ModelConfig.EMBEDDING_MODEL`）。同じ改訂の 3 文書の行数・Ver を再実測 |
| 1.9 | 2026-09-30 | §3.3 に `review_rag_rules_todo.md`（GRACE-Review の規程 RAG 整備 TODO・種別 C）を追加（2026-09-30） |
| 2.0 | 2026-09-30 | §3.3 の `review_rag_rules_todo.md` を v1.1 へ（条文置換用の雛形 CSV を追記。2026-09-30） |
| 2.1 | 2026-09-30 | §3.3 の `review_rag_rules_todo.md` を v2.0 へ（登録後の実測・優先順・セグメント型検索案を反映。2026-09-30） |
| 2.2 | 2026-09-30 | §3.3 の `review_rag_rules_todo.md` を v2.1 へ（「シミが治る」LP の再実行結果 20 秒を反映。2026-09-30） |
| 2.3 | 2026-09-30 | §3.3 の `review_rag_rules_todo.md` を v2.2 へ（yakki-02 へ第 66 条の原文を追記した進捗。2026-09-30） |
| 2.4 | 2026-09-30 | §3.3 の `review_rag_rules_todo.md` を v2.3 へ（yakki-04 への第 66 条の追記を反映。2026-09-30） |
| 2.5 | 2026-10-01 | §3.3 の `review_rag_rules_todo.md` を v3.0 へ（全面整理。両リポジトリ共通の方針・残作業・課題に組み直し。2026-10-01） |
| 2.6 | 2026-10-02 | §3.3 の `review_rag_rules_todo.md` を v3.2 へ（モデル比較と、それを受けたルール・指示文の修正。2026-10-02） |
| 2.7 | 2026-10-02 | §3.3 の `review_rag_rules_todo.md` を v3.3 へ（2.12・2.13 の対応と修正後の実測。2026-10-02） |
| 2.8 | 2026-10-03 | §3.3 の `review_rag_rules_todo.md` を v3.4 へ（2.14 と実測。2026-10-03） |
| 2.9 | 2026-10-03 | §3.3 の `review_rag_rules_todo.md` を v3.5 へ（2.16〜2.18。2026-10-03） |
| 3.0 | 2026-10-03 | §3.3 の `review_rag_rules_todo.md` を v3.6 へ（2.1 の原文照合を済に。2026-10-03） |
| 3.1 | 2026-10-03 | §3.3 の `review_rag_rules_todo.md` を v3.7 へ（2.1 の監修を完了に。2026-10-03） |
| 3.2 | 2026-10-03 | §3.3 の `review_rag_rules_todo.md` を v3.8 へ（2.17・2.18 の後の実測・3.3 の更新。2026-10-03） |
| 3.3 | 2026-10-06 | §3.1 に `app_tabs_overview.md`（処理 3 タブの概要・種別 A）を追加（2026-10-06） |
| 3.4 | 2026-10-06 | §3.1 の `pipelines.md`（v1.4・G7 の Review 列を実装に合わせて是正）と `app_tabs_overview.md`（v1.1・§5 の表を `grace/docs/README.md` 概要へ移した）の行数・Ver を更新（2026-10-06） |
| 3.5 | 2026-10-08 | 軽量モデルを Haiku 4.5（`claude-haiku-4-5` / `claude-haiku-4-5-20251001`）から Claude Haiku 5.5（`claude-haiku-5-5`）へ変更したのに追随（2026-10-08） |
| 3.6 | 2026-10-08 | 現在の既定 LLM の記述を `claude-sonnet-5` から実装（`config.py::ModelConfig.DEFAULT_MODEL` / `config/grace_config.yml` の `llm.model`）どおり `claude-sonnet-5-5` へ是正（冒頭の注記）（2026-10-08） |
| 3.7 | 2026-10-10 | `agent_layers.md` を v1.2 へ（削除した `a_pages_md_format.md` への言及を外した）。変更履歴を 3 列へ移した |
| 3.8 | 2026-10-10 | `grace/step_trace/`（`benchmark.py` を含む）を 2026-10-10 にディレクトリごと削除したのに追随し、現状を述べる記述から外した（過去の経緯の記述は残す）。§3.1 の `agent_layers.md` / `agent_parallel_search.md` の行数・版を実測へ（v1.3） |
| 3.9 | 2026-10-10 | Legacy ReAct 経路（`services/agent_service.py`・`agent_parallel_search.py`・`agent_cache.py`・`executor._execute_legacy_agent_step`・`run_legacy_agent` アクション）を 2026-10-10 に削除したのに追随 |
| 3.10 | 2026-10-10 | `agent_layers.md` の行数・版を実測値へ更新（Tool Use の削除に追随） |
| 3.11 | 2026-10-10 | 索引の行数・版を実測値へ更新（テストを直下 `tests/` へ移した変更に追随） |
| 3.12 | 2026-10-10 | `grace/docs/` の構成整理（`README.md` → `README_grace.md`、`grace.md` / `grace_core.md` / `grace_runtime.md` / `confidence_calibration.md` を `README_grace.md` / `grace_process_flow.md` / `grace_data_flow.md` へ統合）に合わせてリンクを直した |
| 3.13 | 2026-10-10 | `services/docs/` の構成整理（`README.md` → `README_services.md`、`__init__.md` を統合）に合わせてリンクを直した |
