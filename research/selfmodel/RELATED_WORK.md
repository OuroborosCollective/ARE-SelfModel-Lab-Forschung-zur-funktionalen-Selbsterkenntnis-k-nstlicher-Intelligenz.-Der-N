# Forschungslage und Testdesign (Stand: 24. Oktober 2026)

**Fragestellung:** Wann ist eine Selbstmeldung eines Sprachmodells ein Hinweis auf privilegierten Zugriff auf interne Zustände – und wann erklärt ein einfacherer Text- oder Logit-Artefakt die Antwort?

| Quelle | Paradigma | Hauptbefund | Grenze / Konsequenz für ARE SelfModel Lab |
|---|---|---|---|
| Lindsey (2026), [arXiv:2601.01828](https://arxiv.org/abs/2601.01828) | Concept-Injection in versteckte Aktivierungen, danach Selbstauskunft | Unter ausgewählten Bedingungen positive Meldungen, aber unzuverlässig und kontextabhängig | Interventionsort, Stärke und tatsächliche Hidden-State-Änderung getrennt protokollieren; keine Übertragung auf subjektives Erleben |
| Hahami et al. (2026, Preprint), [arXiv:2512.12411](https://arxiv.org/abs/2512.12411) | Binärer Eingriffstest vs. Positionsbestimmung bzw. Vergleich der Stärke | Für binäre Aufgaben erklären globale Logitverschiebungen scheinbare Erkennung; positionsbezogene Aufgaben erreichten im berichteten Setting bis zu 88 % gegenüber 10 % Zufallsniveau | **Primärer nächster Benchmark: Positions-Lokalisierung und relative Stärke**, plus Bias-Kontrollen. Zahlen sind settingbezogen, keine eigene Replikation |
| Singh, Linzen und Ravfogel (COLM 2026), [arXiv:2605.26242](https://arxiv.org/abs/2605.26242) | `input-only`-Prädiktor und sprachliche Gegenmanipulation | Einige behauptete Selbstkenntnisresultate lassen sich durch Eingabeinformationen erklären; Texteinflüsse können mit echten Eingriffen verwechselt werden | Verlangt sowohl privilegierten Zugriff als auch Hinweise auf einen **zweiten, vom Aufgabensignal unterscheidbaren Prozess** |
| Zou et al. (2026, Preprint), [arXiv:2609.35108](https://arxiv.org/abs/2609.35108) | Feste Eingabe, Eingriff an einer von zehn Tokenpositionen oder kein Eingriff | Lokalisierung und mögliche kausale Schaltkreise in beschränkten Modell-/Task-Settings | Für mechanistische Tests: feste Prompts und explizite No-Intervention-Option vorsehen |
| Atkinson, Plunkett und Bau (2026, Preprint), [arXiv:2610.07186](https://arxiv.org/abs/2610.07186) | Kausale Attributionsanalyse künstlich gelernter Präferenzen | Hinweise auf überlappende kausale Attributionen von Präferenzentscheidung und Selbstauskunft in eingeschränktem Setting | Aktivierungs-Ablationen und mechanistische Nachweise statt bloßer Trefferquoten |

## Was sich widerspricht – und was nicht

Die positiven und kritischen Studien untersuchen **nicht dieselbe Aussage**. Ein System kann in einer speziellen Aufgabe ein manipuliertes Muster lokalisieren, ohne dadurch allgemein seine eigenen Denkprozesse zu kennen. Ein binärer Alarm kann durch Logit-Bias entstehen, während differenzierende Aufgaben trotzdem Information über die Eingriffsposition enthalten. Belege für `privileged access` sind nicht automatisch Belege für `second-order computation` oder Bewusstsein.

**Evidenzqualität:** Unterschiedliche Modelle, Interventionsstellen und Definitionen verhindern einen einheitlichen metaanalytischen Zahlenwert. Hahami, Zou und Atkinson werden hier als Preprints gekennzeichnet; die Angaben sind Befunde der jeweiligen Autoren und **nicht von ARE SelfModel Lab repliziert**. Die Kritikarbeit von Singh et al. erschien in COLM 2026.

## Vorab vereinbarter Prüfmaßstab

1. Kein Erfolg allein durch ein gehäuftes `Ja` nach einem Eingriff.
2. Vergleich einer verdeckten Aktivierungsmanipulation mit Sham **und** textueller Gegenmanipulation.
3. Abgleich mit einer `input-only`-Baseline, die dieselbe Ein- und Ausgabestruktur sieht, aber keine Hidden States.
4. Positionsklassifikation (zehn Positionen plus `none`) und Größenordnung-Diskrimination mit balancierten Labels.
5. Evidenzprovenienz (Gewichte, Tokenizer, Hook-Code, Prompt, Seed, Patch und Run-Receipt) mit unveränderlichen Hashes.
6. Aussagen über Bewusstsein ausgeschlossen, sofern keine unabhängige zusätzliche Theorie/Operationalisierung vorliegt.
