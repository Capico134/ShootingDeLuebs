import os 
import tkinter as tk
import zipfile
import io #für zipfile
import csv #Hier für Programm-Buttons
import pygame # Hier für Tonausgabe (ebenfalls für die Joystickeingaben bei HardwareDeLuebs)
from PIL import Image, ImageTk#, ImageFont  # Pillow muss installiert sein: `pip install pillow`
try:
    from robot_hat import TTS # type: ignore
except ImportError:
    import robot_hat_mock
    TTS = robot_hat_mock.TTS
import HardwareDeLuebs as HDeLuebs    
import HighscoreDeLuebs as HSDeLuebs 
import StateManagerDeLuebs as SMDeLuebs

import subprocess
import re

def get_current_version():
    """
    Zieht sich die aktuelle Version automatisch aus dem Git-Tag.
    Gibt einen Fallback zurück, falls Git nicht verfügbar ist.
    """
    try:
        # Fragt Git nach dem neuesten Tag (z.B. "v1.13.1")
        git_tag = subprocess.check_output(["git", "describe", "--tags", "--abbrev=0"], stderr=subprocess.DEVNULL).strip().decode("utf-8")
        
        # Nutzt dein importiertes 're', um alles außer Zahlen und Punkten zu entfernen 
        # (macht aus "v1.13.1" sauber "1.13.1")
        clean_version = re.sub(r'[^\d\.]', '', git_tag)
        return clean_version
        
    except Exception:
        # FALLBACK: Sehr wichtig! Falls das Spiel mal als reine ZIP-Datei 
        # (ohne den versteckten .git Ordner) heruntergeladen wird.
        return "1.13.x (No Git Info)" # So weißt du sofort: Hier fehlt der .git Ordner!

# Die globale Konstante wird jetzt automatisch befüllt!
VERSION = get_current_version()

