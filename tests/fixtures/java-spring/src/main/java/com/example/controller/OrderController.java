package com.example.controller;

import com.example.service.OrderService;

@org.springframework.web.bind.annotation.RestController
@org.springframework.web.bind.annotation.RequestMapping("/api/orders")
public class OrderController {
    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    /**
     * 按门店查询订单
     */
    @org.springframework.web.bind.annotation.GetMapping
    public Object queryByStoreNo(String storeNo) {
        return orderService.findByStoreNo(storeNo);
    }
}
