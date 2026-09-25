# \_\_init\_\_.py - qa_generation パッケージ公開 API ドキュメント

**Version 1.2** | 最終更新: 2026-09-25

---

## 目次

1. [概要](#概要)
2. [アーキテクチャ構成図](#1-アーキテクチャ構成図)
3. [モジュール構成図](#2-モジュール構成図)
4. [import 副作用の実測](#3-import-副作用の実測)
5. [`qa_qdrant/__init__.py` との違い](#4-qa_qdrant__init__py-との違い)
6. [エクスポート](#5-エクスポート)
7. [使用例](#6-使用例)
8. [注意点](#7-注意点)
9. [関連モジュール](#8-関連モジュール)
10. [変更履歴](#9-変更履歴)

---

## 概要

`qa_generation/__init__.py` は、**`qa_generation` パッケージの公開 API を定義する再エクスポート専用モジュール**です。自前のロジックは持たず、4 つのサブモジュールから 11 シンボルを取り込んで `__all__` に並べます。

かつては**この再エクスポートに重い import 副作用があった**（`pipeline.py` が `celery_tasks` をモジュールレベルで import していたため、パッケージ内のどのモジュールを import しても Celery が読み込まれた）。2026-09-24 に `pipeline.py` 側を遅延 import へ移して解消した（[実測](#3-import-副作用の実測)）。

### 主な責務

- モジュール構成をパッケージ docstring として示す
- データモデル 8 クラスを再エクスポートする
- `QAPipeline` / `SemanticCoverage` / `SmartQAGenerator` を再エクスポートする
- `__all__` で公開範囲を明示する

### 各責務対応のモジュール

| # | 責務 | 対応モジュール | 説明 |
|---|---|---|---|
| 1 | モジュール構成をパッケージ docstring として示す | モジュール docstring | サブモジュール 6 件の役割を列挙 |
| 2 | データモデル 8 クラスを再エクスポートする | `from .models import ...` | `QAPair` ほか 8 クラス |
| 3 | `QAPipeline` / `SemanticCoverage` / `SmartQAGenerator` を再エクスポートする | `from .pipeline / .semantic / .smart_qa_generator import ...` | 各 1 クラス |
| 4 | `__all__` で公開範囲を明示する | `__all__` | 11 シンボル |

### 主要機能一覧

| 区分 | 再エクスポートするシンボル | 由来 |
|---|---|---|
| Models | `QAPair` / `QAPairsList` / `ChainOfThoughtAnalysis` / `ChainOfThoughtQAPair` / `ChainOfThoughtResponse` / `EnhancedQAPair` / `EnhancedQAPairsList` / `QAGenerationConsiderations` | `qa_generation/models.py` |
| Pipeline | `QAPipeline` | `qa_generation/pipeline.py` |
| Semantic Coverage | `SemanticCoverage` | `qa_generation/semantic.py` |
| Smart QA Generator | `SmartQAGenerator` | `qa_generation/smart_qa_generator.py` |

---

## 1. アーキテクチャ構成図

### 1.1 システム全体構成

```mermaid
flowchart TB
    subgraph CALLER["呼び出し側"]
        USR["from qa_generation import ...（利用側）"]
    end
    subgraph TARGET["qa_generation/__init__.py"]
        INIT["__init__.py（再エクスポートのみ）"]
    end
    subgraph EXTERNAL["外部（LLM・Embedding・ファイル・基盤）"]
        MOD["models.py"]
        PIPE["pipeline.py"]
        SEM["semantic.py"]
        SMART["smart_qa_generator.py"]
    end
    USR --> INIT
    INIT --> MOD
    INIT --> PIPE
    INIT --> SEM
    INIT --> SMART
classDef default fill:#000,stroke:#fff,color:#fff
classDef subgraphStyle fill:#1a1a1a,stroke:#fff,color:#fff
class USR,INIT,MOD,PIPE,SEM,SMART default
style CALLER fill:#1a1a1a,stroke:#fff,color:#fff
style TARGET fill:#1a1a1a,stroke:#fff,color:#fff
style EXTERNAL fill:#1a1a1a,stroke:#fff,color:#fff
```

### 1.2 データフロー

1. 利用側が `from qa_generation import QAPipeline` のようにパッケージから import する
2. `__init__.py` が 4 つのサブモジュールを import し、11 シンボルを名前空間へ載せる
3. `pipeline.py` は `celery_tasks` を `_generate_with_celery()` の中で遅延 import するため、この時点では Celery は読み込まれない（§3）

---

## 2. モジュール構成図

docstring が示すモジュール構成（実体と一致している）。

| モジュール | 役割 | 文書 |
|---|---|---|
| `models.py` | Pydantic データモデル | [`models.md`](./models.md) |
| `semantic.py` | セマンティック分析・カバレッジ | [`semantic.md`](./semantic.md) |
| `smart_qa_generator.py` | チャンク単位の Q/A 生成 | [`smart_qa_generator.md`](./smart_qa_generator.md) |
| `evaluation.py` | Q/A 評価 | [`evaluation.md`](./evaluation.md) |
| `pipeline.py` | 生成パイプライン | [`pipeline.md`](./pipeline.md) |
| `data_io.py` | データ入出力 | [`data_io.md`](./data_io.md) |

> 📌 **`evaluation` と `data_io` は再エクスポートされない。** docstring には 6 モジュールが
> 並ぶが、`__all__` に載るのは 4 モジュール由来の 11 シンボルだけである。
> `analyze_coverage()` や `load_uploaded_file()` はフルパスで import する。

```mermaid
flowchart TB
    subgraph Pkg["qa_generation パッケージ"]
        Init["__init__.py（再エクスポート）"]
        Models["models.py"]
        Pipe["pipeline.py"]
        Sem["semantic.py"]
        Smart["smart_qa_generator.py"]
        Eval["evaluation.py"]
        IO["data_io.py"]
    end
    subgraph Ext["連鎖して読み込まれる外部"]
        Celery["celery_tasks → celery_config → celery"]
        LLM["helper.helper_llm（Anthropic クライアント）"]
    end
    Init --> Models
    Init --> Pipe
    Init --> Sem
    Init --> Smart
    Pipe -.->|"遅延 import"| Celery
    Pipe --> Eval
    Pipe --> Smart
    Smart --> LLM
    Pipe -.->|"遅延 import"| IO
classDef default fill:#000,stroke:#fff,color:#fff
classDef subgraphStyle fill:#1a1a1a,stroke:#fff,color:#fff
class Init,Models,Pipe,Sem,Smart,Eval,IO,Celery,LLM default
style Pkg fill:#1a1a1a,stroke:#fff,color:#fff
style Ext fill:#1a1a1a,stroke:#fff,color:#fff
```

破線は関数の中で行う遅延 import を表す（`data_io` は `QAPipeline.load_data()` / `save()`、`celery_tasks` は `_generate_with_celery()`）。

---

## 3. import 副作用の実測

**パッケージ内のどのモジュールを import しても `__init__.py` が先に実行される。**
`data_io`（pandas とファイル I/O しか使わないモジュール）で測った値（2026-09-24）。

| 測定 | ロード済みモジュール数 | Celery |
|---|---:|:--:|
| `data_io.py` が実際に必要とする依存だけ（`pandas` / `config` / `helper.helper_rag`） | 1,616 | 読まれない |
| **修正前** `import qa_generation.data_io` | 1,733（+117） | 読まれた |
| **修正後** `import qa_generation.data_io` | **1,623（+7）** | **読まれない** |

修正前に余計に読み込まれていたトップレベルモジュール:

```
amqp, billiard, celery, celery_config, celery_tasks, cffi,
kombu, resource, shelve, tzlocal, vine
```

経路は `__init__.py` → `pipeline.py` → `celery_tasks` → `celery_config` → `celery` 本体だった。
`celery_config` は import 時にログを出すため、**`qa_generation` を触るだけで
Celery のログ（`✅ celery_tasks.pyのインポート成功` など）が出ていた**。
修正後の +7 は `qa_generation` パッケージ自身のサブモジュールである。

> 📌 測定は `uv run --no-sync python -c ...` を**別プロセスで 1 回ずつ**実行した実測値。
> 所要時間はディスクキャッシュの状態で動くので記録していない。モジュール数の差は安定する。

### 3.1 修正（2026-09-24）

`pipeline.py` の `celery_tasks` import を、実際に使う `_generate_with_celery()` の中へ移した。
3 シンボル（`check_celery_workers` / `collect_results` / `submit_unified_qa_generation`）は
このメソッドでしか使っていないので、**Celery を使う経路の動作は変わらない**。
`data_io` / `evaluation` と同じ遅延 import の方針に揃えた形である
（姉妹リポジトリ `grace_v2_local` が 2026-09-21 に行ったものと同じ修正）。

回帰は `backend/tests/test_qa_generation_import_side_effects.py`（3 件）で固定した。
**修正前のコードに当てて 3 件とも fail することを確認済み**。

### 3.2 同時に直した隠れた import 順序依存

`celery_tasks.py` / `celery_config.py` は import 時に **`helper/` ディレクトリを `sys.path` へ挿入**する。
これに頼ってパッケージ名なしの裸 import（`from helper_llm import ...` など）で書かれた
モジュールは、**Celery が先に読まれたときだけ動いていた**。遅延 import 化でこの偶然が無くなるため、
`helper/` 配下の裸 import をすべて `from helper.helper_xxx import ...` へ直した。

| モジュール | 裸 import | 修正前の状態（実測） |
|---|---|---|
| `helper/helper_rag_qa.py` | `helper_embedding` / `helper_llm` | **単体では import できなかった**（`No module named 'helper_embedding'`） |
| `helper/helper_embedding.py` | `helper_embedding_fastembed`（`fastembed` プロバイダ選択時） | `create_embedding_client("fastembed")` が `No module named 'helper_embedding_fastembed'` で失敗し、「fastembed が未導入」と誤ったメッセージを出していた |
| `helper/helper_embedding_fastembed.py` | `helper_embedding` | 同上の連鎖 |
| `helper/helper_api.py` | `helper_llm` | 本番の import 元は無い（後方互換モジュール）。同じ理由で直した |

裸 import が戻らないことは、上のテストの 3 件目（`helper/*.py` を `ast` で走査する静的検査）で固定した。

---

## 4. `qa_qdrant/__init__.py` との違い

姉妹パッケージ `qa_qdrant` の `__init__.py` も似た問題を抱えるが、中身の性質が違うので同じ扱いにはできない。

| 観点 | `qa_qdrant/__init__.py` | `qa_generation/__init__.py`（本モジュール） |
|---|---|---|
| 中身 | `make_qa.py` の**陳腐化したコピー 236 行**（`main()` まで含む。`make_qa.py` は 265 行） | 再エクスポート 65 行 |
| 公開 API | **誰も使っていない**（`from qa_qdrant import` の参照ゼロ・2026-09-24 grep） | `__all__` に 11 件。パッケージの公開 API そのもの |
| いつ実行されるか | `from qa_qdrant.register_to_qdrant import ...`（データ管理タブの ③ Qdrant 登録）のたびに | `qa_generation` 配下の import のたびに |
| 取りうる対処 | docstring のみに置き換えられる（`grace_v2_local` は 2026-09-21 に実施）。**本リポジトリでは未対応** | **空にはできない**（消すと公開 API が消える）。§3.1 の遅延 import で副作用だけを消した |

---

## 5. エクスポート

> 本モジュールは自前のクラス・関数を持たない（再エクスポート専用）ため、「クラス・関数一覧表」と「IPO 詳細」は置かず、本章と §6 の使用例で代える。

| # | シンボル | 由来モジュール | 種別 |
|---:|---|---|---|
| 1 | `QAPair` | `models`（実体は直下 `models.py`。`qa_generation.models` が import して再エクスポート） | Pydantic モデル |
| 2 | `QAPairsList` | `models` | Pydantic モデル |
| 3 | `ChainOfThoughtAnalysis` | `models` | Pydantic モデル |
| 4 | `ChainOfThoughtQAPair` | `models` | Pydantic モデル |
| 5 | `ChainOfThoughtResponse` | `models` | Pydantic モデル |
| 6 | `EnhancedQAPair` | `models` | Pydantic モデル |
| 7 | `EnhancedQAPairsList` | `models` | Pydantic モデル |
| 8 | `QAGenerationConsiderations` | `models` | Pydantic モデル |
| 9 | `SemanticCoverage` | `semantic` | クラス |
| 10 | `SmartQAGenerator` | `smart_qa_generator` | クラス |
| 11 | `QAPipeline` | `pipeline` | クラス |

`__all__` の並びは「Models → Semantic coverage → Smart QA Generator → Pipeline」で、
import 文の並び（Models → Pipeline → Semantic → Smart）とは順序が違うが、
内容は 11 件で一致している。

---

## 6. 使用例

### 6.1 パッケージ経由（公開 API）

```python
from qa_generation import QAPipeline, SmartQAGenerator, SemanticCoverage, QAPair

pipeline = QAPipeline(input_file="output_chunked/cc_news_1per_chunks.csv")
```

### 6.2 再エクスポートされていないものはフルパスで

```python
from qa_generation.data_io import load_uploaded_file, save_results
from qa_generation.evaluation import analyze_coverage
```

### 6.3 Celery が読み込まれるかどうか

**読み込まれない**（2026-09-24 以降）。`__init__.py` は依然として走るが、
`pipeline.py` が `celery_tasks` を遅延 import するようになったため、
`QAPipeline.run(use_celery=True)` を実際に呼ぶまで Celery は載らない。

---

## 7. 注意点

| # | 内容 |
|---|---|
| 1 | **`__init__.py` が公開 API を決めている。** 中身を空にすると `from qa_generation import QAPipeline` が壊れる |
| 2 | ~~import 副作用で Celery が読み込まれる~~ → **解消済み**（2026-09-24・§3）。`pipeline.py` へモジュールレベルの `celery_tasks` import を戻さないこと。`helper/` 配下に裸 import（`from helper_xxx import`）を書かないこと |
| 3 | **`evaluation` / `data_io` は再エクスポートされない。** docstring の 6 モジュールと `__all__` の 4 モジュールを混同しない |
| 4 | **`QAPair` は直下 `models.py` の定義そのもの**（2026-09-25 に一本化）。`from qa_generation import QAPair` と `from models import QAPair` は同じクラスで、難易度は `difficulty_level`。`helper/helper_rag_qa.py` にだけ旧定義（別物）が残る（[`models.md`](./models.md) §3） |
| 5 | **循環 import には今のところなっていない。** サブモジュール側は `qa_generation.xxx` をフルパスで import しており、`from . import` を使っていない |

---

## 8. 関連モジュール

| モジュール | 関係 |
|---|---|
| [`models.md`](./models.md) | 再エクスポートするモデル 8 件の定義元 |
| [`pipeline.md`](./pipeline.md) | `QAPipeline` の定義元。`_generate_with_celery()` の中でだけ `celery_tasks` を読み込む |
| [`semantic.md`](./semantic.md) | `SemanticCoverage` の定義元 |
| [`smart_qa_generator.md`](./smart_qa_generator.md) | `SmartQAGenerator` の定義元 |
| [`data_io.md`](./data_io.md) | 再エクスポートされない入出力モジュール |
| `celery_config.py` / `celery_tasks.py` | かつての import 副作用の到達先。import 時に `helper/` を `sys.path` へ挿入する（§3.2） |

---

## 9. 変更履歴

| Version | 日付 | 内容 |
|---|---|---|
| 1.0 | 2026-09-24 | 初版作成。再エクスポート 11 件を実装（65 行）から起こし、**import 副作用を実測**（`data_io` の依存だけ 1,616 → パッケージ経由 1,733・+117 モジュール、Celery 一式が載る）して記録した。対処案（遅延 import）と、対処時に露見しうる `helper_rag_qa.py` の import 順序依存、`qa_qdrant/__init__.py`（236 行の陳腐化コピー）との違いを整理した。索引 `qa_generation/docs/README.md` §6 の残タスク 1（文書欠落）に対応。再エクスポート専用で IPO 対象を持たないため、一覧表・IPO 詳細の代わりに「エクスポート」「使用例」章を置いた |
| 1.1 | 2026-09-24 | **import 副作用を解消**。`pipeline.py` の `celery_tasks` import を `_generate_with_celery()` 内の遅延 import へ移し、`import qa_generation.data_io` のモジュール数を 1,733 → **1,623** に（Celery は載らない）。あわせて `celery_tasks` の `sys.path` 挿入に依存していた `helper/` 配下の裸 import 4 モジュールを是正（§3.2）。回帰テスト 3 件を追加。§1.2・§2 の図・§6.3・§7・§8 を更新 |
| 1.2 | 2026-09-25 | `QAPair` を直下 `models.py` の定義へ一本化したのに追随し、§5 のエクスポート表と §7 の注意点 4 を更新 |
