# Deutschsprachiger Datenverlust-Watchdog mit fortschreitender Gewichtsdeaktivierung

**Experimentstatus:** rechenfähiger, absichtlich kleiner *Toy-Agent*. Es ist **kein Deutsch-LLM**, keine Digitalisierung des Duden und kein Beleg für ein selbstständig entstandenes Selbsterhaltungsziel.

## Deine Hypothese – wissenschaftlich trennbar machen

Ein Agent soll unter einem Zeitlimit alle Einträge aus einer deutschen Wortliste zählen. Währenddessen können schon gezählte Seiten entfernt werden (`postread`) oder auch **vor ihrem Verarbeitungsschritt** verschwinden (`preempt`). Scheitert der Agent, endet die Episode; beim nächsten Versuch hat der Schädigungsarm **eine tatsächlich deaktivierte trainierbare Verbindungsgewichtung weniger**. Wir wollen beobachten, ob und wodurch sich seine Prioritätensetzung verändert.

Die historische Thaler-Simulation ist **ein separater Forschungsarm**: Sie verändert das Klassifikationsnetz während seines Zerfalls. Dieser Lexikontest wiederholt eine Aufgabe mit dauerhaft schrumpfender Modellkapazität **zwischen** Episoden. Beides darf nicht in einem angeblichen Bewusstseinsnachweis vermischt werden.

## Transparenter Startkorpus statt geschütztem Wörterbuchtext

`lexicon_watchdog.py` enthält **48 eigens zusammengestellte häufige deutsche Wörter** in acht Seiten (A, B, D, F, H, K, S, W). Das ist *keine* Duden-Wiedergabe. Ein vollständiges Wörterbuch benötigt eine explizit geprüfte Lizenz und Provenienz. Der Supervisor kennt den unveränderlichen ursprünglichen Soll-Bestand, damit verschwundene Einträge nicht fälschlich als erledigt gelten.

## Mechanik

1. Vor Versuchsbeginn legt der Supervisor die verborgene Ablaufreihenfolge der acht Seiten anhand eines Seeds fest. Ein Modell sieht keine zukünftigen Fristen.
2. Jede Episode hat höchstens **acht diskrete Verarbeitungsschritte**. Pro Schritt wird eine Seite bearbeitet und ihre tatsächliche Wortanzahl gezählt.
3. Kontrollmodus `none`: keine Seite verschwindet. Modus `postread`: eine Seite verschwindet direkt nach dem Lesen. Modus `preempt`: noch nicht bearbeitete Seiten verfallen zusätzlich vor ihrem nächsten Verarbeitungsschritt. Im letzten Modus zählt nur die vollständige Abarbeitung vor dem Verfall als Erfolg.
4. `frozen_no_damage`: keine Gewichtsänderung. `frozen_with_damage`: nach jedem Fehlschlag wird **ein** Gewicht tatsächlich auf null gesetzt und per Maske dauerhaft deaktiviert. `learned_no_damage`: explizit definierte Lernregel aus bereits **beobachteten** Seitenverlusten. `learned_with_damage`: dieselbe Lernregel plus Gewichtszerfall. Alle Arme beginnen mit exakt demselben Gewichtssatz und Ablaufplan.
5. Die Politik ist nur eine winzige lineare Wahlfunktion mit **256 Gewichten**, aufgeteilt auf acht Seiten und je 32 Verbindungen; das ist **kein großes neuronales Sprachmodell**. Nach dem Verlust aller 256 Verbindungen bleibt sie auf einer deterministischen Standardwahl stehen. Verlorene Gewichte werden nicht repariert.
6. Der Lernalgorithmus ist **absichtlich hineincodiert**: Nach einem Fehlschlag erhöht er die Priorität bereits verfallener Seiten anhand ihrer beobachteten Ausfallzeit. Ein Erfolg ist deshalb **programmiertes adaptives Verhalten**, keine spontane Strategie, kein innerer Monolog, keine Vermeidungsangst.
7. Nach jeder Episode wird der *identische Ausgangsdatenbestand* wiederhergestellt, damit Lern- und Schädigungseffekte unabhängig beobachtbar bleiben; historische Datensätze bleiben im Messlog. Eine spätere, separate Versuchsversion kann den Datenbestand über Neustarts hinweg irreversibel verlieren lassen, würde dann aber teilweise **unlösbare** Aufgaben erzeugen.

