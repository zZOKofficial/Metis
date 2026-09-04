"""Query filters are evaluated by the store, not by scanning the collection.

`list_all()` used to stream every document in a collection and filter in
Python. On Firestore that reads (and bills for) every other tenant's documents
to answer one shop's product list, so the filters are now pushed into the
query. These tests pin both the results and the fact that the work happens in
SQL.
"""
import pytest

from src.services import firestore as fs


@pytest.fixture()
def seeded(client, tmp_path):
    """Two tenants sharing the `products` collection."""
    for i in range(3):
        fs.product_service.create(
            {'business_id': 'biz_A', 'name': f'A{i}', 'stock': i, 'category': 'comics'}
        )
    fs.product_service.create(
        {'business_id': 'biz_A', 'name': 'A-toy', 'stock': 4, 'category': 'toys'}
    )
    for i in range(2):
        fs.product_service.create(
            {'business_id': 'biz_B', 'name': f'B{i}', 'stock': 5, 'category': 'comics'}
        )
    return client


def _names(rows):
    return sorted(r['name'] for r in rows)


def test_equality_filter_isolates_tenants(seeded):
    assert _names(fs.product_service.list_all([('business_id', '==', 'biz_A')])) == [
        'A-toy', 'A0', 'A1', 'A2',
    ]
    assert _names(fs.product_service.list_all([('business_id', '==', 'biz_B')])) == ['B0', 'B1']


def test_unfiltered_list_still_returns_everything(seeded):
    assert len(fs.product_service.list_all()) == 6


def test_greater_than_excludes_zero_and_missing(seeded):
    rows = fs.product_service.list_all([('business_id', '==', 'biz_A'), ('stock', '>', 0)])
    assert _names(rows) == ['A-toy', 'A1', 'A2']  # A0 has stock 0


def test_multiple_equality_filters_compose(seeded):
    rows = fs.product_service.list_all([
        ('business_id', '==', 'biz_A'),
        ('category', '==', 'comics'),
        ('stock', '>', 0),
    ])
    assert _names(rows) == ['A1', 'A2']


def test_rows_carry_their_document_id(seeded):
    rows = fs.product_service.list_all([('business_id', '==', 'biz_A')])
    assert all(r.get('id') for r in rows)


def test_no_match_returns_empty(seeded):
    assert fs.product_service.list_all([('business_id', '==', 'nobody')]) == []


# --- push-down mechanics -----------------------------------------------------

def test_scalar_filters_are_pushable_but_datetimes_are_not():
    from datetime import datetime
    assert fs._can_push('business_id', '==', 'x')
    assert fs._can_push('stock', '>', 0)
    assert fs._can_push('stock', '>=', 1)
    # Datetimes are stored as {__dt__: ...} wrappers and would not compare
    # correctly inside the store, so they must fall back to Python.
    assert not fs._can_push('created_at', '>', datetime(2020, 1, 1))
    # Unsupported operator, and a field name that is not a plain identifier.
    assert not fs._can_push('stock', '!=', 1)
    assert not fs._can_push("a'; drop table metis_store; --", '==', 'x')


def test_unpushable_filter_still_filters_in_python(seeded):
    """A filter the store cannot evaluate must not silently return everything."""
    from datetime import datetime, timedelta
    future = datetime.utcnow() + timedelta(days=1)
    past = datetime.utcnow() - timedelta(days=1)

    # created_at is a datetime, so this filter cannot be pushed down -- it has
    # to be applied in Python after the (pushed-down) business_id filter.
    assert fs.product_service.list_all([
        ('business_id', '==', 'biz_A'),
        ('created_at', '>', future),
    ]) == []
    assert _names(fs.product_service.list_all([
        ('business_id', '==', 'biz_A'),
        ('created_at', '>', past),
    ])) == ['A-toy', 'A0', 'A1', 'A2']


def test_unknown_operator_raises_instead_of_matching_everything():
    with pytest.raises(ValueError, match='unsupported filter operator'):
        fs._matches({'stock': 1}, [('stock', 'array-contains', 1)])


def test_missing_field_never_matches_a_comparison():
    assert not fs._matches({}, [('stock', '>', 0)])
    assert not fs._matches({}, [('business_id', '==', 'biz_A')])
    # Mismatched types must not blow up the query.
    assert not fs._matches({'stock': 'lots'}, [('stock', '>', 0)])


def test_business_filter_uses_the_index_rather_than_scanning(seeded):
    conn = fs.get_db()._connect()
    try:
        plan = conn.execute(
            "EXPLAIN QUERY PLAN SELECT doc_id, data FROM metis_store "
            "WHERE collection = ? AND json_extract(data, '$.business_id') = ?",
            ('products', 'biz_A'),
        ).fetchall()
    finally:
        conn.close()
    detail = ' '.join(str(row[-1]) for row in plan)
    assert 'idx_metis_store_business' in detail, detail
    assert 'SCAN' not in detail, detail
