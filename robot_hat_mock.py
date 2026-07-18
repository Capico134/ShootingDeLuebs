import tkinter as tk
from PIL import Image, ImageTk#, ImageFont  # Pillow muss installiert sein: `pip install pillow`
import zipfile
import math # für krone
import io #für zipfile

class LEDMockGUI:
    def __init__(self, master, led_items, on_button_click, name_vars, gegner_var):
        master.title("Schießstand Anzeige")
        master.geometry("800x319")
        master.configure(bg="gray95")
        master.wm_attributes("-topmost", True)  # Immer im Vordergrund
        self.canvas = tk.Canvas(master, width=870, height=319, bg="gray95")
        self.canvas.pack()
        
        #Mit Pillow
        with zipfile.ZipFile("data.pak", "r") as pak: 
            img = Image.open(io.BytesIO(pak.read("Schiessstand.png"))) 
        tk_img = ImageTk.PhotoImage(img)
        self.canvas.create_image(0, 0, anchor="nw", image=tk_img)
        self.image = tk_img # Referenz halten!        
        
        self.fokus_player = 0
        self.name_vars = name_vars  # Die Variablen speichern
        self.gegner_var = gegner_var  # <--- NEU gespeichert
        
        # --- Transparente Texte auf dem Canvas ---
        self.text_p1 = self.canvas.create_text(
            250, 300, text=f"Fokus: {self.name_vars[0].get()}", 
            fill="darkcyan", font=("Arial", 12, "bold")
        )
        
        self.text_p2 = self.canvas.create_text(
            550, 300, text=f"Fokus: {self.name_vars[1].get()}", 
            fill="gray50", font=("Arial", 12, "normal")
        )
        
        # --- NEU: Mute-Button Setup ---
        self.is_muted = tk.BooleanVar(value=False) # Speichert den aktuellen Status
        
        # Text unten rechts platzieren (x=750, y=300)
        self.mute_text = self.canvas.create_text(
            830, 300, text="Sound On", 
            fill="gray50", font=("Arial", 10, "bold")
        )
        
        # --- DER MAGISCHE TRACE ---
        # "write" bedeutet: Sobald sich der Wert der Variable ändert, rufe die Funktion auf
        self.name_vars[0].trace_add("write", lambda *args: self._update_names())
        self.name_vars[1].trace_add("write", lambda *args: self._update_names())
        # --- NEU: Trace für den Gegner-Modus ---
        self.gegner_var.trace_add("write", lambda *args: self._update_gegner_modus())
        
        # Texte klickbar machen
        self.canvas.tag_bind(self.text_p1, "<Button-1>", lambda e: self._update_fokus(0))
        self.canvas.tag_bind(self.text_p2, "<Button-1>", lambda e: self._update_fokus(1))
        self.canvas.tag_bind(self.mute_text, "<Button-1>", lambda e: self._toggle_mute())
        
        self._update_fokus(0)
        self._update_gegner_modus()  # <--- Prüft beim Start sofort, welcher Modus aktiv ist


        self.led_items = led_items
        self.target_coords = []  # <--- NEU: Liste für die Koordinaten initialisieren
        for i in range(5):
            x = 79 + (4-i) * 159
            y = 175
            self.target_coords.append((x, y))  # <--- NEU: Koordinaten für dieses Ziel speichern!
            outer, inner = self._draw_led(x, y)
            self.led_items.append((outer, inner))
            #Klick-Bindung:
            for item in (outer, inner):
                self.canvas.tag_bind(item, "<Button-1>",
                                     lambda e, bid=i: on_button_click(bid, True))
                self.canvas.tag_bind(item, "<ButtonRelease-1>",
                     lambda e, bid=i: on_button_click(bid, False))                     

    # --- NEUE FUNKTION FÜR DEN TRACE ---
    def _update_names(self):
        """Wird durch Tkinter automatisch im Hintergrund gerufen, wenn sich die Namen ändern."""
        # itemconfig ändert nur den Text. Farbe & Schriftart (Bold/Underline) bleiben erhalten!
        self.canvas.itemconfig(self.text_p1, text=f"Fokus: {self.name_vars[0].get()}")
        self.canvas.itemconfig(self.text_p2, text=f"Fokus: {self.name_vars[1].get()}")

    # --- NEUE FUNKTION FÜR DEN MODUS-WECHSEL ---
    def _update_gegner_modus(self):
        """Reagiert auf Änderungen des Spielmodus (Einzelspieler vs. Mehrspieler)"""
        modus = self.gegner_var.get()
        
        if modus == 0:
            # Einzelspieler: Fokus zwangsweise auf Spieler 1 setzen und Texte verstecken
            self._update_fokus(0)
            self.canvas.itemconfig(self.text_p1, state="hidden")
            self.canvas.itemconfig(self.text_p2, state="hidden")
        else:
            # Mehrspieler: Texte wieder einblenden
            self.canvas.itemconfig(self.text_p1, state="normal")
            self.canvas.itemconfig(self.text_p2, state="normal")

    # Die Toggle-Logik (bleibt fast gleich)
    def _update_fokus(self, selected_player):
        self.fokus_player = selected_player
        
        if selected_player == 0:
            self.canvas.itemconfig(self.text_p1, fill="paleturquoise", font=("Arial", 13, "bold", "underline"))
            self.canvas.itemconfig(self.text_p2, fill="gray80", font=("Arial", 11, "normal"))
        else:
            self.canvas.itemconfig(self.text_p1, fill="gray80", font=("Arial", 11, "normal"))
            self.canvas.itemconfig(self.text_p2, fill="coral", font=("Arial", 13, "bold", "underline"))

    # --- NEUE FUNKTION FÜR DEN MUTE-BUTTON ---
    def _toggle_mute(self):
        """Schaltet die Mock-Geräusche an oder aus."""
        aktuell = self.is_muted.get()
        self.is_muted.set(not aktuell)
        
        if self.is_muted.get():
            # Wenn gemutet: Zeige rotes, durchgestrichenes Icon
            self.canvas.itemconfig(self.mute_text, text="Muted", fill="coral")#🔇🔊
        else:
            # Wenn Sound an: Zeige normales Icon
            self.canvas.itemconfig(self.mute_text, text="Sound On", fill="gray50")

    def _draw_led(self, x, y):
        outer = self.canvas.create_oval(x-22, y-22, x+22, y+22, fill="black", outline="white", width=2)
        inner = self.canvas.create_oval(x-10, y-10, x+10, y+10, fill="black", outline="white", width=1)
        return (outer, inner)

    def set_led_state(self, index, on):
        fill_color = "green" if on else "black"
        outer, inner = self.led_items[index]
        self.canvas.itemconfig(outer, fill=fill_color)
        self.canvas.itemconfig(inner, fill=fill_color)

    def show_hit(self, index, player_id):
        x, y = self.target_coords[index]
        
        # 1. Größe der Krone festlegen
        # Der aktive Fokus-Spieler bekommt einen etwas größeren Stern
        if player_id == self.fokus_player and player_id is not None:
            o_rad = 44  # Etwas größer als vorher
            i_rad = 24
        else:
            o_rad = 35  # Etwas kleiner als Standard
            i_rad = 22
            
        star_points = self._calculate_star(x, y, outer_radius=o_rad, inner_radius=i_rad, points=8)
        
        # 2. Farben anhand des Spielers festlegen
        if player_id == 0:
            # Spieler 1 (Links)
            f_color = "paleturquoise"
            o_color = "darkblue"      # Dunklerer Rand für besseren Kontrast
        elif player_id == 1:
            # Spieler 2 (Rechts)
            f_color = "coral"
            o_color = "darkred"       # Dunklerer Rand für besseren Kontrast
        else:
            # Fehlschuss (None)
            f_color = "gray80"        # Helles Grau
            o_color = "gray50"        # Dunkleres Grau für den Rand
            
        # Zeichne den Zackenstern
        hit_marker = self.canvas.create_polygon(
            star_points, 
            fill=f_color, 
            outline=o_color, 
            width=2
        )
        
        # Wir holen uns die Ovals (Kreise) der getroffenen LED aus unserer Liste
        outer, inner = self.led_items[index]
        
        # Schiebe den Stern GENAU hinter den äußeren schwarzen Ring dieser LED
        self.canvas.tag_lower(hit_marker, outer)
        
        # Lösche den Stern nach 250ms
        self.canvas.after(250, lambda: self.canvas.delete(hit_marker))

    def _calculate_star(self, center_x, center_y, outer_radius, inner_radius, points):
        """Berechnet die Koordinaten für ein gezacktes Polygon (Stern/Krone)."""
        angle = math.pi / points
        coords = []
        for i in range(2 * points):
            r = outer_radius if i % 2 == 0 else inner_radius
            curr_angle = i * angle - math.pi / 2 # -90 Grad, damit die Spitze oben ist
            coords.append(center_x + math.cos(curr_angle) * r)
            coords.append(center_y + math.sin(curr_angle) * r)
        return coords

