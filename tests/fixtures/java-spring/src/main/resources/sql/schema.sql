CREATE TABLE `t_order` (
  `id` bigint NOT NULL,
  `order_no` varchar(64),
  `store_no` varchar(32),
  `status` varchar(16),
  PRIMARY KEY (`id`)
);
