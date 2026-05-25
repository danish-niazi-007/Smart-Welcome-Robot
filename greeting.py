"""
greeting.py - Smart TTS Greeter
================================
Sirf tab greet karta hai jab is_new_visitor=True ho.
Same banda dobara greet nahi hoga jab tak hat ke wapas na aaye.
"""

import threading
import time
from typing import Optional

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("[Greeting] pyttsx3 not installed. Audio disabled.")


class Greeter:
    def __init__(self, rate: int = 150, volume: float = 0.95, cooldown: float = 5.0):
        self._rate = rate
        self._volume = volume
        self._cooldown = cooldown
        self._speaking = False
        self._lock = threading.Lock()
        self._last_spoke = 0.0

    def greet(self, scenario: str, speech_text: str, is_new_visitor: bool = True):
        """
        Sirf tab bolta hai jab:
        1. is_new_visitor = True (naya chehra detect hua)
        2. scenario 'none' nahi hai
        3. Cooldown complete ho gayi
        """
        if not is_new_visitor:
            return
        if scenario == "none" or not speech_text:
            return
        now = time.time()
        if now - self._last_spoke < self._cooldown:
            return
        self._last_spoke = now
        thread = threading.Thread(target=self._speak, args=(speech_text,), daemon=True)
        thread.start()

    def _speak(self, text: str):
        with self._lock:
            if self._speaking:
                return
            self._speaking = True
        try:
            if not TTS_AVAILABLE:
                print(f"[Greeting] (TTS off) Would say: {text}")
                return
            engine = pyttsx3.init()
            engine.setProperty("rate", self._rate)
            engine.setProperty("volume", self._volume)
            voices = engine.getProperty("voices")
            for v in voices:
                if "english" in v.name.lower():
                    engine.setProperty("voice", v.id)
                    break
            print(f"[Greeting] Speaking: \"{text}\"")
            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception as e:
            print(f"[Greeting] TTS error: {e}")
        finally:
            with self._lock:
                self._speaking = False

    def reset(self):
        self._last_spoke = 0.0
