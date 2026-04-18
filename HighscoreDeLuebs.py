import json #Highscore
import datetime as dt #Highscore
import tkinter as tk
from tkinter import ttk #Highscore
from tkinter import messagebox
import re
import zipfile
import io #für zipfile
import os #für Eventlog
from PIL import Image, ImageTk  # Pillow muss installiert sein: `pip install pillow`

class HighscoreDeluebs:
    def __init__(self, SDeluebs):
        self.SDeluebs = SDeluebs
        self.highscore_manager = HighscoreManager()
        self.load_scores()
        self.anzahl_eintraege = tk.IntVar(value=0)
    
    def customize_style(self):
        # Style für das Treeview erstellen
        style = ttk.Style()
        style.configure("Treeview", font=("Arial", 23), rowheight=40)  # Schriftart und Schriftgröße für den Treeview
        style.configure("Treeview.Heading", font=("Arial", 30, "bold"))  # Überschriftenstil
        
        style.configure("TButton", font=("Arial", 22) ) # Schriftart und Schriftgröße für Buttons
        style.configure("TCombobox", padding=(10,5,60,5))
        style.configure("Treeview", background='lavenderblush') # 'dodgerblue') 

        # Funktion zum Aktualisieren der Highscore-Anzeige
    def show_highscore_window(self):
        #self.load_scores()
        self.highscore_window = tk.Toplevel(self.SDeluebs.root)
        self.highscore_window.title("Highscores")
        self.highscore_window.geometry('1800x900')#+50+50')
        self.highscore_window['background'] = 'plum'
        self.highscore_window.option_add("*TCombobox*Listbox.font", ("Arial",25))#Schriftgröße im Auswahlmenü
        self.customize_style()
        #self.highscore_window.wm_attributes("-topmost", True)



        top_frame = tk.Frame(self.highscore_window, bg='plum')#highlightthickness=0, bd=0)
        top_frame.pack(fill="x", padx=10, pady=10)
    
        #Logo
        with zipfile.ZipFile("data.pak", "r") as pak:  
            image = Image.open(io.BytesIO(pak.read("Highscore_v01.png")))  
        #image = image.resize((200, 200), Image.ANTIALIAS)  # Passe die Größe an
        photo = ImageTk.PhotoImage(image)
        label = tk.Label(top_frame, image=photo, highlightthickness=0, borderwidth=0)
        label.pack(side="left", padx=15)
        # Damit das Bild sichtbar bleibt, musst man die Referenz speichern
        label.image = photo  
        
        # Highscore-Modi abrufen
        #modes = set(entry["programm_name"] for entry in self.highscore_manager.data)
        modes = sorted(set(entry["programm_name"] for entry in self.highscore_manager.data))
    
        # Dropdown-Menü (ComboBox) erstellen
        selected_mode = tk.StringVar(value="Alle Modi")
        self.mode_dropdown = ttk.Combobox(top_frame, textvariable=selected_mode, values=["Alle Modi"] + list(modes), width=30, state="readonly")
        self.mode_dropdown.pack(side="left", padx=(150,0))
        self.mode_dropdown.configure(font=('Arial',30))
        self.mode_dropdown.bind("<Button-1>", lambda event: self.mode_dropdown.focus_set())
    
        #Schließen Knopf
        close_button = tk.Button(top_frame, text="Schließen", command=self.highscore_window.destroy, font=('Arial',25))
        close_button.pack(pady=10, side="right", padx=(0,35))
    
        #Label Text-Anzahl-Einträge
        block = tk.Frame(top_frame)
        block.pack(side="right", padx=(5,65))
        label_text_eintraege =  tk.Label(block, text=" Anzahl Einträge ", font=('Arial',17), bg="thistle")
        label_text_eintraege.pack(side=tk.TOP, padx=(0,0))
        label_anzahl_eintraege =  tk.Label(block, textvariable=self.anzahl_eintraege, font=('Arial',17))
        label_anzahl_eintraege.pack(side=tk.BOTTOM, padx=(5,5))
    
        # Frame für Treeview und Scrollbar erstellen
        frame = tk.Frame(self.highscore_window, bg='plum') #highlightthickness=0, bd=0)
        frame.pack(pady=10, fill="both", expand=True)
        
