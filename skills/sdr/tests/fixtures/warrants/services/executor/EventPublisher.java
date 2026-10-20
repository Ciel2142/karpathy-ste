package fixture.executor;

import java.util.function.BiConsumer;

public class EventPublisher {
    private static final String TOPIC = "warrant.executions";
    private final BiConsumer<String, ExecutionEvent> bus;

    public EventPublisher(BiConsumer<String, ExecutionEvent> bus) {
        this.bus = bus;
    }

    public void publish(ExecutionEvent event) {
        bus.accept(TOPIC, event);
    }
}
