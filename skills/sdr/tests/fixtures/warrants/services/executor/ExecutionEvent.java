package fixture.executor;

import java.math.BigDecimal;

public record ExecutionEvent(String warrantId, Action action, BigDecimal amount, BigDecimal warrantTotal) {
    public enum Action { BLOCKED, UNBLOCKED, CONFISCATED }
}
