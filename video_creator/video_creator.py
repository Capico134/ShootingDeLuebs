import os
import sys
import math
import numpy as np
import json
from PIL import Image, ImageFilter, ImageDraw
from moviepy import (
    VideoFileClip, ImageClip, CompositeVideoClip, VideoClip, 
    concatenate_videoclips, vfx, CompositeAudioClip, AudioFileClip
)

# ==========================================
# 1. KONFIGURATION & PARAMETER
# ==========================================
import sys
import os
import json

# Welches JSON soll geladen werden?
if len(sys.argv) > 1:
    CONFIG_DATEI = sys.argv[1]
else:
    CONFIG_DATEI = "../savegames/video_configs/VIDEO_MATCH000383.json"

with open(CONFIG_DATEI, "r", encoding="utf-8") as f:
    cfg = json.load(f)

# --- DER GENIALE TRICK FÜR DEN OUTPUT ---
# Wir ersetzen einfach die Dateiendung. 
# Aus "../savegames/video_configs/VIDEO_MATCH000383.json" 
# wird automatisch "../savegames/video_configs/VIDEO_MATCH000383_Render.mp4"
OUTPUT_NAME = CONFIG_DATEI.replace(".json", "_Render.mp4")

BG_IMAGE = "Schiessstand_upscayl_3x_upscayl-standard-4x.png"

#ALT!!!!
#GUN_VIDEO = "Precision_Air_Pistol_Shot_Simulation.mp4"

# --- OPTIONALE AUDIO-DATEIEN ---
USE_CUSTOM_AUDIO = True  # True = Nutze WAVs, False = Nutze Ton aus schuss.mp4

# Sound für deinen Spieler (POV)
POV_AUDIO_FILE = "pov_schuss.wav"
POV_AUDIO_IMPACT = 0.20  # Der Knall passiert z.B. nach 0.15 Sekunden in der Datei

# Sound für den Gegner
GEGNER_AUDIO_FILE = "gegner_schuss.wav"
GEGNER_AUDIO_IMPACT = 0.20 # Der Knall passiert z.B. nach 0.10 Sekunden in der Datei

TIMING = cfg["TIMING"]
SEQUENCE_POV = cfg["SEQUENCE_POV"]          # <-- NEU
SEQUENCE_GEGNER = cfg["SEQUENCE_GEGNER"]    # <-- NEU

GOLD_LEUCHTEND = cfg["GOLD_LEUCHTEND"]
GOLD_BLINKEND = cfg["GOLD_BLINKEND"]
BLAU_LEUCHTEND = cfg["BLAU_LEUCHTEND"]
BLAU_BLINKEND = cfg["BLAU_BLINKEND"]

## Koordinaten der 5 Ziele auf deinem Hintergrund (X, Y)
TARGETS = [
    (2138, 440), # Ziel 0 (ganz links)
    (1649, 442), # Ziel 1
    (1173, 443), # Ziel 2 (Mitte)
    (697, 443), # Ziel 3
    (212, 443) # Ziel 4 (ganz rechts)
]


# --- NEU: Koordinaten auch für Kommazahlen (Fake-Bewegungen) berechnen ---
def get_target_coords(val):
    if isinstance(val, int):
        return TARGETS[val]
    elif isinstance(val, float):
        lower = int(math.floor(val))
        upper = int(math.ceil(val))
        
        # Sicherheits-Clip, falls mal jemand 4.5 eingibt
        upper = min(upper, len(TARGETS) - 1)
        lower = min(lower, len(TARGETS) - 1)
        
        if lower == upper: 
            return TARGETS[lower]
            
        frac = val - lower
        x = TARGETS[lower][0] + (TARGETS[upper][0] - TARGETS[lower][0]) * frac
        y = TARGETS[lower][1] + (TARGETS[upper][1] - TARGETS[lower][1]) * frac
        return (x, y)
        
    return TARGETS[2] # Fallback


