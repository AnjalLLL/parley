package audio

import "testing"

func TestResampleLengthsAndValues(t *testing.T) {
	in := Int16ToBytes([]int16{0, 300, 600, -32768, 32767, 0})
	up, _ := (&Resampler{24000, 48000}).ResampleReal(in)
	if got := BytesToInt16(up); len(got) != 12 || got[1] != 150 || got[2] != 300 {
		t.Fatalf("upsample: %v", got)
	}
	down, _ := (&Resampler{48000, 16000}).ResampleReal(Int16ToBytes(make([]int16, 960)))
	if len(down) != 320*2 {
		t.Fatalf("downsample len %d", len(down))
	}
	if r := BytesToInt16(Int16ToBytes([]int16{-32768, -1, 32767})); r[0] != -32768 || r[1] != -1 || r[2] != 32767 {
		t.Fatalf("roundtrip %v", r)
	}
}
