"""Per-business currency: field default/round-trip, symbol lookup, and the
curated /api/currencies list."""
from src.core.currency import currency_symbol, CURRENCIES, DEFAULT_CURRENCY


def test_default_currency_is_bdt():
    assert DEFAULT_CURRENCY == 'BDT'


def test_currency_symbol_known_code():
    assert currency_symbol('USD') == '$'
    assert currency_symbol('bdt') == '৳'  # case-insensitive


def test_currency_symbol_falls_back_for_missing_or_unknown_code():
    assert currency_symbol('') == '৳'  # missing -> default (BDT)
    assert currency_symbol('XYZ') == 'XYZ '  # unknown -> code itself


def test_business_defaults_to_bdt(client):
    business_id = client.post('/api/business', json={'name': 'No Currency Given'}).json()['id']
    business = client.get(f'/api/business/{business_id}').json()
    assert business['currency'] == 'BDT'


def test_business_currency_round_trips(client):
    business_id = client.post('/api/business', json={'name': 'US Shop', 'currency': 'USD'}).json()['id']
    business = client.get(f'/api/business/{business_id}').json()
    assert business['currency'] == 'USD'


def test_list_currencies_endpoint(client):
    resp = client.get('/api/currencies')
    assert resp.status_code == 200
    body = resp.json()
    assert body['default'] == 'BDT'
    codes = {c['code'] for c in body['currencies']}
    assert {'BDT', 'USD', 'EUR', 'INR'} <= codes
    assert len(body['currencies']) == len(CURRENCIES)


def test_agent_get_currency_symbol_reads_the_business_record(client):
    from src.agents.registry import get_agent
    from src.models.schemas import AgentType

    usd_business = client.post('/api/business', json={'name': 'US Shop', 'currency': 'USD'}).json()['id']
    bdt_business = client.post('/api/business', json={'name': 'BD Shop'}).json()['id']

    assert get_agent(AgentType.SALES, usd_business).get_currency_symbol() == '$'
    assert get_agent(AgentType.ANALYTICS, bdt_business).get_currency_symbol() == '৳'
