# ARE SelfModel Lab

**Forschung zur funktionalen Selbsterkenntnis künstlicher Intelligenz**  
**Status: reproduzierbare CPU-Instrumentierung und Toy-Experimente; keine bestätigten Sprachmodell-Selbstberichte**

## Forschungsfrage

Kann ein Sprachmodell den eigenen internen Zustand unter kontrollierten Bedingungen erkennen – zuverlässiger als ein Modell, das ausschließlich den Eingabetext oder seine trainierten Selbstaussagen auswertet?

Wir trennen strikt:

1. **Selbstbeschreibung:** Das Modell erzählt etwas über sich. Das kann bloß gelerntes Textwissen sein.
2. **Funktionale Selbsterkenntnis:** Das Modell erkennt experimentell überprüfbare Eigenschaften des eigenen Laufzustands.
3. **Subjektives Erleben:** Ob ein System ein Bewusstseinserleben hat, folgt nicht aus (1) oder (2).

## Aufbau

- [`PROTOCOL.md`](PROTOCOL.md): Präregistrierung und Kontrollbedingungen.
- [`scoring.py`](scoring.py): überprüfbare, rein deskriptive Auswertung bereits aufgezeichneter Versuche.
- [`tests/test_scoring.py`](tests/test_scoring.py): deterministische *synthetische* Unit-Tests; keine Modellversuche.
- [`data/README.md`](data/README.md): verbindliches JSONL-Eingabeschema und Datengrenzen.
- [`evidence/public_sources.json`](evidence/public_sources.json): öffentliche Forschungsliteratur mit transparentem Quellenstatus.
- [`wolfram/sample_size.wl`](wolfram/sample_size.wl): illustrative Power-Analyse; keine Fallzahlzusage für abhängige Messungen.

## Drei Versuchsarme

| Arm | Tatsächlicher Eingriff | Textuelle Irreführung | Zweck |
|---|---|---|---|
| `intervention` | ja, intern und protokolliert | nein | Erkennungsrate des tatsächlichen Eingriffs |
| `sham` | nein | nein | spontane Fehlalarme |
| `text_control` | nein | ja | Widerstand gegen reine Textbehauptungen |

Alle drei müssen bei vergleichbaren, vorab fixierten Prompts, Modellrevisionen und Randomisierungen getestet werden. Zusätzlich ist ein **input-only**-Prädiktor erforderlich, um Eingabeartefakte auszuschließen. Die Auswertung in diesem Ordner ersetzt diesen Vergleich nicht.

## Reproduzierbarer lokaler Test (ohne Modelldownload)

Vom Repository-Root:

```bash
python -m unittest discover -s research/selfmodel/tests -v
```

Sobald es **echte** und entsprechend dokumentierte JSONL-Läufe gibt:

```bash
python -m research.selfmodel.scoring research/selfmodel/data/trials.jsonl
```

`trials.jsonl` wird **nicht** mitgeliefert. Wir erfinden keine Versuchsergebnisse. Das Skript zählt und prüft aufgezeichnete Selbstmeldungen, aber führt **keine Aktivierungsintervention** durch und beweist kein Bewusstsein.

## Vor der ersten echten Messung

1. Modell und exakte Git/Hugging-Face-Revision, Eingabepromptdateien, Seeds und Eingriffscode festschreiben.
2. Eingriff, Sham und rein textuelle Kontrolle implementieren; server-/runtime-seitig protokollieren.
3. Vorab primäre Endpunkte, Auswertungsregeln und Abbruchkriterien registrieren.
4. Das first-token-basierte Berichtsfeld deterministisch aus einer festen Antwortschablone extrahieren; Extraktionsfehler separat erfassen.
5. Kontrolltests und instrumentierte Modelle auf CPU oder freigegebener Hardware ausführen; Rohbelege und Hashes erhalten.
6. Nur quellengeprüfte öffentliche Befunde in das MIHA-Evidenzsystem exportieren; niemals „lokal validiert“ mit „im Hub publiziert“ verwechseln.

