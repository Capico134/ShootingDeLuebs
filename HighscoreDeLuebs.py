import json #Highscore
import time # neu für die aktuelle Zeit für die Highscore
import datetime as dt #Highscore
import tkinter as tk
from tkinter import ttk #Highscore
from tkinter import messagebox
import re
import zipfile
import io #für zipfile
import os #für Eventlog
from PIL import Image, ImageTk  # Pillow muss installiert sein: `pip install pillow`
from StateManagerDeLuebs import GameState

class HighscoreDeluebs:
    def __init__(self, SDeluebs):
        self.SDeluebs = SDeluebs
        self.highscore_manager = HighscoreManager()
        self.load_scores()
        self.anzahl_eintraege = tk.IntVar(value=0)
        
        # --- ELA-Tipp 3: Zentrale Spaltendefinition (Single Source of Truth) ---
        self.columns = ("ID", "Spieler", "Modus", "Punkte Durchgang", "Gesamtpunkte", "Zeitstempel")
    
    def customize_style(self):
        style = ttk.Style()
        style.configure("Treeview", font=("Arial", 23), rowheight=40)
        style.configure("Treeview.Heading", font=("Arial", 30, "bold"))
        style.configure("TButton", font=("Arial", 22))
        style.configure("TCombobox", padding=(10, 5, 60, 5))
        style.configure("Treeview", background='lavenderblush')

    def show_highscore_window(self):
        self.highscore_window = tk.Toplevel(self.SDeluebs.root)
        self.highscore_window.title("Highscores")
        self.highscore_window.geometry('1800x900')
        self.highscore_window['background'] = 'plum'
        self.highscore_window.option_add("*TCombobox*Listbox.font", ("Arial", 25))
        self.customize_style()

        top_frame = tk.Frame(self.highscore_window, bg='plum')
        top_frame.pack(fill="x", padx=10, pady=10)
    
        # Logo aus ZIP laden
        with zipfile.ZipFile("data.pak", "r") as pak:  
            image = Image.open(io.BytesIO(pak.read("Highscore_v01.png")))  
        photo = ImageTk.PhotoImage(image)
        label = tk.Label(top_frame, image=photo, highlightthickness=0, borderwidth=0)
        label.pack(side="left", padx=15)
        label.image = photo  
        
        modes = sorted(set(entry["programm_name"] for entry in self.highscore_manager.data))
    
        # Dropdown
        self.selected_mode = tk.StringVar(value="Alle Modi")
        self.mode_dropdown = ttk.Combobox(top_frame, textvariable=self.selected_mode, values=["Alle Modi"] + list(modes), width=30, state="readonly")
        self.mode_dropdown.pack(side="left", padx=(150, 0))
        self.mode_dropdown.configure(font=('Arial', 30))
        self.mode_dropdown.bind("<Button-1>", lambda event: self.mode_dropdown.focus_set())

        # Schließen Button
        close_button = tk.Button(top_frame, text="Schließen", command=self.highscore_window.destroy, font=('Arial', 25))
        close_button.pack(pady=10, side="right", padx=(0, 35))

        # --- NEU: Refresh Button ---
        refresh_button = tk.Button(top_frame, text="↻", command=self.refresh_table, font=('Arial', 25), bg='lightblue')
        refresh_button.pack(pady=10, side="right", padx=(15, 0))
    
        # Anzahl-Anzeige
        block = tk.Frame(top_frame)
        block.pack(side="right", padx=(5, 65))
        label_text_eintraege = tk.Label(block, text=" Anzahl Einträge ", font=('Arial', 17), bg="thistle")
        label_text_eintraege.pack(side=tk.TOP)
        label_anzahl_eintraege = tk.Label(block, textvariable=self.anzahl_eintraege, font=('Arial', 17))
        label_anzahl_eintraege.pack(side=tk.BOTTOM, padx=(5, 5))
    
        # Frame für Tabelle
        frame = tk.Frame(self.highscore_window, bg='plum')
        frame.pack(pady=10, fill="both", expand=True)
        
        scrollbar = tk.Scrollbar(frame, width=47)
        scrollbar.pack(side="right", fill="y")
        
        # --- ELA-Tipp 1: Tree wird offizielles Klassenattribut! ---
        self.tree = ttk.Treeview(
            frame,
            columns=self.columns,
            show="headings",
            yscrollcommand=scrollbar.set,
            selectmode="extended",
        )
        
        # Spalten-Headings und Sortierung dynamisch setzen
        for col in self.columns:
            self.tree.heading(col, text=col, command=lambda _col=col: self.sort_column(_col, True))
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.tree.yview)
        
        self.tree.column("ID", width=60, anchor="center", stretch=False)
        self.tree.column("Spieler", width=260)
        self.tree.column("Modus", width=400, stretch=True)
        self.tree.column("Punkte Durchgang", width=30, stretch=True)

        # --- AB HIER DIE FILTER-GUI BAUEN ---
        filter_frame = tk.Frame(self.highscore_window, bg='plum')
        filter_frame.pack(fill="x")
        
        # Filter-Eingabefelder generieren
        self.filters = {}
        filter_keys = ("match_id", "spieler", "programm_name", "punkte_durchgang", "gesamtpunkte", "timestamp")
        for col in filter_keys:
            feld_breite = 3 if col == "match_id" else 16 
            entry = tk.Entry(filter_frame, font=('Arial', 25), width=feld_breite)
            entry.pack(side="left", padx=5)
            self.filters[col] = entry
            entry.bind("<Return>", lambda event: self.apply_filters())

        filter_button = tk.Button(filter_frame, text="Filter anwenden", command=self.apply_filters, font=('Arial', 20))
        filter_button.pack(side="right", padx=(0, 5))

        # Event-Bindings für Maus & Tasten
        press_timer = None     
        self.tree.bind("<ButtonPress-1>", lambda e: self._on_press(e))
        self.tree.bind("<ButtonRelease-1>", lambda e: self._on_release(e))        
        self.tree.bind("<Button-3>", lambda e: self.show_context_menu(e))
        self.tree.bind("<Delete>", lambda event: self.delete_selected_entries())
        self.tree.bind("<i>", lambda event: self.show_selected_entries())
        
        # Dropdown-Menü-Aktion binden
        self.mode_dropdown.bind("<<ComboboxSelected>>", lambda event: self.update_highscores())
   
        # Initialer Start
        self.update_highscores()

    # --- Timer-Hilfsfunktionen für das Kontextmenü ---
    def _on_press(self, event):
        self._press_timer = self.tree.after(750, self.show_context_menu, event)
    
    def _on_release(self, event):
        if hasattr(self, '_press_timer') and self._press_timer:
            self.tree.after_cancel(self._press_timer)

    def sort_column(self, col, reverse):
        def convert_value(value):
            try:
                if col == "Zeitstempel":
                    return dt.datetime.strptime(value, "%d.%m.%y %H:%M:%S")
                if value == "-":
                    return -1  
                return float(value) if "." in value else int(value) 
            except ValueError:
                return value            
        # Daten abrufen und konvertieren
        data = [(convert_value(self.tree.set(k, col)), k) for k in self.tree.get_children('')]
        data.sort(reverse=reverse, key=lambda t: t[0])
        # Einträge bewegen
        for index, (val, k) in enumerate(data):
            self.tree.move(k, '', index)
        # Spaltenüberschrift mit Sortierung aktualisieren
        self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))                

    # Funktion zum Aktualisieren der Highscore-Anzeige  
    def update_highscores(self):
        selected = self.mode_dropdown.get()
        filtered_data = self.highscore_manager.filter_highscores(
            mode_name=None if selected == "Alle Modi" else selected, sort_by="gesamtpunkte"
        )# Hier wird es nur nach den Gesamtpunkten von Player 1 sortiert.
        self.update_treeview(filtered_data)        
        self.sort_column("Zeitstempel", True) # AL AL AL Jetzt wird richtig sortiert   

    def update_treeview(self, data):
        self.anzahl_eintraege.set(len(data))
        # Treeview leeren
        for row in self.tree.get_children():
            self.tree.delete(row)
        # Tags definieren mit Farben
        self.tree.tag_configure("even", background="thistle")
        self.tree.tag_configure("odd", background="lavenderblush")
        tag = "even"
        # Einträge hinzufügen
        for hs in data:
            tag = "odd" if tag == "even" else "even"
            
            spieler_name = hs.get("spieler", "Unbekannt")
            punkte_durchgang = hs.get("punkte_durchgang", 0)
            gesamtpunkte = hs.get("gesamtpunkte", 0)
            match_id = hs.get("match_id", "-")
            
            if hs.get("survival_modus", 0) == 1 and hs.get("gegner_modus", 0) == 1:
                spieler_name += f"; {hs['spieler2']}; {hs.get('zyklus','N/A')} Rnd" 
                punkte_durchgang = hs.get("punkte_durchgang", 0) + hs.get("punkte_durchgang_pl2", 0)
                gesamtpunkte = round(hs.get("gesamtpunkte", 0) + hs.get("gesamtpunkte_pl2", 0), 3)     
            
            self.tree.insert(
                "", "end",
                values=(match_id, spieler_name, hs.get("programm_name", "Unbekannt"), punkte_durchgang, gesamtpunkte, hs.get("timestamp", "Unbekannt")),
                tags=(tag,)
            )
            
            if hs.get("survival_modus", 0) == 0 and hs.get("gegner_modus", 0) == 1:
                self.tree.insert(
                    "", "end",
                    values=(match_id, hs.get("spieler2", "Unbekannt"), hs.get("programm_name", "Unbekannt"), hs.get("punkte_durchgang_pl2", 0), hs.get("gesamtpunkte_pl2", 0), hs.get("timestamp", "Unbekannt")),
                    tags=(tag,)
                )

    def apply_filters(self):
        self.update_treeview(self.highscore_manager.data)
        self.update_highscores()
    
        filtered_items = []
        for row_id in self.tree.get_children():
            values = self.tree.item(row_id, "values")
            match = True
    
            for col, entry in self.filters.items():
                val = entry.get()
                if val:
                    try:
                        cell_value = values[list(self.filters.keys()).index(col)]
    
                        if col in ["punkte_durchgang", "gesamtpunkte"]:
                            cell_value = float(cell_value)
                            if ">=" in val:
                                if cell_value < float(val.split(">=")[1].strip()): match = False
                            elif "<=" in val:
                                if cell_value > float(val.split("<=")[1].strip()): match = False
                            elif ">" in val:
                                if cell_value <= float(val.split(">")[1].strip()): match = False
                            elif "<" in val:
                                if cell_value >= float(val.split("<")[1].strip()): match = False
                            elif val.replace(".", "", 1).isdigit():
                                if cell_value != float(val.strip()): match = False
    
                        elif col == "timestamp":
                            if "-" in val:
                                start, end = map(str.strip, val.split("-"))
                                start_date = dt.datetime.strptime(start, "%d.%m.%y")
                                end_date = dt.datetime.strptime(end, "%d.%m.%y") + dt.timedelta(days=1)
                                cell_date = dt.datetime.strptime(cell_value, "%d.%m.%y %H:%M:%S")
                                if not (start_date <= cell_date <= end_date): match = False
    
                        elif col in ["match_id", "spieler", "programm_name"]:
                            pattern = re.compile(val, re.IGNORECASE)
                            if not pattern.search(str(cell_value)): match = False
    
                    except (ValueError, IndexError):
                        match = False
    
            if match:
                filtered_items.append(row_id)
    
        for row_id in self.tree.get_children():
            if row_id not in filtered_items:
                self.tree.delete(row_id)
        
        self.sort_column("Zeitstempel", True)

    def show_context_menu(self, event):
        context_menu = tk.Menu(self.highscore_window, tearoff=0)
        context_menu.add_command(label="Informationen", command=self.show_selected_entries, font=('Arial', 35))            
        context_menu.add_command(label="Highscore Log", command=self.show_selected_highscore_logs, font=('Arial', 35))
        context_menu.add_command(label="Export Video Config", command=self.export_video_config, font=('Arial', 35))
        context_menu.add_command(label="Video generieren", command=self.generate_video, font=('Arial', 35))
        context_menu.add_command(label="Export Replay", command=self.export_match_to_yaml, font=('Arial', 35))
        context_menu.add_command(label="Replay abspielen", command=self.play_replay, font=('Arial', 35))
        context_menu.add_command(label="Löschen", command=self.delete_selected_entries, font=('Arial', 35))
        context_menu.post(event.x_root, event.y_root)

    def delete_selected_entries(self):
        selected_items = self.tree.selection()
        for item in selected_items:
            values = self.tree.item(item, "values")
            for entry in self.highscore_manager.data:
                if entry["timestamp"] == values[5]:
                    entry_data = f"Programm: {entry.get('programm_name','unbekannt')}\n{entry.get('timestamp','unbekannt')}\n\n" \
                                 f"Spieler: {entry.get('spieler','unbekannt')}\nPunkte: {entry.get('punkte_durchgang','0')}\nGesamtpunkte: {entry.get('gesamtpunkte','0')}\n" 
                    if entry["gegner_modus"] == 1:
                        entry_data += f"\nSpieler 2: {entry.get('spieler2','unbekannt')}\nPunkte: {entry.get('punkte_durchgang_pl2','0')}\nGesamtpunkte: {entry.get('gesamtpunkte_pl2','0')}\n"  
                    
                    self.highscore_window.withdraw()
                    antwort = messagebox.askyesno("Bestätigung", f"Eintrag wirklich löschen?\n\n{entry_data}")
                    self.highscore_window.deiconify()
                    self.highscore_window.lift()
                    if not antwort: break
                    self.highscore_manager.data.remove(entry)
                    break
        self.update_treeview(self.highscore_manager.data)
        self.apply_filters()
        
        with open(self.highscore_manager.file_path, "w") as file:
            json.dump(self.highscore_manager.data, file, indent=4)

    def show_selected_entries(self): 
        exclude_keys = {"highscore_log"}
        selected_items = self.tree.selection() 
        for item in selected_items: 
            values = self.tree.item(item, "values") 
            for entry in self.highscore_manager.data:
                if entry["timestamp"] == values[5]:
                    text = "\n".join([f"{key}: {value}" for key, value in entry.items() if key not in exclude_keys])
                    messagebox.showinfo("Highscore-Details", text)

    def show_selected_highscore_logs(self):
        def clean_l(lst):
            if not lst: return ""
            return ", ".join([str(x) for x in lst if x != -1])       

        def hole_score_strings(ev_dict):
            b1, b2 = ev_dict.get('p1_pd', 0), ev_dict.get('p2_pd', 0)
            t1, t2 = b1 + ev_dict.get('p1_spd', 0.0), b2 + ev_dict.get('p2_spd', 0.0)
            return f"{b1} Pkte ({t1:.3f})", f"{b2} Pkte ({t2:.3f})"

        # mini_h und sep WURDEN HIER ENTFERNT UND IN DIE SCHLEIFE VERSCHOBEN!
        
        selected_items = self.tree.selection()
        for item in selected_items:
            values = self.tree.item(item, "values")
            for entry in self.highscore_manager.data:
                if entry["timestamp"] == values[5]:
                    
                    # --- ELA-UPGRADE: Dynamischer Tabellenkopf mit Spielernamen ---
                    # Namen auslesen und auf max. 18 Zeichen begrenzen, damit die Tabelle nicht platzt
                    sp1_name = entry.get('spieler', 'Spieler 1')[:18]
                    
                    # Bei Singleplayer bleibt die rechte Spalte im Header komplett leer
                    if entry.get("gegner_modus", 0) != 0:
                        sp2_name = entry.get('spieler2', 'Spieler 2')[:18]
                    else:
                        sp2_name = ""
                        
                    mini_h = f"{'Zeit':>8} | {'Ref':^7} | {'Zyk':^4} | {'Aktion':<8} | {'Ziel':^4} | {'Zielwahl':^18} | {sp1_name:^18} | {sp2_name:^18}\n"
                    sep = "-" * (len(mini_h) - 1)
                    last_action_was_state = False
                    # --------------------------------------------------------------

                    log_window = tk.Toplevel()
                    log_window.title(f"Detail-Log: {entry.get('programm_name', 'Unbekannt')}")
                    
                    info_lines = [
                        f"PROGRAMM: {entry.get('programm_name', '')}",
                        f"SPIELER 1: {entry.get('spieler', '')} | Punkte: {entry.get('punkte_durchgang', 0)}",
                    ]
                    if entry.get("gegner_modus", 0) != 0:
                        info_lines.append(f"SPIELER 2: {entry.get('spieler2', 'N/A')} | Punkte: {entry.get('punkte_durchgang_pl2', 0)}")
                    info_lines.append(f"ZEITSTEMPEL: {entry.get('timestamp', '')}")
                    info_lines.append("-" * 75)
                    info_lines.append("KLASSISCHES LOG:")
                    info_lines.append(entry.get('highscore_log', '– Kein Log vorhanden –'))
                    info_lines.append("-" * 75)
                    
                    match_id = entry.get("match_id")
                    event_details = ""
                    
                    if match_id:
                        log_path = os.path.join("savegames", "logs", f"MATCH{match_id:06d}.json")
                        if os.path.exists(log_path):
                            try:
                                with open(log_path, "r", encoding="utf-8") as f:
                                    geladene_daten = json.load(f)
                                    timeline = geladene_daten.get("timeline", []) if isinstance(geladene_daten, dict) else geladene_daten
                                
                                event_details = f"DETAILLIERTES EVENT-LOG: MATCH{match_id:06d}\n\n{mini_h}{sep}\n"
                                valid_action_states = [state.name for state in GameState.action_states()]
                                
                                for ev in timeline:
                                    action = ev.get('a', '')
                                    m = ev.get('m', '')
                                    t = f"{ev.get('t', 0):>7.2f}s"
                                    tref = f"{ev.get('tref', 0):>6.2f}s"
                                    zyk = ev.get('z', 0)
                                
                                    # Diese Events verstecken wir im Text-Log # ACHTUNG EIGENTLICH AKTUELL ÜBERFLÜSSIG
                                    if action == "Treffer Wechsel": 
                                        continue
                                    # ---------------------------------------------

                                    if action == "state_change":
                                        if m == "FEUER":
                                            if zyk > 1:
                                                s1_str, s2_str = hole_score_strings(ev)
                                                event_details += f"{' ':>8} | {' ':>7} | {zyk-1:^4} | {'SCORE':<8} | {' ':^4} | {'ZWISCHENSTAND':^18} | {s1_str:^18} | {s2_str:^18}\n"
                                                event_details += "\n" + mini_h + sep + "\n"
                                            elif zyk == 1:
                                                event_details += "\n" + mini_h + sep + "\n"
                                        
                                        line = f"{t} | {tref} | {zyk:^4} | {m[:8]:<8} | {' ':^4} | {'(Statuswechsel)':^18} | {' ':^18} | {' ':^18}\n"
                                        event_details += line
                                        last_action_was_state = True
                                
                                    elif action == "shoot":
                                        v = ev.get('v', '-')
                                        w = clean_l(ev.get('w', []))
                                        p1 = clean_l(ev.get('p1_t', [])) if m in valid_action_states else ""
                                        p2 = clean_l(ev.get('p2_t', [])) if m in valid_action_states else ""
                                        line = f"{t} | {tref} | {zyk:^4} | {'SHOT':<8} | {v:^4} | {w:^18} | {p1:^18} | {p2:^18}\n"
                                        event_details += line
                                        last_action_was_state = False

                                    elif action.startswith("Rec:"):
                                        w = clean_l(ev.get('w', []))
                                        line = f"{t} | {tref} | {zyk:^4} | {' ↳ sync':<8} | {' ':^4} | {w:^18} | {' ':^18} | {' ':^18}\n"
                                        event_details += line
                                        last_action_was_state = False

                                    elif "Bonus" in action:
                                        w = clean_l(ev.get('w', []))
                                        p1_text = "[ BONUS ERHALTEN ]" if "1" in action else ""
                                        p2_text = "[ BONUS ERHALTEN ]" if "2" in action else ""
                                        line = f"{t} | {tref} | {zyk:^4} | {'BONUS':<8} | {' ':^4} | {w:^18} | {p1_text:^18} | {p2_text:^18}\n"
                                        event_details += line
                                        last_action_was_state = False

                                    elif action == "anulliere_zyklus":
                                        p_idx = ev.get('p', -1)
                                        p1_text = "[ ANNULLIERT ]" if p_idx == 0 else ""
                                        p2_text = "[ ANNULLIERT ]" if p_idx == 1 else ""
                                        line = f"{t} | {tref} | {zyk:^4} | {'VAR':<8} | {' ':^4} | {'Manuelle Korrektur':^18} | {p1_text:^18} | {p2_text:^18}\n"
                                        event_details += line
                                        last_action_was_state = False

                                    elif action == "survival_update":
                                        # Neue Feuerzeit aus 'v' holen (Fallback auf 'p' für ganz alte Logs)
                                        feuer_neu = ev.get('v', ev.get('p', '-'))
                                        
                                        # Verwendete Zeit aus 'p' holen
                                        used_time = ev.get('p', None)
                                        
                                        # Text formatieren
                                        if used_time is not None and str(used_time) != str(feuer_neu):
                                            # Reines ASCII '->' verwenden, da Tkinter '➔' breiter darstellt!
                                            detail_text = f"{used_time}s -> {feuer_neu}s"
                                        else:
                                            detail_text = f"Feuerzeit: {feuer_neu}s"
                                            
                                        # Auf 18 Zeichen begrenzen, damit die Spalte nicht platzt
                                        detail_text = detail_text[:18]
                                        
                                        line = f"{t} | {tref} | {zyk:^4} | {'SURVIVE':<8} | {' ':^4} | {detail_text:^18} | {' ':^18} | {' ':^18}\n"
                                        event_details += line
                                        last_action_was_state = False
                                        
                                    else:
                                        aktions_name = str(action)[:18] if action else "UNKNOWN"
                                        line = f"{t} | {tref} | {zyk:^4} | {' ':<8} | {' ':^4} | {aktions_name:^18} | {' ':^18} | {' ':^18}\n"
                                        event_details += line
                                        last_action_was_state = False 

                                if timeline:
                                    s1_str, s2_str = hole_score_strings(timeline[-1])
                                    event_details += f"{sep}\n{' ':>8} | {' ':>7} | {timeline[-1].get('z', 0):^4} | {'SCORE':<8} | {' ':^4} | {'ENDSTAND':^18} | {s1_str:^18} | {s2_str:^18}\n"
                                    
                            except Exception as e:
                                event_details = f"\n[Fehler beim Laden des Event-Logs: {e}]"
                        else:
                            event_details = "\n[Keine detaillierte Event-Datei gefunden]"
                    
                    full_text = "\n".join(info_lines) + "\n\n" + event_details
                    text_widget = tk.Text(log_window, wrap="none", width=120, height=35, font=("Courier", 20))
                    text_widget.insert("1.0", full_text)
                    text_widget.configure(state="disabled")
                    
                    x_scroll = tk.Scrollbar(log_window, orient="horizontal", command=text_widget.xview)
                    y_scroll = tk.Scrollbar(log_window, orient="vertical", command=text_widget.yview)
                    text_widget.configure(xscrollcommand=x_scroll.set, yscrollcommand=y_scroll.set)
                    
                    text_widget.grid(row=0, column=0, sticky="nsew")
                    y_scroll.grid(row=0, column=1, sticky="ns")
                    x_scroll.grid(row=1, column=0, sticky="ew")
                    log_window.grid_rowconfigure(0, weight=1)
                    log_window.grid_columnconfigure(0, weight=1)

    def export_match_to_yaml(self):
        selected_items = self.tree.selection()
        if not selected_items:
            return

        # =================================================================
        # --- 0. GUI ABFRAGE FÜR EXPORT-OPTIONEN ---
        # =================================================================
        top = self.tree.winfo_toplevel()
        dialog = tk.Toplevel(top)
        dialog.title("YAML Export-Optionen")
        dialog.geometry("350x200")
        dialog.transient(top)
        dialog.grab_set()

        # Variablen für die Checkboxen
        var_p1 = tk.BooleanVar(value=True)
        var_p2 = tk.BooleanVar(value=True)
        var_comp = tk.BooleanVar(value=True)

        # UI Layout
        tk.Label(dialog, text="Wer soll im Replay schießen?", font=("Arial", 10, "bold")).pack(pady=(10, 5))
        tk.Checkbutton(dialog, text="Spieler 1 (p=0) exportieren", variable=var_p1).pack(anchor="w", padx=40)
        tk.Checkbutton(dialog, text="Spieler 2 (p=1) exportieren", variable=var_p2).pack(anchor="w", padx=40)

        tk.Label(dialog, text="Zeiteinstellungen:", font=("Arial", 10, "bold")).pack(pady=(15, 5))
        tk.Checkbutton(dialog, text="Ladezeit stauchen (Normaler Export)", variable=var_comp).pack(anchor="w", padx=40)

        # Speicher für das Ergebnis
        export_optionen = {}

        def on_ok():
            export_optionen["p1_aktiv"] = var_p1.get()
            export_optionen["p2_aktiv"] = var_p2.get()
            export_optionen["stauchung"] = var_comp.get()
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        # Buttons
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(side="bottom", fill="x", pady=15)
        tk.Button(btn_frame, text="Exportieren", command=on_ok, width=15).pack(side="left", padx=20)
        tk.Button(btn_frame, text="Abbrechen", command=on_cancel, width=15).pack(side="right", padx=20)

        # Warten, bis der Dialog geschlossen wird
        top.wait_window(dialog)

        # Wurde abgebrochen?
        if not export_optionen:
            return

        # =================================================================
        # --- HAUPT-EXPORT-LOGIK STARTET HIER ---
        # =================================================================
        for item in selected_items:
            values = self.tree.item(item, "values")
            
            # Wir suchen den passenden Eintrag in unseren Master-Daten
            for entry in self.highscore_manager.data:
                if entry["timestamp"] == values[5]:
                    match_id = entry.get("match_id")
                    
                    if match_id:
                        log_path = os.path.join("savegames", "logs", f"MATCH{match_id:06d}.json")
                        time_debt_ms = 0  # Der Puffer für Assertions
                        if os.path.exists(log_path):
                            try:
                                with open(log_path, "r", encoding="utf-8") as f:
                                    geladene_daten = json.load(f)
                                    # --- Der neue, strenge Türsteher ---
                                    if not isinstance(geladene_daten, dict) or "timeline" not in geladene_daten:
                                        from tkinter import messagebox
                                        messagebox.showinfo(
                                            "Replay nicht möglich", 
                                            f"Match {match_id} verwendet ein veraltetes Speicherformat.\n\n"
                                            "Replays stehen nur für neuere Matches zur Verfügung."
                                        )
                                        continue  # Bricht hier ab und geht zum nächsten Match in der Schleife
                                    
                                    # Ab hier können wir uns zu 100% darauf verlassen, dass das Format neu und sauber ist
                                    timeline = geladene_daten.get("timeline", [])
                                    yaml_lines = ["scenario:"]
                                    
                                    # =================================================================
                                    # --- 1. METADATEN AUSLESEN (SINGLE SOURCE OF TRUTH) ---
                                    # =================================================================
                                    metadata = geladene_daten.get("metadata", entry) 
                                    
                                    programm_name = metadata.get("programm_name", "").strip()
                                    is_kaenguru   = metadata.get("kaenguru_modus", 0) == 1
                                    is_zufall     = metadata.get("zufall", 0) == 1

                                    # =================================================================
                                    # --- 2. PROGRAMM-INDEX VIA CSV ERMITTELN ---
                                    # =================================================================
                                    # Direkt abbrechen, wenn modifiziert
                                    if "(modifiziert)" in programm_name:
                                        from tkinter import messagebox
                                        messagebox.showinfo("Replay nicht möglich", 
                                            f"Das Match '{programm_name}' enthält manuell veränderte Einstellungen.\n\n"
                                            "Replays werden aktuell nur für Standard-Programme (ohne Modifikationen) unterstützt.")
                                        continue 
                                    
                                    # Alle Tags entfernen
                                    base_programm_name = programm_name.replace(" (debug)", "")\
                                                                      .replace(" (1min)", "")\
                                                                      .replace(" (dev)", "").strip()
                                    prog_index = None
                                    
                                    # CSV durchsuchen
                                    try:
                                        if os.path.exists("Programme.csv"):
                                            with open("Programme.csv", "r", encoding="utf-8") as csv_file:
                                                lines = csv_file.readlines()
                                                for i in range(2, len(lines)):
                                                    row_name = lines[i].split(',')[0].strip()
                                                    if row_name == base_programm_name:
                                                        prog_index = i - 2  # Korrektur um die 2 Header-Zeilen
                                                        break
                                    except Exception as e:
                                        print(f"Fehler beim Lesen der Programme.csv: {e}")

                                    if prog_index is None:
                                        from tkinter import messagebox
                                        messagebox.showerror("Export abgebrochen", 
                                            f"Das Programm '{base_programm_name}' wurde in der Programme.csv nicht gefunden.\n"
                                            "Ein Replay ist nur für aktuell existierende Programme möglich.")
                                        continue 

                                    # =================================================================
                                    # --- 3. METADATEN NORMALISIEREN & REPLAY-SPEEDUPS ---
                                    # =================================================================
                                    # Spieler-Namen absichern
                                    metadata["spieler"] = metadata.get("spieler", "Spieler 1")
                                    metadata["spieler2"] = metadata.get("spieler2") or "" 

                                    # Fallback für alte Matches
                                    if "default_feuerzeit" not in metadata:
                                        fallback_wert = metadata.get("feuer", 10)
                                        print(f"⚠️ HINWEIS (Match {match_id}): 'default_feuerzeit' fehlt. Nutze Fallback 'feuer' ({fallback_wert}s).")
                                        metadata["default_feuerzeit"] = fallback_wert

                                    # --- GUI-STEUERUNG FÜR DIE STAUCHUNGSFUNKTION ---
                                    lg = metadata.get("ladenGelb", 3)
                                    if export_optionen["stauchung"]:
                                        # Stauchung AKTIVIERT
                                        new_lg = min(lg, 3) 
                                    else:
                                        # Stauchung DEAKTIVIERT (Originalwerte bleiben)
                                        new_lg = lg
                                        
                                    metadata["ladenGelb"] = new_lg

                                    # =================================================================
                                    # --- 4. INITIALISIERUNG & HISTORISCHE ZEITKAPSEL ---
                                    # =================================================================
                                    # Programm laden
                                    yaml_lines.append(f"  - name: \"Programm {prog_index} laden: {base_programm_name}\"")
                                    yaml_lines.append(f"    action: \"call_sm_method\"")
                                    yaml_lines.append(f"    wert: [\"setProgramm\", {prog_index}]")
                                    yaml_lines.append(f"    step_time: 300")
                                    yaml_lines.append("")

                                    # Replay Nummer setzen
                                    replay_id_str = f"Rec\u200A{match_id}"
                                    yaml_lines.append(f"  - name: \"Replay-ID setzen ({replay_id_str})\"")
                                    yaml_lines.append(f"    action: \"call_sm_method\"")
                                    yaml_lines.append(f"    wert: [\"set_replay_match\", \"{replay_id_str}\"]")
                                    yaml_lines.append(f"    step_time: 250")
                                    yaml_lines.append("")          

                                    # --- DIE ALLGEMEINE SCHLEIFE FÜR ALLE PARAMETER ---
                                    sync_params = {
                                        "spieler": "Spieler 1",
                                        "spieler2": "Spieler 2",
                                        "achtung": "Achtung-Zeit",
                                        "default_feuerzeit": "Feuer-Zeit (Startwert)",
                                        "vorbereiten": "Vorbereitungs-Zeit (inkl. Speedup)",
                                        "ladenGelb": "Lade-Zeit Gelb (inkl. Speedup)",
                                        "wiederholungen": "Wiederholungen"
                                    }

                                    for key, label in sync_params.items():
                                        wert = metadata.get(key)
                                        if wert is not None:
                                            yaml_lines.append(f"  - name: \"Wert setzen: {label} ({wert})\"")
                                            yaml_lines.append(f"    action: \"set_sm_attr\"")
                                            
                                            ziel_attribut = "feuer" if key == "default_feuerzeit" else key
                                            wert_str = f'"{wert}"' if isinstance(wert, str) else wert
                                            
                                            yaml_lines.append(f"    wert: [\"{ziel_attribut}\", {wert_str}]")
                                            yaml_lines.append(f"    step_time: 10")
                                            yaml_lines.append("")

                                    # MODIFIZIERT TAG ENTFERNEN
                                    yaml_lines.append(f"  - name: \"Modifiziert-Tag entfernen\"")
                                    yaml_lines.append(f"    action: \"remove_modifiziert_tag\"")
                                    yaml_lines.append(f"    step_time: 10")        
                                    yaml_lines.append("")

                                    # Countdown starten
                                    yaml_lines.append(f"  - name: \"Countdown starten\"")
                                    yaml_lines.append(f"    action: \"start_countdown\"")
                                    yaml_lines.append(f"    step_time: 500")
                                    yaml_lines.append("")

                                    # =================================================================
                                    # --- 5. NEUE MATCH TIMELINE VERARBEITUNG (Single-Pass Parser) ---
                                    # =================================================================
                                    last_t_orig_ms = 0
                                    current_state = ""
                                    accumulated_delay_ms = 0
                                    phase_t_orig_ms = 0 
                                    pending_survival_feuer = None
                                    
                                    lg_safe = max(1, lg)
                                    jaeger_initialisiert = False

                                    for ev in timeline:
                                        action_type = ev.get('a', '')
                                        t_orig_ms = int(ev.get('t', 0.0) * 1000)
                                        z = max(0, ev.get('z', -1))
                                        m = ev.get('m', '')
                                        
                                        # --- GUI-STEUERUNG FÜR DIE SPIELER ---
                                        # Wir filtern die unerwünschten Schüsse heraus, BEVOR sie verarbeitet werden.
                                        if action_type == "shoot":
                                            p_idx = ev.get('p', 0)
                                            if (p_idx == 0 and not export_optionen["p1_aktiv"]) or (p_idx == 1 and not export_optionen["p2_aktiv"]):
                                                # Trick: Wir benennen das Event um. Dadurch fängt es unten dein "else" Block auf!
                                                action_type = "übersprungen"
                                        
                                        # --- Start-Aufstellung setzen und dann die Engine machen lassen ---
                                        if not jaeger_initialisiert:
                                            p1_ij = ev.get('p1_ij')
                                            p2_ij = ev.get('p2_ij')
                                            if p1_ij is not None and p2_ij is not None:
                                                yaml_lines.append(f"  - name: \"Start-Rolle S1 (Sync)\"")
                                                yaml_lines.append(f"    action: \"set_is_jaeger\"")
                                                yaml_lines.append(f"    wert: [0, {p1_ij}]")
                                                yaml_lines.append(f"    step_time: 0") 
                                                yaml_lines.append("")
                                                
                                                yaml_lines.append(f"  - name: \"Start-Rolle S2 (Sync)\"")
                                                yaml_lines.append(f"    action: \"set_is_jaeger\"")
                                                yaml_lines.append(f"    wert: [1, {p2_ij}]")
                                                yaml_lines.append(f"    step_time: 0") 
                                                yaml_lines.append("")
                                                
                                                jaeger_initialisiert = True
                                        # ----------------------------------------------
                                        
                                        delta_orig_ms = max(0, t_orig_ms - last_t_orig_ms)
                                        delta_new_ms = delta_orig_ms 
                                        
                                        # --- DIE GENIALE 2-SEKUNDEN-LOGIK ---
                                        if current_state == "LADEN" and lg_safe > new_lg:
                                            next_phase_t_orig_ms = phase_t_orig_ms + delta_orig_ms
                                            
                                            def map_laden_time(t_ms):
                                                if new_lg <= 2: 
                                                    return t_ms * (new_lg / lg_safe)
                                                
                                                t_uncomp = 2000 
                                                if t_ms <= t_uncomp:
                                                    return float(t_ms)
                                                else:
                                                    ratio = (new_lg * 1000 - t_uncomp) / max(1, (lg_safe * 1000 - t_uncomp))
                                                    return t_uncomp + (t_ms - t_uncomp) * ratio
                                            
                                            mapped_start = map_laden_time(phase_t_orig_ms)
                                            mapped_end = map_laden_time(next_phase_t_orig_ms)
                                            
                                            delta_new_ms = int(mapped_end - mapped_start)
                                            phase_t_orig_ms = next_phase_t_orig_ms
                                        elif current_state == "LADEN":
                                            phase_t_orig_ms += delta_orig_ms
                                        
                                        if action_type in ["state_change", "feuer_start", "zyklus_start"]:
                                            # --- DER FIX: Survival-Sync NACH dem Zyklus erzwingen ---
                                            if pending_survival_feuer is not None:
                                                yaml_lines.append(f"  - name: \"Survival-Sync: Feuerzeit ueberschreiben ({pending_survival_feuer}s)\"")
                                                yaml_lines.append(f"    action: \"set_sm_attr\"")
                                                yaml_lines.append(f"    wert: [\"feuer\", {pending_survival_feuer}]")
                                                yaml_lines.append(f"    step_time: 10")
                                                yaml_lines.append("")
                                                pending_survival_feuer = None
                                                time_debt_ms += 10
                                            # --------------------------------------------------------
                                            accumulated_delay_ms += delta_new_ms
                                            current_state = m
                                            phase_t_orig_ms = 0 
                                            
                                            if m == "FEUER":
                                                w_init = ev.get('w', [])
                                                if w_init and (is_kaenguru or is_zufall):
                                                    yaml_lines.append(f"  - name: \"Zufall-Sync Start Zyklus {z} (Modus: {m})\"")
                                                    yaml_lines.append(f"    action: \"set_ziel_wahl\"")
                                                    yaml_lines.append(f"    wert: [{w_init}]") 
                                                    yaml_lines.append(f"    step_time: {accumulated_delay_ms+50}")
                                                    yaml_lines.append("")
                                                    accumulated_delay_ms = 0 
                                                    time_debt_ms += 50
                                                    
                                        elif action_type in ["shoot", "anulliere_zyklus"]:
                                            delta_new_ms = delta_new_ms + accumulated_delay_ms
                                            accumulated_delay_ms = 0 
                                            delta_new_ms = max(50, delta_new_ms)

                                            if time_debt_ms > 0:
                                                abbau_debt = min(delta_new_ms, time_debt_ms) 
                                                delta_new_ms -= abbau_debt         
                                                time_debt_ms -= abbau_debt 

                                            if action_type == "shoot":
                                                wert = ev.get('v', 0)
                                                yaml_lines.append(f"  - name: \"Schuss auf {wert} (Zyklus {z})\"")
                                                yaml_lines.append(f"    action: \"shoot\"")
                                                yaml_lines.append(f"    wert: {wert}")
                                                yaml_lines.append(f"    step_time: {delta_new_ms}")
                                                yaml_lines.append("")
                                                
                                                w_historisch = ev.get('w', [])
                                                if w_historisch and is_kaenguru:
                                                    yaml_lines.append(f"  - name: \"Zufall-Sync (Känguru Folgeziel)\"")
                                                    yaml_lines.append(f"    action: \"set_ziel_wahl\"")
                                                    yaml_lines.append(f"    wert: [{w_historisch}]")
                                                    yaml_lines.append(f"    step_time: 0")
                                                    yaml_lines.append("")
                                                    
                                            elif action_type == "anulliere_zyklus":
                                                p_idx = ev.get('p', 0)
                                                yaml_lines.append(f"  - name: \"VAR-Eingriff: Annulliere Zyklus für Spieler {p_idx} (Zyklus {z})\"")
                                                yaml_lines.append(f"    action: \"anulliere_zyklus\"")
                                                yaml_lines.append(f"    wert: {p_idx}")
                                                yaml_lines.append(f"    step_time: {delta_new_ms}")
                                                yaml_lines.append("")

                                        # =========================================================
                                        # --- SURVIVAL SYNC FIX (Speichern statt sofort ausführen) ---
                                        # =========================================================
                                        elif action_type == "survival_update":
                                            val_v = ev.get('v')
                                            if val_v is not None:
                                                feuer_neu = float(val_v) 
                                            else:
                                                feuer_neu = 0
                                                print("Achtung survival_update hatte keinen Wert bei v")
                                            
                                            pending_survival_feuer = feuer_neu 
                                            accumulated_delay_ms += delta_new_ms
                                        # =========================================================

                                            aktion_text = f"Schuss auf {wert}" if action_type == "shoot" else "VAR-Eingriff"
                                            yaml_lines.append(f"  - name: \"Prüfe Status nach {aktion_text}\"")
                                            yaml_lines.append(f"    actual_attr: \"get_state\"")
                                            yaml_lines.append(f"    expected: '{m}'")
                                            yaml_lines.append(f"    step_time: 10")  
                                            yaml_lines.append("")
                                            time_debt_ms += 10

                                        else:
                                            # --- DER BUGFIX ---
                                            # Unbekannte oder rein textuelle Events (z.B. "Bonus Spieler 1") 
                                            # ODER übersprungene Schüsse (!) landen hier und sparen ihre Zeit auf.
                                            accumulated_delay_ms += delta_new_ms

                                        
                                        last_t_orig_ms = t_orig_ms

                                    yaml_lines.append(f"  - name: \"GUI schließen\"")
                                    yaml_lines.append(f"    action: \"close_gui\"")
                                    yaml_lines.append(f"    step_time: 20000")
                                    yaml_lines.append("")

                                    # --- IN DATEI SPEICHERN ---
                                    export_dir = "./savegames/replays"
                                    os.makedirs(export_dir, exist_ok=True)
                                    yaml_filename = os.path.join(export_dir, f"REPLAY_MATCH{match_id:06d}.yaml")

                                    with open(yaml_filename, 'w', encoding='utf-8') as f:
                                        f.write("\n".join(yaml_lines))
                                        
                                    print("Export erfolgreich:", f"Replay exportiert nach: {yaml_filename}")
                                    
                            except Exception as e:
                                from tkinter import messagebox
                                messagebox.showerror("Fehler", f"Fehler beim Exportieren:\n{e}")
                        else:
                            from tkinter import messagebox
                            messagebox.showwarning("Nicht gefunden", f"Kein Detail-Log für Match {match_id} gefunden.")


    def export_video_config(self):
        selected_items = self.tree.selection()
        if not selected_items:
            from tkinter import messagebox
            messagebox.showinfo("Nichts ausgewählt", "Bitte wähle zuerst ein Match aus der Liste aus.")
            return

        from tkinter import simpledialog
        import os
        import json
        import tkinter as tk

        for item in selected_items:
            values = self.tree.item(item, "values")
            
            for entry in self.highscore_manager.data:
                if entry["timestamp"] == values[5]:
                    match_id = entry.get("match_id")
                    
                    if match_id:
                        log_path = os.path.join("savegames", "logs", f"MATCH{match_id:06d}.json")
                        if os.path.exists(log_path):
                            
                            # ==========================================
                            # 1. Abfrage: Wer ist POV?
                            # ==========================================
                            spieler_namen = f"{entry.get('spieler', 'Spieler 1')} vs. {entry.get('spieler2', 'Spieler 2')}"
                            pov_num = simpledialog.askinteger(
                                "Kamera-Regie", 
                                f"Match {match_id}: {spieler_namen}\n\nWer soll aus der Ego-Perspektive (POV) gezeigt werden?\n\n1 = {entry.get('spieler', 'Spieler 1')}\n2 = {entry.get('spieler2', 'Spieler 2')}",
                                initialvalue=1, minvalue=1, maxvalue=2
                            )
                            
                            if pov_num is None: continue
                            pov_player_idx = pov_num - 1
                            
                            # ==========================================
                            # 2. Abfrage: Color-Mapping & Video-Optionen
                            # ==========================================
                            mapping_result = {}
                            
                            def on_ok():
                                mapping_result['L'] = var_l.get()
                                mapping_result['B'] = var_b.get()
                                mapping_result['SHORTS'] = var_shorts.get() 
                                mapping_result['FOCUS'] = var_focus.get() 
                                mapping_result['WAFFE'] = var_weapon.get()
                                mapping_result['GHOST'] = var_ghost.get()
                                # --- NEU: Gegner Variablen speichern ---
                                mapping_result['GEGNER_AKTIV'] = var_gegner_active.get()
                                mapping_result['GEGNER_WAFFE'] = var_gegner_weapon.get()
                                mapping_result['GEGNER_GHOST'] = var_gegner_ghost.get()
                                dialog.destroy()
                                
                            dialog = tk.Toplevel(self.tree.master)
                            dialog.title("Video & LED-Farben konfigurieren")
                            dialog.geometry("400x620") # <-- Noch etwas höher für die Gegner-Einstellungen
                            dialog.transient(self.tree.master)
                            dialog.grab_set() 
                            
                            var_l = tk.IntVar(value=0) # 0=Blau, 1=Gold, 2=Split
                            var_b = tk.IntVar(value=1) # 0=Blau, 1=Gold, 2=Split
                            var_shorts = tk.BooleanVar(value=False) 
                            var_focus = tk.BooleanVar(value=True) 
                            var_weapon = tk.StringVar(value="RedDot") 
                            var_ghost = tk.BooleanVar(value=False) 
                            
                            # --- NEU: Variablen für den Gegner ---
                            var_gegner_active = tk.BooleanVar(value=True)
                            var_gegner_weapon = tk.StringVar(value="SteyrLP50")
                            var_gegner_ghost = tk.BooleanVar(value=True)
                            
                            tk.Label(dialog, text="Farbe für LEUCHTENDE Ziele ('L'):", font=("Arial", 10, "bold")).pack(pady=(10,5))
                            tk.Radiobutton(dialog, text="Blau (Alle)", variable=var_l, value=0).pack()
                            tk.Radiobutton(dialog, text="Goldgelb (Alle)", variable=var_l, value=1).pack()
                            tk.Radiobutton(dialog, text="Auto-Split (P1=Blau / P2=Gold)", variable=var_l, value=2).pack()
                            
                            tk.Label(dialog, text="Farbe für BLINKENDE Ziele ('B'):", font=("Arial", 10, "bold")).pack(pady=(10,5))
                            tk.Radiobutton(dialog, text="Blau (Alle)", variable=var_b, value=0).pack()
                            tk.Radiobutton(dialog, text="Goldgelb (Alle)", variable=var_b, value=1).pack()
                            tk.Radiobutton(dialog, text="Auto-Split (P1=Blau / P2=Gold)", variable=var_b, value=2).pack()
                            
                            # --- POV Waffenauswahl ---
                            tk.Frame(dialog, height=2, bd=1, relief="sunken").pack(fill="x", padx=20, pady=10)
                            tk.Label(dialog, text="DEINE Waffe (POV-Spieler):", font=("Arial", 10, "bold")).pack(pady=(0,5))
                            
                            waffen_frame = tk.Frame(dialog)
                            waffen_frame.pack()
                            tk.Radiobutton(waffen_frame, text="Red Dot", variable=var_weapon, value="RedDot").pack(side="left", padx=10)
                            tk.Radiobutton(waffen_frame, text="Steyr LP50", variable=var_weapon, value="SteyrLP50").pack(side="left", padx=10)
                            tk.Checkbutton(dialog, text="Deine Waffe ist halbtransparent", variable=var_ghost, fg="gray").pack()
                            
                            # --- NEU: GEGNER Waffenauswahl ---
                            tk.Frame(dialog, height=2, bd=1, relief="sunken").pack(fill="x", padx=20, pady=10)
                            tk.Label(dialog, text="GEGNER Waffe (Ghost-Spieler):", font=("Arial", 10, "bold")).pack(pady=(0,5))
                            
                            tk.Checkbutton(dialog, text="Gegner im Video anzeigen", variable=var_gegner_active, font=("Arial", 9, "bold"), fg="blue").pack()
                            
                            gegner_waffen_frame = tk.Frame(dialog)
                            gegner_waffen_frame.pack()
                            tk.Radiobutton(gegner_waffen_frame, text="Red Dot", variable=var_gegner_weapon, value="RedDot").pack(side="left", padx=10)
                            tk.Radiobutton(gegner_waffen_frame, text="Steyr LP50", variable=var_gegner_weapon, value="SteyrLP50").pack(side="left", padx=10)
                            tk.Checkbutton(dialog, text="Gegner ist halbtransparent (Ghost)", variable=var_gegner_ghost, fg="gray").pack()
                            
                            # --- Checkboxen ---
                            tk.Frame(dialog, height=2, bd=1, relief="sunken").pack(fill="x", padx=20, pady=10)
                            tk.Checkbutton(dialog, text="YouTube-Shorts Format (9:16)", variable=var_shorts, font=("Arial", 10, "bold"), fg="darkred").pack()
                            tk.Checkbutton(dialog, text="Fokus von Zwischenzielen entkoppeln", variable=var_focus, font=("Arial", 10)).pack(pady=(5,0))
                            
                            tk.Button(dialog, text="Exportieren", command=on_ok, bg="lightgreen").pack(pady=15)
                            self.tree.master.wait_window(dialog)
                            
                            if 'L' not in mapping_result: continue
                            
                            color_map_L = mapping_result['L']
                            color_map_B = mapping_result['B']
                            is_shorts = mapping_result['SHORTS']
                            is_focus = mapping_result['FOCUS']  
                            is_weapon = mapping_result['WAFFE'] 
                            is_ghost = mapping_result['GHOST']
                            
                            is_gegner_aktiv = mapping_result['GEGNER_AKTIV']
                            is_gegner_weapon = mapping_result['GEGNER_WAFFE']
                            is_gegner_ghost = mapping_result['GEGNER_GHOST']

                            # ==========================================
                            # 3. JSON verarbeiten (Die smarte Kamera-Regie)
                            # ==========================================
                            with open(log_path, "r", encoding="utf-8") as f:
                                daten = json.load(f)
                            
                            timeline = daten.get("timeline", daten) if isinstance(daten, dict) else daten
                            
                            timing, sequence_pov, sequence_gegner = [], [], []
                            gold_l, gold_b, blau_l, blau_b = [], [], [], []
                            
                            ACTION_STATES = ["FEUER", "PLAYER1", "PLAYER2", "END", "WINNER"]
                            
                            phase = "IDLE"  # Kann sein: "IDLE", "ACTION", "GRACE"
                            
                            last_orig_t = 0.0
                            t_video = 0.0
                            last_down_t_video = 0.0
                            first_up_done = False
                            grace_timer = 0.0
                            
                            last_L = []
                            last_B = []
                            owner_of_2 = None
                            
                            for ev in timeline:
                                action = ev.get("a", "")
                                m = ev.get("m", "")
                                t_orig = ev.get("t", 0.0)
                                
                                delta_orig = max(0, t_orig - last_orig_t)
                                last_orig_t = t_orig
                                
                                # 1. ZEIT-MANAGEMENT & GRACE-TIMER
                                if phase == "GRACE":
                                    if delta_orig >= grace_timer:
                                        t_video += grace_timer
                                        phase = "IDLE"
                                        last_down_t_video = t_video
                                        
                                        timing.append(round(t_video, 2))
                                        sequence_pov.append("DOWN")
                                        sequence_gegner.append("DOWN") # <-- NEU: Gegner senkt die Waffe!
                                        
                                        gold_l.append(last_L if color_map_L == 0 else [])
                                        blau_l.append(last_L if color_map_L == 1 else [])
                                        gold_b.append(last_B if color_map_B == 0 else [])
                                        blau_b.append(last_B if color_map_B == 1 else [])
                                    else:
                                        t_video += delta_orig
                                        grace_timer -= delta_orig
                                        
                                elif phase == "ACTION":
                                    t_video += delta_orig
                                    
                                last_L = ev.get("L", [])
                                last_B = ev.get("B", [])
                                
                                frame_hinzugefuegt = False
                                
                                # 2. STATUS WECHSEL
                                if action == "state_change":
                                    if m in ACTION_STATES:
                                        if phase in ["IDLE", "GRACE"]:
                                            if phase == "GRACE":
                                                phase = "ACTION"
                                            elif phase == "IDLE":
                                                phase = "ACTION"
                                                if not first_up_done:
                                                    t_video = 0.0
                                                    first_up_done = True
                                                else:
                                                    t_video = last_down_t_video + 3.0
                                                
                                                timing.append(round(t_video, 2))
                                                sequence_pov.append("UP")       
                                                sequence_gegner.append("UP") # <-- NEU: Gegner hebt die Waffe!
                                                frame_hinzugefuegt = True
                                                
                                    elif m not in ACTION_STATES:
                                        if phase == "ACTION":
                                            phase = "GRACE"
                                            grace_timer = 1.5

                                # 3. SCHÜSSE
                                elif action == "shoot" and phase in ["ACTION", "GRACE"]:
                                    timing.append(round(t_video, 2))
                                    
                                    shooter_idx = ev.get("p", -1)
                                    target = ev.get("v", -1)
                                    
                                    if target != -1:
                                        if shooter_idx == pov_player_idx:
                                            sequence_pov.append(target)
                                            sequence_gegner.append(-1)
                                        else:
                                            sequence_pov.append(-1)
                                            sequence_gegner.append(target)
                                    else:
                                        sequence_pov.append(-1) 
                                        sequence_gegner.append(-1)
                                        
                                    frame_hinzugefuegt = True
                                    
                                    if phase == "GRACE":
                                        grace_timer = 1.5
                                
                                # 4. FARBEN SPEICHERN
                                if frame_hinzugefuegt:
                                    L_list = ev.get("L", [])
                                    B_list = ev.get("B", [])
                                    
                                    # --- NEU: Funktion übergibt und speichert den Besitzer ---
                                    def process_colors(leds, mode, current_owner):
                                        if mode == 0: return [], leds, current_owner       
                                        if mode == 1: return leds, [], current_owner       
                                        
                                        g_out, b_out = [], []
                                        g_count = sum(1 for x in leds if x in [0, 1])
                                        b_count = sum(1 for x in leds if x in [3, 4])
                                        
                                        new_owner = current_owner
                                        
                                        for x in leds:
                                            if x in [0, 1]: 
                                                g_out.append(x)
                                            elif x in [3, 4]: 
                                                b_out.append(x)
                                            elif x == 2:
                                                # Hat das Ziel noch keinen Besitzer? Dann JETZT anhand Mehrheit ermitteln!
                                                if new_owner is None:
                                                    if g_count > b_count: 
                                                        new_owner = "GOLD"
                                                    else: 
                                                        new_owner = "BLAU" # (Blau gewinnt nur, wenn es wirklich Gleichstand zur Eroberungszeit gibt)
                                                        
                                                # Ziel anhand des festen Besitzers zuweisen
                                                if new_owner == "GOLD":
                                                    g_out.append(x)
                                                else:
                                                    b_out.append(x) 
                                                    
                                        # Wenn Ziel 2 ausgegangen ist (z.B. neues Match/Reset), Besitzer löschen!
                                        if 2 not in leds:
                                            new_owner = None
                                            
                                        return g_out, b_out, new_owner
                                        
                                    # Farben durch die Maschine jagen und Besitzer aktualisieren
                                    cur_gold_l, cur_blau_l, owner_of_2 = process_colors(L_list, color_map_L, owner_of_2)
                                    cur_gold_b, cur_blau_b, owner_of_2 = process_colors(B_list, color_map_B, owner_of_2)
                                    
                                    gold_l.append(cur_gold_l)
                                    blau_l.append(cur_blau_l)
                                    gold_b.append(cur_gold_b)
                                    blau_b.append(cur_blau_b)
                                    
                            # 5. FINISH
                            if phase in ["ACTION", "GRACE"]:
                                t_video += 1.5
                                timing.append(round(t_video, 2))
                                sequence_pov.append("DOWN")
                                sequence_gegner.append("DOWN") # <-- NEU: Gegner senkt die Waffe!
                                gold_l.append([])
                                blau_l.append([])
                                gold_b.append([])
                                blau_b.append([])
                                    
                            video_config = {
                                "MATCH_ID": match_id,
                                "POV_SPIELER": entry.get('spieler') if pov_num == 1 else entry.get('spieler2'),
                                "WAFFEN_PROFIL": is_weapon,
                                "GHOST_MODUS": is_ghost,
                                "GEGNER_ANZEIGEN": is_gegner_aktiv,      # <-- NEU
                                "WAFFEN_PROFIL_GEGNER": is_gegner_weapon, # <-- NEU
                                "GHOST_MODUS_GEGNER": is_gegner_ghost,    # <-- NEU
                                "YOUTUBE_SHORTS": is_shorts,  
                                "FOCUS_WAYPOINTS": is_focus, 
                                "TIMING": timing,
                                "SEQUENCE_POV": sequence_pov,
                                "SEQUENCE_GEGNER": sequence_gegner,
                                "GOLD_LEUCHTEND": gold_l,
                                "GOLD_BLINKEND": gold_b,
                                "BLAU_LEUCHTEND": blau_l,
                                "BLAU_BLINKEND": blau_b
                            }
                            
                            # ==========================================
                            # --- SMARTES & KOMPAKTES SPEICHERN ---
                            # ==========================================
                            export_dir = "./savegames/video_configs"
                            os.makedirs(export_dir, exist_ok=True)
                            export_path = os.path.join(export_dir, f"VIDEO_MATCH{match_id:06d}.json")
                            
                            num_cols = len(video_config["TIMING"])
                            col_widths = []
                            for i in range(num_cols):
                                w = max(
                                    len(json.dumps(video_config["TIMING"][i])),
                                    len(json.dumps(video_config["SEQUENCE_POV"][i])),
                                    len(json.dumps(video_config["SEQUENCE_GEGNER"][i])),
                                    len(json.dumps(video_config["GOLD_LEUCHTEND"][i])),
                                    len(json.dumps(video_config["GOLD_BLINKEND"][i])),
                                    len(json.dumps(video_config["BLAU_LEUCHTEND"][i])),
                                    len(json.dumps(video_config["BLAU_BLINKEND"][i]))
                                )
                                col_widths.append(w)
                                
                            def format_row(arr):
                                return "[" + ", ".join(f"{json.dumps(arr[i]):>{col_widths[i]}}" for i in range(len(arr))) + "]"
                            
                            json_zeilen = [
                                "{",
                                f'    "MATCH_ID": {video_config["MATCH_ID"]},',
                                f'    "POV_SPIELER": "{video_config["POV_SPIELER"]}",',
                                f'    "WAFFEN_PROFIL": "{video_config["WAFFEN_PROFIL"]}",',
                                f'    "GHOST_MODUS": {"true" if video_config["GHOST_MODUS"] else "false"},',
                                f'    "GEGNER_ANZEIGEN": {"true" if video_config["GEGNER_ANZEIGEN"] else "false"},',
                                f'    "WAFFEN_PROFIL_GEGNER": "{video_config["WAFFEN_PROFIL_GEGNER"]}",',
                                f'    "GHOST_MODUS_GEGNER": {"true" if video_config["GHOST_MODUS_GEGNER"] else "false"},',
                                f'    "YOUTUBE_SHORTS": {"true" if video_config["YOUTUBE_SHORTS"] else "false"},',
                                f'    "FOCUS_WAYPOINTS": {"true" if video_config["FOCUS_WAYPOINTS"] else "false"},',
                                f'    "TIMING":          {format_row(video_config["TIMING"])},',
                                f'    "SEQUENCE_POV":    {format_row(video_config["SEQUENCE_POV"])},',
                                f'    "SEQUENCE_GEGNER": {format_row(video_config["SEQUENCE_GEGNER"])},',
                                f'    "GOLD_LEUCHTEND":  {format_row(video_config["GOLD_LEUCHTEND"])},',
                                f'    "GOLD_BLINKEND":   {format_row(video_config["GOLD_BLINKEND"])},',
                                f'    "BLAU_LEUCHTEND":  {format_row(video_config["BLAU_LEUCHTEND"])},',
                                f'    "BLAU_BLINKEND":   {format_row(video_config["BLAU_BLINKEND"])}',
                                "}"
                            ]
                            
                            kompakter_json_text = "\n".join(json_zeilen)
                            
                            with open(export_path, "w", encoding="utf-8") as f:
                                f.write(kompakter_json_text)
                                
                            print(f"Video-Config erfolgreich exportiert: {export_path}")


    def play_replay(self):
        import subprocess
        import sys
        
        selected_items = self.tree.selection()
        if not selected_items:
            return
            
        for item in selected_items:
            values = self.tree.item(item, "values")
            
            for entry in self.highscore_manager.data:
                if entry["timestamp"] == values[5]:
                    match_id = entry.get("match_id")
                    if match_id:
                        yaml_filename = os.path.join("savegames", "replays", f"REPLAY_MATCH{match_id:06d}.yaml")
                        
                        if os.path.exists(yaml_filename):
                            print(f"Starte Roboter für {yaml_filename}...")
                            subprocess.Popen([sys.executable, "tests/test_ReplayRobot.py", yaml_filename])
                        else:
                            from tkinter import messagebox
                            messagebox.showwarning("Fehlendes Replay", 
                                f"Es wurde noch kein YAML für Match {match_id} exportiert.\n"
                                "Bitte klicke zuerst auf 'Export Replay'.")
                    break

    def generate_video(self):
        import subprocess
        import sys
        import os
        
        selected_items = self.tree.selection()
        if not selected_items:
            return
            
        for item in selected_items:
            values = self.tree.item(item, "values")
            
            for entry in self.highscore_manager.data:
                if entry["timestamp"] == values[5]:
                    match_id = entry.get("match_id")
                    if match_id:
                        # Pfad prüfen (Aus Sicht der GUI im Hauptordner)
                        check_path = os.path.join("savegames", "video_configs", f"VIDEO_MATCH{match_id:06d}.json")
                        
                        if os.path.exists(check_path):
                            print(f"Starte Video-Rendering für Match {match_id}...")
                            
                            # Argument für das Skript (Aus Sicht des video_creator Ordners)
                            config_argument = f"../savegames/video_configs/VIDEO_MATCH{match_id:06d}.json"
                            
                            subprocess.Popen([sys.executable, "video_creator.py", config_argument], cwd="video_creator")
                        else:
                            from tkinter import messagebox
                            messagebox.showwarning("Fehlende Config", 
                                f"Es wurde noch keine Video-Config für Match {match_id} exportiert.\n"
                                "Bitte klicke zuerst im Menü auf 'Export Video Config'.")
                    break

    def save_score(self):
        SD = self.SDeluebs
        # Echte Uhrzeit berechnen
        dauer_sekunden = time.monotonic() - SD.SMobjekt.laufzeit
        jetzt = dt.datetime.now()
        start_zeit_obj = jetzt - dt.timedelta(seconds=dauer_sekunden)
        start_zeit_str = start_zeit_obj.strftime("%H:%M:%S")        
        highscore_entry = {
            "spieler": SD.SMobjekt.spieler.get(),
            "spieler2": SD.SMobjekt.spieler2.get() if SD.SMobjekt.gegner_modus.get() == 1 else None,
            "start_zeit": start_zeit_str,
            "wiederholungen": SD.SMobjekt.wiederholungen.get(),
            "zyklus": SD.SMobjekt.zyklus.get(),
            "vorbereiten": SD.SMobjekt.vorbereiten.get(),
            "ladenGelb": SD.SMobjekt.ladenGelb.get(),
            "achtung": SD.SMobjekt.achtung.get(),
            "feuer": SD.SMobjekt.feuer.get(),
            "scheibenServo": SD.SMobjekt.scheibenServo.get(),
            "zufall": SD.SMobjekt.zufall.get(),
            "reihe": SD.SMobjekt.reihe.get(),
            "gegner_modus": SD.SMobjekt.gegner_modus.get(),
            "jaeger_modus": SD.SMobjekt.jaeger_modus.get(),
            "kaenguru_modus": SD.SMobjekt.kaenguru_modus.get(),
            "survival_modus": SD.SMobjekt.survival_modus.get(),
            "survival_penalty": SD.SMobjekt.survival_penalty,
            "default_feuerzeit": SD.SMobjekt.default_feuerzeit,
            "trick": SD.SMobjekt.trick.get(),
            "zaehlen": SD.SMobjekt.zaehlen.get(),
            "ton": SD.SMobjekt.ton.get(),
            "saveScore": SD.SMobjekt.saveScore.get(),
            "highscore_log": SD.KSobjekt.highscore_log,
            "programm_name": SD.SMobjekt.programm_name.get(),
            "punkte_durchgang": SD.KSobjekt.players[0].punkte_durchgang,
            "speedpunkte_durchgang": round(SD.KSobjekt.players[0].speedpunkte_durchgang,3),
            "gesamtpunkte": round(SD.KSobjekt.players[0].punkte_durchgang+SD.KSobjekt.players[0].speedpunkte_durchgang,3),
            "punkte_durchgang_pl2": SD.KSobjekt.players[1].punkte_durchgang,
            "speedpunkte_durchgang_pl2": round(SD.KSobjekt.players[1].speedpunkte_durchgang,3),
            "gesamtpunkte_pl2": round(SD.KSobjekt.players[1].punkte_durchgang+SD.KSobjekt.players[1].speedpunkte_durchgang,3),
            "match_id": SD.SMobjekt.match_id,
            "version": SD.version,
            "timestamp": dt.datetime.now().strftime("%d.%m.%y %H:%M:%S")
        }
        self.highscore_manager.save_highscore(highscore_entry)
        return highscore_entry

    def load_scores(self):
        self.highscore_manager.load_highscores()

    def refresh_table(self):
        """Lädt die JSON neu von der Festplatte und zeichnet die Tabelle neu."""
        # 1. Daten frisch von der Festplatte in den RAM laden
        self.load_scores()
        
        # 2. Die Anzahl der Einträge oben rechts aktualisieren
        self.anzahl_eintraege.set(len(self.highscore_manager.data))
        
        # 3. Das Dropdown-Menü aktualisieren (falls im Replay ein völlig neuer Modus gespielt wurde)
        modes = sorted(set(entry["programm_name"] for entry in self.highscore_manager.data))
        self.mode_dropdown.configure(values=["Alle Modi"] + list(modes))
        
        # 4. Tabelle neu zeichnen
        # ACHTUNG: Hier musst du die Funktion aufrufen, die du auch benutzt, 
        # wenn du im Dropdown einen Modus wechselst. 
        # (Meistens heißt die sowas wie self.update_tree() oder self.populate_table())
        self.update_highscores() # <-- DIESEN NAMEN BITTE AN DEINEN CODE ANPASSEN

    def save_match(self, match_timeline, highscore_entry):
        """Speichert den Event-Log zusammen mit den Metadaten"""
        try:
            match_id = self.SDeluebs.SMobjekt.match_id
            if match_timeline:
                os.makedirs(os.path.join("savegames", "logs"), exist_ok=True)
                log_dateiname = os.path.join("savegames", "logs", f"MATCH{match_id:06d}.json")
                
                match_data = {
                    "metadata": highscore_entry,
                    "timeline": match_timeline
                }
                
                json_str = json.dumps(match_data, indent=2)
                
                def collapse_arrays(match):
                    collapsed = re.sub(r'\s+', ' ', match.group(0))
                    return collapsed.replace('[ ', '[').replace(' ]', ']')
                
                json_str = re.sub(r'\[[\s\d\.,\-]*\]', collapse_arrays, json_str)
                
                with open(log_dateiname, "w", encoding="utf-8") as f:
                    f.write(json_str)
            print(f"Match {match_id} (Event-Log) erfolgreich gespeichert!")
        except Exception as e:
            print(f"Fehler beim Speichern der Match-Daten: {e}")
            


