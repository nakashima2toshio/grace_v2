# frontend/docs 棚卸し

**Version 1.6** | 最終更新: 2026-09-23

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
| 1 | `ReviewPanel` / `ReviewForm` / `JobClock` / `MetaErrorBanner` に対応する文書が無い | ✅ 解消（4 件を新規作成。§3） |
| 2 | `SupportPanel.md` §4.1 が**修正前のコード**（`.catch(() => setVerticals([]))`）を載せていた | ✅ 解消（v1.3 で本文を実装へ追随） |
| 3 | `frontend/docs` に索引が無く、欠落を検知できなかった | ✅ 解消（本書） |
| 4 | `review_ui.md` が対応する `.tsx` を持たず、命名規則（`<Component>.md`）から外れている | ✅ 解消（v1.3 で**横断文書**と位置づけを明記） |
| 5 | 6 件の文書でヘッダー日付が実装の最終更新より古い | ✅ 解消（**内容は実装と一致していた**。§3.1） |

---

## 2. 文書一覧

### 2.1 コンテナコンポーネント（状態・副作用・API を束ねる）

| 文書 | 対象 | 実装行数 | 版 | 重要度 |
|---|---|---:|---|:--:|
| `SupportPanel.md` | `components/SupportPanel.tsx` — 基本版 / GRACE-Support 共用 | 192 | 1.6 | ★★★ |
| `DataJobPanel.md` | `components/DataJobPanel.tsx` — データ準備ジョブ 3 種 | 738 | 1.4 | ★★★ |
| `DataPanel.md` | `components/DataPanel.tsx` — データ管理タブの枠 | 107 | 1.3 | ★★ |
| `CollectionPanel.md` | `components/CollectionPanel.tsx` — コレクション管理 | 413 | 1.3 | ★★ |
| `App.md` | `App.tsx` — タブ切替・パネルの振り分け・ヘッダーのモデル選択 | 169 | 1.5 | ★★ |
| `ReviewPanel.md` | `components/ReviewPanel.tsx` — GRACE-Review 本体 | 208 | 1.4 | ★★★ |

### 2.2 入力・モーダル

| 文書 | 対象 | 実装行数 | 版 | 重要度 |
|---|---|---:|---|:--:|
| `QueryForm.md` | `components/QueryForm.tsx` | 272 | 1.5 | ★★★ |
| `ConfirmModal.md` | `components/ConfirmModal.tsx` — HITL アクション承認 | 95 | 1.1 | ★★ |
| `QuestionSelectModal.md` | `components/QuestionSelectModal.tsx` — 0-(A) 主質問の選択 | 76 | 1.0 | ★★ |
| `ReviewForm.md` | `components/ReviewForm.tsx` | 237 | 1.4 | ★★ |
| `ModelSelect.md` | `components/ModelSelect.tsx` — フォーム内のモデルセレクタ（**現在未使用**） | 53 | 1.3 | ★ |

### 2.3 表示コンポーネント

| 文書 | 対象 | 実装行数 | 版 | 重要度 |
|---|---|---:|---|:--:|
| `AnswerCard.md` | `components/AnswerCard.tsx` | 226 | 1.2 | ★★★ |
| `FindingList.md` | `components/FindingList.tsx` | 128 | 1.1 | ★★ |
| `Markdown.md` | `components/Markdown.tsx`（`markdown/parseMarkdown.ts`） | 114 | 1.1 | ★★ |
| `Timeline.md` | `components/Timeline.tsx` | 77 | 1.1 | ★★ |
| `StepTimeline.md` | `components/StepTimeline.tsx` | 45 | 1.1 | ★★ |
| `ReviewTimeline.md` | `components/ReviewTimeline.tsx` | 64 | 1.1 | ★ |
| `DocumentView.md` | `components/DocumentView.tsx` | 49 | 1.1 | ★ |
| `JobClock.md` | `components/JobClock.tsx` — 開始行 / 完了行 | 47 | 1.0 | ★ |
| `MetaErrorBanner.md` | `components/MetaErrorBanner.tsx` — メタ取得失敗の表示 | 24 | 1.0 | ★ |

### 2.4 横断文書

| 文書 | 内容 | 版 | 備考 |
|---|---|---|---|
| `review_ui.md` | GRACE-Review 画面全体の設計を俯瞰する**横断文書** | 1.3 | 対応する `.tsx` は無い。個別仕様は各 `<Component>.md` が正（v1.3 で明記） |

---

## 3. 実装カバレッジ（欠落している文書）

`frontend/src/components/*.tsx` は **19 件**、対応する `<Component>.md` も **19 件**。
**欠落は無い**（2026-09-12 に 4 件、2026-09-16 に 1 件を新規作成）。

