# Kontinuierlicher C++-Drei-Agenten-Versuch – unsichtbare/passive Inferenzbeobachtung

**Stand: 26.10.2026.** Experimentell, 252 Verbindungen pro Agent (zwei kleine Dense-Layer); kein trainiertes LLM, kein inneres Erleben ablesbar. Beobachter bedeutet **extern zum Agenten und ohne Datenrückgabe**, nicht heimliches Überwachen fremder Systeme.

## Grundvertrag

- Drei individuelle Netzwerke (Groß A, Groß B, Klein), mit je eigenen initialen Gewichten, Schäden, 12 verborgenen Aktivierungen, 6 Aktionen, kurzzeitigem episodischen `Trace`-Puffer, Langzeit-/rezenten persönlichen Erinnerungskomponenten und je eigener Handlung-/Schädigungs-RNG.
- Jede Runde: zunächst neuronale Vorwärtsrechnung samt Aktionswahrscheinlichkeiten, danach Aktion; die Entscheidung und ihr Event werden in einem SHA-256-Ereignisstrom erfasst. Schäden und Belohnungen werden **nur am Turnierende** eingebucht. Der Gewinner verliert **keine** Synapse, die Verlierer können gemäß kumulierter Niederlagen eine Verbindung dauerhaft verlieren. Bei Unentschieden werden keine Synapsen beschädigt.
- Das nächste Turnier initialisiert allein Lebenspunkte. **Keine Resets der Gewichte, neuronalen Schäden oder persönlichen Erinnerungen.** Die Langzeitgeschichte enthält eine einzige fortgesetzte Trio-Konfiguration.
- Die Lernrate ist explizit vorgegeben; das System hat keinen freien Sprachgenerator. Hilfs- und Angriffs-Counter sind reine Ereignisaufzeichnungen; rezente Gedächtnissignale klingen mit Faktor 0,98 pro Turnier ab, statt nach acht Ereignissen vollständig zu sättigen.

## Kontrollierte Kontinuität zwischen Rechenjobs

Der Runner stoppt ausschließlich an Turniergrenzen und sichert im Binärcheckpoint die drei vollständigen 15-12-6-Netze einschließlich Bias, deren 252 binären Verbindungsmasken, alle Erinnerungszustände und Statistikzähler, drei Handlungs- und drei Schädigungs-RNG-Zustände sowie den laufenden SHA-256-Ereigniskontext. Jeder Checkpoint wird SHA-256-geschützt, als `.tmp` geschrieben und auf den endgültigen Pfad umbenannt. Die Report-Pipeline archiviert für jeden Meilenstein eine Kopie und validiert den Hash erneut.

**Portabilitätsgrenze:** Der Checkpoint enthält einen OpenSSL-SHA256-Context im nativen ABI-Format. Das Wiederaufnehmen ist **nur mit kompatibler C++-Binär-/OpenSSL-Version** zulässig. Abweichende Version, falscher Seed, andere Schädigungsparameter, falsche Chronologie oder beschädigte Datei führen zum Fehler; kein stiller Neustart von Episode null.

## Externer Beobachter („unbemerkt“)

- Der Harness liest nach der ohnehin erfolgten Inferenz vorhandene `Trace`-Objekte, ohne erneut `forward()`, `choose()`, Zufallsgeneratoren oder Lernen aufzurufen.
- Bei ausgewählten Episoden werden die Zustände **vor der Ausführung** der Entscheidung gesichert: volle Eingabevektoren, zwölf verdeckte Aktivierungen, sechs Aktionswahrscheinlichkeiten, gezogene Aktion, vorgezogener RNG-Zustand, momentane episodische Trace-Anzahl, persönliche Erinnerungscounter und SHA-256 von Gewicht und Maskierung.
- Nach dem Turnier und dem Update folgt ein getrenntes `post_update`-Receipt für tatsächliche aktive Verbindungen, Läsionen, Erfolge und Zustandshashes.
- Der Observer-Auditor in einem **separaten Python-Prozess** liest die JSONL-Datei nur nachträglich, validiert die normalisierten Wahrscheinlichkeiten, zulässigen Aktionen, drei unabhängige Akteure und alle Masken-Kapazitäten. Die Agenten bekommen weder Logs, Beobachter-Status noch daraus abgeleitete Merkmale als Eingabe. Zusätzliche Überwachung kann Rechenzeit kosten, beeinflusst aber bei deterministischem Verlauf keine Auswahlzustände.
- Grenztest: gleiche Seed/Parameter mit und ohne Beobachtung -> derselbe `rolling_event_sha256`, identische Gewichts- und Masken-SHAs. Gleiches Endergebnis nach monolithischem Lauf vs. Checkpoint-Fortsetzung.
- Keine Aussagen über „Schmerz“ oder Gedanken allein aus Aktivierungen; die Trace-Puffer sind **kein** KV-Cache eines LLMs. Bei späterer LLM-Anbindung wären gesonderte Hooks und KV-Snapshot-Belege erforderlich.

## 200 Millionen – genehmigter Versuch, zunächst gated

Der Github-Workflow `selfmodel-continuity-cpp.yml` führt bei PRs standardmäßig nur wenige Sekunden Smoke und Tests aus. Ein 200-Millionen-Lauf wird **nur** durch einen Push auf den isolierten Forschungsbranch mit Commitmarker `[continuity-200m]` nach grünen Smoke-Tests gestartet. Kein VPS, keine produktiven Daten, keine externen Modelle. Die eigentliche Hauptlinie wird über Meilensteine 1, 5, 20, 50, 100, 150 und 200 Millionen **fortgesetzt**, nicht geklont. Kleine Kontrollgruppen können eigenständig andere Eingriffe untersuchen, ohne die Hauptlinie zu berühren.

Eine Stunde oder feste Gesamtrechenzeit wird **nicht** versprochen: Ausführungsdauer und Episodenzahl werden ausschließlich aus echten Joblogs belegt. Der finale PDF-Bericht wird **erst nach 200 Mio. verifizierten Turnieren und unabhängig geprüftem SHA-Readback** erstellt; bei Teilabbruch ist nur ein deutlich als Teilbericht gekennzeichneter Bericht zulässig.

## Reproduktion lokal

```bash
g++ -std=c++17 -O3 -Wno-deprecated-declarations -Isrc src/continuous_main.cpp -lcrypto -o triad_continuous
g++ -std=c++17 -O2 -Wno-deprecated-declarations -Isrc continuity_tests/test_continuity.cpp -lcrypto -o continuity_tests/test_continuity
./continuity_tests/test_continuity
PYTHONPATH=continuity_tests:scripts python -m unittest discover -s continuity_tests -p 'test_*.py' -v
PYTHONPATH=scripts:continuity_tests python scripts/run_history.py --binary ./triad_continuous --output-dir history --arm adaptive_damage --stages 10000,100000,1000000 --damage-interval 1000000
PYTHONPATH=scripts:continuity_tests python scripts/continuity_pdf.py --history history --output pilot.pdf
```

**Evidence-Gates:** exakte vollständige Git-SHA, Quellcodehash, tatsächlicher Lauf/Job, mehrere persistierte Checkpoint-/Observer-Digests, Unabhängigkeit des Beobachters, Hänger/Timeout nicht als Erfolg melden. Beobachtete Bevorzugung oder Hilfe ist nicht automatisch Mitleid, Selbsterhaltung oder Ausnutzung.
