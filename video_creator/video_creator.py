import os
import sys
import math
import numpy as np
import json
from PIL import Image, ImageFilter, ImageDraw, ImageEnhance
import random
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

# Versuchen, das Bullet-Hole Bild zu laden
try:
    BULLET_IMG = Image.open("Bullet.png").convert("RGBA")
except FileNotFoundError:
    # Dummy, falls Datei fehlt
    BULLET_IMG = Image.new("RGBA", (50, 50), (100, 100, 100, 150))
    print("WARNUNG: Bullet.png nicht gefunden, nutze Dummy-Hole.")

def stamp_bullet_hole(canvas, target_coords, scale=1.0, offset_x=0, offset_y=0, random_r=15, alpha=1.0):
    """Stempelt das Bullet.png mit Skalierung, Offsets, Zufall UND Transparenz."""
    if scale != 1.0:
        new_size = (int(BULLET_IMG.size[0] * scale), int(BULLET_IMG.size[1] * scale))
        bullet = BULLET_IMG.resize(new_size, Image.Resampling.LANCZOS)
    else:
        bullet = BULLET_IMG.copy()
        
    # --- NEU: Die Alpha-Magie ---
    if alpha != 1.0:
        # Wir trennen Rot, Grün, Blau und Alpha
        r, g, b, a = bullet.split()
        # Wir multiplizieren die Deckkraft mit deinem Wert (z.B. 0.2)
        a = a.point(lambda p: int(p * alpha))
        # Und verheiraten die Kanäle wieder
        bullet = Image.merge("RGBA", (r, g, b, a))
        
    # Zufallsabweichung
    dx = random.uniform(-random_r, random_r)
    dy = random.uniform(-random_r, random_r)
    
    final_x = int(target_coords[0] + dx + offset_x - (bullet.size[0] / 2))
    final_y = int(target_coords[1] + dy + offset_y - (bullet.size[1] / 2))
    
    canvas.paste(bullet, (final_x, final_y), bullet)

def kill_green_spill(frame):
    """
    Erkennt grüne Licht-Reflexionen (Spill) an Kanten und 
    drückt den Grün-Wert auf das Maximum von Rot oder Blau herunter.
    """
    # Rot, Grün und Blau trennen
    r = frame[:, :, 0]
    g = frame[:, :, 1]
    b = frame[:, :, 2]
    
    # Wo ist das Maximum von Rot und Blau?
    max_rb = np.maximum(r, b)
    
    # Grün darf nicht stärker strahlen als Rot/Blau!
    new_g = np.minimum(g, max_rb-10)
    #new_g = g
    
    # Kanäle wieder zusammensetzen
    return np.dstack((r, new_g, b))

# Welches JSON soll geladen werden?
if len(sys.argv) > 1:
    CONFIG_DATEI = sys.argv[1]
else:
    CONFIG_DATEI = "../savegames/video_configs/VIDEO_MATCH000383.json"

with open(CONFIG_DATEI, "r", encoding="utf-8") as f:
    cfg = json.load(f)

YOUTUBE_SHORTS_MODUS = cfg.get("YOUTUBE_SHORTS", False)
FOCUS_WAYPOINTS_MODUS = cfg.get("FOCUS_WAYPOINTS", False)

# --- NEU: Die Toleranz für den Autofokus ---
FOCUS_SNAP_TOLERANCE = 0.05  # Ab welcher Nähe zum Ziel (z.B. 2.05) soll die Holzscheibe scharfgestellt werden?

