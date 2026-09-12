# frontend/docs 棚卸し

**Version 1.0** | 最終更新: 2026-09-12

`frontend/`（Vite + React 18 + TypeScript）のドキュメント一覧と、実装への追随状況・
欠落・残タスクをまとめる。

> **なぜ索引が要るか**: `grace/docs/` と `backend/docs/` には棚卸し README があり、
> 実ファイルとの突き合わせができていた。**frontend/docs だけ索引が無かった**ため、
> コンポーネント 4 件の文書欠落（§3）が長期間検知されずに残っていた。
> **新しいコンポーネントを足したら、この表にも行を足すこと。**

> **関連**: [`grace/docs/README.md`](../../grace/docs/README.md) ／
> [`backend/docs/README.md`](../../backend/docs/README.md) ／
> 全体の改修計画は [`docs/doc_modernization_todo.md`](../../docs/doc_modernization_todo.md)

---

## 目次

- [1. 現在わかっている問題](#1-現在わかっている問題)
- [2. 文書一覧](#2-文書一覧)
- [3. 実装カバレッジ（欠落している文書）](#3-実装カバレッジ欠落している文書)
- [4. state/ 純関数の一覧](#4-state-純関数の一覧)
- [5. テスト件数（実測）](#5-テスト件数実測)
- [6. 検証手順](#6-検証手順)
- [7. 残タスク](#7-残タスク)
- [8. 変更履歴](#8-変更履歴)

---

## 1. 現在わかっている問題

| # | 問題 | 状態 |
|---|---|---|
| 1 | `ReviewPanel` / `ReviewForm` / `JobClock` / `MetaErrorBanner` に対応する文書が無い | ⏳ 未対応（§3） |
| 2 | `SupportPanel.md` §4.1 が**修正前のコード**（`.catch(() => setVerticals([]))`）を載せていた | ✅ 解消（v1.3 で本文を実装へ追随） |
| 3 | `frontend/docs` に索引が無く、欠落を検知できなかった | ✅ 解消（本書） |
| 4 | `review_ui.md` が対応する `.tsx` を持たず、命名規則（`<Component>.md`）から外れている | ⏳ 未対応（§7 の #2） |
| 5 | 5 件の文書でヘッダー日付が実装の最終更新より古い | ⏳ 未対応（§7 の #1） |

---

## 2. 文書一覧

### 2.1 コンテナコンポーネント（状態・副作用・API を束ねる）

| 文書 | 対象 | 実装行数 | 版 | 重要度 |
|---|---|---:|---|:--:|
| `SupportPanel.md` | `components/SupportPanel.tsx` — 基本版 / GRACE-Support 共用 | 184 | 1.3 | ★★★ |
| `DataJobPanel.md` | `components/DataJobPanel.tsx` — データ準備ジョブ 3 種 | 736 | 1.2 | ★★★ |
| `DataPanel.md` | `components/DataPanel.tsx` — データ管理タブの枠 | 94 | 1.2 | ★★ |
| `CollectionPanel.md` | `components/CollectionPanel.tsx` — コレクション管理 | 406 | 1.1 | ★★ |
| `App.md` | `App.tsx` — タブ切替とパネルの振り分け | 86 | 1.2 | ★★ |
| — | `components/ReviewPanel.tsx` — GRACE-Review 本体 | 200 | **欠落** | ★★★ |

### 2.2 入力・モーダル

| 文書 | 対象 | 実装行数 | 版 | 重要度 |
|---|---|---:|---|:--:|
| `QueryForm.md` | `components/QueryForm.tsx` | 266 | 1.2 | ★★★ |
| `ConfirmModal.md` | `components/ConfirmModal.tsx` — HITL アクション承認 | 95 | 1.0 | ★★ |
| `QuestionSelectModal.md` | `components/QuestionSelectModal.tsx` — 0-(A) 主質問の選択 | 76 | 1.0 | ★★ |
| — | `components/ReviewForm.tsx` | 210 | **欠落** | ★★ |

### 2.3 表示コンポーネント

| 文書 | 対象 | 実装行数 | 版 | 重要度 |
|---|---|---:|---|:--:|
| `AnswerCard.md` | `components/AnswerCard.tsx` | 226 | 1.2 | ★★★ |
| `FindingList.md` | `components/FindingList.tsx` | 128 | 1.0 | ★★ |
| `Markdown.md` | `components/Markdown.tsx`（`markdown/parseMarkdown.ts`） | 114 | 1.1 | ★★ |
| `Timeline.md` | `components/Timeline.tsx` | 77 | 1.1 | ★★ |
| `StepTimeline.md` | `components/StepTimeline.tsx` | 45 | 1.0 | ★★ |
| `ReviewTimeline.md` | `components/ReviewTimeline.tsx` | 64 | 1.0 | ★ |
| `DocumentView.md` | `components/DocumentView.tsx` | 49 | 1.0 | ★ |
| — | `components/JobClock.tsx` — 開始行 / 完了行 | 47 | **欠落** | ★ |
| — | `components/MetaErrorBanner.tsx` — メタ取得失敗の表示 | 24 | **欠落** | ★ |

### 2.4 横断文書

| 文書 | 内容 | 版 | 備考 |
|---|---|---|---|
| `review_ui.md` | GRACE-Review 画面全体の設計 | 1.2 | 対応する `.tsx` が無い横断文書（§7 の #2） |

---

## 3. 実装カバレッジ（欠落している文書）

`frontend/src/components/*.tsx` は **18 件**、対応する `<Component>.md` は **14 件**。

| コンポーネント | 実装の最終更新 | 欠落の影響 |
|---|---|---|
| `ReviewPanel.tsx` | 2026-09-12 | **Review タブの中核**。`review_ui.md` が部分的に触れるだけで、props・reducer・SSE の記述が無い |
| `ReviewForm.tsx` | 2026-08-20 | 単体テスト `ReviewForm.examples.test.ts`（17 件）は在るが、仕様書が無い |
| `JobClock.tsx` | 2026-08-18 | ルート `README.md` の対応表に 1 行あるのみ |
| `MetaErrorBanner.tsx` | 2026-08-18 | `SupportPanel.md` v1.3 から参照されるが、単体の文書が無い |

> 📌 `main.tsx`（10 行）・`types.ts`（390 行）・`api/client.ts`（287 行）には個別文書が無い。
> `types.ts` はバックエンドのスキーマと 1:1 で `backend/docs/schemas.md` が正、
> `api/client.ts` は各パネル文書の「API 通信」節が実質の記述である。**意図的に持たない。**

---

## 4. state/ 純関数の一覧

CLAUDE.md §6 のとおり、**判断ロジックはコンポーネントに残さず `state/` の純関数へ出す**
（vitest は `.test.tsx` を収集しないため、コンポーネント内の分岐はテストできない）。

| モジュール | 行数 | 切り出した判断 |
|---|---:|---|
| `dataReducer.ts` | 225 | データ準備ジョブの状態遷移 |
| `reviewReducer.ts` | 191 | Review ジョブの状態遷移 |
| `dataParams.ts` | 181 | データ準備フォーム → API パラメータ |
| `elapsed.ts` | 179 | 所要時間の整形・サーバ権威タイムスタンプの採否 |
| `jobReducer.ts` | 173 | Support ジョブの状態遷移 |
| `queryParams.ts` | 123 | 送信ペイロードの組み立て・基本版の vertical 固定 |
| `formMemory.ts` | 113 | タブ切替時の入力退避と復元 |
| `highlight.ts` | 89 | 引用箇所のハイライト |
| `citations.ts` | 76 | 出典の派生値 |
| `useJobTiming.ts` | 56 | **例外的にフック**。判断は持たず `elapsed.ts` に委ねる |
| `metaFetch.ts` | 53 | メタ取得失敗 → 対処可能な文言 |
| `tabKeys.ts` | 49 | タブの矢印キー移動 |
| `submitKey.ts` | 49 | 送信キー（IME 変換中は送信しない） |
| `activeJobs.ts` | 45 | 実行中ジョブの派生値 |
| `timelineAnnounce.ts` | 43 | 支援技術へ読み上げる 1 行 |
| `interventionKind.ts` | 36 | 承認待ちが action か question か |

> `markdown/parseMarkdown.ts`（250 行）も同じ方針の純関数（`Markdown.md` が担当）。

---

## 5. テスト件数（実測）

**2026-09-12 に `cd frontend && npm test` を実行した実測値。記憶で書かないこと。**

```
Test Files  18 passed (18)
     Tests  266 passed (266)
```

| テストファイル | 件数 |
|---|---:|
| `state/dataParams.test.ts` | 34 |
| `state/queryParams.test.ts` | 25 |
| `state/dataReducer.test.ts` | 24 |
| `state/elapsed.test.ts` | 22 |
| `components/ReviewForm.examples.test.ts` | 17 |
| `state/serverTiming.test.ts` | 16 |
| `markdown/parseMarkdown.test.ts` | 16 |
| `state/reviewReducer.test.ts` | 13 |
| `state/formMemory.test.ts` | 13 |
| `state/highlight.test.ts` | 13 |
| `state/citations.test.ts` | 13 |
| `state/tabKeys.test.ts` | 12 |
| `state/metaFetch.test.ts` | 10 |
| `state/submitKey.test.ts` | 10 |
| `state/timelineAnnounce.test.ts` | 9 |
| `state/activeJobs.test.ts` | 8 |
| `state/jobReducer.test.ts` | 7 |
| `state/interventionKind.test.ts` | 4 |

> ⚠️ `serverTiming.test.ts` が検証するのは `elapsed.ts`（`serverTiming.ts` は**存在しない**）。
> ファイル名から実装を推測しないこと。

---

## 6. 検証手順

```bash
cd frontend
npm run lint     # tsc --noEmit
npm test         # vitest run
npm run build    # 本番ビルド
```

3 つとも CI の blocking ゲート（`frontend (tsc + vitest + build)`）に含まれる。
**バックエンドの API スキーマを変えたら `src/types.ts` も必ず追随させる**
（Python 側が全部緑でも型エラー 1 個でマージは止まる）。

---

## 7. 残タスク

| # | 内容 | 優先 |
|---|---|:--:|
| 1 | ヘッダー日付が実装より古い 5 件（`CollectionPanel` / `ConfirmModal` / `DocumentView` / `FindingList` / `ReviewTimeline` / `StepTimeline`）の Props を実装と突き合わせる | 高 |
| 2 | `review_ui.md` を「Review 画面の横断文書」と位置づけ直し、`ReviewPanel.md` / `ReviewForm.md` と役割を分ける | 中 |
| 3 | §3 の欠落 4 件を `a_react_page_md_format.md` に従って作成する | 高 |
| 4 | ルート `README.md` の画像リンク切れ 25 件（`docs/images/`）を撮影して埋める | 高 |

詳細と根拠は [`docs/doc_modernization_todo.md`](../../docs/doc_modernization_todo.md) を参照。

---

## 8. 変更履歴

| 版 | 日付 | 変更内容 |
|---|---|---|
| 1.0 | 2026-09-12 | 初版作成。文書一覧・実装カバレッジ（欠落 4 件）・state 純関数 16 件・テスト件数（`npm test` の実測 18 ファイル / 266 件）を記載 |
