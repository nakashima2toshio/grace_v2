# grace/docs 棚卸し

**Version 1.6** | 最終更新: 2026-09-14

`grace/` パッケージのドキュメント一覧と、実装への追随状況・残タスク・検証手順をまとめる。
新しく文書を書く／直す前に、まずここを見る。

> ⚠️ **本リポジトリは Anthropic 版。** LLM は `claude-sonnet-4-6`（軽量 `claude-haiku-4-5-20251001`）、
> Embedding のみ Gemini `gemini-embedding-001`（3072 次元）。
> 姉妹リポジトリ `grace_v2_local` は Ollama 版で、**プロバイダ表記はあちらと逆**である。
> 「Anthropic と書いてあるから誤記」ではない。CLAUDE.md §3 を参照。

---

## 目次

- [1. 現在わかっている問題](#1-現在わかっている問題)
- [2. 文書一覧](#2-文書一覧)
  - [2.1 A. コアモジュール（8）](#21-a-コアモジュール8-1-周を回す能力)
  - [2.2 B. 基盤層（3）](#22-b-基盤層3-a-が共通に依存する土台)
  - [2.3 C. 横断・アーキテクチャ文書（4）](#23-c-横断アーキテクチャ文書4)
  - [2.4 A / B の線引きの根拠](#24-a--b-の線引きの根拠実測2026-09-14)
  - [2.5 このディレクトリに置かない文書](#25-このディレクトリに置かない文書)
  - [2.6 横断文書の重複禁止ルール](#26-横断文書の重複禁止ルール)
  - [2.7 重複の検出](#27-重複の検出)
- [3. 実装追随状況](#3-実装追随状況)
- [4. 検証手順](#4-検証手順)
- [5. 残タスク](#5-残タスク)
- [6. 凡例と grep の落とし穴](#6-凡例と-grep-の落とし穴)
- [7. 変更履歴](#7-変更履歴)

---

## 1. 現在わかっている問題

| # | 問題 | 状態 |
|---|---|---|
| 1 | `agent_example.py` を題材にした §D（`grace_core_flow.md`）— この `.py` は git 全履歴に存在しない | ✅ 解消（v2.0 で「本書内の解説用コード片」と明示） |
| 2 | `eval/vertical/` 参照 17 件と、そこでの「実測 KPI」（`support_spec.md`。現在は `backend/docs/`） | ✅ 解消（v2.0 で章ごと削除） |
| 3 | `benchmark.md` の所在が `grace/benchmark.py`（実際は `grace/step_trace/benchmark.py`）／CLI `run_benchmark.py` が存在しない | ✅ 解消（v2.0） |
| 4 | `grace_core.md` の行番号参照 13 件（ほぼ全部ズレていた） | ✅ 解消（v2.0 でシンボル名参照へ） |
| 5 | `grace_core.md` §4.5 の `_record_memory` が**修正前のコードのまま** | ✅ 解消（v2.0 で現行実装へ） |
| 6 | 単数形パス `grace/doc/`（CLAUDE.md §9.1 違反） | ✅ 解消（15 件を是正） |
| 7 | `memory.py` の文書が無い | ✅ 解消（`memory.md` v1.0 を新規作成） |
| 8 | `web_search.md`（1123 行）が `tools.py` 内のクラス 1 個だけの単独文書になっている | ✅ 解消（`tools.md` v3.0 へ統合し削除） |
| 9 | `agent_example_core8.md`（385 行）— `agent_example_core8.py` は git 全履歴に存在しない | ✅ 解消（ユーザー承認のうえ削除。参照元 `support_spec.md` も是正） |
| 10 | モジュール文書に未記載の公開シンボルが 31 件あった | ✅ 解消（**全 11 モジュールで AST 網羅 100%**。§3） |
| 11 | `benchmark.md` が `grace/docs/` にあるが対象は `grace/step_trace/benchmark.py`（CLAUDE.md §9.1 違反。#3 では本文の所在表記を直しただけでファイルは動かしていなかった） | ✅ 解消（2026-09-14 に `grace/step_trace/docs/` へ `git mv`。§2.5） |
| 12 | 文書一覧が「モジュール / 横断」の 2 区分で、A（コア）と B（基盤層）の別が読み取れない | ✅ 解消（2026-09-14 に A/B/C の 3 区分へ再編。線引きの根拠は §2.4 に実測で明示） |
| 13 | 横断文書 4 本のうち `grace.md` / `grace_core.md` / `grace_core_flow.md` が**同じ表・同じ図を重複して持っていた**（モジュール構成図 Mermaid 68 行と依存関係テーブルは `grace_core.md` と `grace_core_flow.md` で**バイト単位で一致**。11 行役割サマリー表は `grace.md` と `grace_core_flow.md` で一致。5 段階設計の ASCII 図・使用例コードも重複） | ✅ 解消（2026-09-14 に WHY/WHAT/HOW の 3 本へ統合。`grace_core_flow.md` → `grace_runtime.md` へ改称。§2.3・§2.6） |
| 14 | §2.1〜§2.3 の「行数」「Ver」列が実測から乖離していた（例: `planner.md` が 1139 行と記載、実測 1183 行） | ✅ 解消（2026-09-14 に `wc -l` と各文書の Version ヘッダーで全件を実測し直した） |
| 15 | 目次の見出しアンカーが 9 件解決しなくなっていた（節番号の繰り下げ・見出しの言い換えに目次が追随していない）。§4.3 のリンク存在チェックでは**ファイルが実在するため検出できない** | ✅ 解消（2026-09-14。`executor.md` 6 件・`backend/docs` 2 件・`docs/support_spec.md` 1 件を是正し、検査を §4.5 として追加） |

---

## 2. 文書一覧

`grace/docs/` は **`grace/*.py`（11 モジュール）の文書と、パッケージ横断の設計文書だけ**を持つ。
サブパッケージ（`grace/step_trace/`）の文書はそのパッケージ配下に置く（CLAUDE.md §9.1）。

区分は `grace_core.md` の依存関係図に合わせて **A（コア）/ B（基盤層）/ C（横断）** の 3 つ。
A と B の線引きは思いつきではなく、**実測した依存の向き**に基づく（§2.4）。

### 2.1 A. コアモジュール（8）— 1 周を回す能力

IPO 形式・`a_class_method_md_format.md` 準拠。**実行順ではなく役割**で束ねている
（理由は §2.4 の注記を参照）。

| 役割 | 文書 | 対象 | 行数 | Ver | 重要度 |
|---|---|---|---:|---|---|
| 計画 | `planner.md` | `grace/planner.py` | 1183 | 3.7 | ★★★ |
| 実行 | `executor.md` | `grace/executor.py` | 2179 | 4.4 | ★★★ |
| 実行 | `tools.md` | `grace/tools.py`（`WebSearchTool` を含む全ツール） | 1678 | 3.1 | ★★★ |
| 評価 | `confidence.md` | `grace/confidence.py` | 1735 | 2.4 | ★★★ |
| 評価 | `calibration.md` | `grace/calibration.py` | 763 | 1.1 | ★★ |
| 制御 | `intervention.md` | `grace/intervention.py` | 1611 | 1.5 | ★★ |
| 制御 | `replan.md` | `grace/replan.py` | 1131 | 2.2 | ★★ |
| 学習 | `memory.md` | `grace/memory.py` | 546 | 1.1 | ★★ |

> 行数は `wc -l` の実測値（2026-09-14）。

### 2.2 B. 基盤層（3）— A が共通に依存する土台

いずれも **`grace` 内への依存がゼロ**で、被依存が多い。

| 文書 | 対象 | 行数 | Ver | 重要度 |
|---|---|---:|---|---|
| `config.md` | `grace/config.py` | 972 | 1.3 | ★★★ |
| `schemas.md` | `grace/schemas.py` | 1314 | 2.0 | ★★★ |
| `llm_compat.md` | `grace/llm_compat.py` | 806 | 1.1 | ★★★ |

### 2.3 C. 横断・アーキテクチャ文書（4）

特定の 1 モジュールに紐づかない設計文書。**WHY / WHAT / HOW の 3 本立て**で、
同じ表・同じ図を 2 箇所に持たないことを規約とする（2026-09-14 の統合。§2.6）。

| 文書 | 問い | 内容 | 行数 | Ver | 重要度 |
|---|---|---|---:|---|---|
| `grace.md` | **WHY** | 設計思想。ReAct → Reflection → GRACE の経緯と **5 段階設計の定義（正本）** | 322 | 2.0 | ★★★ |
| `grace_core.md` | **WHAT** | 実装アーキテクチャ。**構成図・依存関係・モジュール役割サマリー（§3.0）の正本**。§4 に実行メモリの実例、§7 に最小実行サンプル | 1100 | 3.0 | ★★★ |
| `grace_runtime.md` | **HOW** | 実行時に発行される API とプロンプト全文（**正本**）。旧 `grace_core_flow.md` | 415 | 3.0 | ★★★ |
| `confidence_calibration.md` | — | `confidence.py` × `calibration.py` の処理順 | 355 | 1.1 | ★★ |

**どこに何を書くか**（迷ったらこの表を見る）:

| 書きたいもの | 置き場所 |
|---|---|
| 5 段階設計の定義・フェーズの意味・A→B→C の経緯 | `grace.md` |
| モジュール一覧表・依存関係・Mermaid 構成図・使用例コード | `grace_core.md` |
| プロンプト全文・`messages.create` / `embed_content` の発行部・API の発行順 | `grace_runtime.md` |
| 1 モジュールの IPO 詳細 | `<module>.md`（A / B 群） |

> 本書（`README.md`）は文書そのものではなく**棚卸しのメタ文書**なので、A/B/C のどれにも入れない。

### 2.4 A / B の線引きの根拠（実測・2026-09-14）

`grace/*.py` を AST で解析した依存の向き。**B は「依存ゼロ・被依存多」**で、
`tools.py` は config / llm_compat に**依存する側**なので基盤層ではなく A に入る。

| モジュール | 区分 | grace 内依存 | 被依存 |
|---|:--:|---|---:|
| `config` | B | なし | **6** |
| `schemas` | B | なし | 4 |
| `llm_compat` | B | なし | 4 |
| `confidence` | A | config, llm_compat | 2 |
| `memory` | A | なし | 2 |
| `tools` | A | config, llm_compat | 1 |
| `calibration` | A | なし | 1 |
| `intervention` | A | confidence, config, schemas | 1 |
| `replan` | A | config, **planner**, schemas | 1 |
| `planner` | A | config, llm_compat, memory, schemas | 1 |
| `executor` | A | 上記 9 個すべて（`planner` を除く） | 0 |

> ⚠️ **A を「実行順 1〜8」で並べないこと。** 実装と食い違う:
> - `memory` は 1 周の**両端**にまたがる。`planner` が読み（コレクション事前分布）、
>   `executor` が書く（`_record_memory`）。`grace_core.md` §4 の題も
>   「planner → executor → memory」である。
> - `calibration` は `confidence` の**後処理**であって独立ステップではない。
> - `executor` は **`planner` に依存していない**（計画は引数で渡る）。逆に
>   `replan` が `planner` に依存する。番号を振るとこの向きが見えなくなる。
>
> パイプラインとしての順序は `grace.md`（5 段階設計の定義・正本）が受け持つ。
> 本一覧は**文書の棚卸し**なので役割で束ねる。

### 2.5 このディレクトリに置かない文書

| 文書 | 所在 | 理由 |
|---|---|---|
| `benchmark.md` | `grace/step_trace/docs/benchmark.md` | 対象が `grace/step_trace/benchmark.py`。サブパッケージの文書はそのパッケージ配下（CLAUDE.md §9.1）。**2026-09-14 に `grace/docs/` から移動** |
| `s0_arg.md`〜`s9_render.md` | `grace/step_trace/docs/` | 同上 |
| GRACE-Support 設計 3 点 | `backend/docs/` | `backend/app/core/` の文書（2026-09-04 に移動済み・§5 タスク 4） |

### 2.6 横断文書の重複禁止ルール

C 区分の 3 本（`grace.md` / `grace_core.md` / `grace_runtime.md`）は
**同じ表・同じ Mermaid 図を 2 箇所に置かない**。正本は次のとおり。

| 資産 | 正本 | 他の文書での扱い |
|---|---|---|
| 5 段階設計の定義・フェーズ表・5 段階フロー図 | `grace.md` 第1部 (C) | リンクで参照 |
| モジュール役割サマリー（11 モジュール）・5 段階×担当モジュール表 | `grace_core.md` §3.0 | リンクで参照 |
| モジュール構成図（Mermaid）・依存関係テーブル | `grace_core.md` §2 / §2.1 | リンクで参照 |
| 最小実行サンプル・実行方法 | `grace_core.md` §7 | リンクで参照 |
| プロンプト全文・API 発行部・発行順 | `grace_runtime.md` | リンクで参照 |

> ⚠️ **重複は必ず片方だけ腐る。** 2026-09-14 の統合前、`grace_core_flow.md` §B.1 の
> 構成図は `grace_core.md` §2 とバイト単位で一致していた（＝一方を直しても他方は取り残される）。
> 新しい表や図を足すときは、まずこの表の「正本」欄に該当するものが無いか確認する。

### 2.7 重複の検出

同じ Mermaid ブロックが 2 箇所に無いかを確認する（リポジトリ直下で実行）。

```bash
python3 - <<'EOF'
import re, pathlib, collections
blocks = collections.defaultdict(list)
for md in sorted(pathlib.Path('grace/docs').glob('*.md')):
    for b in re.findall(r'```mermaid\n(.*?)```', md.read_text(encoding='utf-8'), re.S):
        blocks[b.strip()].append(md.name)
for b, files in blocks.items():
    if len(files) > 1:
        print(f"重複 {len(b.splitlines())}行: {files}")
EOF
```

---

## 3. 実装追随状況

### 3.1 公開シンボルの網羅（AST 照合・2026-09-04）

**全 11 モジュールで 100%。**

| 文書 | 公開シンボル | 未記載 |
|---|---:|---:|
| `calibration.md` | 15 | 0 |
| `confidence.md` | 45 | 0 |
| `config.md` | 29 | 0 |
| `executor.md` | 48 | 0 |
| `intervention.md` | 36 | 0 |
| `llm_compat.md` | 15 | 0 |
| `memory.md` | 16 | 0 |
| `planner.md` | 24 | 0 |
| `replan.md` | 29 | 0 |
| `schemas.md` | 17 | 0 |
| `tools.md` | 37 | 0 |

2026-09-04 の点検で **31 件の未記載**が見つかり、すべて実装から書き起こして追加した。
内訳は `executor.md` 7（S3 ReAct 経路まるごと）/ `confidence.md` 6 / `intervention.md` 5 /
`schemas.md` 7（ReAct スキーマ 3 クラス＋`repair_plan_dependencies`）/ `config.md` 2 /
`replan.md` 2 / `planner.md` 1 / `tools.md` 1（別途 `CodeExecuteTool` ほか 10 件）。

### 3.2 ⚠️ 「コードの日付 > 文書の日付」は追随遅れの証拠にならない

本リポジトリの履歴は途中でまとめてインポートされている。
`grace/calibration.py` / `intervention.py` / `replan.py` は **1 コミット（`2f93674`）で
新規追加**されており、その日付（2026-08-11）は「そのとき書き換わった」ことを意味しない。

実際、この 3 件のうち `calibration.md` は日付が 2 か月古いのに **AST 網羅は 15/15 で問題なし**、
逆に日付差が小さい `planner.md` / `config.md` には未記載があった。

**日付の比較は当たりを付けるためだけに使い、判断は §4.1 のシンボル網羅と実コードの読解で行う。**

そのうえで、日付ではなく**内容**でズレていたものは次のとおり:

| 文書 | ズレていた内容 |
|---|---|
| `replan.md` | `_enhance_query_with_context` / `_create_remaining_query` を一覧に載せていたが、**この名前のメソッドは既に無い**（`1fbbc6d` で `_build_context_hints` / `_create_remaining_hints` へ改名・役割変更） |
| `planner.md` | `_prioritized_collection` の Process が `best_collection(query, min_count, min_score)` のままで、**実装が渡している `exclude=self._is_excluded` が抜けていた** |
| `tools.md` | §3.2 の `RAGSearchTool._calculate_confidence_factors` 行に **WebSearchTool 用の注記**が付いていた（前 PR の置換ミス）。§7 の再エクスポート記述も実態と違った |
| `config.md` | `GraceConfig` のフィールド表が 13 行しかなく、**実装の 15 フィールドに 2 つ足りなかった** |

---

## 4. 検証手順

文書を直したら、この 5 つを回す。

### 4.1 公開シンボルの網羅（AST）

```bash
python3 - <<'PY'
import ast, pathlib, sys
mod, doc = sys.argv[1], sys.argv[2]
tree = ast.parse(pathlib.Path(mod).read_text(encoding="utf-8"))
syms = []
for n in tree.body:
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)): syms.append(n.name)
    elif isinstance(n, ast.ClassDef):
        syms.append(n.name)
        syms += [m.name for m in n.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
    elif isinstance(n, ast.Assign):
        syms += [t.id for t in n.targets if isinstance(t, ast.Name) and t.id.isupper()]
text = pathlib.Path(doc).read_text(encoding="utf-8")
missing = [s for s in syms if not s.startswith("__") and s not in text]
print(f"{len(syms)} 件中 未記載 {len(missing)}: {missing}")
PY
# 使い方: 上のスクリプトに grace/memory.py grace/docs/memory.md を渡す
```

### 4.2 Mermaid 規約（CLAUDE.md §7.6）

```bash
for f in grace/docs/*.md; do
  fc=$(grep -cE '^\s*(flowchart|graph) ' "$f")
  cd_=$(grep -cE 'classDef default fill: ?#000' "$f")
  sq=$(grep -c '^sequenceDiagram' "$f"); init=$(grep -c '%%{ init' "$f")
  [ "$fc" = "$cd_" ] && [ "$sq" -le "$init" ] || echo "NG $f  fc=$fc cd=$cd_ sq=$sq init=$init"
done
```

### 4.3 リンク存在確認

```bash
python3 -c "
import re, pathlib
bad = []
for md in pathlib.Path('grace/docs').rglob('*.md'):
    t = md.read_text(encoding='utf-8')
    for x in re.findall(r'\]\(([^)#\s]+)', t):
        if x.startswith(('http', 'mailto:')) or x.endswith('.png'): continue
        if not (md.parent / x).resolve().exists(): bad.append(f'{md}: {x}')
print('リンク切れ:', len(bad), bad)"
```

### 4.4 実在しないファイルへの参照

```bash
# 文書がバッククォートで挙げている「パス形式」の .py / .sh を実在確認する。
# ⚠️ ディレクトリを含まない裸のファイル名（`planner.py` 等）は
#    `grace/planner.py` の略記なので除外する（含めると誤検出だらけになる）。
grep -rhoE '`[a-z0-9_]+(/[a-z0-9_]+)+\.(py|sh)`' grace/docs/*.md backend/docs/*.md \
  | tr -d '`' | sort -u | while read -r p; do
    # ⚠️ `core/gates.py` のような**リポジトリ相対でない略記**も混じるので、
    #    よく使う接頭辞を足して総当たりする。
    for pre in "" "backend/app/" "backend/" "grace/"; do
      [ -e "$pre$p" ] && continue 2
    done
    # 過去に存在した形跡すら無ければ「文書だけに存在するファイル」
    git log --all --full-history --oneline -- "$p" | grep -q . || echo "存在しない: $p"
  done
```

> 📝 このチェックで実際に見つかったもの: `agent_example.py` / `agent_example_core8.py` /
> `eval/vertical/run.py` / `run_benchmark.py` / `grace/benchmark.py`（実際は
> `grace/step_trace/benchmark.py`）/ `grace/web_search.py`（実際は `grace/tools.py` 内のクラス）/
> `tests/grace/test_vertical_scope.py`（実際は `backend/tests/test_vertical_scope.py`）。
> いずれも**文書の中にしか存在しなかった**。
>
> 是正後にこのチェックを流すと、残るのは
> 「存在しないと**明記している**説明文・変更履歴の中の名前」だけになる。
> 0 件にはならないので、**行を読んで判断する**（件数だけを見ない）。

### 4.5 見出しアンカーの解決確認

文書内リンクの `#` 以降（アンカー）が、実際の見出しから生成される値と一致するかを確認する。
**節番号を繰り下げたり見出しを言い換えたときに、目次だけが取り残される**のがこの検査で見つかる。

```bash
python3 - <<'PY' grace/docs backend/docs frontend/docs docs grace/step_trace/docs
import re, pathlib, sys
def slug(h):                      # GitHub の見出しアンカー生成則
    out = []
    for c in h.lower():
        if c == ' ': out.append('-')
        elif c in '-_': out.append(c)
        # 英数字と CJK は残し、記号（. : （） ・ ~~ ** → ① 等）は区切り無しで落とす
        elif c.isalnum() and (c.isascii() or c.isalpha() or c.isdecimal()): out.append(c)
    return ''.join(out)
def anchors(path):
    out, fence = set(), False
    for line in pathlib.Path(path).read_text(encoding='utf-8').splitlines():
        if line.startswith('```'): fence = not fence; continue
        if fence or not line.startswith('#'): continue
        out.add(slug(line.lstrip('#').strip()))
    return out
bad = []
for d in sys.argv[1:]:
    for md in pathlib.Path(d).glob('*.md'):
        for link in re.findall(r'\]\(([^)\s]*#[^)\s]+)\)', md.read_text(encoding='utf-8')):
            f, _, anc = link.partition('#')
            tgt = (md.parent / f).resolve() if f else md
            if tgt.exists() and anc not in anchors(tgt): bad.append(f'{md}: #{anc}')
print('アンカー不一致:', len(bad))
for b in bad: print('  ', b)
PY
```

> ⚠️ **記号は「区切り無しで」落ちる。** `①` `・` `~~` `**` `→` `（）` はいずれも
> ハイフンに変わらず**消えるだけ**である（例: `### S2. ① Plan（質問分類・計画）`
> → `#s2--plan質問分類計画`。`①` が消えて前後の空白だけがハイフン 2 個として残る）。
> 手で書くと必ず間違えるので、**このスクリプトに計算させる**こと。
>
> 📝 2026-09-14 にこの検査で **9 件**見つかった。内訳は `executor.md` 6 件
> （v4.4 で `4.1 使用例` を挿入し `### 4.N` を繰り下げたとき目次だけ旧番号のまま残った）、
> `backend/docs/README.md` 1 件・`backend/docs/support_spec.md` 1 件
> （見出しを言い換えたが目次は旧題のまま）、`docs/support_spec.md` 1 件。
> **いずれもリンク存在チェック（§4.3）では検出できない**（ファイルは実在するため）。

---

## 5. 残タスク

| # | タスク | 内容 | 状態 |
|---|---|---|---|
| 1 | ~~追随が遅れている 10 件の突き合わせ~~ | **完了**（2026-09-04）。全 11 モジュールで AST 網羅 100%。§3 参照 | ✅ |
| 2 | ~~`tools.md` の未記載シンボル 10 件~~ | **完了**（2026-09-04）。`CodeExecuteTool` を §4.7 として新設し、37/37 を確認 | ✅ |
| 3 | ~~`grace.md` のバージョン欄~~ | **完了**（2026-09-14）。`**Version 1.0** \| 最終更新: 2026-09-14` を追加し、`grace/docs/` の全 15 文書でヘッダーが揃った | ✅ |
| 4 | ~~GRACE-Support 3 点の所在~~ | **完了**（2026-09-04）。`backend/docs/` へ `git mv` し相対リンクを張り替えた。以後 `grace/docs/` は `grace/` パッケージの文書だけを持つ | ✅ |

> ⚠️ **統合時の落とし穴（実例・2026-09-04）。** `web_search.md` は
> `_calculate_confidence_factors` を**修正前の姿**（`top_score` / `score_spread` のみ。現行は
> **正準キー `max_score` / `score_variance` を併記**する）で保存していた。そのまま写していれば
> **直ったバグを文書化するところだった**。実際、`tools.md` 側の `execute` 戻り値例も
> 旧キーしか載せておらず、Executor が実際に読むキーが見えない状態だった。
> **文書から文書へ写さず、必ず実装から書き起こす。**

---

## 6. 凡例と grep の落とし穴

同じ失敗を繰り返さないための記録。**grep の件数をそのまま信じない。**

| 落とし穴 | 中身 |
|---|---|
| **プロバイダ grep の誤検出** | 「Anthropic」で引くと、`grace_v2_local` との A/B や後方互換を説明する**正当な記述**も引っかかる。件数を数えず、行を読む |
| **本リポジトリは Anthropic 版** | `grace_v2_local`（Ollama 版）と表記が逆。あちらの文書を持ち込むときにプロバイダ記述を混ぜない |
| **Mermaid grep のスペース** | `classDef default fill: #000`（コロンの後にスペース）は **Mermaid としては正しい**が §7.6 の grep に引っかからない。検証スクリプトは `fill: ?#000` で書く（§4.2 はそうしてある） |
| **`grace/doc/` の誤検出** | 「`grace/doc/` → `grace/docs/` に訂正」という**変更履歴の記述**が 2 件ある。これは違反ではない |
| **行番号参照は必ず腐る** | `grace_core.md` の 13 件はほぼ全部ズレていた。シンボル名で参照する |
| **本 README 自体が Mermaid チェックで NG になる** | §4.2 の検証スクリプトが**自分のコードブロックの中の文字列**を拾うため、`fc=0 / cd=1` と出る。図は 1 枚も無いので問題ない |
| **grep で見つかる誤りは軽い方** | 深刻なのは**実装を読まないと気づかない**もの: 修正前のコードのままの記述、存在しない実行基盤の「実測値」、丸ごと抜けたパイプライン段。日付やリンクが揃っていても中身が嘘なことがある |
| **姉妹リポジトリからのコピー** | CLAUDE.md §5。`memory.py` は `best_collection(exclude=...)` が grace_v2 にだけある。文書も丸ごとコピーできない |

---

## 7. 変更履歴

| バージョン | 変更内容 |
|-----------|---------|
| 1.6 | **見出しアンカーの解決確認を §4.5 として追加し、壊れていた 9 件を是正**（2026-09-14・問題 #15）。`executor.md` 6 件（v4.4 で `4.1 使用例` を挿入し `### 4.N` を繰り下げた際、目次だけ旧番号のまま残った。あわせて移動前の「## 6. 使用例」配下に取り残されていた使用例 3 件を §4.1 の下へ移した）、`backend/docs/README.md` 1 件・`backend/docs/support_spec.md` 1 件（見出しを言い換えたが目次は旧題のまま）、`docs/support_spec.md` 1 件。**この種の腐りは §4.3 のリンク存在チェックでは捕まらない**（ファイルは実在し、壊れているのは `#` 以降だけ）ため、検証手順を 4 つから 5 つへ増やした |
| 1.5 | **横断文書 4 本を WHY/WHAT/HOW の 3 本へ統合**（2026-09-14・問題 #13）。`grace.md` / `grace_core.md` / `grace_core_flow.md` は**同じ表と同じ図を重複して持って**いた（構成図 Mermaid 68 行と依存関係テーブルは `grace_core.md` と `grace_core_flow.md` で**バイト単位で一致**、11 行役割サマリー表は `grace.md` と `grace_core_flow.md` で一致、5 段階設計の ASCII 図・使用例コードも重複）。正本を 1 箇所ずつ決め、**`grace.md`＝5 段階設計の定義（WHY）／ `grace_core.md`＝構成図・依存関係・役割サマリー §3.0・最小実行サンプル §7（WHAT）／ `grace_runtime.md`（旧 `grace_core_flow.md` から改称）＝プロンプトと API 発行部（HOW）** に整理した。重複禁止ルールを §2.6、検出スクリプトを §2.7 として明文化。あわせて §2.1〜§2.3 の行数・Ver を `wc -l` と Version ヘッダーで**実測し直した**（問題 #14。`planner.md` 1139→1183 等がずれていた）。外部からのリンク（`backend/docs/support_spec.md` / `support_spec.md` / `backend/docs/README.md` / `docs/doc_modernization_todo.md`）も張り替えた |
| 1.4 | **文書一覧を A/B/C の 3 区分へ再編**（2026-09-14）。従来は「モジュール単位 / 横断」の 2 区分で、コア（A）と基盤層（B）の別が読み取れなかった。`grace_core.md` の依存関係図に合わせ **A. コアモジュール 8 / B. 基盤層 3 / C. 横断 4** とし、線引きの根拠を §2.4 に**実測**で載せた（`grace/*.py` を AST 解析。B は依存ゼロ・被依存 6/4/4、`tools.py` は config / llm_compat に依存する側なので A）。あわせて **A を「実行順 1〜8」で並べない**理由を明記——`memory` は planner が読み executor が書く両端モジュール、`calibration` は confidence の後処理、`executor` は `planner` に依存しない（逆に `replan` が依存する）ため。`benchmark.md` は `grace/step_trace/docs/` へ移動（§2.5・問題 #11）。`grace.md` に Version ヘッダーを追加し残タスク #3 を解消 |
| 1.3 | **GRACE-Support 3 点を `backend/docs/` へ移設**（2026-09-04）。実装が `backend/app/core/support_agent.py` にあるため。`grace/docs/` は `grace/` パッケージの文書だけを持つ状態になった。あわせて、前版でヘッダーの版数だけ 1.1 のまま置き忘れていたのを是正 |
| 1.2 | **モジュール文書 8 件の未記載シンボル 31 件を解消**（2026-09-04）。全 11 モジュールで AST 網羅 **100%** に到達。§3 を「日付比較」から「AST 網羅＋内容でズレていた 4 件」の記録へ書き換えた。⚠️ 本リポジトリの履歴は途中でまとめてインポートされており（`2f93674` が calibration / intervention / replan を新規追加）、**「コードの日付 > 文書の日付」は追随遅れの証拠にならない**ことが分かったので、その注意も §3.2 に明記 |
| 1.1 | `web_search.md` の `tools.md` への統合と `agent_example_core8.md` の削除を反映（問題 #8 / #9 を解消）。文書は 22 → 20 件。統合の副産物として、`tools.md` に **`CodeExecuteTool` クラスごと未記載**であること（AST 照合で 37 件中 10 件が未記載）が判明したため残タスクへ追加 |
| 1.0 | 初版作成。文書 22 件（モジュール 12・横断 9・本書）の一覧、コード最終コミット日との追随比較、検証手順 4 種（AST シンボル網羅・Mermaid 規約・リンク存在・実在しないファイル参照）、残タスク 4 件、grep の落とし穴 7 件を整備 |
