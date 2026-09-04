# grace/docs 棚卸し

**Version 1.1** | 最終更新: 2026-09-04

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
| 2 | `eval/vertical/` 参照 17 件と、そこでの「実測 KPI」（`agent_support_verticals.md`） | ✅ 解消（v2.0 で章ごと削除） |
| 3 | `benchmark.md` の所在が `grace/benchmark.py`（実際は `grace/step_trace/benchmark.py`）／CLI `run_benchmark.py` が存在しない | ✅ 解消（v2.0） |
| 4 | `grace_core.md` の行番号参照 13 件（ほぼ全部ズレていた） | ✅ 解消（v2.0 でシンボル名参照へ） |
| 5 | `grace_core.md` §4.5 の `_record_memory` が**修正前のコードのまま** | ✅ 解消（v2.0 で現行実装へ） |
| 6 | 単数形パス `grace/doc/`（CLAUDE.md §9.1 違反） | ✅ 解消（15 件を是正） |
| 7 | `memory.py` の文書が無い | ✅ 解消（`memory.md` v1.0 を新規作成） |
| 8 | `web_search.md`（1123 行）が `tools.py` 内のクラス 1 個だけの単独文書になっている | ✅ 解消（`tools.md` v3.0 へ統合し削除） |
| 9 | `agent_example_core8.md`（385 行）— `agent_example_core8.py` は git 全履歴に存在しない | ✅ 解消（ユーザー承認のうえ削除。参照元 `agent_support_example.md` も是正） |
| 10 | 主要モジュール文書 10 件が、対応するコードの最終更新より古い | ⏳ 未対応（§3・§5 の #3） |

---

## 2. 文書一覧

### 2.1 モジュール単位（IPO 形式・`a_class_method_md_format.md` に準拠）

| 文書 | 対象 | 行数 | Ver | 重要度 |
|---|---|---:|---|---|
| `planner.md` | `grace/planner.py` | 1139 | 3.4 | ★★★ |
| `executor.md` | `grace/executor.py` | 2015 | 4.1 | ★★★ |
| `confidence.md` | `grace/confidence.py` | 1587 | 2.2 | ★★★ |
| `tools.md` | `grace/tools.py`（`WebSearchTool` を含む全ツール） | 1296 | 3.0 | ★★★ |
| `schemas.md` | `grace/schemas.py` | 1125 | 1.2 | ★★★ |
| `config.md` | `grace/config.py` | 920 | 1.1 | ★★★ |
| `llm_compat.md` | `grace/llm_compat.py` | 806 | 1.1 | ★★★ |
| `intervention.md` | `grace/intervention.py` | 1514 | 1.2 | ★★ |
| `replan.md` | `grace/replan.py` | 1064 | 1.5 | ★★ |
| `calibration.md` | `grace/calibration.py` | 763 | 1.0 | ★★ |
| `memory.md` | `grace/memory.py` | 546 | 1.0 | ★★ |
| `benchmark.md` | `grace/step_trace/benchmark.py` | 869 | 2.0 | ★ |

> ✅ **`grace/*.py`（11 モジュール）はすべて対応する `.md` を持つ。** 欠落は無い。

### 2.2 横断・設計文書

| 文書 | 内容 | 行数 | Ver | 重要度 |
|---|---|---:|---|---|
| `grace.md` | GRACE 自律型エージェントの思想・ReAct との関係 | 340 | — | ★★★ |
| `grace_core.md` | コア 8 モジュールの横断アーキテクチャ（§4 に実行メモリの実例） | 948 | 2.0 | ★★★ |
| `grace_core_flow.md` | 5 段階設計・モジュール連携・プロンプト/API 発行部 | 786 | 2.0 | ★★★ |
| `agent_support_example.md` | GRACE-Support 本体の設計書 | 995 | — | ★★★ |
| `agent_support_example_flow.md` | 1 コマンドの実行トレース（IN/OUT データフロー） | 455 | 1.2 | ★★ |
| `agent_support_verticals.md` | 業界特化（gov / saas / ec）の `VerticalProfile` 設計 | 388 | 2.0 | ★★ |
| `confidence_calibration.md` | 信頼度と較正の関係 | 355 | 1.1 | ★★ |

---

## 3. 実装追随状況