# ==========================================
# Einmalige Vorberechnung für die Kamera (mit Versteck-Logik)
# ==========================================
HIDE_OFFSET_Y = 1000  # Wie viele Pixel soll die Waffe nach unten ins "Holster" verschwinden?

GUN_WAYPOINTS = []

# ==========================================
# Einmalige Vorberechnung für die Kamera (mit Versteck-Logik)
# ==========================================
HIDE_OFFSET_Y = 1000 
GUN_WAYPOINTS = []

def find_target(start_idx, direction=1):
    idx = start_idx
    while 0 <= idx < len(SEQUENCE_POV):
        val = SEQUENCE_POV[idx]
        if isinstance(val, (int, float)) and val >= 0:
            return get_target_coords(val)
        idx += direction
    return TARGETS[2]

last_valid_pos = None

for i, val in enumerate(SEQUENCE_POV):
    current_t = TIMING[i]

    if val == "UP":
        tgt = find_target(i, 1)
        pos = (tgt[0], tgt[1] + HIDE_OFFSET_Y)
        GUN_WAYPOINTS.append((current_t, pos))
        last_valid_pos = pos

    elif val == "DOWN":
        tgt = find_target(i, -1)
        pos = (tgt[0], tgt[1] + HIDE_OFFSET_Y)
        
        if last_valid_pos:
            # FIX Punkt 1: 1.5 Sekunden statt 0.8 sorgt für ein samtweiches Absenken!
            hold_time = max(0, current_t - 1.5)
            if len(GUN_WAYPOINTS) > 0 and hold_time > GUN_WAYPOINTS[-1][0]:
                GUN_WAYPOINTS.append((hold_time, last_valid_pos))
                
        GUN_WAYPOINTS.append((current_t, pos))
        last_valid_pos = pos

    elif isinstance(val, (int, float)) and val >= 0:
        # Normaler Schuss ODER Fake-Fahrt (z.B. 0.7)
        pos = get_target_coords(val)
        GUN_WAYPOINTS.append((current_t, pos))
        last_valid_pos = pos



###########ALTE DATEN###########
#TIMING =      [0.00, 2.52, 4.18, 4.46, 6.28, 7.24, 8.59, 9.92]
#SEQUENCE =    [3,    0,   -1,    3,    2,   -1,    0,   -1]
## Listen gehören jetzt fest zu den Spielern
#LEDS_POV =    [[0],  [3],  [3],  [2],  [0], [0],  [4],  [4]]
#LEDS_GEGNER = [[2],  [2],  [4],  [4],  [4], [2],  [2],  [3]]
## --- NEU: Style-Schalter ---
#POV_BLINKT = True       # True = POV-Spieler blinkt, False = Dauerlicht
#GEGNER_BLINKT = False   # True = Gegner blinkt, False = Dauerlicht
## Einmalige Vorberechnung für die Kamera (Ignoriert Andreas' -1 Treffer)
#GUN_WAYPOINTS = []
#for i in range(len(TIMING)):
#    if SEQUENCE[i] != -1:
#        GUN_WAYPOINTS.append((TIMING[i], TARGETS[SEQUENCE[i]]))


# Offset: Wie weit ist der rote Punkt vom Video-Mittelpunkt entfernt?
# (Musst du ggf. anpassen, damit das Visier genau auf dem Ziel liegt)
GUN_OFFSET_X = -155-460
GUN_OFFSET_Y = -70

#SPEED_FAKTOR = 1.5
#SPEED_FAKTOR = 2

# Zeit-Parameter
START_DELAY = 2.10#/SPEED_FAKTOR      # Wartezeit vor dem ersten Sprung
MOVE_DURATION = 2.0#/SPEED_FAKTOR   # Wie lange dauert der Schwenk (Torquen)? 2.8
AIM_DURATION = 2.05#/SPEED_FAKTOR    # Wie lange wird gezielt/geschossen?
STEP_TIME = MOVE_DURATION + AIM_DURATION

