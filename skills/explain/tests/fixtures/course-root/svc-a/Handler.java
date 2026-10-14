package demo;

public class Handler {
    @Listener(queue = "IN_QUEUE")
    public void receive(Message message) {
        Result result = validator.validate(message);
        if (!result.ok()) {
            reject(message, result.reason());
            return;
        }
        sender.send(message);
    }
}
