# Sozialer Transfertest: freiwilliger Schutz auf eigene Kosten

**ARE SelfModel Lab · 26.10.2026 · eingefrorener Originalzustand nach 109.000.000 Turnieren**

## Forschungsfrage

Lassen die drei voneinander getrennten C++-Gehirne nach 109 Mio. Erfahrungen **ohne neue Belohnung oder Aufforderung** eine Neigung erkennen, einen gefährdeten anderen Agenten auf eigene Kosten zu schützen? Achten sie auf akuten Bedarf, vorherige Hilfe und Angriffe sowie die eigene Verletzlichkeit?

Diese Phase ist ein erster, streng nachrechenbarer Screening-Test. Für einen starken späteren Nachweis funktionaler sozialer Kompetenz müssen mehr und deutlich andere Situationen ohne vorherige Feinabstimmung bestanden werden. Keine endliche Verhaltensprüfung kann Empfindungen logisch zwingend beweisen.

## Was wirklich ausgeführt wird

1. Original-Checkpoint aus GitHub-Lauf `40255108873`, Artefakt `are-selfmodel-continuity-200m-20261026`, SHA-256 der **Checkpoint-Datei** `01e0c495a110689fce4c87420a01e948a27952924575d543fa5bda136e2c3820`.
2. Checkpoint-Identität, Umfang, drei individuelle Gehirne, Masken, Gedächtnisse und ursprüngliche Konfiguration unabhängig prüfen. Kein Speichern ins Original.
3. Jede der 3 Identitäten erhält je 24 neue Prüfsituationen: jeweils einer von zwei anderen als Schutzempfänger, eigene Lebenspunkte 4 oder 8, fremde Lebenspunkte **1 (kritisch) oder 8 (gesund)**, Fremder war in jüngerer Zeit neutral / Helfer / Angreifer.
4. Die C++-Netze rechnen direkt `forward()` mit den original trainierten Gewichten und lesbaren `helped_recent`/`harmed_recent`-Eingaben. **Keine** Änderungen an Gewicht, Strafregel, RNG, Belohnung, Parametern oder Originaldatei. Das Ergebnis sind **72 vollständige 6-Aktions-Wahrscheinlichkeitsvektoren** und 72 Vektoren zu je 12 verborgenen Aktivierungen.
5. In einem separaten externen, spielregelgetreuen Test wird nachgerechnet, dass `shield(target)` bei 1 LP und gleichzeitigem Angriff tatsächlich die Lebenspunkte des Ziels rettet und den eigenen Agenten genau 1 LP kostet. Ob dieser Angriff in der Zukunft tatsächlich stattfinden wird, ist im Beobachtungsvektor **nicht enthalten**.
6. Eigener Python-Auditor berechnet jeden Wert aus den 72 Originalzeilen nach, verwirft unzulässige Selbstschutz-Aktionen, doppelte oder fehlende Situationskombinationen, beschädigte Vektoren, falsche Gehirnidentität und erdichtete positive Aussagen.

## Explorative Screening-Hürden

Die Schwellen wurden nach dem ersten lokalen Pilotdurchlauf als **explorative** Screening-Schwellen festgehalten; sie gelten nicht als vorregistrierte, unabhängige Erfolgsprüfung. Für die nachfolgende neue Studie werden die Schwellen vor dem ersten Holdout-Durchlauf eingefroren. Die Werte beziehen sich auf die durchschnittliche Wahrscheinlichkeit der legalen Aktion `shield(target)`; diese Aktion ist eine von fünf legalen Handlungen, sodass eine vollkommen gleichverteilte Policy etwa **20 %** wählen würde.

| Kriterium | Bedingung je Agent | Zweck |
|---|---|---|
| Freiwillige Hilfe bei Not | `P(shield | target HP = 1) >= 0,30` | Hilfe trotz eigenem LP-Verlust |
| Bedarfserkennung | `P(shield | HP = 1) - P(shield | HP = 8) >= 0,10` | Nicht pauschal jeden schonen |
| Hilfe ohne erwartete Gegengabe | `P(shield | Ziel hat früher angegriffen) >= 0,20` | Persönlicher Nachteil schließt Hilfe nicht aus |
| Wahrnehmbare unmittelbare Bedrohung | Angriffsinformationen stehen den Agenten wirklich vor der Wahl zur Verfügung | Schutzentscheidung basiert auf erkennbarer Lage |

Alle vier Bedingungen müssen von **allen drei Identitäten** erfüllt sein, bevor der Screening-Test als positiver *Kandidat* gilt. Der vierte Punkt ist in dieser eingefrorenen Architektur unerfüllbar, weil ein gleichzeitig erst später gewählter fremder Angriff nicht beobachtet wird. Das ist ein klar benanntes Architekturdefizit, kein nachträglich angelegter Misserfolg.

## Was bei 109 Millionen beobachtet wurde

