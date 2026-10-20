package fixture.orchestrator;

import java.util.function.BiConsumer;

public class LegacyClaimWorkflow {
    private final BiConsumer<String, String> endUser;

    public LegacyClaimWorkflow(BiConsumer<String, String> endUser) {
        this.endUser = endUser;
    }

    public void run(Claim claim) {
        endUser.accept(claim.debtorId(), "Claim " + claim.claimId() + " is accepted");
        endUser.accept(claim.debtorId(), "Claim " + claim.claimId() + " is sent to the executor");
        endUser.accept(claim.debtorId(), "Claim " + claim.claimId() + " is done");
    }
}
