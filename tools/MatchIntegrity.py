import os
import sys
import json
import shutil
import hashlib
import argparse
from datetime import datetime

HIGHSCORE_PATH = os.path.join("savegames", "highscore.json")
LOGS_DIR = os.path.join("savegames", "logs")
HASH_KEY = "match_sha256"


def compute_sha256(filepath):
    """Berechnet den SHA256-Hash einer Datei schnell und speicherschonend."""
    with open(filepath, "rb") as f:
        if hasattr(hashlib, "file_digest"):
            return hashlib.file_digest(f, "sha256").hexdigest()
        h = hashlib.sha256()
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
        return h.hexdigest()


def analyze_integrity(highscore_path=HIGHSCORE_PATH, logs_dir=LOGS_DIR):
    """
    Prüft die Konsistenz zwischen highscore.json und savegames/logs/MATCH*.json (100% Read-Only).
    """
    res = {
        "valid": [],           # ✅ Hash stimmt überein
        "missing_hash": [],    # 🔵 Hash fehlt noch in highscore.json (MATCH-Datei ist aber da)
        "mismatch": [],        # ❌ Hash-Konflikt (MATCH-Datei verändert oder korrupt)
        "missing_file": [],    # ⚠️ In highscore.json gelistet, aber MATCH-Datei fehlt lokal
        "orphaned_files": [],  # 👻 MATCH-Datei liegt im Ordner, steht aber nicht in highscore.json
        "json_error": None,
        "total_json": 0,
        "total_files": 0
    }

    # 1. highscore.json lesen
    if not os.path.exists(highscore_path):
        res["json_error"] = f"Datei nicht gefunden: {highscore_path}"
        highscore_data = []
    else:
        try:
            with open(highscore_path, "r", encoding="utf-8") as f:
                highscore_data = json.load(f)
        except Exception as e:
            res["json_error"] = f"Fehler beim Lesen der {highscore_path}: {e}"
            return res

    res["total_json"] = len(highscore_data)

    # 2. Alle vorhandenen MATCH*.json im Ordner erfassen
    existing_files = {}
    if os.path.exists(logs_dir):
        for fname in sorted(os.listdir(logs_dir)):
            if fname.upper().startswith("MATCH") and fname.lower().endswith(".json"):
                full_path = os.path.join(logs_dir, fname)
                if os.path.isfile(full_path):
                    existing_files[fname] = full_path

    res["total_files"] = len(existing_files)
    referenced_files = set()

    # 3. Jeden Eintrag der highscore.json abgleichen
    for idx, entry in enumerate(highscore_data):
        match_id = entry.get("match_id")
        if match_id is None:
            continue
        try:
            mid_int = int(match_id)
            file_name = f"MATCH{mid_int:06d}.json"
        except ValueError:
            continue

        referenced_files.add(file_name)
        file_path = existing_files.get(file_name)
        recorded_hash = entry.get(HASH_KEY)

        # Spieler & Punkte für die Anzeige formatieren
        sp1 = entry.get("spieler", "Unbekannt")
        sp2 = entry.get("spieler2")
        gegner = entry.get("gegner_modus", 0) == 1
        spieler_str = f"{sp1} / {sp2}" if (gegner and sp2) else str(sp1)

        p1 = entry.get("gesamtpunkte", 0)
        p2 = entry.get("gesamtpunkte_pl2", 0)
        punkte_str = f"{p1} / {p2}" if gegner else str(p1)

        info = {
            "idx": idx,
            "match_id": mid_int,
            "file_name": file_name,
            "file_path": file_path,
            "spieler": spieler_str,
            "modus": entry.get("programm_name", "Unbekannt"),
            "timestamp": entry.get("timestamp", "-"),
            "punkte": punkte_str,
            "recorded_hash": recorded_hash,
            "actual_hash": None
        }

        if not file_path or not os.path.exists(file_path):
            res["missing_file"].append(info)
        else:
            try:
                actual_hash = compute_sha256(file_path)
                info["actual_hash"] = actual_hash
            except Exception as e:
                info["actual_hash"] = f"READ_ERROR: {e}"
                res["mismatch"].append(info)
                continue

            if not recorded_hash:
                res["missing_hash"].append(info)
            elif recorded_hash.lower() == actual_hash.lower():
                res["valid"].append(info)
            else:
                res["mismatch"].append(info)

    # 4. Verwaiste MATCH*.json ermitteln (im Ordner vorhanden, aber nicht in highscore.json)
    for file_name, file_path in existing_files.items():
        if file_name not in referenced_files:
            size_kb = os.path.getsize(file_path) / 1024.0
            mtime = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%d.%m.%y %H:%M:%S")
            res["orphaned_files"].append({
                "file_name": file_name,
                "file_path": file_path,
                "size_kb": size_kb,
                "mtime": mtime
            })

    return res


