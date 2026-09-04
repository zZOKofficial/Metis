// Symbols only, mirroring backend/src/core/currency.py — kept local so price
// formatting (<Cash>) never waits on a network round trip. The full list
// with display names is fetched from GET /api/currencies for the picker.
export const DEFAULT_CURRENCY = 'BDT';

const SYMBOLS: Record<string, string> = {
  BDT: '৳', USD: '$', EUR: '€', GBP: '£', INR: '₹', PKR: '₨',
  JPY: '¥', CNY: '¥', AUD: 'A$', CAD: 'C$', AED: 'AED', SAR: 'SAR',
  SGD: 'S$', MYR: 'RM', NGN: '₦', KES: 'KSh', ZAR: 'R', BRL: 'R$',
};

export function getCurrencySymbol(code?: string | null): string {
  const key = (code || DEFAULT_CURRENCY).toUpperCase();
  return SYMBOLS[key] ?? `${key} `;
}
