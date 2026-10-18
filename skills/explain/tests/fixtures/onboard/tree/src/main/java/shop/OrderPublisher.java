package shop;

public class OrderPublisher {
    private final ApplicationEventPublisher events;

    public void placed(Order order) {
        events.publishEvent(new OrderPlacedEvent(order.id(), order.total()));
    }
}
