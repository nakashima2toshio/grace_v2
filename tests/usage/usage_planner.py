import os
from pathlib import Path

# 実行メモリ（logs/grace_memory.jsonl）は相対パスなので、リポジトリ直下で動かす
# （設定 config/grace_config.yml は作業ディレクトリに関係なく読まれる）
os.chdir(Path(__file__).resolve().parents[2])

from backend.app.core.question_refiner import Aspect, Sentence, Topic  # noqa: E402
from grace.planner import create_planner  # noqa: E402

# 1. Planner を作る（config を省略すると get_config()。下の 2 つの経路は LLM を呼ばない）
planner = create_planner()


def show(title, plan):
    print(f"{title} -> complexity={plan.complexity}")
    for step in plan.steps:
        extra = f"（Web 検索語: {step.web_query}）" if step.web_query else ""
        required = "・必ず実行" if step.required else ""
        print(f"  step{step.step_id}: {step.action} - {step.description}{extra}{required}")


def main():
    # パターン A：画面と同じ。0-(A) が整理した話題から、観点ごとに計画する（create_plan_for_topic）。
    # 本番では refine_question()（LLM）が作る Topic を、ここでは手で書いて渡す。
    topic = Topic(
        answer_question="49ers の Jed York CEO が新しい GM とヘッドコーチを探す背景の経緯と、新 GM・ヘッドコーチの人事を教えて",
        sentences=[
            Sentence(text="Jed York CEOが新しいGMとコーチを探す背景には、どのような経緯がありますか？",
                     aspect="経緯", relation="主"),
            Sentence(text="その件の経緯を詳しく教えて", aspect="経緯", relation="同一"),
            Sentence(text="最新ニュースを検索して、49ersの新GMとヘッドコーチの人事を教えて",
                     aspect="人事", relation="別観点"),
        ],
        aspects=[
            Aspect(name="経緯", search_query="Jed York CEO が新しい GM とコーチを探す背景の経緯",
                   web_query="Jed York GM コーチ 経緯", wants_latest_web=False),
            Aspect(name="人事", search_query="49ers の新 GM とヘッドコーチの人事",
                   web_query="49ers GM ヘッドコーチ 人事", wants_latest_web=True),
        ],
    )
    show("[A] create_plan_for_topic", planner.create_plan_for_topic(topic))

    # パターン B：リプラン以外の create_plan。ルールベースの 2 ステップ（rag_search → reasoning）。
    # LLM 計画になるのは context_hints（リプラン）があるか planner.force_llm_plan が真のときだけ。
    show("[B] create_plan", planner.create_plan("その件の経緯を詳しく教えて"))


if __name__ == "__main__":
    main()