class HighscoreManager:
    def __init__(self, file_path="./savegames/highscore.json"):
        self.file_path = file_path
        self.data = []
        # NEU: Die Wegfahrsperre! Standardmäßig ist das Speichern erlaubt.
        self.readonly = False 

    def save_highscore(self, highscore_entry):
        # --- NEU: Der Türsteher ---
        if self.readonly:
            messagebox.showerror(
                "Speichern blockiert!", 
                "Die Highscore-Datei konnte beim Start nicht korrekt geladen werden "
                "(Netzwerkfehler oder beschädigte Datei).\n\n"
                "Um deine bisherigen Daten zu schützen, wurde das Speichern für "
                "diese Sitzung deaktiviert! Bitte überprüfe die highscore.json."
            )
            return  # Bricht die Funktion hier ab, NICHTS wird auf die Festplatte geschrieben!

        # ... (Dein bisheriger, sicherer Temp-File Code bleibt exakt gleich)
        self.data.append(highscore_entry)
        temp_file = self.file_path + ".tmp"
        
        try:
            with open(temp_file, "w", encoding="utf-8") as file:
                json.dump(self.data, file, indent=4)
                
            os.replace(temp_file, self.file_path)
            print("Neuer Highscore erfolgreich und sicher gespeichert.")
            
        except OSError as e:
            print(f"KRITISCHER FEHLER beim Speichern ({e}).")
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    pass

    def load_highscores(self):
        try:
            with open(self.file_path, "r", encoding="utf-8") as file:
                raw_data = json.load(file)
                
            self.data = [
                entry for entry in raw_data 
                if all(key in entry for key in [
                    "spieler", "programm_name", "punkte_durchgang", 
                    "gesamtpunkte", "timestamp" # (Gekürzt für die Übersicht)
                ])
            ]
            self.readonly = False # Alles gut, Speichern erlaubt.
            print("Highscores erfolgreich geladen.")
            
        except FileNotFoundError:
            # Völlig normal beim allerersten Start oder wenn man absichtlich löscht.
            self.data = []
            self.readonly = False # Speichern ist erlaubt!
            # Hier keine Messagebox, das würde beim Neuinstallieren nur nerven.
            print("Bisher keine Highscore-Datei gefunden. Starte mit leerer Liste.")
            
        except json.JSONDecodeError:
            # KRITISCH: Datei da, aber kaputt!
            self.data = []
            self.readonly = True # WEGFAHRSPERRE AKTIVIERT!
            messagebox.showerror(
                "Kritischer Fehler", 
                "Die Datei 'highscore.json' ist beschädigt und kann nicht gelesen werden!\n\n"
                "Das Spiel startet jetzt im schreibgeschützten Modus, "
                "damit die Datei nicht überschrieben wird."
            )
            
        except OSError as e:
            # KRITISCH: NAS/Netzwerk weg!
            self.data = []
            self.readonly = True # WEGFAHRSPERRE AKTIVIERT!
            messagebox.showerror(
                "Netzwerk/Zugriffs-Fehler", 
                f"Die Highscore-Datei ist nicht erreichbar!\nGrund: {e}\n\n"
                "Das Spiel startet jetzt im schreibgeschützten Modus."
            )
        
    def filter_highscores(self, mode_name=None, sort_by="gesamtpunkte"): 
        # Filter nach Modusname
        filtered_data = [entry for entry in self.data if mode_name is None or entry["programm_name"] == mode_name]
        
        # Sortierung nach Gesamtpunkten oder anderen Kriterien
        #filtered_data.sort(key=lambda x: x.get(sort_by, 0), reverse=True) #ACHTUNG DIESER FILTER WURDE ABGESCHALTET!!!!!!!!!!!!!
        return filtered_data

class DummyDeluebs:
    def __init__(self, root):
        self.root = root
        #HighscoreDeluebs
        self.HSobjekt = HighscoreDeluebs(self)    

if __name__ == "__main__":
    root = tk.Tk()
    app = DummyDeluebs(root)
    app.HSobjekt.show_highscore_window()
    root.mainloop()
