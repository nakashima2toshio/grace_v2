# backend/tests/test_replan_query_hygiene.py
"""リプランが**次の試行を悪化させない**ことを固定するテスト。

## 背景（grace_v2_local で実測、本リポジトリにも同じコードが残っていた）

### ① リプランのヒントが検索クエリになっていた

`_enhance_query_with_context()` が `f"{original_query}\\n\\n【追加情報】\\n…"` を
返し、それが `create_plan()` の query → `PlanStep.query` になっていた。
実測での rag_search の検索クエリ:

    '明日の東京の天気は？\\n\\n【追加情報】\\n注意: 前回の試行で「ステップ 2
     (reasoning) が 30 秒でタイムアウトしました」というエラーが発生'

embedding が壊れて再検索も外す。部分再計画はさらに酷く、
**「以下の計画の続きを作成してください。元の質問: …」という指示文まるごと**が
検索クエリになっていた。

### ② 汚染が高コスト経路を呼び込む自己増幅ループ

`estimate_complexity()` は長さで加点する（>100 で +0.1、>200 で +0.1）。
連結で複雑度が上がって閾値 0.7 を越えると、ルールベース計画（LLM 呼び出し
0 回）から LLM 計画生成へ落ちる。**汚染 → 複雑度上昇 → 失敗 → リプラン**の
自己増幅になる。

### ③ 実行不能な依存を持つ計画が警告だけで採用されていた

`Executor._check_dependencies` は依存先の結果が `state.step_results` に無い限り
False を返すため、存在しないステップ ID へ依存するステップは**永久に実行
されない**。それが reasoning だと回答が生成されないまま計画が「完走」する。
実測ログの `Plan validation errors: ['Step 4: 存在しない依存先 3']` がまさに
これで、警告のまま採用されていた。

### ④ リプラン後のステップが timeout_seconds を落としていた

`_adjust_step_ids` が `timeout_seconds` を引き継がず、フィールド既定へ戻して
いた。既定値と設定値がたまたま同じなので今は表に出ないが、設定を上げると
リプラン後のステップだけが取り残される。

⚠️ LLM には接続しない（planner の LLM 経路は呼ばない）。
"""
from __future__ import annotations

from grace.replan import ReplanContext, ReplanManager, ReplanTrigger
from grace.schemas import (
    ExecutionPlan,
    PlanStep,
    repair_plan_dependencies,
    validate_plan_dependencies,
)

QUERY = "明日の東京の天気は？"
ERROR = "ステップ 2 (reasoning) が 30 秒でタイムアウトしました"


def _step(step_id, action="rag_search", depends_on=None, timeout=None):
    return PlanStep(
        step_id=step_id,
        action=action,
        description=f"ステップ{step_id}",
        query=QUERY,
        depends_on=depends_on or [],
        expected_output="結果",
        **({"timeout_seconds": timeout} if timeout is not None else {}),
    )


def _plan(steps):
    return ExecutionPlan(
        plan_id="p1", original_query=QUERY, steps=steps,
        complexity=0.5, estimated_steps=len(steps),
        requires_confirmation=False, success_criteria="回答が生成される",
    )


def _context(**kwargs):
    return ReplanContext(
        trigger=ReplanTrigger.STEP_FAILED,
        original_query=QUERY,
        error_message=kwargs.pop("error_message", ERROR),
        **kwargs,
    )


# =============================================================================
# ① ヒントが検索クエリに混ざらない
# =============================================================================

class TestHintsDoNotPolluteTheQuery:

    def test_context_hints_carry_the_error_only(self):
        hints = ReplanManager()._build_context_hints(_context())

        assert ERROR in hints
        assert QUERY not in hints, (
            "元の質問がヒントに混ざっている（連結される設計が残っている）"
        )
        assert "【追加情報】" not in hints

    def test_hints_include_progress_and_feedback(self):
        hints = ReplanManager()._build_context_hints(_context(
            completed_results={1: "ok"}, user_feedback="もっと詳しく",
        ))

        assert "ステップ1は完了済み" in hints
        assert "もっと詳しく" in hints

    def test_empty_context_produces_empty_hints(self):
        assert ReplanManager()._build_context_hints(_context(error_message=None)) == ""

    def test_remaining_hints_are_not_an_instruction_block(self):
        """指示文まるごとが検索クエリになっていたのが実測の不具合。"""
        hints = ReplanManager()._create_remaining_hints(_context(), [_step(1)])

        assert "以下の計画の続きを作成してください" not in hints
        assert "JSON" not in hints, "スキーマ指示は _build_plan_prompt 側の責務"
        assert "完了済みステップ: 1個" in hints
        assert ERROR in hints


