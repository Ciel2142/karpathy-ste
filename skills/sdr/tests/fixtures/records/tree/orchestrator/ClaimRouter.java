package fixture.orchestrator;

import java.util.Map;
import java.util.Optional;

/** Maps each claim to the one warrant that holds it. */
public class ClaimRouter {
    // Many claims, one warrant: the source system sums every claim of a debtor under a single warrant.
    private final Map<String, String> warrantByClaim;

    public ClaimRouter(Map<String, String> warrantByClaim) {
        this.warrantByClaim = warrantByClaim;
    }

    public Optional<String> warrantOf(String claimId) {
        return Optional.ofNullable(warrantByClaim.get(claimId));
    }
}
