# CPU-Probe: nachgewiesener Aktivierungseingriff

Status: **Technischer Instrumentierungsnachweis, nicht KI-Introspektion.**

Die Datei `cpu_probe.py` führt mit PyTorch auf der CPU vier Forward-Pässe durch:

1. `reference`: feste Token-IDs, zufällig initialisierter Decoder, keine Hooks.
2. `sham`: exakt dieselben Tokens und Gewichte, kein Hook; Output muss bitidentisch sein.
3. `text_control`: geänderte sichtbare Token-ID an einer Stelle, **kein** Aktivierungs-Hook.
4. `intervention`: gleiche Tokens wie Referenz, echte Veränderung des Embedding-Aktivierungstensors durch einen registrierten PyTorch-Forward-Hook.

Damit kann der Runner beweisen, **dass ein interner Eingriff stattfindet** und ob er die Logits tatsächlich ändert. Die vorherigen Tokenpositionen dürfen bei kausaler Maskierung nicht verändert werden; der Runner stoppt bei Verletzung dieses Vertrages.

**Keine Bewusstseins- oder Selbsterkenntnisbehauptung:** Das eingesetzte Modell ist winzig, zufällig initialisiert, nicht trainiert und kann nicht sinnvoll über seinen eigenen Zustand berichten. Die reine Änderung eines Logits ist keine Metakognition. Außerdem ist die sichtbare Textkontrolle hier nur eine Tokenvariation – nicht die sprachliche Gaslighting-Kontrolle, die eine spätere Studie benötigt.

## Lokal ausführen

Im Repository-Root (benötigt PyTorch CPU und NumPy; GitHub Actions installiert `torch==2.10.0` und `numpy==2.3.5` ausdrücklich):

```bash
python -m unittest discover -s research/selfmodel/tests -p 'test_cpu_probe.py' -v
python -m research.selfmodel.cpu_probe --seed 17 --position 2 --strength 1.0 --output cpu_probe_receipt.json
python -m coverage run --branch -m unittest discover -s research/selfmodel/tests -p 'test_cpu_probe.py' -v
python -m coverage report -m --include='research/selfmodel/cpu_probe.py' --fail-under=95
```

Der ausführbare Runner erzeugt einen JSON-Receipt mit identischen Eingaben, Seed, Tensor- und Gewichts-Hash, Patch-Hash, Eingriffszähler und Logitdifferenz. Eine unveränderte Sham-Ausgabe sowie eine echte Aktivierungsänderung sind **hart geprüfte Bedingungen**. Den Receipt nicht als tatsächliche Introspektion in die Verhaltens-Scoringdatei umwandeln.

## Nächste wissenschaftliche Stufe (noch NICHT gemessen)

- Instrumentierte **vortrainierte** offene Sprachmodelle, feste revisionsgebundene Gewichte und Tokenizer.
- Eingriffe in zufällig gewählte Satzpositionen sowie Magnitudenvergleich (nicht nur Ja/Nein-Frage).
- Echte Texteingabe-Täuschung als dritte Gruppe und ein trainierter `input-only`-Prädiktor.
- Randomisierte und verblindete Bedingungen, erste Tokenantwort, offengelegte Fehlerraten.
- Pre-Registration und eine passende Statistik für durch Prompts oder Modelle korrelierte Daten.

Siehe [RELATED_WORK.md](RELATED_WORK.md) und [PROTOCOL.md](PROTOCOL.md).
