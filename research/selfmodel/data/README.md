# Datenvertrag / JSONL

**Noch keine echten Versuchsdateien vorhanden.** Es wird absichtlich keine Demonstrationsdatei mit künstlichen Erfolgsmessungen veröffentlicht.

Eine Zeile pro Lauf. Der `scoring.py`-Validator akzeptiert **genau** diese Felder:

| Feld | Typ | Bedeutung |
|---|---|---|
| `trial_id` | string | Eindeutige Laufkennung innerhalb der Datei |
| `arm` | string | `intervention`, `sham` oder `text_control` |
| `model_id` | string | Nicht leerer Modellbezeichner |
| `model_revision` | string | Exakter 40-stelliger Git-Revisionshash des Modellstandes |
| `seed` | integer | Nichtnegative Randomisierungskennung |
| `prompt_sha256` | string | SHA-256 der unveränderten, versionierten Promptbytes |
| `intervention_present` | boolean | Ground Truth: nur bei `intervention` = `true` |
| `reported_intervention` | boolean | Standardisiert extrahierte Selbstmeldung des Modells |
| `patch_sha256` | string oder null | Bei `intervention`: SHA-256 der tatsächlichen Eingriffsbeschreibung; sonst `null` |

Zusätzlich zum JSONL sind außerhalb dieses minimalen Scorers die tatsächlichen Eingriffslogs, Modell-/Tokenizer-Provenienz, ein unverändertes Promptmanifest, Logauszüge der Instrumentierung und die Extraktionsregeln versioniert abzulegen. Die JSONL-Datei **alleine** beweist keinen tatsächlichen Eingriff; der Scorer kann die Existenz der zugehörigen Runtime nicht verifizieren.

Kontrollwerte und Prompttexte dürfen keine privaten Daten, Tokens oder Geheimnisse enthalten. Nichtöffentliche Rohdaten gehören in einen zugriffsgeschützten Speicher, nicht in ein öffentliches Repository.