#        # Canvas als Hintergrund, mit place statt pack
#        self.MyCanvas = tk.Canvas(frame, width=1800, height=900, highlightthickness=0)
#        self.mein_bg = tk.PhotoImage(file='Hintergrundv04.png') 
#        self.MyCanvas.create_image(0, 0, anchor="nw", image=self.mein_bg)
#        self.MyCanvas.place(x=0, y=0, relwidth=1, relheight=1)  # Setzt es als Hintergrund
        
        # Scrollbar erstellen
        scrollbar = tk.Scrollbar(frame, width=47)
        scrollbar.pack(side="right", fill="y")
        
        # Treeview erstellen und an die Scrollbar binden
        tree = ttk.Treeview(
            frame,  # Direkt im Frame, nicht im Canvas
            # NEU: "Match-ID" als allererste Spalte hinzugefügt
            columns=("Match-ID", "Spieler", "Modus", "Punkte Durchgang", "Gesamtpunkte", "Zeitstempel"),
            show="headings",
            yscrollcommand=scrollbar.set,
            selectmode="extended",
        )
        tree.heading("Match-ID", text="ID")
        tree.heading("Spieler", text="Spieler")
        tree.heading("Modus", text="Modus")
        tree.heading("Punkte Durchgang", text="Punkte")
        tree.heading("Gesamtpunkte", text="Gesamtpunkte")
        tree.heading("Zeitstempel", text="Zeitstempel")
        tree.pack(side="left", fill="both", expand=True)
        
        scrollbar.config(command=tree.yview)
        
        tree.column("Match-ID", width=60, anchor="center", stretch=False)
        tree.column("Spieler", width= 260)#, stretch=True)
        tree.column("Modus", width= 400, stretch=True)
        tree.column("Punkte Durchgang", width= 30, stretch=True)

        # Funktion zum Sortieren basierend auf einer Spalte
        def sort_column(tree, col, reverse):
            def convert_value(value):
                try:
                    if col == "Zeitstempel":
                        return dt.datetime.strptime(value, "%d.%m.%y %H:%M:%S")
                    
                    # --- NEU: Den Strich abfangen, damit Python beim Sortieren nicht crasht ---
                    if value == "-":
                        return -1  # Alte Matches rutschen damit immer ans Ende/den Anfang
                        
                    return float(value) if "." in value else int(value) 
                except ValueError:
                    return value
            
            # Daten abrufen und konvertieren
            data = [(convert_value(tree.set(k, col)), k) for k in tree.get_children('')]
            data.sort(reverse=reverse, key=lambda t: t[0])
            
            # Einträge bewegen
            for index, (val, k) in enumerate(data):
                tree.move(k, '', index)
            
            # Spaltenüberschrift mit Sortierung aktualisieren
            tree.heading(col, command=lambda: sort_column(tree, col, not reverse))

        
        # Event-Bindung für jede Spalte in Treeview
        for col in ("Match-ID", "Spieler", "Modus", "Punkte Durchgang", "Gesamtpunkte", "Zeitstempel"):
            tree.heading(col, command=lambda _col=col: sort_column(tree, _col, True)) #War vorher auf False


        # Frame für Filter-Eingaben
        filter_frame = tk.Frame(self.highscore_window, bg='plum')
        filter_frame.pack(fill="x")
        
        filters = {}
        # NEU: "match_id" ganz vorne in das Tupel eingefügt!
        for col in ("match_id", "spieler", "programm_name", "punkte_durchgang", "gesamtpunkte", "timestamp"):
            # Das erste Feld (ID) schmaler machen, die anderen bleiben auf 16
            feld_breite = 3 if col == "match_id" else 16 
            
            entry = tk.Entry(filter_frame, font=('Arial',25), width=feld_breite)
            entry.pack(side="left", padx=5)
            filters[col] = entry
            entry.bind("<Return>", lambda event: apply_filters()) #Bindet die Enter-Taste

        def apply_filters():
            # Treeview zuerst mit allen Daten aktualisieren
            update_treeview(tree, self.highscore_manager.data)
            update_highscores()
        
            # Gefilterte Einträge sammeln
            filtered_items = []
            for row_id in tree.get_children():
                values = tree.item(row_id, "values")  # Hier sind die Zeilenwerte (Tuple)
                match = True
        
                for col, entry in filters.items():  # Verwende Filter-Spaltennamen aus `filters`
                    val = entry.get()
                    if val:
                        try:
                            # Hier wird kein Index gesucht, sondern direkt der Wert aus `values`
                            cell_value = values[list(filters.keys()).index(col)]  # Spaltennamen aus `filters` nutzen
        
                            # Zahlenwerte filtern
                            if col in ["punkte_durchgang", "gesamtpunkte"]:
                                #print('hier')
                                cell_value = float(cell_value)
                                if ">=" in val:
                                    threshold = float(val.split(">=")[1].strip())  # Float statt int
                                    if cell_value < threshold:
                                        match = False
                                elif "<=" in val:
                                    threshold = float(val.split("<=")[1].strip())
                                    if cell_value > threshold:
                                        match = False
                                elif ">" in val:
                                    threshold = float(val.split(">")[1].strip())
                                    if cell_value <= threshold:
                                        match = False
                                elif "<" in val:
                                    threshold = float(val.split("<")[1].strip())
                                    if cell_value >= threshold:
                                        match = False
                                elif val.replace(".", "", 1).isdigit():  # Prüft, ob val eine gültige Dezimalzahl ist
                                    if cell_value != float(val.strip()):  # Float statt int
                                        match = False
                                else:
                                    print(f"Ungültige Eingabe: {val}")  # Fehlerabfangung
        
                            # Timestamp filtern (Datum muss innerhalb des Bereichs sein)
                            elif col == "timestamp":
                                if "-" in val:  # Bereichsfilterung
                                    try:
                                        start, end = map(str.strip, val.split("-"))
                                        format_filter = "%d.%m.%y"# %H:%M:%S"
                                        format_tree = "%d.%m.%y %H:%M:%S"
                                        start_date = dt.datetime.strptime(start, format_filter)
                                        end_date = dt.datetime.strptime(end, format_filter) + dt.timedelta(days=1)
                                        cell_date = dt.datetime.strptime(cell_value, format_tree)
                                        
                                        if not (start_date <= cell_date <= end_date):
                                            match = False
                                    except ValueError:
                                        print(f"Ungültiges Zeitformat: {val}. Bitte im Format 'TT.MM.JJ - TT.MM.JJ' eingeben.")
        
                            # Wildcard-Suche (NEU: "match_id" hier ergänzt!)
                            elif col in ["match_id", "spieler", "programm_name"]:
                                pattern = re.compile(val, re.IGNORECASE)  # Regex-Muster mit Wildcard
                                # WICHTIG: str(cell_value) nutzen, falls die ID als Zahl (int) vorliegt!
                                if not pattern.search(str(cell_value)):
                                    match = False
        
                        except (ValueError, IndexError):
                            print(f"Ungültige Eingabe für {col}: {val}")
                            match = False
        
                if match:
                    filtered_items.append(row_id)
        
            # Alle Treeview-Einträge löschen, die den Kriterien nicht entsprechen
            for row_id in tree.get_children():
                if row_id not in filtered_items:
                    tree.delete(row_id)
            
            #sort_column(tree, "Gesamtpunkte", True) # AL AL AL Jetzt wird richtig sortiert        
            sort_column(tree, "Zeitstempel", True) # AL AL AL Jetzt wird richtig sortiert        

        # Filter auf einen Button binden
        filter_button = tk.Button(filter_frame, text="Filter anwenden", command=apply_filters, font=('Arial',20))
        filter_button.pack(side="right", padx=(0,5))

 
        # Funktion zum Aktualisieren der Highscore-Anzeige
        def update_highscores():
            selected = selected_mode.get()
            filtered_data = self.highscore_manager.filter_highscores(
                mode_name=None if selected == "Alle Modi" else selected, sort_by="gesamtpunkte"
            ) # Hier wird es nur nach den Gesamtpunkten von Player 1 sortiert.
            update_treeview(tree, filtered_data)        
            #sort_column(tree, "Gesamtpunkte", True) # AL AL AL Jetzt wird richtig sortiert
            sort_column(tree, "Zeitstempel", True) # AL AL AL Jetzt wird richtig sortiert        

        def update_treeview(tree, data):
            #print(f"Anzahl der Einträge: {len(data)}")
            self.anzahl_eintraege.set(len(data))
            # Treeview leeren
            for row in tree.get_children():
                tree.delete(row)
            
            # Tags definieren mit Farben
            tree.tag_configure("even", background="thistle")
            tree.tag_configure("odd", background="lavenderblush")
            tag="even"
            
            # Einträge hinzufügen
            for hs in data:
                #timestamp=hs.get("timestamp", "Unbekannt")
                #print(f"Time: {timestamp} tag: {tag}")
                if tag =="even": tag = "odd"
                else: tag = "even"
                
                spieler_name = hs.get("spieler", "Unbekannt")
                punkte_durchgang = hs.get("punkte_durchgang", 0)
                gesamtpunkte = hs.get("gesamtpunkte", 0)
                match_id = hs.get("match_id", "-")
                if hs.get("survival_modus", 0) == 1 and hs.get("gegner_modus", 0) == 1: # and "spieler2" in hs:
                    spieler_name += f"; {hs['spieler2']}"  # Kombinierte Spielernamen im Gegner-Modus
                    spieler_name += f"; {hs.get('zyklus','N/A')} Rnd" 
                    punkte_durchgang = hs.get("punkte_durchgang", 0)+hs.get("punkte_durchgang_pl2", 0)
                    gesamtpunkte = round(hs.get("gesamtpunkte", 0)+hs.get("gesamtpunkte_pl2", 0),3)     
                    # --- NEU: Match-ID auslesen (mit Fallback "-", falls alte Matches keine haben) ---
                
                
                tree.insert(
                    "",
                    "end",
                    values=(
                        match_id,            # <--- HIER ALS ERSTES EINFÜGEN!
                        spieler_name,
                        hs.get("programm_name", "Unbekannt"),
                        punkte_durchgang,
                        gesamtpunkte,
                        hs.get("timestamp", "Unbekannt")
                    ),
                    tags=(tag,)
                )
                
                if hs.get("survival_modus", 0) == 0 and hs.get("gegner_modus", 0) == 1: #and "spieler2" in hs:
                    tree.insert(
                        "",
                        "end",
                        values=(
                            match_id,            # <--- HIER ALS ERSTES EINFÜGEN!
                            hs.get("spieler2", "Unbekannt"),
                            hs.get("programm_name", "Unbekannt"),
                            hs.get("punkte_durchgang_pl2", 0),
                            hs.get("gesamtpunkte_pl2", 0),     
                            hs.get("timestamp", "Unbekannt")
                        ),
                        tags=(tag,)
                    )

    
        # Kontextmenü erstellen
        def show_context_menu(event):
            context_menu = tk.Menu(self.highscore_window, tearoff=0)
            context_menu.add_command(label="Informationen", command=show_selected_entries,font=('Arial',35))            
            context_menu.add_command(label="Highscore Log", command=show_selected_highscore_logs,font=('Arial',35))
            context_menu.add_command(label="Export Replay", command=export_match_to_yaml,font=('Arial',35))
            context_menu.add_command(label="Replay abspielen", command=play_replay, font=('Arial',35))
            context_menu.add_command(label="Löschen", command=delete_selected_entries,font=('Arial',35))
            context_menu.post(event.x_root, event.y_root)
            #def close_menu(event):
            #    context_menu.unpost()
            #tree.bind("<Button-1>", close_menu)
    
        # Funktion zum Löschen von ausgewählten Einträgen
        def delete_selected_entries():
            selected_items = tree.selection()
            for item in selected_items:
                values = tree.item(item, "values")
                for entry in self.highscore_manager.data:
                    if entry["timestamp"] == values[5]:
                    #if entry["spieler"] == values[0] and entry["programm_name"] == values[1] and str(entry["gesamtpunkte"]) == values[3]:
                        entry_data =  "Programm: "+entry.get("programm_name","unbekannt")+"\n"+str(entry.get("timestamp","unbekannt"))+"\n\n" \
                                      "Spieler: " +entry.get("spieler","unbekannt")+"\nPunkte: "+str(entry.get("punkte_durchgang","0"))+"\nGesamtpunkte: "+str(entry.get("gesamtpunkte","0"))+"\n" 
                        if entry["gegner_modus"] == 1:
                            entry_data = entry_data + "\n" \
                                      "Spieler 2: "+entry.get("spieler2","unbekannt")+"\nPunkte: "+str(entry.get("punkte_durchgang_pl2","0"))+"\nGesamtpunkte: "+str(entry.get("gesamtpunkte_pl2","0"))+"\n"  
                        self.highscore_window.withdraw()
                        antwort = messagebox.askyesno("Bestätigung", "Eintrag wirklich löschen?\n\n"+entry_data)
                        self.highscore_window.deiconify()
                        self.highscore_window.lift()
                        if not antwort: break
                        self.highscore_manager.data.remove(entry)
                        #tree.delete(item)
                        break
            update_treeview(tree, self.highscore_manager.data) #Datenbank neu Aufbauen
            apply_filters() #AL AL AL Filter anwenden
            #sort_column(tree, "Gesamtpunkte", True) # AL AL AL Jetzt wird sortiert, dass Gesamtpunkte oben sind.
            sort_column(tree, "Zeitstempel", True) # AL AL AL Jetzt wird richtig sortiert        
            
            # Datenbank speichern #Dies sollte besser von einer Funktion in der Klasse Highscore durchgeführt werden
            with open(self.highscore_manager.file_path, "w") as file:
                json.dump(self.highscore_manager.data, file, indent=4)

        #Funktion um alle Inhalte anzuzeigen
        def show_selected_entries(): 
            exclude_keys = {"highscore_log"} #, "saveScore", "default_feuerzeit"}  # Erweiterbar bei Bedarf
            selected_items = tree.selection() 
            for item in selected_items: 
                values = tree.item(item, "values") 
                for entry in self.highscore_manager.data:
                    if entry["timestamp"] == values[5]:
                        text = "\n".join(
                            [f"{key}: {value}" for key, value in entry.items() if key not in exclude_keys]
                        )
                        messagebox.showinfo("Highscore-Details", text)
 


        def show_selected_highscore_logs():
            selected_items = tree.selection()
            for item in selected_items:
                values = tree.item(item, "values")
                # Wir suchen den passenden Eintrag in unseren Master-Daten
                for entry in self.highscore_manager.data:
                    if entry["timestamp"] == values[5]:
                        log_window = tk.Toplevel()
                        log_window.title(f"Detail-Log: {entry.get('programm_name', 'Unbekannt')}")
                        
                        # 1. Basis-Infos vorbereiten
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
                        
                        # 2. EVENT-LOG (aus separater Datei) nachladen
                        match_id = entry.get("match_id")
                        event_details = ""
                        
                        if match_id:
                            #log_path = os.path.join("logs", f"MATCH{match_id:06d}.json")
                            log_path = os.path.join("savegames", "logs", f"MATCH{match_id:06d}.json")
                            if os.path.exists(log_path):
                                try:
                                    with open(log_path, "r", encoding="utf-8") as f:
                                        geladene_daten = json.load(f)
                                        # --- NEU: Die Türsteher-Weiche ---
                                        if isinstance(geladene_daten, dict):
                                            # Neues Format (ab Match 102): Aus der Schublade holen
                                            timeline = geladene_daten.get("timeline", [])
                                        else:
                                            # Altes Format (Match 1 bis 101): Ist bereits die Liste
                                            timeline = geladene_daten
                                        
                                    event_details = "DETAILLIERTES EVENT-LOG: "+ f"MATCH{match_id:06d}"+"\n"
                                    
                                    # Tabellen-Header erstellen (Modus auf 12 verbreitert für längere Namen)
                                    header = f"{'Zeit':>8} | {'Ref':>6} | {'Zykl':^4} | {'Modus':^8} | {'Ziel':^4} | {'Zielwahl':^20} | {'P1-Treffer':^20} | {'P2-Treffer':^20}"
                                    separator = "-" * len(header)
                                    
                                    event_details += f"{header}\n{separator}\n"
                                    
                                    # Zeilen generieren
                                    for ev in timeline:
                                        # Zeiten mit Nachkommastellen runden
                                        t = f"{ev.get('t', 0):.2f}s"
                                        tref = f"{ev.get('tref', 0):.2f}s"
                                        
                                        # Reine Werte holen (OHNE Breiten-Formatierung)
                                        zyk = ev.get('z', 0)
                                        modus = str(ev.get('m', '')).strip() # Ein strip() schadet hier zur Sicherheit nie!
                                        
                                        # Getroffenes Ziel (v). Falls es kein Schuss war oder 'v' fehlt, zeige '-'
                                        ziel_getroffen = ev.get('v', '-')
                                        
                                        # Listen in reine Strings umwandeln
                                        zielwahl = str(ev.get('w', []))
                                        p1_treffer = str(ev.get('p1_t', []))
                                        p2_treffer = str(ev.get('p2_t', []))
                                        
                                        # HIER passiert die Magie: Strikt nach festen Breiten formatieren
                                        line = f"{t:>8} | {tref:>6} | {zyk:^4} | {modus:^8} | {ziel_getroffen:^4} | {zielwahl:^20} | {p1_treffer:^20} | {p2_treffer:^20}\n"
                                        event_details += line

                                        
                                except Exception as e:
                                    event_details = f"\n[Fehler beim Laden des Event-Logs: {e}]"
                            else:
                                event_details = "\n[Keine detaillierte Event-Datei gefunden]"
                        
                        # 3. GUI Text-Widget befüllen
                        full_text = "\n".join(info_lines) + "\n\n" + event_details
                        
                        text_widget = tk.Text(log_window, wrap="none", width=120, height=35, font=("Courier", 20))
                        text_widget.insert("1.0", full_text)
                        text_widget.configure(state="disabled")
                        
                        # Scrollbars
                        x_scroll = tk.Scrollbar(log_window, orient="horizontal", command=text_widget.xview)
                        y_scroll = tk.Scrollbar(log_window, orient="vertical", command=text_widget.yview)
                        text_widget.configure(xscrollcommand=x_scroll.set, yscrollcommand=y_scroll.set)
                        
                        text_widget.grid(row=0, column=0, sticky="nsew")
                        y_scroll.grid(row=0, column=1, sticky="ns")
                        x_scroll.grid(row=1, column=0, sticky="ew")
                        
                        log_window.grid_rowconfigure(0, weight=1)
                        log_window.grid_columnconfigure(0, weight=1)

        def export_match_to_yaml():
            selected_items = tree.selection()
            for item in selected_items:
                values = tree.item(item, "values")
                
                # Wir suchen den passenden Eintrag in unseren Master-Daten
                for entry in self.highscore_manager.data:
                    if entry["timestamp"] == values[5]:
                        match_id = entry.get("match_id")
                        
                        if match_id:
                            log_path = os.path.join("savegames", "logs", f"MATCH{match_id:06d}.json")
                            time_debt_ms = 0  # Der Puffer
                            if os.path.exists(log_path):
                                try:
                                    with open(log_path, "r", encoding="utf-8") as f:
                                        geladene_daten = json.load(f)
                                        # --- NEU: Die Türsteher-Weiche ---
                                        if isinstance(geladene_daten, dict):
                                            # Neues Format (ab Match 102): Aus der Schublade holen
                                            timeline = geladene_daten.get("timeline", [])
                                        else:
                                            # Altes Format (Match 1 bis 101): Ist bereits die Liste
                                            timeline = geladene_daten
                                        
                                    yaml_lines = ["scenario:"]
                                    last_t = 0.0

                                    # --- PROGRAMM-INDEX VIA CSV ERMITTELN ---
                                    # 1. Originalnamen aus dem Log holen
                                    programm_name = entry.get("programm_name", "").strip()

                                    # --- NEU: Direkt abbrechen, wenn modifiziert ---
                                    if "(modifiziert)" in programm_name:
                                        from tkinter import messagebox
                                        messagebox.showinfo("Replay nicht möglich", 
                                            f"Das Match '{programm_name}' enthält manuell veränderte Einstellungen.\n\n"
                                            "Replays werden aktuell nur für Standard-Programme (ohne Modifikationen) unterstützt.")
                                        continue # Überspringt dieses Match
                                    
                                    # 2. Alle Tags entfernen, um den nackten Basisnamen für die CSV zu bekommen
                                    base_programm_name = programm_name.replace(" (debug)", "")\
                                                                      .replace(" (1min)", "")\
                                                                      .replace(" (dev)", "").strip()
                                    prog_index = None
                                    
                                    # 3. CSV durchsuchen
                                    try:
                                        if os.path.exists("Programme.csv"):
                                            with open("Programme.csv", "r", encoding="utf-8") as csv_file:
                                                lines = csv_file.readlines()
                                                # Wir starten ab Index 2 (die 3. Zeile), da Zeile 1+2 Header sind
                                                for i in range(2, len(lines)):
                                                    # Text vor dem ersten Komma extrahieren
                                                    row_name = lines[i].split(',')[0].strip()
                                                    if row_name == base_programm_name:
                                                        prog_index = i - 2  # Korrektur um die 2 Header-Zeilen
                                                        break
                                    except Exception as e:
                                        print(f"Fehler beim Lesen der Programme.csv: {e}")

                                    # Prüfung: Wurde das Programm gefunden?
                                    if prog_index is None:
                                        from tkinter import messagebox
                                        messagebox.showerror("Export abgebrochen", 
                                            f"Das Programm '{base_programm_name}' wurde in der Programme.csv nicht gefunden.\n"
                                            "Ein Replay ist nur für aktuell existierende Programme möglich.")
                                        continue # Überspringt dieses Match und macht mit dem nächsten markierten weiter

                                    # --- INITIALISIERUNG IM YAML SCHREIBEN ---