def backfill_missing_hashes(highscore_path=HIGHSCORE_PATH, logs_dir=LOGS_DIR):
    """
    Ergänzt NUR fehlende 'match_sha256' in der highscore.json.
    Erstellt vorher ein Backup und speichert atomar über eine .tmp-Datei.
    Bereits vorhandene Hashes werden NIEMALS überschrieben!
    """
    if not os.path.exists(highscore_path):
        return 0, f"Datei nicht gefunden: {highscore_path}"

    try:
        with open(highscore_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return 0, f"Fehler beim Lesen der highscore.json: {e}"

    updated_count = 0
    for entry in data:
        if entry.get(HASH_KEY):
            continue  # Bereits vorhandener Hash wird niemals angefasst!

        match_id = entry.get("match_id")
        if match_id is None:
            continue
        try:
            file_name = f"MATCH{int(match_id):06d}.json"
        except ValueError:
            continue

        file_path = os.path.join(logs_dir, file_name)
        if os.path.isfile(file_path):
            entry[HASH_KEY] = compute_sha256(file_path)
            updated_count += 1

    if updated_count > 0:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = highscore_path.replace(".json", f"_backup_vor_backfill_{ts}.json")
        shutil.copy2(highscore_path, backup_path)

        temp_file = highscore_path + ".tmp"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            os.replace(temp_file, highscore_path)
            return updated_count, f"{updated_count} Hash-Werte erfolgreich nachgetragen!\nBackup erstellt: {os.path.basename(backup_path)}"
        except Exception as e:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    pass
            return 0, f"Kritischer Fehler beim Speichern: {e}"

    return 0, "Keine fehlenden Hashes zum Nachtragen gefunden."


def format_report(res):
    """Formatiert das Analyse-Ergebnis als sauberen Monospace-Bericht."""
    lines = []
    lines.append("=" * 120)
    lines.append(f"Infos:")
    lines.append(f"python tools/MatchIntegrity.py --backfill: Trägt fehlende Einträge nach")
    lines.append(f"python tools/MatchIntegrity.py --gui: Öffnet direkt das grafische Diagnose-Fenster")
    lines.append("=" * 120)
    lines.append(f"🔍 SHOOTING DELÜBS - MATCH-INTEGRITÄTS-BERICHT  (Stand: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')})")
    lines.append("=" * 120)

    if res.get("json_error"):
        lines.append(f"\n❌ KRITISCHER FEHLER: {res['json_error']}\n")
        return "\n".join(lines)

    lines.append(f"Einträge in highscore.json     : {res['total_json']}")
    lines.append(f"MATCH-JSONs in savegames/logs/ : {res['total_files']}")
    lines.append("-" * 120)
    lines.append(f"  ✅ Synchron & Valide (Hash stimmt exakt)            : {len(res['valid']):>4}")
    lines.append(f"  🔵 Hash fehlt noch in highscore.json (Backfill)     : {len(res['missing_hash']):>4}")
    lines.append(f"  ❌ HASH-KONFLIKT (MATCH-JSON verändert / korrupt!)  : {len(res['mismatch']):>4}")
    lines.append(f"  ⚠️ MATCH-JSON fehlt lokal (In Highscore, Datei weg) : {len(res['missing_file']):>4}")
    lines.append(f"  👻 Verwaiste MATCH-JSONs (Im Ordner, nicht gelistet): {len(res['orphaned_files']):>4}")
    lines.append("=" * 120)

    # 1. ❌ HASH-KONFLIKTE
    if res["mismatch"]:
        lines.append("\n❌ [ROT] HASH-KONFLIKTE (Lokale MATCH-JSON weicht von highscore.json ab!):")
        lines.append("-" * 120)
        for m in res["mismatch"]:
            lines.append(f"  • {m['file_name']} | {m['timestamp']:<17} | {m['spieler']:<22} | {m['modus']:<20} | Pkt: {m['punkte']}")
            lines.append(f"      Soll-Hash (Highscore): {m['recorded_hash']}")
            lines.append(f"      Ist-Hash  (Log-JSON) : {m['actual_hash']}")

    # 2. ⚠️ FEHLENDE DATEIEN
    if res["missing_file"]:
        lines.append("\n⚠️ [GELB] FEHLENDE MATCH-DATEIEN (In highscore.json eingetragen, aber Datei fehlt in savegames/logs/):")
        lines.append("-" * 120)
        for m in res["missing_file"]:
            h_info = f"Hash: {m['recorded_hash'][:12]}..." if m["recorded_hash"] else "Kein Hash"
            lines.append(f"  • {m['file_name']} | {m['timestamp']:<17} | {m['spieler']:<22} | {m['modus']:<20} | Pkt: {m['punkte']:<10} | ({h_info})")

    # 3. 👻 VERWAISTE DATEIEN
    if res["orphaned_files"]:
        lines.append("\n👻 [GELB] VERWAISTE MATCH-DATEIEN (Liegen in savegames/logs/, existieren aber NICHT in highscore.json):")
        lines.append("-" * 120)
        for o in res["orphaned_files"]:
            lines.append(f"  • {o['file_name']} | Geändert: {o['mtime']:<17} | Größe: {o['size_kb']:>6.1f} KB  (z.B. in Highscore gelöscht)")

    # 4. 🔵 FEHLENDE HASHES
    if res["missing_hash"]:
        lines.append("\n🔵 [BLAU] HASH FEHLT NOCH IN HIGHSCORE.JSON (MATCH-Datei ist da, Hash kann nachgetragen werden):")
        lines.append("-" * 120)
        for m in res["missing_hash"]:
            lines.append(f"  • {m['file_name']} | {m['timestamp']:<17} | {m['spieler']:<22} | Pkt: {m['punkte']:<10} | SHA256: {m['actual_hash'][:16]}...")

    # 5. ✅ VALIDE MATCHES
    if res["valid"]:
        lines.append(f"\n✅ [GRÜN] SYNCHRONE & VALIDE MATCHES ({len(res['valid'])} Stück):")
        lines.append("-" * 120)
        for m in res["valid"]:
            lines.append(f"  • {m['file_name']} | {m['timestamp']:<17} | {m['spieler']:<22} | Pkt: {m['punkte']:<10} | SHA256: {m['actual_hash'][:16]}... OK")

    lines.append("\n" + "=" * 120)
    return "\n".join(lines)


def start_ui(parent_root=None):
    """Öffnet das grafische Diagnose-Fenster (auch standalone über --gui nutzbar)."""
    import tkinter as tk
    from tkinter import messagebox

    standalone = (parent_root is None)
    win = tk.Tk() if standalone else tk.Toplevel(parent_root)
    win.title("🔍 Shooting DeLübs - Match-Integrität & Hash-Abgleich")

    sf = win.winfo_fpixels('1i') / 96.0
    w, h = int(1280 * sf), int(720 * sf)
    win.geometry(f"{w}x{h}")
    win.lift()
    win.focus_force()

    btn_frame = tk.Frame(win)
    btn_frame.pack(fill=tk.X, padx=10, pady=6)

    txt_frame = tk.Frame(win)
    txt_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    scrollbar = tk.Scrollbar(txt_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    txt = tk.Text(txt_frame, font=("Courier", 11), bg="#1e1e1e", fg="#00ff00",
                  padx=10, pady=10, yscrollcommand=scrollbar.set)
    txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=txt.yview)

    def copy_to_clipboard():
        full_log = txt.get("1.0", tk.END)
        win.clipboard_clear()
        win.clipboard_append(full_log)
        messagebox.showinfo("Kopiert", "Der Integritäts-Bericht wurde in die Zwischenablage kopiert!", parent=win)

    tk.Button(btn_frame, text="📋 In Zwischenablage kopieren", command=copy_to_clipboard,
              bg="#3498db", fg="white", font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=(0, 10))

    btn_refresh = tk.Button(btn_frame, text="🔄 Neu prüfen", bg="#34495e", fg="white", font=("Arial", 11, "bold"))
    btn_refresh.pack(side=tk.LEFT, padx=(0, 10))

    btn_backfill = tk.Button(btn_frame, text="", bg="#e67e22", fg="white", font=("Arial", 11, "bold"))

    def run_check():
        txt.config(state=tk.NORMAL)
        txt.delete("1.0", tk.END)
        txt.insert(tk.END, "⏳ Prüfe SHA256-Prüfsummen aller MATCH-JSONs...\n")
        win.update()

        res = analyze_integrity()
        report = format_report(res)

        txt.delete("1.0", tk.END)
        txt.insert(tk.END, report)
        txt.config(state=tk.DISABLED)

        missing_count = len(res.get("missing_hash", []))
        if missing_count > 0:
            btn_backfill.config(
                text=f"🔧 Fehlende Hashes in highscore.json nachtragen ({missing_count} Stück)",
                command=lambda: on_backfill(missing_count)
            )
            btn_backfill.pack(side=tk.LEFT, padx=(10, 0))
        else:
            btn_backfill.pack_forget()

    def on_backfill(count):
        ask = messagebox.askyesno(
            "Fehlende Hashes nachtragen (Backfill)",
            f"Möchtest du für {count} bestehende Match-Logs, denen noch ein Hash-Eintrag fehlt, "
            f"jetzt den SHA256-Wert in der 'highscore.json' ergänzen?\n\n"
            f"• Bereits vorhandene Hashes werden NIEMALS überschrieben.\n"
            f"• Es wird automatisch ein Backup der highscore.json angelegt.\n"
            f"• Das Speichern erfolgt absturzsicher über eine .tmp-Datei.",
            parent=win
        )
        if not ask:
            return
        updated, msg = backfill_missing_hashes()
        if updated > 0:
            messagebox.showinfo("Backfill abgeschlossen", msg, parent=win)
            run_check()
        else:
            messagebox.showwarning("Hinweis", msg, parent=win)

    btn_refresh.config(command=run_check)
    win.after(50, run_check)

    if standalone:
        win.mainloop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Match-Integrität & SHA256-Prüfwerkzeug für Shooting DeLübs")
    parser.add_argument("--backfill", action="store_true",
                        help="Trägt fehlende SHA256-Hashes in der highscore.json nach (mit Backup & .tmp-Schutz)")
    parser.add_argument("--gui", action="store_true",
                        help="Startet das grafische Diagnose-Fenster")
    args = parser.parse_args()

    if args.gui:
        start_ui()
    else:
        if args.backfill:
            count, message = backfill_missing_hashes()
            print(message)
            print()

        result = analyze_integrity()
        print(format_report(result))