pin_to_idx = {
    6:  0,
    7:  1,
    8:  2,
    9:  3,
   10:  4,
}


#def init_mock_hardware_gui(pytaster):
#    mock_root = tk.Toplevel()
#    mock_root.servos = pytaster.KSobjekt.LEDs
#    mock_root.gui = LEDMockGUI(mock_root, led_items=[], on_button_click=pytaster.handle_button_press)

def init_mock_hardware_gui(pytaster):
    mock_root = tk.Toplevel()
    mock_root.servos = pytaster.KSobjekt.LEDs
    
    # --- NEU: Direkt die StringVar-Objekte holen ---
    try:
        var_p1 = pytaster.KSobjekt.SM.spieler
        var_p2 = pytaster.KSobjekt.SM.spieler2
        var_gegner = pytaster.KSobjekt.SM.gegner_modus  # <--- NEU
    except AttributeError:
        # Fallback, falls der SM noch nicht existiert (z.B. beim isolierten Testen)
        var_p1 = tk.StringVar(value="Spieler 1")
        var_p2 = tk.StringVar(value="Spieler 2")
        var_gegner = tk.IntVar(value=1)
        

    mock_root.gui = LEDMockGUI(
        mock_root, 
        led_items=[], 
        on_button_click=pytaster.handle_button_press,
        name_vars=(var_p1, var_p2),
        gegner_var=var_gegner
    )
    # ...

    # --- NEU: Callback für Treffer-Visualisierung ---
    def hit_callback(button_id, player_id):
        mock_root.gui.show_hit(button_id, player_id)
        
        # --- NEU: Stummschaltung prüfen ---
        if mock_root.gui.is_muted.get():
            return  # Bricht hier ab, keine Mock-Sounds werden abgespielt!
        
        # 1. FEHLSCHUSS (Das glorreiche Zonk)
        if player_id is None:
            pytaster.KSobjekt.SDeluebs.audio.sound_shoot.play()
            return # Hier brechen wir ab, da kein Stern gezeichnet werden muss
        
        # 3. SOUND-FOKUS (Aktiver vs. Passiver Spieler)
        if player_id == mock_root.gui.fokus_player:
            pytaster.KSobjekt.SDeluebs.audio.sound_shoot_active.play()
        else:
            pytaster.KSobjekt.SDeluebs.audio.sound_shoot_passive.play()
            
            
    # Den Hook an den Taster hängen
    pytaster.on_button_event = hit_callback

    
    # Callback erwartet (pin_name, angle)
    def led_callback(pin_name, angle):
        pin_nr = int(pin_name.lstrip("P"))     # z.B. "P6" → 6
        idx    = pin_to_idx[pin_nr]            # 6 → 4 (rechte Scheibe)
        mock_root.gui.set_led_state(idx, angle > 0)

    # jedem Servo den Callback zuweisen
    for srv in mock_root.servos:
        srv.on_angle_change = led_callback

    # Startzustand: alle LEDs aus
    for srv in mock_root.servos:
        srv.angle(0)
    
    return mock_root    

# Beispiel-Servos mit LED-Steuerung
class Servo:
    def __init__(self, index, on_angle_change=None):
        self.index = index
        self.on_angle_change = on_angle_change

    def angle(self, val):
        #print(f"Servo an Pin {self.index} auf Winkel {val} gesetzt (Mock)")
        if self.on_angle_change:
            self.on_angle_change(self.index, val)
        
        
class TTS:
    def __init__(self, lang=None): print(f"TTS init (Mock), Sprache: {lang}")
    def say(self, text): print(f"TTS sagt: {text} (Mock)")           