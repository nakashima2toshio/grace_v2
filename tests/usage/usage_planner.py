from grace.planner import create_planner

# 1. Planner を作る（config を省略すると get_config()。LLM は計画が要るときだけ呼ぶ）
planner = create_planner()


# 2. 質問の種類によって、計画の作り方が変わる
def main():
    for query in [
        "『金色夜叉』の作者は誰ですか？",  # 通常 → ルールベースの 2 ステップ（LLM なし）
        "あの件について教えて",  # 曖昧（指示語だけ）→ ask_user で確認する計画
        "最新ニュースを検索して、生成AIの動向を教えて",  # Web 検索の指示 → LLM 計画
    ]:
        plan = planner.create_plan(query)
        print(f"{query} -> complexity={plan.complexity}")
        for step in plan.steps:
            print(f"  step{step.step_id}: {step.action} - {step.description}")


if __name__ == "__main__":
    main()
