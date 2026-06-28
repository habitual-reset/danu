from __future__ import annotations

import uuid
from pathlib import Path

from danu.channels.voice import format_voice_response
from danu.config import get_settings


class VoiceTTS:
    """OpenAI TTS — better voice quality, served to Twilio via /audio/{id}.mp3"""

    def __init__(self) -> None:
        settings = get_settings()
        self.enabled = bool(settings.openai_api_key and settings.voice_tts_enabled)
        self.model = settings.voice_tts_model
        self.voice = settings.voice_tts_voice
        self.audio_dir = Path(settings.voice_tts_audio_dir)
        self.audio_dir.mkdir(parents=True, exist_ok=True)

    def synthesize(self, text: str) -> tuple[str, str] | None:
        if not self.enabled:
            return None

        cleaned = format_voice_response(text)
        if not cleaned:
            return None

        from openai import OpenAI

        client = OpenAI(api_key=get_settings().openai_api_key)
        clip_id = str(uuid.uuid4())
        path = self.audio_dir / f"{clip_id}.mp3"
        response = client.audio.speech.create(
            model=self.model,
            voice=self.voice,
            input=cleaned,
        )
        path.write_bytes(response.content)

        settings = get_settings()
        url = settings.twilio_webhook_url_for(f"/audio/{clip_id}.mp3")
        return clip_id, url


def get_voice_tts() -> VoiceTTS:
    return VoiceTTS()