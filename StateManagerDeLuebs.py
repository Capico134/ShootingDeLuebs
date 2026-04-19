import time
import tkinter as tk
from enum import Enum
#from typing import Callable, Optional 
import csv
import os # Um die ID für das Logevent zu finden

from enum import Enum
class GameState(Enum):
    SICHERHEIT = ("Sicherheit", "orange")
    VORBEREITEN = ("Vorbereiten", "dodgerblue")
    LADEN = ("Laden", "#fdee73")  # ähnlich wie gelb
    ACHTUNG = ("Achtung", "crimson")
    FEUER = ("Feuer", "green")
    RESET = ("Reset", "thistle") 
    PLAYER1 = ("Spieler 1", "paleturquoise")
    PLAYER2 = ("Spieler 2", "coral")
    WINNER = ("Gewonnen", "plum")
    END = ("Ende", "grey")    

    def __new__(cls, value, color):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.color = color
        return obj
        
    @classmethod
    def action_states(cls):
        return {cls.FEUER, cls.PLAYER1, cls.PLAYER2, cls.END, cls.WINNER}    

    @classmethod
    def bonus_states(cls):
        return {cls.PLAYER1, cls.PLAYER2}    
    
    def is_action_state(self):
        #print(f"Wert {self.value} → {self in self.__class__.action_states()}")
        return self in self.__class__.action_states()
        
    def is_bonus_state(self):
        return self in self.__class__.bonus_states()    

class Tag(Enum):
    DEBUG = '(debug)'
    ONEMIN = '(1min)'
    MODIFIZIERT = '(modifiziert)'
    DEVELOPER = '(dev)'
    #REPLAY = '(replay)'    
   
