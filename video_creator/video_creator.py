import os
import sys
import math
import numpy as np
import json
from PIL import Image, ImageFilter, ImageDraw, ImageEnhance
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

YOUTUBE_SHORTS_MODUS = cfg.get("YOUTUBE_SHORTS", False)
FOCUS_WAYPOINTS_MODUS = cfg.get("FOCUS_WAYPOINTS", False)

# --- NEU: Die Waffe aus der JSON auslesen (Fallback auf "SteyrLP50", falls nichts drinsteht) ---
WAFFEN_PROFIL = cfg.get("WAFFEN_PROFIL", "SteyrLP50")
FOCUS_EFFEKT = cfg.get("FOCUS_EFFEKT", ["BLUR_LIGHT", "SPOTLIGHT", "COLOR"])
WAFFEN_PROFIL_GEGNER = cfg.get("WAFFEN_PROFIL_GEGNER", "SteyrLP50") # Z.B. Steyr für den Gegner
GHOST_MODUS_GEGNER = cfg.get("GHOST_MODUS_GEGNER", True)          # Der Gegner ist standardmäßig ein Geist

OUTPUT_NAME = CONFIG_DATEI.replace(".json", "_Render.mp4")
print(f"OUTPUT_NAME: {OUTPUT_NAME}")

BG_IMAGE = "Schiessstand_upscayl_3x_upscayl-standard-4x.png"

# ==========================================
# WAFFEN-PROFILE (Alle Einstellungen auf einen Blick)
# ==========================================
PROFILES = {
    "RedDot": {
        "TARGETS": [(2138+26, 440+45), (1649+26, 442+45), (1173+26, 443+45), (697+26, 443+45), (212+26, 443+45)],
        "IDLE_IMG": "standbild.png",
        "SHOOT_VID": "schuss.mp4",
        "T_IMPACT": 2.6,
        "CLIP_DURATION": 4.75,
        "MIN_RECOIL": 0.6,
        "ZOOM": 1.0,           # 1.0 = Originalgröße
        "OFFSET_X": -155-460-26,  # Individueller Offset für die Waffe
        "OFFSET_Y": -70-45,
        # --- NEU: Eigene Greenscreen-Werte ---
        "GS_COLOR": [57, 177, 65],
        "GS_THRESH": 88
    },
    "SteyrLP50": {
        "TARGETS": [(2138+26, 440+45), (1649+26, 442+45), (1173+26, 443+45), (697+26, 443+45), (212+26, 443+45)],
        "IDLE_IMG": "standbild_SteyrLP50.png",
        "SHOOT_VID": "schuss_SteyrLP50.mp4",
        "T_IMPACT": 1.50,
        "CLIP_DURATION": 2.7,
        "MIN_RECOIL": 0.6,
        "ZOOM": 1.3,          # <-- HIER: 25% reingezoomt!
        "OFFSET_X": -155-460-205-26,  # Ggf. anpassen, wenn das Bild durch den Zoom verrutscht
        "OFFSET_Y": -70+39-45,
        # --- NEU: Eigene Greenscreen-Werte ---
        "GS_COLOR": [57, 177, 65],
        "GS_THRESH": 88
    }
}

# Das aktive Profil laden
active_gun = PROFILES.get(WAFFEN_PROFIL, PROFILES["RedDot"])

TARGETS = active_gun["TARGETS"]
GUN_OFFSET_X = active_gun["OFFSET_X"]
GUN_OFFSET_Y = active_gun["OFFSET_Y"]


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
#TARGETS = [
#    (2138, 440), # Ziel 0 (ganz links)
#    (1649, 442), # Ziel 1
#    (1173, 443), # Ziel 2 (Mitte)
#    (697, 443), # Ziel 3
#    (212, 443) # Ziel 4 (ganz rechts)
#]

#TARGETS = [
#    (2128, 430), # Ziel 0 (ganz links)
#    (1639, 432), # Ziel 1
#    (1163, 433), # Ziel 2 (Mitte)
#    (687, 433), # Ziel 3
#    (202, 433) # Ziel 4 (ganz rechts)
#]


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
last_valid_focus = None
FOCUS_WAYPOINTS = [] # <-- NEU: Eigene Wegpunkte für die Schärfe

