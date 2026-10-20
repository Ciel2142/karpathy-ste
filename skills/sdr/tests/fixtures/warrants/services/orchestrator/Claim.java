package fixture.orchestrator;

import java.math.BigDecimal;

public record Claim(String claimId, String sourceSystem, String debtorId, Action action, BigDecimal amount) {
    public enum Action { BLOCK, SET_ALLOWANCE, UNBLOCK, CONFISCATE }
}