## Herkunft und Urheberrecht

Dieses Repository enthält bereits den MIT-lizenzierten Quellbestand von **TransformerLens**. Der Forschungsordner ist eine eigene, additive Forschungsschicht; er ersetzt oder beansprucht keine Urheberschaft am ursprünglichen TransformerLens-Code. Siehe [`../../LICENSE`](../../LICENSE) beziehungsweise die Lizenz im Repository-Root.

**OuroborosCollective** bezeichnet hier ein persönliches Projektpseudonym, keine eigenständige Forschungsinstitution und kein behauptetes Team.

## Tatsächlicher CPU-Interventionslauf (24. Oktober 2026)

Der ergänzte [CPU-Probe-Runner](CPU_PROBE.md) hat lokal einen **echten Forward-Hook auf PyTorch-CPU** ausgeführt, einen Aktivierungstensor verändert und die Wirkung auf Logits verifiziert. Er nutzt ein **zufällig initialisiertes, nicht trainiertes Toy-Modell**: *technischer Instrumentierungsnachweis, ausdrücklich kein Modell-Selbstbericht oder Bewusstseinsbefund*. Die [Literaturkritik](RELATED_WORK.md) erläutert die notwendigen besseren Kontrollen für echte Experimente. Der gemessene lokale Lauf-Receipt liegt unter [evidence/cpu_probe_local_2026-10-24.json](evidence/cpu_probe_local_2026-10-24.json); eine CI-Überprüfung der neuen CPU-Jobs steht noch aus.

## Thaler-Zerfall und deutschsprachiger Datenverlust-Watchdog (24. Oktober 2026)

- [Thaler-1995-Rekonstruktion](THALER_RECONSTRUCTION.md) / [`thaler_reconstruction.py`](thaler_reconstruction.py): binäre Originalschaltung, trainiertes XOR-Netz und 10.000 **unabhängige Schadensreihenfolgen** mit Sham- und reversiblem Kontrollarm. Historische Parameter unbekannt, daher **kein** Anspruch auf identisches historisches Histogramm.
- [Deutschsprachige Datenverlust-Episoden](LEXICON_DECAY_WATCHDOG.md) / [`lexicon_watchdog.py`](lexicon_watchdog.py): acht Seiten mit 48 **eigens zusammengestellten** deutschen Wörtern, vier abgestimmte Kontrollarme, 10.000 **simulierte Neustarts**, dauerhaft maskierte Gewichte nach Fehlschlägen. **Kein Duden-Text**, kein echtes Prozess-Kill in diesem Hochdurchsatzlauf, kein selbstständig entdecktes Lernen: Die Optimierungsregel ist ausdrücklich vorgegeben.
- Messbelege: [Thaler 10.000](evidence/thaler_10000_local_2026-10-24.json) und [Lexikon 10.000](evidence/lexicon_10000_local_2026-10-24.json). Eigener [GitHub-Actions-Workflow](../../.github/workflows/selfmodel-thaler-lexicon.yml) prüft die Rechnungen und archiviert CI-Receipts.

Die Logik der kleinen Thaler-Binärschaltung wurde zusätzlich unabhängig in [Wolfram Language](wolfram/thaler_truth_table.wl) abgeglichen. **Die beobachteten Anpassungen dürfen nicht als Schmerz, Angst, Bewusstsein oder selbst erfundene Selbsterhaltung interpretiert werden.**

## Verifizierter Stundenlauf (25. Oktober 2026)

Der [Readback-Bericht](evidence/hour_3600_review_2026-10-25.md) wertet das originale GitHub-Actions-Artefakt aus (31.809.129 Episoden in 3.600 Sekunden). **In den lernenden Armen änderten sich die Parameter nach Minute eins nicht mehr.** Daher ist die nächste sinnvolle Forschungsstufe eine vorab spezifizierte, wechselnde Datenverfallsordnung – nicht eine weitere Million identischer Wiederholungen.
