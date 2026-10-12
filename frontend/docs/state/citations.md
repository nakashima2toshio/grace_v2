# citations.ts - 出典の解析と表示文言 ドキュメント

**Version 1.0** | 最終更新: 2026-10-12

---

## 目次

- [概要](#概要)
- [1. アーキテクチャ構成図](#1-アーキテクチャ構成図)
- [2. エクスポート一覧](#2-エクスポート一覧)
- [3. 判断の規則](#3-判断の規則)
- [4. テスト](#4-テスト)
- [5. 変更履歴](#5-変更履歴)

---

## 概要

| 項目 | 内容 |
|---|---|
| ファイル | `frontend/src/state/citations.ts`（76 行） |
| 種別 | 純ロジック（表示用の派生値） |
| 利用元 | `components/AnswerCard.tsx`（出典リスト・矛盾の注意書き・エスカレ時の前置き） |
| 対応バックエンド | `backend/app/core/gates.py::_collect_citations`（出典を `[社内] …` / `[Web] …` の接頭辞つき文字列で返す） |

GRACE-Support の回答カードに出す出典と、出典の内訳によって変わる固定文言を決める。
表示文言が「社内」を名乗ってよいかはこの内訳で決まるので、判定規則をコンポーネント側に散らさない
（以前はエスカレ時の固定文言だけが別の規則で、片方だけ直した齟齬が残っていた）。

### 主な責務

- 出典 1 件が Web 由来かを判定し、表示用に接頭辞を落とす
- 出典リスト全体の内訳（社内 / Web / 混在 / なし）を判定する
- エスカレ時の前置きを、内訳に合わせて決める（Web だけなのに「社内ナレッジ」と名乗らない）
- 矛盾検知時の注意書きを、内訳に合わせて決める

### 各責務対応のモジュール

| # | 責務 | 対応モジュール | 説明 |
|---|---|---|---|
| 1 | 1 件の判定と本文 | `isWebCitation` / `citationBody` | `[Web]` で始まれば Web。`[Web]` / `[社内]` と直後の空白を落とす |
| 2 | 内訳 | `citationSourceMix` / `CitationSourceMix` | `[Web]` 以外はすべて社内として数える |
| 3 | エスカレ時の前置き | `escalateReferenceNotice` | 4 分岐。どれにも「方針により有人対応へ引き継ぎます。」が付く |
| 4 | 矛盾の注意書き | `contradictionNotice` | 混在のときだけ「社内ナレッジと Web 情報」と書く |

> 📌 **きっかけ（実測）**: 「明日の東京の天気は？」で社内 RAG が 0 件・出典 9 件がすべて Web だったのに、
> エスカレ時の固定文言が「以下は**社内ナレッジ**に基づく参考情報です」と出た。
> Web の情報を社内ナレッジと偽らない方針（`grace/tools.py` の出典ルール 3）を、LLM の生成文だけでなくアプリの固定文言にも適用する。

---

## 1. アーキテクチャ構成図

### 1.1 位置づけ

```mermaid
flowchart TB
    subgraph Users["利用元コンポーネント"]
        AC["AnswerCard.tsx<br>result.citations"]
    end
    subgraph Mod["state/citations.ts"]
        One["isWebCitation / citationBody"]
        Mix["citationSourceMix"]
        Esc["escalateReferenceNotice"]
        Con["contradictionNotice"]
    end
    subgraph Ext["外部"]
        Be["backend/app/core/gates.py<br>_collect_citations: [社内] / [Web]"]
        Sp["SupportPanel.tsx<br>SSE の result イベント"]
    end
    Be -->|"JobResult.citations"| Sp
    Sp --> AC
    AC --> One
    AC --> Esc
    AC --> Con
    Esc --> Mix
    Con --> Mix
classDef default fill:#000,stroke:#fff,color:#fff
classDef subgraphStyle fill:#1a1a1a,stroke:#fff,color:#fff
class AC,One,Mix,Esc,Con,Be,Sp default
style Users fill:#1a1a1a,stroke:#fff,color:#fff
style Mod fill:#1a1a1a,stroke:#fff,color:#fff
style Ext fill:#1a1a1a,stroke:#fff,color:#fff
```

---

## 2. エクスポート一覧

```ts
export function isWebCitation(text: string): boolean
export function citationBody(text: string): string

export type CitationSourceMix = 'internal' | 'web' | 'mixed' | 'none';
export function citationSourceMix(citations: string[]): CitationSourceMix

export function escalateReferenceNotice(citations: string[]): string
export function contradictionNotice(citations: string[]): string
```

---

## 3. 判断の規則

### 3.1 使用例

`AnswerCard` と同じ使い方。出典の文字列はバックエンドが返す形（`[社内] …` / `[Web] …`）。

```ts
import {
  citationBody, citationSourceMix, contradictionNotice, escalateReferenceNotice, isWebCitation,
} from '../../src/state/citations';

const web = ['[Web] https://example.com/weather', '[Web] https://example.org/forecast'];
const mixed = ['[社内] saas_faq #12', ...web];

console.log(isWebCitation(web[0]), citationBody(web[0]), citationBody(mixed[0]));
console.log(citationSourceMix(web), citationSourceMix(mixed), citationSourceMix([]));
console.log(escalateReferenceNotice(web));   // Web だけ → 社内を名乗らない
console.log(escalateReferenceNotice([]));    // 強制エスカレ（出典ゼロ）
console.log(contradictionNotice(web));       // Web どうしの矛盾
console.log(contradictionNotice(mixed));
```

```text
true https://example.com/weather saas_faq #12
web mixed none
以下は Web 検索結果に基づく参考情報です（社内ナレッジには該当がありませんでした）。方針により有人対応へ引き継ぎます。
以下は参考情報です（出典は取得できていません）。方針により有人対応へ引き継ぎます。
⚠️ 注意: 複数の情報源の間で食い違いの可能性があります。
⚠️ 注意: 社内ナレッジと Web 情報で食い違いの可能性があります。
```

> 📝 **確かめ方（2026-10-12）**: 上の例を esbuild で束ねて node で実行し、出力が一致することを確かめた。

### 3.2 規則

`citationSourceMix(citations)` と、それで決まる 2 つの文言:

| 内訳 | 条件 | `escalateReferenceNotice` の前半 | `contradictionNotice` |
|---|---|---|---|
| `internal` | すべて `[Web]` 以外 | 以下は社内ナレッジに基づく参考情報です。 | 複数の情報源の間で食い違い… |
| `web` | すべて `[Web]` | 以下は Web 検索結果に基づく参考情報です（社内ナレッジには該当がありませんでした）。 | 複数の情報源の間で食い違い… |
| `mixed` | 両方ある | 以下は社内ナレッジと Web 検索結果に基づく参考情報です。 | **社内ナレッジと Web 情報で**食い違い… |
| `none` | 空（強制エスカレ） | 以下は参考情報です（出典は取得できていません）。 | 複数の情報源の間で食い違い… |

- `escalateReferenceNotice` はどの分岐でも末尾に `方針により有人対応へ引き継ぎます。` が付く。
- `contradiction` はバックエンドで Web どうしの矛盾でも立つので、混在のときだけ社内を名乗る。
- `citationBody` は先頭の `[Web]` / `[社内]` と直後の空白だけを落とす（途中の同じ文字列は残す）。

---

## 4. テスト

| テストファイル | 対象 | 件数 | 実行 |
|---|---|---:|---|
| `src/state/citations.test.ts` | 1 件の判定 2 件・内訳 4 件・前置き 5 件・注意書き 2 件 | 13 | `npm test` |

件数は 2026-10-12 に `npx vitest run` で実測した。

---

## 5. 変更履歴

| バージョン | 日付 | 変更内容 |
|---|---|---|
| 1.0 | 2026-10-12 | 新規作成（`a_react_page_md_format.md` §2.4 の軽量構成）。使用例は esbuild + node で実行して確かめた |
