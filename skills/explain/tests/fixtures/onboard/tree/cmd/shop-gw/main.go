package main

import (
	"context"
	"net/http"
	"time"
)

func main() {
	ctx := context.Background()
	r := gin.Default()
	r.GET("/health", health)
	http.HandleFunc("/metrics", metrics)
	go consumer.Consume(ctx, handle)
	ticker := time.NewTicker(time.Minute)
	defer ticker.Stop()
	pb.RegisterShopServer(grpcServer, &shopServer{})
	r.Run(":8080")
}
