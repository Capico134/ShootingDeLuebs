import tkinter as tk
from PIL import Image, ImageTk#, ImageFont  # Pillow muss installiert sein: `pip install pillow`
import zipfile
import math # für krone
import io #für zipfile

class LEDMockGUI:
    def __init__(self, master, led_items, on_button_click):
        master.title("Schießstand Anzeige")
        master.geometry("800x319")
        master.configure(bg="gray95")
        master.wm_attributes("-topmost", True)  # Immer im Vordergrund
        self.canvas = tk.Canvas(master, width=800, height=319, bg="gray95")
        self.canvas.pack()
        
        #Mit Pillow
        with zipfile.ZipFile("data.pak", "r") as pak: 
            img = Image.open(io.BytesIO(pak.read("Schiessstand.png"))) 
        tk_img = ImageTk.PhotoImage(img)
        self.canvas.create_image(0, 0, anchor="nw", image=tk_img)
        self.image = tk_img # Referenz halten!

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

    def _draw_led(self, x, y):
        outer = self.canvas.create_oval(x-22, y-22, x+22, y+22, fill="black", outline="white", width=2)
        inner = self.canvas.create_oval(x-10, y-10, x+10, y+10, fill="black", outline="white", width=1)
        return (outer, inner)

    def set_led_state(self, index, on):
        fill_color = "green" if on else "black"
        outer, inner = self.led_items[index]
        self.canvas.itemconfig(outer, fill=fill_color)
        self.canvas.itemconfig(inner, fill=fill_color)

    def show_hit(self, index):
        x, y = self.target_coords[index]
        star_points = self._calculate_star(x, y, outer_radius=40, inner_radius=25, points=8)
        
        # Zeichne den roten Zackenstern
        hit_marker = self.canvas.create_polygon(star_points, fill="red", outline="yellow", width=2)
        
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

def init_mock_hardware_gui(pytaster):
    mock_root = tk.Toplevel()
    mock_root.servos = pytaster.KSobjekt.LEDs
    mock_root.gui = LEDMockGUI(mock_root, led_items=[], on_button_click=pytaster.handle_button_press)

    # --- NEU: Callback für Treffer-Visualisierung ---
    def hit_callback(button_id):
        # Nur für die Zielscheiben 0 bis 4 (falls 7 z.B. Reset ist)
        #print("hit_callback")
        if 0 <= button_id <= 4:
            mock_root.gui.show_hit(button_id)
            pytaster.KSobjekt.SDeluebs.sound_shoot.play()
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