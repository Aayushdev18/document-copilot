from app.retrieval.fusion import reciprocal_rank_fusion


def test_rrf_prefers_items_ranked_highly_in_both_lists() -> None:
    fused = reciprocal_rank_fusion(
        [
            ["a", "b", "c"],
            ["b", "c", "a"],
        ],
        k=1,
    )
    assert [item_id for item_id, _score in fused] == ["b", "a", "c"]


def test_rrf_keeps_an_item_that_appears_in_only_one_list() -> None:
    fused = reciprocal_rank_fusion([["only"], []], k=60)
    assert fused[0][0] == "only"
    assert fused[0][1] == 1 / 61
