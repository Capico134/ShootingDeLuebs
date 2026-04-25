import os #Um die Version zu dedektieren
import re #Um die Version zu dedektieren
#import importlib #Um Importe mittels String durchzuführen
#Version aus Dateinamen extrahieren
#filename = os.path.basename(__file__)
#match = re.search(r'v(\d+)_(\d+)_(\d+)', filename)
#if match:
#    VERSION = f"v{match.group(1)}_{match.group(2)}_{match.group(3)}"
#else:
#    VERSION = "v1_0_0"  # Fallback
#SMDeLuebs = importlib.import_module(f"StateManagerDeLuebs_{VERSION}")
from StateManagerDeLuebs import GameState

import time #für die sleep-Funktion
import datetime as dt #Datum/Uhrzeit ausgeben
import random
import timeit # Für die Zeitmessung #WAHRSCHEINLICH OBSOLETE?
import pygame
import threading
try:
    from robot_hat import Servo
except ImportError:
    import robot_hat_mock
    Servo = robot_hat_mock.Servo    
    init_mock_hardware_gui = robot_hat_mock.init_mock_hardware_gui
      
class Player:
    def __init__(self):
        self.name=None #tk.StrinVar
        self.punkte_durchgang = 0
        self.speedpunkte_durchgang = 0
        self.treffer = [-1, -1, -1, -1, -1]
        self.punkte_zyklus = 0
        self.speedpunkte_zyklus = 0
        self.restzeit_zyklus = [0, 0, 0, 0, 0]
        self.is_jaeger = True
        
    def reset_zyklus(self):
        self.treffer = [-1, -1, -1, -1, -1]
        self.punkte_zyklus = 0
        self.speedpunkte_zyklus = 0
        self.restzeit_zyklus = [0, 0, 0, 0, 0]
        
    def set_verloren(self):
        for i in range(5):
            self.treffer[i] = -2
        self.punkte_zyklus = 0
        self.speedpunkte_zyklus = 0
        self.restzeit_zyklus = [0, 0, 0, 0, 0]
        
    def to_dict(self):
        return {
            "name": self.name.get(),  # .get() weil es ein tk.StringVar ist
            "punkte_durchgang": self.punkte_durchgang,
            "speedpunkte_durchgang": self.speedpunkte_durchgang,
            "treffer": self.treffer,
            "punkte_zyklus": self.punkte_zyklus,
            "speedpunkte_zyklus": self.speedpunkte_zyklus,
            "restzeit_zyklus": self.restzeit_zyklus,
            "is_jaeger": self.is_jaeger
        }        
        
    def switch_jaeger(self):
        self.is_jaeger = not self.is_jaeger #Die Jäger wechseln sich ab    

def set_punkte(player: Player, welcherSchuss: int, feuer: int, referenzzeit: float, key: int, multiplier: int = 1):
    player.treffer[welcherSchuss]=key
    restzeit = max ( round((feuer - (time.monotonic() - referenzzeit)), 3) , 0 )
    player.restzeit_zyklus[welcherSchuss] = restzeit
    player.punkte_zyklus = player.punkte_zyklus + multiplier 
    player.speedpunkte_zyklus = player.speedpunkte_zyklus + (restzeit/feuer/5) * multiplier

