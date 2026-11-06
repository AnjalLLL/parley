package grpc

import (
	"context"
	"testing"

	pb "github.com/AnjalLLL/voxwire/sfu/grpc/proto"
)

func TestCreateAndEndSession(t *testing.T) {
	s := NewServer()
	ctx := context.Background()
	if _, err := s.CreateSession(ctx, &pb.CreateSessionRequest{SessionId: "a"}); err != nil {
		t.Fatal(err)
	}
	old := s.sessions["a"]
	s.CreateSession(ctx, &pb.CreateSessionRequest{SessionId: "a"}) // re-create replaces and closes the old one
	select {
	case <-old.Done():
	default:
		t.Fatal("old session not closed on re-create")
	}
	s.EndSession(ctx, &pb.SessionID{SessionId: "a"})
	if _, ok := s.sessions["a"]; ok {
		t.Fatal("session still present after EndSession")
	}
	s.EndSession(ctx, &pb.SessionID{SessionId: "missing"}) // unknown id is a no-op
}
