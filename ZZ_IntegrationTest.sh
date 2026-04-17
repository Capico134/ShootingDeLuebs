#!/bin/bash
# Wechselt ins Verzeichnis des Scripts
cd "$(dirname "$0")"

# Führt die Tests aus
python3 -m unittest discover -s tests

# Wartet auf Tastendruck (ähnlich wie pause)
read -p "Drücke [Enter], um das Fenster zu schließen..."