package sfu

import (
	"log"

	"ai-call-pion/audio"
	"github.com/pion/webrtc/v3"
)

func (s *Session) HandleIncomingAudio(track *webrtc.TrackRemote) {
	log.Printf("Started receiving audio track: %s", track.ID())
	
	codec := audio.NewRTPCodec()
	resampler, _ := audio.NewResampler(48000, 16000)

	for {
		packet, _, err := track.ReadRTP()
		if err != nil {
			log.Printf("Error reading RTP: %v", err)
			return
		}

		pcm48, err := codec.Decode(packet)
		if err != nil {
			continue
		}

		// Use ResampleReal for actual resampling
		pcm16, err := resampler.ResampleReal(pcm48)
		if err != nil {
			pcm16 = pcm48 // Fallback
		}
		s.PushUserAudio(pcm16)
	}
}
