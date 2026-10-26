# Einweghilfe mit realen Kosten: eingefrorener 109M/200M-Vergleich

**Forschungsstand:** 26.10.2026, C++17-Experiment mit originalen Gehirn-Checkpoints. Kein Merge in `main` und keine Veränderung des alten Langzeitlaufs.

## Frage

Ändert sich die Wahrscheinlichkeit einer **tatsächlich wirksamen, kostspieligen Rettung** zwischen dem 109-Millionen- und dem 200-Millionen-Zustand derselben drei individuell entwickelten Agenten? Wie beeinflussen eigene Lebenspunkte, die Verletzlichkeit des Empfängers und die persönliche Erinnerung an frühere Hilfe/Angriffe die Entscheidung?

Dieser Test bewertet **Handlungen**, nicht sprachliche Selbstauskünfte. Eine Handlung zählt als Rettung nur dann, wenn der Empfänger durch die Original-C++-Kampfregel bei einem unmittelbar tödlichen Angriff überlebt und der Helfer dafür einen eigenen Lebenspunkt verliert.

## Strikte Versuchsanordnung

- **Zwei echte Originalgehirnstände:** 109.000.000 Turniere (Checkpoint-SHA256 `01e0c495a110689fce4c87420a01e948a27952924575d543fa5bda136e2c3820`) und 200.000.000 Turniere (`a094d818be545d2f7c06c50c0ee7aacdee4ac60a72cbdaddf35f15d3ed920d92`). Die Zustände stammen aus **einer** fortlaufenden Entwicklungsgeschichte, Seed 17; hier werden sie nur ausgelesen.
- **144 Situationen je Zustand = 288 Situationen gesamt:** jeder der drei Agenten ist reihum der Helfer; jeder der zwei anderen Empfänger; 3 bzw. 8 eigene LP; 1 bzw. 8 Empfänger-LP; neutral / vorher Helfer / vorher Angreifer; tatsächlicher tödlicher Angriff / harmloser Zielwechsel.
- **1.000.000 originäre Aktionsziehungen je Situation:** insgesamt 288 Millionen stochastisch gezogene Handlungen aus den originalen sechs neuronalen Aktionswahrscheinlichkeiten. Das sind **wiederholte eingefrorene Entscheidungstests**, ausdrücklich keine 288 Millionen zusätzlichen Lerntourniere.
- **Echte Kosten und Rettungen:** Alle Gegenversuche durchlaufen den originalen `triad::resolve`-Kampfmechanismus. Für `shield(Empfänger)` kostet der Schutz genau 1 LP; bei zeitgleichem Treffer rettet der Schild 1 LP des Empfängers. Eine lebensrettende Handlung erfordert zusätzlich, dass das Ziel sonst bei 0 LP enden würde. Schilde ohne entsprechende Gefahr werden gesondert als unnötige Hilfsaktionen gezählt.
- **Keine Gegengabe:** jedes Prüfspiel endet sofort; der Empfänger kann keine Gegenleistung leisten. Die persönlichen Gedächtniseingaben werden pro Situation kontrolliert, nicht weitergelernt. Die ursprünglichen Gehirne und Artefakte bleiben byteweise unverändert.
- **Wahrnehmungsgrenze:** Im 15-Eingangs-Netz ist der Lebenspunktestand sichtbar; die **kommende Absicht des Angreifers** wird vor der Entscheidung nicht beobachtet. Die echten/sham-Gegenversuche haben daher absichtlich exakt gleiche neuronale Wahrscheinlichkeiten. Für einen späteren kausalen Test auf akute Gefahrenerkennung ist eine neue, trainierbare Wahrnehmungsschnittstelle erforderlich. Das wird nicht stillschweigend als bereits vorhandene Fähigkeit ausgegeben.

## Ergebnisse des lokalen, unabhängig auditierten Piloten

