import os
from pathlib import Path

# 設定（config/grace_config.yml）と実行メモリ（logs/）は相対パスなので、リポジトリ直下で動かす
os.chdir(Path(__file__).resolve().parents[2])

from grace.planner import create_planner

# 1. Planner を作る（config を省略すると get_config()。LLM は計画が要るときだけ呼ぶ）
planner = create_planner()


# 2. 質問の種類によって、計画の作り方が変わる
def main():
    # パターン A：同じ話題でそろえる（おすすめ）
    for query in [
        "Jed York CEOが新しいGMとコーチを探す背景には、どのような経緯がありますか？",  # 通常 → ルールベースの 2 ステップ（LLM なし）
        "その件の経緯を詳しく教えて",  # 曖昧（その＝指示語だけ）→ ask_user で確認する計画
        "最新ニュースを検索して、49ersの新GMとヘッドコーチの人事を教えて",  # Web 検索の指示 → LLM 計画
    ]:
        plan = planner.create_plan(query)
        print(f"{query} -> complexity={plan.complexity}")
        for step in plan.steps:
            print(f"  step{step.step_id}: {step.action} - {step.description}")


if __name__ == "__main__":
    main()