class Klappscheibe:
   
    def __init__(self, SDeluebs):#modi, score_file, feuer):
        self.SDeluebs = SDeluebs
        self.event_log = []  # Liste zur Zwischenspeicherung zum Debugging
        self.highscore_log = ""  # String zur Zwischenspeicherung für den highscore_log
        self.match_timeline = [] # Zur Zwischenspeicherung für den Event_log
        
        #Players initialisieren
        self.players = [Player(), Player()]
        self.players[1].is_jaeger=False #self.players[0]=True per Default 
        self.players[0].name=self.SM.spieler #tk.StrinVar
        self.players[1].name=self.SM.spieler2#tk.StrinVar
        
        self.jaeger_wahl = -1 #-1=Jäger hat noch nicht gewählt; sonst gleich der Wahl des Jägers 
        self.richtung0bis4 = True # bei False 4bis0
        self.ReferenzZeit = time.monotonic()
        self.ziel_wahl = [] #Beispiele: 
                            #Einzelspieler mit 3 Zufallszielen: [4, 0, 2] müssen getroffen werden
                            #Zweispieler mit einem Zufallsziel je Spieler: [4, 0, 1, 2]: player_index=0 hat die 4; player_index=1 hat die 1 
                            #Zweispieler mit 2 Zufallszielen je Spieler:   [4, 0, 1, 2]: player_index=0 hat die 4 und die 0; player_index=1 hat die 1 und die 2
                            #Jägermodus: [3, 4, 0, 1, 2]: Jäger hat die 3 ausgewählt. Gejagter hat die 3 und die 4; Jäger hat die 0, 1 und 2
                            #Känguru-Modus: Einzelspieler: [1]: Aktuelles Ziel; Gegner-Modus: [2,4]: Aktuelle Ziele für Spieler 1 und 2
                            #Wechsel-Modus: [2, 2, -1, 1, 1] Dies ist die Anfangssituation: Die beiden Linken sind von Spieler 1 zu treffen; die Mitte ist ungefiniert; die beiden Rechten sind von Spieler 2 zu treffen.
                            
        self.verwendete_zeit = -1
              
        #LEDOU
        self.LEDs = [Servo(f"P{i}") for i in [6,7,8,9,10]]
        self.LED_status = [False, False, False, False, False]
        self.blink_freq = 167  # Initialisiere die Blinkfrequenz in Millisekunden
        self.blinking = [False, False, False, False, False]
        self.LEDsOff()

    @property
    def SM(self):
        return self.SDeluebs.SMobjekt

    def name_winning_player(self, name: str):
        self.SDeluebs.tts.say('Gewinner ist '+name) 

    def init_zyklus(self): #Erstellen der ziel_wahl
        anzahlZiele = 1 #Wenn kein sinvoller Wert bei scheibenServo angegeben ist, dann nur 1 Ziel.
        if self.SM.scheibenServo.get() > 0 and self.SM.scheibenServo.get() < 5: anzahlZiele = self.SM.scheibenServo.get()
        
        #Zufall mit Gegnermodus
        if self.SM.gegner_modus.get()==1 and self.SM.zufall.get()==1: 
            self.ziel_wahl = random.sample(range(5), 4) #bei anzahlZiele=1 ist ziel_wahl[0] für Spieler 1 und ziel_wahl[2] für Spieler 2      
            #Player 1:
            self.SetLED(self.ziel_wahl[0],True) 
            if anzahlZiele>1: self.SetLED(self.ziel_wahl[1],True) 
            #Player 2:
            self.SetBlinking(self.ziel_wahl[2],True)          
            if anzahlZiele>1: self.SetBlinking(self.ziel_wahl[3],True)    
                    
        #Zufall ohne Gegnermodus
        elif self.SM.gegner_modus.get()==0 and self.SM.zufall.get()==1:
            self.ziel_wahl = random.sample(range(5), anzahlZiele)
            for wert in self.ziel_wahl:
                self.SetLED(wert,True)
                
        #Känguru-Modus
        elif self.SM.kaenguru_modus.get()==1:
            self.ziel_wahl = random.sample(range(5), self.SM.gegner_modus.get()+1)
            self.SetLED(self.ziel_wahl[0], True)         
            if self.SM.gegner_modus.get()==1:
                self.SetBlinking(self.ziel_wahl[1],True)         
                
        #Wechsel-Modus
        elif self.SM.reihe.get()==1 and self.SM.gegner_modus.get()==1:
            #print(self.ziel_wahl)
            if all(player.punkte_durchgang == 0 for player in self.players):
                self.ziel_wahl = [2, 2, -1, 1, 1]
            for index, ziel in enumerate(self.ziel_wahl):
                if ziel == 1: self.SetLED(index, True)
                if ziel == 2: self.SetBlinking(index, True)
                
        else: self.ziel_wahl = [] 
                
    
    def set_treffer(self, key: int):
        player = self.players[0]
        welcherSchuss = self.welcherSchuss(player.treffer)
        if self.SM.get_state().is_action_state():
            # Wenn es der 0te Schuss ist, dann ist jede scheibe akzeptabel
            if welcherSchuss == 0: 
                set_punkte(player, welcherSchuss, self.SM.feuer.get(), self.ReferenzZeit, key) #Punkte zuweisen!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                #LEDOU
                self.SetLED(player.treffer[0],True)
            #Wenn es der 1te Schuss ist, wird die Richtung definiert
            elif welcherSchuss == 1:
                player.treffer[1]=key #GEHT DAS BESSSER ?????????(ES IST DOPPELT MIT set_punkte)
                #Wenn es zweimal die gleiche Scheibe war ist die zyklus verloren
                if player.treffer[0]==player.treffer[1]: 
                    self.checkVerloren(True)
                else: 
                    if player.treffer[1]>player.treffer[0]: self.richtung0bis4 = True
                    else: self.richtung0bis4 = False
                    set_punkte(player, welcherSchuss, self.SM.feuer.get(), self.ReferenzZeit, key) #Punkte zuweisen!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                    #LEDOU
                    self.SetLED(player.treffer[1],True)    
            #Hier zwischen dem 2tem und dem 4ten Schuss oder -1 für bereits verloren
            elif welcherSchuss > 1: 
                    player.treffer[welcherSchuss]=key #GEHT DAS BESSSER ?????????(ES IST DOPPELT MIT set_punkte)
                    self.checkVerloren(False)    
                    if player.treffer[0]!=-2:  
                        set_punkte(player, welcherSchuss, self.SM.feuer.get(), self.ReferenzZeit, key) #Punkte zuweisen!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                        #LEDOU
                        self.SetLED(player.treffer[welcherSchuss],True)
                        if self.SM.ton.get() == 1 and welcherSchuss == 4:
                            self.SDeluebs.sound_win.play()    
                            self.set_ueberlebt()
            else: self.checkVerloren(True)             
    
    def set_treffer_jaeger(self, key: int):
        if self.SM.get_state().is_action_state():
            #Prüfen wer Jäger und Gejagter ist
            if self.players[0].is_jaeger: 
                jaeger=self.players[0] 
                gejagter=self.players[1] 
            else: 
                jaeger=self.players[1] 
                gejagter=self.players[0] 
            #Der erste Schuss vom Jäger
            if self.jaeger_wahl==-1: 
                self.jaeger_wahl=key
                self.ziel_wahl = [key, (key+1)%5, (key+2)%5, (key+3)%5, (key+4)%5] #Jägermodus: [3, 4, 0, 1, 2]: Jäger hat die 3 ausgewählt. Gejagter hat die 3 und die 4; Jäger hat die 0, 1 und 2
                self.SetBlinking(self.ziel_wahl[0],True)  
                self.SetBlinking(self.ziel_wahl[1],True)  
                self.SetLED(self.ziel_wahl[2],True) 
                self.SetLED(self.ziel_wahl[3],True) 
                self.SetLED(self.ziel_wahl[4],True) 
                restzeit_zyklus=round((self.SM.feuer.get()-(time.monotonic()-self.ReferenzZeit)),3)
                jaeger.speedpunkte_zyklus = restzeit_zyklus / self.SM.feuer.get()/5                       # HIER GIBTS SPEEDPUNKTE
                if self.SM.ton.get()==1: self.SDeluebs.sound0.play()
            #Gejagter trifft
            elif key in [self.ziel_wahl[0], self.ziel_wahl[1]] and self.jaeger_wahl>-1:
                if key not in gejagter.treffer: #Einen neuen getroffen 
                    welcherSchuss =self.welcherSchuss(gejagter.treffer)
                    if welcherSchuss==0: multiplier= self.SM.scheibenServo.get()//2
                    else: #Alle beide Ziele erreicht:
                        self.jaeger_wahl=-2#-2 => Jetzt kann der andere nicht mehr Treffen
                        multiplier= self.SM.scheibenServo.get() - self.SM.scheibenServo.get()//2
                        if self.SM.ton.get() == 1: 
                            self.SDeluebs.sound_win.play()
                            self.SDeluebs.root.after(2500, lambda: self.name_winning_player(gejagter.name.get()))    
                        self.set_ueberlebt()
                        if self.SM.stand>5: self.SM.stand=5
                    set_punkte(gejagter, welcherSchuss, self.SM.feuer.get(), self.ReferenzZeit, key, multiplier) #Punkte zuweisen!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                    self.SetBlinking(key,False) 
                    self.SetLED(key,False) 
            #Jäger trifft
            elif key in [self.ziel_wahl[2], self.ziel_wahl[3], self.ziel_wahl[4]] and self.jaeger_wahl>-1:
                if key not in jaeger.treffer: #Einen neuen getroffen             
                    welcherSchuss =self.welcherSchuss(jaeger.treffer)
                    if welcherSchuss==2: #Alle drei Ziele erreicht:=2
                        self.jaeger_wahl=-2#-2 => Jetzt kann der andere nicht mehr Treffen
                        if self.SM.ton.get() == 1: 
                            self.SDeluebs.sound_win.play()    
                            self.SDeluebs.root.after(2500, lambda: self.name_winning_player(jaeger.name.get()))    
                        self.set_ueberlebt()
                        if self.SM.stand>5: self.SM.stand=5 
                    set_punkte(jaeger, welcherSchuss, self.SM.feuer.get(), self.ReferenzZeit, key) #Punkte zuweisen!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                    self.SetLED(key,False)             
 
    def set_treffer_kaenguru(self, key: int):
        if self.SM.get_state().is_action_state():
            player_index =-1
            if key == self.ziel_wahl[0]: player_index=0 #Spieler 1  
            elif self.SM.gegner_modus.get()==1: 
                if key == self.ziel_wahl[1]: player_index=1 #Spieler 2
            if player_index > -1:
                #print(player_index)
                player = self.players[player_index]
                welcherSchuss = self.welcherSchuss(player.treffer)
                #print(f"Spieler: {player_index} welcherSchuss: {welcherSchuss}")
                if welcherSchuss < self.SM.scheibenServo.get() and welcherSchuss!=-1: #scheibenServo wird als maximale Schussanzahl verwendet
                    set_punkte(player, welcherSchuss, self.SM.feuer.get(), self.ReferenzZeit, key) #Punkte zuweisen!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                    #Diese LED aus:
                    if player_index == 1: self.SetBlinking(key,False) 
                    self.SetLED(key,False) 
                    if welcherSchuss == (self.SM.scheibenServo.get()-1): #Gewonnen
                        if self.SM.ton.get() == 1: self.SDeluebs.sound_win.play()    
                        if self.SM.zyklus_ueberlebt==False: self.set_ueberlebt()
                        self.ziel_wahl[player_index]=-1 #Das Ziel auf -1 setzten, damit der andere Spieler, wenn er weiter spielt auch das letzte Ziel des Gewinners nochmal zufällig ausgewählt bekommen kann.
                    else: #Neue LED an:
                        possible_values = [i for i in range(5) if i not in self.ziel_wahl]
                        self.ziel_wahl[player_index] = random.choice(possible_values)
                        if player_index==0: self.SetLED(self.ziel_wahl[0], True)  
                        else: self.SetBlinking(self.ziel_wahl[1],True) 

    def set_treffer_wechsel(self, key: int):
        if self.SM.get_state().is_action_state():
            #print("Ziel_Wahl",self.ziel_wahl,"Key",key)
            if self.ziel_wahl[key] > 0:
                if self.ziel_wahl[key] == 1: #Spieler 1 hat getroffen
                    self.ziel_wahl[key] = 2
                    self.SetBlinking(key, True)   
                    #Hier Bonuspunkte:
                    if (self.SM.scheibenServo.get() > -1 and self.SM.scheibenServo.get() < 2) and self.ziel_wahl[2] != -1:
                        if self.ziel_wahl.count(1) > (3 - self.SM.scheibenServo.get()):
                            bonus_key = self.find_wechsel_bonus_key(key,self.ziel_wahl,1,-1)
                            if bonus_key is not None:                            
                                self.ziel_wahl[bonus_key] = 2
                                self.SetBlinking(bonus_key, True) 
                                self.append_event_snapshot(f"Bonus Spieler 1")
                                if self.SM.ton.get() == 1: self.SDeluebs.sound_orchestra.play()
                elif self.ziel_wahl[key] == 2: #Spieler 2 hat getroffen
                    self.ziel_wahl[key] = 1
                    self.SetBlinking(key, False)   
                    self.SetLED(key, True)
                    #Hier Bonuspunkte:
                    if (self.SM.scheibenServo.get() > -1 and self.SM.scheibenServo.get() < 2) and self.ziel_wahl[2] != -1:
                        if self.ziel_wahl.count(2) > (3 - self.SM.scheibenServo.get()):
                            bonus_key = self.find_wechsel_bonus_key(key,self.ziel_wahl,2,1)
                            if bonus_key is not None:
                                self.ziel_wahl[bonus_key] = 1
                                self.SetBlinking(bonus_key, False)   
                                self.SetLED(bonus_key, True)
                                self.append_event_snapshot(f"Bonus Spieler 2")
                                if self.SM.ton.get() == 1: self.SDeluebs.sound_orchestra.play()                    
                #Hier erstmalig die Mitte zuweisen:
                if self.ziel_wahl[2] == -1:
                    self.ziel_wahl[2] = self.ziel_wahl[key]
                    if self.ziel_wahl[2] == 1: self.SetLED(2, True)
                    if self.ziel_wahl[2] == 2: self.SetBlinking(2, True) 
                #Winner-Sound:
                if self.SM.ton.get() == 1 and all(ziel == self.ziel_wahl[0] for ziel in self.ziel_wahl):
                    self.SDeluebs.sound_win.play()

    def find_wechsel_bonus_key(self, key, ziel_wahl, player_id, direction):
        """
        Sucht zyklisch nach dem nächsten Ziel des Gegners.
        :param key: Der aktuell getroffene Index (0-4)
        :param ziel_wahl: Die Liste der Ziele [2, 1, 2, 2, 2]
        :param gegner_id: Die ID, die wir suchen (z.B. 1)
        :param direction: 1 für rechtsherum, -1 für linksherum
        """
        anzahl_ziele = len(ziel_wahl)
        #Wir prüfen die anderen 4 Positionen
        for i in range(1, anzahl_ziele):
            # Wir multiplizieren den Schritt (i) mit der Richtung (1 oder -1)
            pruef_index = (key + (i * direction)) % anzahl_ziele
            if ziel_wahl[pruef_index] == player_id:
                return pruef_index
        return None
    
    def transfer_punkte_wechsel(self):
        multiplier=1
        if self.SM.zyklus.get()==self.SM.wiederholungen.get(): multiplier=2
        #print(self.SM.zyklus.get())
        for index, ziel in enumerate(self.ziel_wahl):
            if ziel>0:
                player_index = (3-ziel)-1
                player = self.players[player_index]
                #print(f"Name: {player.name.get()} player_index: {player_index} ziel: {ziel} index: {index}")
                welcherSchuss = self.welcherSchuss(player.treffer)
                set_punkte(player, welcherSchuss, self.SM.feuer.get(), self.ReferenzZeit, index, multiplier)
   
    def set_treffer_zufall(self, key: int):
        player = self.players[0]
        if self.SM.get_state().is_action_state():
            welcherSchuss =self.welcherSchuss(player.treffer)
            if welcherSchuss!=-1:
                for ziel in self.ziel_wahl:
                    if ziel==key: # Eins der Ziele getroffen
                        if (key in player.treffer) == False: # auch ein Ziel getroffen, dass noch nicht da war 
                            set_punkte(player, welcherSchuss, self.SM.feuer.get(), self.ReferenzZeit, key) #Punkte zuweisen!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                            self.SetLED(key,False) 
                        else: #Einen doppelt getroffen    
                            self.checkVerloren(True)
            if player.treffer[welcherSchuss] < 0: self.checkVerloren(True) #Entweder schon -2 oder einen Falschen getroffen
            if self.welcherSchuss(self.players[0].treffer)==len(self.ziel_wahl):
                if self.SM.ton.get() == 1: self.SDeluebs.sound_win.play()    
                self.set_ueberlebt()                                

    def set_treffer_gegner_zufall(self, key: int):
        anzahlZiele = 1 #Wenn kleiner gleich 1 nur eine Scheibe pro Spieler
        if self.SM.scheibenServo.get() > 1 and self.SM.scheibenServo.get() < 5: anzahlZiele = 2 #sonst 2 Scheiben pro Spieler
        
        if self.SM.get_state().is_action_state():
            if key in self.ziel_wahl:
                key_position = self.ziel_wahl.index(key)
                if anzahlZiele==2 or key_position in [0, 2]:
                    if key_position < 2: player_index=0
                    else:                player_index=1
                    player = self.players[player_index]
                    welcherSchuss =self.welcherSchuss(player.treffer)
                    if ((key in player.treffer) == False) and welcherSchuss!=-1: # auch ein Ziel getroffen, dass noch nicht da war 
                        set_punkte(player, welcherSchuss, self.SM.feuer.get(), self.ReferenzZeit, key) #Punkte zuweisen!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                        if player_index == 1: self.SetBlinking(key,False) 
                        self.SetLED(key,False) 
                    else: #Einen doppelt getroffen oder schon -2 
                         self.setVerloren_gegner_zufall(player_index) 
                else: #Einen falschen getroffen bei anzahlZiele==1
                    self.setVerloren_gegner_zufall(0) 
                    self.setVerloren_gegner_zufall(1) 
            else: #Einen falschen getroffen
                    self.setVerloren_gegner_zufall(0) 
                    self.setVerloren_gegner_zufall(1)                      
            #Bereits zyklus_ueberlebt?:    
            if self.welcherSchuss(self.players[0].treffer)==anzahlZiele and self.welcherSchuss(self.players[1].treffer)==anzahlZiele:
                if self.SM.ton.get() == 1: self.SDeluebs.sound_win.play()    
                self.set_ueberlebt()

    def set_treffer_gegner(self, key: int):
        if self.SM.get_state().is_action_state():
            if key in [3, 4, 0, 1]:
                player_index = 0 if key in [3, 4] else 1
                #bonus_color = 'paleturquoise' if player_index == 0 else 'coral'
                other_player_index = 1 - player_index
                player = self.players[player_index]
                anderer_spieler = self.players[other_player_index]
                welcherSchuss = self.welcherSchuss(player.treffer)                
                if key not in player.treffer and welcherSchuss != -1: #Korrekten Schuss durchgeführt
                    set_punkte(player, welcherSchuss, self.SM.feuer.get(), self.ReferenzZeit, key) #Punkte zuweisen!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                    self.SetLED(key, True)
                    if welcherSchuss > 0: 
                        if self.bonus_modus == 0: #Bonus-Modus aktivieren
                            self.bonus_modus = player_index + 1
                            #self.SDeluebs.MyCanvas['background'] = bonus_color
                            self.SM.set_state(GameState.PLAYER1) if player_index == 0 else self.SM.set_state(GameState.PLAYER2)
                        elif (self.bonus_modus == other_player_index + 1) and (self.SM.survival_modus.get()==0): #Bonus deaktivieren (nicht beim Survival-Modus)
                            self.bonus_modus = -1
                            #self.SDeluebs.MyCanvas['background'] = 'grey'
                            self.SM.set_state(GameState.END)
                            if self.SM.ton.get() == 1:
                                self.SDeluebs.sound_pfeife.play()
                    self.SDeluebs.root.update_idletasks()
                else: #Einen doppelt getroffen
                    self.setVerloren_gegner(player_index)
            elif key == 2:
                self.handle_bonus_modus()#player_index, welcherSchuss, player)                    

    def handle_bonus_modus(self):#, player_index, welcherSchuss, player):
        #bonus_color = 'plum'
        player = None
        if self.bonus_modus==1: player = self.players[0]
        if self.bonus_modus==2: player = self.players[1]        
        if self.bonus_modus>0 and player is not None:
            welcherSchuss = self.welcherSchuss(player.treffer)
            if welcherSchuss==2: #Bonus getroffen
                self.bonus_modus = 3
                set_punkte(player, welcherSchuss, self.SM.feuer.get(), self.ReferenzZeit, 2, 2) #Punkte zuweisen!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                #self.SDeluebs.MyCanvas['background'] = bonus_color
                self.SM.set_state(GameState.WINNER)
                if self.SM.ton.get() == 1:
                    self.SDeluebs.sound_win.play()
                self.set_ueberlebt()
                self.SetLED(2, True)
                self.SDeluebs.root.update_idletasks()                                                    

    def set_ueberlebt(self):
        if self.SM.survival_modus.get()==1:
            self.SM.zyklus_ueberlebt=True
            self.verwendete_zeit = time.monotonic()-self.ReferenzZeit
            penalty_faktor = 1-self.verwendete_zeit/self.SM.feuer.get()*self.SM.survival_penalty
            self.SM.feuer.set(int(penalty_faktor*self.SM.feuer.get()+0.5)) 
            if self.SM.stand>5: self.SM.stand=5 
    
    def welcherSchuss(self, spieler_treffer: list[int]) -> int:
        #if spieler_treffer[0]==-2: return -1
        for index, value in enumerate(spieler_treffer):
            if value == -1:
                return index
        return -1  # Falls kein -1 im Array gefunden wird
  
    def checkVerloren(self, direktverloren: bool): #Für normale Klappscheibe und Zufallsmodus
        player = self.players[0]
        verloren = direktverloren
        if verloren==False:
            #print('Check ob Reihenfolge korrekt')
            for i in range(4):
                if self.richtung0bis4:  
                    if player.treffer[i+1]!=-1 and player.treffer[i+1]<=player.treffer[i]: verloren = True 
                else:                   
                    if player.treffer[i+1]!=-1 and player.treffer[i+1]>=player.treffer[i]: verloren = True
        #print('Verloren =',verloren)
        if verloren: 
            player.set_verloren()
            #Sound
            if self.SM.ton.get()==1: self.SDeluebs.sound_error.play()
            #LEDOU
            self.LEDsOff()   

    def setVerloren_gegner(self, player_index: int): #Für Gegnermodus
        self.players[player_index].set_verloren()
        if self.bonus_modus == player_index + 1:
            self.bonus_modus = -1
            self.SDeluebs.MyCanvas['background'] = 'grey'
        if self.SM.ton.get() == 1:
            self.SDeluebs.sound_error.play()
        self.SetLED((1-player_index) * 3 + 0, False)
        self.SetLED((1-player_index) * 3 + 1, False)

    def setVerloren_gegner_zufall(self, player_index: int): #Für Gegnermodus mit Zufall
        self.players[player_index].set_verloren()
        if self.SM.ton.get() == 1: self.SDeluebs.sound_error.play()
        if player_index==1:
            self.SetBlinking(self.ziel_wahl[2], False)
            self.SetBlinking(self.ziel_wahl[3], False)
        self.SetLED(self.ziel_wahl[2*player_index], False)
        self.SetLED(self.ziel_wahl[2*player_index+1], False)

    def Reset_zyklus(self):
        for player in self.players:
            player.reset_zyklus()
        self.richtung0bis4 = True
        self.bonus_modus = 0 # WARUM IST bonus_modus nicht in der Init von Klappscheibe? Man braucht bonus_modus auch nicht mehr, da man GameState dazu abrufen kann (Player1 oder Player2).
        self.verwendete_zeit = -1 #Für survival_modus
        self.jaeger_wahl = -1 #Für Jägermodus
        self.ReferenzZeit = time.monotonic()
        #self.LEDsOff()

    def Reset_durchgang(self):
        self.Reset_zyklus()
        self.highscore_log = ""  # Leere highscore_log  
        for player in self.players:
            player.punkte_durchgang = 0
            player.speedpunkte_durchgang = 0
            
    def SavePgm_Start(self):
        output = '\n'+self.SM.programm_name.get() \
                +'\n'+'Spieler: '    +self.SM.spieler.get()+' '+dt.datetime.now().strftime("%d.%m.%y %H:%M:%S") \
                +'\n'+'Zyklen: '     +str(self.SM.wiederholungen.get()) \
                +    ' Vorbereiten: '+str(self.SM.vorbereiten.get()) \
                +    ' Laden: '      +str(self.SM.ladenGelb.get()) \
                +    ' Achtung: '    +str(self.SM.achtung.get()) \
                +    ' Feuer: '      +str(self.SM.feuer.get()) \
                +    ' Scheibe: '    +str(self.SM.scheibenServo.get()) \
                +'\n'+'Zufall: '     +str(self.SM.zufall.get()) \
                +    ' Reihe: '     +str(self.SM.reihe.get()) \
                +    ' Gegner: '     +str(self.SM.gegner_modus.get()) \
                +    ' Jäger: '      +str(self.SM.jaeger_modus.get()) \
                +    ' Känguru: '    +str(self.SM.kaenguru_modus.get()) \
                +    ' Survival: '   +str(self.SM.survival_modus.get())
        if self.SM.gegner_modus.get()==1:
            output = output + ' Spieler2: '+self.SM.spieler2.get()
        print(output)
        #self.highscore_log.append(output+'\n')  ###################highscore_log###################    
    
    def Transfer_zyklus2durchgang(self):
        for player in self.players:
            player.punkte_durchgang = player.punkte_durchgang +  player.punkte_zyklus
            player.speedpunkte_durchgang = player.speedpunkte_durchgang + player.speedpunkte_zyklus
    
    def SaveHighscore_zyklus(self):
        #Debugging
        with open("debug_log.txt", "a") as logfile:
            logfile.write("\n".join(self.event_log) + "\n")
        self.event_log.clear()  # Leere die Liste nach dem Schreiben
        
        pl1_name = self.players[0].name.get()
        pl2_name = self.players[1].name.get()        
        if self.SM.jaeger_modus.get()==1:  
            pl1_name = 'Jäger: '+pl1_name if self.players[0].is_jaeger else 'Gejagter: '+pl1_name
            pl2_name = 'Jäger: '+pl2_name if self.players[1].is_jaeger else 'Gejagter: '+pl2_name
        outputtext = '=====================================================================\n'
        outputtext = outputtext + 'Zyklus: ' + str(self.SM.zyklus.get()) + '\n'
        outputtext = outputtext + (pl1_name+': '+' '.join(str(x) for x in self.players[0].treffer)+' Pkt: '+str(self.players[0].punkte_zyklus)+' Rest: '+' '.join(str(z) for z in self.players[0].restzeit_zyklus)+' Speed: '+str(round(self.players[0].speedpunkte_zyklus,3)))
        print(outputtext)
        self.highscore_log=self.highscore_log+"\n"+outputtext ###################highscore_log###################  
        outputtext2=''
        if self.SM.gegner_modus.get()==1:
            outputtext2 = (pl2_name+': '+' '.join(str(x) for x in self.players[1].treffer)+' Pkt: '+str(self.players[1].punkte_zyklus)+' Rest: '+' '.join(str(z) for z in self.players[1].restzeit_zyklus)+' Speed: '+str(round(self.players[1].speedpunkte_zyklus,3)))
            print(outputtext2)
            self.highscore_log=self.highscore_log+"\n"+outputtext2 ###################highscore_log###################  
        if self.SM.survival_modus.get()==1:
            outputtext3 = 'Verwendete Zeit: '+str(round(self.verwendete_zeit,3))+' Neue Feuerzeit: '+str(self.SM.feuer.get())
            print(outputtext3)     
            self.highscore_log=self.highscore_log+"\n"+outputtext3 ###################highscore_log###################  
        for player in self.players:
            player.switch_jaeger() #####################JÄGER-SWITCH##################################          
    
    def SaveHighscore_durchgang(self):
        punkte_durchgang=self.players[0].punkte_durchgang
        speedpunkte_durchgang=round(self.players[0].speedpunkte_durchgang,3)
        gesamtpunkte=round(self.players[0].punkte_durchgang+self.players[0].speedpunkte_durchgang,3)
        output = '=====================================================================\n'
        output = output + dt.datetime.now().strftime("%d.%m.%y %H:%M:%S")+'\n'
        output = output+self.players[0].name.get()+': Durchgang: Punkte: '+str(punkte_durchgang)+' Speedpunkte: '+str(speedpunkte_durchgang)+' Gesamtpunkte: '+str(gesamtpunkte)
        print(output)
        #self.highscore_log.append(output)#+'\n') ###################highscore_log###################  
        output2=''
        spieler2_punkte_durchgang=0      #ohne das Nullsetzen findet der Survivalmodus sonst diese Variablen nicht im Einzelspieler
        spieler2_speedpunkte_durchgang=0 #ohne das Nullsetzen findet der Survivalmodus sonst diese Variablen nicht im Einzelspieler
        spieler2_gesamtpunkte=0          #ohne das Nullsetzen findet der Survivalmodus sonst diese Variablen nicht im Einzelspieler
        if self.SM.gegner_modus.get()==1:
            spieler2_punkte_durchgang = self.players[1].punkte_durchgang
            spieler2_speedpunkte_durchgang = round(self.players[1].speedpunkte_durchgang,3)
            spieler2_gesamtpunkte = round(self.players[1].punkte_durchgang+self.players[1].speedpunkte_durchgang,3)
            output2 = self.players[1].name.get()+': Durchgang: Punkte: '+str(spieler2_punkte_durchgang)+' Speedpunkte: '+str(spieler2_speedpunkte_durchgang)+' Gesamtpunkte: '+str(spieler2_gesamtpunkte)
            print(output2)
            #self.highscore_log.append(output2) ###################highscore_log###################  
            if self.SM.survival_modus.get()==0:
                punkte_durchgang = max(punkte_durchgang,spieler2_punkte_durchgang)
                speedpunkte_durchgang= max(speedpunkte_durchgang,spieler2_speedpunkte_durchgang)
                gesamtpunkte = max(gesamtpunkte,spieler2_gesamtpunkte)
        if self.SM.survival_modus.get()==1:
            punkte_durchgang = punkte_durchgang+spieler2_punkte_durchgang
            speedpunkte_durchgang= speedpunkte_durchgang+spieler2_speedpunkte_durchgang
            gesamtpunkte = round(gesamtpunkte+spieler2_gesamtpunkte,3)
            output3 = ('Erreichter Zyklus: '+str(self.SM.zyklus.get()))
            #self.highscore_log.append(output3) ###################highscore_log###################  
            if self.SM.gegner_modus.get()==1:      
                output3 = output3+' Gesamtpunkte: '+str(gesamtpunkte)
            print(output3)  
        return self.SDeluebs.HSobjekt.save_score()#punkte_durchgang, speedpunkte_durchgang, gesamtpunkte)    

    def append_event_snapshot(self, event_type, value=None, player_idx=None):
        # Basis-Eventdaten
        snapshot = {
            "t": time.monotonic() - self.SM.laufzeit, # Aktuelle Spielzeit
            "z": self.SM.zyklus.get(),#Zyklus
            "tref": time.monotonic() - self.ReferenzZeit, # Spielzeit nach Feuerstart
            "m": self.SM.get_state().name,
            "a": event_type,
            "w": list(self.ziel_wahl),
        }
        if value is not None: snapshot["v"] = value
        if player_idx is not None: snapshot["p"] = player_idx
        # Spieler-Stats hinzufügen (kurze Keys für JSON-Sparen)
        for i, p in enumerate(self.players):
            prefix = f"p{i+1}_"
            snapshot.update({
                f"{prefix}pd":  p.punkte_durchgang,
                f"{prefix}spd": p.speedpunkte_durchgang,
                f"{prefix}t":   list(p.treffer), # Kopie der Liste!
                f"{prefix}pz":  p.punkte_zyklus,
                f"{prefix}spz": p.speedpunkte_zyklus,
                f"{prefix}rz":  list(p.restzeit_zyklus),
                f"{prefix}ij":  1 if p.is_jaeger else 0 # 1/0 spart Platz gegenüber true/false
            })
        self.match_timeline.append(snapshot)    
    #return snapshot

    def set_ziel_wahl_replay(self, w_liste):
        #startzeit = time.monotonic()
        """
        Synchronisiert den physischen Zustand (LEDs) mit der historischen Zielwahl.
        Unterscheidet zwischen Positions-Maps (Wechsel) und ID-Listen (Zufall/Känguru).
        Wird aktuell nur angewandt für Zufallsmodi.
        """
        Modus = None
        if   self.SM.zufall.get()==1 and self.SM.gegner_modus.get()==1:  Modus = "gegner_zufall" #Gegnermodus mit Zufallsmodus       
        elif self.SM.zufall.get()==1:                                    Modus = "zufall"        #Zufalls-Modus
        #elif self.SM.jaeger_modus.get()==1:                             Modus = "jaeger"        #Jäger-Modus
        elif self.SM.kaenguru_modus.get()==1:                            Modus = "kaenguru"      #Känguru-Modus
        #elif self.SM.reihe.get()==1 and  self.SM.gegner_modus.get()==1: Modus = "wechsel"      #Wechsel-Modus
        #elif self.SM.gegner_modus.get()==1:                             Modus = "gegner"       #Gegner-Modus
        #else:                                                           Modus = "treffer"      #Klappscheibe          
        if Modus is not None:
            if (not w_liste) or (not self.SM.get_state().is_action_state()):
                return  # Nichts tun, wenn keine Ziele definiert sind oder der Treffer nicht während der zulässigen Zeit war
            # 0. anzahlZiele auslesen
            anzahlZiele = 1 #Wenn kein sinvoller Wert bei scheibenServo angegeben ist, dann nur 1 Ziel.
            if self.SM.scheibenServo.get() > 0 and self.SM.scheibenServo.get() < 5: anzahlZiele = self.SM.scheibenServo.get()
            # 1. Den internen Status der Engine knallhart überschreiben #####################################WORKAROUND!!!!!!!!!!!!!!!!#####################
            # --- FIX: Matroschka-Schutz ---
            # Falls die Liste durch das YAML-Parsing verschachtelt ankommt (z.B. [[1, 2]])
            if isinstance(w_liste[0], (list, tuple)):
                self.ziel_wahl = list(w_liste[0])
            else:
                self.ziel_wahl = list(w_liste)
            # 2. SOLL-ZUSTAND BERECHNEN (Verhindert das Timer-Doppelblinken!)
            # Wir bereiten zwei Schablonen vor, wie die LEDs aussehen sollen.
            soll_led = [False] * 5
            soll_blink = [False] * 5
            
            # Hilfsfunktion, um Fehler durch den Wert "-1" (oder Out-of-Bounds) zu vermeiden
            def safe_set(listen_typ, idx):
                if 0 <= idx < 5:
                    listen_typ[idx] = True

            # Die Schablonen gemäß deinem Modus füllen
            if Modus == "gegner_zufall":
                if len(self.ziel_wahl) > 0: safe_set(soll_led, self.ziel_wahl[0])
                if len(self.ziel_wahl) > 1: safe_set(soll_led, self.ziel_wahl[1])     # P1, 2. Ziel
                if len(self.ziel_wahl) > 2: safe_set(soll_blink, self.ziel_wahl[2])
                if len(self.ziel_wahl) > 3: safe_set(soll_blink, self.ziel_wahl[3])   # P2, 2. Ziel

            elif Modus == "zufall": 
                for wert in self.ziel_wahl:
                    safe_set(soll_led, wert)

            elif Modus == "kaenguru":
                if len(self.ziel_wahl) > 0: safe_set(soll_led, self.ziel_wahl[0])         
                if self.SM.gegner_modus.get()==1 and len(self.ziel_wahl) > 1:
                    safe_set(soll_blink, self.ziel_wahl[1])   
            
            # 3. SMART UPDATE: Nur schalten, was abweicht!
            for i in range(5):
                # Blinken abgleichen
                if self.blinking[i] != soll_blink[i]:
                    self.SetBlinking(i, soll_blink[i])
                
                # Dauerleuchten abgleichen (aber nur, wenn die LED nicht blinken soll)
                if not soll_blink[i]:
                    if self.LED_status[i] != soll_led[i]:
                        self.SetLED(i, soll_led[i])
            #print(f"Ziel-Sequenz erfolgreich gesetzt: {w_liste}")    
            self.append_event_snapshot(f"Rec:{w_liste}")
         #   print(f"Laufzeit von set_ziel_wahl_replay { time.monotonic() - startzeit}")

    def SetLED(self, Nr: int, LEDswitch: bool): #Einzelne LED schalten
        if LEDswitch: self.LEDs[Nr].angle(90)
        else:         self.LEDs[Nr].angle(-40)
        self.LED_status[Nr] = LEDswitch
        
    def LEDsOff(self): #Alle LEDs aus
        for i in range(5): 
            self.SetBlinking(i,False) 
            self.SetLED(i,False)

    def SetBlinking(self, Nr: int, LEDswitch: bool): #Einzelne LED zum blinken bringen
        self.blinking[Nr] = LEDswitch
        if self.blinking[Nr]==True:
            self.blink_LED(Nr)
                
    def blink_LED(self, Nr: int): #Schleife fürs blinken
        if self.blinking[Nr]==True:
            if self.LED_status[Nr]:  self.SetLED(Nr, False)
            else:               self.SetLED(Nr, True)
            self.SDeluebs.root.after(self.blink_freq, lambda: self.blink_LED(Nr))