for i, val in enumerate(SEQUENCE_POV):
    current_t = TIMING[i]

    if val == "UP":
        tgt = find_target(i, 1)
        pos = (tgt[0], tgt[1] + HIDE_OFFSET_Y)
        GUN_WAYPOINTS.append((current_t, pos))
        FOCUS_WAYPOINTS.append((current_t, pos))
        last_valid_pos = pos
        last_valid_focus = pos

    elif val == "DOWN":
        tgt = find_target(i, -1)
        pos = (tgt[0], tgt[1] + HIDE_OFFSET_Y)
        
        if last_valid_pos:
            hold_time = max(0, current_t - 1.5)
            if len(GUN_WAYPOINTS) > 0 and hold_time > GUN_WAYPOINTS[-1][0]:
                GUN_WAYPOINTS.append((hold_time, last_valid_pos))
                FOCUS_WAYPOINTS.append((hold_time, last_valid_focus))
                
        GUN_WAYPOINTS.append((current_t, pos))
        FOCUS_WAYPOINTS.append((current_t, pos))
        last_valid_pos = pos
        last_valid_focus = pos

    elif isinstance(val, (int, float)) and val >= 0:
        pos = get_target_coords(val)
        GUN_WAYPOINTS.append((current_t, pos))
        last_valid_pos = pos
        
        # --- DIE ZUWEISUNGS-WEICHE ---
        if FOCUS_WAYPOINTS_MODUS:
            # Wenn entkoppelt werden soll: Nur Ganzzahlen (echte Ziele) in den Fokus!
            if isinstance(val, int):
                FOCUS_WAYPOINTS.append((current_t, pos))
                last_valid_focus = pos
        else:
            # Wenn nicht entkoppelt wird: Fokus läuft 1:1 synchron zur Waffe
            FOCUS_WAYPOINTS.append((current_t, pos))
            last_valid_focus = pos



# Offset: Wie weit ist der rote Punkt vom Video-Mittelpunkt entfernt?
# (Musst du ggf. anpassen, damit das Visier genau auf dem Ziel liegt)
#GUN_OFFSET_X = -155-460
#GUN_OFFSET_Y = -70
# Zeit-Parameter
START_DELAY = 2.10#/SPEED_FAKTOR      # Wartezeit vor dem ersten Sprung
MOVE_DURATION = 2.0#/SPEED_FAKTOR   # Wie lange dauert der Schwenk (Torquen)? 2.8
AIM_DURATION = 2.05#/SPEED_FAKTOR    # Wie lange wird gezielt/geschossen?
STEP_TIME = MOVE_DURATION + AIM_DURATION

# ==========================================
# 2. DIE MATHEMATISCHE ENGINE (Bewegung)
# ==========================================

def get_current_target_info(t):
    """Ermittelt Basis-Infos für die Waffe (und YouTube Shorts Kamera)"""
    if t < GUN_WAYPOINTS[0][0]:
        return GUN_WAYPOINTS[0][1], GUN_WAYPOINTS[0][1], 1.0 
        
    if t >= GUN_WAYPOINTS[-1][0]:
        return GUN_WAYPOINTS[-1][1], GUN_WAYPOINTS[-1][1], 1.0 
        
    for i in range(len(GUN_WAYPOINTS) - 1):
        t_start, p_start = GUN_WAYPOINTS[i]
        t_end, p_end = GUN_WAYPOINTS[i+1]
        
        if t_start <= t < t_end:
            duration = t_end - t_start
            raw_progress = (t - t_start) / duration
            
            # =======================================================
            # --- DIE NEUE DYNAMISCHE KINEMATIK (Physik-Engine) ---
            # =======================================================
            if p_end[1] > p_start[1] + 500:
                # 1. Waffe geht DOWN (Schwerkraft -> Cubic Ease-In)
                # Startet ganz sanft und fällt dann exponentiell schneller nach unten.
                progress = raw_progress ** 3
                
            elif p_start[1] > p_end[1] + 500:
                # 2. Waffe geht UP (Muskelkraft -> Cubic Ease-Out)
                # Reißt extrem schnell aus dem Off nach oben und bremst sanft im Ziel ein.
                progress = 1.0 - ((1.0 - raw_progress) ** 3)
                
            else:
                # 3. Normaler Schwenk (Körperdrehung -> Smoothstep Ease-In-Out)
                # Sanftes Anfahren und sanftes Abbremsen.
                progress = raw_progress * raw_progress * (3.0 - 2.0 * raw_progress)
                
            return p_start, p_end, progress
            
    return GUN_WAYPOINTS[-1][1], GUN_WAYPOINTS[-1][1], 1.0

