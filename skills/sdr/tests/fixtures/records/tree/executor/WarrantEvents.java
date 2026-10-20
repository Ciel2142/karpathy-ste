package fixture.executor;

import java.math.BigDecimal;
import java.util.function.BiConsumer;

/** Publishes the warrant actions. Each event carries the warrant total and no claim id. */
public class WarrantEvents {
    private final BiConsumer<String, Object> bus;

    public WarrantEvents(BiConsumer<String, Object> bus) {
        this.bus = bus;
    }

    public void block(String warrantId, BigDecimal total) { bus.accept("warrant.blocked", total); }

    public void unblock(String warrantId, BigDecimal total) { bus.accept("warrant.unblocked", total); }

    public void confiscate(String warrantId, BigDecimal total) { bus.accept("warrant.confiscated", total); }
}
