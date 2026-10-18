# vorlage-test

Wegwerf-Repository zum Ende-zu-Ende-Test der Projektvorlage aus `ai-projects` (Issue, Agent, PR, CI, Gate, Merge). Wird nach dem Test archiviert oder geloescht. Coding-Agenten setzen Issues autonom um; ein Mensch legt vorab die Akzeptanztests fest
(`tests/akzeptanz/`) und merged, sofern Auto-Merge nicht bewusst erlaubt ist.
Konventionen: `ai-projects/KONVENTIONEN.md`.

## Ablauf

1. Issue schreiben und Label `agent` setzen.
2. GitHub Agentic Workflows startet den Coding-Agenten (Anbieter: `.github/workflows/shared/anbieter.md`)
   mit Leserechten, Netzwerk-Allowlist und API-Key nur im Proxy.
3. Der Agent setzt das Issue um und fuehrt `ruff` und `pytest` aus (Regeln in `AGENTS.md`).
   Technisch erzwungen (Workflow, nicht verhandelbar): nur `src/` und `tests/`, Manifest- und
   Anweisungsdateien gesperrt, Patch hoechstens 200 KB. Verstoesse verhindern den Pull Request.
4. Ein Pruefjob kontrolliert das Ergebnis, danach entsteht ein Draft-Pull-Request.
5. Der Pull Request wird mit dem Token der eigenen GitHub App erstellt (`APP-EINRICHTUNG.md`): die CI
   (`.github/workflows/ci.yml`, Pflicht-Check `test`) startet ohne Freigabeklick. Ohne App braucht
   sie pro PR einen Klick ("Approve and run").
6. Das Agent-Gate (`.github/workflows/agent-gate.yml`) prueft nach der CI Autor, HEAD, Dateien
   (nur `src/` und `tests/`), Tests, Groesse, Akzeptanztest (`tests/akzeptanz/`, spec-first),
   `ABWEICHUNG:`-Zeile und den Zustand der CI auf main, und setzt den Pflicht-Check `agent-gate`.
7. Merge: Standard ist Handarbeit (Mensch prueft und merged). Nur wenn das Repo Auto-Merge
   (`allow_auto_merge`) bewusst erlaubt, merged das Gate gruene Agenten-PRs selbst, startet danach
   die CI auf main, schliesst die Issues und loescht den Branch.

## Kostenbremsen

Agent hoechstens 50 AI-Credits (rund 0.50 USD) pro Lauf, Pruefjob 20, alle Laeufe zusammen 200 pro
24 Stunden, hoechstens 30 Minuten. Harte Grenze: Prepaid-Guthaben beim Anbieter.

## Entwicklung lokal

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\ruff check .
.venv\Scripts\pytest
```
