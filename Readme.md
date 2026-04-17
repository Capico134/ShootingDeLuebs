# 🎯 Shooting DeLübs
Das interaktive computergestütze Zielsystem für Sportschützen zum Reaktions-Training.

*Shooting DeLübs* entstand als Vater-Sohn-Projekt in der Weihnachtszeit 2024. Was beim Weihnachtsessen mit einem Raspberry Pi 5 und einer Keksdose als Sound-Quelle begann, ist heute eine ausgereifte Trainings-Suite für moderne Schießanlagen (Dreh- und Klappscheiben).

## 📺 Media & Story
Folge dem Projekt auf YouTube für Shorts über neue Funktionen und Dev-Logs. Hinterlasst auch gerne einen Kommentar in den Videos oder auf der Homepage!
* 🎥 **YouTube-Shorts:** [(https://www.youtube.com/@DeLuebs)]
* ℹ️ **Homepage:** [https://DeLuebs.de/]

## 🛠️ Hardware-Stack
Die Anlage ist modular aufgebaut und nutzt robuste Komponenten für den rauen Schießstand-Alltag:
* **Hardware-Schnittstelle:** Sunfounder Robot Hat, der die sichere Ansteuerung der Servos und LEDs übernimmt.
* **Mechanik:** AZDelivery 5 x MG996R Micro Digital Servo Motor mit Metallgetriebe für die Drehscheiben.
* **Eingabe & Feedback:** EG STARTS USB-Encoder und Arcade-Buttons mit LED.
* **Beleuchtung:** PWM-gesteuerte Schaltmodule für blitzschnelle Klappscheiben-LEDs.

## 🔬 High-Precision Engine
In diesem Sport entscheiden Hundertstelsekunden. 
* **Latenz-Korrektur:** Das System gleicht Verzögerungen durch das Betriebssystem (OS-Scheduling) auf die Millisekunde genau aus.
* **Hardware-Mock:** Entwickle bequem am PC (Windows) – der integrierte Mock simuliert die Hardware-Schnittstellen (`robot_hat`) fehlerfrei.

## 🚀 Installation & Start
* **Entwicklung am PC:** Repo klonen -> `pip install -r requirements.txt` -> `python ShootingDeLuebs.py` starten.
* **Raspberry Pi 5:** `./ZZ_IntegrationTest.sh` ausführen, um die Latenz-Engine zu prüfen.

## 📚 Dokumentation & Details
Tauche tiefer in die Mechaniken und Hintergründe ein:
* 🎮 [**GameModi.md**](./GameModi.md) – Alle Spielregeln, Duell-Modi und Modifikatoren (Wechsel, Känguru, Jäger, Survival) im Detail.
* 📢 [**Credits.md**](./Credits.md) – Audio-Lizenzen und die Story der legendären "Keksdosen"-Aufnahme.

## 🤝 Mitwirken & Support
* **Fehler & Neue Ideen:** Etwas klappt nicht oder du wünschst dir Unterstützung für andere Hardware (z.B. andere Motor-Hats)? Eröffne einfach ein GitHub Issue.
* **Pull Requests:** Gerne gesehen! Bitte stelle vorab sicher, dass der Latenz-Test (./ZZ_IntegrationTest.sh) fehlerfrei durchläuft.

## ⚖️ Lizenz & Nutzungsrechte
Dieses Projekt ist ein Herzensprojekt und lizenziert unter **[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.de)**. Weitere Details und meine persönlichen Anmerkungen zur Nutzung findest du in der Datei [**LICENSE.md**](./LICENSE.md).

**Was mir wichtig ist:**
* ✅ **Privat & Verein:** Ich habe das System für Freunde, Familie und meinen Schützenverein gebaut. Ihr dürft es sehr gerne nachbauen, verbessern und für euer Training nutzen!
* ❌ **Gewerbliche Nutzung:** Da extrem viel Freizeit und Herzblut in der Entwicklung steckt, möchte ich nicht, dass Firmen mein System ohne Rücksprache kommerziell vermarkten oder damit Profit erzielen.

**Du hast eine gewerbliche Idee?**
Falls du Shooting DeLübs über den privaten Bereich hinaus nutzen möchtest (z.B. Verkauf von Anlagen oder kommerzielle Events), melde dich einfach bei mir. Wir finden sicher eine faire Lösung. Kontaktiere mich dazu am besten über ein GitHub-Issue oder meine Homepage.

