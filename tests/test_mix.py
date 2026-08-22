from projections.mix import mix_bundle, mix_comparable


def test_mix_bundle_sums_price_and_per_gw_xp() -> None:
    eze = {
        "price": 7.5,
        "projections": {"gw2": {"total_xp": 4.0}, "gw3": {"total_xp": 5.0}},
    }
    oreilly = {
        "price": 5.0,
        "projections": {"gw2": {"total_xp": 3.5}, "gw3": {"total_xp": 2.0}},
    }
    bundle = mix_bundle([eze, oreilly], [2, 3])
    assert bundle["price"] == 12.5
    assert bundle["per_gw"] == [7.5, 7.0]
    assert bundle["total"] == 14.5
    assert mix_comparable([eze, oreilly], [{}, {}]) is True
    assert mix_comparable([eze, oreilly], [{}]) is False
