# docs 棚卸し（リポジトリ直下 `docs/`）

**Version 1.0** | 最終更新: 2026-09-15

リポジトリ直下 `docs/` の一覧と、**どのディレクトリに何を置くかの境界**をまとめる。
各領域の棚卸しは [`backend/docs/README.md`](../backend/docs/README.md) /
[`grace/docs/README.md`](../grace/docs/README.md) /
[`frontend/docs/README.md`](../frontend/docs/README.md) にある。

> ⚠️ **本リポジトリは Anthropic 版。** LLM は `claude-sonnet-5`（軽量 `claude-haiku-4-5-20251001`）で
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
| `<package>/docs/<module>.md` | Python モジュールの IPO | **1 ファイル = 1 文書**。`chunking/` `qa_generation/` `qa_qdrant/` `services/` `grace/` `grace/step_trace/` |
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

> ⚠️ **トップレベル `.py` の IPO は直下 `docs/` が現状の置き場所**である
> （`agent_parallel_search.md`）。パッケージに属さないため `<package>/docs/` が作れない。
> 横断文書と混ざるが、これを分けるために 1 ファイルのためのディレクトリは切らない。

---

## 3. 文書一覧

> 行数・Ver は 2026-09-15 の実測値（`wc -l` と各文書の Version ヘッダー）。

### 3.1 横断文書（2 つ以上の領域にまたがる）

| 文書 | 内容 | またがる領域 | 行数 | Ver |
|---|---|---|---:|---|
| `pipelines.md` | **3 モード対照のハブ**（基本版 / Support / Review）。ステップ対照表・実行順・基本版との差・ガードレール有効表 | backend + frontend | 162 | — |
| `guardrails.md` | ガードレール GA〜G9 の機構 → 実装 → **失敗時の既定** | backend + grace + ルート | 278 | — |
| `reasoning_flow.md` | 生成の 2 ステップ（Support の `reasoning` / Review の `detect`） | grace + backend | 320 | 2.0 |
| `performance_levers.md` | 回答品質・レイテンシ・コストを決めている箇所と未実装レバー | 全域 | 489 | 2.0 |
| `agent_layers.md` | **一般エージェント用語 → 実装の対応表**（L0〜L4）。実装を読む前の見取り図 | 全域 | 338 | 1.0 |

### 3.2 モジュール IPO（トップレベル `.py`）

| 文書 | 対象 | 行数 | Ver |
|---|---|---:|---|
| `agent_parallel_search.md` | `agent_parallel_search.py` — 並列検索エンジン（`ThreadPoolExecutor`）。⚠️ Legacy ReAct 経路専用で Web アプリからは未稼働（同文書「稼働範囲」参照） | 723 | 1.1 |

### 3.3 進行中の TODO

| 文書 | 内容 | 行数 | Ver |
|---|---|---:|---|
| `doc_modernization_todo.md` | ドキュメント最新化 TODO。**①〜⑧ は完了、§10 に未完 3 件が残る**（スクリーンショット 14 枚・`ReviewForm` / `ReviewPanel` のアクセシビリティ） | 465 | 2.0 |

### 3.4 資材ディレクトリ

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
`grace/docs/README.md` §2.7 の検出を**全 docs ディレクトリへ広げた**もの。

```bash
python3 - <<'EOF'
import re, pathlib, collections
ROOTS = ['docs', 'backend/docs', 'grace/docs', 'frontend/docs', 'services/docs',
         'chunking/docs', 'qa_generation/docs', 'qa_qdrant/docs', 'grace/step_trace/docs']
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
| 1 | スクリーンショット 14 枚 | `doc_modernization_todo.md` §10 の残タスク #1。`ANTHROPIC_API_KEY` ＋ Qdrant のある環境で撮影 | ⏳ 環境 |
| 2 | `ReviewForm` / `ReviewPanel` のアクセシビリティ | 同 #5 / #6。`<label>` の欠落・`aria-live` / `role` の欠落 | ⏳ 実装変更 |
| 3 | `pipelines.md` / `guardrails.md` の Version ヘッダー | この 2 件だけ `**Version X.X**` ヘッダーが無い（他の 5 文書にはある） | ⏳ |

---

## 7. 変更履歴

| バージョン | 変更内容 |
|-----------|---------|
| 1.1 | `agent_layers.md`（一般エージェント用語と実装の L0〜L4 対応表）を §3.1 へ追加し、§4 の正本一覧に「一般用語 → 実装の対応」を登録（2026-09-17）。同書はステップ表・ガードレール表を持たず `pipelines.md` / `guardrails.md` へリンクする |
| 1.0 | 初版作成（2026-09-15）。直下 `docs/` だけ棚卸しの索引が無く、**どこに何を置くかの境界が明文化されていなかった**ため、同じ内容が別の場所へ書かれる事故が繰り返されていた（`grace/docs/` の 4 本重複・`backend/docs/` の IPO 3〜4 重管理・`pipelines.md` §3 の複製）。§2 に配置の判定基準、§4 に重複禁止ルールと正本の一覧、§5 に**全 docs ディレクトリを横断する検出スクリプト**を置いた。あわせて完了済みの `qa_tab_port_todo.md` を `archive/` へ移動し、`guardrails.md` §2 の表見出し「実装（ファイル:行）」を実態（行番号は書かない規則。実際に行番号は 1 つも無い）に合わせて「実装（ファイル・シンボル）」へ是正した |
