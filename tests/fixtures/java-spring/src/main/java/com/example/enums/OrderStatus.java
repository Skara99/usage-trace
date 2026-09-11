package com.example.enums;

public enum OrderStatus {
    PAID("PAID", "已支付"),
    CANCELLED("CANCELLED", "已取消"),
    PENDING("PENDING", "待处理");

    private final String code;
    private final String label;

    OrderStatus(String code, String label) {
        this.code = code;
        this.label = label;
    }

    public String getCode() {
        return code;
    }

    public String getLabel() {
        return label;
    }
}