# --- NEU: Die Waffe aus der JSON auslesen (Fallback auf "SteyrLP50", falls nichts drinsteht) ---
WAFFEN_PROFIL = cfg.get("WAFFEN_PROFIL", "SteyrLP50")
FOCUS_EFFEKT = cfg.get("FOCUS_EFFEKT", ["BLUR_LIGHT", "SPOTLIGHT", "COLOR"])
WAFFEN_PROFIL_GEGNER = cfg.get("WAFFEN_PROFIL_GEGNER", "RedDot") # Z.B. Steyr für den Gegner
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
        #"GS_THRESH": 88,
        "GS_THRESH": 75,
        "CROP": (0, 120, 1120, 720)
    },
    #"SteyrLP50": {
    #    "TARGETS": [(2138+26, 440+45), (1649+26, 442+45), (1173+26, 443+45), (697+26, 443+45), (212+26, 443+45)],
    #    "IDLE_IMG": "standbild_SteyrLP50.png",
    #    "SHOOT_VID": "schuss_SteyrLP50.mp4",
    #    "T_IMPACT": 1.50,
    #    "CLIP_DURATION": 2.7,
    #    "MIN_RECOIL": 0.6,
    #    "ZOOM": 1.3,          # <-- HIER: 25% reingezoomt!
    #    "OFFSET_X": -155-460-205-26,  # Ggf. anpassen, wenn das Bild durch den Zoom verrutscht
    #    "OFFSET_Y": -70+39-45,
    #    # --- NEU: Eigene Greenscreen-Werte ---
    #    "GS_COLOR": [57, 177, 65],
    #    "GS_THRESH": 88
    #}
    "SteyrLP50": {
        "TARGETS": [(2138+26, 440+45), (1649+26, 442+45), (1173+26, 443+45), (697+26, 443+45), (212+26, 443+45)],
        "IDLE_IMG": "standbild_Steyr_1080.png",
        "SHOOT_VID": "schuss_Steyr_1080p.mp4",
        #"T_IMPACT": 1.575,
        "T_IMPACT": 2.55,
        "CLIP_DURATION": 4.75,
        "MIN_RECOIL": 0.6,
        "ZOOM": 1.0,          # <-- HIER: 25% reingezoomt!
        "OFFSET_X":-786+2138-1649-38+5,  # Ggf. anpassen, wenn das Bild durch den Zoom verrutscht
        "OFFSET_Y": -70+39-45+40,
        # --- NEU: Eigene Greenscreen-Werte ---
        "GS_COLOR": [0, 185, 15],
        "GS_THRESH": 105,
        "CROP": None
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

# --- NEU: Die magische Trigger-Weiche ---
def is_shot(val):
    """Prüft, ob der Abzug gedrückt wird (Treffer oder Fehlschuss)"""
    if isinstance(val, int) and 0 <= val < 10: 
        return True # Echter Treffer (0-9)
    if isinstance(val, (int, float)) and val >= 10: 
        return True # Fehlschuss (+10 Offset)
    return False

# --- NEU: Koordinaten auch für Kommazahlen (Fake-Bewegungen) berechnen ---
# --- Koordinaten berechnen (mit +10 Fix) ---
def get_target_coords(val):
    # Wenn es ein Fehlschuss ist, ziehen wir die 10 für die Position einfach ab!
    if isinstance(val, (int, float)) and val >= 10:
        val = val - 10

    if isinstance(val, int):
        return TARGETS[val]
    elif isinstance(val, float):
        lower = int(math.floor(val))
        upper = int(math.ceil(val))
        
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
HIDE_OFFSET_Y = 1000 
HIDE_OFFSET_Y_GEGNER = 2000
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
        
        # --- DIE ZUWEISUNGS-WEICHE (SMARTER AUTOFOKUS) ---
        if FOCUS_WAYPOINTS_MODUS:
            # 1. Den "nackten" Wert berechnen (Fehlschuss-Offset +10 abziehen)
            raw_val = val - 10 if val >= 10 else val
            
            # 2. Welches Ziel ist am nächsten? (Sicherstellen, dass es zwischen 0 und 4 bleibt)
            closest_target = int(round(raw_val))
            closest_target = max(0, min(closest_target, len(TARGETS) - 1))
            
            # 3. Wie weit zielt die Waffe vom perfekten Zentrum weg?
            distance = abs(raw_val - closest_target)
            
            # 4. Das magische Kamera-Auge:
            if is_shot(val) or distance <= FOCUS_SNAP_TOLERANCE:
                # SCHUSS oder GANZ NAH DRAN: Fokus rastet knallhart auf der Holzscheibe ein!
                focus_pos = TARGETS[closest_target]
                FOCUS_WAYPOINTS.append((current_t, focus_pos))
                last_valid_focus = focus_pos
            else:
                # KÄNGURU-SCHWENK INS LEERE: 
                # Wir setzen absichtlich KEINEN Wegpunkt. Dadurch zieht die Engine die 
                # Schärfe später butterweich über diesen Moment hinweg zum nächsten echten Ziel!
                pass
        else:
            # Wenn nicht entkoppelt wird: Fokus läuft 1:1 stur synchron zur Waffe
            FOCUS_WAYPOINTS.append((current_t, pos))
            last_valid_focus = pos


# ==========================================
# NEU: Wegpunkte für die Gegner-Waffe
# ==========================================
GEGNER_WAYPOINTS = []
last_valid_pos_gegner = None

def find_target_gegner(start_idx, direction=1):
    idx = start_idx
    while 0 <= idx < len(SEQUENCE_GEGNER):
        val = SEQUENCE_GEGNER[idx]
        if isinstance(val, (int, float)) and val >= 0:
            return get_target_coords(val)
        idx += direction
    return TARGETS[2]

for i, val in enumerate(SEQUENCE_GEGNER):
    current_t = TIMING[i]

    if val == "UP":
        tgt = find_target_gegner(i, 1)
        pos = (tgt[0], tgt[1] + HIDE_OFFSET_Y_GEGNER)
        GEGNER_WAYPOINTS.append((current_t, pos))
        last_valid_pos_gegner = pos

    elif val == "DOWN":
        tgt = find_target_gegner(i, -1)
        pos = (tgt[0], tgt[1] + HIDE_OFFSET_Y_GEGNER)
        
        if last_valid_pos_gegner:
            hold_time = max(0, current_t - 1.5)
            if len(GEGNER_WAYPOINTS) > 0 and hold_time > GEGNER_WAYPOINTS[-1][0]:
                GEGNER_WAYPOINTS.append((hold_time, last_valid_pos_gegner))
                
        GEGNER_WAYPOINTS.append((current_t, pos))
        last_valid_pos_gegner = pos

    elif isinstance(val, (int, float)) and val >= 0:
        pos = get_target_coords(val)
        GEGNER_WAYPOINTS.append((current_t, pos))
        last_valid_pos_gegner = pos




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
            # --- DIE NEUE DYNAMISCHE KINEMATIK (POV-Spieler) ---
            # =======================================================
            if p_end[1] > p_start[1] + 500:
                # 1. Waffe geht DOWN (Schwerkraft)
                # POV ist schneller und zackiger: Quintic Ease-In (Hochzahl 5)
                # Fällt anfangs kurz sanft, sackt dann aber rasend schnell ab.
                progress = raw_progress ** 5
                
            elif p_start[1] > p_end[1] + 500:
                # 2. Waffe geht UP (Muskelkraft)
                # POV reißt die Waffe aggressiv hoch: Quintic Ease-Out (Hochzahl 5)
                # Schießt extrem schnell ins Bild und bremst hart im Ziel ein.
                progress = 1.0 - ((1.0 - raw_progress) ** 5)
                
            else:
                # 3. Normaler Schwenk zwischen Zielen
                # Hier machen wir den POV auch minimal aggressiver (Smootherstep statt Smoothstep)
                progress = raw_progress * raw_progress * raw_progress * (raw_progress * (raw_progress * 6.0 - 15.0) + 10.0)
                
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
    """Wackelt bei ALLEN Schüssen (Treffer und Fehlschüsse)"""
    for i, wp_time in enumerate(TIMING):
        val = SEQUENCE_POV[i]
        
        # HIER DEN HELFER NUTZEN:
        if is_shot(val):
            if wp_time < t < (wp_time + 0.2): 
                time_since_shot = t - wp_time
                shake_y = math.sin(time_since_shot * 100) * 6
                shake_x = math.cos(time_since_shot * 80) * 3
                return shake_x, shake_y
    return 0, 0

#SMOOTH_FOCUS = True

def get_aim_position(t):
    """
    DIE MASTER-KOORDINATE: Berechnet das exakte Fadenkreuz der Waffe 
    (inkl. Atmen und Rückstoß-Wackeln).
    """
    start_pos, end_pos, progress = get_current_target_info(t)
    
    # 1. Die cleane Basis-Koordinate
    base_x = start_pos[0] + (end_pos[0] - start_pos[0]) * progress
    base_y = start_pos[1] + (end_pos[1] - start_pos[1]) * progress
    
    # 2. Atmen und Wackeln hinzufügen
    breath_x = math.sin(t * 1.5) * 4
    breath_y = math.cos(t * 1.2) * 6
    base_shake_x, base_shake_y = get_camera_shake(t)
    
    aim_x = base_x + breath_x + (base_shake_x * 2)
    aim_y = base_y + breath_y + (base_shake_y * 2)
    
    return aim_x, aim_y

def get_focus_position(t):
    """Berechnet die exakte (X,Y) Position für die scharfe Maske."""
    
    if FOCUS_WAYPOINTS_MODUS:
        # 1. Smart-Autofokus (Der Kameramann entscheidet)
        # IMMER harter Cut, um den unschönen "Taschenlampen-Effekt" zu vermeiden.
        _, end_pos, _ = get_focus_target_info(t)
        return end_pos[0], end_pos[1]
    else:
        # 2. Stur an die Waffe gekoppelt (Klassischer Modus)
        # IMMER butterweich, da wir das atmende/wackelnde Fadenkreuz exakt abzapfen!
        return get_aim_position(t)

def get_gun_position(t):
    """Positioniert das Waffen-Bild (holt sich die Master-Koordinate + eigenen Offset)"""
    aim_x, aim_y = get_aim_position(t)
    
    final_x = aim_x + GUN_OFFSET_X
    final_y = aim_y + GUN_OFFSET_Y
    
    return (final_x, min(final_y, 915))


###################### GEGNER GEISTER POSITION ######################

active_gegner_gun = PROFILES.get(WAFFEN_PROFIL_GEGNER, PROFILES["SteyrLP50"])

def get_gegner_target_info(t):
    if t < GEGNER_WAYPOINTS[0][0]: return GEGNER_WAYPOINTS[0][1], GEGNER_WAYPOINTS[0][1], 1.0 
    if t >= GEGNER_WAYPOINTS[-1][0]: return GEGNER_WAYPOINTS[-1][1], GEGNER_WAYPOINTS[-1][1], 1.0 
        
    for i in range(len(GEGNER_WAYPOINTS) - 1):
        t_start, p_start = GEGNER_WAYPOINTS[i]
        t_end, p_end = GEGNER_WAYPOINTS[i+1]
        
        if t_start <= t < t_end:
            duration = t_end - t_start
            raw_progress = (t - t_start) / duration
            
            if p_end[1] > p_start[1] + 500: progress = raw_progress ** 3
            elif p_start[1] > p_end[1] + 500: progress = 1.0 - ((1.0 - raw_progress) ** 3)
            else: progress = raw_progress * raw_progress * (3.0 - 2.0 * raw_progress)
                
            return p_start, p_end, progress
    return GEGNER_WAYPOINTS[-1][1], GEGNER_WAYPOINTS[-1][1], 1.0

def get_gegner_gun_position(t):
    start_pos, end_pos, progress = get_gegner_target_info(t)
    base_x = start_pos[0] + (end_pos[0] - start_pos[0]) * progress
    base_y = start_pos[1] + (end_pos[1] - start_pos[1]) * progress
    
    # Gegner atmet leicht asynchron zum Spieler!
    breath_x = math.sin(t * 1.3) * 4
    breath_y = math.cos(t * 1.1) * 6
    
    # Kein Camera-Shake für den Gegner (er wackelt ja nicht an unserer Kamera)
    final_x = base_x + breath_x + active_gegner_gun["OFFSET_X"]
    final_y = base_y + breath_y + active_gegner_gun["OFFSET_Y"]
    return (final_x, min(final_y, 915))

# ==========================================
# NEU: Das entspannte Handgelenk (Nur bei DOWN)
# ==========================================

def get_gun_rotation(t):
    """Berechnet die Neigung der POV-Waffe (Handgelenk kippt schnell ab)"""
    for i in range(len(GUN_WAYPOINTS) - 1):
        t_start, p_start = GUN_WAYPOINTS[i]
        t_end, p_end = GUN_WAYPOINTS[i+1]
        
        if t_start <= t < t_end:
            # Ist es eine DOWN-Bewegung?
            if p_end[1] > p_start[1] + 500:
                duration = t_end - t_start
                raw_progress = (t - t_start) / duration
                
                # Hoch 0.5 (Wurzel) = Drehung startet SOFORT, noch bevor die Waffe tief fällt!
                return 7.0 * (raw_progress ** 1.25)
    return 0.0

def get_gegner_gun_rotation(t):
    """Berechnet die Neigung für den Gegner"""
    for i in range(len(GEGNER_WAYPOINTS) - 1):
        t_start, p_start = GEGNER_WAYPOINTS[i]
        t_end, p_end = GEGNER_WAYPOINTS[i+1]
        
        if t_start <= t < t_end:
            if p_end[1] > p_start[1] + 500:
                duration = t_end - t_start
                raw_progress = (t - t_start) / duration
                
                # Gegner dreht sich etwas weniger (10 Grad)
                return 3.5 * (raw_progress ** 0.5)
    return 0.0



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
        
        # ==========================================================
        # NEU: Einschusslöcher stempeln (Die Tweak-Zone!)
        # ==========================================================
        H_SCALE = 0.18       # Deine perfekt abgestimmte Größe
        H_OFF_X = -13        # Manuelle Korrektur X
        H_OFF_Y = 25         # Manuelle Korrektur Y
        H_RAND_R = 12        # Maximale Zufallsabweichung in Pixeln
        
        H_ALPHA_MISS = 0.8   # Hohe Deckkraft für Fehlschüsse (+10)
        H_ALPHA_HIT = 0.5    # Sanfte Deckkraft für echte Treffer (0-9)
        
        for i, wp_time in enumerate(TIMING):
            # 1. SPIELER (POV)
            val_pov = SEQUENCE_POV[i]
            # is_shot() erkennt jetzt echte Treffer UND Fehlschüsse!
            if is_shot(val_pov) and wp_time <= t:
                random.seed(str(wp_time) + "_pov") 
                base_coords = get_target_coords(val_pov)
                
                # Alpha festlegen (Fehlschuss oder Hit?)
                current_alpha = H_ALPHA_MISS if val_pov >= 10 else H_ALPHA_HIT
                
                # Stempeln (mit dem neuen Parameter alpha=current_alpha)
                stamp_bullet_hole(img_copy, base_coords, H_SCALE, H_OFF_X, H_OFF_Y, H_RAND_R, alpha=current_alpha)
                
            # 2. GEGNER (GEIST)
            val_gegner = SEQUENCE_GEGNER[i]
            if is_shot(val_gegner) and wp_time <= t:
                random.seed(str(wp_time) + "_gegner") 
                base_coords = get_target_coords(val_gegner)
                
                current_alpha = H_ALPHA_MISS if val_gegner >= 10 else H_ALPHA_HIT
                
                stamp_bullet_hole(img_copy, base_coords, H_SCALE, H_OFF_X, H_OFF_Y, H_RAND_R, alpha=current_alpha)
        # ==========================================================
        
        # Erst JETZT den Draw-Kontext für die LEDs aufrufen, 
        # damit sie über die Löcher gemalt werden!
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
                # NUR GANZZAHLEN UNTER 10 ERLAUBT:
                if isinstance(val, int) and 0 <= val < 10:
                    if wp_time <= t <= (wp_time + 0.15): 
                        flash_pos = get_target_coords(val)
                        flash_x, flash_y = flash_pos[0], flash_pos[1]
                        flash_radius = 175  
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


    # C1 PISTOLE (Greenscreen & Trigger-System) ---
    
    # 1. Effekte dynamisch zusammenbauen
    gun_effects = []
    
    # Hat die Waffe einen CROP-Parameter? Dann füge ihn als Erstes hinzu!
    if active_gun.get("CROP") is not None:
        cx1, cy1, cx2, cy2 = active_gun["CROP"]
        gun_effects.append(vfx.Crop(x1=cx1, y1=cy1, x2=cx2, y2=cy2))
        
    # Danach immer den Greenscreen hinzufügen
    gun_effects.append(
        vfx.MaskColor(
            color=active_gun.get("GS_COLOR", [57, 177, 65]), 
            threshold=active_gun.get("GS_THRESH", 88), 
            stiffness=10
        )
    )
    
    # 2. Assets dynamisch aus dem Waffen-Profil laden (und Grün-Schimmer killen!)
    idle_clip = (ImageClip(active_gun["IDLE_IMG"])
                 .with_duration(total_duration)
                 .with_effects(gun_effects)
                 .image_transform(kill_green_spill)) # <--- NEU: Zieht das giftige Grün aus den Rändern!
                 
    recoil_clip = (VideoFileClip(active_gun["SHOOT_VID"])
                   .without_audio()
                   .with_effects(gun_effects)
                   .image_transform(kill_green_spill)) # <--- NEU
                   
    # --- NEU: DEN ZOOM ANWENDEN ---
    if active_gun["ZOOM"] != 1.0:
        idle_clip = idle_clip.resized(active_gun["ZOOM"])
        recoil_clip = recoil_clip.resized(active_gun["ZOOM"])

    # 3. Parameter aus dem Profil auslesen
    T_IMPACT = active_gun["T_IMPACT"]
    CLIP_DURATION = active_gun["CLIP_DURATION"]
    MIN_RECOIL = active_gun["MIN_RECOIL"]
    
    # ==========================================
    # C2. GEGNER-PISTOLE (Greenscreen & Assets)
    # ==========================================
    
    # 1. Effekte dynamisch zusammenbauen (für den Gegner)
    gegner_effects = []
    
    if active_gegner_gun.get("CROP") is not None:
        cx1, cy1, cx2, cy2 = active_gegner_gun["CROP"]
        gegner_effects.append(vfx.Crop(x1=cx1, y1=cy1, x2=cx2, y2=cy2))
        
    gegner_effects.append(
        vfx.MaskColor(
            color=active_gegner_gun.get("GS_COLOR", [57, 177, 65]), 
            threshold=active_gegner_gun.get("GS_THRESH", 88), 
            stiffness=8
        )
    )
    
    # 2. Gegner-Assets laden
    gegner_idle_clip = (ImageClip(active_gegner_gun["IDLE_IMG"])
                        .with_duration(total_duration)
                        .with_effects(gegner_effects)
                        .image_transform(kill_green_spill)) # <--- NEU: Zieht das giftige Grün aus den Rändern!
                 
    gegner_recoil_clip = (VideoFileClip(active_gegner_gun["SHOOT_VID"])
                          .without_audio()
                          .with_effects(gegner_effects)
                          .image_transform(kill_green_spill)) # <--- NEU
                   
    # 3. Zoom für den Gegner anwenden
    if active_gegner_gun["ZOOM"] != 1.0:
        gegner_idle_clip = gegner_idle_clip.resized(active_gegner_gun["ZOOM"])
        gegner_recoil_clip = gegner_recoil_clip.resized(active_gegner_gun["ZOOM"])

    # 4. Parameter für den Gegner auslesen
    G_T_IMPACT = active_gegner_gun["T_IMPACT"]
    G_CLIP_DURATION = active_gegner_gun["CLIP_DURATION"]
    G_MIN_RECOIL = active_gegner_gun["MIN_RECOIL"]

    # ==========================================
    # --- DER DYNAMISCHE MOTOR FÜR DEN GEGNER ---
    # ==========================================
    def get_active_gegner_clip_time(t):
        """Spielt das Video (Greenscreen-Rückstoß) NUR bei echten Schüssen ab!"""
        valid_shots = [TIMING[i] for i, val in enumerate(SEQUENCE_GEGNER) if is_shot(val)]
        
        for i in range(len(valid_shots) - 1, -1, -1):
            wp_time = valid_shots[i]
            ideal_start = wp_time - G_T_IMPACT
            
            if i > 0:
                prev_wp_time = valid_shots[i-1]
                actual_start = max(prev_wp_time + G_MIN_RECOIL, ideal_start)
            else:
                actual_start = ideal_start
                
            end_time = wp_time + (G_CLIP_DURATION - G_T_IMPACT)
            
            if actual_start <= t < end_time:
                local_t = G_T_IMPACT + (t - wp_time)
                if local_t < 0:
                    return None
                return local_t
        return None

    def make_gegner_gun_frame(t):
        local_t = get_active_gegner_clip_time(t)
        if local_t is not None:
            return gegner_recoil_clip.get_frame(local_t)
        return gegner_idle_clip.get_frame(t)

    def make_gegner_gun_mask_frame(t):
        local_t = get_active_gegner_clip_time(t)
        if local_t is not None:
            return gegner_recoil_clip.mask.get_frame(local_t)
        return gegner_idle_clip.mask.get_frame(t)

    # Den dynamischen Clip für den Gegner zusammenstecken
    gegner_gun_clip_dynamic = VideoClip(frame_function=make_gegner_gun_frame, duration=total_duration)
    gegner_gun_mask_dynamic = VideoClip(frame_function=make_gegner_gun_mask_frame, is_mask=True, duration=total_duration)
    # ---> DIESE ZEILE HAT GEFEHLT! (Bild und Maske verheiraten) <---
    gegner_gun_clip = gegner_gun_clip_dynamic.with_mask(gegner_gun_mask_dynamic)
    # Bewegung, Atmung UND Rotation auf den Gegner anwenden
    gegner_gun_clip = gegner_gun_clip.with_position(get_gegner_gun_position)
    # expand=False ist EXTREM WICHTIG, damit der Greenscreen-Rand nicht zerschossen wird!
    gegner_gun_clip = gegner_gun_clip.with_effects([vfx.Rotate(angle=get_gegner_gun_rotation, expand=False)])
                            

    # 3. Die professionelle Time-Warp-Logik
    def get_active_gun_clip_time(t):
        """Spielt das Video (Greenscreen-Rückstoß) NUR bei echten Schüssen ab!"""
        # 1. Wir filtern uns schnell alle ECHTEN Schuss-Zeiten heraus
        valid_shots = [TIMING[i] for i, val in enumerate(SEQUENCE_POV) if is_shot(val)]
        
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
    # expand=False verhindert, dass sich das Bild beim Drehen aufbläht
    gun_clip = gun_clip.with_effects([vfx.Rotate(angle=get_gun_rotation, expand=False)])

    # --- D. SANDWICH BAUEN & EXPORT ---
    
    # Wir leiten die Shake-Werte an die Hintergrund-Ebenen weiter
    def bg_position(t):
        return get_camera_shake(t)

    # Wenn der Ghost-Modus an ist, Gegner transparent machen
    if GHOST_MODUS_GEGNER:
        gegner_gun_clip = gegner_gun_clip.with_opacity(0.5) # Leicht durchsichtig
        
    # Auch der POV Spieler kann ein Geist sein (je nach Konfiguration)
    GHOST_MODUS = cfg.get("GHOST_MODUS", False)
    if GHOST_MODUS:
        gun_clip = gun_clip.with_opacity(0.5) 

    # Reihenfolge: Basis -> Scharfer Fokus -> Gegner (Geist) -> POV Spieler (Vordergrund)
    final_video = CompositeVideoClip(
        [
            bg_base.with_position(bg_position), 
            bg_sharp_masked.with_position(bg_position), 
            gegner_gun_clip, # <-- Fehler behoben (nutzt jetzt automatisch get_gegner_gun_position)
            gun_clip         # <-- Fehler behoben (nutzt jetzt automatisch get_gun_position)
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
            val_pov = SEQUENCE_POV[i]
            val_gegner = SEQUENCE_GEGNER[i]
            
            # 1. Hat der POV-Spieler geschossen? (Treffer oder Fehlschuss)
            if is_shot(val_pov):
                start_time = wp_time - POV_AUDIO_IMPACT
                if start_time < 0:
                    ac = pov_audio_base.subclipped(-start_time).with_start(0)
                else:
                    ac = pov_audio_base.with_start(start_time)
                audio_clips.append(ac)
                
            # 2. Hat der Gegner geschossen? (Unabhängige Abfrage!)
            if is_shot(val_gegner):
                start_time = wp_time - GEGNER_AUDIO_IMPACT
                if start_time < 0:
                    ac = gegner_audio_base.subclipped(-start_time).with_start(0)
                else:
                    ac = gegner_audio_base.with_start(start_time)
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