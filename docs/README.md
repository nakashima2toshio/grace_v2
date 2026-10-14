# docs 棚卸し（リポジトリ直下 `docs/`）

**Version 3.24** | 最終更新: 2026-10-14

リポジトリ直下 `docs/` の一覧と、**どのディレクトリに何を置くかの境界**をまとめる。
各領域の棚卸しは backend（[`README_app.md`](../backend/app/docs/README_app.md)・[`README_backend_api.md`](../backend/app/api/docs/README_backend_api.md)・[`README_backend_core.md`](../backend/app/core/docs/README_backend_core.md)） /
[`grace/docs/README_grace.md`](../grace/docs/README_grace.md) /
[`frontend/docs/README_frontend.md`](../frontend/docs/README_frontend.md) /
[`qa_generation/docs/README_qa_generation.md`](../qa_generation/docs/README_qa_generation.md) /
[`chunking/docs/README_chunking.md`](../chunking/docs/README_chunking.md) /
[`qa_qdrant/docs/README_qa_qdrant.md`](../qa_qdrant/docs/README_qa_qdrant.md) /
[`services/docs/README_services.md`](../services/docs/README_services.md) /
[`helper/docs/README_helper.md`](../helper/docs/README_helper.md) /
[`scripts/docs/README_scripts.md`](../scripts/docs/README_scripts.md) にある（直下の本書を含め全 10 領域）。

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
| `<package>/docs/<module>.md` | Python モジュールの IPO | **1 ファイル = 1 文書**。`chunking/` `qa_generation/` `qa_qdrant/` `services/` `grace/` `helper/` `scripts/`・`backend/app/` `backend/app/api/` `backend/app/core/` |
| `backend/app/**/docs/` の `README_<dir>.md` / `core_process_flow.md` | backend 全体の構成（`README_app.md`）・API 契約（`README_backend_api.md`）・Support / Review の流れとジョブ基盤（`core_process_flow.md`）。`backend/docs/` は 2026-10-12 に廃止 | 対象が `backend/app/` に閉じているか |
| `frontend/docs/` | React コンポーネント 1 件ごと | 対象が `frontend/src/` に閉じているか |
| **直下 `docs/`** | **2 つ以上の領域にまたがる横断文書**、およびトップレベル `.py` の IPO | 「`backend/` だけ」「`grace/` だけ」で説明しきれないもの |

### 2.1 直下 `docs/` に置いてよいかの判定

```
その文書が説明する実装は、1 つの領域（backend / grace / frontend / <package>）に閉じているか？
  ├─ はい  → その領域の docs/ へ置く。直下 docs/ には置かない
  └─ いいえ → 直下 docs/ へ置く。ただし §4 の「正本」欄に同じ資産が無いか先に確認する
```

**実例**: `data_prep_install.md` は `chunking/` ＋ `qa_generation/` ＋ `qa_qdrant/` ＋ 直下の `celery_*.py` にまたがる手順なので直下。
一方、ガードレール一覧（GA〜G9）は `gates.py` ＋ `grace/confidence.py` ＋ `grace/executor.py` にまたがるが、**読む人が backend の流れから辿る**ので
2026-10-13 に直下の `guardrails.md` から [`core_process_flow.md` §4](../backend/app/core/docs/core_process_flow.md) へ移した。
またがる領域の数だけでなく、**誰がどこから辿るか**でも置き場所を決める。

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
> （`qdrant_delete_collection.md`。以前あった `agent_parallel_search.md` は対象のモジュールを 2026-10-10 に削除し、文書も 2026-10-13 に削除した）。パッケージに属さないため `<package>/docs/` が作れない。
> 横断文書と混ざるが、これを分けるために 1 ファイルのためのディレクトリは切らない。

---

## 3. 文書一覧

> 行数・Ver は 2026-09-24 の実測値（`wc -l` と各文書の Version ヘッダー）。
> 2026-09-26 に Embedding の記述を改訂した文書（`gemini-embedding-2` への変更と、同日の `gemini-embedding-001` への戻し）の行は、同日に再実測した。

### 3.1 横断文書（2 つ以上の領域にまたがる）

> 📝 2026-10-13 に読み物の横断文書 4 本（`pipelines.md`・`guardrails.md`・`reasoning_flow.md`・`agent_layers.md`）を統合して削除した。
> 3 モードの対照・ガードレール・生成ステップは [`core_process_flow.md` §4](../backend/app/core/docs/core_process_flow.md)、一般用語との対応は直下 [`README.md`](../README.md) §6.5 にある。

