package main

import (
	"log"
	"net"

	"github.com/AnjalLLL/voxwire/sfu/grpc"
	pb "github.com/AnjalLLL/voxwire/sfu/grpc/proto"
	grpc_lib "google.golang.org/grpc"
)

func main() {
	lis, err := net.Listen("tcp", ":50051")
	if err != nil {
		log.Fatalf("failed to listen: %v", err)
	}
	s := grpc_lib.NewServer()
	
	server := grpc.NewServer()
	pb.RegisterSFUServiceServer(s, server)
	
	log.Println("Pion gRPC server listening on :50051")
	if err := s.Serve(lis); err != nil {
		log.Fatalf("failed to serve: %v", err)
	}
}
