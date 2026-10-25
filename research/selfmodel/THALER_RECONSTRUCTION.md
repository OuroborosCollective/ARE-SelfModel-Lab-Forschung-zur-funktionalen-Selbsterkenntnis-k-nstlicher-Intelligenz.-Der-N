# Thaler (1995): unabhängiger methodischer Nachbau – kein Bewusstseinsnachweis

## Primärquelle und Abgrenzung

Stephen L. Thaler (1995). *Death of a Gedanken Creature*, Journal of Near-Death Studies **13**(3), 149–166. Grundlage ist die vom Auftraggeber bereitgestellte 18-seitige PDF-Ausgabe, insbesondere PDF-Seite 3 (Abbildung 1), Seite 6 (Abbildung 2) und Seite 8 (Abbildung 3).

Die Arbeit beschreibt das Abschalten von Netzwerkverbindungen und daraus entstehende, den realen Eingaben widersprechende Signale, die Thaler als „virtual inputs“ interpretiert. **Das Dokument enthält keine vollständig veröffentlichten trainierten Parameter oder exakten Zufallsfolgen für sein größeres Netzwerk.** Daher ist ein bytegenauer Nachbau des historischen Histogramms nicht möglich. Jede eigene Messung heißt ausdrücklich *unabhängige methodische Rekonstruktion*.

## Experimente

### A. Binäres Zwei-Sensoren-Netz (Abbildungen 1 und 2)

- Eingaben `x,y` sind binär, verstecktes Neuron aktiviert oberhalb der Schwelle `1.5`.
- Ausgabeneuron aktiviert oberhalb `0.5`; versteckter Hemmeingang trägt `-2` bei.
- Ein intakter Aufbau implementiert XOR: `(0,0) -> 0`, `(0,1) -> 1`, `(1,0) -> 1`, `(1,1) -> 0`.
- Durch Abtrennen des Hemmeingangs wird die unveränderte Nahrungseingabe `(1,1)` fälschlich zur Gefahrenausgabe `1`. Das ist ein **Klassifikationsfehler infolge einer tatsächlichen Leitungsunterbrechung**, kein nachgewiesenes Halluzinationserleben.

### B. Trainierter 2–5–1-Nachbau (Abbildung 3)

- Eigene CPU-Implementierung: fünf verborgene Sigmoidneuronen, ein Sigmoidausgang, 15 Verbindungsmultiplikatoren (zuzüglich trainierter Biaswerte).
- Tatsächliches XOR-Training per Backpropagation und Adam, mit fixiertem Trainingsseed und nachprüfbarer XOR-Fehlerschranke.
- Je Trajektorie werden 15 zufällig ausgewählte Verbindungen nacheinander auf **null** gesetzt. Die Eingaben bleiben konstant bei `(0.5,0.5)`; kein beobachtetes reales Umweltobjekt wechselt.
- Vier abgestimmte Kontrollarme mit identischer Reihenfolge: `trained_cumulative` (dauerhaft innerhalb des Zerfallslaufs), `trained_sham` (unverändert), `trained_reversible` (je Schritt nur ein einzelner Eingriff) und `untrained_cumulative` (nicht trainierte Anfangsgewichte).
- Die 10.000 Trajektorien sind **verschiedene Zerstörungsreihenfolgen eines festen trainierten Netzes**, nicht 10.000 unabhängige Modelltrainings oder autonome Wiederbelebungen.

## Reproduktionsbefehle

Vom Repo-Root mit Python >= 3.10, nur Standardbibliothek:

```bash
python -m unittest discover -s research/selfmodel/tests -p 'test_thaler_reconstruction.py' -v
python -m research.selfmodel.thaler_reconstruction --trials 10000 --seed 37 --training-seed 23 --max-seconds 180 --receipt thaler_receipt.json
```

Optional für einzelne vollständige JSONL-Ereignisse (erzeugt umfangreiche Dateien):

```bash
python -m research.selfmodel.thaler_reconstruction --trials 20 --events thaler_events.jsonl --receipt thaler_small_receipt.json
```

Das API bietet einen expliziten Ressourcenrahmen: maximal 100.000 Trajektorien und höchstens vier Stunden Messzeit; Teilläufe melden `timeout_incomplete`, statt Erfolg vorzutäuschen. Ein vorhandenes Log-/Receipt-Ziel wird nicht stillschweigend überschrieben.

## Evidenz / Interpretation

Das 10.000-Trajektorien-Receipt vom 24.10.2026 befindet sich unter [`evidence/thaler_10000_local_2026-10-24.json`](evidence/thaler_10000_local_2026-10-24.json). Diese lokalen Messungen enthalten viermal 160.000 auswertbare Zustände. Im trainierten kumulativen Arm gab es 117.746 Abweichungen von mehr als 0,05 Ausgabeeinheiten gegenüber der unbeschädigten Ausgangsausgabe; im Sham-Arm **null**. Die Daten zeigen den **kausalen Einfluss der künstlichen Schäden auf die numerischen Ausgaben**; sie zeigen **keinen** Schmerz, kein Erinnerungsvermögen und kein subjektives Erleben.

## Unabhängige rechnerische Kontrolle

`wolfram/thaler_truth_table.wl` spezifiziert die kleine Binärschaltung als Wolfram-Referenz und prüft sowohl die vier Eingaben als auch die Fehlklassifikation bei `(1,1)` nach Unterbrechung der Hemmleitung. Unsere Umsetzung wurde mit Wolfram Language überprüft. Die komplexeren Gewichte dieses Nachbaus sind unabhängig trainiert; es wird keine Gleichheit mit unveröffentlichten Thaler-Parametern behauptet.

Weiterführende methodische Literatur: Zhang & Nanda, *Towards Best Practices of Activation Patching in Language Models* ([arXiv:2309.16042](https://arxiv.org/abs/2309.16042)); die Wahl von Nullierungsbasis, Ausgabemetrik und Kontrolle kann Kausalattribution erheblich beeinflussen. Deshalb berichten wir hier sowohl Sham- als auch reversible und kumulative Eingriffe und bewerten nur explizite Ausgaben, nicht Bewusstsein.
