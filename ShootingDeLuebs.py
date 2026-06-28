import os 
import tkinter as tk
import zipfile
import io #für zipfile
import csv #Hier für Programm-Buttons
import pygame # Hier für Tonausgabe (ebenfalls für die Joystickeingaben bei HardwareDeLuebs)
from PIL import Image, ImageTk#, ImageFont  # Pillow muss installiert sein: `pip install pillow`

import platform  #Für neuen TTS
import threading #Für neuen TTS
import subprocess#Für neuen TTS

try:
    from robot_hat import TTS # type: ignore
except ImportError:
    import robot_hat_mock
    TTS = robot_hat_mock.TTS
import HardwareDeLuebs as HDeLuebs    
import HighscoreDeLuebs as HSDeLuebs 
import StateManagerDeLuebs as SMDeLuebs
from StateManagerDeLuebs import GameState
from AudioDeLuebs import AudioManager

import subprocess
import re

def get_current_version():
    try:
        # Wir lassen --abbrev=0 weg und nutzen --always
        # "git describe --tags --always --dirty"
        # --dirty hängt "-dirty" an, wenn du ungespeicherte Änderungen im Code hast!
        raw_git = subprocess.check_output(
            ["git", "describe", "--tags", "--always", "--dirty"], 
            stderr=subprocess.DEVNULL
        ).strip().decode("utf-8")

        # Wenn wir direkt auf einem Tag sind, kommt nur "v1.13.4"
        # Wenn wir weiter sind, kommt "v1.13.4-5-g123abcd"
        
        # Wir säubern es für die Anzeige, aber behalten die Info
        clean_version = raw_git.lstrip('v') 
        return clean_version
        
    except Exception:
        # Der Fallback bleibt wichtig für die .zip Nutzer
        return "1.13.4-zip"

def normalize_version(v_string):
#    Macht aus 'v1_9_6' oder '1.13.2' ein einheitliches '1.9.6' oder '1.13.2'.
    if not v_string:
        return "0.0.0"
    # 1. Unterstriche durch Punkte ersetzen (v1_9_6 -> v1.9.6)
    v_clean = v_string.replace('_', '.')
    # 2. Alles entfernen, was keine Zahl oder Punkt ist (v1.9.6 -> 1.9.6)
    v_clean = "".join(c for c in v_clean if c.isdigit() or c == '.')
    # 3. Falls am Ende noch Punkte hängen (z.B. durch '..'), säubern
    return v_clean.strip('.')
# Beispiel-Check:
# normalize_version("v1_9_6") -> "1.9.6"
# normalize_version("1.13.3") -> "1.13.3"        
        
# Die globale Konstante wird jetzt automatisch befüllt!
VERSION = get_current_version()