| コンポーネント | 文書 | 作成日 |
|---|---|---|
| `ModelSelect.tsx` | `ModelSelect.md` | 2026-09-16 |
| `ReviewPanel.tsx` | `ReviewPanel.md` | 2026-09-12 |
| `ReviewForm.tsx` | `ReviewForm.md` | 2026-09-12 |
| `JobClock.tsx` | `JobClock.md` | 2026-09-12 |
| `MetaErrorBanner.tsx` | `MetaErrorBanner.md` | 2026-09-12 |

> 📌 `main.tsx`（10 行）・`types.ts`（390 行）・`api/client.ts`（287 行）には個別文書が無い。
> `types.ts` はバックエンドのスキーマと 1:1 で `backend/docs/reference/schemas.md` が正、
> `api/client.ts` は各パネル文書の「API 通信」節が実質の記述である。**意図的に持たない。**

### 3.1 ヘッダー日付が遅れていた 6 件 — 内容は一致していた

ヘッダーの「最終更新」が実装の最終コミットより古い文書が 6 件あったため、
**実装と突き合わせて確認した**（2026-09-12）。

| 文書 | 確認したこと | 結果 |
|---|---|---|
| `ConfirmModal.md` / `DocumentView.md` / `FindingList.md` | Props の TS ブロックが実装の逐語コピーか | **一致** |
| `ReviewTimeline.md` / `StepTimeline.md` | export シグネチャ・ステップ数（ともに 9） | **一致** |
| `CollectionPanel.md` | export シグネチャ（props なし） | **一致** |

**内容の修正は不要だった。** 遅れていたのはヘッダーの日付だけで、本文は
同じコミットで更新されていた。検証した事実を残すため版を 1 つ上げ、
変更履歴に「差分が無いことを確認」と記録した。

> 📌 **「日付が古い ＝ 内容も古い」とは限らない。** 逆に `SupportPanel.md` v1.2 は
> **変更履歴だけが新しく本文が古い**（修正前のコードを載せていた）という、
> より危険な状態だった。**日付ではなく本文を実装と突き合わせて判断すること。**

## 4. state/ 純関数の一覧

CLAUDE.md §6 のとおり、**判断ロジックはコンポーネントに残さず `state/` の純関数へ出す**
（vitest は `.test.tsx` を収集しないため、コンポーネント内の分岐はテストできない）。

| モジュール | 行数 | 切り出した判断 |
|---|---:|---|
| `dataReducer.ts` | 225 | データ準備ジョブの状態遷移 |
| `reviewReducer.ts` | 191 | Review ジョブの状態遷移 |
| `dataParams.ts` | 196 | データ準備フォーム → API パラメータ（未選択モデルのキー省略を含む） |
| `elapsed.ts` | 179 | 所要時間の整形・サーバ権威タイムスタンプの採否 |
| `jobReducer.ts` | 173 | Support ジョブの状態遷移 |
| `queryParams.ts` | 127 | 送信ペイロードの組み立て・基本版の vertical 固定・モデル未選択の null 化 |
| `formMemory.ts` | 118 | タブ切替時の入力退避と復元（モデルはヘッダー側が持つので含まない） |
| `headerModel.ts` | 126 | ヘッダーのモデルセレクタ（タブごとのスロット・表示値・選択肢・論理層の注記） |
| `highlight.ts` | 89 | 引用箇所のハイライト |
| `citations.ts` | 76 | 出典の派生値 |
| `useJobTiming.ts` | 56 | **例外的にフック**。判断は持たず `elapsed.ts` に委ねる |
| `modelLabel.ts` | 68 | モデル名の表示文字列（ヘッダー・「（既定値: …）」・単価つき選択肢） |
| `metaFetch.ts` | 53 | メタ取得失敗 → 対処可能な文言 |
| `documentLimit.ts` | 52 | 文字数上限の判定・表示文言・アナウンス文言 |
| `tabKeys.ts` | 49 | タブの矢印キー移動 |
| `submitKey.ts` | 49 | 送信キー（IME 変換中は送信しない） |
| `activeJobs.ts` | 45 | 実行中ジョブの派生値 |
| `timelineAnnounce.ts` | 43 | 支援技術へ読み上げる 1 行 |
| `interventionKind.ts` | 36 | 承認待ちが action か question か |

> `markdown/parseMarkdown.ts`（250 行）も同じ方針の純関数（`Markdown.md` が担当）。

---

## 5. テスト件数（実測）

**2026-09-23 に `cd frontend && npm test` を実行した実測値。記憶で書かないこと。**

```
Test Files  21 passed (21)
     Tests  304 passed (304)
```

