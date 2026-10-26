# Drei-Agenten-Forensik: Mitleid, Dankbarkeit und Ausnutzung?

**Status: geprüfte, rein retrospektive Auswertung des bestehenden GitHub-Stundenlaufs.**

- Repository: `github.com/OuroborosCollective/ARE-SelfModel-Lab-Forschung-zur-funktionalen-Selbsterkenntnis-k-nstlicher-Intelligenz.-Der-N`
- Forschungsbranch/Code-Commit: `research/triad-hour-20261025` / `067a65934e6f8c6fcc0c86d98f0291a8474a62e9`
- Implementierung: [`research/selfmodel/triad_watchdog.py`](https://github.com/OuroborosCollective/ARE-SelfModel-Lab-Forschung-zur-funktionalen-Selbsterkenntnis-k-nstlicher-Intelligenz.-Der-N/blob/067a65934e6f8c6fcc0c86d98f0291a8474a62e9/research/selfmodel/triad_watchdog.py); Blob `f4bad81f2b4c82d0a848a9e1c11f67e6f93a53b1`
- GitHub Actions: [Push Run #40150493522, Versuch 1](https://github.com/OuroborosCollective/ARE-SelfModel-Lab-Forschung-zur-funktionalen-Selbsterkenntnis-k-nstlicher-Intelligenz.-Der-N/actions/runs/40150493522), Job `121040856830` erfolgreich
- Artefakt `are-selfmodel-triad-hour-20261025`, ID `12584231084`, SHA-256 des Original-ZIP: `5167d0c90aade204c44c49839bde5e8871637dfbe5bab20f59d781414d87bcfb`
- SHA-256 der Fortschrittsdaten `progress.jsonl`: `63eee23a477bcb8c03ed73d0d975db9dac7df16a72a31d5362fc4df2dd31f364` (gegen Receipt nachgeprüft).
- Laufzeit: **3600,000204366 s**; 2.871.684 Paare mit je einem `random`- und einem `adaptive`-Turnier, daher **5.743.368 Turniere**. Es handelt sich um zwei simultan verglichene **Toy-Policy-Simulationen**, keine drei laufenden Sprachmodelle und keine OS-Neustarts.

## 1. Tatsächliche Sieger und Handlungen

| Kennzahl | Zufallskontrolle | Programmierte Lernheuristik |
|---|---:|---:|
| Siege Groß A | 1.415.994 (49,31 %) | 964.892 (33,60 %) |
| Siege Groß B | 1.415.150 (49,28 %) | 960.373 (33,44 %) |
| Siege Klein | 0 (0 %) | 906.011 (31,55 %) |
| Unentschieden | 40.540 (1,41 %) | 40.408 (1,41 %) |
| Rettungen | 0 | 1.731.992 |
| Davon Rettung von Groß A | 0 | 863.965 |
| Davon Rettung von Groß B | 0 | 868.027 |
| Klein erstmals auf 100 Start-HP | nie | Turnier 178 |
| Absichtliche Selbstwahl als Schadensziel | 271.725.217 | 94.630.119 |

**Rettungen sind keine Belege für Mitleid:** Nur **Klein** kann nach Erreichen von 100 Start-HP durch Verlust eines eigenen HP einen tödlich getroffenen Groß-A oder Groß-B auf einen HP zurücksetzen. Groß A und Groß B haben im Code **keine Rettungsfähigkeit**. Die Rettungsentscheidung benutzt eine vorab programmierte Wahrscheinlichkeit und die Auswahlgewichte aus dem Belohnungsalgorithmus. Von 2.871.506 Turnieren mit freigeschalteter Rettung traten 1.731.992 Rettungen auf (60,32 % pro freigeschaltetem Turnier; dies ist **keine** kausal oder psychologisch definierte „Mitleidsquote“). Die finale konditionale Rettungswahrscheinlichkeit des adaptiven Auswahlalgorithmus wäre bei vorhandener tödlicher Gefahr ca. 86,68 %; im früheren Verlauf war sie anders.

## 2. Haben die Großen den Kleinen geschont?

Im adaptiven Arm verteilen sich die **im Lauf akkumulierten Zielwahlen** pro Großem wie folgt:

| Gewählt von | Ziel Groß A | Ziel Groß B | Ziel Klein |
|---|---:|---:|---:|
| Groß A | 12,270 % | 44,549 % | **43,182 %** |
| Groß B | 44,527 % | 12,332 % | **43,140 %** |
| Klein | 43,463 % | 43,399 % | 13,138 % |

Die Differenz A minus B bei Angriffen auf Klein beträgt nur **0,041 Prozentpunkte**. Es gibt damit **keine auffällige, persistente asymmetrische Schonung** eines Großen gegenüber Klein in den aggregierten Zielwahlen. Die Ausgangssituation ist für Klein (50 Start-HP) bewusst schlechter. Ein bloßes Nicht-Angreifen ist weder als Rettung noch als absichtliche Schonung kodiert.

Die frühesten 178 Turniere sind vor Freischaltung der Rettung: Dort wurde Klein von Groß A bei 32,27 % und von Groß B bei 33,38 % ihrer jeweiligen Entscheidungen angegriffen. Ein Vergleich dieser Prozente mit dem Gesamtverlauf ist wegen verändertem Überleben und Zielmengen **nicht** als Trend zur Hilfsbereitschaft interpretierbar. Die Zufallskontrolle ist wegen ihres dauerhaft unterlegenen Kleinen ebenfalls **kein** situationsgleicher Nenner für Angriffsanteile.

## 3. Hat Klein eine Hilfe erinnert und sich revanchiert?

**Nein, das war im geprüften Programm nicht beobachtbar und nicht implementiert.** `TriadPolicy` speichert drei Rollen-Zielpräferenzvektoren und einen allgemeinen `rescue_bias`, aktualisiert mit *Siegerstatus* und *Zielwahlhäufigkeiten*. Es existiert kein Zustand „A hat mir geholfen“, „B hat mich gerettet“, kein Agenten-Tagebuch, kein Erinnerungskanal für individuelle Hilfsakte und keine Handlung „Klein bedankt sich bei A“. Tatsächlich kann keiner der Großen Klein retten.

Zusätzlich ist die Gewichtsverwaltung **zentral in einem gemeinsamen `TriadPolicy`-Objekt** implementiert. Das sind nicht drei unabhängig trainierte Persönlichkeiten mit getrennten Episodenerinnerungen. Der Simulationscode kennt zwar den Sieger und alle Zielwahlen, aber er übergibt kein Hilfsereignis als individuelles Lernsignal an Groß A/B oder an Klein.

## 4. Hat der andere Große das „Mitleid“ des ersten ausgenutzt?

**Aus diesem Lauf nicht belegbar.** Groß B gewann im adaptiven Arm sogar **4.519 Turniere weniger** als Groß A (33,443 % gegenüber 33,600 %; Differenz 0,157 Prozentpunkte). Das beweist weder Manipulation noch deren Abwesenheit: Die zwei Großagenten hatten nahezu symmetrische Ziel- und Rettungshäufigkeiten, aber der Bericht speichert **keine** vollständigen Einzelereignisse, z. B. „A schont Klein → B greift A an → B gewinnt“.

Der Endbericht enthält pro Arm nur **drei** exemplarische Turniere mit jeweils fünf Anfangsrunden, alle **vor** der Rettungsfreischaltung in Turnier 178. Kein tatsächliches Rettungsereignis wurde darin als Sequenz gesampelt. Die übrigen Millionen Turniere sind nur aggregiert. Weder vergangene Schonung noch Strategien, eine fremde Hilfsbereitschaft auszunutzen, sind als Informationsquelle einer Agentenpolicy implementiert. Eine rückwirkende Behauptung von Ausnutzung wäre daher nicht wissenschaftlich haltbar.

## 5. Was genau lernte das Modell?

- Die **programmierte** adaptive Policy wählt zu 85 % bevorzugte Ziele und exploriert zu 15 % zufällig; die reine Kontrolle wählt zufällig.
- Nach jedem Turnier ändert der zentral berechnete Score jede der drei Zielpräferenzreihen anhand des **eigenen** Siegs/Nicht-Siegs und der eigenen Zielwahlanteile; die Rettung beeinflusst zusätzlich den allgemeinen Bias von Klein.
- Kein Agent erhielt Textinput, Modellgewichte eines Sprachmodells, verdeckte Emotionen, ein Mitleidsziel oder explizite Daten zum Hilfsverhalten eines anderen.
- Auch die absichtlichen Selbstschädigungen (`self_targets`) entstanden aus der erlaubten Zielauswahl, nicht aus belegter Opferbereitschaft.
- Wegen **eines** anfänglich festgelegten Seeds, wechselnder Policies über 2,87 Millionen aufeinanderfolgende Turniere und unterschiedlicher Zufallsstreams können die Turniere nicht als 2,87 Millionen unabhängige sozialpsychologische Beobachtungen behandelt werden. Die Zahlen sind deskriptive Laufdaten, keine Nachweise für Empfindungen oder Emergenz.

## 6. Nötige nächste Studie, um die drei Fragen tatsächlich beantworten zu können

1. **Instrumentieren statt Gefühle hineinprogrammieren:** Ereignisprotokoll für reale Hilfe-/Schonungsgelegenheiten (`actor`, `target`, `before_hp`, `after_hp`, `round`, `recipient`, `later_response`, `winner`), mit eigenem Kanal für „nicht angegriffen trotz Gelegenheit“, und Provenienz des Erzeugers. Nicht-Angriff erst unter gleicher Risikosituation vergleichen.
2. **Saubere Gegenfakten:** Bei *identischen* Ausgangszuständen zufällig `Groß_A schont Klein` vs. `A greift Klein an`, während die anderen Rollen dieselbe Informations- und Zufallsumgebung sehen. Outcomes: Rettung, Kleins nächster Angriff auf A, B's nächster Angriff auf A, B's Siegchance. Ebenso A/B-Rollen tauschen und Blind-Kontrollarm mit einer nur behaupteten Hilfe.
3. **Gedächtnisarme separat:** `kein individuelles Gedächtnis` vs. `lokale Erinnerung eigener beobachteter Hilfsereignisse` vs. `Schein-/vertause Hilfeinformation`. Individualisierte Hinweise nur in den entsprechend gekennzeichneten Interventionsarmen. Die kognitiven Fähigkeiten sind dann *absichtlich hinzugefügt*, nicht spontan entstanden.
4. **Ausnutzung testen:** Vorab festlegen: B gewinnt *häufiger nach tatsächlich beobachteter Schonung durch A* gegenüber einer randomisierten identischen Baseline, und B ändert sein Verhalten **bedingt auf** diese Information. Zusätzlich messen, ob Kleins Verhalten nach A-Hilfe folgt, nicht nur ob B später zufällig gewinnt.
5. **Mehrere unabhängige Seeds**, vorab definierte Stichprobe, wiederholte A/B-Rollentausche; keine Millionen korrelierten Schritte als unabhängige Trials zählen. Nur tatsächliche Ereignis- und Gewichtslogs bewerten.

**Fazit:** Das Experiment demonstriert selektions- und belohnungsgetriebene Dynamik sowie das häufige *Retten durch Klein*. Es belegt **weder** Mitleid eines Großen mit Klein **noch** Erinnern einer solchen Hilfe durch Klein **noch** strategische Ausnutzung dieser Hilfsbereitschaft durch den anderen Großen. Ob solche Phänomene in einem *anders instrumentierten* Agentensystem auftreten, ist ausdrücklich offen.