class PyGameTaster(threading.Thread):
    def __init__(self, KSobjekt):
        self.KSobjekt = KSobjekt
        self.on_button_event = None # --- NEU: Platzhalter für unseren GUI-Hook ---       
        self._running = True 
        threading.Thread.__init__(self)
        self.buttonsleep = 0.25
        start_time = time.monotonic()
        self.buttonlasttime = [start_time] * 5 #[start_time, start_time, start_time, start_time, start_time] 
        self.buttonlaststate = [False, False, False, False, False] 
        self.start()
        #print('Thread für Tastereingabe gestartet!')


    def callback(self):
        self.root.quit()

    def run(self):
        self.PyGameTasterLoop()  

    def stop(self):
        self._running = False  # 🆕 Methode zum Stoppen des Loops        

    def handle_button_press(self, button_id: int, button_status: bool):
        #timestamp = time.monotonic()                                                                                    ###################EVENTLOG###################
        #if button_status==1: self.KSobjekt.event_log.append(f"PRESSED - Button {button_id} Status: {button_status}")    ###################EVENTLOG###################
        #self.KSobjekt.event_log.append(f"{timestamp} - Button {button_id} Status: {button_status}")                     ###################EVENTLOG###################
        #print(timestamp)
        #if button_status:  print(f"button_id: {button_id}; button_status: {button_status}")

        # DEN ALTEN MOCK-HOOK HIER ENTFERNEN! MOCK!!!
        #if self.on_button_event and button_status == True:
        #    self.on_button_event(button_id)
        
        if button_status and self.buttonlaststate[button_id]==False and time.monotonic()-self.buttonlasttime[button_id]>self.buttonsleep: 
            # --- NEU: Der Mock-Hook ist jetzt hier "geschützt" ---
            if self.on_button_event:
                self.on_button_event(button_id)            
            #Hier Programmauswertung
            if   self.KSobjekt.SM.zufall.get()==1 and self.KSobjekt.SM.gegner_modus.get()==1: self.KSobjekt.set_treffer_gegner_zufall(button_id) #Gegnermodus mit Zufallsmodus       
            elif self.KSobjekt.SM.zufall.get()==1:                                            self.KSobjekt.set_treffer_zufall(button_id)        #Zufalls-Modus
            elif self.KSobjekt.SM.jaeger_modus.get()==1:                                      self.KSobjekt.set_treffer_jaeger(button_id)        #Jäger-Modus
            elif self.KSobjekt.SM.kaenguru_modus.get()==1:                                    self.KSobjekt.set_treffer_kaenguru(button_id)      #Känguru-Modus
            elif self.KSobjekt.SM.reihe.get()==1 and  self.KSobjekt.SM.gegner_modus.get()==1: self.KSobjekt.set_treffer_wechsel(button_id)       #Wechsel-Modus
            elif self.KSobjekt.SM.gegner_modus.get()==1:                                      self.KSobjekt.set_treffer_gegner(button_id)        #Gegner-Modus
            else:                                                                             self.KSobjekt.set_treffer(button_id)               #Klappscheibe          
            self.buttonlaststate[button_id]=True
            self.buttonlasttime[button_id]=time.monotonic()
            self.KSobjekt.append_event_snapshot("shoot", button_id) # HIER EVENTLOG ERSTELLEN
        elif button_status==0 and self.buttonlaststate[button_id]==True: 
            self.buttonlaststate[button_id]=False #Hier wird erkannt, dass der Knopf losgelassen wurde


    def PyGameTasterLoop(self):
        pygame.init()
        pygame.joystick.init() #initialise the joystick module
        clock = pygame.time.Clock() #create clock for setting game frame rate
        FPS = 300
        
        joysticks = [] #create empty list to store joysticks
        joystick_found = False
        
        last_check_time = time.monotonic()  # Initialisiere die Zeitvariable für die Joysticküberprüfung
        #run = True

        while self._running:  # 🆕 Kontrolliertes Beenden
            clock.tick(FPS)
            #timestamp = time.monotonic()                      ###################julLOG###################
            #self.KSobjekt.event_log.append(f"{timestamp}")    ###################EVENTLOG###################

            try:
                for joystick in joysticks:
                    for i in range (5):
                        self.handle_button_press(i,joystick.get_button(i))
                    if joystick.get_numbuttons() > 7:
                        self.handle_button_press(2, joystick.get_button(7)) #7 soll wie 2 funktionieren
            except pygame.error as e:
                self.KSobjekt.SDeluebs.programm_name.set(f"Fehler bei pygame.event: Events konnten nicht gelesen werden:\n{e}")
                timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.KSobjekt.event_log.append(f"[{timestamp}] [ERROR] Fehler bei pygame.event: {e}")
            
                #for i in range (12):        
                #    if joystick.get_button(i): 
                #        print('Button:',i)
                #        time.sleep(buttonsleep)

            #event handler
            try:
                for event in pygame.event.get():
                    if event.type == pygame.JOYDEVICEADDED:
                        print('Tastereingabe für Klappscheibe gefunden!')
                        joy = pygame.joystick.Joystick(event.device_index)
                        joysticks.append(joy)
                        if joystick_found:
                            self.KSobjekt.SDeluebs.programm_name.set("Klappscheibe wurde erneut verbunden. Wackelkontakt?")
                            timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            self.KSobjekt.event_log.append(f"[{timestamp}] [WARNUNG] Joystick wurde erneut verbunden – mögliche USB-Störung")
                        else: joystick_found = True
                    if event.type == pygame.JOYDEVICEREMOVED:
                        print("Tastereingabe für Klappscheibe wurde entfernt.")
                        self.KSobjekt.SDeluebs.programm_name.set("Klappscheibe wurde entfernt.")
                        timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        self.KSobjekt.event_log.append(f"[{timestamp}] [WARNUNG] Joystick wurde entfernt")
                        joysticks.clear()    
            except pygame.error as e:
                self.KSobjekt.SDeluebs.programm_name.set(f"Joystick konnte nicht initialisiert werden:\n{e}")    
                timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.KSobjekt.event_log.append(f"[{timestamp}] [ERROR] Joystick konnte nicht initialisiert werden: {e}")
            #if event.type == pygame.QUIT:
            #    run = False         

