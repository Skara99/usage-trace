package com.example.service;

import com.example.enums.OrderStatus;

@org.springframework.stereotype.Service
public class OrderStatusService {

    /**
     * 支付成功后把订单标为已支付
     */
    public void markPaid(String status) {
        if (status.equals(OrderStatus.PAID.getCode()) || status == OrderStatus.PAID.name()) {
            return;
        }
        apply(OrderStatus.PAID);
    }

    /**
     * 用户取消订单
     */
    public void cancel(OrderStatus status) {
        if (status == OrderStatus.CANCELLED) {
            return;
        }
        apply(OrderStatus.CANCELLED);
    }

    /**
     * 待处理订单进入审核
     */
    public void holdPending(OrderStatus status) {
        switch (status) {
            case PENDING:
                apply(OrderStatus.PENDING);
                break;
            default:
                break;
        }
    }

    private void apply(OrderStatus status) {
        // persist
    }
}
