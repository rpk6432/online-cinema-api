import stripe
from fastapi import APIRouter, Query, Request, status

from core.dependencies import ActiveUser, DBSession
from core.exceptions import BadRequestError, NotFoundError
from crud.order import order_crud
from crud.payment import payment_crud
from crud.user import user_crud
from models.order import OrderStatusEnum
from models.payment import PaymentStatusEnum
from schemas.common import MessageResponse, PaginatedResponse
from schemas.payments import CheckoutResponse, PaymentListItemResponse
from services.stripe import create_checkout_session, verify_webhook
from tasks.email import send_order_confirmation_email

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    "/{order_id}/checkout",
    status_code=status.HTTP_201_CREATED,
    summary="Checkout",
    responses={
        400: {"description": "Only pending orders can be paid"},
        401: {"description": "Not authenticated"},
        404: {"description": "Order not found"},
    },
)
async def checkout(order_id: int, user: ActiveUser, db: DBSession) -> CheckoutResponse:
    """Create a Stripe Checkout Session for an order."""
    order = await order_crud.get_order(db, order_id, user.id)
    if order is None:
        raise NotFoundError("Order not found")
    if order.status != OrderStatusEnum.PENDING:
        raise BadRequestError("Only pending orders can be paid")

    await payment_crud.cancel_pending_payments(db, order_id)

    session = await create_checkout_session(order)
    payment = await payment_crud.create_payment(
        db, user.id, order_id, order.total_amount, session.id
    )

    return CheckoutResponse(checkout_url=session.url or "", payment_id=payment.id)


@router.post(
    "/webhook",
    summary="Stripe webhook",
    responses={400: {"description": "Invalid signature"}},
)
async def webhook(request: Request, db: DBSession) -> MessageResponse:
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = verify_webhook(payload, sig_header)
    except stripe.SignatureVerificationError:
        raise BadRequestError("Invalid signature") from None

    if event.type == "checkout.session.completed":
        session = event.data.object
        session_id = session.get("id", "") if isinstance(session, dict) else session.id

        payment = await payment_crud.get_payment_by_external_id(db, session_id)
        if payment is not None:
            await payment_crud.update_payment_status(
                db, payment, PaymentStatusEnum.SUCCESSFUL
            )

            order = await order_crud.get_order_by_id(db, payment.order_id)
            if order is not None:
                await order_crud.mark_order_paid(db, order)

                user = await user_crud.get(db, payment.user_id)
                if user is not None:
                    send_order_confirmation_email.delay(
                        user.email,
                        order.id,
                        str(payment.amount),
                    )

    return MessageResponse(detail="Webhook processed")


@router.get(
    "",
    summary="List payments",
    responses={401: {"description": "Not authenticated"}},
)
async def list_payments(
    user: ActiveUser,
    db: DBSession,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[PaymentListItemResponse]:
    """List the current user's payments."""
    offset = (page - 1) * per_page
    payments = await payment_crud.get_user_payments(db, user.id, offset, per_page)
    total = await payment_crud.count_user_payments(db, user.id)

    items = [PaymentListItemResponse.model_validate(p) for p in payments]
    return PaginatedResponse.create(
        items=items, total=total, page=page, per_page=per_page
    )