# ==========================================
# 2. DIE MATHEMATISCHE ENGINE (Bewegung)
# ==========================================
def get_current_target_info(t):
    """Ermittelt Basis-Infos für Kamera UND Fokus basierend auf den ECHTEN Zeitstempeln!"""
    # Vor dem allerersten Schuss (Wir ruhen auf dem ersten Ziel)
    if t < GUN_WAYPOINTS[0][0]:
        return GUN_WAYPOINTS[0][1], GUN_WAYPOINTS[0][1], 1.0 
        
    # Nach dem allerletzten Schuss (Wir bleiben auf dem letzten Ziel)
    if t >= GUN_WAYPOINTS[-1][0]:
        return GUN_WAYPOINTS[-1][1], GUN_WAYPOINTS[-1][1], 1.0 
        
    # Dazwischen: Finde heraus, auf welchem Wegstück wir gerade sind
    for i in range(len(GUN_WAYPOINTS) - 1):
        t_start, p_start = GUN_WAYPOINTS[i]
        t_end, p_end = GUN_WAYPOINTS[i+1]
        
        if t_start <= t < t_end:
            duration = t_end - t_start
            raw_progress = (t - t_start) / duration
            
            # Weiches Anfahren und Abbremsen
            progress = raw_progress * raw_progress * (3 - 2 * raw_progress)
            return p_start, p_end, progress
            
    return GUN_WAYPOINTS[-1][1], GUN_WAYPOINTS[-1][1], 1.0

def get_camera_shake(t):
    """Wackelt NUR bei echten Schüssen, nicht bei UP/DOWN Fahrten!"""
    for i, wp_time in enumerate(TIMING):
        val = SEQUENCE_POV[i]
        
        # Ist es ein echter Schuss (Zahl 0 bis 4)?
        if isinstance(val, int) and val >= 0:
            if wp_time < t < (wp_time + 0.2): 
                # BÄM! Rückstoß
                time_since_shot = t - wp_time
                shake_y = math.sin(time_since_shot * 100) * 6
                shake_x = math.cos(time_since_shot * 80) * 3
                return shake_x, shake_y
                
    return 0, 0 # Kein Shake bei UP, DOWN oder -1

#SMART!!!!!!!!!!!!!!!!!!!!!!!!!!
# True = Der Fokus gleitet in jedem Frame weich mit der Pistole mit.
# False = "Sniper-Modus": Der Fokus springt hart auf das nächste Ziel.
SMOOTH_FOCUS = False
def get_focus_position(t):
    """Berechnet die exakte (X,Y) Position für die scharfe Maske."""
    # Holt alle Infos aus unserer Master-Timing-Engine
    start_pos, end_pos, progress = get_current_target_info(t)
    
    if SMOOTH_FOCUS:
        # ---------------------------------------------------------
        # MODUS A (True): Kamera-Autofokus (Weich)
        # ---------------------------------------------------------
        # Die Schärfe wandert Pixel für Pixel exakt mit dem Visier mit.
        x = start_pos[0] + (end_pos[0] - start_pos[0]) * progress
        y = start_pos[1] + (end_pos[1] - start_pos[1]) * progress
        return x, y
        
    else:
        # ---------------------------------------------------------
        # MODUS B (False): Sniper-Blick (Harter Sprung)
        # ---------------------------------------------------------
        if progress < 1.0:
            # Wir sind gerade mitten im Schwenk.
            # Der Fokus springt vorausschauend schon auf das Ziel, 
            # zu dem die Pistole gerade unterwegs ist!
            return end_pos
        else:
            # Wir sind angekommen und zielen/schießen gerade.
            # Der Fokus ruht sicher auf dem aktuellen Ziel.
            return end_pos


    

