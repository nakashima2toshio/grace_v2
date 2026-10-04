#!/usr/bin/env python3
"""RAG の検索スコアを実データで測り、しきい値（採用の下限・Web 検索の要否）を確かめる。

## なぜ必要か

GRACE-Support の executor は、RAG の最高スコアで次の 2 つを決める。

| しきい値 | 既定 | 意味 |
|---|---|---|
| `executor.reasoning_min_rag_score` | 0.64 | これ以上の結果だけを推論に使い、出典に載せる（採用の下限） |
| `qdrant.rag_sufficient_score` | 0.64 | これ未満なら Web 検索を差し込む。以上なら LLM の適合性チェックが決める |

0.64 は grace_v2_local で測った値（範囲内 n=12 / 範囲外 n=5）で、サンプルが少ない
（`config/grace_config.yml` のコメント）。Embedding モデルやデータを変えたら測り直す必要がある。

このスクリプトは **LLM を呼ばない**（Gemini Embedding と Qdrant だけ。費用はほぼかからない）。
業界プロファイルごとに「答えがあるはずの質問」と「無いはずの質問」を流し、

- 範囲内の最小スコアと範囲外の最大スコア（その間がしきい値を置ける幅）
- 今のしきい値で、範囲内の質問が「採用されない」「無条件に Web を検索する」件数
- 範囲外の質問が「採用されてしまう」件数（無関係な社内文書を根拠にする）

を出す。結果は `logs/rag_scores/rag_scores_<日時>.json` にも書く。

## 使い方

```bash
# 前提: .env に GOOGLE_API_KEY、Qdrant に実データ（Mac）
python scripts/measure_rag_scores.py

# 質問を足す（CSV: vertical,label,query。label は in / out）
python scripts/measure_rag_scores.py --queries my_queries.csv
```

検索は executor の RAG ツールと同じ下位関数（`qdrant_client_wrapper.search_collection`、
sparse が使えれば hybrid）で、業界プロファイルの許可コレクションをすべて引き、最高スコアを取る。
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 答えがあるはずの質問。画面の例文と、その回答に実際に出てきた社内ナレッジの内容
# （2026-10-04 の Mac の E2E レポート）から作った言い換え。
IN_SCOPE: Dict[str, List[str]] = {
    "gov": [
        "住民票の写しの手数料はいくらですか",
        "コンビニで住民票を取得できますか",
        "住民票を郵送で請求するときの支払い方法は？",
    ],
    "saas": [
        "障害情報はどこで確認できますか",
        "計画メンテナンスはいつ通知されますか",
        "Enterprise プランの稼働率保証は？",
        "サポート窓口の受付時間は？",
    ],
    "ec": [
        "返品できる期限は何日ですか",
        "不良品が届いたらどうすればいいですか",
        "返金はいつされますか",
        "発送前の注文はキャンセルできますか",
    ],
}

# どの業界にも答えが無いはずの質問。加えて、他の業界の例文も「範囲外」として流す
# （例: ec のプロファイルで「住民票の写しの取り方は？」）。
OUT_OF_SCOPE_COMMON: List[str] = [
    "明日の東京の天気を教えてください",
    "今日の日経平均株価は？",
    "カレーの作り方を教えて",
    "おすすめの映画を教えて",
]


def build_queries(screen_examples: Dict[str, str], verticals: List[str]) -> List[Tuple[str, str, str]]:
    """(vertical, label, query) の一覧。画面の例文は自分の業界で in、他の業界で out。"""
    rows: List[Tuple[str, str, str]] = []
    for vertical in verticals:
        if vertical in screen_examples:
            rows.append((vertical, "in", screen_examples[vertical]))
        rows += [(vertical, "in", q) for q in IN_SCOPE.get(vertical, [])]
        rows += [(vertical, "out", q) for q in OUT_OF_SCOPE_COMMON]
        rows += [(vertical, "out", q) for v, q in screen_examples.items() if v != vertical]
    return rows


def load_queries(path: Path) -> List[Tuple[str, str, str]]:
    with path.open(encoding="utf-8") as f:
        rows = [(r["vertical"].strip(), r["label"].strip(), r["query"].strip()) for r in csv.DictReader(f)]
    bad = [r for r in rows if r[1] not in ("in", "out")]
    if bad:
        raise ValueError(f"label は in / out のどちらか: {bad[:3]}")
    return rows


def zone(score: float, adopt: float, sufficient: float) -> str:
    """executor から見たスコアの帯。

    - rejected:  採用されない（0 件扱い → Web へ）
    - forced_web: 採用されるのに、無条件で Web も検索する（adopt ≤ score < sufficient）
    - relevance: 採用され、LLM の適合性チェックが Web の要否を決める
    """
    if score < adopt:
        return "rejected"
    if score < sufficient:
        return "forced_web"
    return "relevance"


def analyze(rows: List[Dict], adopt: float, sufficient: float) -> Dict[str, Dict]:
    """業界ごと（と全体）に、範囲内・範囲外のスコア分布と、今のしきい値での振る舞いを集計する。"""
    groups: Dict[str, List[Dict]] = {"(all)": rows}
    for row in rows:
        groups.setdefault(row["vertical"], []).append(row)

    out: Dict[str, Dict] = {}
    for name, items in groups.items():
        ins = sorted(r["top"] for r in items if r["label"] == "in")
        outs = sorted(r["top"] for r in items if r["label"] == "out")
        entry: Dict[str, object] = {
            "in": {"n": len(ins), "min": _r(ins[0]) if ins else None,
                   "median": _r(statistics.median(ins)) if ins else None, "max": _r(ins[-1]) if ins else None},
            "out": {"n": len(outs), "max": _r(outs[-1]) if outs else None},
            # 範囲内の質問が採用されない／採用されるのに Web も検索する件数
            "in_rejected": sum(zone(s, adopt, sufficient) == "rejected" for s in ins),
            "in_forced_web": sum(zone(s, adopt, sufficient) == "forced_web" for s in ins),
            # 範囲外の質問が採用されてしまう件数（無関係な社内文書を根拠にする）
            "out_adopted": sum(s >= adopt for s in outs),
        }
        if ins and outs:
            entry["margin"] = _r(ins[0] - outs[-1])
            # 範囲内の最小と範囲外の最大の中点（幅が正のときだけ意味がある）
            entry["midpoint"] = _r((ins[0] + outs[-1]) / 2) if ins[0] > outs[-1] else None
        out[name] = entry
    return out


def _r(x: float) -> float:
    return round(float(x), 4)


def measure(rows: List[Tuple[str, str, str]], profiles, qdrant_url: str) -> List[Dict]:
    """各質問を、その業界の許可コレクションすべてで検索して最高スコアを取る。"""
    from qdrant_client import QdrantClient

    from qdrant_client_wrapper import (
        embed_query,
        embed_sparse_query_unified,
        search_collection,
    )

    client = QdrantClient(url=qdrant_url, timeout=30)
    existing = {c.name for c in client.get_collections().collections}
    sparse_ok: Optional[bool] = None
    results: List[Dict] = []
    for vertical, label, query in rows:
        collections = [c for c in profiles[vertical].collections if c in existing]
        if not collections:
            raise SystemExit(f"❌ {vertical} の許可コレクションが Qdrant に無い: {profiles[vertical].collections}")
        vector = embed_query(query)
        sparse = None
        if sparse_ok is not False:
            try:
                sparse = embed_sparse_query_unified(query)
                sparse_ok = True
            except Exception:
                sparse_ok = False      # 取れなければ以降は dense だけ（アプリも同じく倒れる）
        best, best_coll = 0.0, None
        for coll in collections:
            hits = search_collection(client=client, collection_name=coll, query_vector=vector,
                                     sparse_vector=sparse, limit=20)
            top = max((h.get("score", 0.0) for h in hits or []), default=0.0)
            if top > best:
                best, best_coll = top, coll
        results.append({"vertical": vertical, "label": label, "query": query,
                        "top": _r(best), "collection": best_coll})
        print(f"  {vertical:5} {label:3} {best:.4f}  {query}  ({best_coll})")
    client.close()
    print(f"\n検索: {'hybrid（dense + sparse）' if sparse_ok else 'dense のみ（sparse モデルを取得できない）'}")
    return results


def main(argv: Optional[List[str]] = None) -> int:
    from backend.app.core.verticals import PROFILES
    from backend.tests.e2e.cases import support_examples
    from config import QdrantConfig
    from grace.config import get_config

    parser = argparse.ArgumentParser(description="RAG の検索スコアを実データで測る（LLM は呼ばない）")
    parser.add_argument("--queries", type=Path, help="追加の質問 CSV（vertical,label,query）")
    parser.add_argument("--only-file", action="store_true", help="組み込みの質問を使わず --queries だけを流す")
    parser.add_argument("--qdrant-url", default=None, help="既定: config.QdrantConfig.URL")
    parser.add_argument("--out", type=Path, default=None, help="結果 JSON（既定: logs/rag_scores/rag_scores_<日時>.json）")
    args = parser.parse_args(argv)

    cfg = get_config()
    adopt = cfg.executor.reasoning_min_rag_score
    sufficient = cfg.qdrant.rag_sufficient_score
    rows = [] if args.only_file else build_queries(support_examples(), list(PROFILES))
    if args.queries:
        rows += load_queries(args.queries)
    unknown = sorted({v for v, _, _ in rows} - set(PROFILES))
    if unknown:
        raise SystemExit(f"❌ 未知の業界: {unknown}（{sorted(PROFILES)} のどれか）")

    print(f"しきい値: 採用の下限 {adopt} / Web 検索の要否 {sufficient}\n")
    results = measure(rows, PROFILES, args.qdrant_url or QdrantConfig.URL)
    summary = analyze(results, adopt, sufficient)

    print("\n業界   範囲内(n・最小・中央)   範囲外(n・最大)  幅      中点    範囲内:不採用/強制Web  範囲外:採用")
    for name, s in summary.items():
        i, o = s["in"], s["out"]
        print(f"{name:6} {i['n']:2}・{i['min']}・{i['median']}   {o['n']:2}・{o['max']}   "
              f"{s.get('margin')}  {s.get('midpoint')}   {s['in_rejected']}/{s['in_forced_web']}   {s['out_adopted']}")

    path = args.out or ROOT / "logs" / "rag_scores" / f"rag_scores_{datetime.now():%Y%m%d_%H%M%S}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"thresholds": {"reasoning_min_rag_score": adopt, "rag_sufficient_score": sufficient},
                                "summary": summary, "results": results}, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    print(f"\n結果: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
