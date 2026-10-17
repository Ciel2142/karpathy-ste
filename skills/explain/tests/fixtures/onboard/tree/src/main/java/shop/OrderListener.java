package shop;

import org.springframework.kafka.annotation.KafkaListener;

public class OrderListener {
    private final OrderRepository repository;

    public OrderListener(OrderRepository repository) {
        this.repository = repository;
    }

    @KafkaListener(topics = "orders.cancel")
    public void onCancel(String id) {
        Order order = repository.find(id);
        if (order.status() == Order.Status.SHIPPED) {
            return;
        }
        order.setStatus(Order.Status.CANCELLED);
        repository.save(order);
    }
}
