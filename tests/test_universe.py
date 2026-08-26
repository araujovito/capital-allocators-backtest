from capallo.universe import CAPITAL_ALLOCATORS, PASSIVE_ETFS, Region, by_region


def test_dois_allocators_por_regiao():
    for region in Region:
        assert len(by_region(CAPITAL_ALLOCATORS, region)) == 2


def test_um_etf_por_regiao():
    for region in Region:
        assert len(by_region(PASSIVE_ETFS, region)) == 1


def test_etfs_nao_americanos_expoem_moeda_subjacente():
    """O wrapper USD de IEV/EWJ e transparente para a decomposicao cambial."""
    iev, ewj = (a for a in PASSIVE_ETFS if a.ticker in {"IEV", "EWJ"})
    assert iev.listing_currency.value == "USD" and iev.exposure_currency.value == "EUR"
    assert ewj.listing_currency.value == "USD" and ewj.exposure_currency.value == "JPY"
