from dataclasses import dataclass

@dataclass(frozen=True)
class Quote:
    subtotal: int
    discount: int
    tax: int
    total: int

@dataclass(frozen=True)
class Reservation:
    id: str
    event_id: str
    customer_id: str
    seats: int
    total: int
    status: str
    created_at: str

    @classmethod
    def from_row(cls, row):
        return cls(**{field: row[field] for field in cls.__dataclass_fields__})
