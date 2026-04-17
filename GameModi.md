# 🎮 Spielmodi & Modifikatoren

*Shooting DeLübs* bietet weit mehr als nur eine Standard Drehscheibe oder Klappscheibe. Durch clevere Software-Logik wird aus einfacher Hardware ein hochkompetitives Spielsystem. Viele Modi nutzen die Variable `ScheibenServo`, um die Einstellungen individuell anzupassen.

## 🎲 Zufall-Modus (Reaktion)
Der absolute Klassiker für das schnelle, unvorhersehbare Reaktionstraining.
* **Drehscheibe:** Eine zufällige Anzahl von Zielen dreht sich blitzschnell in die Schussposition.
* **Klappscheibe:** Ziele leuchten zufällig auf.
* **Zufall+Gegner:** Ein asymmetrischer Stresstest. Die Ziele des linken Spielers leuchten dauerhaft, die des rechten Spielers blinken. Perfekt, für ein Match gegeneinander mit zufälligen Zielen.

## ⚔️ Gegner-Modus (Duell)
Ein kompetitiver Modus für zwei Schützen, bei dem Reaktionszeit und Taktik gleichermaßen zählen.
* **Ablauf:** Jeder Spieler erhält ein zufälliges Ziel. Die mittlere Scheibe fungiert als umkämpfte Zone (Bonus oder Penalty).
* **Taktik (Klappscheiben):** Spieler müssen erst ihre eigenen Flanken abräumen. Wer schneller ist, schaltet die begehrte Mitte frei. Zieht der Gegner jedoch rechtzeitig nach, wird die Mitte wieder neutralisiert. Ein ständiges Hin und Her!

## 🔄 Wechsel-/Reihen-Modus (Das Othello-Prinzip)
Ein strategisches Tauziehen, das an das Brettspiel Othello erinnert. Nichts für schwache Nerven!
* **Mechanik:** Getroffene Ziele wechseln die Farbe bzw. die Zugehörigkeit zum Gegner. 
* **Wertung:** Punkte werden nicht sofort vergeben, sondern erst am Ende eines kompletten Zyklus abgerechnet. 
* **Der Endspurt:** Im letzten Durchgang zählen alle Punkte doppelt. Ein scheinbar sicherer Sieg kann im letzten Moment komplett gedreht werden.
* **Rubberbanding** (den Gummiband-Effekt). Unser eingebauter Aufhol-Bonus misst nicht nur die Schuss-Leistung, sondern optimiert den "Duell-Spaß":
  * **Keine Resignation:** Wer hinten liegt, erhält vom System subtile Hilfe (z.B. durch Mehrfach-Wertungen bei Treffern). Er hat bis zum letzten Schuss eine reelle Chance auf den Sieg.
  * **Keine Sicherheit:** Der Führende kann seinen Vorsprung nicht einfach "verwalten". Ein 4:1-Vorsprung bedeutet nichts, wenn der Gegner durch die Gummiband-Mechanik aufholt. Der Stärkere muss bis zur letzten Millisekunde Vollgas geben.
  * **Pures Drama:** Es verhindert langweilige Start-Ziel-Siege und zwingt beide Spieler in eine absolute Nervenschlacht am Schießstand.

## 🎯 Jäger-Modus (Asymmetrisch)
Ein Spieler schlüpft in die Rolle des Jägers, der andere ist der Gejagte.
* **Regeln:** Der Jäger markiert mit seinem allerersten Treffer sein "Revier". Seine Aufgabe ist es nun, den Gejagten durch gezielte, schnelle Schüsse strategisch einzukreisen. Der Gejagte muss versuchen, durch ständige Positionswechsel über das vorgegebene Zeitlimit zu überleben.
* **Jäger**: Leuchtende Ziele
* **Gejagter**: Binkende Ziele
---

## 🦘 Känguru-Modus (Das flüchtige Ziel)
In diesem Modus ist das Ziel extrem agil und "flieht" vor dem Schützen.
* **Mechanik:** Bei einem Treffer verschwindet das Ziel sofort und springt unverzüglich an eine völlig neue, zufällige Position auf der Anlage.
* **Der absolute Favorit (Känguru + Gegner):** Da für 2-Spieler-Modi immer der "Gegner"-Button aktiv ist, lassen sich diese beiden kombinieren. Das Ergebnis ist das absolute Highlight der Anlage: Beide Spieler jagen gleichzeitig ihre rasant hüpfenden Ziele. Ein pures Reaktions-Chaos, das höchste Konzentration erfordert.


## 🔧 Modifikatoren & System-Optionen
Diese speziellen Parameter lassen sich über das System aktivieren, um das Training drastisch zu verändern und die Anlage exakt an eure Hardware anzupassen:

* 💀 **Survival-Modus:** Null Fehlertoleranz. Die Spieler erreichen die nächste Runde nur dann, wenn das vorgegebene Ziel innerhalb der knappen Zeit erreicht wurde. Erkennbar durch den "Win-Sound".
* ⏱️ **BuzzTick / Trick:** Ein Modifikator mit Doppelfunktion!
  * *Bei Klappscheiben (BuzzTick):* Akustischer Stress pur! In den letzten 4 Sekunden tickt eine laute Uhr unerbittlich herunter, um den mentalen Druck vor Ablauf der Zeit künstlich zu maximieren.
  * *Bei Drehscheiben (Trick):* Geisel-Simulation! Ziele drehen sich gelegentlich auf 180° statt 90° und dürfen nicht getroffen werden. Ein Fehlschuss! (Erfahrene Schützen erkennen den Trick oft schon am längeren Drehwinkel der Servos).
* 🔢 **Zählen:** Wenn deaktiviert, wird die aktuelle Runden-Nummer bei "Achtung" und "Feuer" auf dem Display versteckt. Es wird deutlich schwieriger abzuschätzen, wie lange der Zyklus noch geht – die Spannung steigt.
* 🔇 **Ton:** Aktiviert oder deaktiviert sämtliche Soundeffekte der Anlage.
* 💾 **Save / ServoOff:** Der zentrale Schalter für die Hardware-Logik.
  * *Aktiviert (Klappscheiben-Fokus):* Ergebnisse und Highscores werden gespeichert. Die Servos bewegen sich nicht.
  * *Deaktiviert (Drehscheiben-Fokus):* Keine Speicherung von Ergebnissen, dafür werden die physischen Drehscheiben-Servos angesteuert.