package shop;

public class Order {
    public enum Status { NEW, PAID, SHIPPED, CANCELLED }

    private String id;
    private long total;
    private Status status = Status.NEW;

    public String id() { return id; }
    public long total() { return total; }
    public Status status() { return status; }
    public void setStatus(Status status) { this.status = status; }
}