# --- INITIALISIERUNG IM YAML SCHREIBEN ---
                                    
                                    # SCHRITT 1: Programm laden
                                    yaml_lines.append(f"  - name: \"Programm {prog_index} laden: {base_programm_name}\"")
                                    yaml_lines.append(f"    action: \"call_sm_method\"")
                                    yaml_lines.append(f"    wert: [\"setProgramm\", {prog_index}]")
                                    yaml_lines.append(f"    step_time: 300")
                                    yaml_lines.append("")

                                    # SCHRITT 1.1: Replay Nummer setzen
                                    replay_id_str = f"Rec\u200A{match_id}"
                                    yaml_lines.append(f"  - name: \"Replay-ID setzen ({replay_id_str})\"")
                                    yaml_lines.append(f"    action: \"call_sm_method\"")
                                    yaml_lines.append(f"    wert: [\"set_replay_match\", \"{replay_id_str}\"]")
                                    yaml_lines.append(f"    step_time: 250")
                                    yaml_lines.append("")           


                                    # SCHRITT 1.2: Spielernamen aus der Highscore auslesen und setzen
                                    sp1 = entry.get("spieler", "Spieler 1")
                                    sp2 = entry.get("spieler2", "Spieler 2")
                                    if sp2 is None: 
                                        sp2 = "" # Verhindert, dass None als Text "None" gesetzt wird

                                    # Da set_sm_attr das system_update_laeuft selbst regelt, machen wir einfach 2 saubere Schritte daraus!
                                    yaml_lines.append(f"  - name: \"Spieler 1 aus Highscore setzen\"")
                                    yaml_lines.append(f"    action: \"set_sm_attr\"")
                                    yaml_lines.append(f"    wert: [\"spieler\", \"{sp1}\"]")
                                    yaml_lines.append(f"    step_time: 10")
                                    yaml_lines.append("")

                                    yaml_lines.append(f"  - name: \"Spieler 2 aus Highscore setzen\"")
                                    yaml_lines.append(f"    action: \"set_sm_attr\"")
                                    yaml_lines.append(f"    wert: [\"spieler2\", \"{sp2}\"]")
                                    yaml_lines.append(f"    step_time: 10")
                                    yaml_lines.append("")

                                    # SCHRITT 1.5: Dev-Override & Smart-Fast-Forward
                                    vorb = entry.get("vorbereiten", 5)
                                    lg   = entry.get("ladenGelb", 3)
                                    
                                    time_saved_ms = 0
                                    first_shot_done = False # Wichtig für die Zeit-Korrektur später
                                    
                                    if "(dev)" in programm_name:
                                        # DEV-Mode: Extreme Beschleunigung
                                        wdh = entry.get("wiederholungen", 2)
                                        # Wir teilen die Liste in 3 einzelne saubere Aktionen auf
                                        yaml_lines.append(f"  - name: \"Dev-Override: Vorbereiten auf 1\"")
                                        yaml_lines.append(f"    action: \"set_sm_attr\"")
                                        yaml_lines.append(f"    wert: [\"vorbereiten\", 1]")
                                        yaml_lines.append(f"    step_time: 10")
                                        yaml_lines.append("")
                                        
                                        yaml_lines.append(f"  - name: \"Dev-Override: LadenGelb auf 1\"")
                                        yaml_lines.append(f"    action: \"set_sm_attr\"")
                                        yaml_lines.append(f"    wert: [\"ladenGelb\", 1]")
                                        yaml_lines.append(f"    step_time: 10")
                                        yaml_lines.append("")
                                        
                                        yaml_lines.append(f"  - name: \"Dev-Override: Wiederholungen setzen\"")
                                        yaml_lines.append(f"    action: \"set_sm_attr\"")
                                        yaml_lines.append(f"    wert: [\"wiederholungen\", {wdh}]")
                                        yaml_lines.append(f"    step_time: 10")
                                        yaml_lines.append("")
                                    else:
                                        # SMART-SPEEDUP für normale, echte Matches
                                        new_lg = min(lg, 3)
                                        
                                        # Berechnen, wie viele Sekunden wir der Realität klauen
                                        time_saved_s =  (lg - new_lg)
                                        time_saved_ms = int(time_saved_s * 1000)
                                        
                                        if time_saved_ms > 0:
                                            yaml_lines.append(f"  - name: \"Smart-Override: Wartezeiten auf je max 3s reduziert\"")
                                            yaml_lines.append(f"    action: \"set_sm_attr\"")
                                            yaml_lines.append(f"    wert: [\"ladenGelb\", {new_lg}]")                                           
                                            yaml_lines.append(f"    step_time: 10")
                                            yaml_lines.append("")
                                            
                                        # MODIFIZIERT TAG ENTFERNEN
                                        yaml_lines.append(f"  - name: \"Modifiziert-Tag entfernen\"")
                                        yaml_lines.append(f"    action: \"remove_modifiziert_tag\"")
                                        yaml_lines.append(f"    step_time: 10")       
                                        yaml_lines.append("")

                                    
