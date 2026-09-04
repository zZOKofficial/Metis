"""Curated currency list and symbol lookup.

Each business picks one currency at setup; every prompt/response METIS builds
uses that business's symbol. There is no FX conversion — a business only
ever deals in its own currency, so this is display-only.
"""

DEFAULT_CURRENCY = 'BDT'

CURRENCIES: list[dict[str, str]] = [
    {'code': 'BDT', 'symbol': '৳', 'name': 'Bangladeshi Taka'},
    {'code': 'USD', 'symbol': '$', 'name': 'US Dollar'},
    {'code': 'EUR', 'symbol': '€', 'name': 'Euro'},
    {'code': 'GBP', 'symbol': '£', 'name': 'British Pound'},
    {'code': 'INR', 'symbol': '₹', 'name': 'Indian Rupee'},
    {'code': 'PKR', 'symbol': '₨', 'name': 'Pakistani Rupee'},
    {'code': 'JPY', 'symbol': '¥', 'name': 'Japanese Yen'},
    {'code': 'CNY', 'symbol': '¥', 'name': 'Chinese Yuan'},
    {'code': 'AUD', 'symbol': 'A$', 'name': 'Australian Dollar'},
    {'code': 'CAD', 'symbol': 'C$', 'name': 'Canadian Dollar'},
    {'code': 'AED', 'symbol': 'AED', 'name': 'UAE Dirham'},
    {'code': 'SAR', 'symbol': 'SAR', 'name': 'Saudi Riyal'},
    {'code': 'SGD', 'symbol': 'S$', 'name': 'Singapore Dollar'},
    {'code': 'MYR', 'symbol': 'RM', 'name': 'Malaysian Ringgit'},
    {'code': 'NGN', 'symbol': '₦', 'name': 'Nigerian Naira'},
    {'code': 'KES', 'symbol': 'KSh', 'name': 'Kenyan Shilling'},
    {'code': 'ZAR', 'symbol': 'R', 'name': 'South African Rand'},
    {'code': 'BRL', 'symbol': 'R$', 'name': 'Brazilian Real'},
]

_SYMBOLS: dict[str, str] = {c['code']: c['symbol'] for c in CURRENCIES}


def currency_symbol(code: str) -> str:
    """Display symbol for a currency code.

    Falls back to `DEFAULT_CURRENCY` for an empty/missing code (older
    businesses created before this field existed), and to the code itself
    for one outside the curated list.
    """
    key = (code or DEFAULT_CURRENCY).upper()
    return _SYMBOLS.get(key, key + ' ')
