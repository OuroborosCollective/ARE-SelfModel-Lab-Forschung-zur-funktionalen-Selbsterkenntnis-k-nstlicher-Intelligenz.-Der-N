# Ein-Stunden-Langzeitversuch: Lexikon-Watchdog mit verlangsamtem Synapsenverlust

**Status:** Implementierung und Kurztest; der einstündige GitHub-Lauf ist nur dann belegt, wenn der `endurance-hour`-Job tatsächlich beendet wurde und die Artefakte ausgelesen wurden.

## Fragestellung und Kontrollgruppen

Die bisherige 10.000-Episoden-Messung war eine extrem schnelle Wiederholung einer **festen** deutschsprachigen Spielaufgabe: acht selbst erstellte Wörterseiten mit insgesamt 48 Wörtern, keine Duden-Kopie und **kein** trainiertes Sprachmodell. Vier identisch initialisierte Varianten messen mit/ohne extern programmierte Lernregel und mit/ohne kumulativen Gewichtsverlust. Ein „Reset“ ist ein logischer Episoden-Neustart, **kein OS-Kill**. `learning_rule_externally_specified=true` ist kein Hinweis auf spontan entstandene Strategie.

Die Dauer des neuen Laufs beträgt **3.600 Sekunden echter Wall-Clock-Zeit**. Es gibt **keine `sleep`-Drosselung**. Durchsatz wird gemessen statt angenommen. Beim ersten Scheitern wird weiterhin ein Gewichtsparameter dauerhaft deaktiviert; danach nur noch bei jedem 250.000. Scheitern in dem jeweiligen Schädigungsarm. Damit bleiben Verluste über eine Stunde sichtbar, statt sofort alle 256 Parameter zu entfernen. Korrekte Episoden bewirken **keine** Bestrafung.

Der Datenverlust innerhalb einer Episode bleibt zur Vergleichbarkeit **unverändert** (`preempt`, vor der nächsten Aktion); die Wörterseiten werden zu Beginn jeder Episode erneut zur Verfügung gestellt. Es gibt **keine** geheime, zukünftige Ablaufvorgabe an die Policy, wohl aber stets dieselbe feste Ablaufreihenfolge. Dieser Wiederholungseffekt ist ein bewusst untersuchter Confounder.

## Sicherheits- und Auditgrenzen

- Maximale Wall-Clock-Dauer: 4 Stunden; dieser Job nutzt 1 Stunde und hat ein separates GitHub-Joblimit von 75 Minuten.
- Sicherheitslimit: maximal 80 Millionen Episoden; wird es vor Ablauf der Zeit erreicht, ist die Studie **nicht** erfolgreich beendet, und der Prozess liefert Exit-Code 124.
- Ein Rechenthread, keine Internetzugriffe, kein Download von Sprachmodellen, keine Datenbankänderungen.
- Einträge im Fortschrittsprotokoll etwa alle **60 Sekunden**, kompakt und nach SHA-256 prüfbar; kein riesiges Millionenzeilen-Episodenlog.
- Alle vier Kontrollarme werden vorangetrieben; jeder hat eigene Gewichtszustände und Randomisierungsinstanz für die Unterbrechungen.
- Aussagen zu „Schmerz“, „Angst“, „Erwachen“ oder subjektivem Erleben sind aus diesem Experiment **nicht ableitbar**.

## Start auf GitHub Actions

Die Datei `.github/workflows/selfmodel-hour.yml` führt auf jedem passenden PR und Push zuerst einen kurzen Smoke-Test aus. Der echte Stundenlauf startet **nur bei einem Push auf den festgelegten Forschungsbranch**, dessen Commitnachricht die eindeutige Markierung `[hour-3600]` enthält; damit verhindern normale Folgecommits einen versehentlichen erneuten einstündigen Lauf.

Nach dem Lauf liefert GitHub Actions das Artefakt `are-selfmodel-hour-endurance-20261024` mit `receipt.json`, `stdout.json` und `progress.jsonl`; letzteres kann mit `progress_sha256` bytegenau abgeglichen werden. Während der Ausführung erscheinen Statuszeilen im GitHub-Joblog.

## Reproduktion lokal

Vom Repository-Root (Python-Standardbibliothek genügt):

```bash
python -m unittest discover -s research/selfmodel/tests -p 'test_longrun_watchdog.py' -v
python -m research.selfmodel.longrun_watchdog \
  --duration-seconds 3600 --max-episodes 80000000 \
  --damage-every-failures 250000 --progress-seconds 60 \
  --seed 17 --progress progress.jsonl --receipt receipt.json
```

Die beobachtete Trefferzahl ist abhängig von Rechner, CPU-Kontingent und Last. **Zeit ist die unabhängige Laufgrenze**, nicht eine vorab unterstellte Anzahl Episoden.