class ShootingDeluebs:
    def __init__(self, root):
        self.root = root
        self.root.geometry('1920x1200')
        self.root.title(f"Shooting DeLübs: Version {VERSION}")
        self.root['background'] = 'grey'
        self.version = VERSION
        print(f"🎯 Shooting DeLübs     [v{self.version}]")
        
        # Audio-Manager initialisiert Pygame, lädt ZIPs und verwaltet TTS
        self.audio = AudioManager()
        
        # Abwärtskompatibilität für deinen restlichen Code:
        # self.tts.say("...") und self.sound_win.play() funktionieren weiter!
        self.tts = self.audio
        self.sound_win = self.audio.sound_win
        self.sound_wrong = self.audio.sound_wrong
        self.sound0 = self.audio.sound0
        self.sound1 = self.audio.sound1
        self.sound_error = self.audio.sound_error
        self.sound_pfeife = self.audio.sound_pfeife
        self.sound_load = self.audio.sound_load
        self.sound_orchestra = self.audio.sound_orchestra
        self.sound_buzzticker = self.audio.sound_buzzticker
        self.sound_shoot = self.audio.sound_shoot
        
        # Sorgt dafür, dass bei jedem Linksklick geprüft wird, ob der Fokus gelöscht werden muss
        self.root.bind_all("<Button-1>", self.fokus_leeren)
        
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
        self.root.unbind_all("<Key-F10>")
        self.root.unbind_all("<Shift-Key-F10>")
        self.root.bind_all('<Key>', self.key_handler)
        #self.root.bind_all('<Tab>', self.key_handler) # <--- NEU: Tab explizit fangen!
 
    def create_widgets(self):
        #Background mit Hintergrundfarbe
        WIDTH, HEIGHT = 1920, 1200
        CENTER_X, CENTER_Y = WIDTH // 2, HEIGHT // 2-10
        MAX_RADIUS = 550  # 1050 px Durchmesser
        
        self.MyCanvas = tk.Canvas(master=self.root, width=WIDTH, height=HEIGHT, highlightthickness=0)
        self.MyCanvas.place(x = 0, y = 0)
        self.MyCanvas['background'] = 'orange'
        
        with zipfile.ZipFile("data.pak", "r") as pak:        
        #Mit Pillow
            img_data = pak.read('Logo.png')
            pil_img = Image.open(io.BytesIO(img_data))
            # Diese Referenz wird durch den Launcher-Patch automatisch skaliert!
            self.mein_logo = ImageTk.PhotoImage(pil_img)        
        # Im Canvas nur noch verwenden
        self.logo_id = self.MyCanvas.create_image(205, 130, image=self.mein_logo)
       #Logo ohne Pillow
       #     self.mein_logo = tk.PhotoImage(data=pak.read('Logo.png'))
       #     self.logo = self.MyCanvas.create_image(205, 130, image=self.mein_logo)
       #Hintergrundbild
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
        
        self.buttonHilfe = tk.Button(master=self.root, text='Hilfe / Hotkeys', bg='lightblue', command=self.zeige_hilfe_fenster, font=('Arial', 20))
        self.buttonHilfe.place(x=1340, y=215, width=280, height=52)        
        
        # --- PROGRAMM-BUTTONS (0 bis 7) ---
        self.pgmButtons = []
        for i in range(0, 8):  # Nur noch 8 normale Knöpfe (0 bis 7)
            self.pgmButtons.append(tk.Button(master=self.root, text=str(i), bg='#FBD975', command=lambda i=i: self.SMobjekt.setProgramm(i), font=('Arial',12)) )
            x = 1085 + ((i) % 3) * 275
            y =  920-95-30 + ((i) // 3) * 70
            self.pgmButtons[i].place(x=x, y=y, width=250, height=60)        

        # Der 9. Button (an Position von Index 8) wird der "Alle Programme..." Touch-Button
        self.buttonAlleProgramme = tk.Button(master=self.root, text='Alle Programme...', bg='#FBD975', command=self.zeige_programm_raster, font=('Arial', 12, 'bold'))
        x = 1085 + (8 % 3) * 275
        y = 920-95-30 + (8 // 3) * 70
        self.buttonAlleProgramme.place(x=x, y=y, width=250, height=60)

        # --- CSV EINLESEN & BACKUP FÜR GRID ---
        self.programm_namen = []  # Hier speichern wir ALLE Namen für das große Touch-Grid
        
        with open('Programme.csv', mode='r', encoding='utf-8') as file:
            csvFile = csv.reader(file)
            csvLine = next(csvFile)
            self.trimZero = [float(csvLine[0]),float(csvLine[1]),float(csvLine[2]),float(csvLine[4]),float(csvLine[4])]
            next(csvFile)  # Kopfzeile überspringen
            
            for row in csvFile:
                if row:
                    self.programm_namen.append(row[0])

        # Jetzt beschriften wir die 8 Hauptknöpfe mit den ersten 8 Einträgen aus der Liste
        for idx, btn in enumerate(self.pgmButtons):
            if idx < len(self.programm_namen):
                btn.config(text=self.programm_namen[idx])

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

        #entry = tk.Entry(bottom_row, textvariable=var, justify='center', bg=bg, font=('Arial', 20-FONT_reduction), width=17)
        
        tuersteher = (frame.register(self.nur_zahlen_erlaubt), '%P')
        # --- GEÄNDERT: Das Entry-Feld bekommt die validate-Parameter ---
        entry = tk.Entry(bottom_row, textvariable=var, justify='center', bg=bg, font=('Arial', 20-FONT_reduction), width=17,
                         validate="key", validatecommand=tuersteher)        
        entry.pack(side=tk.RIGHT, padx=4, pady=0, ipadx=0, ipady=6)
        return entry

    def nur_zahlen_erlaubt(self, neu_text):
        """
        Prüft, ob die Eingabe nur aus Ziffern besteht.
        Leerer Text ("") muss erlaubt sein, damit man mit Backspace/Entf alles löschen kann.
        """
        if neu_text == "" or neu_text.isdigit():
            return True
        else:
            return False

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

    def zeige_hilfe_fenster(self):
        hilfe_win = tk.Toplevel(self.root)
        hilfe_win.title("Hilfe & Tastenkombinationen")
        hilfe_win.geometry("900x700")
        hilfe_win.configure(bg="gray90")
        # Macht das Fenster modal (blockiert das Hauptfenster, bis es geschlossen wird)
        hilfe_win.transient(self.root)
        hilfe_win.grab_set()

        titel = tk.Label(hilfe_win, text="Tastenkombinationen & Steuerung", font=("Arial", 24, "bold"), bg="gray90")
        titel.pack(pady=20)

        text_frame = tk.Frame(hilfe_win, bg="gray90")
        text_frame.pack(expand=True, fill="both", padx=30, pady=10)

        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")

        # ==========================================================
        # --- NEU: tabs=("250", "left") zwingt \t exakt auf 250 Pixel ---
        # ==========================================================
        text_widget = tk.Text(text_frame, font=("Arial", 16), bg="white", wrap="word", padx=20, pady=20, yscrollcommand=scrollbar.set, tabs=("190", "left"))
        text_widget.pack(side="left", expand=True, fill="both")
        scrollbar.config(command=text_widget.yview)

        # ==========================================================
        # --- NEU: Alle Leerzeichen vor dem Doppelpunkt sind nun ein \t ---
        # ==========================================================
        hilfe_text = """ALLGEMEINE STEUERUNG
-----------------------------------------
• Linke Strg-Taste\t: Start - MATCH
• Escape (Esc)\t: Reset / Abbruch
• Linksklick\t: Nimmt den Fokus aus Textfeldern

OBERFLÄCHE & HIGHSCORES
-----------------------------------------
• Tooltips\t: Bewege die Maus über ein Element (oder halte es am Touchscreen gedrückt), um Erklärungen zu sehen.
• Programmanzeige\t: Das große Feld mit dem Programmnamen unter der Statusanzeige (z.B. Sicherheit) ist ein Button!
• Highscores\t: Ein Klick auf die Programmanzeige öffnet die Bestenliste. Hovern zeigt die Info zum Programm.

PROGRAMMAUSWAHL (mit Tastatur)
-----------------------------------------
• F1 bis F12\t: Lädt Programm 1 bis 12
• Shift + F1-F12\t: Lädt Programm 13 bis 24

ENTWICKLER- UND SONDERFUNKTIONEN
-----------------------------------------
• Taste 'T'\t: Ladezeit auf 1-Minute setzen
• Taste 'D'\t: Dev-Mode (Fast-Forward, nur 2 Zyklen)
• Taste 'S'\t: Starte Loop, um die Spielernamen automatisch zu aktualisieren in Verbindung mit Championship DeLübs
• Taste '<'\t: Annulliere aktuellen Zyklus (Spieler 1)
• Taste '-'\t: Annulliere aktuellen Zyklus (Spieler 2)"""
        
        text_widget.insert("1.0", hilfe_text)

        # ==========================================================
        # --- NEU: lmargin2 auf 265 Pixel gesetzt ---
        # (250 Pixel für den Tab + ca. 15 Pixel für ": " = 265)
        # So bricht der Text rechts bündig unter dem vorherigen Text um!
        # ==========================================================
        text_widget.tag_configure("bullet_indent", lmargin1=0, lmargin2=205)
        
        for i, line in enumerate(hilfe_text.split('\n')):
            if line.startswith('•'):
                text_widget.tag_add("bullet_indent", f"{i+1}.0", f"{i+1}.end")

        # Schreibschutz wieder aktivieren
        text_widget.configure(state='disabled') 

        schliessen_btn = tk.Button(hilfe_win, text="Schließen", font=("Arial", 20), bg="#FBD975", command=hilfe_win.destroy)
        schliessen_btn.pack(pady=20, ipadx=40, ipady=10)

    def zeige_programm_raster(self):
        if not self.SMobjekt.get_state()==GameState.SICHERHEIT: return
        raster_win = tk.Toplevel(self.root)
        raster_win.title("Programmauswahl")
        
        # Perfekt dimensioniert für Touchscreens (nahezu Vollbild auf dem Pi-Monitor)
        raster_win.geometry("1500x950")
        raster_win.configure(bg="gray15") # Edler, dunkler Hintergrund für guten Kontrast
        raster_win.transient(self.root)
        raster_win.grab_set()

        # Große, gut lesbare Überschrift
        titel = tk.Label(raster_win, text="Wähle ein Schießprogramm", font=("Arial", 26, "bold"), bg="gray15", fg="white")
        titel.pack(pady=10)

        # Container-Frame für die Kacheln
        grid_frame = tk.Frame(raster_win, bg="gray15")
        grid_frame.pack(expand=True, fill="both", padx=50, pady=10)

        # Layout-Konfiguration: 4 Spalten x 6 Zeilen ergibt exakt 24 Programme
        anz_spalten = 4
        
        for idx, name in enumerate(self.programm_namen):
            if idx >= 48: break # Sicherheitsbremse bei mehr CSV-Einträgen
            
            row_idx = idx // anz_spalten
            col_idx = idx % anz_spalten
            
            # --- NEUE LOGIK FÜR DIE BESCHRIFTUNG ---
            if idx < 12:
                # Programme 1 bis 12
                btn_text = f"{name}\n(F{idx+1})"
            elif idx < 24:
                # Programme 13 bis 24
                btn_text = f"{name}\n(Shift+F{idx-11})"
            else:
                # Ab Programm 25 gibt es keine Standard-Shortcuts mehr
                btn_text = name 
            # ---------------------------------------

            # Die riesige Touch-Kachel
            btn = tk.Button(
                grid_frame, 
                text=btn_text,  # Hier setzen wir jetzt unseren dynamischen Text ein
                font=("Arial", 16, "bold"),
                bg="#FBD975",
                activebackground="darkorange",
                borderwidth=2,
                relief="raised",
                # Beim Klick: Programm setzen und das Fenster sofort wieder schließen!
                command=lambda idx=idx: [self.SMobjekt.setProgramm(idx), raster_win.destroy()]
            )
            # Dehnt die Buttons dank sticky='nsew' perfekt in ihre Grid-Zellen aus
            btn.grid(row=row_idx, column=col_idx, padx=12, pady=12, sticky="nsew")

        # Gewichtung definieren, damit alle Zeilen/Spalten exakt gleich groß skaliert werden
        for i in range(8): # Jetzt 8 Zeilen statt 6
            grid_frame.rowconfigure(i, weight=1)
        for i in range(4): # Spalten bleiben bei 4
            grid_frame.columnconfigure(i, weight=1)

        # Großer Abbrechen-Button ganz unten, falls man sich verklickt hat
        schliessen_btn = tk.Button(raster_win, text="Zurück zum Hauptmenü", font=("Arial", 22, "bold"), bg="gray35", fg="white", activebackground="gray50", command=raster_win.destroy)
        schliessen_btn.pack(pady=25, ipadx=60, ipady=12)



    def say(self, text):
        def run():
            if self.system == "Linux":
                import shlex
                # 1. Offline-Generierung (PicoTTS)
                wav_file = "temp_speech.wav"
                os.system(f'pico2wave --lang=de-DE --wave={wav_file} {shlex.quote(text)}')
                
                # 2. Pygame Sound-Check & Play
                try:
                    # Sound laden und abspielen
                    voice = pygame.mixer.Sound(wav_file)
                    voice.play() 
                    # Gut zu wissen: voice.play() von pygame ist von Natur aus asynchron!
                except Exception as e:
                    print(f"Audio-Fehler am Pi: {e}")
                    
            elif self.system == "Windows":
                # Native Windows-Sprachausgabe (SAPI) via PowerShell
                ps_cmd = f'Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("{text}")'
                
                # Subprocess nutzen: Sicherer bei Strings und versteckt das CMD-Fenster!
                # CREATE_NO_WINDOW (0x08000000) verhindert, dass kurz ein schwarzes Fenster aufblitzt
                CREATE_NO_WINDOW = 0x08000000
                try:
                    subprocess.run(["powershell", "-Command", ps_cmd], creationflags=CREATE_NO_WINDOW)
                except Exception as e:
                    print(f"Windows Audio-Mock Fehler: {e}")
    
        # Asynchroner Start: Das Spiel läuft flüssig weiter!
        threading.Thread(target=run, daemon=True).start()

    def fokus_leeren(self, event):
        """
        Prüft bei jedem Klick: Wenn nicht in ein Textfeld geklickt wurde, 
        nimm den Fokus aus dem Textfeld weg und gib ihn dem Hintergrund.
        """
        # SCHUTZSCHILD: Prüfen, ob event.widget überhaupt eine winfo_class Methode hat.
        # Wenn nicht (z.B. weil Tkinter uns einen rohen String liefert), brechen wir ab.
        if not hasattr(event.widget, 'winfo_class'):
            return

        # Wenn das angeklickte Element KEIN Texteingabefeld ist...
        if event.widget.winfo_class() not in ('Entry', 'TEntry', 'Text'):
            # ... dann gib dem angeklickten Element (z.B. dem grauen Hintergrund) den Fokus!
            event.widget.focus_set()

    
    def key_handler(self, event=None):
        if not event: return
        
        # ==========================================================
        # 1. GLOBALE HOTKEYS (Immer aktiv, auch in Textfeldern!)
        # ==========================================================
        
        # A) F-Tasten (Programme umschalten)
        if event.keysym.startswith('F'):
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
                    
                    # ELA-FIX FÜR WINDOWS F10 BLOCKADE
                    # Sobald F10 (oder Shift+F10) verarbeitet wurde, brechen wir hier ab,
                    # damit Windows das Event NIEMALS zu Gesicht bekommt!
                    if f_num == 10:
                        return 'break'
            except ValueError:
                pass

        # B) Start-Taste (Strg Links)
        if event.keysym == 'Control_L' and self.SMobjekt.stand == -1: 
            
            # --- DER TREEVIEW-SCHUTZ ---
            # Wenn man gerade in der Highscore-Tabelle ist, wollen wir
            # Strg für den Multi-Select nutzen. Der Start wird hier ignoriert!
            if getattr(event.widget, 'winfo_class', lambda: '')() == 'Treeview':
                return 
            # ---------------------------

            print("Start")
            # --- Fokus sofort aus jedem Textfeld klauen! ---
            self.root.focus_set()
            # ----------------------------------------------------            
            self.SMobjekt.buttonCountdownClick()

        # C) Reset-Taste (Escape)
        if event.keysym == 'Escape': 
            self.SMobjekt.buttonResetClick()


        # ==========================================================
        # --- DER EINGABEFELD-SCHUTZSCHILD ---
        # Ab hier: Hotkeys (Buchstaben), die NICHT feuern dürfen,
        # wenn man gerade einen Namen in ein Textfeld eintippt!
        # ==========================================================
        if event.widget.winfo_class() in ('Entry', 'TEntry', 'Text'):
            return 


        # ==========================================================
        # 2. LOKALE HOTKEYS (Nur aktiv, wenn KEIN Textfeld fokussiert ist)
        # ==========================================================
        if event.keysym in ('t', 'T'):
            if not self.SMobjekt.has_tag(SMDeLuebs.Tag.MODIFIZIERT):
                self.SMobjekt.system_update_laeuft = True
                self.SMobjekt.ladenGelb.set(60)   
                self.SMobjekt.system_update_laeuft = False
                self.SMobjekt.add_tag(SMDeLuebs.Tag.ONEMIN)
            else: 
                self.SMobjekt.ladenGelb.set(60)              
            return 'break'            
            
        if event.keysym in ('d', 'D'):
            print("DEV MODE: Fast-Forward aktiviert!")
            self.SMobjekt.system_update_laeuft = True
            self.SMobjekt.vorbereiten.set(1)
            self.SMobjekt.ladenGelb.set(1)
            if self.SMobjekt.survival_modus.get() == 0: 
                self.SMobjekt.wiederholungen.set(2)
            self.SMobjekt.system_update_laeuft = False
            self.SMobjekt.add_tag(SMDeLuebs.Tag.DEVELOPER)         
            
        if event.keysym in ('s', 'S'):
            if not getattr(self.SMobjekt, 'champion_loop_laeuft', False):
                print("Lade Meisterschaft Spieler (Loop gestartet)!")
                self.SMobjekt.setChampionMatch()
            else:
                print("Ignoriert: Meisterschafts-Loop läuft bereits!")
                
        if event.keysym == 'less':
            self.KSobjekt.Anulliere_zyklus2durchgang(0)
            
        if event.keysym == 'minus':
            self.KSobjekt.Anulliere_zyklus2durchgang(1)
        
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