対応するコードの最終コミット日と、文書の「最終更新」の比較（2026-09-04 時点）。

| 文書 | コード | 文書 | 差 |
|---|---|---|---|
| `calibration.md` | 2026-08-11 | 2026-06-16 | **約 2 か月** |
| `intervention.md` | 2026-08-11 | 2026-06-16 | **約 2 か月** |
| `replan.md` | 2026-08-17 | 2026-06-16 | **約 2 か月** |
| `confidence.md` | 2026-08-30 | 2026-08-01 | 約 1 か月 |
| `config.md` | 2026-08-30 | 2026-08-01 | 約 1 か月 |
| `tools.md` | 2026-08-30 | 2026-08-01 | 約 1 か月 |
| `executor.md` | 2026-08-29 | 2026-08-01 | 約 1 か月 |
| `schemas.md` | 2026-08-29 | 2026-08-01 | 約 1 か月 |
| `planner.md` | 2026-08-17 | 2026-08-01 | 約半月 |
| `llm_compat.md` | 2026-08-11 | 2026-08-01 | 約 10 日 |
| `memory.md` | 2026-08-17 | 2026-09-04 | ✅ 追随済み |
| `grace_core.md` / `grace_core_flow.md` / `agent_support_verticals.md` / `benchmark.md` | — | 2026-09-04 | ✅ 追随済み |

> ⚠️ **日付の差は「ズレている」ことの証明ではない**（コード側の変更が文書に無関係な場合もある）。
> 差が大きいものから §4 のシンボル網羅チェックを当てて、実際にズレているかを確かめる。

---

## 4. 検証手順

文書を直したら、この 4 つを回す。

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

---

## 5. 残タスク

| # | タスク | 内容 | 状態 |
|---|---|---|---|
| 1 | 追随が遅れている 10 件の突き合わせ | §3 の差が大きいもの（`calibration.md` / `intervention.md` / `replan.md`）から §4.1 を当てる | ⏳ |
| 2 | `tools.md` の未記載シンボル 10 件 | `WebSearchTool`（9/9）と `WebSearchConfig`（12/12）は統合時に網羅したが、AST で当てると **`CodeExecuteTool` クラスごと未記載**であることが分かった。ほかに `RAGSearchTool` の内部 8 件（`_apply_allowed_collections` / `_apply_excluded_collections` / `_apply_limits` / `_collection_dense_dim` / `_embed_query_once` / `_static_check` / `_source_origin` / `clear_collections_cache` / `_now_text`）。※`CodeExecuteTool` は opt-in | ⏳ |
| 3 | `grace.md` / `agent_support_example.md` のバージョン欄 | この 2 件だけ `**Version X.X**` ヘッダーが無い。他と揃える | ⏳ |
| 4 | GRACE-Support 3 点の所在 | `agent_support_example.md` / `_flow.md` / `_verticals.md` は実装（`backend/app/core/support_agent.py`）から遠い。`grace_v2_local` は `backend/docs/` へ移設済み。**移設すると相対リンクが全滅する**ので張り替えとセットで行う | ⏳ |

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
| **grep で見つかる誤りは軽い方** | 深刻なのは**実装を読まないと気づかない**もの: 修正前のコードのままの記述、存在しない実行基盤の「実測値」、丸ごと抜けたパイプライン段。日付やリンクが揃っていても中身が嘘なことがある |
| **姉妹リポジトリからのコピー** | CLAUDE.md §5。`memory.py` は `best_collection(exclude=...)` が grace_v2 にだけある。文書も丸ごとコピーできない |

---

## 7. 変更履歴

| バージョン | 変更内容 |
|-----------|---------|
| 1.1 | `web_search.md` の `tools.md` への統合と `agent_example_core8.md` の削除を反映（問題 #8 / #9 を解消）。文書は 22 → 20 件。統合の副産物として、`tools.md` に **`CodeExecuteTool` クラスごと未記載**であること（AST 照合で 37 件中 10 件が未記載）が判明したため残タスクへ追加 |
| 1.0 | 初版作成。文書 22 件（モジュール 12・横断 9・本書）の一覧、コード最終コミット日との追随比較、検証手順 4 種（AST シンボル網羅・Mermaid 規約・リンク存在・実在しないファイル参照）、残タスク 4 件、grep の落とし穴 7 件を整備 |
