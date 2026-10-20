package fixture.orchestrator;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.Map;
import java.util.function.Consumer;

public class WarrantMapper {
    public record WarrantCommand(String warrantId, BigDecimal blockTotal, BigDecimal confiscateTotal) {}

    private static final String BULK = "BULK";
    private final Map<String, Claim> claims = new HashMap<>();
    private final Consumer<WarrantCommand> executor;

    public WarrantMapper(Consumer<WarrantCommand> executor) {
        this.executor = executor;
    }

    public String warrantOf(Claim claim) {
        if (BULK.equals(claim.sourceSystem())) {
            return claim.debtorId();
        }
        return claim.claimId();
    }

    public void onClaimChanged(Claim claim) {
        claims.put(claim.claimId(), claim);
        String warrantId = warrantOf(claim);
        BigDecimal blockTotal = total(warrantId, Claim.Action.BLOCK);
        BigDecimal confiscateTotal = total(warrantId, Claim.Action.CONFISCATE);
        executor.accept(new WarrantCommand(warrantId, blockTotal, confiscateTotal));
    }

    private BigDecimal total(String warrantId, Claim.Action action) {
        return claims.values().stream()
                .filter(claim -> warrantOf(claim).equals(warrantId) && claim.action() == action)
                .map(Claim::amount)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
    }
}