def get_focus_target_info(t):
    """Ermittelt Basis-Infos NUR für den Fokus (berücksichtigt die Entkopplung)"""
    if t < FOCUS_WAYPOINTS[0][0]:
        return FOCUS_WAYPOINTS[0][1], FOCUS_WAYPOINTS[0][1], 1.0 
    if t >= FOCUS_WAYPOINTS[-1][0]:
        return FOCUS_WAYPOINTS[-1][1], FOCUS_WAYPOINTS[-1][1], 1.0 
        
    for i in range(len(FOCUS_WAYPOINTS) - 1):
        t_start, p_start = FOCUS_WAYPOINTS[i]
        t_end, p_end = FOCUS_WAYPOINTS[i+1]
        
        if t_start <= t < t_end:
            duration = t_end - t_start
            raw_progress = (t - t_start) / duration
            
            # Fokus nutzt die identische Physik, damit Schärfe und Waffe exakt synchron laufen!
            if p_end[1] > p_start[1] + 500:
                progress = raw_progress ** 3
            elif p_start[1] > p_end[1] + 500:
                progress = 1.0 - ((1.0 - raw_progress) ** 3)
            else:
                progress = raw_progress * raw_progress * (3.0 - 2.0 * raw_progress)
                
            return p_start, p_end, progress
            
    return FOCUS_WAYPOINTS[-1][1], FOCUS_WAYPOINTS[-1][1], 1.0

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
    return 0, 0 

SMOOTH_FOCUS = False

def get_focus_position(t):
    """Berechnet die exakte (X,Y) Position für die scharfe Maske."""
    # HIER ist die Weiche: Wir nutzen den neuen Fokus-Motor!
    start_pos, end_pos, progress = get_focus_target_info(t)
    
    if SMOOTH_FOCUS:
        x = start_pos[0] + (end_pos[0] - start_pos[0]) * progress
        y = start_pos[1] + (end_pos[1] - start_pos[1]) * progress
        return x, y
    else:
        # Sniper-Modus
        if progress < 1.0:
            return end_pos
        else:
            return end_pos

def get_gun_position(t):
    """Gleitet sanft, nutzt den normalen Motor für die Pistole!"""
    # HIER nutzen wir weiterhin den normalen Waffen-Motor!
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
    
    final_y = min(final_y, 915)
    return (final_x, final_y)

