from .errors import InvalidRequest

def format_cents(value):
    if type(value) is not int:
        raise InvalidRequest
    if value < 0:
        return '-' + format_cents(-value)
    elif value == 0:
        return '0.00'
    else:
        dollars = value // 100
        cents = value % 100
        return f'{dollars}.{cents:02d}'