| テストファイル | 件数 |
|---|---:|
| `state/dataParams.test.ts` | 35 |
| `state/documentLimit.test.ts` | 10 |
| `state/queryParams.test.ts` | 27 |
| `state/dataReducer.test.ts` | 24 |
| `state/elapsed.test.ts` | 22 |
| `components/ReviewForm.examples.test.ts` | 17 |
| `state/serverTiming.test.ts` | 16 |
| `markdown/parseMarkdown.test.ts` | 16 |
| `state/reviewReducer.test.ts` | 13 |
| `state/formMemory.test.ts` | 13 |
| `state/headerModel.test.ts` | 16 |
| `state/highlight.test.ts` | 13 |
| `state/citations.test.ts` | 13 |
| `state/tabKeys.test.ts` | 12 |
| `state/metaFetch.test.ts` | 10 |
| `state/submitKey.test.ts` | 10 |
| `state/timelineAnnounce.test.ts` | 9 |
| `state/modelLabel.test.ts` | 9 |
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
| 1 | ~~ヘッダー日付が古い 6 件の Props 突き合わせ~~ | ✅ 完了（§3.1・差分なし） |
| 2 | ~~`review_ui.md` の位置づけ直し~~ | ✅ 完了（v1.3） |
| 3 | ~~欠落 4 件の文書作成~~ | ✅ 完了（§3） |
| 4 | ルート `README.md` のスクリーンショット残り 14 枚（`ANTHROPIC_API_KEY` と Qdrant のある環境が必要） | 中 |
| 5 | ~~`ReviewForm` のアクセシビリティ~~ | ✅ 完了（v1.1・`.sr-only` ラベル＋`aria-invalid`＋ライブ領域） |
| 6 | ~~`ReviewPanel` の打ち切り警告に `role` が無い~~ | ✅ 完了（v1.1・`role="alert"`） |
| 7 | ~~`CollectionPanel.tsx` の中止バナーに `role` が無い~~ | ✅ 完了（v1.3・`role="status"`）。**banner 系 9 箇所すべてに role が付いた** |
| 8 | `components/ModelSelect.tsx` が未使用（全タブのモデル選択をヘッダーへ移したため）。削除するか要判断（あわせて `modelLabel.ts` の `formatModelLabel` / `defaultOptionLabel` も未使用） | 低 |

詳細と根拠は [`docs/doc_modernization_todo.md`](../../docs/doc_modernization_todo.md) を参照。

---

## 8. 変更履歴

| 版 | 日付 | 変更内容 |
|---|---|---|
| 1.6 | 2026-09-23 | **データ管理タブもヘッダーでモデルを選ぶ変更に追随。** `App.md` v1.5 / `DataPanel.md` v1.3 / `DataJobPanel.md` v1.4 / `ModelSelect.md` v1.3（**未使用**になった）の版と実装行数を更新。テスト件数を **21 ファイル / 304 件**（実測）へ更新 |
| 1.5 | 2026-09-23 | **モデル選択をヘッダー（`App`）へ移した変更に追随。** `App.md` v1.4 / `SupportPanel.md` v1.6 / `ReviewPanel.md` v1.4 / `QueryForm.md` v1.5 / `ReviewForm.md` v1.4 / `ModelSelect.md` v1.2 の版と実装行数を更新。`state/headerModel.ts` を §4 へ追加し、テスト件数を **21 ファイル / 301 件**（実測）へ更新 |
| 1.4 | 2026-09-16 | **モデルセレクタの追加に追随。** `ModelSelect.md` を新規作成し §2.2 へ追加。`QueryForm.md` v1.3 / `ReviewForm.md` v1.2 の版と実装行数を更新。`state/modelLabel.ts` を §4 へ追加し、テスト件数を **20 ファイル / 288 件**（実測）へ更新 |
| 1.3 | 2026-09-12 | 残タスク 7（`CollectionPanel` の中止バナー）を完了し、**banner 系 9 箇所すべてに `role` が付いた**。あわせて `SupportPanel.md` / `ReviewPanel.md` の「実行中であることが伝わるか ❌」を訂正（`Timeline` の `aria-live` が読み上げており、バナーに足すと二重読み上げになる） |
| 1.2 | 2026-09-12 | **アクセシビリティ改善に追随。** `ReviewForm` v1.1（`.sr-only` ラベル・`aria-invalid`・ライブ領域）と `ReviewPanel` v1.1（`role="alert"`）を反映。`state/documentLimit.ts`（純関数・10 件）を一覧へ追加し、テスト件数を 19 ファイル / 276 件へ更新。残タスクに `CollectionPanel` の同種 1 件を追加 |
| 1.1 | 2026-09-12 | 欠落 4 件（`ReviewPanel` / `ReviewForm` / `JobClock` / `MetaErrorBanner`）を新規作成して解消。ヘッダー日付が遅れていた 6 件を実装と突き合わせ、**差分が無いことを確認**（§3.1）。`review_ui.md` を横断文書として位置づけ直し。残タスクにアクセシビリティの 2 件を追加 |
| 1.0 | 2026-09-12 | 初版作成。文書一覧・実装カバレッジ（欠落 4 件）・state 純関数 16 件・テスト件数（`npm test` の実測 18 ファイル / 266 件）を記載 |
