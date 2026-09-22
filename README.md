# RIS-OGD-Reader

Ein lesender, auf **OGH, VwGH und VfGH** beschränkter Recherche-Zulieferer für den Österreichischen Bewertungsmonitor. Keine offizielle Anwendung des Bundeskanzleramts.

## Gerichtsauswahl und Recherchemethode

- **OGH:** Die RIS-Applikation `Justiz` wird mit `Gericht=OGH` abgefragt. Rechtssätze und Entscheidungstexte werden nach definierten Fachbegriffen durchsucht. Eine zusätzliche **OGH-gefilterte Suche nach allen in den letzten zwei Wochen neu veröffentlichten Dokumenten** findet auch Treffer ohne die definierten Suchbegriffe. Ergebnisse anderer Gerichte werden selbst bei einer fehlerhaften API-Antwort zurückgewiesen.
- **VwGH und VfGH:** Stichwortsuche in Rechtssätzen und Entscheidungstexten; zusätzlich History-Abfrage mit Veröffentlichungen bzw. Änderungen der letzten 14 Tage.
- **OLG, LG, BG und andere Gerichtsbarkeiten:** nicht Gegenstand des Readers.

**Wichtige Einschränkung:** Die RIS-History für die Applikation `Justiz` ist nicht nach `Gericht=OGH` eingeschränkt. Deshalb wird die appweite Justiz-History bewusst **nicht** abgerufen. Die stattdessen eingesetzte OGH-gefilterte Recherche erfasst neue Veröffentlichungen; Änderungen an bereits zuvor veröffentlichten OGH-Dokumenten sind damit **nicht lückenlos** abgedeckt. Auch bei erfolgreicher Abfrage ist keine juristische Vollständigkeitsfeststellung zulässig.

## Automatisierter Betrieb

GitHub Actions startet sonntags um 20:15 UTC und ist zusätzlich manuell auslösbar. Die Daten stehen unter
[**data/latest.json**](data/latest.json) beziehungsweise öffentlich unter
https://raw.githubusercontent.com/th9k5vzvbf-spec/ris-ogd-reader/main/data/latest.json.

Der öffentliche Raw-Link ist ohne GitHub Pages lesbar. Der nachgelagerte Bewertungsmonitor muss `generated_at_utc`, `status`, `court_scope`, die Anzahl der Rückgaben sowie alle Fehler und unvollständig paginierten Teilabfragen prüfen und jede relevante Entscheidung im Original-RIS inhaltlich verifizieren.

Die API-Aufrufe erfolgen nacheinander mit einem Mindestabstand von 2,2 Sekunden; höchstens zwei Trefferseiten je Stichwort und bis zu 35 Seiten für die drei breiteren Prüfschritte. Bei Fehlern bzw. unvollständiger Paginierung wird der Ergebnisstatus `incomplete` geschrieben und die GitHub Action als fehlgeschlagen angezeigt, statt einen Erfolg vorzutäuschen.

Programmtests lokal: `python -m unittest discover -s tests -v`.

## Quellen und Nutzungsbedingungen

Datenquelle: [RIS – Open Government Data](https://www.ris.bka.gv.at/UI/Ogd.aspx), Bundeskanzleramt Österreich, CC BY 4.0. [Dokumentation RIS OGD API v2.6](https://www.data.gv.at/katalog/dataset/0fb9ae1a-92cb-4ab8-a589-470c16d4fe21/resource/42070d46-01fe-4b36-803f-4af925290f59/download/dokumentation_ogd-ris_api.pdf).

Der Reader speichert ausschließlich öffentliche RIS-Fundstellen; keine Zugangsdaten, keine persönlichen Gutachten, keine privaten Dokumente. GitHub Actions ist kein Garant für minutengenaue Ausführung.
