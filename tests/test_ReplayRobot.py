import unittest
import tkinter as tk
import threading
import time
import yaml
import json

#Für Replay
import sys
import os
main_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, main_dir)

#import LoadModule
import Util_Testing as ut

#SD = LoadModule.import_latest_module('ShootingDeLuebs')
#HDeLuebs = LoadModule.import_latest_module('HardwareDeLuebs')
import ShootingDeLuebs as SD
import StateManagerDeLuebs as SMDeLuebs
import HardwareDeLuebs as HDeLuebs

class TestShootingDeLuebsGUI(unittest.TestCase):
    def load_scenario(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)["scenario"]

    def start_gui(self):
        self.root = tk.Tk()
        #self.root.withdraw() 
        self.app = SD.ShootingDeluebs(self.root)
        if hasattr(self.app.KSobjekt.LEDs[0], "on_angle_change"):
            schiesstand_anzeige = HDeLuebs.init_mock_hardware_gui(self.app.pytaster)

        # --- NEU: Echtzeit-Variablen initialisieren ---
        self.current_step_idx = 0
        self.start_time = time.monotonic()
        self.total_target_delay = 0.0 # Soll-Zeit in Sekunden
        
        # Den ersten Schritt in die Pipeline schieben
        self.root.after(0, self.execute_next_step)
        
        self.root.mainloop()


    def execute_next_step(self):
        if self.current_step_idx >= len(self.scenario):
            return  # Das Replay ist komplett beendet

        # 1. Aktuellen Schritt holen und ausführen
        step = self.scenario[self.current_step_idx]
        name = step.get("name", "Unnamed Step")
        
        # ---------------------------------------------------------
        # 1A: Auswertelogik ACTION (Befehle sicher ausführen)
        # ---------------------------------------------------------
        if "action" in step:
            action_name = step["action"]
            method = getattr(self, action_name, None)
            
            if method:
                if "wert" in step:
                    # HIER: Der Stern entpackt Listen in Einzelargumente!
                    # z.B. wert: ["ladenGelb", 3] -> method("ladenGelb", 3)
                    if isinstance(step["wert"], list):
                        method(*step["wert"])
                    else:
                        method(step["wert"])
                else:
                    method()
            else:
                print(f"⚠️ Aktion '{action_name}' nicht gefunden.")
                
        # ---------------------------------------------------------
        # 1B: Auswertelogik ACTUAL (Werte sicher auslesen ohne eval)
        # ---------------------------------------------------------
        elif "actual_attr" in step and ("expected" in step or "expected_exception" in step):
            attr_name = step["actual_attr"]
            expected = step.get("expected", None)
            expected_exception = step.get("expected_exception", None)
            
            # Wir packen das Auslesen in ein sicheres, winziges Lambda.
            # So kann check_result weiterhin Exceptions sauber abfangen.
            actual_func = lambda: self.get_sm_attr(attr_name)
            
            self.check_result(name, actual_func, expected, expected_exception)

        # 1C: Auswertelogik ACTUAL_METHOD (Eigene Test-Funktionen abrufen)
        elif "actual_method" in step and ("expected" in step or "expected_exception" in step):
            method_name = step["actual_method"]
            method = getattr(self, method_name, None)
            expected = step.get("expected", None)
            expected_exception = step.get("expected_exception", None)
            
            if method:
                # Wir bauen ein sicheres Lambda, das die Argumente übergibt
                if "wert" in step:
                    if isinstance(step["wert"], list):
                        actual_func = lambda: method(*step["wert"])
                    else:
                        actual_func = lambda: method(step["wert"])
                else:
                    actual_func = lambda: method()
                
                self.check_result(name, actual_func, expected, expected_exception)
            else:
                print(f"⚠️ Test-Methode '{method_name}' nicht gefunden.")

        # ---------------------------------------------------------
        # --- DER TÜRSTEHER (Muss GANZ ans Ende der Prüfungen!) ---
        # ---------------------------------------------------------
        elif "actual" in step:
            # Ein harter Abbruch, wenn noch alter eval-Code in der YAML steht
            raise ValueError(f"❌ VERALTETES FORMAT in '{name}': Der Befehl 'actual' wird nicht mehr unterstützt. Bitte auf 'actual_attr' oder 'actual_method' umstellen!")
        
        elif not any(key in step for key in ["action", "actual_attr", "actual_method"]): 
            # Ein harter Abbruch, wenn man sich in der YAML vertippt hat (z.B. 'aktion' statt 'action')
            raise ValueError(f"❌ UNBEKANNTER SCHRITT in '{name}': Es fehlt 'action', 'actual_attr' oder 'actual_method'. (Gefundene Schlüssel: {list(step.keys())})")


        # ---------------------------------------------------------
        # 2. Den NÄCHSTEN Schritt vorbereiten und korrigiert planen
        # ---------------------------------------------------------
        self.current_step_idx += 1
        
        if self.current_step_idx < len(self.scenario):
            next_step = self.scenario[self.current_step_idx]
            step_time_ms = next_step.get("step_time", 1000)
            
            # Die absolute Soll-Zeit aufaddieren (in Sekunden!)
            self.total_target_delay += (step_time_ms / 1000.0)
            target_time = self.start_time + self.total_target_delay
            
            # Wie viel Uhr ist es wirklich?
            now = time.monotonic()
            
            # WICHTIG: Die korrigierte Wartezeit berechnen. 
            # Wenn wir 70ms im Verzug sind, wird wait_time_ms hier automatisch 70ms kürzer!
            wait_time_ms = int(max(0, target_time - now) * 1000)
            
            self.root.after(wait_time_ms, self.execute_next_step)




    def start_countdown(self):
        print("⏳ Countdown wird gestartet...")
        self.app.SMobjekt.buttonCountdownClick()

    def reset_button_click(self):
        print("🔄 Reset-Knopf wird gedrückt...")
        self.app.SMobjekt.buttonResetClick()

    def get_sm_attr(self, attr_name):
        """Liest Attribute sicher aus (inkl. Tkinter und Enums/Methoden)."""
        current_attr = getattr(self.app.SMobjekt, attr_name, None)
        
        # 1. Ist es eine Methode? (z.B. 'get_state')
        if callable(current_attr):
            result = current_attr()
            # Wenn das Ergebnis ein Enum ist (hat ein '.name' Attribut), gib den Text zurück
            if hasattr(result, 'name'):
                return result.name
            return result
            
        # 2. Ist es eine Tkinter-Variable?
        if hasattr(current_attr, 'get'):
            return current_attr.get()
            
        # 3. Ansonsten normale Python-Variable
        return current_attr


    def set_sm_attr(self, attr_name, value):
        #attr_name, value = args
        # 1. Wir holen uns das existierende Objekt (z.B. die IntVar)
        target = getattr(self.app.SMobjekt, attr_name)
    
        # 2. PRÜFUNG: Ist das Ziel ein Tkinter-Objekt?
        if hasattr(target, 'set'):
            # JA: Wir nutzen die .set() Methode des Behälters.
            # Der Behälter bleibt bestehen, nur der Inhalt ändert sich.
            self.app.SMobjekt.system_update_laeuft = True
            target.set(value)
            print(f"🔧 Tkinter-Variable '{attr_name}' wurde auf {value} aktualisiert.")
            self.app.SMobjekt.system_update_laeuft = False
        else:
            # NEIN: Es ist eine normale Variable (z.B. ein String oder Bool).
            # Hier können wir den Wert einfach direkt überschreiben.
            setattr(self.app.SMobjekt, attr_name, value)
            print(f"🔧 Normales Attribut '{attr_name}' wurde auf {value} gesetzt.")


    def call_sm_method(self, method_name, *params):
        """Führt eine SM-Methode aus, loggt den Erfolg und gibt den Wert zurück."""
        
        # 1. Methode suchen (Ohne 'None' als Puffer! Wenn sie fehlt, knallt es hier
        # absichtlich mit einem AttributeError - perfekt für Negativ-Tests!)
        method = getattr(self.app.SMobjekt, method_name)

        # 2. Methode ausführen (Gibt das Ergebnis für actual_method zurück)
        result = method(*params)
        
        # 3. Wenn wir bis hierhin kommen, gab es keinen Absturz
        print(f"🚀 Methode '{method_name}' erfolgreich aufgerufen (Parameter: {params}).")
        
        return result

    def remove_modifiziert_tag(self):
        """Entfernt das Modifiziert-Tag sicher aus dem StateManager."""
        try:
            self.app.SMobjekt.remove_tag(self.app.SMobjekt.Tag.MODIFIZIERT)
            print("🔧 Tag 'MODIFIZIERT' erfolgreich entfernt.")
        except Exception as e:
            print(f"⚠️ Konnte Tag nicht entfernen: {e}")
        
    def shoot(self, key: int):
        print(f"🎯 Feuer auf die {key}...")
        self.app.pytaster.handle_button_press(key, True)
        self.root.after(100, lambda: self.app.pytaster.handle_button_press(key, False))

    def close_gui(self):
        print("🛑 GUI wird geschlossen...")
        try:
            if hasattr(self.app, 'pytaster') and hasattr(self.app.pytaster, 'stop'):
                print("🎮 Joystick-Thread wird gestoppt...")
                self.app.pytaster.stop()
        except Exception as e:
            print(f"⚠️ Fehler beim Stoppen des Joystick-Threads: {e}")
        self.root.quit()
        self.root.destroy()

    def get_player_punkte(self, player_idx):
        """Holt sicher die Punkte aus dem KSobjekt"""
        return self.app.KSobjekt.players[player_idx].punkte_durchgang

    def get_player_speedpunkte(self, player_idx):
        """Holt sicher die Speedpunkte aus dem KSobjekt"""
        return self.app.KSobjekt.players[player_idx].speedpunkte_durchgang

    def verify_player_json(self, filepath):
        """Lagert den komplexen JSON-Vergleich sauber aus"""
        players_dict = {
            'player0': self.app.KSobjekt.players[0].to_dict(), 
            'player1': self.app.KSobjekt.players[1].to_dict()
        }
        diff = ut.compare_dicts_with_json(players_dict, filepath)
        
        # Da es eine "Action" ist, machen wir die Assert-Prüfung direkt hier
        if diff == {}:
            print("✅ JSON Vergleich der Spieler erfolgreich!")
        else:
            print(f"❌ JSON Vergleich fehlgeschlagen. Unterschiede: {diff}")
            self.assertEqual(diff, {})

    def save_sd_attributes(self, filepath, *attribute_names):
        """Exportiert beliebige Attribute flexibel aus der Main-App in ein JSON."""
        # Das Sternchen packt alle restlichen YAML-Werte in ein Tuple (attribute_names)
        attributes = ut.export_attributes(self.app, list(attribute_names))
        ut.save_to_json(filepath, attributes)
        print(f"💾 Attribute {list(attribute_names)} erfolgreich unter '{filepath}' gespeichert.")

    def compare_sm_tkvars_with_json(self, filepath):
        """Vergleicht die aktuellen Tkinter-Variablen mit einem JSON-Backup."""
        return ut.compare_with_json(self.app.SMobjekt, filepath)

    def check_result(self, name, actual_or_func, expected=None, expected_exception=None):
        try:
            actual = actual_or_func() if callable(actual_or_func) else actual_or_func
            if expected_exception:
                passed = False  # Es hätte eine Exception kommen sollen
            else:
                EPSILON = 1e-2
                if isinstance(actual, float) and isinstance(expected, float): 
                    passed = abs(actual - expected) < EPSILON
                else:
                    passed = actual == expected
        except Exception as e:
            #Hier überprüfen, ob die Fehlermeldung auch der Erwartung entspricht:
            if expected_exception and type(e).__name__ == expected_exception:
                actual = f"{type(e).__name__}" #OK
                passed = True
            else:
                actual = f"{type(e).__name__}: {e}"
                passed = False
        symbol = "✅" if passed else "❌"
        print(f"🔍 Test: {name} | Ergebnis: {actual} | Erwartet: {expected or expected_exception} | {symbol} Erfolgreich: {passed}")
        self.test_results[name] = {
            "actual": actual,
            "expected": expected or expected_exception,
            "passed": passed
        }

    def run_scenario_test(self, yaml_file, timeout=None):
        print(f"🔍 Starte Testszenario: {yaml_file}")
        self.test_results = {}
        self.yaml_file = yaml_file
        self.scenario = self.load_scenario(self.yaml_file)
        self.gui_thread = threading.Thread(target=self.start_gui)
        self.gui_thread.start()
        self.gui_thread.join(timeout)
        for name, result in self.test_results.items():
            with self.subTest(name=name):
                self.assertTrue(result["passed"], msg=f"{name}: {result['actual']} != {result['expected']}")

#    def test_REPLAY_MATCH000070(self):
#        self.run_scenario_test("./tests/REPLAY_MATCH000070.yaml")

    def test_scenario(self):
        self.run_scenario_test("./tests/test_scenario.yaml")
        
    def test_scenario2(self):
        self.run_scenario_test("./tests/test_scenario2.yaml", timeout=10)
        

if __name__ == '__main__':
    import sys
    
    # Prüfen, ob eine Datei als Argument übergeben wurde
    if len(sys.argv) > 1:
        yaml_path = sys.argv[1]
        print(f"🚀 Starte dynamisches Replay für: {yaml_path}")
        
        # Wir bauen on-the-fly eine Test-Klasse für diese eine Datei
        class DynamicTest(TestShootingDeLuebsGUI):
            def test_dynamic_replay(self):
                self.run_scenario_test(yaml_path)
                
        # Führt nur diesen einen Test aus
        suite = unittest.TestSuite()
        suite.addTest(DynamicTest('test_dynamic_replay'))
        runner = unittest.TextTestRunner()
        runner.run(suite)
        
    else:
        # Standard-Verhalten (führt alle fest verdrahteten def test_... aus)
        unittest.main()