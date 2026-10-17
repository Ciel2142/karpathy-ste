package shop;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/orders")
public class OrderController {
    private static final long LIMIT = 10_000;
    private final OrderRepository repository;
    private final PaymentsClient payments;
    private final KafkaTemplate<String, String> kafka;

    @PostMapping
    public ResponseEntity<String> create(@RequestBody Order order) {
        if (order.total() > LIMIT) {
            return ResponseEntity.badRequest().body("over the limit");
        }
        payments.charge(order);
        repository.save(order);
        kafka.send("orders.created", order.id());
        return ResponseEntity.accepted().body(order.id());
    }

    @GetMapping("/{id}")
    public Order find(@PathVariable String id) {
        return repository.find(id);
    }

    @RequestMapping(method = RequestMethod.DELETE, path = "/{id}")
    public void remove(@PathVariable String id) {
        repository.delete(id);
    }
}
