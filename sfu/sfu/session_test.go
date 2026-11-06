package sfu

import "testing"

func TestPushUserAudioDeliversThenDropsWhenFull(t *testing.T) {
	s := NewSession("s1")
	s.PushUserAudio([]byte{1, 2})
	if got := <-s.GetAudioStream(); len(got) != 2 {
		t.Fatalf("want 2 bytes, got %v", got)
	}
	for i := 0; i < cap(s.pcmInChan)+10; i++ { // must never block, even when nobody reads
		s.PushUserAudio([]byte{0})
	}
}

func TestCloseIsIdempotentAndSignalsDone(t *testing.T) {
	s := NewSession("s1")
	s.Close()
	s.Close()
	select {
	case <-s.Done():
	default:
		t.Fatal("Done() not closed after Close()")
	}
	s.PushUserAudio([]byte{1}) // after close: no panic, no block
}

func TestProcessOfferRejectsGarbageSDP(t *testing.T) {
	s := NewSession("s1")
	defer s.Close()
	if _, err := s.ProcessOffer("not sdp"); err == nil {
		t.Fatal("expected an error for invalid SDP")
	}
}