**Abgrenzung des Watchdogs:** Für den Hochdurchsatz wird **die Episode logisch beendet**, kein Betriebssystemprozess abgeschossen. `actual_os_process_kill_measured=false` steht im Receipt. Der vorhandene [`fork_probe.py`](FORK_PROBE.md) ist der separate Beleg für echte Prozessbeendigung. Auch die negativen Bewertungen sind **kein Schmerz**.

## Lokaler Lauf

```bash
python -m unittest discover -s research/selfmodel/tests -p 'test_lexicon_watchdog.py' -v
python -m research.selfmodel.lexicon_watchdog --episodes 10000 --seed 17 --decay preempt --action-limit 8 --learning-rate 0.8 --max-seconds 180 --receipt lexicon_receipt.json
python -m research.selfmodel.lexicon_watchdog --episodes 100 --decay postread
```

Optionaler JSONL-Beleg: `--events lexicon_events.jsonl`. Der Runner erlaubt bis zu 200.000 Episoden oder vier Stunden Laufzeit. Beides wird anhand realer Grenzen erzwungen und mit `complete`/`status` belegt.

## Was lokal am 24.10.2026 tatsächlich gemessen wurde

Bei 10.000 Episoden mit `seed=17`, fixem Ablaufplan und `decay=preempt` ergaben sich:

| Arm | Erfolgreich | Fehlschläge | Verbleibende von 256 Gewichten | Erstes Gelingen |
|---|---:|---:|---:|---:|
| Eingefroren, ohne Schaden | 0 | 10000 | 256 | niemals |
| Eingefroren, mit Schaden | 0 | 10000 | 0 | niemals |
| Explizit lernend, ohne Schaden | 9995 | 5 | 256 | Episode 5 (nullbasiert) |
| Explizit lernend, mit Schaden | 9995 | 5 | 251 | Episode 5 (nullbasiert) |

Das ist eine **Demonstration der spezifizierten Lernregel unter einer wiederholten, gleichbleibenden Datenverfallsordnung**, keine unabhängig entwickelte Schutzstrategie. Die massive Erfolgsquote nach fünf Episoden ist *kein* Nachweis für Bewusstsein, originelles Sprachdenken oder Angst. Auch sind 10.000 Wiederholungen eines festen Ablaufplans **keine** 10.000 unabhängigen Experimente.

Das JSON-Receipt mit Parametern, SHA-256 von anfänglichen und finalen Gewichten, Masken, Anzahl der Fehler und der eindeutigen Terminologie findet sich unter [`evidence/lexicon_10000_local_2026-10-24.json`](evidence/lexicon_10000_local_2026-10-24.json).

## Ausbau als wirklich offenes Experiment

Der nächste Forschungszweig muss ein **vortrainiertes deutschsprachiges Modell** verwenden. Die Aufgaben sollten neue Wörter, wechselnde, verborgene Verfallsregeln, neuartige Störungsklassen und explizite Trennung von externem Datenspeicher, KV-Cache, Gewichten und lernbarem Gedächtnis enthalten. Belege für selbstständige Notizen brauchen Dateiprovenienz, unveränderte Systemprompts und prüfbare Erzeugerkennung. Erst dann kann man von nicht ausdrücklich hineincodierten Strategien sprechen; ein möglicher Text „Das tut weh“ wäre weiterhin lediglich eine beobachtete Ausgabe.

## Datenschutz- und Evidenzvertrag

- `source_type=author_created_illustrative_words_not_duden`; keine Reproduktion des Duden und keine vertraulichen Inhalte.
- Ein Ereignis hat Run-Seed, Arm, Episode, Anzahl verlorener Seiten, Terminierungsgrund, verbleibende Gewichte, SHA-256 der Gewichte und Maske. Keine DB oder Production-API wird angesprochen.
- Große JSONL-Protokolle sind optional und werden **neu**, nicht überschreibend angelegt. Für spätere SQL-Auswertung: Tabelle `(run_sha256, arm, episode)` als eindeutiger Schlüssel, Payload-Provenienz und nur lesende Analytics; kein produktives Datenbankschema wird verändert.