# ==========================================
# 3. VIDEO-ZUSAMMENBAU (MoviePy v2.2.1)
# ==========================================
def build_video():
    global OUTPUT_NAME  # <--- DIESE ZEILE HINZUFÜGEN!
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
            lx = target_pos[0] + 80 + 13 -26
            ly = target_pos[1] - 80 + 31 -45
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

    def make_base_bg_frame(t):
        """Das ist unsere unterste Sandwich-Scheibe (Der Raum außerhalb des Fokus)"""
        frame = make_bg_frame(t)
        img = Image.fromarray(frame)
        
        # --- DIE FILTER-KETTE (Mehrere Effekte nahtlos kombinierbar!) ---
        if "BLUR_HEAVY" in FOCUS_EFFEKT:
            img = img.filter(ImageFilter.GaussianBlur(radius=5))
            
        if "BLUR_LIGHT" in FOCUS_EFFEKT:
            img = img.filter(ImageFilter.GaussianBlur(radius=1.8))
            
        if "COLOR" in FOCUS_EFFEKT:
            # Sin City / Matrix: Reduziert die Farbe auf 10%
            img = ImageEnhance.Color(img).enhance(0.85)
            
        if "SPOTLIGHT" in FOCUS_EFFEKT:
            # Der Raum wird um 60% abgedunkelt (0.4 = 40% Resthelligkeit)
            img = ImageEnhance.Brightness(img).enhance(0.825)
            
        return np.array(img)

    # 4. MoviePy die Kontrolle übergeben
    bg_sharp = VideoClip(frame_function=make_bg_frame, duration=total_duration)
    bg_base = VideoClip(frame_function=make_base_bg_frame, duration=total_duration) # <-- Früher bg_blurred
    
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
            
            # 1. Basis-Fokus
            current_radius = 130
            
            # 2. Gibt es gerade einen Schuss-Blitz? (Entkoppelt!)
            flash_x, flash_y = None, None
            flash_radius = 0
            
            for i, wp_time in enumerate(TIMING):
                val = SEQUENCE_POV[i]
                if isinstance(val, int) and val >= 0:
                    if wp_time <= t <= (wp_time + 0.15): 
                        # HIER IST DER TRICK: Wir holen uns die exakte, 
                        # unbewegliche Position des Ziels, auf das geschossen wird!
                        flash_pos = get_target_coords(val)
                        flash_x, flash_y = flash_pos[0], flash_pos[1]
                        flash_radius = 175  # Der größere Lichtblitz
                        break
            
            # 3. CACHE-CHECK: Wir speichern jetzt auch die Flash-Werte im Cache
            cache_key = (cx, cy, flash_x, flash_y)
            if hasattr(self, 'last_cache_key') and self.last_cache_key == cache_key and self.last_mask is not None:
                return self.last_mask
            
            # 4. NEUBERECHNUNG
            y, x = np.ogrid[:h, :w]
            feather = 75
            
            # A) Die normale Kamera (Basis-Radius)
            dist_base = np.sqrt((x - cx)**2 + (y - cy)**2)
            mask = np.clip((current_radius + feather - dist_base) / feather, 0, 1)
            
            # B) Der entkoppelte Impact-Blitz (falls einer existiert)
            if flash_x is not None:
                dist_flash = np.sqrt((x - flash_x)**2 + (y - flash_y)**2)
                mask_flash = np.clip((flash_radius + feather - dist_flash) / feather, 0, 1)
                
                # Wir legen beide Masken übereinander (der jeweils hellere Wert gewinnt!)
                mask = np.maximum(mask, mask_flash)
            
            # 5. CACHE UPDATEN
            self.last_cache_key = cache_key
            self.last_mask = mask
            
            return mask



    # 1. Die Klasse instanziieren und die Dauer festlegen
    focus_mask = DynamicFocusMask(bg_w, bg_h).with_duration(total_duration)
    
    # 2. Die Maske auf das scharfe Bild anwenden
    bg_sharp_masked = bg_sharp.with_mask(focus_mask)


    # --- C. PISTOLE (Greenscreen & Trigger-System) ---
    
    # 1. Effekte definieren (Crop & Greenscreen dynamisch!)
    gun_effects = [
        vfx.Crop(x1=0, y1=120, x2=1120, y2=720), 
        vfx.MaskColor(
            color=active_gun.get("GS_COLOR", [57, 177, 65]), 
            threshold=active_gun.get("GS_THRESH", 88), 
            stiffness=8
        )
    ]
    
    # 2. Assets dynamisch aus dem Waffen-Profil laden
    idle_clip = (ImageClip(active_gun["IDLE_IMG"])
                 .with_duration(total_duration)
                 .with_effects(gun_effects))
                 
    recoil_clip = (VideoFileClip(active_gun["SHOOT_VID"])
                   .without_audio()
                   .with_effects(gun_effects))
                   
    # --- NEU: DEN ZOOM ANWENDEN ---
    if active_gun["ZOOM"] != 1.0:
        idle_clip = idle_clip.resized(active_gun["ZOOM"])
        recoil_clip = recoil_clip.resized(active_gun["ZOOM"])

    # 3. Parameter aus dem Profil auslesen
    T_IMPACT = active_gun["T_IMPACT"]
    CLIP_DURATION = active_gun["CLIP_DURATION"]
    MIN_RECOIL = active_gun["MIN_RECOIL"]
    
#    # 2. Assets laden und vorbereiten
#    idle_clip = (ImageClip("standbild.png")
#                 .with_duration(total_duration)
#                 .with_effects(gun_effects))
#    # NEU: Wir laden das KOMPLETTE Video (0 bis 4.75s)
#    recoil_clip = (VideoFileClip("schuss.mp4")
#                   .without_audio()
#                   .with_effects(gun_effects))
#    # --- Die Parameter deiner Animation ---
#    T_IMPACT = 2.6          # Bei welcher Sekunde im Video fällt der Schuss?
#    CLIP_DURATION = 4.75    # Wie lang ist das schuss.mp4 insgesamt?
#    MIN_RECOIL = 0.6        # Wie lange (in Sekunden) muss der Rückstoß des 
                            # VORHERIGEN Schusses mindestens laufen, bevor er abgebrochen wird?
                            
