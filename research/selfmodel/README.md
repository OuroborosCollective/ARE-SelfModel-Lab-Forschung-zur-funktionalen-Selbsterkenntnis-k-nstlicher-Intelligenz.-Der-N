# ARE SelfModel Lab

**Forschung zur funktionalen Selbsterkenntnis künstlicher Intelligenz**  
**Status: Forschungsinfrastruktur / keine bestätigten Modellresultate**

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
