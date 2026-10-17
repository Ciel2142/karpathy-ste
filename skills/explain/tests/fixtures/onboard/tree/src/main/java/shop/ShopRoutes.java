package shop;

import org.apache.camel.builder.RouteBuilder;

public class ShopRoutes extends RouteBuilder {
    @Override
    public void configure() {
        from("jms:queue:shop.in")
            .to("log:shop.in");
    }
}
