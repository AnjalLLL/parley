package sfu

import (
	"encoding/json"
	"fmt"
	"log"
	"sync"
	"time"

	"ai-call-pion/audio"

	"github.com/pion/webrtc/v3"
	"github.com/pion/webrtc/v3/pkg/media"
)

const frameBytes48k = 960 * 2 // 20ms of 48kHz mono int16, the only frame size we hand to Opus

type Session struct {
	ID             string
	peerConnection *webrtc.PeerConnection
	audioTrack     *webrtc.TrackLocalStaticSample
	pcmInChan      chan []byte // user audio, 16kHz, -> FastAPI
	pcmOutChan     chan []byte // AI audio, 48kHz 20ms frames, -> browser
	done           chan struct{}
	closeOnce      sync.Once
	mu             sync.Mutex
	outBuf         []byte
}

func NewSession(id string) *Session {
	return &Session{
		ID:         id,
		pcmInChan:  make(chan []byte, 100),
		pcmOutChan: make(chan []byte, 50), // 1s; full channel backpressures the gRPC stream
		done:       make(chan struct{}),
	}
}

func (s *Session) ProcessOffer(sdp string) (string, error) {
	if s.peerConnection != nil {
		return "", fmt.Errorf("session %s already has a peer connection", s.ID)
	}
	pc, err := s.NewPeerConnection()
	if err != nil {
		return "", err
	}
	s.peerConnection = pc

	audioTrack, err := webrtc.NewTrackLocalStaticSample(webrtc.RTPCodecCapability{MimeType: webrtc.MimeTypeOpus}, "audio", "pion")
	if err != nil {
		return "", err
	}
	s.audioTrack = audioTrack
	if _, err = pc.AddTrack(audioTrack); err != nil {
		return "", err
	}
	if err = pc.SetRemoteDescription(webrtc.SessionDescription{Type: webrtc.SDPTypeOffer, SDP: sdp}); err != nil {
		return "", err
	}
	answer, err := pc.CreateAnswer(nil)
	if err != nil {
		return "", err
	}
	// Server never trickles its candidates, so wait until they are all in the SDP.
	gathered := webrtc.GatheringCompletePromise(pc)
	if err = pc.SetLocalDescription(answer); err != nil {
		return "", err
	}
	<-gathered

	go s.playbackLoop()
	return pc.LocalDescription().SDP, nil
}

func (s *Session) AddIceCandidate(candidateJSON string) {
	if s.peerConnection == nil {
		log.Printf("ICE candidate before offer for session %s, dropped", s.ID)
		return
	}
	var candidate webrtc.ICECandidateInit
	if err := json.Unmarshal([]byte(candidateJSON), &candidate); err != nil {
		log.Printf("Failed to unmarshal ICE candidate: %v", err)
		return
	}
	if err := s.peerConnection.AddICECandidate(candidate); err != nil {
		log.Printf("Failed to add ICE candidate: %v", err)
	}
}

// PlayAudio takes PCM at any rate, resamples to 48kHz and queues exact 20ms frames.
func (s *Session) PlayAudio(pcmData []byte, sampleRate int) {
	resampler, _ := audio.NewResampler(sampleRate, 48000)
	pcm48, _ := resampler.ResampleReal(pcmData)

	s.mu.Lock()
	s.outBuf = append(s.outBuf, pcm48...)
	var frames [][]byte
	for len(s.outBuf) >= frameBytes48k {
		frames = append(frames, append([]byte(nil), s.outBuf[:frameBytes48k]...))
		s.outBuf = s.outBuf[frameBytes48k:]
	}
	s.mu.Unlock()

	for _, f := range frames {
		select {
		case s.pcmOutChan <- f:
		case <-s.done:
			return
		}
	}
}

// playbackLoop writes one Opus frame every 20ms so the browser gets real-time audio, not bursts.
func (s *Session) playbackLoop() {
	codec := audio.NewRTPCodec()
	ticker := time.NewTicker(audio.OpusFrameDuration)
	defer ticker.Stop()
	for {
		select {
		case <-s.done:
			return
		case <-ticker.C:
		}
		select {
		case frame := <-s.pcmOutChan:
			opus, err := codec.Encode(frame)
			if err != nil {
				log.Printf("Opus encode error: %v", err)
				continue
			}
			s.audioTrack.WriteSample(media.Sample{Data: opus, Duration: audio.OpusFrameDuration})
		default: // nothing to play this tick
		}
	}
}

// PushUserAudio drops audio instead of blocking RTP reading when nobody consumes it.
func (s *Session) PushUserAudio(pcm []byte) {
	select {
	case s.pcmInChan <- pcm:
	case <-s.done:
	default:
	}
}

func (s *Session) GetAudioStream() chan []byte { return s.pcmInChan }

func (s *Session) Done() <-chan struct{} { return s.done }

// Close never closes the data channels: other goroutines may still be sending on them.
func (s *Session) Close() {
	s.closeOnce.Do(func() {
		close(s.done)
		if s.peerConnection != nil {
			s.peerConnection.Close()
		}
	})
}