#                                    # SCHRITT 1: Programm laden
#                                    yaml_lines.append(f"  - name: \"Programm {prog_index} laden: {base_programm_name}\"")
#                                    yaml_lines.append(f"    actual: \"lambda: self.app.SMobjekt.setProgramm({prog_index})\"")
#                                    yaml_lines.append(f"    expected:")
#                                    yaml_lines.append(f"    step_time: 300")
#                                    yaml_lines.append("")
#
#                                    # SCHRITT 1.1: Replay Nummer setzen
#                                    replay_id_str = f"Rec\u200A{match_id}"
#                                    yaml_lines.append(f"  - name: \"Replay-ID setzen ({replay_id_str})\"")
#                                    yaml_lines.append(f"    actual: \"lambda: self.app.SMobjekt.set_replay_match('{replay_id_str}')\"")
#                                    yaml_lines.append(f"    expected: null")
#                                    yaml_lines.append(f"    step_time: 250")
#                                    yaml_lines.append("")            
#
#
#                                    # SCHRITT 1.2: Spielernamen aus der Highscore auslesen und setzen
#                                    sp1 = entry.get("spieler", "Spieler 1")
#                                    sp2 = entry.get("spieler2", "Spieler 2")
#                                    if sp2 is None: 
#                                        sp2 = "" # Verhindert, dass None als Text "None" gesetzt wird
#
#                                    yaml_lines.append(f"  - name: \"Spielernamen aus Highscore setzen\"")
#                                    # Mit der Mute-Taste (system_update_laeuft), damit kein (modifiziert) Tag entsteht!
#                                    yaml_lines.append(f"    actual: \"lambda: [setattr(self.app.SMobjekt, 'system_update_laeuft', True), self.app.SMobjekt.spieler.set('{sp1}'), self.app.SMobjekt.spieler2.set('{sp2}'), setattr(self.app.SMobjekt, 'system_update_laeuft', False)]\"")
#                                    yaml_lines.append(f"    expected: [null, null, null, null]")
#                                    yaml_lines.append(f"    step_time: 10")
#                                    yaml_lines.append("")
#
#
#
#                                    # SCHRITT 1.5: Dev-Override & Smart-Fast-Forward
#                                    vorb = entry.get("vorbereiten", 5)
#                                    lg   = entry.get("ladenGelb", 3)
#                                    #print("lg: "+str(lg))
#                                    
#                                    time_saved_ms = 0
#                                    first_shot_done = False # Wichtig für die Zeit-Korrektur später
#                                    
#                                    if "(dev)" in programm_name:
#                                        # DEV-Mode: Extreme Beschleunigung wie bisher
#                                        wdh = entry.get("wiederholungen", 2)
#                                        yaml_lines.append(f"  - name: \"Dev-Override: Fast-Forward (Werte erzwingen)\"")
#                                        yaml_lines.append(f"    actual: \"lambda: [self.app.SMobjekt.vorbereiten.set(1), self.app.SMobjekt.ladenGelb.set(1), self.app.SMobjekt.wiederholungen.set({wdh})]\"")
#                                        yaml_lines.append(f"    expected: [null, null, null]")
#                                        yaml_lines.append(f"    step_time: 10")
#                                        yaml_lines.append("")
#                                    else:
#                                        # SMART-SPEEDUP für normale, echte Matches
#                                        # Wir deckeln die Zeiten auf maximal 3 Sekunden
#                                        #new_vorb = min(vorb, 3)
#                                        new_lg = min(lg, 3)
#                                        
#                                        # Berechnen, wie viele Sekunden wir der Realität klauen
#                                        #time_saved_s = (vorb - new_vorb) + (lg - new_lg)
#                                        time_saved_s =  (lg - new_lg)
#                                        time_saved_ms = int(time_saved_s * 1000)
#                                        #print(time_saved_ms)
#                                        
#                                        if time_saved_ms > 0:
#                                            yaml_lines.append(f"  - name: \"Smart-Override: Wartezeiten auf je max 3s reduziert\"")
#                                            #yaml_lines.append(f"    actual: \"lambda: [self.app.SMobjekt.vorbereiten.set({new_vorb}), self.app.SMobjekt.ladenGelb.set({new_lg})]\"")
#                                            #yaml_lines.append(f"    expected: [null, null]")
#                                            yaml_lines.append(f"    actual: \"lambda:  self.app.SMobjekt.ladenGelb.set({new_lg})\"")
#                                            yaml_lines.append(f"    expected: null")                                            
#                                            yaml_lines.append(f"    step_time: 10")
#                                            yaml_lines.append("")
#                                            
#                                    yaml_lines.append(f"  - name: \"Modifiziert-Tag entfernen\"")
#                                    yaml_lines.append("    actual: 'lambda: self.app.SMobjekt.remove_tag(self.app.SMobjekt.Tag.MODIFIZIERT)'")
#                                    yaml_lines.append(f"    expected:")
#                                    yaml_lines.append(f"    step_time: 10")       
#                                    yaml_lines.append("")                                    

                                    # SCHRITT 2: Countdown starten
                                    yaml_lines.append(f"  - name: \"Countdown starten\"")
                                    yaml_lines.append(f"    action: \"start_countdown\"")
                                    yaml_lines.append(f"    step_time: 500")
                                    yaml_lines.append("")

                                    # --- MATCH TIMELINE VERARBEITEN ---
                                    current_cycle = -1  # Tracker für den Zykluswechsel
                                    
                                    for ev in timeline:
                                        action_type = ev.get('a', '')
                                        t = ev.get('t', 0.0)
                                        z = ev.get('z', -1) # Den aktuellen Zyklus aus dem Event holen
                                        
                                        
                                        # Nur Schüsse (Action) in den Robot-Test übernehmen
                                        if action_type == "shoot":
                                            # Zeitdifferenz in ms berechnen
                                            delta_ms = int(max(0, t - last_t) * 1000)
                                            last_t = t  # Update HIER, damit die Pausen zwischen den Schüssen exakt stimmen
                                            
                                            #Kommentar = "YAML-Export:"
                                            # --- NEU: Zeit-Korrektur für den allerersten Schuss JEDES Zyklus ---
                                            if z != current_cycle and time_saved_ms > 0:
                                                # Wir ziehen die gestrichene Wartezeit ab
                                                delta_ms = max(0, delta_ms - time_saved_ms)
                                                current_cycle = z  # Zyklus als "abgearbeitet" markieren
                                                #Kommentar+=(f" delta_ms {delta_ms} time_saved_ms {time_saved_ms}")
                                                #print(f"YAML-Export: RAPANTE")
                                            # -------------------------------------------------------------------

                                            # --- NEU: Den Puffer (Zeitschulden) abbauen ---
                                            if time_debt_ms > 0:
                                                # Wir können maximal so viel abbauen, wie wir Zeit bis zum Schuss haben
                                                abbau = min(delta_ms, time_debt_ms) 
                                                delta_ms = delta_ms - abbau         # Schuss vorverlegen
                                                time_debt_ms = time_debt_ms - abbau # Schulden reduzieren

                                            
                                            wert = ev.get('v', 0)
                                            original_state = ev.get("m")  # Holt "FEUER", "LADEN", "PLAYER1" etc. aus dem JSON
                                            
                                            # SCHRITT 3: Aktion (Der Schuss) komplett ausgeschrieben
                                            yaml_lines.append(f"  - name: \"Schuss auf {wert} (Zyklus {z})\"")
                                            yaml_lines.append(f"    action: \"shoot\"")
                                            yaml_lines.append(f"    wert: {wert}")
                                            yaml_lines.append(f"    step_time: {delta_ms}")
                                            yaml_lines.append("")
                                            #print(Kommentar)

                                            # SCHRITT 4: Assertions 

                                            # --- NEU: Die direkte Assertion danach (OHNE eval) ---
                                            yaml_lines.append(f"  - name: \"Prüfe Status nach Schuss auf {wert}\"")
                                            yaml_lines.append(f"    actual_attr: \"get_state\"")
                                            yaml_lines.append(f"    expected: '{original_state}'")
                                            yaml_lines.append(f"    step_time: 10")  # Nur 10ms warten
                                            yaml_lines.append("")
                                            time_debt_ms += 10
                                            

                                            # p_idx = ev.get('p', 0)
                                            # p_number = p_idx + 1
                                            # p_key = f"p{p_number}_"
                                            # punkte = ev.get(f"{p_key}pd", 0)
                                            # treffer = ev.get(f"{p_key}t", [])
                                            #
                                            # yaml_lines.append(f"  - name: \"Prüfe Punkte Spieler {p_number}\"")
                                            # yaml_lines.append(f"    actual: \"lambda: self.app.KSobjekt.players[{p_idx}].punkte_durchgang\"")
                                            # yaml_lines.append(f"    expected: {punkte}")
                                            # yaml_lines.append(f"    step_time: 50")
                                            # yaml_lines.append("")
                                            #
                                            # yaml_lines.append(f"  - name: \"Prüfe Trefferbild Spieler {p_number}\"")
                                            # yaml_lines.append(f"    actual: \"lambda: list(self.app.KSobjekt.players[{p_idx}].treffer)\"")
                                            # yaml_lines.append(f"    expected: {treffer}")
                                            # yaml_lines.append(f"    step_time: 0")
                                            # yaml_lines.append("")

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

        def play_replay():
            import subprocess
            import sys
            
            selected_items = tree.selection()
            if not selected_items:
                return
                
            for item in selected_items:
                values = tree.item(item, "values")
                
                for entry in self.highscore_manager.data:
                    if entry["timestamp"] == values[5]:
                        match_id = entry.get("match_id")
                        if match_id:
                            # Wir suchen die YAML-Datei im replays-Ordner
                            yaml_filename = os.path.join("savegames", "replays", f"REPLAY_MATCH{match_id:06d}.yaml")
                            
                            if os.path.exists(yaml_filename):
                                print(f"Starte Roboter für {yaml_filename}...")
                                # Test-Skript als eigenen Prozess starten!
                                # sys.executable stellt sicher, dass exakt dieselbe Python-Version genutzt wird
                                subprocess.Popen([sys.executable, "tests/test_ReplayRobot.py", yaml_filename])
                            else:
                                from tkinter import messagebox
                                messagebox.showwarning("Fehlendes Replay", 
                                    f"Es wurde noch kein YAML für Match {match_id} exportiert.\n"
                                    "Bitte klicke zuerst auf 'Export Replay'.")
                        break


 
        def on_press(event):
            global press_timer
            press_timer = tree.after(750, show_context_menu, event)  # 1000 ms = 1 Sekunde Halten
        
        def on_release(event):
            global press_timer
            if press_timer:
                tree.after_cancel(press_timer)  # Wenn losgelassen wird, die Timer-Aktion abbrechen
        
        press_timer = None     
        
        # Maus binden für das Kontextmenü
        tree.bind("<ButtonPress-1>", on_press)  # Wenn gedrückt wird
        tree.bind("<ButtonRelease-1>", on_release)  # Wenn losgelassen wird        
        tree.bind("<Button-3>", show_context_menu)
        
        # I und ENTF binden
        tree.bind("<Delete>", lambda event: delete_selected_entries())
        tree.bind("<i>", lambda event: show_selected_entries())
        
        # Dropdown-Menü-Aktion binden
        self.mode_dropdown.bind("<<ComboboxSelected>>", lambda event: update_highscores())
    
        # Highscores initial anzeigen
        update_highscores()
    
    def save_score(self):#, punkte_durchgang, speedpunkte_durchgang, gesamtpunkte):
        SD = self.SDeluebs
        highscore_entry = {
            "spieler": SD.SMobjekt.spieler.get(),
            "spieler2": SD.SMobjekt.spieler2.get() if SD.SMobjekt.gegner_modus.get() == 1 else None,
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
        #for entry in self.highscore_manager.data:
        #    print(entry)

    def save_match(self, match_timeline, highscore_entry):
        """Speichert den Event-Log zusammen mit den Metadaten"""
        try:
            # Match-ID frühzeitig auslesen (für Dateinamen und Print-Ausgabe)
            match_id = self.SDeluebs.SMobjekt.match_id
            # Event-Log als separate Datei speichern (nur wenn Events existieren)
            if match_timeline:
                os.makedirs(os.path.join("savegames", "logs"), exist_ok=True)
                log_dateiname = os.path.join("savegames", "logs", f"MATCH{match_id:06d}.json")
                # --- NEU: Die "Zwei-Zimmer-Wohnung" (Wrapper) bauen ---
                match_data = {
                    "metadata": highscore_entry,
                    "timeline": match_timeline
                }
                # 1. JSON als formatierten String erzeugen (jetzt mit match_data!)
                json_str = json.dumps(match_data, indent=2)
                # 2. Hilfsfunktion für den Regex-Ersetzer
                def collapse_arrays(match):
                    # Alle Zeilenumbrüche und doppelten Leerzeichen in der Liste entfernen
                    collapsed = re.sub(r'\s+', ' ', match.group(0))
                    # Optik verbessern: "[ 0, -1 ]" -> "[0, -1]"
                    return collapsed.replace('[ ', '[').replace(' ]', ']')
                # 3. Sucht alle Listen [...], die nur aus Zahlen, Kommas, Minus und Punkten bestehen
                json_str = re.sub(r'\[[\s\d\.,\-]*\]', collapse_arrays, json_str)
                # 4. Den optimierten String in die Datei schreiben
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
