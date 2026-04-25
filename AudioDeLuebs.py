import os
import platform
import threading
import subprocess
import zipfile
import io
import pygame
import shlex  # Für Linux TTS

class AudioManager:
    def __init__(self):
        self.system = platform.system()
        
        # 1. Mixer initialisieren
        pygame.mixer.pre_init(44100, -16, 4, 512)
        pygame.mixer.init()
        
        # 2. Alle Soundeffekte aus dem Pak laden
        try:
            with zipfile.ZipFile("data.pak", "r") as pak:
                self.sound0 = pygame.mixer.Sound(io.BytesIO(pak.read("beep-07a.wav")))
                self.sound0.set_volume(0.9)
                self.sound1 = pygame.mixer.Sound(io.BytesIO(pak.read("bumbbumbv2.wav")))
                self.sound1.set_volume(0.9)
                self.sound_error = pygame.mixer.Sound(io.BytesIO(pak.read('error_kurz.wav')))
                self.sound_error.set_volume(0.9)
                self.sound_pfeife = pygame.mixer.Sound(io.BytesIO(pak.read('PfeifeKurz2.wav')))
                self.sound_pfeife.set_volume(0.9)
                self.sound_win = pygame.mixer.Sound(io.BytesIO(pak.read('goodresult-82807.mp3')))
                self.sound_win.set_volume(0.9)
                self.sound_load = pygame.mixer.Sound(io.BytesIO(pak.read('new-notification-07-210334.mp3')))
                self.sound_load.set_volume(0.9)         
                self.sound_orchestra = pygame.mixer.Sound(io.BytesIO(pak.read('11325622-orchestra-hit-240475.wav')))
                self.sound_orchestra.set_volume(0.9)                        
                self.sound_buzzticker = pygame.mixer.Sound(io.BytesIO(pak.read('BuzzTicker_early.wav')))
                self.sound_buzzticker.set_volume(0.8)                    
                self.sound_shoot = pygame.mixer.Sound(io.BytesIO(pak.read('freesound_community-080997_bullet-39735.wav')))
                self.sound_shoot.set_volume(0.9)
        except Exception as e:
            print(f"WARNUNG: Konnte Audio-Dateien nicht laden: {e}")

    # 3. Die perfekte asynchrone TTS-Methode
    def say(self, text):
        def run():
            if self.system == "Linux":
                wav_file = "/dev/shm/temp_speech.wav"
                os.system(f'pico2wave --lang=de-DE --wave={wav_file} {shlex.quote(text)}')
                try:
                    voice = pygame.mixer.Sound(wav_file)
                    voice.play()
                except Exception as e:
                    print(f"Audio-Fehler am Pi: {e}")
                    
            elif self.system == "Windows":
                ps_cmd = f'Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("{text}")'
                CREATE_NO_WINDOW = 0x08000000
                try:
                    subprocess.run(["powershell", "-Command", ps_cmd], creationflags=CREATE_NO_WINDOW)
                except Exception as e:
                    print(f"Windows Audio Fehler: {e}")

        threading.Thread(target=run, daemon=True).start()