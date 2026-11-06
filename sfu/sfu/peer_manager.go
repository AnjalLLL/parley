package sfu

import (
	"os"

	"github.com/pion/webrtc/v3"
)

func (s *Session) NewPeerConnection() (*webrtc.PeerConnection, error) {
	// Docker only publishes UDP 5000-5100, and container IPs are unreachable from the browser.
	se := webrtc.SettingEngine{}
	if err := se.SetEphemeralUDPPortRange(5000, 5100); err != nil {
		return nil, err
	}
	if ip := os.Getenv("PION_PUBLIC_IP"); ip != "" {
		se.SetNAT1To1IPs([]string{ip}, webrtc.ICECandidateTypeHost)
	}
	m := &webrtc.MediaEngine{}
	if err := m.RegisterDefaultCodecs(); err != nil {
		return nil, err
	}
	api := webrtc.NewAPI(webrtc.WithMediaEngine(m), webrtc.WithSettingEngine(se))

	pc, err := api.NewPeerConnection(webrtc.Configuration{
		ICEServers: []webrtc.ICEServer{{URLs: []string{"stun:stun.l.google.com:19302"}}},
	})
	if err != nil {
		return nil, err
	}

	pc.OnTrack(func(track *webrtc.TrackRemote, receiver *webrtc.RTPReceiver) {
		if track.Kind() == webrtc.RTPCodecTypeAudio {
			s.HandleIncomingAudio(track)
		}
	})
	return pc, nil
}
