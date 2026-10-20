package fixture.executor;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.Map;

public class WarrantCommandListener {
    private final Map<String, BigDecimal> blocked = new HashMap<>();
    private final Map<String, BigDecimal> confiscated = new HashMap<>();
    private final EventPublisher publisher;

    public WarrantCommandListener(EventPublisher publisher) { this.publisher = publisher; }

    public void onCommand(String warrantId, BigDecimal blockTotal, BigDecimal confiscateTotal) {
        BigDecimal blockStep = blockTotal.subtract(blocked.getOrDefault(warrantId, BigDecimal.ZERO));
        BigDecimal confiscateStep = confiscateTotal.subtract(confiscated.getOrDefault(warrantId, BigDecimal.ZERO));
        blocked.put(warrantId, blockTotal);
        confiscated.put(warrantId, confiscateTotal);
        if (blockStep.signum() > 0) {
            block(warrantId, blockStep, blockTotal);
        } else if (blockStep.signum() < 0) {
            unblock(warrantId, blockStep.negate(), blockTotal);
        }
        if (confiscateStep.signum() > 0) {
            confiscate(warrantId, confiscateStep, confiscateTotal);
        }
    }

    private void block(String warrantId, BigDecimal amount, BigDecimal total) {
        publisher.publish(new ExecutionEvent(warrantId, ExecutionEvent.Action.BLOCKED, amount, total));
    }

    private void unblock(String warrantId, BigDecimal amount, BigDecimal total) {
        publisher.publish(new ExecutionEvent(warrantId, ExecutionEvent.Action.UNBLOCKED, amount, total));
    }

    private void confiscate(String warrantId, BigDecimal amount, BigDecimal total) {
        publisher.publish(new ExecutionEvent(warrantId, ExecutionEvent.Action.CONFISCATED, amount, total));
    }
}