#    # 2. Assets laden und vorbereiten
#    idle_clip = (ImageClip("standbild_SteyrLP50.png")
#                 .with_duration(total_duration)
#                 .with_effects(gun_effects))
#    # NEU: Wir laden das KOMPLETTE Video (0 bis 4.75s)
#    recoil_clip = (VideoFileClip("schuss_SteyrLP50.mp4")
#                   .without_audio()
#                   .with_effects(gun_effects))
#    # --- Die Parameter deiner Animation ---
#    T_IMPACT = 1.50          # Bei welcher Sekunde im Video fällt der Schuss?
#    CLIP_DURATION = 3.00    # Wie lang ist das schuss.mp4 insgesamt?
#    MIN_RECOIL = 0.6        # Wie lange (in Sekunden) muss der Rückstoß des 
#                           # VORHERIGEN Schusses mindestens laufen, bevor er abgebrochen wird?

                            

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
    
    # --- NEU: DER GHOST-MODUS ---
    GHOST_MODUS = cfg.get("GHOST_MODUS", False) # Das liest du oben bei den anderen cfg.get() ein
    if GHOST_MODUS:
        gun_clip = gun_clip.with_opacity(0.4) # 40% Deckkraft = Perfekter Geister-Look!
    
    # 6. Schwenken und Shake aus der Engine anwenden
    gun_clip = gun_clip.with_position(get_gun_position)



    # --- D. SANDWICH BAUEN & EXPORT ---
    
    # Wir leiten die Shake-Werte an die Hintergrund-Ebenen weiter
    def bg_position(t):
        return get_camera_shake(t)

    # Reihenfolge: 1. Basis-Raum -> 2. Scharfer Fokusbereich -> 3. Pistole
    final_video = CompositeVideoClip(
        [
            bg_base.with_position(bg_position), # <-- HIER umbenannt
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
        print("--- Vorschau fertig! ---")
        return  # <--- HIER IST DEIN RETTER! Er bricht die Funktion hier ab.

    if YOUTUBE_SHORTS_MODUS:
        print("Wandle Video in dynamischen Kamera-Ausschnitt um (ohne Ränder)...")
        
        # 1. Die Kamera-Intelligenz: Wo ist das Visier gerade?
        def get_pan_x(t):
            start_pos, end_pos, progress = get_current_target_info(t)
            base_x = start_pos[0] + (end_pos[0] - start_pos[0]) * progress
            
            # Wir wollen 1080 Pixel Breite. Die Kamera soll base_x genau in der Mitte haben
            x1 = base_x - (1080 / 2)
            
            # Crash-Schutz: Die Kamera darf nicht links oder rechts über den Rand fallen!
            x1 = max(0, min(x1, 2400 - 1080))
            return int(x1)
            
        # 2. Den "Kameramann" auf das breite Video anwenden
        def dynamic_crop(get_frame, t):
            frame = get_frame(t)
            x1 = get_pan_x(t)
            # Schneidet das Bild in der Breite auf 1080px zu, Höhe (920px) bleibt gleich
            return frame[:, x1:x1+1080, :]
            
        # 3. Wir überschreiben final_video direkt mit dem zugeschnittenen Clip (1080x920)
        # 3. Wir überschreiben final_video direkt mit dem zugeschnittenen Clip (1080x920)
        final_video = (final_video
                       .transform(dynamic_crop)
                       .with_audio(final_video.audio)
                       .with_mask(None)) # <--- HIER IST DER RETTER! Wir löschen die 2400px Maske.
        
        # Damit das normale Breitbild-Video nicht überschrieben wird:
        OUTPUT_NAME = OUTPUT_NAME.replace("_Render.mp4", "_Shorts.mp4")


    # ========================================================
    # --- DER GPU-TURBO EXPORT (Immer ausführen!) ---
    # ========================================================
    print(f"Schreibe Datei: {OUTPUT_NAME}")
    final_video.write_videofile(
        OUTPUT_NAME, 
        fps=30, 
        codec="h264_nvenc",          
        preset="fast",               
        threads=4,
        ffmpeg_params=["-pix_fmt", "yuv420p"] 
    )

    print("--- Video erfolgreich exportiert! ---")

if __name__ == "__main__":
    build_video()