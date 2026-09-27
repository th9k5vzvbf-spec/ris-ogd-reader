# RIS-OGD-Reader – Einrichtungsstatus

Stand: 27. September 2026, nach dem erfolgreichen Kontrolllauf

- Gerichtsauswahl: ausschließlich OGH, VwGH und VfGH.
- Programmprüfung: 19 automatisierte Tests erfolgreich, lokal und auf GitHub.
- Live-Prüfung: GitHub-Actions-Lauf vom 27. September 2026 erfolgreich abgeschlossen; Status `technical_queries_complete`, keine verbleibenden Abruffehler.
- Kontrolllauf: https://github.com/th9k5vzvbf-spec/ris-ogd-reader/actions/runs/36348917693
- Ergebnis: 536 eindeutige Dokumentkandidaten. OGH-Sammelabfrage: 150 Dokumente; VwGH-History: 314 Dokumente; VfGH-History: 72 Dokumente. Alle 21 Stichwortabfragen und alle drei Sammelabfragen wurden vollständig paginiert.
- Dokumentlinks: Bei allen 536 Kandidaten sind Original- und HTML-Links vorhanden.
- Behobene Probleme: Antwortfrist von 35 auf 60 Sekunden erhöht; höchstens zwei Wiederholungen mit 5 bzw. 15 Sekunden Wartezeit bei vorübergehenden Fehlern; offizielle Dokumentdomain `ogd.ris.bka.gv.at` zugelassen. Der Kontrolllauf fing erneut aufgetretene Zeitüberschreitungen durch Wiederholungen auf.
- Betrieb: sonntags um 20:15 UTC sowie manuell; API-Anfragen nacheinander mit mindestens 2,2 Sekunden Pause nach jeder Antwort. Höchstens zwei Seiten je Stichwort und 35 Seiten je Sammelabfrage.
- Ergebnisdatei: https://raw.githubusercontent.com/th9k5vzvbf-spec/ris-ogd-reader/main/data/latest.json

Der technische Erfolg belegt die vollständige Verarbeitung der vorgesehenen Abfragen dieses Laufs. Die Kandidaten sind noch inhaltlich zu prüfen. Änderungen an schon früher veröffentlichten OGH-Dokumenten werden weiterhin nicht lückenlos erfasst; eine juristische Vollständigkeitsfeststellung ist damit nicht verbunden.