| 文書 | 種別 | 内容 | またがる領域 | 行数 | Ver |
|---|:--:|---|---|---:|---|
| `data_prep_install.md` | B | データ準備（チャンク化 → Q/A 生成 → Qdrant 登録）の環境構築。MeCab・Docker（Qdrant / Redis）・Celery の起動とトラブル対応（§5。2026-10-13 に `celery_quick_start.md` を統合）・API キー（2026-10-11 に `qa_qdrant/docs/01_install.md` から移した） | chunking + qa_generation + qa_qdrant | 925 | 2.10 |
| `testing.md` | B | テストの地図。実行方法（結合テスト・E2E）・どこを触ったらどれを流すか・CI の 4 ゲート（2026-10-12 に `backend/docs/` から移した） | tests + backend + frontend + scripts | 421 | 2.13 |

### 3.2 モジュール IPO（トップレベル `.py`）

| 文書 | 種別 | 対象 | 行数 | Ver |
|---|:--:|---|---:|---|
| `qdrant_delete_collection.md` | E | `qdrant_delete_collection.py` — Qdrant のコレクション削除 CLI（2026-10-11 に `qa_qdrant/docs/` から移した） | 344 | 1.2 |

### 3.3 TODO・改善候補

| 文書 | 種別 | 内容 | 行数 | Ver |
|---|:--:|---|---:|---|
| `review_rag_rules_todo.md` | C | GRACE-Review の規程 RAG 整備 TODO。条文が根拠に届かない問題は両リポジトリで解消済み。**規程の雛形は grace_v2 にだけ置く方針**、残作業（雛形の監修・Qdrant コレクションの整理・policy-01 の規程登録ほか）と課題（Web 裏取りの価値・gemma4 の判定の質など）。Sonnet 5.5 / Opus 5.5 のモデル比較（3 サンプルで指摘が完全一致・既定は Sonnet 5.5 のまま） | 191 | 3.11 |
| `performance_levers.md` | C | 回答品質・レイテンシ・コストを決めている箇所と、**未実装の改善候補**（P-03b・P-05・P-10 ほか）と実施順序。2026-10-13 に実装済みレバーの経緯を要約して縮めた | 359 | 2.12 |

### 3.4 資材ディレクトリ

種別はすべて D（書式不問）。

| ディレクトリ | 内容 |
|---|---|
| `examples/` | 画面の例文を流した実行ログ（`GRACE-Support_例文4件.txt`・`GRACE-Review_例文3件.txt`。直下 README §3.3・§4.3 が参照。2026-10-12 に `backend/docs/` から移した） |
| `images/` | README・各文書が参照するスクリーンショット 31 枚（どこからも参照されていない 4 枚は 2026-10-13 に削除） |
| `LLM/` | GRACE とは別の実験の記録。React の `useReducer` カウンタを各モデルに解説・バグ修正させた比較（`llm_compare.md`）と各モデルの出力、課題文（`bug_code_check_llm.txt`・`a_rules.txt`・`reactバグ修正.txt`）。2026-10-13 に grace_v2_local の分（課題文 2 本と qwen の別の実行 `react_ollama_qwen3_5_9b_local.md`）をここへ集約した |
| `LLM_design/` | 同じ実験の一部。外部モデルが書いた `Counter.tsx` の設計書（`by_gpt56sol.md`） |

### 3.5 アーカイブ（`docs/archive/`）

**現在は無い**（2026-10-13 に `archive/qa_tab_port_todo.md`・`archive/agent_parallel_search.md` を削除した。どちらも役目を終えた記録で、git 履歴に残る）。
完了した TODO は `archive/` へ移さずに削除し、残すべき結論だけを現行の文書へ移す。

---

## 4. 横断文書の重複禁止ルール

直下 `docs/` と各領域の `docs/` は**同じ表・同じ Mermaid 図を 2 箇所に置かない**。正本は次のとおり。

