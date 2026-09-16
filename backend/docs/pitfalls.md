# backend の落とし穴 ドキュメント

**Version 1.0** | 最終更新: 2026-09-16

> **本書の位置づけ**: **コードを触る前に読む 1 枚。** 各モジュール文書に散らすと
> 「踏んでから読む」ことになる種類の知識——非自明な設計判断・過去に実際に壊れた箇所・
> 直したくなるが直してはいけない箇所——を集めた。

> **関連ドキュメント**
> - [`architecture.md`](./architecture.md) / [`job_runtime.md`](./job_runtime.md)
> - [`config_and_providers.md`](./config_and_providers.md)
> - `CLAUDE.md` の CRITICAL RULES（R1〜R5）が上位規範

---

## 目次

- [1. Support と Review は部品を共用している](#1-support-と-review-は部品を共用している)
- [2. import の副作用で runner が登録される](#2-import-の副作用で-runner-が登録される)
- [3. ログ転送はスレッドで絞っている](#3-ログ転送はスレッドで絞っている)
- [4. HITL のタイムアウトは「実行しない」](#4-hitl-のタイムアウトは実行しない)
- [5. モデル解決は定数を直接参照しない](#5-モデル解決は定数を直接参照しない)
- [6. Embedding を Anthropic にしない](#6-embedding-を-anthropic-にしない)
- [7. ステップ番号は実行順と一致しない](#7-ステップ番号は実行順と一致しない)
- [8. API スキーマを変えたら types.ts も変える](#8-api-スキーマを変えたら-typests-も変える)
- [9. 直してはいけないもの](#9-直してはいけないもの)
- [10. 変更履歴](#10-変更履歴)

---

## 1. Support と Review は部品を共用している

**Support のつもりで入れた変更が Review を壊す。**

| 共用部品 | 実体 |
|---|---|
| `GroundednessVerifier` | `grace.confidence.create_groundedness_verifier` |
| `InterventionBridge` | `backend/app/core/intervention_bridge.py` |
| `ActionBackend` / 本人確認 | `support_actions.py` |
| ジョブ基盤・SSE | `backend/app/core/jobs.py` |
| キーワード一致・モデル解決 | `gates.py::_match_keyword` / `judge_model`（`review_gates.py` が再利用） |

`backend/tests` の約 1/3（58 ファイル中 18 ファイル）が Review 系である。
**共用部品を触ったら `backend/tests/test_review_*.py` も流す。**

---

## 2. import の副作用で runner が登録される

`review_agent.py` / `data_jobs.py` は **import 時に** `register_runner()` を実行する。

- **消してはいけない**: 「使われていない import」に見えても、消すと
  `_resolve_runner` が `TypeError: 未登録の params 型です` を出す
- **循環 import を作らない**: `jobs.py` から Review / データ準備を import してはいけない。
  この一方向の登録がその回避策である

詳細: [`job_runtime.md` §3](./job_runtime.md)

---

## 3. ログ転送はスレッドで絞っている

`capture_logs()` が付ける `JobLogHandler` は**プロセス全体のロガー**に付く。
そのため 2 つの守りが入っている。**どちらも消すと実測で壊れる。**

| 守り | 消すとどうなるか |
|---|---|
| `record.thread != self._thread_ident` で無視 | 同時実行した別ジョブのログが混ざる |
| ロガー level の参照カウント（`_level_refs`） | 2 本同時実行後、ロガーが INFO のまま復元されない |

また `capture_logs` は**必ず `with` で使う**。外し忘れるとハンドラが積み上がり、
1 行のログが N 回転送される。

---

## 4. HITL のタイムアウトは「実行しない」

`InterventionBridge.resolver()` は時間切れ（既定 300 秒）で
`InterventionResponse(action=CANCEL, timeout_reached=True)` を返す。

- **「返事が無い＝承認」にしない。** 破壊的操作（コレクション削除・アクション実行）が
  無人で走る
- **CLI の自動承認（`AUTO_PROCEED`）を Web 経路に持ち込まない**
- タイムアウトしても**ジョブは失敗しない**。安全側に倒して続行する

---

## 5. モデル解決は定数を直接参照しない

`INTENT_MODEL` / `ModelConfig.DEFAULT_MODEL` を直接使わず、
`judge_model(config)` / `detect_model(config)` を経由する。

過去に `detect_model()` が無かったとき、Review の Detect 33 回がすべて 404 になり、
指摘が全件「自動判定に失敗したため要確認」に落ちた実測がある。
詳細: [`config_and_providers.md` §2](./config_and_providers.md)

---

## 6. Embedding を Anthropic にしない

`RegisterParams.provider` の既定は `"gemini"` で、**これが正しい**。
LLM 用途（Anthropic）と Embedding 用途（Gemini）は別系統である。
変更するとベクトル次元が変わり、**既存 Qdrant コレクションの再作成と全件再登録**が要る。

---

## 7. ステップ番号は実行順と一致しない

`CLAUDE.md` の番号（①〜⑦）は**対応を示す呼称**であって実行順ではない。

| 系統 | 実行順（`*_STEP_IDS`）と番号のずれ |
|---|---|
| Support | `web`（⑤）の**後**に `no_info`（④'）が来る |
| Review | `web`（⑥）の**後**に `severity`（⑤）が来る |

文書やフロントの表示順は `STEP_IDS` / `REVIEW_STEP_IDS` の**定義順**に合わせる。

---

## 8. API スキーマを変えたら types.ts も変える

CI の frontend ゲートは `frontend/src/types.ts` の型エラー 1 個でマージを止める。
Python 側が全部緑でも通らない。対応表は
[`api_contract.md` §6](./api_contract.md)。

---

## 9. 直してはいけないもの

| 見かけ上おかしいもの | 実際は |
|---|---|
| `claude-haiku-4-5`（日付なし） | 実在するエイリアス。チャンク化の既定値 |
| `/api/qdrant/health` が Qdrant 停止中でも 200 | 意図的。画面でエラーを出し分けるため |
| `ConfirmResponse.status = "not_waiting"` が 200 | 意図的。タイムアウト済みの応答は異常ではない |
| `api/review.py` が `api/support.py` とほぼ同じ | 意図的な対称性。共通化するとジョブ種別の差が読めなくなる |
| `config.py::GeminiConfig.DEFAULT_MODEL`（`gemini-2.5-flash`） | **参照ゼロの死にコード**。調査済み・触らなくてよい（`CLAUDE.md` §3.3） |
| `INTENT_MODEL` が残っている | `judge_model()` のフォールバック用（テストスタブ向け） |
| モデル名（`claude-sonnet-4-6` 等） | すべて実在する。マッピングを作らない（`CLAUDE.md` R1） |

---

## 10. 変更履歴

| Version | 日付 | 変更内容 |
|---|---|---|
| 1.0 | 2026-09-16 | 新規作成。各モジュール文書に散っていた非自明な設計判断・過去の事故・「直してはいけないもの」を 1 枚に集約した |
