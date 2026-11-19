"""Procedural 16-bit PCM sound effect and chiptune background track generator."""

from array import array
import math
import random
from typing import Dict, List, Optional, Tuple

import pygame

from game.constants import AUDIO_SAMPLE_RATE
from game.systems.settings import GameSettings


class AudioManager:
    """Generates and plays procedural sound effects and ambient loop without external audio files."""

    def __init__(self, settings: GameSettings) -> None:
        """Initialize pygame.mixer safely and synthesize all sound buffers."""
        self.settings: GameSettings = settings
        self.available: bool = False
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.music_sound: Optional[pygame.mixer.Sound] = None
        self.music_channel: Optional[pygame.mixer.Channel] = None
        self._init_mixer()

    def _init_mixer(self) -> None:
        """Attempt to initialize pygame.mixer; degrade gracefully if no audio device exists."""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=AUDIO_SAMPLE_RATE, size=-16, channels=1, buffer=512)
            self.available = True
            self._generate_all_sounds()
            self.apply_volume()
        except pygame.error:
            self.available = False

    def _make_sound(self, samples: array) -> Optional[pygame.mixer.Sound]:
        """Create a pygame.mixer.Sound from a 16-bit signed PCM array."""
        if not self.available:
            return None
        try:
            init_info = pygame.mixer.get_init()
            channels = init_info[2] if init_info else 1
            if channels == 2:
                stereo = array("h")
                for s in samples:
                    stereo.append(s)
                    stereo.append(s)
                return pygame.mixer.Sound(buffer=stereo.tobytes())
            return pygame.mixer.Sound(buffer=samples.tobytes())
        except pygame.error:
            return None

    def _generate_all_sounds(self) -> None:
        """Synthesize click, stamp, success, error, page_turn, coin, and ambient music."""
        self.sounds["click"] = self._synth_click()
        self.sounds["stamp"] = self._synth_stamp()
        self.sounds["success"] = self._synth_arpeggio([(523.25, 0.08), (659.25, 0.08), (783.99, 0.09), (1046.5, 0.18)])
        self.sounds["error"] = self._synth_error()
        self.sounds["page"] = self._synth_page_turn()
        self.sounds["coin"] = self._synth_arpeggio([(987.77, 0.05), (1318.51, 0.14)])
        self.music_sound = self._synth_ambient_loop()

    def _synth_click(self) -> Optional[pygame.mixer.Sound]:
        """Short crisp UI button click."""
        n = int(AUDIO_SAMPLE_RATE * 0.035)
        buf = array("h")
        for i in range(n):
            t = i / AUDIO_SAMPLE_RATE
            env = (1.0 - i / n) ** 2
            val = math.sin(2.0 * math.pi * (900.0 - 450.0 * (i / n)) * t) * env
            buf.append(int(val * 12000))
        return self._make_sound(buf)

    def _synth_stamp(self) -> Optional[pygame.mixer.Sound]:
        """Heavy mechanical rubber-stamp thump."""
        n = int(AUDIO_SAMPLE_RATE * 0.16)
        buf = array("h")
        rng = random.Random(42)
        for i in range(n):
            t = i / AUDIO_SAMPLE_RATE
            env = (1.0 - i / n) ** 1.8
            freq = 135.0 * (0.45 + 0.55 * (1.0 - i / n))
            thump = math.sin(2.0 * math.pi * freq * t)
            noise = (rng.random() * 2.0 - 1.0) * (0.45 if i < n * 0.25 else 0.15)
            val = max(-1.0, min(1.0, (0.75 * thump + 0.35 * noise) * env))
            buf.append(int(val * 22000))
        return self._make_sound(buf)

    def _synth_arpeggio(self, notes: List[Tuple[float, float]]) -> Optional[pygame.mixer.Sound]:
        """Bright triangle/sine arpeggio for coin or success jingles."""
        buf = array("h")
        for freq, dur in notes:
            n = int(AUDIO_SAMPLE_RATE * dur)
            for i in range(n):
                t = i / AUDIO_SAMPLE_RATE
                env = min(1.0, i / 120.0) * ((1.0 - i / n) ** 0.7)
                s1 = math.sin(2.0 * math.pi * freq * t)
                s2 = 0.35 * math.sin(2.0 * math.pi * (freq * 2.0) * t)
                val = (s1 + s2) * 0.75 * env
                buf.append(int(max(-1.0, min(1.0, val)) * 16000))
        return self._make_sound(buf)

    def _synth_error(self) -> Optional[pygame.mixer.Sound]:
        """Low buzzer sound for errors or denials."""
        n = int(AUDIO_SAMPLE_RATE * 0.24)
        buf = array("h")
        for i in range(n):
            t = i / AUDIO_SAMPLE_RATE
            freq = 165.0 if i < n // 2 else 130.0
            env = (1.0 - (i % (n // 2)) / (n // 2)) ** 0.4
            # Soft square-like wave
            raw = math.sin(2.0 * math.pi * freq * t) + 0.33 * math.sin(2.0 * math.pi * freq * 3.0 * t)
            buf.append(int(max(-1.0, min(1.0, raw * env)) * 14000))
        return self._make_sound(buf)

    def _synth_page_turn(self) -> Optional[pygame.mixer.Sound]:
        """Soft filtered noise swish resembling turning paper."""
        n = int(AUDIO_SAMPLE_RATE * 0.11)
        buf = array("h")
        rng = random.Random(99)
        prev = 0.0
        for i in range(n):
            u = i / n
            env = math.sin(math.pi * u) ** 1.3
            white = rng.random() * 2.0 - 1.0
            prev = 0.7 * prev + 0.3 * white
            buf.append(int(max(-1.0, min(1.0, prev * env)) * 10000))
        return self._make_sound(buf)

    def _synth_ambient_loop(self) -> Optional[pygame.mixer.Sound]:
        """Gentle, quiet chiptune-style bureaucratic background loop (~4.8 seconds)."""
        chord_notes = [
            (220.00, 0.4),
            (261.63, 0.4),
            (329.63, 0.4),
            (293.66, 0.4),
            (196.00, 0.4),
            (246.94, 0.4),
            (293.66, 0.4),
            (261.63, 0.4),
            (174.61, 0.4),
            (220.00, 0.4),
            (261.63, 0.4),
            (246.94, 0.4),
        ]
        buf = array("h")
        for freq, dur in chord_notes:
            n = int(AUDIO_SAMPLE_RATE * dur)
            for i in range(n):
                t = i / AUDIO_SAMPLE_RATE
                u = i / n
                env = math.sin(math.pi * u) ** 0.8
                tone = 0.7 * math.sin(2.0 * math.pi * freq * t) + 0.3 * math.sin(2.0 * math.pi * (freq * 0.5) * t)
                buf.append(int(tone * env * 3800))
        return self._make_sound(buf)

    def start_music(self) -> None:
        """Start looping the ambient background track if available."""
        if not self.available or self.music_sound is None:
            return
        try:
            if self.music_channel is None or not self.music_channel.get_busy():
                self.music_channel = self.music_sound.play(loops=-1)
            self.apply_volume()
        except pygame.error:
            pass

    def apply_volume(self) -> None:
        """Apply current SFX/music volume and mute state from self.settings."""
        if not self.available:
            return
        sfx_vol = 0.0 if self.settings.muted else self.settings.sfx_volume
        mus_vol = 0.0 if self.settings.muted else self.settings.music_volume
        for snd in self.sounds.values():
            if snd is not None:
                snd.set_volume(sfx_vol)
        if self.music_sound is not None:
            self.music_sound.set_volume(mus_vol)

    def toggle_mute(self) -> bool:
        """Toggle mute setting and immediately update mixer volumes."""
        self.settings.muted = not self.settings.muted
        self.apply_volume()
        return self.settings.muted

    def play(self, name: str) -> None:
        """Play a named sound effect ('click', 'stamp', 'success', 'error', 'page', 'coin')."""
        if not self.available or self.settings.muted:
            return
        snd = self.sounds.get(name)
        if snd is not None:
            try:
                snd.play()
            except pygame.error:
                pass