def get_gun_position(t):
    """Gleitet sanft, nutzt jetzt exakt dieselbe Motor-Logik wie der Fokus!"""
    start_pos, end_pos, progress = get_current_target_info(t)
    
    # 1. Basis-Koordinaten berechnen
    base_x = start_pos[0] + (end_pos[0] - start_pos[0]) * progress
    base_y = start_pos[1] + (end_pos[1] - start_pos[1]) * progress
    
    # 2. Atmen und Wackeln hinzufügen
    breath_x = math.sin(t * 1.5) * 4
    breath_y = math.cos(t * 1.2) * 6
    
    base_shake_x, base_shake_y = get_camera_shake(t)
    
    final_x = base_x + breath_x + (base_shake_x * 2) + GUN_OFFSET_X
    final_y = base_y + breath_y + (base_shake_y * 2) + GUN_OFFSET_Y
    
    # ==========================================
    # --- MOVIEPY CRASH-SCHUTZ ---
    # Wir lassen die Waffe niemals tiefer als Y=915 fallen. 
    # So bleibt 1 Millimeter im Bild, MoviePy stürzt nicht ab, 
    # und durch den Greenscreen sieht man trotzdem absolut nichts!
    final_y = min(final_y, 915)
    # ==========================================
    
    return (final_x, final_y)

