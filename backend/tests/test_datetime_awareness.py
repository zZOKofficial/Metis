"""Stored datetimes are timezone-aware, so Firestore and SQLite behave alike.

These pin a class of bug that no other test could catch, because it is
invisible on the store used for local development. Firestore always hands back
timezone-aware values (`DatetimeWithNanoseconds`, UTC) no matter what was
written, while SQLite hands back whatever was serialized. When the app wrote
naive `datetime.utcnow()` values, every comparison between a stored timestamp
and a freshly computed one passed on a laptop and raised

    TypeError: can't compare offset-naive and offset-aware datetimes

on the deployment -- `GET /analytics/{id}/revenue?period=7d` returned 500 in
production and 200 everywhere it was tested.

The fix normalizes at the boundary: writes are aware, and values revived from
an older SQLite file are promoted to aware on read. The tests below therefore
plant an aware `created_at` (exactly what Firestore returns) and require the
code paths that touch it to work.
"""
from datetime import datetime, timedelta, timezone

import pytest

from src.agents.analytics import AnalyticsAgent
from src.core import clock
from src.services import firestore as fs


def test_utcnow_is_timezone_aware():
    assert clock.utcnow().tzinfo is not None
    assert clock.utcnow().utcoffset() == timedelta(0)


def test_as_utc_promotes_naive_and_preserves_aware():
    naive = datetime(2026, 1, 1, 12, 0, 0)
    assert clock.as_utc(naive) == datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    aware = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert clock.as_utc(aware) is not None
    assert clock.as_utc(aware) == aware


def test_created_at_round_trips_as_aware(client):
    """A document written and read back carries an aware timestamp."""
    doc_id = fs.product_service.create({'business_id': 'biz_tz', 'name': 'Mug', 'stock': 1})
    stored = fs.product_service.get(doc_id)
    assert isinstance(stored['created_at'], datetime)
    assert stored['created_at'].tzinfo is not None


def test_legacy_naive_row_is_revived_as_aware():
    """Rows written by an older build come back aware, not naive.

    Without this, an existing `backend/data/metis.db` would keep feeding naive
    values into comparisons that now assume aware ones.
    """
    legacy = fs._load('{"created_at": {"__dt__": "2026-01-01T12:00:00"}}')
    assert legacy['created_at'].tzinfo is not None
    assert legacy['created_at'] == datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize('period', ['today', '7d', '30d'])
def test_revenue_period_filter_survives_aware_timestamps(client, period):
    """The regression itself: an aware `created_at` must not crash the filter.

    This is what Firestore returns for every document, so before the fix this
    raised TypeError for each of these periods on the deployed backend.
    """
    business_id = 'biz_tz_revenue'
    order_id = fs.order_service.create({
        'business_id': business_id,
        'customer_id': 'cust_1',
        'items': [],
        'total_amount': 500.0,
        'status': 'confirmed',
    })
    fs.order_service.update(order_id, {'created_at': datetime.now(timezone.utc)})

    revenue = AnalyticsAgent(business_id).get_revenue(period)
    assert revenue['total_revenue'] == 500.0
    assert revenue['recognized_order_count'] == 1


def test_revenue_period_excludes_older_orders(client):
    """The filter still filters -- an aware cutoff has not made it match everything."""
    business_id = 'biz_tz_old'
    old = fs.order_service.create({
        'business_id': business_id, 'customer_id': 'c', 'items': [],
        'total_amount': 100.0, 'status': 'confirmed',
    })
    fs.order_service.update(old, {'created_at': datetime.now(timezone.utc) - timedelta(days=30)})
    recent = fs.order_service.create({
        'business_id': business_id, 'customer_id': 'c', 'items': [],
        'total_amount': 40.0, 'status': 'confirmed',
    })
    fs.order_service.update(recent, {'created_at': datetime.now(timezone.utc)})

    assert AnalyticsAgent(business_id).get_revenue('7d')['total_revenue'] == 40.0
    assert AnalyticsAgent(business_id).get_revenue('all')['total_revenue'] == 140.0


def test_chat_history_sorts_around_a_message_with_no_timestamp(client):
    """One malformed document must not 500 the whole history.

    The sort fell back to a naive `datetime.min`, which cannot be ordered
    against the aware timestamps on every other message.
    """
    business_id = 'biz_tz_chat'
    fs.chat_service.create({'business_id': business_id, 'role': 'user', 'content': 'second'})
    broken = fs.chat_service.create({'business_id': business_id, 'role': 'user', 'content': 'first'})
    # A document that predates the timestamp field, or was written by hand.
    fs.chat_service.db.collection('chat_messages').document(broken).set(
        {'business_id': business_id, 'role': 'user', 'content': 'first'}
    )

    from src.api.routes import _sorted_chat_history
    ordered = _sorted_chat_history(business_id)
    assert [m['content'] for m in ordered] == ['first', 'second']
