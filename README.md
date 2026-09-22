# RIS-OGD-Reader

Automatisierte, ausschließlich lesende Suche in öffentlichen RIS-Judikaturdaten als Zulieferer für den **Österreichischen Bewertungsmonitor**.

**Status am 22.09.2026:** Implementierung vorhanden; 13 automatisierte Tests erfolgreich. Zwei echte RIS-Abrufe wurden ausgeführt. Beim zweiten Abruf war die Seitenbegrenzung auf 35 History-Seiten erhöht; die RIS-API lieferte jedoch wiederholte Zeitüberschreitungen. Der gespeicherte letzte Abruf ist daher korrekt als `incomplete` gekennzeichnet. Ein erfolgreicher vollständiger Live-Abruf ist noch nicht nachgewiesen.

## Ablauf

- Sonntag 20:15 Uhr UTC: GitHub Actions führt die Abfrage für Justiz, VwGH und VfGH aus.
- Suche nach einschlägigen Stichworten bei Rechtssätzen **und** Entscheidungstexten, beschränkt auf die jüngsten zwei Wochen im RIS.
- Zusätzliche RIS-History-Abfrage für denselben Zeitraum. Sie erfasst auch ältere Entscheidungen, die erst kürzlich ins RIS kamen, mit bis zu 35 Ergebnisseiten je Applikation (50 Dokumente pro Seite). Falls mehr Treffer vorliegen oder die RIS-API nicht antwortet, wird die Abfrage ausdrücklich als unvollständig gekennzeichnet.
- Ergebnisse sind **ungeprüfte Fundstellen**, keine automatisch bewerteten juristischen Aussagen.
- Die maschinenlesbare Ausgabe liegt nach dem ersten Lauf unter [data/latest.json](data/latest.json), extern abrufbar über https://raw.githubusercontent.com/th9k5vzvbf-spec/ris-ogd-reader/main/data/latest.json .
- Der österreichische Bewertungsmonitor soll ausschließlich Fundstellen nach eigener inhaltlicher Prüfung zitieren. Wenn der Status auf "incomplete" steht oder legal_completeness_claim falsch ist, darf er keine vollständige Judikaturprüfung behaupten.

## Betrieb und Sicherheit

- Nur die offizielle öffentliche OGD-API: https://data.bka.gv.at/ris/api/v2.6/
- Nur lesende GET-Aufrufe zu den festgelegten Endpunkten **Judikatur** und **History**. Keine frei wählbaren API-Ziele, keine Weiterleitungen, keine Datenbank, keine Uploads, keine Geheimnisse.
- Mindestens 2,2 Sekunden zwischen RIS-Aufrufen, keine parallelen RIS-Abfragen; maximal zwei Ergebnisseiten pro Stichwortabfrage und gesondert maximal 35 History-Seiten je Applikation (höchstens 1.750 Änderungsdatensätze).
- Kein externer Python-Paketbedarf. Tests: python -m unittest discover -s tests -v.
- Start per GitHub **Actions → RIS OGD weekly reader → Run workflow** oder automatisch am Sonntag.
- Ergebnis inklusive Fehlermeldungen wird auch bei unvollständiger Recherche gespeichert. Ein unvollständiger Lauf wird als fehlgeschlagene GitHub Action angezeigt.
- Eine öffentliche GitHub-Datei ist **keine geschützte Ablage**. Niemals personenbezogene Gutachten oder vertrauliche Informationen eintragen.

## Grenzen

Die Stichwortsuche garantiert keine Vollständigkeit und der Inhalt der Fundstellen wird nicht automatisch rechtlich bewertet. Bei zu vielen Treffern, inkompatiblen RIS-Antworten oder technischen Fehlern zeigt das JSON "incomplete". Die History-Suche ist zusätzlich ein technischer Änderungsnachweis, noch keine semantische Volltextprüfung aller RIS-Änderungen.

Die Uhrzeit geplanter GitHub-Actions-Läufe ist nicht minutengenau garantiert; die Abfrage findet deshalb vor dem Montagsmonitor statt. Der aktuelle JSON-Status ist über die oben verlinkte öffentliche GitHub-Raw-URL ohne GitHub Pages abrufbar. GitHub Pages ist derzeit nicht aktiviert und für diesen Datentransfer nicht erforderlich.

## Originalquelle / Attribution

RIS – Rechtsinformationssystem des Bundes, [Bundeskanzleramt](https://www.ris.bka.gv.at/), OGD-Daten unter [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.de). [Offizielle OGD-Information](https://www.ris.bka.gv.at/UI/Ogd.aspx), [API-Handbuch](https://www.data.gv.at/katalog/dataset/0fb9ae1a-92cb-4ab8-a589-470c16d4fe21/resource/42070d46-01fe-4b36-803f-4af925290f59/download/dokumentation_ogd-ris_api.pdf). Dies ist **kein offizieller RIS-Dienst**.
