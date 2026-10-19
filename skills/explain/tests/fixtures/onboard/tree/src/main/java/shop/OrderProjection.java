package shop;

public class OrderProjection {
    private final OrderRepository repository;

    public void on(OrderPlacedEvent event) {
        repository.save(repository.find(event.id()));
    }
}
