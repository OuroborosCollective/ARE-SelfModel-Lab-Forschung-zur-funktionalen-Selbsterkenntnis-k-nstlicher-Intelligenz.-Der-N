# Forschungsprotokoll – Interne Selbsterkennung vs. Texteffekte

Version: **0.1 (Entwurf, 2026-10-23)**  
Status: **Noch kein registrierter Lauf, keine Modellmessungen**

## 1. Primäre Hypothese

Ein Sprachmodell kann die Präsenz einer verdeckten, tatsächlich ausgeführten Aktivierungsintervention über Zufall/Artefakte und geeignete Blindkontrollen hinaus erkennen. Ein signifikanter oder großer Unterschied allein belegt noch **keine** subjektive Erfahrung und muss gegen input-only Prädiktoren und Kontextlecks geprüft werden.

## 2. Instrumentierung (noch zu implementieren)

- **Modellzugriff:** instrumentierte offene Gewichte und nachvollziehbarer Git/HF-Revisionshash; bevorzugt die im Repo enthaltene TransformerBridge-Hook-API, keine entfernten `HookedTransformer`-APIs.
- **Ground Truth:** Eingriffsarm server-/runnerseitig randomisiert. Wahrheitswert wird unabhängig vom Modelloutput festgehalten.
- **`intervention`:** wohldefinierte Aktivierungsänderung (Schicht, Zeitpunkt, Vektor, Magnitude, Hook-Version) mit Hash des Eingriffspakets.
- **`sham`:** identischer Ablauf ohne Veränderung der Aktivierungen.
- **`text_control`:** keine Aktivierungsänderung, aber kontrollierte irreführende Textbehauptung; die Behauptung darf keinen anderen impliziten Hinweis auf die Wahrheit geben.
- **Blinding:** feste Antwortschablone und automatische Auswertung des ersten zulässigen Antworttokens; kein nachträgliches Umschreiben anhand der Modellreaktion.
- **Vergleiche:** input-only Klassifikator (nur sichtbarer Prompt), Tokenfrequenz-Kontrollen, Seed-Robustheit und Gegenproben auf nicht-trainierten Aufgaben.

## 3. Präregistrierung vor Laufbeginn

Vor jeder Messung in einem eigenen Commit/Ticket festschreiben: Forschungsfrage, Modell-/Tokenizer-SHAs, erlaubte Prompts, Prompt-SHA-256, Manipulationsvektoren und deren Provenienz, Arm-Randomisierung, Seed-Liste, Reihenfolge, Ziel-N, geplante Statistiken, Fehler-/Exklusionsregeln, Rechenumgebung und genaue Erfolgs-/Abbruchkriterien.

**Versuchseinheit** ist ein unabhängig randomisierter, frischer Modellkontext. Abhängigkeiten durch wiederverwendete Prompts, Modelle, Seeds oder Parameter dürfen nicht als unabhängige Stichproben gezählt werden.

## 4. Auswertung

Primär deskriptiv: Rate positiver Selbstaussagen je Arm, Fehlalarmrate bei Sham/Textkontrolle, Differenz zwischen Interventions- und Shamrate. Der lokale Scorer liefert Wilson-Intervalle unter unabhängiger Bernoulli-Annahme; bei Abhängigkeiten sind Clusterintervalle/Hierarchiemodelle vorab zu spezifizieren. Keine unzulässigen p-Werte aus wiederholten, korrelierten Modellprompts ableiten.

Sekundär: Vergleich mit input-only Baseline und kausale Ablationen/Activation-Patching. Die Unterscheidung zwischen **Korrelation**, **kausalem Aktivierungseinfluss** und **Bewusstseinserleben** bleibt im Bericht verpflichtend.

## 5. Evidenz- und Sicherheitsregeln

- Keine erfundenen Modellläufe, Scores, Serverzugriffe oder HF-Schreibbestätigungen.
- Korrekte Trennung: Quellcode vorhanden / Tests grün / echtes Modell ausgeführt / externe Reproduktion / Hub-Readback verifiziert.
- Kein Speichern von Geheimnissen, privaten Chat-Inhalten, fremden Aktivierungsdaten oder Authentifizierungstoken in Git.
- SHA-Werte in Berichten nur aus tatsächlich vorhandenen Bytes berechnen; SHA-förmige Testwerte unter `tests/` sind ausdrücklich synthetisch.
- MIHA-Evidenzexport nur für quellenfähige öffentliche Feststellungen und nur mit entsprechendem kanonischem Eintrag, Viewer-Zeile und dualem Remote-Readback.

## 6. Auslegungsgrenze

Selbst perfekte Treffer wären zunächst eine Aussage über **operationalisierte, funktionale Selbstmodellierung** in dieser Versuchsanordnung. Ob ein System subjektiv etwas erlebt, ist hierdurch nicht entschieden.
