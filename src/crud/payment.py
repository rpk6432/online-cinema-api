from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.payment import Payment, PaymentStatusEnum


class CRUDPayment:
    async def create_payment(
        self,
        db: AsyncSession,
        user_id: int,
        order_id: int,
        amount: Decimal,
        external_payment_id: str,
    ) -> Payment:
        """Create a new payment record."""
        payment = Payment(
            user_id=user_id,
            order_id=order_id,
            amount=amount,
            external_payment_id=external_payment_id,
        )
        db.add(payment)
        await db.commit()
        await db.refresh(payment)
        return payment

    async def get_payment_by_external_id(
        self, db: AsyncSession, external_payment_id: str
    ) -> Payment | None:
        """Find a payment by Stripe session ID."""
        result = await db.execute(
            select(Payment).where(Payment.external_payment_id == external_payment_id)
        )
        return result.scalar_one_or_none()

    async def update_payment_status(
        self, db: AsyncSession, payment: Payment, status: PaymentStatusEnum
    ) -> None:
        """Update payment status."""
        payment.status = status
        await db.commit()

    async def get_user_payments(
        self,
        db: AsyncSession,
        user_id: int,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Payment]:
        """Return paginated list of user's payments."""
        result = await db.execute(
            select(Payment)
            .where(Payment.user_id == user_id)
            .order_by(Payment.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_user_payments(self, db: AsyncSession, user_id: int) -> int:
        """Count user's payments."""
        result = await db.execute(
            select(func.count()).select_from(Payment).where(Payment.user_id == user_id)
        )
        return result.scalar_one()

    async def cancel_pending_payments(self, db: AsyncSession, order_id: int) -> None:
        """Cancel all pending payments for an order."""
        await db.execute(
            update(Payment)
            .where(
                Payment.order_id == order_id,
                Payment.status == PaymentStatusEnum.PENDING,
            )
            .values(status=PaymentStatusEnum.CANCELED)
        )
        await db.commit()


payment_crud = CRUDPayment()
