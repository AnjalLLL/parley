package grpc

import (
	"context"
	"io"
	"sync"

	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	"ai-call-pion/sfu"
	pb "ai-call-pion/grpc/proto" // This assumes the generated code is here
)

type Server struct {
	pb.UnimplementedSFUServiceServer
	mu       sync.RWMutex
	sessions map[string]*sfu.Session
}

func NewServer() *Server {
	return &Server{
		sessions: make(map[string]*sfu.Session),
	}
}

func (s *Server) CreateSession(ctx context.Context, req *pb.CreateSessionRequest) (*pb.CreateSessionResponse, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if old, ok := s.sessions[req.SessionId]; ok {
		old.Close()
	}
	s.sessions[req.SessionId] = sfu.NewSession(req.SessionId)

	return &pb.CreateSessionResponse{SessionId: req.SessionId}, nil
}

func (s *Server) ProcessOffer(ctx context.Context, req *pb.OfferRequest) (*pb.AnswerResponse, error) {
	s.mu.RLock()
	session, ok := s.sessions[req.SessionId]
	s.mu.RUnlock()

	if !ok {
		return nil, status.Errorf(codes.NotFound, "session %s not found", req.SessionId)
	}

	answer, err := session.ProcessOffer(req.Sdp)
	if err != nil {
		return nil, err
	}

	return &pb.AnswerResponse{Sdp: answer}, nil
}

func (s *Server) AddIceCandidate(ctx context.Context, req *pb.IceCandidateRequest) (*pb.Empty, error) {
	s.mu.RLock()
	session, ok := s.sessions[req.SessionId]
	s.mu.RUnlock()

	if ok {
		session.AddIceCandidate(req.CandidateJson)
	}
	return &pb.Empty{}, nil
}

func (s *Server) StreamAudioToPion(stream pb.SFUService_StreamAudioToPionServer) error {
	for {
		chunk, err := stream.Recv()
		if err == io.EOF {
			return stream.SendAndClose(&pb.Empty{})
		}
		if err != nil {
			return err
		}

		s.mu.RLock()
		session, ok := s.sessions[chunk.SessionId]
		s.mu.RUnlock()

		if ok {
			session.PlayAudio(chunk.PcmData, int(chunk.SampleRate))
		}
	}
}

func (s *Server) StreamAudioFromPion(req *pb.SessionID, stream pb.SFUService_StreamAudioFromPionServer) error {
	s.mu.RLock()
	session, ok := s.sessions[req.SessionId]
	s.mu.RUnlock()

	if !ok {
		return status.Errorf(codes.NotFound, "session %s not found", req.SessionId)
	}

	pcmChan := session.GetAudioStream()
	for {
		select {
		case <-session.Done():
			return nil
		case <-stream.Context().Done():
			return nil
		case pcm := <-pcmChan:
			err := stream.Send(&pb.AudioChunk{SessionId: req.SessionId, PcmData: pcm, SampleRate: 16000})
			if err != nil {
				return err
			}
		}
	}
}

func (s *Server) EndSession(ctx context.Context, req *pb.SessionID) (*pb.Empty, error) {
	s.mu.Lock()
	session, ok := s.sessions[req.SessionId]
	delete(s.sessions, req.SessionId)
	s.mu.Unlock()

	if ok {
		session.Close()
	}
	return &pb.Empty{}, nil
}
