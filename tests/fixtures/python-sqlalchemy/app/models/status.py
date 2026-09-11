from enum import Enum


class OrderStatus(Enum):
    PAID = "paid"
    CANCELLED = "cancelled"
    PENDING = "pending"
