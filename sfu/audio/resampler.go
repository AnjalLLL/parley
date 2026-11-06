package audio

// Resampler converts 16-bit little-endian mono PCM between sample rates with linear interpolation.
// shortcut: linear interpolation, no anti-alias filter; fine for speech, swap for soxr if quality matters.
type Resampler struct {
	from int
	to   int
}

func NewResampler(from, to int) (*Resampler, error) {
	return &Resampler{from: from, to: to}, nil
}

func (r *Resampler) Resample(pcmData []byte) []byte {
	out, _ := r.ResampleReal(pcmData)
	return out
}

func (r *Resampler) ResampleReal(pcmData []byte) ([]byte, error) {
	n := len(pcmData) / 2
	if r.from == r.to || n == 0 {
		return pcmData, nil
	}
	in := BytesToInt16(pcmData)
	outN := n * r.to / r.from
	out := make([]int16, outN)
	for i := range out {
		pos := float64(i) * float64(r.from) / float64(r.to)
		j := int(pos)
		frac := pos - float64(j)
		a := float64(in[j])
		b := a
		if j+1 < n {
			b = float64(in[j+1])
		}
		out[i] = int16(a + (b-a)*frac)
	}
	return Int16ToBytes(out), nil
}

func BytesToInt16(b []byte) []int16 {
	s := make([]int16, len(b)/2)
	for i := range s {
		s[i] = int16(uint16(b[i*2]) | uint16(b[i*2+1])<<8)
	}
	return s
}

func Int16ToBytes(s []int16) []byte {
	b := make([]byte, len(s)*2)
	for i, v := range s {
		b[i*2] = byte(v)
		b[i*2+1] = byte(uint16(v) >> 8)
	}
	return b
}
