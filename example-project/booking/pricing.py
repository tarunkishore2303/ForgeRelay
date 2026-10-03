from decimal import Decimal, ROUND_HALF_UP
from .errors import InvalidRequest
from .models import Quote

def quote(unit_price, seats, *, member=False, coupon=None, tax_bps=825):
    """Money is integer cents; discounts don't stack; tax is on net subtotal."""
    for name, value in [('unit_price',unit_price),('seats',seats),('tax_bps',tax_bps)]:
        if type(value) is not int:
            raise InvalidRequest(f'{name} must be an integer')
    if unit_price < 0 or not 1 <= seats <= 20 or not 0 <= tax_bps <= 10000:
        raise InvalidRequest('pricing arguments outside allowed range')
    if type(member) is not bool:
        raise InvalidRequest('member must be boolean')
    if coupon not in (None,'SAVE15'):
        raise InvalidRequest('unknown coupon')
    subtotal = unit_price * seats
    rate = max(10 if member else 0, 15 if coupon == 'SAVE15' else 0)
    discount = int((Decimal(subtotal)*rate/100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    tax = int((Decimal(subtotal-discount)*tax_bps/10000).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    return Quote(subtotal, discount, tax, subtotal-discount+tax)
