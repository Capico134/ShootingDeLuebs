import tkinter as tk
import json 
import numbers

def resolve_path(obj, path):
    parts = path.split(".")
    current = obj
    for part in parts:
        try:
            current = getattr(current, part)
        except AttributeError:
            print(f"[Fehler] Attribut '{part}' in Pfad '{path}' nicht gefunden.")
            return None
    # Automatisches .get() bei Tkinter-Variablen
    if hasattr(current, "get") and callable(current.get):
        try:
            return current.get()
        except Exception as e:
            print(f"[Fehler] .get() bei '{path}' fehlgeschlagen: {e}")
            return None
    return current
    
def export_attributes(obj, path_list):
    result = {}
    for path in path_list:
        value = resolve_path(obj, path)
        result[path] = value
    return result

def export_local_tk_vars(obj):
    result = {}
    for attr_name in dir(obj):
        if attr_name.startswith("_"):
            continue
        try:
            attr = getattr(obj, attr_name)
            if isinstance(attr, (tk.IntVar, tk.StringVar, tk.DoubleVar, tk.BooleanVar)):
                result[attr_name] = attr.get()
        except Exception as e:
            print(f"[Fehler] Zugriff auf '{attr_name}' fehlgeschlagen: {e}")
    return result
    
def save_to_json(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Fehler] Speichern in '{filename}' fehlgeschlagen: {e}")

def compare_with_json(obj, filename, path_list=None):
    with open(filename, "r", encoding="utf-8") as f:
        json_data = json.load(f)

    # Aktuelle Werte aus dem Objekt holen
    current_data = export_local_tk_vars(obj)

    diffs = {}

    # Wenn keine Pfade angegeben sind, vergleiche alles
    keys_to_check = path_list if path_list else json_data.keys()

    for key in keys_to_check:
        json_value = json_data.get(key)
        current_value = current_data.get(key)

        if json_value != current_value:
            diffs[key] = {
                "expected": json_value,
                "actual": current_value
            }
    return diffs
    
def compare_dicts_with_json(actual_dict, filename, keys=None):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            expected_dict = json.load(f)
    except Exception as e:
        print(f"[Fehler] Laden von '{filename}' fehlgeschlagen: {e}")
        return {}

    diffs = {}
    keys_to_check = keys if keys else expected_dict.keys()

    for key in keys_to_check:
        expected = expected_dict.get(key)
        actual = actual_dict.get(key)

        if isinstance(expected, dict) and isinstance(actual, dict):
            # Rekursiver Vergleich
            sub_diffs = compare_nested_dicts(expected, actual)
            if sub_diffs:
                diffs[key] = sub_diffs
        elif expected != actual:
            diffs[key] = {
                "expected": expected,
                "actual": actual
            }

    return diffs

def compare_nested_dicts(expected, actual, tolerance=0.02):
    diffs = {}
    all_keys = set(expected.keys()) | set(actual.keys())

    for key in all_keys:
        exp = expected.get(key)
        act = actual.get(key)

        # Rekursiver Vergleich bei verschachtelten Dicts
        if isinstance(exp, dict) and isinstance(act, dict):
            sub_diffs = compare_nested_dicts(exp, act, tolerance)
            if sub_diffs:
                diffs[key] = sub_diffs

        # Vergleich von Listen mit Floats
        elif isinstance(exp, list) and isinstance(act, list) and all(isinstance(x, numbers.Real) for x in exp + act):
            #print("compare_nested_dicts!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            if len(exp) != len(act):
                diffs[key] = {"expected": exp, "actual": act}
            else:
                sub_diffs = {}
                for i, (e, a) in enumerate(zip(exp, act)):
                    if abs(e - a) > tolerance:
                        print(f"FLOAT-Liste: i:{i} e:{e} a:{a}")
                        sub_diffs[i] = {"expected": e, "actual": a}
                if sub_diffs:
                    diffs[key] = sub_diffs

        # Vergleich von einzelnen Floats mit Toleranz
        elif isinstance(exp, float) and isinstance(act, float):
            if abs(exp - act) > tolerance:
                diffs[key] = {"expected": exp, "actual": act}

        # Standardvergleich für andere Typen
        elif exp != act:
            diffs[key] = {"expected": exp, "actual": act}

    return diffs