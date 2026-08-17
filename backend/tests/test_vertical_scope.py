# backend/tests/test_vertical_scope.py
"""業界プロファイルの**検索スコープに汎用コーパスを含めない**ことを固定するテスト。

## 背景（実測 2026-08-17 11:39）

gov プロファイルの許可リストに `wikipedia_ja` が残っていた。

    # wikipedia_ja は専用コレクション（gov_faq/gov_laws）登録までの代替
    collections=["gov_faq_anthropic", "gov_laws_anthropic", "wikipedia_ja"]

コメントのとおり暫定措置だったが、`gov_faq_anthropic` / `gov_laws_anthropic` は
既に登録済みで、実測でも gov_faq が 0.8011 でヒットしている。役目は終わっている。

**残しておくと害がある。** `qdrant.excluded_collections`（汎用コーパスの除外）は
「許可リストで名指しされた候補は落とさない」仕様なので、`wikipedia_ja` が
許可リストに居る限り除外を素通りする。つまり自治体の回答に Wikipedia が
**「社内ナレッジ」として**提示されうる。

saas / ec は元から専用コレクションだけなので、gov もそれに揃える。

ここで固定すること:
  1. どのプロファイルの検索スコープにも汎用コーパスが入っていないこと
  2. gov の専用コレクションは維持されていること（スコープを空にしない）
  3. 全プロファイルが `*_anthropic` 命名規約に従っていること
"""
from __future__ import annotations

import pytest

from backend.app.core.verticals import PROFILES
from grace.config import QdrantConfig

# 除外リストの既定（汎用コーパスのキーワード）
GENERIC_CORPORA = QdrantConfig().excluded_collections


class TestNoGenericCorporaInScope:

    @pytest.mark.parametrize("key", sorted(PROFILES))
    def test_profile_scope_excludes_generic_corpora(self, key):
        """⚠️ 許可リストは除外リストより強い。汎用コーパスを書いてはいけない。"""
        offenders = [
            c for c in PROFILES[key].collections
            if any(keyword in c for keyword in GENERIC_CORPORA)
        ]

        assert offenders == [], (
            f"{key} プロファイルの検索スコープに汎用コーパス {offenders} が入っている。"
            "許可リストは excluded_collections の保護対象になるため、"
            "汎用コーパスが「社内ナレッジ」として提示されうる"
        )

    @pytest.mark.parametrize("key", sorted(PROFILES))
    def test_profile_scope_is_not_empty(self, key):
        """スコープを空にしない（空だと全コレクション横断へ落ちる）。"""
        assert PROFILES[key].collections

    @pytest.mark.parametrize("key", sorted(PROFILES))
    def test_collections_follow_the_naming_convention(self, key):
        """命名規約 `*_anthropic`（docs/vertical_test_data.md）。"""
        for collection in PROFILES[key].collections:
            assert collection.endswith("_anthropic"), (
                f"{key}: {collection} が命名規約に従っていない"
            )


class TestGovKeepsItsOwnCollections:

    def test_gov_scope(self):
        """wikipedia_ja を外しても専用コレクションは残っていること。"""
        assert PROFILES["gov"].collections == [
            "gov_faq_anthropic", "gov_laws_anthropic",
        ]

    def test_other_profiles_are_untouched(self):
        assert PROFILES["saas"].collections == [
            "saas_docs_anthropic", "saas_api_anthropic",
        ]
        assert PROFILES["ec"].collections == [
            "ec_policy_anthropic", "ec_faq_anthropic",
        ]
