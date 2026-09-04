'''Caller identity and per-business access control.

Every owner-facing route takes `business_id` from the URL. Until now nothing
verified that the business existed, let alone that the caller was entitled to
it -- fine for a single-user app on localhost, a data breach once the API is
reachable from the internet.

`require_business_access` is the single choke point. It always loads the
business (so a bad id is a clean 404 instead of a blind write), and when
authentication is enabled it also checks ownership. Identity itself arrives in
Milestone 8: an auth dependency sets `request.state.uid`, and everything here
starts enforcing without any route changing again.
'''
from typing import Optional

from fastapi import Depends, HTTPException, Request

from .config import settings
from ..services.firestore import business_service

# Fields a client may never set on a business through the API.
PROTECTED_BUSINESS_FIELDS = frozenset({'id', 'owner_uid', 'created_at'})


def get_current_uid(request: Request) -> Optional[str]:
    '''The authenticated caller's uid, or None when auth is not enabled.

    Populated by the auth dependency added in Milestone 8; absent until then.
    '''
    return getattr(request.state, 'uid', None)


def require_business_access(
    business_id: str,
    uid: Optional[str] = Depends(get_current_uid),
) -> dict:
    '''Resolve the business in the path, enforcing ownership when known.

    Returns the business document so routes that need it can take it straight
    from the dependency instead of loading it a second time.

    A business the caller does not own is reported as 404, not 403: a 403 would
    confirm that someone else's business id exists.
    '''
    business = business_service.get(business_id)
    if not business:
        raise HTTPException(status_code=404, detail='Business not found.')

    if not settings.METIS_AUTH_ENABLED:
        return business

    owner_uid = business.get('owner_uid')
    if owner_uid and owner_uid != uid:
        raise HTTPException(status_code=404, detail='Business not found.')

    return business


def require_user(uid: Optional[str] = Depends(get_current_uid)) -> Optional[str]:
    '''Demand a signed-in caller, for routes that create ownership.

    Most routes derive their authorisation from the business in the path, but
    POST /business and POST /demo/seed have no business yet -- they mint one.
    Without this, an anonymous caller could keep creating businesses that no
    account owns and that ownership checks would then wave through.
    '''
    if settings.METIS_AUTH_ENABLED and not uid:
        raise HTTPException(status_code=401, detail='Authentication required.')
    return uid


def list_owned_businesses(uid: Optional[str]) -> list[dict]:
    '''Businesses belonging to a caller.

    With auth off there is no identity to filter by, so every business is
    "yours" -- which is exactly right for a single-user local install.
    '''
    if not settings.METIS_AUTH_ENABLED:
        return business_service.list_all()
    if not uid:
        return []
    return business_service.list_all([('owner_uid', '==', uid)])


def get_business_or_404(business_id: str) -> dict:
    '''Existence check only, for the public storefront routes.

    Shoppers are not logged in, so ownership cannot apply here -- but a bogus
    business id should still be a 404 rather than an empty storefront.
    '''
    business = business_service.get(business_id)
    if not business:
        raise HTTPException(status_code=404, detail='Business not found.')
    return business


def strip_protected_fields(data: dict) -> dict:
    '''Drop fields a client is not allowed to set on a business.'''
    return {k: v for k, v in data.items() if k not in PROTECTED_BUSINESS_FIELDS}
