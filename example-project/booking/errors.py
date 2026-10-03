class BookingError(Exception):
    pass

class NotFound(BookingError):
    pass

class InvalidRequest(BookingError):
    pass

class SoldOut(BookingError):
    pass

class Conflict(BookingError):
    pass