class ShootingDeluebs:
    def __init__(self, root):
        self.root = root
        self.root.geometry('1920x1200')
        self.root.title('Shooting DeLübs')
        self.root['background'] = 'grey'
        self.version = VERSION
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=128)
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
        self.tts = TTS(lang='de-DE')
        self.hintergrundbilder = {}

        #HighscoreDeluebs
        self.HSobjekt = HSDeLuebs.HighscoreDeluebs(self)

        #STATEMANAGER 
        self.SMobjekt = SMDeLuebs.StateManager(self)

        #HardwareDeluebs
        self.KSobjekt = HDeLuebs.Klappscheibe(self)
        self.pytaster = HDeLuebs.PyGameTaster(self.KSobjekt)
        self.DSobjekt = HDeLuebs.Drehscheibe(self)
        self.trimZero = [0,0,0,0,0] # Defaultwerte; Wird durch create_widgets() gleich mit der Programme.csv überschrieben

        #VARIABLEN NUR FÜR DIE ANZEIGE
        self.anzeige_zyklus = tk.StringVar()
        self.update_zyklus_anzeige()
        self.SMobjekt.zyklus.trace_add("write", self.update_zyklus_anzeige)
        
        #Widgets
        self.create_widgets()
        self.root.bind('<Key>', self.key_handler)
 
    def create_widgets(self):
        #Background mit Hintergrundfarbe
        WIDTH, HEIGHT = 1920, 1200
        CENTER_X, CENTER_Y = WIDTH // 2, HEIGHT // 2-10
        MAX_RADIUS = 550  # 1050 px Durchmesser
        
        self.MyCanvas = tk.Canvas(master=self.root, width=WIDTH, height=HEIGHT, highlightthickness=0)
        self.MyCanvas.place(x = 0, y = 0)
        self.MyCanvas['background'] = 'orange'
        
        with zipfile.ZipFile("data.pak", "r") as pak:        
            #Logo
            self.mein_logo = tk.PhotoImage(data=pak.read('Logo.png'))
            self.logo = self.MyCanvas.create_image(205, 130, image=self.mein_logo)
        #     #Mit Pillow
       #      img = Image.open(io.BytesIO(pak.read("Hintergrundv06.png"))) 
       #      tk_img = ImageTk.PhotoImage(img)
       #      self.MyCanvas.create_image(0, 0, anchor="nw", image=tk_img)
       #      self.image = tk_img # Referenz halten!
        
        #Mit TK
        #self.mein_bg = tk.PhotoImage(file='Hintergrundv06.png')
        #self.backgr = self.MyCanvas.create_image(960, 600, image=self.mein_bg)
        
        #with zipfile.ZipFile("hintergrundbilder.pak", "r") as pak:       
        #    self.hintergrundbilder = {
        #        state.name: ImageTk.PhotoImage(data=pak.read(f"{state.name}.bmp"))
        #        for state in SMDeLuebs.GameState
        #    }
        #self.bg_image_id = self.MyCanvas.create_image(0, 0, anchor="nw", image=self.hintergrundbilder[self.SMobjekt.get_state().name])
        
        #self.SMobjekt.set_state(SMDeLuebs.GameState.VORBEREITEN)
        
        
        #Farbverlauf für die Kreise (von außen nach innen)
        circle_colors = ["gray60", "gray65", "gray70", "gray75", "gray80", "gray82", "gray85", "gray88", "gray90"]
        circle_colors =circle_colors[::-1]
        # anz_Kreislinien
        anz_Kreislinien = 6
        for i in range(anz_Kreislinien):
            r = MAX_RADIUS - i * (MAX_RADIUS // (anz_Kreislinien-0.5))
            color = circle_colors[i]
            self.MyCanvas.create_oval(CENTER_X - r, CENTER_Y - r, CENTER_X + r, CENTER_Y + r, outline=color, width=1)
        
        #DIES IST DAS HAUPTZIEL
        self.standCanvas = self.MyCanvas.create_text(960, 550, text="", font=("Arial",200), fill="black")  #calibri 40 bold", fill="white")
        #draw.text((100, 100), "Willkommen", fill="white")
             
        # Labels
        self.labelModi = tk.Label(master=self.root, textvariable=self.SMobjekt.gamestate_stringvar, bg='sandybrown', font=('Arial', 103), borderwidth=1, relief='groove')
        self.labelModi.place(x=600, y=35, width=720, height=180)
        ToolTip(self.labelModi, lambda: self.SMobjekt.programm_info.get())

        self.labelwiederholungen = tk.Label(master=self.root, textvariable=self.anzeige_zyklus, bg='plum1', font=('Arial', 140), borderwidth=1, relief='groove')
        self.labelwiederholungen.place(x=1340, y=35, width=550, height=180)

        # Buttons
        self.buttonStart = tk.Button(master=self.root, text='Start', bg='#FBD975', command=self.SMobjekt.buttonCountdownClick, font=('Arial',24))
        self.buttonStart.place(x=210, y=1000-80, width=145, height=80)
        
        self.buttonReset = tk.Button(master=self.root, text='Reset', bg='#FBD975', command=self.SMobjekt.buttonResetClick, font=('Arial',24))
        self.buttonReset.place(x=40, y=1000-80, width=145, height=80)

        self.buttonProgramm = tk.Button(master=self.root, textvariable=self.SMobjekt.programm_name, bg='sandybrown', command=self.HSobjekt.show_highscore_window, font=('Arial',27))
        self.buttonProgramm.place(x=600, y=215, width=720, height=52)
        ToolTip(self.buttonProgramm, lambda: self.SMobjekt.programm_info.get())
        
        self.pgmButtons = []
        for i in range(0, 9):
            self.pgmButtons.append(tk.Button(master=self.root, text=str(i), bg='#FBD975', command=lambda i=i: self.SMobjekt.setProgramm(i), font=('Arial',12)) )
            x = 1085 + ((i) % 3) * 275
            y =  920-95-30 + ((i) // 3) * 70
            self.pgmButtons[i].place(x=x, y=y, width=250, height=60)        

        #CSV einlesen
        with open('Programme.csv', mode ='r', encoding='utf-8') as file:
            csvFile = csv.reader(file)
            csvLine = next(csvFile)
            self.trimZero = [float(csvLine[0]),float(csvLine[1]),float(csvLine[2]),float(csvLine[4]),float(csvLine[4])]
            csvLine = next(csvFile)
            for i in self.pgmButtons:
                csvLine = next(csvFile)
                i.config(text=csvLine[0])

        #Spieler
        self.entryspieler = tk.Entry(master=self.root, textvariable=self.SMobjekt.spieler, justify='center', bg='paleturquoise', font=('Arial',24))
        self.entryspieler.place(x=385, y=960-40, width=310, height=80)
        self.entryspieler2 = tk.Entry(master=self.root, textvariable=self.SMobjekt.spieler2, justify='center', bg='coral', font=('Arial',24))
        #self.entryspieler2.place(x=715, y=960, width=300, height=80)
        
        InkFrame = tk.Frame(master=self.root)
        InkFrame.place(x=20, y=300)

        self.create_entry_buttons(InkFrame, self.SMobjekt.vorbereiten, tk.StringVar(value="Vorbereitungszeit"), 'dodgerblue', self.SMobjekt.vorbereiten_up,    self.SMobjekt.vorbereiten_down,'Stelle hier ein wie viele Sekunden die Vorbereitungszeit dauern soll')
        self.create_entry_buttons(InkFrame, self.SMobjekt.ladenGelb, tk.StringVar(value="Ladezeit"), '#fdee73',               self.SMobjekt.ladenGelb_up,      self.SMobjekt.ladenGelb_down,'Stelle hier ein wie viele Sekunden die Zeit zum Nachladen dauern soll')
        self.create_entry_buttons(InkFrame, self.SMobjekt.achtung, tk.StringVar(value="Achtungszeit"), 'crimson',             self.SMobjekt.achtung_up,        self.SMobjekt.achtung_down, 'Die Achtungszeit zählt kurz bevor gefeuert wird runter')
        self.create_entry_buttons(InkFrame, self.SMobjekt.feuer, tk.StringVar(value="Feuerzeit"), 'green',                    self.SMobjekt.feuer_up,          self.SMobjekt.feuer_down, 'Die Feuerzeit bestimmt die Länge des Zeitintervalls indem geschossen werden darf')
        self.create_entry_buttons(InkFrame, self.SMobjekt.wiederholungen, tk.StringVar(value="Wiederholungen"), 'plum1',      self.SMobjekt.wiederholungen_up, self.SMobjekt.wiederholungen_down, 'Jeder Durchgang besteht aus mehreren Zyklen in denen geschossen werden darf.\nDie Anzahl der Wiederholungen wird hier festgelegt.')
        self.create_entry_buttons(InkFrame, self.SMobjekt.scheibenServo, tk.StringVar(value="ScheibenServo"), 'silver',       self.SMobjekt.scheibenServo_up,  self.SMobjekt.scheibenServo_down, self.SMobjekt.string_info_scheibenservo)
                
        ChkFrames = tk.Frame(master=self.root)
        ChkFrames.place(x=1630, y=240-15)
        
        self.chk_zufall = self.create_checkbutton(ChkFrames, 'Zufall',          self.SMobjekt.zufall, self.SMobjekt.string_info_zufall)
        self.chk_reihe = self.create_checkbutton(ChkFrames, 'Wechsel/Reihe',    self.SMobjekt.reihe, self.SMobjekt.string_info_reihe)
        self.chk_gegner_modus = self.create_checkbutton(ChkFrames, 'Gegner',    self.SMobjekt.gegner_modus, self.SMobjekt.string_info_gegner)
        self.chk_jaeger_modus = self.create_checkbutton(ChkFrames, 'Jäger',     self.SMobjekt.jaeger_modus, self.SMobjekt.string_info_jaeger)
        self.chk_kaenguru_modus = self.create_checkbutton(ChkFrames, 'Känguru', self.SMobjekt.kaenguru_modus, self.SMobjekt.string_info_kaenguru)

        self.create_checkbutton(ChkFrames, 'Survival', self.SMobjekt.survival_modus, self.SMobjekt.string_info_survival)
        self.create_checkbutton(ChkFrames, 'BuzzTick/Trick',    self.SMobjekt.trick, self.SMobjekt.string_info_buzztick)
        self.create_checkbutton(ChkFrames, 'Zählen',   self.SMobjekt.zaehlen, self.SMobjekt.string_info_zaehlen)
        self.create_checkbutton(ChkFrames, 'Ton',      self.SMobjekt.ton, self.SMobjekt.string_info_ton)
        self.create_checkbutton(ChkFrames, 'Save/ServoOff',     self.SMobjekt.saveScore, self.SMobjekt.string_info_save_servooff)
    
    def create_entry_buttons(self, frame, var, label_text_var, bg, command_up, command_down, tooltip=""):
        if hasattr(self.KSobjekt.LEDs[0], "on_angle_change"): FONT_reduction = 3  # Windows
        else: FONT_reduction = 0  # Raspberry Pi

        block = tk.Frame(frame)
        block.pack(padx=0, pady=0, ipadx=0, ipady=1)
        # Oberste Zeile: Label und ▲ Button
        top_row = tk.Frame(block)
        top_row.pack(side=tk.TOP, padx=0, pady=0, ipadx=0, ipady=1)

        btn_up = tk.Button(top_row, text="▲", font=('Arial', 20-FONT_reduction), command=command_up, width=3)
        btn_up.pack(side=tk.RIGHT, padx=2, pady=0, ipadx=0, ipady=1)

        label = tk.Label(top_row, textvariable=label_text_var, font=('Arial', 20-FONT_reduction, 'bold'), bg=bg, width=17)
        label.pack(side=tk.RIGHT, padx=4, pady=0, ipadx=0, ipady=5)
        if tooltip:
            ToolTip(label, tooltip)
        
        # Untere Zeile: Entry und ▼ Button
        bottom_row = tk.Frame(block)
        bottom_row.pack(side=tk.TOP)

        btn_down = tk.Button(bottom_row, text="▼", font=('Arial', 20-FONT_reduction), command=command_down, width=3)
        btn_down.pack(side=tk.RIGHT, padx=2, pady=0, ipadx=0, ipady=1)

        entry = tk.Entry(bottom_row, textvariable=var, justify='center', bg=bg, font=('Arial', 20-FONT_reduction), width=17)
        entry.pack(side=tk.RIGHT, padx=4, pady=0, ipadx=0, ipady=6)
        return entry

    def create_checkbutton(self, frame, text, var, tooltip_text=None):
            if hasattr(self.KSobjekt.LEDs[0], "on_angle_change"): 
                FONT_reduction = 3  # Windows
            else: 
                FONT_reduction = 0  # Raspberry Pi
            chk = tk.Checkbutton(master=frame, text=text, variable=var, 
                                font=('Arial', 28 - FONT_reduction), justify='left', 
                                bg='lightsteelblue', activebackground="white", 
                                width=4, height=1, indicatoron=False, selectcolor="darkgreen")
            chk.pack(side=tk.TOP, padx=0, pady=0, ipadx=85, ipady=1)
            # ToolTip optional anheften
            if tooltip_text:
                ToolTip(chk, tooltip_text)
            return chk

    def update_zyklus_anzeige(self, *args):
        aktuell = self.SMobjekt.zyklus.get()
        if self.SMobjekt.survival_modus.get() == 1:
            # Im Survival Modus gibt es kein Ende, also nur die aktuelle Runde
            self.anzeige_zyklus.set(f"{aktuell}") 
        else:
            # Im normalen Modus: 1/7, 2/7
            try:
                gesamt = self.SMobjekt.wiederholungen.get()
            except (tk.TclError, ValueError):
                # Wenn das Feld leer ist, zeigen wir eine 0 oder lassen es kurz leer
                gesamt = 0
            self.anzeige_zyklus.set(f"{aktuell}\u2009/\u200A{gesamt}")




#    def create_checkbutton(self, frame, text, var):
#        if hasattr(self.KSobjekt.LEDs[0], "on_angle_change"): FONT_reduction = 3  # Windows
#        else: FONT_reduction = 0  # Raspberry Pi
#        chk = tk.Checkbutton(master=frame, text=text, variable=var, font=('Arial',28-FONT_reduction), justify='left', bg='lightsteelblue', activebackground="white", width=4, height=1, indicatoron=False, selectcolor="darkgreen")#, command=lambda: self.update_color_checkbutton(var, chk))
#        chk.pack(side=tk.TOP, padx=0,pady=0, ipadx=85, ipady=1)
#        return chk

    def update_hauptlabel(self):
        #start = time.perf_counter() ###Zeitmessung
        #Hauptlabel aktualisieren
        if self.SMobjekt.get_state() == SMDeLuebs.GameState.SICHERHEIT:
            #HardwareDeLuebs: Hier Bestenliste anzeigen:
            player1= self.KSobjekt.players[0]
            player2= self.KSobjekt.players[1]
            if player1.punkte_durchgang!=0 or player2.punkte_durchgang!=0 : 
                if self.SMobjekt.gegner_modus.get()==0: self.MyCanvas.itemconfig(self.standCanvas, text=str('Punkte: '+str(player1.punkte_durchgang)+'\nSpeedpunkte: '+str(round(player1.speedpunkte_durchgang,3))+'\nGesamtpunkte: '+str(round(player1.punkte_durchgang+player1.speedpunkte_durchgang,3))), font=('Arial', 80))                
                else:
                    ausgabe_text =str(self.SMobjekt.spieler.get()) + \
                        '\nPunkte: '      +str(player1.punkte_durchgang) + \
                        '\nSpeedpunkte: ' +str(round(player1.speedpunkte_durchgang,3)) + \
                        '\nGesamtpunkte: '+str(round(player1.punkte_durchgang+player1.speedpunkte_durchgang,3)) + \
                        '\n'+str(self.SMobjekt.spieler2.get()) + \
                        '\nPunkte: '      +str(player2.punkte_durchgang) + \
                        '\nSpeedpunkte: ' +str(round(player2.speedpunkte_durchgang,3)) + \
                        '\nGesamtpunkte: '+str(round(player2.punkte_durchgang+player2.speedpunkte_durchgang,3)) 
                    if self.SMobjekt.survival_modus.get()==1:
                        gesamtpunkte_survival = str(round(player1.punkte_durchgang+player1.speedpunkte_durchgang + player2.punkte_durchgang+player2.speedpunkte_durchgang,3)) 
                        ausgabe_text = ausgabe_text+'\nStartfeuerzeit: '+str(self.SMobjekt.default_feuerzeit)+ ' Gesamtpunkte: '+gesamtpunkte_survival                 
                    self.MyCanvas.itemconfig(self.standCanvas, text= ausgabe_text, font=('Arial', 32))  
                        
            else: self.MyCanvas.itemconfig(self.standCanvas,text=str(''), font=("Arial",200))
        elif self.SMobjekt.get_state() == SMDeLuebs.GameState.RESET:
            self.MyCanvas.itemconfig(self.standCanvas,text=str(self.SMobjekt.stand), font=("Arial",200))
        elif self.SMobjekt.zaehlen.get() == 1 or self.SMobjekt.get_state() in [SMDeLuebs.GameState.VORBEREITEN, SMDeLuebs.GameState.LADEN]:
            self.MyCanvas.itemconfig(self.standCanvas,text=str(self.SMobjekt.stand), font=("Arial",420))
        else:
            self.MyCanvas.itemconfig(self.standCanvas,text='') # Zeigt nichts an, wenn die Bedingung nicht erfüllt ist.
        
        self.root.update_idletasks() 
        #print(f"Dauer: {time.perf_counter() - start:.6f} Sekunden") ###Zeitmessung

#UNÖTIGIGE AUFTEILUNG zwischen Hauptlabel und update_graphic   
    def update_graphic(self):
        self.update_hauptlabel() #enthält update_idletasks()
    
    def key_handler(self, event=None):
        if event and event.keysym.startswith('F'):
            try:
                f_num = int(event.keysym[1:])
                if 1 <= f_num <= 12:
                    # Prüfen, ob Shift gedrückt ist (Bitmaske 0x0001)
                    if event.state & 0x0001:
                        # Shift + Fx gedrückt
                        self.SMobjekt.setProgramm(f_num + 11)  # z.B. F1 → 12, F2 → 13, ...
                    else:
                        # Nur Fx gedrückt
                        self.SMobjekt.setProgramm(f_num - 1)  # z.B. F1 → 0, F2 → 1, ...
            except ValueError:
                pass
        if event.keysym=='Control_L' and self.SMobjekt.stand==-1: self.SMobjekt.buttonCountdownClick() #Standabfrage ist hier, da Knopf verschwindet und der Button aktiv bleibt
        if event.keysym=='Escape': self.SMobjekt.buttonResetClick() #and not self.SMobjekt.stand==-1 #standabfrage ist in der Funktion
        if event.keysym=='Tab': 
            if not self.SMobjekt.has_tag(SMDeLuebs.Tag.MODIFIZIERT):
                self.SMobjekt.system_update_laeuft=True
                self.SMobjekt.ladenGelb.set(60)   
                #self.SMobjekt.remove_tag(SMDeLuebs.Tag.MODIFIZIERT)
                self.SMobjekt.system_update_laeuft=False
                self.SMobjekt.add_tag(SMDeLuebs.Tag.ONEMIN)
            else: self.SMobjekt.ladenGelb.set(60)                  
        if event.keysym == 'D':
            print("DEV MODE: Fast-Forward aktiviert!")
            self.SMobjekt.system_update_laeuft=True
            self.SMobjekt.vorbereiten.set(1)
            self.SMobjekt.ladenGelb.set(1)
            if self.SMobjekt.survival_modus.get()==0: self.SMobjekt.wiederholungen.set(2)
            # Tags aufräumen und DEV setzen
            #self.SMobjekt.remove_tag(SMDeLuebs.Tag.MODIFIZIERT)
            #self.SMobjekt.remove_tag(SMDeLuebs.Tag.ONEMIN)
            self.SMobjekt.system_update_laeuft=False
            self.SMobjekt.add_tag(SMDeLuebs.Tag.DEVELOPER)                
        
class ToolTip:
    def __init__(self, widget, text, delay=500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tipwindow = None
        self.id = None
        self.widget.bind("<Enter>", self.schedule)
        self.widget.bind("<Leave>", self.hide)
        
    def schedule(self, event=None):
        self.unschedule()
        self.id = self.widget.after(self.delay, self.show)
        
    def unschedule(self):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None
            
    def show(self):
            # Dynamischer Text (Callable-Check)
            display_text = self.text() if callable(self.text) else self.text
            
            if self.tipwindow or not display_text:
                return
                
            x = self.widget.winfo_pointerx() + 20
            y = self.widget.winfo_pointery() + 20
            
            self.tipwindow = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            
            label = tk.Label(tw, text=display_text, background="#ffffe0", relief=tk.SOLID,
                            borderwidth=1, font=("tahoma", "17", "normal"))
            label["justify"] = 'left'
            label.pack(ipadx=6, ipady=2)
            
            # --- Rand-Korrektur (Rechts UND Unten) ---
            tw.update_idletasks()
            tip_width = tw.winfo_width()
            tip_height = tw.winfo_height()
            screen_width = self.widget.winfo_screenwidth()
            screen_height = self.widget.winfo_screenheight()
            
            # Check Rechts
            if x + tip_width > screen_width:
                x = self.widget.winfo_pointerx() - tip_width - 20
                
            # Check Unten
            if y + tip_height > screen_height:
                y = self.widget.winfo_pointery() - tip_height - 20
                
            tw.wm_geometry(f"+{x}+{y}")

        
    def hide(self, event=None):
        self.unschedule()
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None
            
            
if __name__ == "__main__":
    root = tk.Tk()
    app = ShootingDeluebs(root)
    if hasattr(app.KSobjekt.LEDs[0], "on_angle_change"):
        mockgui = HDeLuebs.init_mock_hardware_gui(app.pytaster)
    root.mainloop()
