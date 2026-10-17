package shop;

public class ReportQuery {
    private static final Table ORDERS = Table.named("orders");

    public Query open() {
        return Query.select(COLUMNS).from(ORDERS).where(OPEN);
    }
}
