package webrtcconfig

import (
	"github.com/pion/webrtc/v3"
)

func GetDefaultConfiguration() webrtc.Configuration {
	return webrtc.Configuration{
		ICEServers: []webrtc.ICEServer{
			{
				URLs: []string{"stun:stun.l.google.com:19302"},
			},
		},
	}
}
