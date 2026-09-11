from app.models.status import OrderStatus


class StatusService:
    def mark_paid(self, status: str):
        """支付成功后标记已支付"""
        if status == OrderStatus.PAID.value:
            return OrderStatus.PAID
        return status

    def cancel(self, status: OrderStatus):
        """用户取消订单"""
        if status is OrderStatus.CANCELLED:
            return status
        return OrderStatus.CANCELLED
