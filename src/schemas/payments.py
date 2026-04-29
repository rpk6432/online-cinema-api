from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class CheckoutResponse(BaseModel):
    checkout_url: str
    payment_id: int


class PaymentBaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    status: str
    amount: Decimal
    created_at: datetime


class PaymentListItemResponse(PaymentBaseResponse):
    pass


class PaymentResponse(PaymentBaseResponse):
    external_payment_id: str | None