| 資産 | 正本 | 他の文書での扱い |
|---|---|---|
| 3 モードのステップ対照表・モード別のガードレール | `backend/app/core/docs/core_process_flow.md` §4.1・§4.2 | リンクで参照 |
| 基本版と GRACE-Support の差 | `backend/app/core/docs/core_process_flow.md` §1.7 | リンクで参照 |
| ガードレール GA〜G9 の機構・実装・失敗時の既定 | `backend/app/core/docs/core_process_flow.md` §4.2 | リンクで参照 |
| reasoning / detect の比較 | `backend/app/core/docs/core_process_flow.md` §4.3（プロンプトの文面は `grace/docs/tools.md` §5.4） | リンクで参照 |
| 性能レバーの現況一覧 | `performance_levers.md` §2 | リンクで参照 |
| 一般用語 → 実装の対応（L0〜L4） | 直下 `README.md` §6.5 | リンクで参照 |
| 関数・クラスの IPO | **各領域の `docs/`**（`backend/app/core/docs/*.md` 等） | 横断文書は IPO を持たない |

> ⚠️ **重複は必ず片方だけ腐る。** 新しい表や図を足すときは、まずこの表の「正本」欄に
> 該当するものが無いか確認する。あれば**リンクにする**。

---

## 5. 重複の検出

同じ Mermaid ブロック・同じ表が 2 箇所に無いかを見る（リポジトリ直下で実行）。
旧 `grace/docs/README.md` §2.7 の検出（2026-10-10 に README_grace.md へ改称した際に整理）を**全 docs ディレクトリへ広げた**もの。

```bash
python3 - <<'EOF'
import re, pathlib, collections
ROOTS = ['docs', 'backend/app/docs', 'backend/app/api/docs', 'backend/app/core/docs', 'grace/docs', 'frontend/docs', 'services/docs',
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
> 削除済み）。直下 `docs/` の文書どうし、または直下と領域別 docs のあいだで出たものが
> **本当の違反**である。

---

## 6. 残タスク

無い（以前の 4 件はすべて完了したので、2026-10-13 に表を外した。経緯は変更履歴と git 履歴にある）。

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
| 3.14 | 2026-10-11 | helper/docs/README_helper.md（2026-10-11 新設）への参照を足した |
| 3.15 | 2026-10-11 | `qa_qdrant/docs/` の構成整理に合わせ、移ってきた 3 文書（`data_prep_install.md`（旧 `qa_qdrant/docs/01_install.md`）・`celery_quick_start.md`・`qdrant_delete_collection.md`）を §3.1・§3.2 に足し、`qa_qdrant/docs/README.md` → `README_qa_qdrant.md` の改名に合わせてリンクを直した |
| 3.16 | 2026-10-11 | `chunking/docs/` の構成整理（`README.md` → `README_chunking.md`）に合わせてリンクを直した |
| 3.17 | 2026-10-11 | `qa_generation/docs/` の構成整理（`README.md` → `README_qa_generation.md`、`__init__.md` を統合、`make_qa_qapipeline.md` → `qa_generation_process_flow.md`）に合わせてリンクを直した |
| 3.18 | 2026-10-11 | `scripts/docs/README_scripts.md`（2026-10-11 新設）への参照を足した（全 10 領域） |
| 3.19 | 2026-10-11 | backend のモジュール文書を `backend/docs/reference/` から `backend/app/docs/`・`backend/app/api/docs/`・`backend/app/core/docs/` へ移したのに追随（冒頭の索引・§2 の配置の境界） |
| 3.20 | 2026-10-12 | backend/docs/ の横断文書の廃止（2026-10-12）に追随し、参照先を backend/app/docs/README_app.md・backend/app/api/docs/README_api.md・backend/app/core/docs/core_process_flow.md などへ付け替えた |
| 3.21 | 2026-10-12 | backend/docs/testing.md を直下 docs/testing.md へ、例文の実行ログを docs/examples/ へ移したのに追随（参照の付け替え） |
| 3.22 | 2026-10-13 | docs/ の整理: app_tabs_overview・celery_quick_start・doc_modernization_todo・archive/ の 2 本・未参照の画像 4 枚を削除。grace_v2_local の LLM 資材を LLM/ へ集約。§3.5・§6 を更新 |
| 3.23 | 2026-10-13 | 読み物の横断文書 4 本（pipelines・guardrails・reasoning_flow・agent_layers）を統合して削除。performance_levers を種別 C（改善候補）へ移し、§4 の正本表を付け替えた |
| 3.24 | 2026-10-14 | 索引の改名（frontend/docs/README.md → README_frontend.md、README_api.md → README_backend_api.md、README_core.md → README_backend_core.md）に合わせて参照を付け替えた |
