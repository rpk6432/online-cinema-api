from typing import Any

import stripe

from core.config import settings
from models.order import Order

stripe.api_key = settings.stripe_secret_key


async def create_checkout_session(order: Order) -> stripe.checkout.Session:
    """Create a Stripe Checkout Session for the given order."""
    line_items: list[dict[str, Any]] = [
        {
            "price_data": {
                "currency": "usd",
                "product_data": {"name": item.movie.name},
                "unit_amount": int(item.price_at_order * 100),
            },
            "quantity": 1,
        }
        for item in order.items
    ]

    return await stripe.checkout.Session.create_async(
        payment_method_types=["card"],
        line_items=line_items,  # type: ignore[arg-type]  # Stripe SDK typing gap
        mode="payment",
        success_url=settings.stripe_success_url,
        cancel_url=settings.stripe_cancel_url,
        metadata={"order_id": str(order.id)},
    )


def verify_webhook(payload: bytes, sig_header: str) -> stripe.Event:
    """Verify and construct a Stripe webhook event."""
    event: stripe.Event = stripe.Webhook.construct_event(  # type: ignore[no-untyped-call]  # Stripe SDK untyped
        payload, sig_header, settings.stripe_webhook_secret
    )
    return event
