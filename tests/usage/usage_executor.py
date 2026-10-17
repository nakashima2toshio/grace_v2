import os
from pathlib import Path

# 設定（config/grace_config.yml）と実行メモリ（logs/）は相対パスなので、リポジトリ直下で動かす
os.chdir(Path(__file__).resolve().parents[2])

from grace.executor import create_executor  # noqa: E402
from grace.planner import create_planner  # noqa: E402


def main():
    # 1. Planner と Executor を 1 回だけ作る（LLM=Anthropic Claude、Embedding=Gemini）
    #    ⚠️ create_executor の第 1 引数は config（GraceConfig）。計画（plan）を渡すと
    #    AttributeError: 'ExecutionPlan' object has no attribute 'tools' で落ちる
    planner = create_planner()
    executor = create_executor()

    # パターン A：同じ話題でそろえる（おすすめ）
    for query in [
        "Jed York CEOが新しいGMとコーチを探す背景には、どのような経緯がありますか？",  # 通常 → ルールベースの 2 ステップ（LLM なし）
        "その件の経緯を詳しく教えて",  # 曖昧（その＝指示語だけ）→ ask_user で確認する計画
        "最新ニュースを検索して、49ersの新GMとヘッドコーチの人事を教えて",  # Web 検索の指示 → LLM 計画
    ]:
        # 2. 計画を作る
        plan = planner.create_plan(query)
        print(f"{query} -> complexity={plan.complexity}")
        for step in plan.steps:
            print(f"  step{step.step_id}: {step.action} - {step.description}")

        # 3. 計画を実行（ブロッキング版）
        result = executor.execute_plan(plan)

        # 4. 結果を確認（ExecutionResult）。質問ごとに出す
        print(f"  ステータス: {result.overall_status}")  # success / partial / failed / cancelled
        print(f"  信頼度: {result.overall_confidence:.2f}")
        print(f"  回答: {result.final_answer}")
        print(f"  実行時間: {result.total_execution_time_ms}ms")
        print()


if __name__ == "__main__":
    main()
