# backend/docs 再編計画 ドキュメント

**Version 3.0** | 最終更新: 2026-09-16

> **本書の位置づけ**: `backend/docs` を「横断 / 系統別 / 参照」の 3 階建てへ
> 作り替える計画と進捗。完了した作業は [`docs_audit.md`](./docs_audit.md) の
> 変更履歴へ、現在の構成は [`README.md`](./README.md) へ落とす。

---

## 目次

- [1. 再編の狙い](#1-再編の狙い)
- [2. Phase 1（完了・2026-09-16）](#2-phase-1完了2026-09-16)
- [3. Phase 2（完了・2026-09-16）系統別文書の統合](#3-phase-2完了2026-09-16系統別文書の統合)
- [4. Phase 3（完了・2026-09-16）参照文書の点検](#4-phase-3完了2026-09-16参照文書の点検)
- [5. 進め方の原則](#5-進め方の原則)
- [6. 変更履歴](#6-変更履歴)

---

## 1. 再編の狙い

再編前の `backend/docs` には、次の 3 つの問題があった。

| # | 問題 | 根拠 |
|---|---|---|
| 1 | **共有基盤の説明が 3 か所に重複していた。** ジョブ・SSE・HITL は Support / Review / データ準備で同一実装なのに、説明が各系統の文書に分散していた | `api/review.py` と `api/data.py` の docstring が自ら「`api/support.py` と構造は同一」と書いている |
| 2 | **`*_spec.md` と `*_flow.md` の 2 本立てが巨大だった。** Support は 155KB、Review は 89KB あり、通読できない | `support_flow.md` 1,622 行 + `support_spec.md` 934 行 |
| 3 | **モジュール文書（17 本）と読み物（設計・フロー）が同じ階層に平置きされ、読む順路が無かった** | `README.md` が棚卸し表 33KB で、入口として機能していなかった |

狙いは **「横断＝ job_runtime / 系統＝ flow / 索引＝ reference」の 3 階建て**にして、
**同じ内容を 2 か所に持たない**こと。複製は必ず腐る（`review_agent_spec.md` が
`rulesets.py` のキーワード表を複製し、15 ルール分の語が欠落した前例がある）。

---

## 2. Phase 1（完了・2026-09-16）

### 2.1 新設した横断文書

| 文書 | 何を集約したか |
|---|---|
| `architecture.md` | 層構造・モジュール責務・**外部境界**（backend が `grace/` `services/` 等へ委ねているもの）・依存の向き |
| `job_runtime.md` | **`jobs.py` / `intervention_bridge.py` / `job_logs.py` の共有基盤を 1 本に集約。** 3 系統の重複説明をここへ寄せる受け皿 |
| `api_contract.md` | 全 23 エンドポイント・SSE ワイヤ形式・ステータス方針・`types.ts` 対応 |
| `config_and_providers.md` | モデル名の 3 本の解決経路・`judge_model()` / `detect_model()`・キーのガード位置 |
| `pitfalls.md` | 非自明な設計判断・過去の事故・**直してはいけないもの** |

### 2.2 構成の変更

- モジュール文書 17 本（`api_*.md` 5 / `core_*.md` 10 / `main.md` / `schemas.md`）を
  **`reference/` へ移動**（`git mv`）。リポジトリ全体の相対リンクを機械的に追随させ、
  **136 の Markdown で壊れリンク 0 を確認**した
- `README.md`（棚卸し 33KB）を **`docs_audit.md`** へ改称し、README を**地図**に作り替えた

### 2.3 Phase 1 で意図的にやらなかったこと

**内容の統合・削除は 1 件も行っていない。** `support_spec.md` 等の大きな文書は
そのまま残っている（Phase 2 で扱う）。Phase 1 は**足す・動かす**だけに限定した。

---

## 3. Phase 2（完了・2026-09-16）系統別文書の統合

**目的**: 系統ごとに 1 本へ寄せ、共有基盤の重複を `job_runtime.md` へ移す。

### 3.0 実施結果

| 変更 | 結果 |
|---|---|
| `support_spec.md`（929 行）→ `support_flow.md` v3.0 | 統合完了。**2,217 行**（旧 flow 1,622 + spec の設計判断） |
| `review_spec.md`（1,080 行）→ `review_flow.md` v2.0 | 統合完了。**1,225 行**（各ステップの直下に `#### 設計仕様` を配置） |
| `verticals_and_rulesets.md` 新設 | `support_spec.md` §6 ＋ `review_spec.md` §5 ＋ 増やし方（§3） |
| `testing.md` 新設 | `review_spec.md` §9 ＋ `backend/tests` の実測地図 |
| `review_spec.md` §6（ジョブ基盤）/ §7.1・§7.2（API）/ §8（フロント） | それぞれ `job_runtime.md` §3 / `api_contract.md` / `frontend/docs/review_ui.md` が既に同内容を持つため**移送せずリンクへ集約** |
| `review_spec.md` §10（実装計画とファイル一覧） | 実装完了済みのため**引き継がない**（git 履歴に残る） |
| 旧 `support_flow.md` §3.2（関数一覧）/ 旧 `review_flow.md` §3（クラス・関数一覧表） | `reference/core_*.md` と 3 重管理だったため**削除してリンクへ置換** |
| リポジトリ全体の参照 | `*_spec.md` を指していた .md / .py の参照 40 ファイルを新しい移送先（節番号つき）へ是正 |

> ⚠️ **訂正**: v1.0 の §3.2 で「`review_flow.md` 515 行目の `## [HIGH]` が見出しレベル 2 で
> 目次を汚している」と書いたが、**これは誤り**だった。当該行は ```` ```markdown ```` の
> **コードフェンス内**にあり、レンダラは見出しとして扱わない（`_build_report()` の出力例そのもの）。
> 直す必要は無かったため、**そのまま残してある**。ただしフェンスを見ない素朴な
> 見出し分割ツールはここで誤って区切るため、統合作業のスクリプトはフェンス対応にした。

### 3.1 Support（`support_flow.md` 1,622 行 + `support_spec.md` 934 行 → 1 本）

| 統合前 | 行 | 統合後の行き先 |
|---|---:|---|
| `support_spec.md` §1 回答ポリシー | 94- | `support_flow.md`「④ 回答ゲート」の節へ（判断の WHY を段の説明に隣接させる） |
| `support_spec.md` §2 HITL ポリシー | 147- | **`job_runtime.md` §4 へ寄せる**（機構は共通。Support 固有の閾値だけ残す） |
| `support_spec.md` §3 データ契約・アクション実行 | 162- | `support_flow.md`「⑥ Action」の節へ |
| `support_spec.md` §4 処理シーケンス | 218- | `support_flow.md` §1・§2 と**重複**。統合先に 1 つ残す |
| `support_spec.md` §5 複数質問 | 265- | `support_flow.md`「0-(A)」の節へ |
| `support_spec.md` §6 業界特化 | 566- | **新設 `verticals_and_rulesets.md` へ**（§3.3） |
| `support_spec.md` §7 基本版タブ | 797- | `support_flow.md`「0-(B)」の節へ |
| `support_spec.md` §8 KPI / §9 ロードマップ | 844- | KPI は統合先の末尾へ。ロードマップは `docs_audit.md` §6 の残タスクへ |
| `support_flow.md` §3 クラス・関数一覧 | 235- | **破棄**（`reference/core_*.md` が正本。3 重管理になっている） |
| `support_flow.md` 付録A CLI / 付録B トレース | 1109- | 維持（実行例は読み物として価値がある） |

### 3.2 Review（`review_flow.md` 663 行 + `review_spec.md` 1,080 行 → 1 本）

| 統合前 | 行き先 |
|---|---|
| `review_spec.md` §1 概要・§2 アーキテクチャ・§3 パイプライン | `review_flow.md` の各段へマージ |
| `review_spec.md` §4 データモデル | `reference/schemas.md` / `reference/core_review_agent.md` へリンクし**本文は持たない** |
| `review_spec.md` §5 RuleSet 定義 | **新設 `verticals_and_rulesets.md` へ**（本文は複製せず `rulesets.py` を指す） |
| `review_spec.md` §6 ジョブ基盤の汎用化 | **`job_runtime.md` §3 へ寄せる**（共有基盤そのもの） |
| `review_spec.md` §7 API 設計 | **`api_contract.md` へ寄せる** |
| `review_spec.md` §8 フロントエンド設計 | `frontend/docs/` へ移送を検討 |
| `review_spec.md` §9 テスト方針 | **新設 `testing.md` へ**（§3.4） |
| `review_spec.md` §10-11 実装計画・未決事項 | `docs_audit.md` §6 の残タスクへ |
| `review_flow.md` §3 クラス・関数一覧 | **破棄**（`reference/` が正本） |

> 📝 `review_flow.md` の `## [HIGH] 最上級表現の根拠不備…` は**コードフェンス内の出力例**であり、
> 見出しではない（§3.0 の訂正を参照）。

### 3.3 新設 `verticals_and_rulesets.md`

`VerticalProfile`（gov / saas / ec）と `RuleSet`（ec_ad・23 ルール）の**カタログ**。

- 載せるもの: プロファイル / ルールセットの一覧、選び方、閾値の意味、増やし方
- **載せないもの**: `RuleItem.description` とキーワードの**本文**。複製すると腐るため
  `backend/app/core/rulesets.py` を正本として指す

### 3.4 新設 `testing.md`

- `backend/tests` の地図（Support 系 / Review 系 / 共有部品 / API）
- `requirements-test.txt` と `uv run --no-sync` が要る理由
- CI 4 ゲートと、**どこを触ったらどれを流すか**
- テスト件数は**実行して実測値**を書く

### 3.5 `webapp_flow.md` の扱い

`run_dev.sh` 起点の end-to-end は、フロント側の関心（描画・状態遷移）と
backend の関心（API 契約）が混ざっている。§6 リクエストライフサイクルは
`architecture.md` §6 と重複するため、**§0 タブ ↔ 文書の対応表**を README へ、
API 部分を `api_contract.md` へ寄せ、残りを `frontend/docs/` へ移すか検討する。

---

## 4. Phase 3（完了・2026-09-16）参照文書の点検

### 4.1 計画は「圧縮」だったが、測ったら前提が成り立たなかった

v1.0 の計画は「`reference/*.md`（約 380KB）は系統別文書と重複する設計説明を持つので、
IPO と索引に絞って薄くする」だった。着手前に**実測した結果、この前提は誤りだった**。

| 検査 | 方法 | 結果 |
|---|---|---|
| 逐語の重複 | 正規化した連続 3 行以上が L1/L2 文書に一致する割合 | **0〜1%**（最大 `core_gates.md` の 13 行 / 1,000 行） |
| 構成の重複 | §1 アーキテクチャ構成図・§2 モジュール構成図 | **重複ではない。** いずれも**モジュール中心**の図で、文書規約 `a_class_method_md_format.md` §1.2 が必須としているもの |
| 公開シンボルの網羅 | AST（`docs_audit.md` §5.1 のスクリプト） | **223 シンボル中 未記載 0** |
| 件数クレームの一致 | `rulesets.py` を実行して計測 | ルール 23 / `always_check` 7 / `web_check` 5 / 法令別 12・6・4・1 — **文書の記載と一致** |

つまり `reference/` が大きいのは重複のせいではなく、**17 モジュール分の IPO がそれだけあるから**である。
削ると規約違反か情報欠落になるため、**圧縮は行わなかった**。

### 4.2 代わりに実施したこと

| 変更 | 理由 |
|---|---|
| 17 文書すべての冒頭に**位置づけと上位文書への導線**を追加（`本書の位置づけ` ブロック） | 3 階建てにしたのに `reference/` から上位へ戻る導線が無く、**リファレンスを入口にした人が設計文書へ辿り着けなかった**。各文書の Version を 1 つ上げ、変更履歴にも記録した |
| 移送で古くなったポインタの是正（`backend/docs/README.md` §1 問題 #N → `docs_audit.md` §1） | Phase 1 で README の中身を `docs_audit.md` へ分離したため、節番号つきの参照が指す先が変わっていた |

### 4.3 残す判断

- **`reference/schemas.md`（38KB）と `api_contract.md` の役割分担は現状のままでよい。**
  前者はフィールド単位の定義、後者はエンドポイント一覧と SSE の契約で、重複していない。
- **`reference/main.md` と `architecture.md` も分担できている。**
  前者は `main.py` の 4 要素（`app` / `load_dotenv` / CORS / ルータ結線）の IPO、
  後者は層構造と外部境界で、図の粒度が違う。

## 5. 進め方の原則

1. **1 Phase = 1 PR。** 移動と内容変更を同じコミットに混ぜない（レビューで差分が読めなくなる）
2. **統合は「削除」ではなく「移送」。** 行き先を本書の表に明記してから動かす
3. **実装の表・定数を文書へ複製しない。** 正本へのリンクに置き換える
4. **リンクは機械的に検証する。** 全 Markdown の相対リンクが解決することを確認する
5. **数値（行数・件数・テスト数）は実測値を書く。** 記憶で書かない

---

## 6. 変更履歴

| Version | 日付 | 変更内容 |
|---|---|---|
| 3.0 | 2026-09-16 | **Phase 3 を実施し、結果（§4）を記録**。計画していた「参照文書の圧縮」は、実測で重複がほぼ無い（0〜1%・シンボル網羅 100%）ことが分かったため**行わず**、代わりに上位文書への導線追加と古いポインタの是正を行った |
| 2.0 | 2026-09-16 | **Phase 2 を実施し、結果（§3.0）を記録**。あわせて v1.0 の `## [HIGH]` に関する記述の誤りを訂正した |
| 1.0 | 2026-09-16 | 新規作成。Phase 1 の完了内容と、Phase 2・3 の節単位の移送計画を記載した |