class Drehscheibe:
   
    def __init__(self, SDeluebs):
        self.SDeluebs = SDeluebs
        #SERVOU
        self.ShootServos = [Servo(f"P{i}") for i in range(5)]
        self.ServoZero() # Wird jetzt (seit v1_12_1) nichts mehr machen, weil bei "self.SM.saveScore.get()==0" ausgeschaltet.
        
    @property
    def SM(self):
        return self.SDeluebs.SMobjekt
 
    #HIER BEI -2 gar nicht mehr reagieren?!?
    def update_servos(self):
        if self.SM.saveScore.get()==0:
            if self.SM.get_state() in [GameState.SICHERHEIT, GameState.VORBEREITEN]:
                self.ServoZero()
            
            elif self.SM.get_state() in [GameState.LADEN, GameState.ACHTUNG, GameState.RESET]:
                #SERVOUO auf 90°
                for servo in self.ShootServos:
                    servo.angle(90) 
                    time.sleep(self.SM.servoDelay)
            
            elif self.SM.get_state()==GameState.FEUER:
                #SERVOUO auf Feuerstellung°
                servopos = 0 #Standardmässig auf 0° fahren        
                #Wenn Trick zufällig aktiviert wird, dann servopos = -90
                if self.SM.trick.get()==1:
                    Zufallszahl = random.randint(0,99)
                    if Zufallszahl<self.SM.trickWahrsch.get(): servopos = -90
                    else: servopos = 0
                #Hier der Zufall-Modus
                if self.SM.zufall.get()==1: 
                    anzahlZiele = 1 #Wenn kein sinvoller Wert bei scheibenServo angegeben ist, dann nur 1 Ziel.
                    if self.SM.scheibenServo.get() > 0 and self.SM.scheibenServo.get() < 5: anzahlZiele = self.SM.scheibenServo.get()
                    AktiveServos = random.sample(range(5), anzahlZiele) 
                    for AktiverServo in AktiveServos: 
                        self.ShootServos[AktiverServo].angle( servopos + self.SDeluebs.trimZero[AktiverServo] )
                        time.sleep(self.SM.servoDelay)
                #Gegnermodus für Drehscheibe
                elif self.SM.gegner_modus.get()==1:     
                    #print("NEUER MODUS")
                    ZielSpieler1 = random.choice([3, 4])
                    ZielSpieler2 = random.choice([0, 1])
                    MitteWahrsch = self.SM.survival_penalty
                    # Prüfen, ob die Mitte ausgelöst wird
                    if random.random() < MitteWahrsch:
                        if random.random() < 0.5: # Mitte für Spieler 1
                            ZielSpieler1 = 2
                        else: # Mitte für Spieler 2
                            ZielSpieler2 = 2
                    self.ShootServos[ZielSpieler1].angle( servopos + self.SDeluebs.trimZero[ZielSpieler1] )
                    time.sleep(self.SM.servoDelay)
                    self.ShootServos[ZielSpieler2].angle( servopos + self.SDeluebs.trimZero[ZielSpieler2] )
                else: #Hier der Normal-Modus 
                    if self.SM.scheibenServo.get()<0 and self.SM.reihe.get()==0: # Hier alle Servos
                        i=0
                        for servo in self.ShootServos:
                            servo.angle(servopos+self.SDeluebs.trimZero[i])
                            time.sleep(self.SM.servoDelay)
                            i=i+1 
                    else: # Hier nur 1 Servo
                        if self.SM.reihe.get()==1:
                            #Hier für Reihe-Modus nächsten Servo auswählen
                            if self.SM.scheibenServo.get()<0 or self.SM.scheibenServo.get()>3: #Servo 0 wenn scheibenServo ist negativ oder wenn 4 erreicht
                                self.SM.scheibenServo.set(0)                        
                            else: self.SM.scheibenServo.set(self.SM.scheibenServo.get()+1)     #Ansonsten scheibenservo zum nächsten wechseln
                        if self.SM.scheibenServo.get() >-1 and self.SM.scheibenServo.get()<5:
                            self.ShootServos[self.SM.scheibenServo.get()].angle(servopos+self.SDeluebs.trimZero[self.SM.scheibenServo.get()])
                        #print('angle',servopos+self.SDeluebs.trimZero[self.SM.scheibenServo.get()])
    
    #SERVOUO hier Servo auf 0° Position bringen inkl. Trim
    def ServoZero(self):
        i=0
        for servo in self.ShootServos:
            servo.angle(0+self.SM.trimZero[i])
            time.sleep(self.SM.servoDelay)
            i=i+1 
        