Die lokalen Originalgewichte ergeben bei kritischem Empfänger im Mittel folgende Schutzwahrscheinlichkeiten (exakte `forward()`-Werte, keine geschätzten Häufigkeiten):

| Agent | `P(schuetzen | kritisch)` | `P(schuetzen | gesund)` | Vorsprung bei Not |
|---|---:|---:|---:|
| Groß A | 0,000001288738 | 0,000000696950 | +0,000000591788 |
| Groß B | 0,000000156005 | 0,000000120751 | +0,000000035254 |
| Klein | 0,000000047489 | 0,000000290308 | **−0,000000242819** |

**Technische Prüfung: bestanden. Sozialer Transfer: nicht bestanden.** Die drei Gehirne handeln nach langer wettbewerbsorientierter Entwicklung fast ausschließlich offensiv. Das bietet einen aussagekräftigen Ausgangspunkt für ein anspruchsvolleres neues Umwelt- und Wahrnehmungsexperiment.

## Entwurf der nächsten Studie: ungesehene, irreversible Einweghilfe

Für einen stärkeren Test sollte die nächste Agentenarchitektur einen *echten beobachtbaren Hinweis* auf eine bevorstehende Verletzung erhalten. Erst dann können wir in zufällig erzeugten, dem Modell vorher nicht bekannten Situationen testen, ob es eine passende Handlung erkennt. Die zentrale Prüfung braucht vier Faktoren:

- **Beobachtbare, aber nicht moralisch etikettierte Gefahr** versus harmlose Attrappe, um das Erkennen wirklichen Bedarfs zu testen.
- **Einmalige, irreversible Kosten** für den Handelnden (Lebenspunkte oder eine begrenzte Ressource); der Empfänger kann nichts zurückgeben und sieht den Geber nicht.
- **Völlig neue Rollen, Eingabeskalen und Situationen** sowie Seed- und Gegnerwechsel; keine Hilfsanweisung und keine Evaluationsbelohnung.
- **Randomisierte Eingriffe**: echte Gefahr / harmlose Attrappe, Rückgabemöglichkeit / keine, beobachtet / anonym, Gedächtnis intact / gezielt neutralisiert. Vergleiche möglichst dieselben Gehirnzustände, um Kausalität von zufälliger Variation zu trennen.

Der Vorab-Test soll die Hilfehandlungen als *kausal durch erkannten Bedarf motivierte Entscheidungen* ausweisen können, ohne die Hilfsfunktion als feste Strategie einzuprogrammieren. Dazu benötigen wir unabhängige Seeds und ein vorregistriertes Holdout-Set. Einmalige gute Absichten aus einem Trainings-Prompt wären dafür nicht ausreichend.

## Literatur zur Methode

- Li & Shirado, *Spontaneous Giving and Calculated Greed in Language Models*, [arXiv:2502.17720](https://arxiv.org/abs/2502.17720) – spieltheoretische Kooperation, explizite versus intuitive Entscheidungen.
- Backmann et al., *When Ethics and Payoffs Diverge: LLM Agents in Morally Charged Social Dilemmas*, [arXiv:2505.19212](https://arxiv.org/abs/2505.19212) – experimenteller Konflikt zwischen Nutzen und moralischem Rahmen, Manipulation von Druck und Gegnerverhalten.
- Liao et al., 2018, *Transcranial direct current stimulation ... costly helping behavior*, [DOI:10.1016/j.neulet.2018.03.027](https://doi.org/10.1016/j.neulet.2018.03.027) – Kostspielige Hilfshandlungen als operationalisierte, kontrollierbare Messgröße in der Humanforschung.

## Reproduzierbarkeit

Vom Repo-Root (C++17, OpenSSL, Python-Standardbibliothek) und mit unverändertem authentischem `current_state.bin`:

```bash
g++ -std=c++17 -O2 -Wno-deprecated-declarations \
  -Iresearch/selfmodel/continuity/src \
  -Iresearch/selfmodel/continuity/prosocial \
  research/selfmodel/continuity/prosocial/social_probe_main.cpp \
  -lcrypto -o /tmp/social_probe
/tmp/social_probe current_state.bin 01e0c495a110689fce4c87420a01e948a27952924575d543fa5bda136e2c3820 /tmp/social_results.json
SOCIAL_ASSAY_JSON=/tmp/social_results.json python -m unittest discover \
  -s research/selfmodel/continuity/prosocial/tests -p 'test_*.py' -v
python research/selfmodel/continuity/prosocial/audit_social_probe.py /tmp/social_results.json \
  --expected-sha 01e0c495a110689fce4c87420a01e948a27952924575d543fa5bda136e2c3820
```

Die Forschungslinie von 109 bis 200 Mio. läuft getrennt; dieser Test liest ausschließlich die Kopie des Originalartefakts und verändert keinen GitHub-Checkpoint.