# ==========================================
# 3. VIDEO-ZUSAMMENBAU (MoviePy v2.2.1)
# ==========================================
def build_video():
    print(f"--- Starte Rendering: {OUTPUT_NAME} ---")
    
    # NEU: Die Videolänge richtet sich jetzt dynamisch nach den JSON-Daten!
    total_duration = TIMING[-1] + 2.0  
    
    # --- A. HINTERGRUND (Dynamisch gezeichnet für jeden Frame) ---
    bg_img = Image.open(BG_IMAGE)
    bg_w, bg_h = bg_img.size

    def make_bg_frame(t):
        # 1. Frische Kopie vom Hintergrund nehmen
        img_copy = bg_img.copy()
        draw = ImageDraw.Draw(img_copy)
        
        # 2. Welchen Index (Zeitabschnitt) haben wir gerade?
        current_idx = 0
        for i, t_val in enumerate(TIMING):
            if t >= t_val: current_idx = i
            else: break
            
        # 3. Den Blink-Takt EINMAL für diesen Frame berechnen
        blink_faktor = (math.sin(t * 15) + 1) / 2
        ist_an = blink_faktor > 0.5
        
        # 4. Alle 5 LEDs durchgehen
        for led_idx, target_pos in enumerate(TARGETS):
            lx = target_pos[0] + 80 + 13
            ly = target_pos[1] - 80 + 31 
            radius = 22
            
            # --- DIE GENIALE FARB-WEICHE ---
            # Soll dieses Ziel Gold oder Blau gezeichnet werden?
            draw_gold = (led_idx in GOLD_LEUCHTEND[current_idx]) or (led_idx in GOLD_BLINKEND[current_idx] and ist_an)
            draw_blau = (led_idx in BLAU_LEUCHTEND[current_idx]) or (led_idx in BLAU_BLINKEND[current_idx] and ist_an)
            
            #if draw_gold:
            #    # --- GOLDGELB ---
            #    draw.ellipse((lx - radius, ly - radius, lx + radius, ly + radius), fill=(255, 190, 80)) 
            #    draw.ellipse((lx - 25, ly - 25, lx + 25, ly + 25), fill=(255, 230, 150))
            #    draw.ellipse((lx - 10, ly - 10, lx + 10, ly + 10), fill=(220, 240, 255))

            if draw_gold:
                # --- GOLDGELB ---
                draw.ellipse((lx - radius, ly - radius, lx + radius, ly + radius), fill=(255, 90, 30)) 
                #draw.ellipse((lx - 25, ly - 25, lx + 25, ly + 25), fill=(255, 130, 100))
                draw.ellipse((lx - 10, ly - 10, lx + 10, ly + 10), fill=(255, 240, 205))                
                
            elif draw_blau:
                # --- BLAU ---
                draw.ellipse((lx - radius, ly - radius, lx + radius, ly + radius), fill=(80, 150, 255)) 
                draw.ellipse((lx - 10, ly - 10, lx + 10, ly + 10), fill=(220, 240, 255))
                
            else:
                # --- AUS ---
                draw.ellipse((lx - radius, ly - radius, lx + radius, ly + radius), fill=(30, 30, 40))
                draw.ellipse((lx - 10, ly - 10, lx + 10, ly + 10), fill=(20, 20, 25))

        return np.array(img_copy)

    def make_blurred_bg_frame(t):
        # Wir rendern das Bild mit LEDs und machen es unscharf (für den Bokeh-Effekt!)
        frame = make_bg_frame(t)
        blurred = Image.fromarray(frame).filter(ImageFilter.GaussianBlur(radius=5))
        return np.array(blurred)

    # 4. MoviePy die Kontrolle übergeben (ruft die Funktionen für jeden Frame selbst auf)
    bg_sharp = VideoClip(frame_function=make_bg_frame, duration=total_duration)
    bg_blurred = VideoClip(frame_function=make_blurred_bg_frame, duration=total_duration)
    
    # --- B. DYNAMISCHE FOKUS-MASKE (mit CPU-Cache) ---
    class DynamicFocusMask(VideoClip):
        def __init__(self, w, h):
            super().__init__()
            self.is_mask = True 
            self.size = (w, h)
            self.frame_function = self.create_mask_frame
            
            # --- UNSER NEUER CACHE ---
            self.last_pos = None  # Merkt sich die letzte Koordinate
            self.last_mask = None # Merkt sich das fertig berechnete Bild

        #def create_mask_frame(self, t):
        #    w, h = self.size
        #    cx, cy = get_focus_position(t)
        #    
        #    # 1. CACHE-CHECK: Hat sich die Position überhaupt verändert?
        #    if self.last_pos == (cx, cy) and self.last_mask is not None:
        #        # CPU RETTUNG: Position ist gleich! Wir überspringen die 
        #        # gesamte Mathematik und geben das Bild vom letzten Frame zurück.
        #        return self.last_mask
        #    
        #    # 2. NEUBERECHNUNG (Nur wenn sich das Ziel bewegt hat)
        #    y, x = np.ogrid[:h, :w]
        #    dist = np.sqrt((x - cx)**2 + (y - cy)**2)
        #    
        #    radius = 130
        #    feather = 75
        #    mask = np.clip((radius + feather - dist) / feather, 0, 1)
        #    
        #    # 3. CACHE UPDATEN: Neue Daten für den nächsten Frame merken
        #    self.last_pos = (cx, cy)
        #    self.last_mask = mask# Basis-Radius
        #    
        #    return mask

        def create_mask_frame(self, t):
            w, h = self.size
            cx, cy = get_focus_position(t)
            
            # --- NEU: Den Shake auslesen ---
            sh_x, sh_y = get_camera_shake(t)
            
            # Basis-Radius und Druckwelle berechnen
            current_radius = 130
            if sh_y != 0:
                current_radius += 20 # Druckwelle beim Schuss!
            
            # 1. CACHE-CHECK: Hat sich Position ODER der Radius verändert?
            # Wir speichern jetzt 3 Werte im Cache: cx, cy und current_radius
            if self.last_pos == (cx, cy, current_radius) and self.last_mask is not None:
                return self.last_mask
            
            # 2. NEUBERECHNUNG
            y, x = np.ogrid[:h, :w]
            dist = np.sqrt((x - cx)**2 + (y - cy)**2)
            
            feather = 75
            mask = np.clip((current_radius + feather - dist) / feather, 0, 1)
            
            # 3. CACHE UPDATEN: Neue Daten für den nächsten Frame merken
            self.last_pos = (cx, cy, current_radius)
            self.last_mask = mask
            
            return mask



    # 1. Die Klasse instanziieren und die Dauer festlegen
    focus_mask = DynamicFocusMask(bg_w, bg_h).with_duration(total_duration)
    
    # 2. Die Maske auf das scharfe Bild anwenden
    bg_sharp_masked = bg_sharp.with_mask(focus_mask)


    # --- C. PISTOLE (Greenscreen & Trigger-System) ---
    
    # 1. Effekte definieren (Crop & Greenscreen)
    gun_effects = [
        vfx.Crop(x1=0, y1=120, x2=1120, y2=720), 
        vfx.MaskColor(color=[57, 177, 65], threshold=88, stiffness=8)
    ]
    
    # 2. Assets laden und vorbereiten
    idle_clip = (ImageClip("standbild.png")
                 .with_duration(total_duration)
                 .with_effects(gun_effects))
    
    # NEU: Wir laden das KOMPLETTE Video (0 bis 4.75s)
    recoil_clip = (VideoFileClip("schuss.mp4")
                   .without_audio()
                   .with_effects(gun_effects))
    
    # --- Die Parameter deiner Animation ---
    T_IMPACT = 2.6          # Bei welcher Sekunde im Video fällt der Schuss?
    CLIP_DURATION = 4.75    # Wie lang ist das schuss.mp4 insgesamt?
    MIN_RECOIL = 0.6        # Wie lange (in Sekunden) muss der Rückstoß des 
                            # VORHERIGEN Schusses mindestens laufen, bevor er abgebrochen wird?

    # 3. Die professionelle Time-Warp-Logik
    def get_active_gun_clip_time(t):
        """Spielt das Video (Greenscreen-Rückstoß) NUR bei echten Schüssen ab!"""
        # 1. Wir filtern uns schnell alle ECHTEN Schuss-Zeiten heraus
        valid_shots = [TIMING[i] for i, val in enumerate(SEQUENCE_POV) if isinstance(val, int) and val >= 0]
        
        # 2. Wir prüfen die Zeiten rückwärts
        for i in range(len(valid_shots) - 1, -1, -1):
            wp_time = valid_shots[i]
            
            ideal_start = wp_time - T_IMPACT
            
            if i > 0:
                prev_wp_time = valid_shots[i-1]
                actual_start = max(prev_wp_time + MIN_RECOIL, ideal_start)
            else:
                actual_start = ideal_start
                
            end_time = wp_time + (CLIP_DURATION - T_IMPACT)
            
            if actual_start <= t < end_time:
                local_t = T_IMPACT + (t - wp_time)
                if local_t < 0:
                    return None
                return local_t
                
        return None

    # 4. Bild- und Masken-Generator
    def make_gun_frame(t):
        local_t = get_active_gun_clip_time(t)
        if local_t is not None:
            return recoil_clip.get_frame(local_t)
        return idle_clip.get_frame(t)

    def make_gun_mask_frame(t):
        local_t = get_active_gun_clip_time(t)
        if local_t is not None:
            return recoil_clip.mask.get_frame(local_t)
        return idle_clip.mask.get_frame(t)

    # 5. Den finalen dynamischen Clip zusammenstecken
    gun_clip_dynamic = VideoClip(frame_function=make_gun_frame, duration=total_duration)
    gun_mask_dynamic = VideoClip(frame_function=make_gun_mask_frame, is_mask=True, duration=total_duration)
    
    gun_clip = gun_clip_dynamic.with_mask(gun_mask_dynamic)
    
    # 6. Schwenken und Shake aus der Engine anwenden
    gun_clip = gun_clip.with_position(get_gun_position)



    # --- D. SANDWICH BAUEN & EXPORT ---
    
    # Wir leiten die Shake-Werte an die Hintergrund-Ebenen weiter
    def bg_position(t):
        return get_camera_shake(t)

    # Reihenfolge: 1. Unscharf -> 2. Scharf -> 3. Pistole
    final_video = CompositeVideoClip(
        [
            bg_blurred.with_position(bg_position), 
            bg_sharp_masked.with_position(bg_position), 
            gun_clip
        ], 
        size=(2400, 920) 
    )


    # ==========================================
    # --- AUDIO-MISCHPULT ---
    # ==========================================
    print("Mische Audio-Spuren...")
    audio_clips = []
    
    if USE_CUSTOM_AUDIO:
        pov_audio_base = AudioFileClip(POV_AUDIO_FILE)
        gegner_audio_base = AudioFileClip(GEGNER_AUDIO_FILE)
        
        for i, wp_time in enumerate(TIMING):
            start_time = None
            ac_base = None
            
            val_pov = SEQUENCE_POV[i]
            val_gegner = SEQUENCE_GEGNER[i]
            
            # Hat der POV-Spieler ECHT geschossen? (Ausschluss von "UP" / "DOWN")
            if isinstance(val_pov, int) and val_pov >= 0:
                start_time = wp_time - POV_AUDIO_IMPACT
                ac_base = pov_audio_base
                
            # Oder hat der Gegner geschossen?
            elif isinstance(val_gegner, int) and val_gegner >= 0:
                start_time = wp_time - GEGNER_AUDIO_IMPACT
                ac_base = gegner_audio_base
                
            # Wenn jemand geschossen hat, Clip zuschneiden und anfügen
            if start_time is not None and ac_base is not None:
                if start_time < 0:
                    ac = ac_base.subclipped(-start_time).with_start(0)
                else:
                    ac = ac_base.with_start(start_time)
                audio_clips.append(ac)
            
    # Mixdown und unter das Video legen
    if audio_clips:
        final_audio = CompositeAudioClip(audio_clips)
        if final_audio.duration > total_duration:
            final_audio = final_audio.subclipped(0, total_duration)
        final_video = final_video.with_audio(final_audio)

    


    VORSCHAU_MODUS = False


    if VORSCHAU_MODUS:
        # --- VORSCHAU-EXPORT ---
        print("Starte schnellen Vorschau-Render...")
        
        (final_video
        .resized(0.5)           # 1. Auflösung halbieren (4x weniger Pixel!)
        .subclipped(0, 10)       # 2. Nur die ersten 5 Sekunden rendern
        .write_videofile(
            "vorschau_test.mp4", 
            fps=10,             # 3. Nur 10 Bilder pro Sekunde (reicht für Bewegungstests)
            codec="libx264",
            preset="ultrafast", # 4. FFmpeg-Turbo (Datei wird größer, rendert aber sofort)
            threads=4           # 5. Nutzt mehrere CPU-Kerne (je nach deinem PC, z.B. 4 oder 8)
        ))

    else:
        # --- DER GPU-TURBO EXPORT ---
        #final_video=final_video.subclipped(1, 9.5)       # 2. Nur die ersten X Sekunden rendern
        final_video.write_videofile(
            OUTPUT_NAME, 
            fps=30, 
            codec="h264_nvenc",          # <-- Hier sitzt die Magie (Nvidia Hardware Encoding)
            preset="fast",               # nvenc hat eigene Presets wie "fast", "medium", "slow"
            threads=4,
            ffmpeg_params=["-pix_fmt", "yuv420p"] # Verhindert Farb-Kompatibilitätsprobleme
        )


    
    #final_video.write_videofile(OUTPUT_NAME, fps=30, codec="libx264")
    
    
    
#GEHT NICHT!    
    #final_video.write_videofile(
    #    OUTPUT_NAME, 
    #    fps=30, 
    #    codec="libx264", 
    #    # Hier wird die Größe erzwungen:
    #    size=(1920, 1080) 
    #)
    print("--- Video erfolgreich exportiert! ---")

if __name__ == "__main__":
    build_video()