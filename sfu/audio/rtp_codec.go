package audio

import (
	"fmt"
	"time"

	"github.com/hraban/opus"
	"github.com/pion/rtp"
)

const (
	OpusFrameDuration = 20 * time.Millisecond
)

type RTPCodec struct {
	decoder *opus.Decoder
	encoder *opus.Encoder
}

func NewRTPCodec() *RTPCodec {
	// 48000Hz, 1 channel
	dec, err := opus.NewDecoder(48000, 1)
	if err != nil {
		fmt.Printf("Error creating decoder: %v\n", err)
	}
	enc, err := opus.NewEncoder(48000, 1, opus.AppVoIP)
	if err != nil {
		fmt.Printf("Error creating encoder: %v\n", err)
	}
	return &RTPCodec{
		decoder: dec,
		encoder: enc,
	}
}

func (c *RTPCodec) Decode(packet *rtp.Packet) ([]byte, error) {
	if c.decoder == nil {
		return nil, fmt.Errorf("decoder not initialized")
	}
	// Max samples per frame at 48kHz is 5760 (120ms)
	pcm := make([]int16, 5760)
	n, err := c.decoder.Decode(packet.Payload, pcm)
	if err != nil {
		return nil, err
	}
	
	// Convert int16 to []byte (little endian)
	res := make([]byte, n*2)
	for i := 0; i < n; i++ {
		res[i*2] = byte(pcm[i] & 0xff)
		res[i*2+1] = byte(pcm[i] >> 8)
	}
	return res, nil
}

func (c *RTPCodec) Encode(pcmData []byte) ([]byte, error) {
	if c.encoder == nil {
		return nil, fmt.Errorf("encoder not initialized")
	}
	// Convert []byte (little endian) to int16
	n := len(pcmData) / 2
	pcm := make([]int16, n)
	for i := 0; i < n; i++ {
		pcm[i] = int16(pcmData[i*2]) | (int16(pcmData[i*2+1]) << 8)
	}

	data := make([]byte, 1000)
	size, err := c.encoder.Encode(pcm, data)
	if err != nil {
		return nil, err
	}
	return data[:size], nil
}