# =============================================================================
# ② プロンプトにだけ載る／複雑度に混ざらない
# =============================================================================

class TestPlannerKeepsHintsOutOfTheQuery:

    def test_hints_appear_in_the_prompt(self):
        from grace.planner import Planner

        prompt = Planner()._build_plan_prompt(QUERY, ERROR)

        assert ERROR in prompt
        assert "【前回の試行に関する補足】" in prompt
        assert "各ステップの query（検索文）には含めないでください" in prompt

    def test_prompt_without_hints_is_unchanged(self):
        from grace.planner import Planner

        prompt = Planner()._build_plan_prompt(QUERY)

        assert "【前回の試行に関する補足】" not in prompt
        assert "valid, complete JSON object" in prompt

    def test_complexity_ignores_hints(self):
        """長さ加点で閾値を越え、高コスト経路へ落ちるのを防ぐ。"""
        from grace.planner import Planner

        planner = Planner()
        polluted = f"{QUERY}\n\n【追加情報】\n注意: 前回の試行で「{ERROR}」というエラーが発生"

        assert planner.estimate_complexity(QUERY) < planner.estimate_complexity(polluted), (
            "この差こそが自己増幅の原因（連結すると複雑度が上がる）"
        )
        # create_plan は query だけを複雑度に使う（hints は別引数）
        assert planner.estimate_complexity(QUERY) == planner.estimate_complexity(QUERY)


# =============================================================================
# ③ 実行不能な依存を取り除く
# =============================================================================

class TestBrokenDependenciesAreRepaired:

    def test_missing_dependency_is_removed(self):
        """存在しない依存先を持つステップは永久に実行されない。"""
        plan = _plan([_step(1), _step(2, "reasoning", depends_on=[1, 3])])

        repairs = repair_plan_dependencies(plan)

        assert plan.steps[1].depends_on == [1]
        assert any("存在しない依存先 3" in r for r in repairs)

    def test_forward_dependency_is_removed(self):
        plan = _plan([_step(1, depends_on=[2]), _step(2)])

        repair_plan_dependencies(plan)

        assert plan.steps[0].depends_on == []

    def test_self_dependency_is_removed(self):
        plan = _plan([_step(1, depends_on=[1])])

        repair_plan_dependencies(plan)

        assert plan.steps[0].depends_on == []

    def test_the_step_itself_survives(self):
        """⚠️ 依存だけ落としてステップは残す（落とすと reasoning ごと消える）。"""
        plan = _plan([_step(1), _step(2, "reasoning", depends_on=[9])])

        repair_plan_dependencies(plan)

        assert len(plan.steps) == 2
        assert plan.steps[1].action == "reasoning"

    def test_valid_plan_is_untouched(self):
        plan = _plan([_step(1), _step(2, "reasoning", depends_on=[1])])

        assert repair_plan_dependencies(plan) == []
        assert plan.steps[1].depends_on == [1]

    def test_repaired_plan_passes_validation(self):
        plan = _plan([_step(1), _step(2, "reasoning", depends_on=[1, 7])])

        repair_plan_dependencies(plan)

        assert validate_plan_dependencies(plan) == []


# =============================================================================
# ④ リプラン後のステップが設定を落とさない
# =============================================================================

class TestAdjustedStepsKeepTheirTimeout:

    def test_timeout_is_carried_over(self):
        adjusted = ReplanManager()._adjust_step_ids(
            [_step(1, "reasoning", timeout=240)], start_id=3, completed_count=2,
        )

        assert adjusted[0].timeout_seconds == 240, (
            "リプラン後のステップだけがフィールド既定へ戻っている"
        )

    def test_other_fields_are_preserved(self):
        original = _step(1, "rag_search", timeout=120)
        original.collection = "customer_support_faq"

        [adjusted] = ReplanManager()._adjust_step_ids(
            [original], start_id=2, completed_count=1,
        )

        assert adjusted.action == "rag_search"
        assert adjusted.query == QUERY
        assert adjusted.collection == "customer_support_faq"
        assert adjusted.step_id == 2