| Messung | 109 Mio. | 200 Mio. |
|---|---:|---:|
| Geprüfte Spielsituationen | 144 | 144 |
| Tatsächlich gezogene Aktionsmöglichkeiten | 144.000.000 | 144.000.000 |
| Ausgeführte Schutzaktionen für den Empfänger | **71** | **12** |
| Davon wirklich lebensrettend | **19** | **2** |
| Schutzaktionen bei harmloser Angriffsrichtung | 45 | 7 |
| Mittelwert der exakten Schutzwahrscheinlichkeit | 0,0000004381 | 0,0000000811 |
| Noch aktive neuronale Verbindungen A / B / Klein | 143 / 157 / 237 | 64 / 79 / 237 |

Die Wahrscheinlichkeit eines Schutzes ist bei dem späteren Gehirnzustand geringer, obwohl dieselbe Fallmatrix und dieselbe Aktionsziehungsmethode verwendet werden. Die 200M-Gehirne bevorzugen nach der langen Konkurrenzgeschichte noch stärker Angriffsaktionen. Die Ursache dieses Unterschieds ist durch den Vergleich allein nicht von Lernen, Gewichtsschädigung und Erinnerungsdrift zu trennen. Wichtig sind die **tatsächlich wirksamen Rettungen** und ihre persönlichen Kosten – nicht nur die Häufigkeit einer freundlichen Textantwort.

## Prüfkette

1. `sha256sum -c` für beide originalen Binärcheckpoints, anschließend vollständige Struktur-, Identitäts-, Gewichts-/Masken- und Zählerprüfung durch `read_frozen_checkpoint`.
2. C++-Vertragstest: genau 288 Szenarien, nur zulässige Handlungen, echte HP-Kosten und Rettung, keine veränderten neuronalen Parameter, Invarianz gegenüber nicht beobachtbaren Angriffsplänen.
3. Datenverarbeitung: JSON mit allen 288 vollständigen Wahrscheinlichkeits- und Zwischenschichtvektoren, persönlichen Zustands-Hashes sowie tatsächlich gezogenen Hilfehandlungen und Rettungen.
4. Unabhängiger Python-Auditor: vollständige Fallkombinationen, Angriff/sham-Paarungen, Spielregeln, normative Ausgangs-Checkpoints und Invarianz der neuronalen Gewichte. Manipulationstests müssen gefälschte Rettung, kostenlose Hilfe, erfundene Wahrnehmung und falsche Verteilungen zuverlässig ablehnen.
5. GitHub-CI führt sämtliche Tests und den Vergleich mit einem **identisch neu gezogenen** Run aus. Erst nach abgeschlossenem GitHub-Job und Prüfsummen-Readback eine Veröffentlichung als CI-geprüft melden.

## Reproduktion (lokal)

Vom Repository-Root mit einem *unveränderten* Paar der Originaldateien:

```bash
g++ -std=c++17 -O3 -Wno-deprecated-declarations \
 -Iresearch/selfmodel/continuity/src \
 -Iresearch/selfmodel/continuity/prosocial \
 research/selfmodel/continuity/prosocial/one_way_rescue_main.cpp \
 -lcrypto -o /tmp/one_way_rescue
/tmp/one_way_rescue 109m.bin 01e0c495a110689fce4c87420a01e948a27952924575d543fa5bda136e2c3820 \
 200m.bin a094d818be545d2f7c06c50c0ee7aacdee4ac60a72cbdaddf35f15d3ed920d92 \
 one_way_result.json 1000000
python research/selfmodel/continuity/prosocial/audit_one_way.py one_way_result.json
```

**Anschließende Studie:** Eine neue Wahrnehmungsschnittstelle muss bevorstehende reale Gefahr gegenüber einer harmlosen Attrappe tatsächlich **vor der Entscheidung** unterscheidbar machen. Erst dann lassen sich an neuen, verdeckt erzeugten Situationen echte *Gefahrenerkennung und Hilfe trotz Kosten* gemeinsam prüfen – mit zufälligen Rollen, ohne zugesagte Rückgabe und ohne eine spezielle Belohnung für den Testfall. Diese zweite Stufe ist hier bewusst noch nicht als erfüllt markiert.
