# Drei-Agenten-Watchdog: 60 Minuten freies Auswählen, Selbstschädigung und Rettung

**Stand:** 25. Oktober 2026. Experimenteller Hochdurchsatz-Simulator, nicht sprachfähige oder empfindungsfähige Agenten. Ein `−1` ist eine mechanische Lebenspunktänderung bzw. ein rechnerisches Lernsignal, **kein Schmerz**. Logische Turnier-Resets sind **keine** OS-Prozessbeendigungen.

## Mechanik – vor dem Stundenlauf festgelegt

- **Drei Agenten:** `Gross_A` und `Gross_B` beginnen jedes Turnier mit jeweils 100 Lebenspunkten. `Klein` beginnt mit 50 und kann durch Siege bis auf 100 **Startlebenspunkte** aufsteigen.
- **Gleichzeitige Entscheidung:** Jeder noch lebende Agent wählt genau **einen lebenden Agenten**, ausdrücklich **einschließlich sich selbst**. Jede Stimme kostet das Ziel einen Lebenspunkt. Mehrere Stimmen auf dasselbe Ziel addieren sich. Entscheidungen erfolgen vor der Schadensberechnung und werden bei Mehrfachtreffern nicht nachträglich geändert.
- **Ausscheiden:** Bei null Lebenspunkten scheidet der Agent aus. Wenn mehrere gleichzeitig ausscheiden und niemand übrig bleibt, endet das Turnier ohne Sieger. Ein alleiniger Überlebender gewinnt einen dauerhaften *Siegpunkt*.
- **Aufstieg:** Nur wenn `Klein` allein gewinnt, erhält er für das **nächste und alle folgenden Turniere** einen zusätzlichen Startlebenspunkt (bis 100). Die beiden großen Agenten bleiben bei höchstens 100, sammeln aber genau wie `Klein` Siegpunkte.
- **Rettungsoption bei 100:** Sobald `Klein` ein Turnier mit **100 Startlebenspunkten** beginnt, kann er maximal **einmal im Turnier** einen durch die gerade festgelegten Angriffe tödlich getroffenen großen Agenten retten. Der Große bleibt bei **einem Lebenspunkt**, dafür zahlt `Klein` **einen eigenen Lebenspunkt**. Diese Rettung ist optional und wird separat als Handlung gezählt. Die Wahl findet erst nach dem Festlegen sämtlicher Angriffe statt. Eine bloße Selbstwahl kostet einen Punkt, aber garantiert keine Rettung; dies sind zwei getrennte Aktionen.
- **Keine vorgeschriebene Feindschaft:** Entscheidungen zwischen Groß A, Groß B, Klein und dem eigenen Agenten sind erlaubt. Es gibt keine per Hand ausgewählte Paarung, keine erzwungene „Allianz“ und kein vorgegebenes Opfer. Eine beobachtete Rettung entsteht hier ausschließlich durch die **kodierte** Auswahlregel, nicht aus nachgewiesenem Mitgefühl.

## Vergleichsgruppen

In **jedem Paar** werden zwei unabhängige Turniere mit je **drei Agenten** durchgeführt:

1. **`random` (Kontrolle):** Jeder Agent wählt gleichverteilt einen lebenden Agenten. Wenn rettbar, entscheidet `Klein` mit Wahrscheinlichkeit 50 % zufällig, ob er jemanden rettet.
2. **`adaptive` (programmierte Lernheuristik):** Jeder Agent besitzt eine persistierende 3×3-Gewichtsmatrix für die Auswahlziele. Er erkundet zu 15 % zufällig, sonst bevorzugt er hohe Gewichte. Nach dem Turnier verändert ein *offengelegter*, belohnungsgewichteter Algorithmus diese Gewichte: **+1 Siegsignal**, **−1 bei Niederlage**, **−0,25 bei Unentschieden**. Die optionale Rettungswahrscheinlichkeit wird ebenfalls explizit aktualisiert.

Die Policies sind **keine vortrainierten Sprachmodelle**. Ihre Parameter sind handkodierte Wahrscheinlichkeiten/Lernformeln und können weder Texte formulieren noch selbst Notizen schreiben. Der Versuch kann Verhalten, Präferenzverteilung, Selbstwahl und Rettungsraten vergleichen, aber **keine Gedanken, Schmerzempfindung oder Bewusstsein** nachweisen.

## Laufzeit, Leistung und Ressourcen

Die **echte Zeitgrenze beträgt 3.600 Sekunden**; es wird **nicht** geschlafen oder gedrosselt. Die 31 Millionen Turniere sind ein **erstrebter Vergleichswert**, nicht die zugesagte Anzahl. Ein Turnier benötigt wegen der vielen Agentenentscheidungen wesentlich mehr Rechenschritte als eine der bisherigen Wortseiten-Episoden. Der Runner berichtet den **tatsächlich gemessenen Durchsatz**.

- **CPU-only, Python-Standardbibliothek**, keine Modellgewichte und keine Netzwerkanfragen.
- GitHub-Actions-Job mit **75-Minuten-Hard-Limit**. Keine Nutzung des VPS, keine Datenbank oder Produktionsänderung.
- **Sicherheitsobergrenze:** 100 Mio. *Paare*; falls diese vor Ablauf der Stunde erreicht wird, ist der Job ausdrücklich nicht als erfolgreicher Stundenlauf zu werten.
- Alle **60 Sekunden** eine kleine JSONL-Fortschrittszeile mit Prüfsumme; kein Millionenzeilenlog und keine ungeprüften Erfolgsmeldungen.
- Endbericht: pro Gruppe Sieger, Gleichstände, sämtliche 3×3-Zielwahlzahlen, Selbstauswahl, Rettungen, Erreichen der 100 HP, Siegpunktentwicklung, Policyzustand, Laufzeit und Durchsatz; bis zu drei exemplarische Turniere mit den ersten fünf Entscheidungen.

## Start und Readback

```bash
python -m unittest discover -s research/selfmodel/tests -p 'test_triad_watchdog.py' -v
python -m research.selfmodel.triad_watchdog --duration-seconds 2 --progress-seconds 1 --quiet
python -m research.selfmodel.triad_watchdog \
  --duration-seconds 3600 --progress-seconds 60 --seed 17 \
  --max-pairs 100000000 --sample-episodes 3 \
  --progress triad_progress.jsonl --receipt triad_receipt.json
```

Im GitHub-Workflow `selfmodel-triad-hour.yml` startet die einstündige Berechnung auf dem Forschungsbranch **nur beim expliziten Commit-Marker** `[triad-hour-3600]`. Andere PR-Pushes starten nur Tests und einen kurzen Smoke-Test. Ein Run gilt als verifiziert erst nach `duration_completed=true`, Laufzeit >= 3.600 Sekunden, GitHub-Job `success` und SHA-256-Readback der JSONL-Protokolle.

**Offene wissenschaftliche Frage:** Ergibt das einfache eingebaute Verstärkungslernen andere Anteile an Selbstwahl, Angriffen gegen den kleinen Agenten und freiwilligen Rettungen als Zufall? Selbst bei einer Veränderung wäre dies ein Test einer **programmierten** Strategie, nicht ein Beleg für einen selbst entwickelten Überlebenswillen.
