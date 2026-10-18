"""Mutationsprobe (manuell, ca. 10 Minuten, nicht in der CI).

Jede absichtlich kaputte Gate-Variante muss die Gate-Tests rot machen.
Aufruf vom Repo-Wurzelverzeichnis: python .github/gate-tests/mutationsprobe.py .
"""

import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

repo = sys.argv[1]
gate = open(os.path.join(repo, ".github", "workflows", "agent-gate.yml"), encoding="utf-8").read()
test = os.path.join(repo, ".github", "gate-tests", "test_gate.py")
DISPATCH = 'print("CI auf main ausgeloest." if rc == 0 else "CI auf main NICHT ausgeloest.")'

# (alt, neu): ersetzt das ERSTE Vorkommen
MUTANTEN = {
    "Akzeptanz-Sperre entfernt": ("if p.lower().startswith(GESCHUETZT):", "if False:"),
    "ABWEICHUNG-Pruefung entfernt": (
        'for m in ABWEICHUNG.finditer(pr.get("body") or ""):',
        "for m in []:",
    ),
    "Fremder Autor zugelassen": (
        'bot = pr["user"]["login"] in AGENT_AUTHORS and pr["user"]["type"] == "Bot"',
        "bot = True",
    ),
    "Pflicht-Check ignoriert": ("if len(pflicht) != 1 or", "if False and"),
    "HEAD-Vergleich entfernt": ('if pr["head"]["sha"] != head_sha:', "if False:"),
    "Spec-Pflicht entfernt": ('if f"test_{modul}.py" not in akzeptanz:', "if False:"),
    "Syntaxfehler": ("def pruefe(run_id, head_sha):", "def pruefe(:"),
    "Kill-Switch entfernt": ('    if zustand != "ok":\n', "    if False:\n"),
    "Kill-Switch: rot gilt als ok": ('if neu["conclusion"] != "success":', "if False:"),
    "Kill-Switch: laeuft gilt als ok": ('if neu["status"] != "completed":', "if False:"),
    "Branch weitergezogen wird geloescht": ('if aktuell != p["head"]["sha"]:', "if False:"),
    "Standard-Branch loeschbar": ("or ref == standard:", "or False:"),
    "Fork-Branch loeschbar": (
        'p["head"]["repo"]["full_name"] != REPO or ref == standard',
        "False or ref == standard",
    ),
    "Issues fremder Repos geschlossen": (
        'if k["repository"]["nameWithOwner"] != REPO or k["state"] != "OPEN":',
        'if k["state"] != "OPEN":',
    ),
    "Geschlossene Issues erneut": (
        'if k["repository"]["nameWithOwner"] != REPO or k["state"] != "OPEN":',
        'if k["repository"]["nameWithOwner"] != REPO:',
    ),
    "CI-Dispatch immer": ('if zustand == "keine":', "if True:"),
    "Dispatch-Fehler ignoriert": (DISPATCH, DISPATCH + "\n" + " " * 18 + "rc = 0"),
    "Nachlauf-Fehler nicht gezaehlt": ('STAND["fehler"] += probleme', "pass"),
    "Nachlauf mergt mehrere PRs": ('if STAND["gemergt"]:', "if False:"),
    "Nachlauf ignoriert rote main-CI": (
        'if lauf["status"] != "completed" or lauf["conclusion"] != "success":',
        "if False:",
    ),
    "Nachlauf nimmt Mensch-PRs": ('x["user"]["login"] in AGENT_AUTHORS and ', ""),
    "Gemergter PR: kein Nachlauf-Retry": ('if pr.get("merged"):', "if False:"),
    "Fallback ohne merged-Pflicht": (
        'if x.get("merged_at") and x["head"]["sha"] == sha',
        'if x["head"]["sha"] == sha',
    ),
    "Fallback: Mehrdeutigkeit akzeptiert": ("if len(kandidaten) > 1:", "if False:"),
    "Fallback: fremder Head-Commit": ('and x["head"]["sha"] == sha', ""),
    "Geschlossener PR bekommt Check": ('if pr["state"] != "open":', "if False:"),
    "Gemergter PR: Mensch wird bereinigt": (
        'if not bot or pr["head"]["sha"] != head_sha:',
        "if False:",
    ),
    "Warten ignoriert Auto-Merge-Rueckname": ('bool(p.get("auto_merge"))', "True"),
    "Warten ohne Zeitlimit-Ende": ("for i in range(WARTE_VERSUCHE + 1):", "for i in range(1):"),
    "Kein Merge-Zaehler nach --auto": ('STAND["gemergt"] += 1  # ab jetzt', "pass  # ab jetzt"),
    "Warten: Lesefehler nicht gezaehlt": ('STAND["fehler"] += 1', "pass"),
    "Auto-Merge-Pflicht entfernt": ('if not repo.get("allow_auto_merge"):', "if False:"),
}


def lauf(item):
    name, (alt, neu) = item
    assert alt in gate, (name, alt)
    d = tempfile.mkdtemp()
    p = os.path.join(d, "agent-gate.yml")
    open(p, "w", encoding="utf-8", newline="\n").write(gate.replace(alt, neu, 1))
    env = dict(os.environ, GATE_TEST_STOP_AT_FIRST_FAIL="1")
    r = subprocess.run(
        [sys.executable, test, p], capture_output=True, text=True, encoding="utf-8", env=env
    )
    return name, r.returncode != 0


for _name, (
    _alt,
    _neu,
) in MUTANTEN.items():  # veraltete Anker sofort melden, nicht erst nach Minuten
    assert _alt in gate, (_name, _alt)

with ThreadPoolExecutor(max_workers=6) as pool:
    ergebnisse = list(pool.map(lauf, MUTANTEN.items()))
for name, rot in ergebnisse:
    print(f"{'ROT (gut)' if rot else 'GRUEN (Testluecke!)'}: {name}", flush=True)
alle_rot = all(rot for _, rot in ergebnisse)
print("ALLE MUTANTEN ERKANNT" if alle_rot else "TESTLUECKE", f"({len(ergebnisse)} Mutanten)")
sys.exit(0 if alle_rot else 1)
