# Einmaliger Start des 200-Millionen-Kontinuitätsversuchs

- Forschungsbranch: `research/continuity-cpp-20261026`
- Vorheriger geprüfter Commit: `4ab3d1f060efdcadb993f8e4466f5fb6840be37b`
- Smoke-CI: GitHub Actions Run #40255006953, Job `continuity-contract`: `success`; Run #40255006928 Scorer: `success`.
- Der **einzige** Trigger für die große Serie ist der Marker `[continuity-200m]` im Commit-Text dieses expliziten Start-Commits. Normale Dokumentations- und Code-Pushes dürfen keinen erneuten 200-Mio.-Lauf auslösen.
- Sieben Zeitpunkte sind **kumulative** Meilensteine derselben ununterbrochenen Trio-Geschichte (1, 5, 20, 50, 100, 150, 200 Mio.). Zwischenstufen starten aus vollständigen, SHA-256-geschützten Zustandssnapshots, niemals aus dem Ursprung.
- Logger: pro Million Turniere passive Schnappschüsse aus Eingabe, Aktivierungen, Aktionswahrscheinlichkeit, internem Erfahrungsspeicher und Gewichts-/Masken-Hashes. Kein Rückkanal in die drei Agenten.
- Eventuelle Zeitüberschreitung oder unvollständige Etappe wird als nicht abgeschlossen gemeldet. Das PDF wird erst nach Validierung aller 200 Mio. erstellt.
- Eingeschränktes C++17-Spielzeugmodell, kein LLM, kein Bewusstseins-/Schmerznachweis; keine Produktions- oder VPS-Auswirkung.