class StateManager:
    def __init__(self, SDeluebs):
        self.SDeluebs = SDeluebs
                
        self._state = GameState.SICHERHEIT

        self.Tag = Tag # <--- NEU: Wir binden die Klasse an das Objekt!
        self._tags = set()
        self.system_update_laeuft = False
    
        # Dictionary zur Nachverfolgung aller Traces
        #Dieses enthält Listen in dennen die Traces sind. self.trace_ids[name][0] zeigt immer auf self.set_modus_to_custom. Ggf. sind weitere in der Liste vorhanden.  
        self.trace_ids = {} #ACHTUNG DIESE TRACES WERDEN BISHER NICHT VERWENDET!!!!!!!!!!!!!!!!!!!
        
        # Funktion zur Erzeugung von IntVar mit Trace-Funktionen
        # Alle Variablen sind als self.<name> verfügbar
        def init_var(name, value, trace_func=None):
            var = tk.IntVar(value=value)
            trace_id_list = [var.trace_add('write', self.set_modus_to_custom)]
            if trace_func is not None:
                trace_id_list.append(var.trace_add('write', trace_func))                
            self.trace_ids[name] = (var, trace_id_list)
            setattr(self, name, var)
            return var, trace_id_list 
        
        #################################################
        ###########  Variablen  #########################
        #################################################

        #Einfache Variablen
        self.trimZero = [0.0, 0.0, 0.0, 0.0, 0.0]
        self.stand = -1       
        self.zyklus_ueberlebt = True        
        self.survival_penalty = 0.4999
        self.survival_relax_time = 5
        self.default_feuerzeit = 25
        self.servoDelay = 0.0035
        self.cancel = False #Verwendet für den Resetbutton
        self.match_id = self.get_next_match_id() #print("Match_id",self.match_id) # Könnte man auch mit -1 initialisieren, weil beim Vorbereiten eh neu gesetzt.
        self.aktuelle_replay_id = None
        self._base_programm_name = "Default"
        self.laufzeit = time.monotonic()


        #StrVar 
        self.spieler  = tk.StringVar(value='Andreas')
        self.spieler2 = tk.StringVar(value='Günther')
        self.gamestate_stringvar = tk.StringVar(value="Sicherheit")
        self.programm_name = tk.StringVar()         
        self._refresh_gui_name() #Damit der Programmname aktualisiert wird  
        self.programm_info = tk.StringVar(value="Dies ist das Default Programm.")
        
        #IntVar
        # Hinweis für Entwickler:
        # Variablen werden über init_var(name, value, trace_func) erzeugt
        # Diese Variablen haben immer einen trace auf self.set_modus_to_custom, da jede manuelle Änderung "(modifiziert)" zum Modusnamen hinzufügt
        # Alle Variablen sind als self.<name> verfügbar
        init_var('vorbereiten', 5)
        init_var('ladenGelb', 3)
        init_var('achtung', 4)
        ##Trace Feuer mit eigener Variable, damit man es abschalten kann. (Beim Survival-Modus ändert sich die Feuerzeit standartmäßig) 
        self.feuer_trace = init_var('feuer', 2, self.update4feuer2default)[1][0]
        init_var('wiederholungen', 3, self.update4wiederholungen)
        init_var('scheibenServo', -1)
        init_var('trickWahrsch', 25)
        init_var('zufall', 0, lambda *args: self.check_exclusive_options('zufall'))
        init_var('trick', 0)
        init_var('reihe', 0, lambda *args: self.check_exclusive_options('reihe'))
        init_var('gegner_modus', 0, lambda *args: self.check_exclusive_options('gegner_modus'))
        init_var('jaeger_modus', 0, lambda *args: self.check_exclusive_options('jaeger_modus'))
        init_var('kaenguru_modus', 0, lambda *args: self.check_exclusive_options('kaenguru_modus'))
        init_var('survival_modus', 0, lambda *args: self.check_exclusive_options('survival_modus'))
        init_var('zaehlen', 0)
        init_var('ton', 1)
        init_var('saveScore', 1) 
        self.zyklus = tk.IntVar(value=0)
        
        self.string_info_scheibenservo = 'ScheibenServo wird vielfältig verwendet:'+ \
             '\nDrehscheibe:' + \
             '\n  - Ohne weitere Optionen: -2=immer aus; -1=alle; sonst Servo 0 - 4'+\
             '\n  - Zufall-Modus: Gibt an wieviele der Ziele gedreht werden' + \
             '\nKlappscheibe:' + \
             '\n  - Zufall-Modus: Anzahl der Ziele (Wenn kein sinvoller Wert bei scheibenServo angegeben ist, dann nur 1 Ziel.)' + \
             '\n  - Zufall-Gegner-Modus: <=1: Ein Ziel je Spieler; >=2 Zwei Ziele je Spieler' + \
             '\n  - Jäger-Modus: Punkte je Runde für den Gejagten' + \
             '\n  - Känguru-Modus: Wird als maximale Schussanzahl je Spieler verwendet' +\
             '\n  - Wechsel-Modus: Bei 0/1: Liegt der Spieler zurück mit nur 0/1 Zielen, bekommt er den nächsten Nachbar als Bonustreffer dazu' 
       
        self.string_info_zufall = \
               'Drehscheibe:' + \
             '\nZufall: Es wird zufällig eine definierte Anzahl von Zielen gedreht'+ \
             '\n   -Die Anzahl wird durch die Variable ScheibenServo bestimmt (graues Feld)'+ \
             '\nKlappscheibe:'+\
             '\nZufall: Es werden zufällig eine definierte Anzahl von aktiviert'+\
             '\n   -Die Anzahl wird durch die Variable ScheibenServo bestimmt (graues Feld)'+ \
             '\nZufall+Gegner: Zweispielervariante'+\
             '\n   -Linker Spieler: Leuchtende Ziele '+ \
             '\n   -Rechter Spieler: Blinkende Ziele '
        
        self.string_info_reihe = \
               'Drehscheibe: Reihenmodus' + \
             '\n-Die Ziele werden einfach direkt der Reihe nach gedreht'+ \
             '\n-Variable ScheibenServo bestimmt den Anfangsservo'+ \
             '\nKlappscheibe: Wechselmodus'+\
             '\n-Der linke Spieler muss zunächst eins der beiden linken Ziele treffen.\n-Der rechte Spieler muss zunächst eins der beiden rechten Ziele treffen.\n-Die Anfangs undefinierte Mitte wechselt zugunsten des Spielers, der als erstes ein Ziel getroffen hat.\n-Punkte gibt es erst am Ende eines Zyklus.\n-Für jedes eingenommene Ziel gibt es einen Punkt.\n-Im nächsten Zyklus wird der Stand aus dem vorherigen übernommen.\n-Im letzten Zyklus gibt es für jedes eingenommene Ziel doppelte Punkte.'

        self.string_info_gegner = \
               'Drehscheibe: Gegnermodus ohne weitere Optionen' + \
             '\n   -Grundsätzlich hat der linke Spieler die linken und der rechte Spieler die rechten Ziele'+\
             '\n   -Für jeden Spieler wird zufällig eins seiner beiden Ziele gedreht'+\
             '\n   -Penalty (programme.csv) definiert Wahrscheinlichkeit wie oft Mitte gedreht wird'+\
             '\nKlappscheibe: Gegnermodus ohne weitere Optionen' + \
             '\n   -Der "normale" Gegnermodus:\n   -Der linke Spieler muss zunächst die beiden linken Ziele treffen.\n   -Der rechte Spieler muss zunächst die beiden rechten Ziele treffen.\n    -Hat ein Spieler seine zwei Ziele getroffen, bekommt er die Mitte für sich freigeschaltet.\n   -Trifft auch der andere Spieler seine zwei Ziele, wird die Mitte wieder deaktiviert.'+\
             '\nWeitere kombinierte Modi sind bei den jeweiligen Knöpfen erklärt.'

        self.string_info_jaeger = \
               'Klappscheibe:'\
             '\nEs gibt einen Jäger und einen Gejagten.\n-Der Jäger startet und trifft ein beliebiges Ziel.\n-Damit bestimmt der Jäger die zu verteidigenden Ziele für den Gejagten:\n  *Das gewählte Ziel\n  *Und das Ziel links daneben \n-Die Ziele vom gejagten blinken.\n-Der Jäger muss den Gejagten in der Zeit einkreisen.\n-Entsprechend muss der Jäger alle 3 weiteren leuchtenden Ziele treffen.\n-Sobald der Jäger oder der Gejagte sein Ziel erreicht, wird der Zyklus beendet.\n-Sowohl Jäger als auch Gejagter können maximal drei Punkte erreichen:'+\
             '\n  *Der Jäger erhält einen Punkt für jeden Treffer'+\
             '\n  *ScheibenServo bestimmt die Punkte je Runde für den Gejagten'

        self.string_info_kaenguru = \
               'Klappscheibe: Känguru-Modus' + \
             '\n-Die Ziele "hüpfen"! Trifft ein Spieler sein Ziel, springt dieses sofort auf eine neue Position.'+ \
             '\n-Ein dynamisches Reaktions- und Verfolgungsspiel.'+ \
             '\n-Die Variable ScheibenServo bestimmt hierbei die Anzahl der Sprünge je Zyklus.'

        self.string_info_survival = \
               'Zusatz-Option: Survival-Modus' + \
             '\n-Gnadenlos: Man erreicht den nächsten Zyklus (Runde) nur, wenn alle Ziele getroffen wurden.'+ \
             '\n-Verfehlt man auch nur ein Ziel oder ist zu langsam, ist das Spiel sofort vorbei!'

        self.string_info_buzztick = \
               'Zusatz-Option: BuzzTick / Trick' + \
             '\n-Klappscheibe (BuzzTick): Sorgt für psychologischen Druck. In den letzten 4 Sekunden startet ein Ticken, das mit einem Buzzer endet.'+ \
             '\n-Drehscheibe (Trick): Geisel-Simulation! Ziele drehen sich zu X% auf 180° statt 90° und dürfen nicht getroffen werden.'+ \
             '\n-Hinweis: Erfahrene Schützen erkennen den Trick oft schon am längeren Drehwinkel der Servos.'

 #       self.string_info_buzztick = \
 #              'Zusatz-Option: BuzzTick / Trick' + \
 #            '\n-Sorgt für psychologischen Druck am Ende eines Zyklus.'+ \
 #            '\n-In den letzten 4 Sekunden startet ein lautes Uhren-Ticken.'+ \
 #            '\n-Die Runde endet mit einem lauten Buzzer-Sound.'

        self.string_info_zaehlen = \
               'Anzeige-Option: Zählen' + \
             '\n-Versteckt die Runden-Nummer bei "Achtung" und "Feuer", wenn deaktiviert.'+ \
             '\n-Erhöht die Spannung, da das Ende des Zyklus schwerer abzuschätzen ist.'

        self.string_info_ton = \
               'Audio-Option: Ton' + \
             '\n-Aktiviert oder deaktiviert sämtliche Soundeffekte der Anlage.'

        self.string_info_save_servooff = \
               'Hardware-Option: Save / ServoOff' + \
             '\n-Aktiviert (AN): Speichert Ergebnisse (Highscore). Servos bewegen sich nicht (Ideal für Klappscheiben).'+ \
             '\n-Deaktiviert (AUS): Keine Speicherung. Servos werden angesteuert (Ideal für Drehscheiben).'+ \
             '\n-Tipp: Dient primär zum schnellen Umschalten zwischen Klapp- und Drehscheiben-Modus.'
               

    def set_state(self, new_state: GameState):
        if not isinstance(new_state, GameState):
            raise ValueError("Ungültiger Zustand!")
        else:
            self._state = new_state
            #self.SDeluebs.root.after(0, self._apply_state_ui, new_state)
            self._apply_state_ui(new_state)
            
            #self.gamestate_stringvar.set(new_state.value)
            #self.SDeluebs.MyCanvas['background'] = new_state.color
            #self.SDeluebs.MyCanvas.itemconfig(self.SDeluebs.bg_image_id, image=self.SDeluebs.hintergrundbilder[self.get_state().name])    

    def _apply_state_ui(self, state):
        """
        Diese Hilfsfunktion wird von Tkinter im Haupt-Thread aufgerufen.
        Hier darf alles gemacht werden, was die GUI verändert.
        """
        # Sicherer Zugriff auf die StringVar
        self.gamestate_stringvar.set(state.value)
        # Sicherer Zugriff auf das Canvas-Widget
        self.SDeluebs.MyCanvas['background'] = state.color
        #self.SDeluebs.root.update_idletasks()

    
    def get_state(self): return self._state

    # Diese Funktion nutzt du von nun an ÜBERALL, wenn ein neues Programm geladen wird!
    def set_basis_programm_name(self, neuer_name: str):
        self._base_programm_name = neuer_name # 1. Die reinen Daten speichern
        self._refresh_gui_name()              # 2. Die Tkinter-GUI aktualisieren

    def set_replay_match(self, match_id_string: str):
        """Aktiviert den Replay-Modus für ein spezifisches Match (z.B. 'MATCH000089')"""
        self.aktuelle_replay_id = match_id_string
        self._refresh_gui_name()

    def clear_replay_match(self):
        """Beendet den Replay-Modus"""
        self.aktuelle_replay_id = None
        self._refresh_gui_name()

    def _refresh_gui_name(self):
        """Mischt alle Daten zusammen und aktualisiert die GUI"""
        # 1. Wir starten mit dem Rohteig (z.B. "Wechsel-Modus")
        namens_teile = [self._base_programm_name]
        
        # 2. Zuckerschrift: Ist es ein Replay? Dann ID anhängen!
        if self.aktuelle_replay_id:
            namens_teile.append(f"({self.aktuelle_replay_id})")
            
        # 3. Kirschen: Sind noch Tags da? (z.B. "(modifiziert)")
        tag_suffix = self.get_tag_string()
        if tag_suffix:
            namens_teile.append(tag_suffix)
            
        # 4. Alles mit Leerzeichen verbinden und in die dumme StringVar schieben
        fertiger_name = " ".join(namens_teile)
        self.programm_name.set(fertiger_name)
        
    def add_tag(self, tag: Tag):
        self._tags.add(tag)
        self._refresh_gui_name()
        #self.update_tag_string(self.programm_name)

    def clear_tags(self):
        self._tags.clear()
        self._refresh_gui_name()
        #self.update_tag_string(self.programm_name)

    def remove_tag(self, tag: Tag):
        self._tags.discard(tag)
        self._refresh_gui_name()
        #self.update_tag_string(self.programm_name)

    def has_tag(self, tag: Tag) -> bool:
        return tag in self._tags

    def get_tag_string(self) -> str:
        return ' '.join(tag.value for tag in sorted(self._tags, key=lambda t: t.name))
    
    #def update_tag_string(self, string_var: tk.StringVar): #string_var ist hier in den meisten Fällen "self.programm_name"
    #    #"""Entfernt alte Tags und hängt die aktuellen Tags an."""
    #    self.remove_tag_string(string_var)
    #    base_name = string_var.get()
    #    tag_suffix = self.get_tag_string()
    #    if tag_suffix:
    #        if Tag.REPLAY in self._tags: tag_suffix = str(f" {self.aktuelle_replay_id}")
    #        #print(f"{self._tags.value} {Tag.REPLAY.value} {self._tags == Tag.REPLAY}")
    #        string_var.set(f"{base_name} {tag_suffix}")
    #    else:
    #        string_var.set(base_name)      

    def remove_tag_string(self, string_var: tk.StringVar): #string_var ist hier in den meisten Fällen "self.programm_name"
        #"""Entfernt alle bekannten Tags aus dem StringVar."""
        name = string_var.get()
        for tag in Tag:
            name = name.replace(tag.value, '')
        # Bereinige Leerzeichen
        name = ' '.join(name.split())
        string_var.set(name)
    
    def update4wiederholungen(self, *args):
        try:
            self.zyklus.set(0)#self.wiederholungen.get())
        except tk.TclError:
            i=0
    
    def update4feuer2default(self, *args):
        try:
            if self.stand==-1: self.default_feuerzeit = self.feuer.get()
        except tk.TclError:
            i=0   
            
    def set_modus_to_custom(self, *args):
        if not self.system_update_laeuft: self.add_tag(Tag.MODIFIZIERT)
        #self.add_tag(Tag.MODIFIZIERT)
             
        #################################################
        ###########  Hauptschleife  #####################
        #################################################         
 
    def buttonCountdownClick(self):
        #self.zeitverlust_messung() #Ausführen um Wert zurückzusetzen
        #self.loop_anzahl+=1
        #print(self.loop_anzahl, time.monotonic()) 
        
        if self.cancel==False:
            self.SDeluebs.buttonStart.place_forget()
              
            if self.stand > 1: # Zähleraktualisierung
                self.stand = self.stand - 1
                self.SDeluebs.update_hauptlabel()
                #BuzzTicker Sound # Es muss GameState.FEUER sein; GameState PLAYER1 oder PLAYER2 oder WINNER oder END gehen nicht!
                if self.get_state()==GameState.FEUER and self.stand==4 and self.ton.get()==1 and self.trick.get() == 1 and self.saveScore.get() == 1: self.SDeluebs.sound_buzzticker.play()
                self.SDeluebs.root.after(int(1000-self.zeitverlust_messung()), self.buttonCountdownClick)            
            else:
                
                #Wenn vorher Feuer war, dann wurde ein Zyklus jetzt beendet
                if self.get_state().is_action_state():
                    #Sound
                    # HACK: Verhindert Doppel-Sound im Wechsel-Modus, wenn BuzzTicker aktiv ist
                    if not (self.trick.get() == 1 and self.saveScore.get() == 1):
                        if self.ton.get()==1: self.SDeluebs.sound_pfeife.play()
                    #FRÜHERES UPDATE VOM ZYKLUS
                    #if self.survival_modus.get()==0: self.zyklus.set(self.zyklus.get()-1) #Hier KEIN Survival Modus 
                    #else: #Hier Survival Modus Updates                      
                    #    self.zyklus.set(self.zyklus.get()+1)
                    #HardwareDeLuebs
                    if self.reihe.get()==1 and self.gegner_modus.get()==1: #Hier Wechselmodus-Punkte
                        self.SDeluebs.KSobjekt.transfer_punkte_wechsel()
                    self.SDeluebs.KSobjekt.Transfer_zyklus2durchgang()
                    if self.saveScore.get()==1: self.SDeluebs.KSobjekt.SaveHighscore_zyklus() #Inklusive Jäger-Switch
                
                # --- BEDINGUNGEN FÜR DEN NÄCHSTEN ZYKLUS PRÜFEN ---
                ist_sicherheit = (self.get_state() == GameState.SICHERHEIT)
                # Alle Status-Arten, die eine laufende oder gerade beendete Runde repräsentieren
                feuer_status_liste = [
                    GameState.FEUER, 
                    GameState.PLAYER1, 
                    GameState.PLAYER2, 
                    GameState.WINNER, 
                    GameState.END
                ]
                # Im normalen Modus abbrechen, wenn wir das Ende der LETZTEN Runde erreicht haben
                letzte_runde_beendet = (self.get_state() in feuer_status_liste) and (self.zyklus.get() >= self.wiederholungen.get())
                normal_weiter = (self.survival_modus.get() == 0) and not letzte_runde_beendet
                survival_weiter = (self.survival_modus.get() == 1) and self.zyklus_ueberlebt                
                #Hier kommt noch ein Zyklus                                
                if ist_sicherheit or normal_weiter or survival_weiter:
                    
                    #Hier Wechsel zu Vorbereiten
                    if self.get_state()==GameState.SICHERHEIT: 
                        self.laufzeit = time.monotonic()        
                        self.set_state(GameState.VORBEREITEN)
                        self.match_id = self.get_next_match_id() #Match-ID-Updaten
                        self.SDeluebs.HSobjekt.event_log = [] #Event-Log zurücksetzen
                        self.stand = self.vorbereiten.get()
                        if self.survival_modus.get()==0: 
                            self.zyklus.set(0) #ES wird jetzt immer auf 0 gesetzt
                        else: #Wenn Survival-Modus:                           
                            self.zyklus.set(0) #ES wird jetzt immer auf 0 gesetzt
                            self.feuer.trace_remove('write', self.feuer_trace)
                            self.feuer.set(self.default_feuerzeit)
                        self.SDeluebs.update_graphic()
                        #HardwareDeluebs
                        if self.saveScore.get()==1: self.SDeluebs.KSobjekt.SavePgm_Start()
                        self.SDeluebs.KSobjekt.Reset_durchgang()
                        if self.scheibenServo.get()!=-2: self.SDeluebs.DSobjekt.update_servos() 
                        self.SDeluebs.KSobjekt.match_timeline.clear()
                
                                         
                    #Hier Wechsel zu Laden
                    elif (self.get_state()==GameState.VORBEREITEN or self.get_state().is_action_state()) and self.ladenGelb.get()>0:  
                        self.set_state(GameState.LADEN)
                        self.stand=self.ladenGelb.get()
                        self.SDeluebs.update_graphic()
                        #HardwareDeLuebs
                        if self.scheibenServo.get()!=-2: self.SDeluebs.DSobjekt.update_servos()
                    
                    #Hier Wechsel zu Achtung
                    elif (self.get_state()==GameState.LADEN or self.get_state()==GameState.VORBEREITEN or self.get_state().is_action_state()): 
                        self.set_state(GameState.ACHTUNG)
                        self.stand=self.achtung.get()
                        #Anpassen des Zyklus (hierher wegen Event log)
                        self.zyklus.set(self.zyklus.get()+1)
                        self.SDeluebs.update_graphic()
                        if self.ton.get()==1: 
                            if self.survival_modus.get()==0 and self.jaeger_modus.get()==0: self.SDeluebs.sound1.play()
                            if self.survival_modus.get()==1: self.SDeluebs.tts.say('Feuerzeit '+str(self.feuer.get())+' Sekunden') 
                            if self.jaeger_modus.get()==1:
                                jaeger_name = self.spieler.get() if self.SDeluebs.KSobjekt.players[0].is_jaeger else self.spieler2.get() 
                                self.SDeluebs.tts.say('Jäger ist '+jaeger_name) 
                        #HardwareDeLuebs
                        if self.scheibenServo.get()!=-2: self.SDeluebs.DSobjekt.update_servos()
                        self.SDeluebs.KSobjekt.LEDsOff()
                        
                    #Hier Wechsel zu Feuer
                    elif (self.get_state()==GameState.ACHTUNG): 
                        self.set_state(GameState.FEUER)
                        self.stand=self.feuer.get()
                        #Anpassen des Zyklus (hierher wegen Event log)
                        self.zyklus_ueberlebt = False #Sofern das nicht geändert wird, wurde die Runde nicht überlebt 
                        #if self.survival_modus.get()==1: #Hier Survival Modus Updates
                        #    self.zyklus.set(self.zyklus.get()+1)      
                        #elif self.zyklus.get()==-1: self.zyklus.set(self.wiederholungen.get()) #Hier erster Zyklus ohne Survival Mouds
                        #else: self.zyklus.set(self.zyklus.get()-1) #Hier KEIN Survival Modus                         
                        self.SDeluebs.update_graphic()
                        if self.ton.get()==1: self.SDeluebs.sound0.play()
                        #HardwareDeLuebs
                        self.SDeluebs.KSobjekt.Reset_zyklus() # Das muss hier möglichst spät sein, damit die Zeitberechnung erst hier beginnt.
                        self.SDeluebs.KSobjekt.init_zyklus()
                        if self.scheibenServo.get()!=-2: self.SDeluebs.DSobjekt.update_servos()                    
                    
                    self.SDeluebs.root.after(int(1000-self.zeitverlust_messung()), self.buttonCountdownClick)    
                    
                #Hier Programmende erreicht.
                else: 
                    #HardwareDeluebs
                    self.buttonResetClick()
                    if self.saveScore.get() == 1:#  and self.aktuelle_replay_id is None: 
                        # 1. Highscore speichern und die Daten "auffangen"
                        hs_entry = self.SDeluebs.KSobjekt.SaveHighscore_durchgang() 
                        # (Hinweis: Stelle sicher, dass SaveHighscore_durchgang das hs_entry auch mit 'return' an diese Stelle zurückgibt!)
                        # 2. Beides zusammen an save_match übergeben
                        self.SDeluebs.HSobjekt.save_match(self.SDeluebs.KSobjekt.match_timeline, hs_entry)
                        # 3. Aufräumen
                        self.SDeluebs.KSobjekt.match_timeline.clear()
        #self.cancel = False     #Evtl nicht merhr wichtig

    def buttonResetClick(self):
        if not self.stand==-1 and (self.get_state() is not GameState.RESET):
            #print('Oh Mann')
            self.cancel = True #Abbrechen sofern noch ein Loop läuft 
            ##Reset-Bildschirm
            self.set_state(GameState.RESET)
            self.stand = 'Warten'
            self.SDeluebs.update_graphic()
            if self.survival_modus.get()==1: #Wiedereinschalten sofern der Trace für Feuer durch den Survival-Modus ausgeschaltet wurde.
                self.feuer_trace = self.feuer.trace_add('write', self.set_modus_to_custom) 
            #HardwareDeLuebs
            if self.scheibenServo.get()!=-2: self.SDeluebs.DSobjekt.update_servos()
            #time.sleep(3)
            #self.root.after(int(30000), self.sleep_after) 
            self.SDeluebs.root.after(int(4000), self.continueRestetClick)            
    
    def continueRestetClick(self):
        self.set_state(GameState.SICHERHEIT)
        self.zyklus_ueberlebt = True
        self.SDeluebs.update_graphic()
        self.SDeluebs.update_hauptlabel()
        #HardwareDeLuebs
        self.SDeluebs.KSobjekt.LEDsOff()
        if self.scheibenServo.get()!=-2: self.SDeluebs.DSobjekt.update_servos()
        self.SDeluebs.buttonStart.place(x=210, y=920, width=145-40, height=80)    
        self.stand = -1 #Erst wenn self.stand wieder -1 ist, kann ein neues Spiel mit Strg gestartet werden.
        self.cancel = False #Neu bei dieser Methode hinzugefügt
    
    def vorbereiten_up(self):
        self.vorbereiten.set(self.vorbereiten.get() + 1)
    def vorbereiten_down(self):
        self.vorbereiten.set(self.vorbereiten.get() - 1)

    def ladenGelb_up(self): self.ladenGelb.set(self.ladenGelb.get()+1)
    def ladenGelb_down(self): self.ladenGelb.set(self.ladenGelb.get()-1)

    def achtung_up(self): self.achtung.set(self.achtung.get() + 1)
    def achtung_down(self): self.achtung.set(self.achtung.get() - 1)

    def feuer_up(self): self.feuer.set(self.feuer.get() + 1)
        #self.default_feuerzeit = self.feuer.get()
    def feuer_down(self): self.feuer.set(self.feuer.get() - 1)
        #self.default_feuerzeit = self.feuer.get()

    def wiederholungen_up(self): self.wiederholungen.set(self.wiederholungen.get() + 1)
    def wiederholungen_down(self): self.wiederholungen.set(self.wiederholungen.get() - 1)

    def scheibenServo_up(self): 
        if self.scheibenServo.get()<4: self.scheibenServo.set(self.scheibenServo.get() + 1)
        else: self.scheibenServo.set(4)
    def scheibenServo_down(self): 
        if self.scheibenServo.get()>-2: self.scheibenServo.set(self.scheibenServo.get() - 1)
        else: self.scheibenServo.set(-2)

    def zeitverlust_messung(self):
        #returnwert = (time.monotonic()-self.laufzeit)*1000
        #self.laufzeit = time.monotonic()
        #return returnwert    
        now = time.monotonic()
        delta = (now - self.laufzeit) * 1000
        ret = (delta % 1000)
        #print(ret) ###################################################################!!!!!!!!!!!!!!!!!!
        return ret if ret < 900  else (ret-1000)

    def setProgramm(self,pgmNr: int):
        #print(f"pgmNr {pgmNr}")
        if self.stand==-1: 
          with open('Programme.csv', mode ='r', encoding='utf-8') as file:
            csvFile = csv.reader(file, skipinitialspace=True)
            for _ in range(pgmNr+3): #Vorspringen auf die korrekte Zeile
                csvLine = next(csvFile)
            self.vorbereiten.set(int(csvLine[1]))
            self.ladenGelb.set(int(csvLine[2]))
            self.achtung.set(int(csvLine[3]))
            self.feuer.set(int(csvLine[4]))
            self.default_feuerzeit = self.feuer.get()
            self.scheibenServo.set(int(csvLine[6]))
            self.trickWahrsch.set(int(csvLine[7]))
            self.zufall.set(int(csvLine[8]))
            self.trick.set((int(csvLine[9])))
            self.reihe.set(int(csvLine[10]))
            self.gegner_modus.set(int(csvLine[11]))
            self.jaeger_modus.set(int(csvLine[12]))
            self.kaenguru_modus.set(int(csvLine[13]))
            self.survival_modus.set(int(csvLine[14]))
            self.survival_penalty=float(csvLine[15]) 
            self.wiederholungen.set(int(csvLine[5]))#Wiederholungen erst nach SURVIVAL, damit das Label oben rechts sich updatet
            #self.check_exclusive_options(self.chk_gegner_modus, self.gegner_modus) #########ACHTUNG WIEDER EINSCHALTEN################
            self.zaehlen.set(int(csvLine[16]))
            self.ton.set(int(csvLine[17]))
            self.saveScore.set(int(csvLine[18]))
            raw_text = csvLine[19].strip().strip('"')
            formatted_text = raw_text.replace('\\n', '\n')
            self.programm_info.set(formatted_text)
            #self.programm_name.set(csvLine[0].strip()) #Das muss am Ende stehen  
            self.set_basis_programm_name(csvLine[0].strip())
            self.clear_tags()
            if self.ton.get()==1: self.SDeluebs.sound_load.play()            

    def check_exclusive_options(self, name: str):
        #Wenn Reihe aktiviert wird, andere abschalten
        if name=='reihe' and self.reihe.get()==1:
            self.zufall.set(0)
            #self.gegner_modus.set(0)
            self.jaeger_modus.set(0)
            self.kaenguru_modus.set(0)
            self.survival_modus.set(0)
            #self.SDeluebs.entryspieler2.place_forget()
        #Wenn Zufall aktiviert wird, Reihe, Jaeger und Känguru abschalten
        if name=='zufall' and self.zufall.get()==1:
            self.reihe.set(0)
            self.jaeger_modus.set(0)
            self.kaenguru_modus.set(0)
        #Wenn Gegner-Modus aktiviert wird, Reihe abschalten
        if name=='gegner_modus' and self.gegner_modus.get()==1:
            #self.reihe.set(0)
            self.SDeluebs.entryspieler2.place(x=715, y=960-40, width=300, height=80)
        #Wenn Jaeger-Modus aktiviert wird, Gegner einschalten; Zufall, Reihe und Känguru abschalten
        if name=='jaeger_modus' and self.jaeger_modus.get()==1:
            self.gegner_modus.set(1)            
            self.reihe.set(0)
            self.zufall.set(0)       
            self.kaenguru_modus.set(0)    
            self.SDeluebs.entryspieler2.place(x=715, y=960-40, width=300, height=80) #braucht man das hier?
        #Wenn Gegner ausgeschaltet wird Jägermodus abschalten und Spieler2-Anzeige entfernen
        if (name=='gegner_modus' and self.gegner_modus.get()==0): #or name=='Jäger')
            self.SDeluebs.entryspieler2.place_forget()
            self.jaeger_modus.set(0)
            #self.gegner_modus.set(0)
        #Wenn Känguru-Modus aktiviert wird Reihe, Zufall und Jäger abschalten
        if name=='kaenguru_modus' and self.kaenguru_modus.get()==1:
            self.reihe.set(0)
            self.zufall.set(0)
            self.jaeger_modus.set(0)
        #Wenn Survival-Modus aktiviert wird Reihe deaktivieren    
        if name=='survival_modus' and self.survival_modus.get()==1:
            self.reihe.set(0)
            
    #Funktion um die ID für das Logevent zu finden
    def get_next_match_id(self):
        highest_id = 0
        log_dir = os.path.join("savegames", "logs")
        os.makedirs(log_dir, exist_ok=True) # Ordner erstellen, falls er fehlt    
        for filename in os.listdir(log_dir): # os.listdir ist das Python-Äquivalent zu "ls" oder "dir"
            # Prüfen, ob das Namensmuster stimmt (MATCH....json)
            if filename.startswith("MATCH") and filename.endswith(".json"):
                try: 
                    # Schneidet "MATCH" (5 Zeichen) vorne und ".json" (5 Zeichen) hinten ab
                    number_str = filename[5:-5] 
                    number = int(number_str)
                    if number > highest_id:
                        highest_id = number
                except ValueError:
                    pass # Falls mal eine Datei "MATCH_kaputt.json" heißt, ignorieren wir sie
        if self.SDeluebs.HSobjekt.highscore_manager.data:
            highest_json_id = max([eintrag.get("match_id", 0) for eintrag in self.SDeluebs.HSobjekt.highscore_manager.data])
            if highest_json_id > highest_id:
                highest_id = highest_json_id
        return highest_id + 1
