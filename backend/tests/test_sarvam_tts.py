from app.services.sarvam_tts_service import SarvamTTSService


def test_chunk_text_preserves_sentences():
    service = SarvamTTSService()
    text = (
        "Agar aapko lagta hai ki thriller pasand hai toh ye 3 movies dekhein. "
        "Pehli movie hai Shutter Island. "
        "Dusri movie hai Prisoners. "
        "Teesri movie hai The Prestige. "
        "Inme se aapki favourite kaun si hai? Comment karein!"
    )
    chunks = service.chunk_text(text, max_chars=100)
    assert len(chunks) >= 2
    assert all(len(c) <= 100 for c in chunks)
    combined = " ".join(chunks)
    assert "Shutter Island" in combined
    assert "The Prestige" in combined


def test_clean_text_removes_markdown():
    service = SarvamTTSService()
    dirty = "[EXCITED] Shutter Island (2010) - insane thriller! [WHISPERING] End of scene."
    clean = service.clean_voice_text(dirty)
    assert "[EXCITED]" not in clean
    assert "[WHISPERING]" not in clean
    assert "Shutter Island" in clean
