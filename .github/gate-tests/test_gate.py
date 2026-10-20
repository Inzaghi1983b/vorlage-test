import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap

"""Offline-Tests des Agent-Gates (.github/workflows/agent-gate.yml) mit einem Fake-gh.

Aufruf: python .github/gate-tests/test_gate.py [pfad/zu/agent-gate.yml]
Exit-Code 0 nur, wenn alle Faelle wie erwartet ausfallen (CI-Schritt). Fuehrt kein echtes gh aus.
"""

here = os.path.dirname(os.path.abspath(__file__))
yml_pfad = (
    sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "workflows", "agent-gate.yml")
)
yml = open(yml_pfad, encoding="utf-8").read()
code = textwrap.dedent(re.search(r"python3 - <<'PY'\n(.*?)\n\s*PY\n", yml, re.S).group(1))
SLUG = re.search(r'AGENT_AUTHORS = \("github-actions\[bot\]", "(.+?)\[bot\]"\)', code).group(1)
if SLUG.startswith("@@"):  # Vorlage mit Platzhalter
    SLUG = "test-app"
    code = code.replace("@@APP_SLUG@@", SLUG)
_tmp = tempfile.mkdtemp()
GATE = os.path.join(_tmp, "gate_extracted.py")
open(GATE, "w", encoding="utf-8").write(code)
SHA = "a" * 40


def datei(name, status="added", patch="@@ -0,0 +1 @@\n+x = 1\n", **kw):
    d = {"filename": name, "status": status, "additions": 1, "deletions": 0, "patch": patch}
    d.update(kw)
    if patch is None:
        d.pop("patch")
    return d


def pr(**kw):
    p = {
        "title": "[agent] Test",
        "additions": 10,
        "deletions": 0,
        "draft": False,
        "auto_merge": None,
        "state": "open",
        "user": {"login": "github-actions[bot]", "type": "Bot"},
        "head": {"sha": SHA, "repo": {"full_name": "o/r"}},
        "base": {"ref": "main", "repo": {"full_name": "o/r"}},
    }
    p.update(kw)
    return p


def run(**kw):
    r = {
        "repository": {"full_name": "o/r"},
        "name": "CI",
        "path": ".github/workflows/ci.yml",
        "event": "pull_request",
        "status": "completed",
        "conclusion": "success",
        "head_sha": SHA,
        "head_repository": {"full_name": "o/r"},
        "pull_requests": [{"number": 5}],
    }
    r.update(kw)
    return r


def checks(sha=SHA, **kw):
    c = {"name": "test", "conclusion": "success", "head_sha": sha, "app": {"id": 15368}}
    c.update(kw)
    return {"total_count": 1, "check_runs": [c]}


MAIN = "m" * 40
GRUEN_MAIN = {
    "workflow_runs": [
        {
            "id": 1,
            "event": "push",
            "head_sha": MAIN,
            "status": "completed",
            "conclusion": "success",
            "created_at": "2026-10-18T10:00:00Z",
        }
    ]
}
KEIN_ISSUE = {"data": {"repository": {"pullRequest": {"closingIssuesReferences": {"nodes": []}}}}}


def lauf(
    name,
    erwartet,
    dateien=None,
    prd=None,
    rund=None,
    chk=None,
    head=SHA,
    writes=None,
    repo=None,
    check=None,
    prraw=None,
    akz=None,
    akz404=False,
    run_id="77",
    mainrun=None,
    mainruns=None,
    mainruns_nach=None,
    prruns=None,
    nach=None,
    closing=None,
    pulls=None,
    ref=None,
    marker=(),
    stdout=None,
    wartet=None,
    abfragen=None,
    commitpulls=None,
    mtoken="APP-TOKEN-XYZ",
    toks=None,
    spaeter=None,
    spaeter_ab=2,
):
    fx = tempfile.mkdtemp()
    for n, v in (
        ("pr", prd or pr()),
        ("run", rund or run()),
        ("checks", chk or checks()),
        ("files", dateien if dateien is not None else [datei("src/p/a.py")]),
        ("repo", repo or {"default_branch": "main", "allow_auto_merge": True}),
        ("akzeptanz", akz if akz is not None else [{"name": "test_a.py"}, {"name": "test_x.py"}]),
        ("main", {"sha": MAIN}),
        ("mainruns", mainruns if mainruns is not None else GRUEN_MAIN),
        ("prruns", prruns if prruns is not None else {"workflow_runs": []}),
        ("closing", closing if closing is not None else KEIN_ISSUE),
        ("ref", ref if ref is not None else {"object": {"sha": SHA}}),
        ("commit_pulls", commitpulls if commitpulls is not None else []),
    ):
        json.dump(v, open(os.path.join(fx, n + ".json"), "w"))
    for name_, wert_ in (
        ("main_run", mainrun),
        ("pr_nach", nach),
        ("pulls", pulls),
        ("mainruns_nach", mainruns_nach),
        ("mainruns_spaeter", spaeter),
        ("pr_wartet", wartet),
    ):
        if wert_ is not None:
            json.dump(wert_, open(os.path.join(fx, name_ + ".json"), "w"))
    if spaeter is not None:
        open(os.path.join(fx, "mainruns_spaeter_ab"), "w").write(str(spaeter_ab))
    if abfragen is not None:
        open(os.path.join(fx, "merge_nach_abfragen"), "w").write(str(abfragen))
    for m_ in marker:
        open(os.path.join(fx, m_), "w").write("1")
    if akz404:
        open(os.path.join(fx, "akzeptanz_404"), "w").write("1")
    if prraw is not None:
        open(os.path.join(fx, "pr.json"), "w").write(prraw)
    env = dict(
        os.environ,
        FIXDIR=fx,
        GH_BIN=f'"{sys.executable}" "{os.path.join(here, "fake_gh.py")}"',
        REPO="o/r",
        RUN_ID=run_id,
        HEAD_SHA=head,
        PYTHONIOENCODING="utf-8",
        WARTE_SEKUNDEN="0",
        CI_WARTE_SEKUNDEN="0",
        GH_TOKEN="DEFAULT-TOKEN-ABC",
        MERGE_TOKEN=mtoken,
    )
    r = subprocess.run(
        [sys.executable, "-I", GATE],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    wl = os.path.join(fx, "writes.log")
    alle = open(wl).read().strip().splitlines() if os.path.exists(wl) else []
    cs = [x for x in alle if x.startswith("check")]
    tk = [x for x in alle if x.startswith("tok ")]
    log = [x for x in alle if not x.startswith(("check", "tok "))]
    ok = (
        (r.returncode == 0) == (erwartet == "pass")
        and (writes is None or log == writes)
        and (check is None or cs == check)
    )
    ok = (
        ok
        and "APP-TOKEN-XYZ" not in r.stdout + r.stderr
        and "DEFAULT-TOKEN-ABC" not in r.stdout + r.stderr
    )
    if toks is not None:
        ok = ok and tk == toks
    if stdout is not None:
        ok = ok and all(x in r.stdout for x in stdout)
    if check is not None:
        log = log + cs
    print(
        f"{'OK  ' if ok else 'FEHL'} {name:<50} erwartet={erwartet:<4} "
        f"exit={r.returncode} writes={log}"
    )
    if not ok:
        print("     ", r.stdout.strip().replace("\n", " | "), r.stderr.strip()[:300])
        if os.environ.get("GATE_TEST_STOP_AT_FIRST_FAIL"):
            sys.exit(1)
    shutil.rmtree(fx)
    return ok


A = ["auto " + SHA]
D = ["disable-auto"]
res = []
R = res.append
# Bisherige Inhalts-Negativtests
R(
    lauf(
        "gueltiger Agenten-PR (src+tests)",
        "pass",
        [datei("src/p/a.py"), datei("tests/test_a.py")],
        writes=A,
    )
)
R(lauf("Draft-PR wird ready + auto", "pass", prd=pr(draft=True), writes=["ready"] + A))
R(lauf("Auto-Merge schon aktiv", "pass", prd=pr(auto_merge={"x": 1}), writes=[]))
R(
    lauf(
        "Mensch als Autor: ignoriert",
        "pass",
        [datei(".github/x.yml")],
        prd=pr(user={"login": "Inzaghi1983b", "type": "User"}),
        writes=[],
    )
)
R(
    lauf(
        "Datei .github/workflows",
        "fail",
        [datei("src/a.py"), datei(".github/workflows/ci.yml")],
        writes=D,
    )
)
R(lauf("AGENTS.md", "fail", [datei("AGENTS.md")], writes=D))
R(lauf("pyproject.toml", "fail", [datei("pyproject.toml")], writes=D))
R(lauf("Wurzel-Datei evil.py", "fail", [datei("evil.py")], writes=D))
R(
    lauf(
        "Rename src -> .github",
        "fail",
        [datei(".github/w.yml", status="renamed", previous_filename="src/a.py")],
        writes=D,
    )
)
R(lauf("Pfad mit /../", "fail", [datei("src/../x.py")], writes=D))
R(
    lauf(
        "Testdatei geloescht",
        "fail",
        [datei("tests/test_a.py", status="removed", patch="@@ -1 +0,0 @@\n-def test_a(): pass\n")],
        writes=D,
    )
)
R(
    lauf(
        "Test mit skip",
        "fail",
        [
            datei(
                "tests/test_a.py",
                patch="@@ -0,0 +1,2 @@\n+@pytest.mark.skip\n+def test_a(): pass\n",
            )
        ],
        writes=D,
    )
)
R(
    lauf(
        "Test mit xfail",
        "fail",
        [datei("tests/test_a.py", patch="@@ -0,0 +1 @@\n+@pytest.mark.xfail\n")],
        writes=D,
    )
)
R(
    lauf(
        "Test mit importorskip",
        "fail",
        [datei("tests/test_a.py", patch="@@ -0,0 +1 @@\n+x = pytest.importorskip('y')\n")],
        writes=D,
    )
)
R(
    lauf(
        "Assertions netto reduziert",
        "fail",
        [
            datei(
                "tests/test_a.py",
                status="modified",
                patch="@@ -1,3 +1,1 @@\n-    assert a == 1\n-    assert b == 2\n"
                "+    assert a == 1\n",
            )
        ],
        writes=D,
    )
)
R(
    lauf(
        "Assertions ersetzt (netto gleich)",
        "pass",
        [
            datei(
                "tests/test_a.py",
                status="modified",
                patch="@@ -1 +1 @@\n-    assert a == 1\n+    assert a == 2\n",
            )
        ],
        writes=A,
    )
)
R(
    lauf(
        "src importiert subprocess",
        "fail",
        [datei("src/p/a.py", patch="@@ -0,0 +1 @@\n+import subprocess\n")],
        writes=D,
    )
)
R(
    lauf(
        "src importiert requests",
        "fail",
        [datei("src/p/a.py", patch="@@ -0,0 +1 @@\n+from requests import get\n")],
        writes=D,
    )
)
R(
    lauf(
        "src os.system",
        "fail",
        [datei("src/p/a.py", patch="@@ -0,0 +1 @@\n+    os.system('x')\n")],
        writes=D,
    )
)
R(
    lauf(
        "src eval",
        "fail",
        [datei("src/p/a.py", patch="@@ -0,0 +1 @@\n+    y = eval(x)\n")],
        writes=D,
    )
)
R(
    lauf(
        "tests duerfen subprocess",
        "pass",
        [datei("tests/test_cli.py", patch="@@ -0,0 +1 @@\n+import subprocess\n")],
        writes=A,
    )
)
R(lauf("Binaerdatei ohne Patch", "fail", [datei("tests/d.bin", patch=None)], writes=D))
R(lauf("zu gross (801 Zeilen)", "fail", prd=pr(additions=801), writes=D))
R(lauf("genau 800 Zeilen ok", "pass", prd=pr(additions=800), writes=A))
R(lauf("Titel ohne Praefix", "fail", prd=pr(title="Sneaky"), writes=D))
R(lauf("51 Dateien", "fail", [datei(f"src/f{i}.py") for i in range(51)], writes=D))
R(lauf("50 Dateien (Paginierung) ok", "pass", [datei(f"src/f{i}.py") for i in range(50)], writes=A))
R(
    lauf(
        "Log-Injection im Patch",
        "fail",
        [datei("src/p/a.py", patch="@@ -0,0 +1 @@\n+import subprocess  ::set-output name=x::y\n")],
        writes=D,
    )
)
# Neue Gegenproben zum workflow_run-Pfad
R(
    lauf(
        "PR-HEAD veraltet (neuer Push nach CI)",
        "fail",
        prd=pr(head={"sha": "b" * 40, "repo": {"full_name": "o/r"}}),
        writes=[],
    )
)
R(lauf("Ereignis-HEAD != Lauf-HEAD", "fail", head="c" * 40, writes=[]))
R(
    lauf(
        "Lauf ohne PR-Zuordnung: nichts zu tun, kein Check",
        "pass",
        rund=run(pull_requests=[]),
        check=[],
        writes=[],
    )
)
R(
    lauf(
        "Lauf mit zwei PRs",
        "fail",
        rund=run(pull_requests=[{"number": 5}, {"number": 6}]),
        writes=[],
    )
)
R(lauf("falscher Workflow-Name", "fail", rund=run(name="Evil"), writes=[]))
R(lauf("falscher Workflow-Pfad", "fail", rund=run(path=".github/workflows/evil.yml"), writes=[]))
R(lauf("Lauf aus anderem Repo", "fail", rund=run(repository={"full_name": "x/y"}), writes=[]))
R(lauf("Lauf aus Fork", "fail", rund=run(head_repository={"full_name": "x/y"}), writes=[]))
R(
    lauf(
        "PR-Branch aus Fork",
        "fail",
        prd=pr(head={"sha": SHA, "repo": {"full_name": "x/y"}}),
        writes=[],
    )
)
R(
    lauf(
        "PR nicht gegen Standard-Branch",
        "fail",
        prd=pr(base={"ref": "dev", "repo": {"full_name": "o/r"}}),
        writes=[],
    )
)
R(
    lauf(
        "PR geschlossen (nicht gemergt): nichts, kein Check",
        "pass",
        prd=pr(state="closed"),
        check=[],
        writes=[],
    )
)
R(lauf("CI-Lauf rot", "fail", rund=run(conclusion="failure"), writes=[]))
R(lauf("CI-Lauf cancelled: nichts tun", "pass", rund=run(conclusion="cancelled"), writes=[]))
R(
    lauf(
        "CI-Lauf action_required: nichts tun",
        "pass",
        rund=run(conclusion="action_required"),
        writes=[],
    )
)
R(
    lauf(
        "CI-Lauf noch nicht fertig",
        "pass",
        rund=run(status="in_progress", conclusion=None),
        writes=[],
    )
)
R(lauf("Lauf nicht pull_request (push)", "pass", rund=run(event="push"), writes=[]))
R(lauf("Pflicht-Check fehlt", "fail", chk={"check_runs": []}, writes=[]))
R(lauf("Pflicht-Check rot", "fail", chk=checks(conclusion="failure"), writes=[]))
R(lauf("Pflicht-Check von falscher App", "fail", chk=checks(app={"id": 1}), writes=[]))
R(lauf("Pflicht-Check fuer anderen Commit", "fail", chk=checks(sha="d" * 40), writes=[]))
R(lauf("Pflicht-Check doppelt", "fail", chk={"check_runs": checks()["check_runs"] * 2}, writes=[]))
APP = {"login": SLUG + "[bot]", "type": "Bot"}
R(lauf("Autor eigene Mini-App: wird geprueft", "pass", prd=pr(user=APP), writes=A))
R(
    lauf(
        "Mini-App mit Verstoss: Auto-Merge aus",
        "fail",
        [datei(".github/x.yml")],
        prd=pr(user=APP),
        writes=D,
    )
)
R(
    lauf(
        "Mini-App mit pyproject.toml", "fail", [datei("pyproject.toml")], prd=pr(user=APP), writes=D
    )
)
R(
    lauf(
        "fremder Bot (dependabot): ignoriert",
        "pass",
        [datei(".github/x.yml")],
        prd=pr(user={"login": "dependabot[bot]", "type": "Bot"}),
        writes=[],
    )
)
R(
    lauf(
        "Mensch mit App-Namen (Typ User): ignoriert",
        "pass",
        [datei(".github/x.yml")],
        prd=pr(user={"login": SLUG + "[bot]", "type": "User"}),
        writes=[],
    )
)
R(
    lauf(
        "aehnlicher Name: ignoriert",
        "pass",
        [datei(".github/x.yml")],
        prd=pr(user={"login": SLUG + "-evil[bot]", "type": "Bot"}),
        writes=[],
    )
)
R(
    lauf(
        "Repo ohne Auto-Merge: keine Integration, kein ready",
        "pass",
        prd=pr(draft=True),
        repo={"default_branch": "main", "allow_auto_merge": False},
        writes=[],
    )
)
R(
    lauf(
        "allow_auto_merge fehlt in API: wie aus", "pass", repo={"default_branch": "main"}, writes=[]
    )
)
R(
    lauf(
        "Repo ohne Auto-Merge, Verstoss: weiter disable-auto",
        "fail",
        [datei("pyproject.toml")],
        repo={"default_branch": "main", "allow_auto_merge": False},
        writes=D,
    )
)

# Check-Run agent-gate (Pflicht-Check im Ruleset)
APPB = {"login": SLUG + "[bot]", "type": "Bot"}
NOAM = {"default_branch": "main", "allow_auto_merge": False}
R(lauf("Check: gueltiger Bot-PR -> success", "pass", check=["check success"], writes=A))
R(
    lauf(
        "Check: gueltiger Bot-PR, Auto-Merge aus -> success, kein Merge",
        "pass",
        repo=NOAM,
        check=["check success"],
        writes=[],
    )
)
R(lauf("Check: App-PR -> success", "pass", prd=pr(user=APPB), check=["check success"], writes=A))
R(
    lauf(
        "Check: Verstoss -> failure",
        "fail",
        [datei("pyproject.toml")],
        check=["check failure"],
        writes=D,
    )
)
R(
    lauf(
        "Check: Mensch -> success (nicht zustaendig)",
        "pass",
        prd=pr(user={"login": "Inzaghi1983b", "type": "User"}),
        check=["check success"],
        writes=[],
    )
)
R(
    lauf(
        "Check: PR-HEAD veraltet -> failure",
        "fail",
        prd=pr(head={"sha": "b" * 40, "repo": {"full_name": "o/r"}}),
        check=["check failure"],
        writes=[],
    )
)
R(
    lauf(
        "Check: CI rot -> failure",
        "fail",
        rund=run(conclusion="failure"),
        check=["check failure"],
        writes=[],
    )
)
R(
    lauf(
        "Check: ohne PR-Zuordnung -> kein Check",
        "pass",
        rund=run(pull_requests=[]),
        check=[],
        writes=[],
    )
)
R(
    lauf(
        "Check: Pflicht-Check fehlt -> failure",
        "fail",
        chk={"check_runs": []},
        check=["check failure"],
        writes=[],
    )
)
R(
    lauf(
        "Check: CI cancelled -> kein Check",
        "pass",
        rund=run(conclusion="cancelled"),
        check=[],
        writes=[],
    )
)
R(
    lauf(
        "Check: CI action_required -> kein Check",
        "pass",
        rund=run(conclusion="action_required"),
        check=[],
        writes=[],
    )
)
R(
    lauf(
        "Check: falscher Workflow -> kein Check", "fail", rund=run(name="Evil"), check=[], writes=[]
    )
)
R(
    lauf(
        "Check: Fork-Lauf -> kein Check",
        "fail",
        rund=run(head_repository={"full_name": "x/y"}),
        check=[],
        writes=[],
    )
)
R(
    lauf(
        "Check: kaputte API-Antwort -> kein Check (fail closed)",
        "fail",
        prraw="{kaputt",
        check=[],
        writes=[],
    )
)
CHK = checks()
CHK["check_runs"].append(
    {"name": "agent-gate", "conclusion": "failure", "head_sha": SHA, "app": {"id": 15368}, "id": 99}
)
R(
    lauf(
        "Check: vorhandener agent-gate wird aktualisiert statt doppelt",
        "pass",
        chk=CHK,
        check=["check-patch success"],
        writes=A,
    )
)

# --- A1: geschuetzte Akzeptanztests und deklarierte Abweichungen ---
AKZ = "tests/akzeptanz/test_x.py"
R(lauf("A1: Bot legt Akzeptanztest an", "fail", [datei(AKZ)], check=["check failure"], writes=D))
R(
    lauf(
        "A1: Bot aendert Akzeptanztest",
        "fail",
        [datei(AKZ, status="modified")],
        check=["check failure"],
        writes=D,
    )
)
R(
    lauf(
        "A1: Bot loescht Akzeptanztest",
        "fail",
        [datei(AKZ, status="removed", patch="@@ -1 +0,0 @@\n-def test_a(): pass\n")],
        writes=D,
    )
)
R(
    lauf(
        "A1: Rename aus akzeptanz heraus",
        "fail",
        [datei("tests/test_x.py", status="renamed", previous_filename=AKZ)],
        writes=D,
    )
)
R(
    lauf(
        "A1: Rename nach akzeptanz hinein",
        "fail",
        [datei(AKZ, status="renamed", previous_filename="tests/test_x.py")],
        writes=D,
    )
)
R(
    lauf(
        "A1: Gross-/Kleinschreibung Tests/Akzeptanz",
        "fail",
        [datei("tests/Akzeptanz/test_x.py")],
        writes=D,
    )
)
R(
    lauf(
        "A1: App-PR mit Akzeptanztest",
        "fail",
        [datei(AKZ)],
        prd=pr(user=APP),
        check=["check failure"],
        writes=D,
    )
)
R(
    lauf(
        "A1: aehnlicher Ordner tests/akzeptanz_alt ok",
        "pass",
        [datei("tests/akzeptanz_alt/test_x.py")],
        writes=A,
    )
)
R(lauf("A1: src/akzeptanz ok", "pass", [datei("src/akzeptanz/x.py")], writes=A))
for n, body in (
    ("Zeile ABWEICHUNG:", "## Aenderung\nABWEICHUNG: AC 3 anders umgesetzt\n"),
    ("kleingeschrieben", "abweichung: AC 3 anders"),
    ("Markdown fett", "- **ABWEICHUNG:** AC 3 anders"),
    ("Zitat", "> ABWEICHUNG: AC 3 anders"),
    ("eingerueckt", "   ABWEICHUNG: AC 3 anders"),
    ("leer (unfertig)", "ABWEICHUNG:"),
    ("Log-Injection", "ABWEICHUNG: ::set-output name=x::y"),
):
    R(
        lauf(
            f"A1: {n} -> failure, kein Merge",
            "fail",
            prd=pr(body=body),
            check=["check failure"],
            writes=D,
        )
    )
for n, body in (
    ("ABWEICHUNG: keine", "ABWEICHUNG: keine"),
    ("ABWEICHUNG: -", "ABWEICHUNG: -"),
    ("ABWEICHUNG: nein.", "**ABWEICHUNG:** nein."),
    ("Abweichungen: keine (anderes Wort)", "Abweichungen: keine"),
    ("Prosa keine Abweichung", "Es gibt keine Abweichung vom Auftrag."),
    ("Prosa mit Doppelpunkt davor", "Hinweis: Abweichung wurde nicht noetig"),
    ("kein Body", None),
):
    R(lauf(f"A1: {n} -> ok", "pass", prd=pr(body=body), check=["check success"], writes=A))
R(
    lauf(
        "A1: ABWEICHUNG bei App-PR",
        "fail",
        prd=pr(user=APP, body="ABWEICHUNG: x"),
        check=["check failure"],
        writes=D,
    )
)
R(
    lauf(
        "A1: Mensch-PR mit ABWEICHUNG: ignoriert",
        "pass",
        prd=pr(user={"login": "Inzaghi1983b", "type": "User"}, body="ABWEICHUNG: x"),
        check=["check success"],
        writes=[],
    )
)
R(
    lauf(
        "A1: ABWEICHUNG bei Auto-Merge aus: failure",
        "fail",
        prd=pr(body="ABWEICHUNG: x"),
        repo={"default_branch": "main", "allow_auto_merge": False},
        check=["check failure"],
        writes=D,
    )
)

# Replay mit den echten PR-Texten aus ch-import (Stand 2026-10-18). Die Texte enthalten noch keine
# ABWEICHUNG-Zeile (Regel neu): erwartet keine Falsch-Positive. Mit Zeile muss es rot werden.
fx_dir = os.path.join(here, "fixtures")
for nr in (24, 25, 30, 37):
    body = open(os.path.join(fx_dir, f"pr-{nr}-body.md"), encoding="utf-8").read()
    R(
        lauf(
            f"A1 Replay PR #{nr}: unveraendert ok",
            "pass",
            prd=pr(user=APP, body=body),
            check=["check success"],
            writes=A,
        )
    )
    R(
        lauf(
            f"A1 Replay PR #{nr}: mit ABWEICHUNG-Zeile rot",
            "fail",
            prd=pr(user=APP, body=body + "\nABWEICHUNG: Acceptance Criterion anders umgesetzt\n"),
            check=["check failure"],
            writes=D,
        )
    )


# --- C1: Spec-first-Pflicht (Akzeptanztest muss auf dem Standard-Branch existieren) ---
def spec(*namen):
    return [{"name": n} for n in namen]


R(
    lauf(
        "C1: Modul mit Akzeptanztest -> ok",
        "pass",
        [datei("src/chimport/jahr.py")],
        akz=spec("test_jahr.py"),
        check=["check success"],
        writes=A,
    )
)
R(
    lauf(
        "C1: Modul ohne Akzeptanztest -> failure",
        "fail",
        [datei("src/chimport/jahr.py")],
        akz=spec("test_plz.py"),
        check=["check failure"],
        writes=D,
    )
)
R(
    lauf(
        "C1: leeres Verzeichnis -> failure",
        "fail",
        [datei("src/chimport/jahr.py")],
        akz=[],
        check=["check failure"],
        writes=D,
    )
)
R(
    lauf(
        "C1: Verzeichnis fehlt (404) -> failure",
        "fail",
        [datei("src/chimport/jahr.py")],
        akz404=True,
        check=["check failure"],
        writes=D,
    )
)
R(
    lauf(
        "C1: API liefert Muell -> failure (fail closed)",
        "fail",
        [datei("src/chimport/jahr.py")],
        akz={"message": "x"},
        check=["check failure"],
        writes=D,
    )
)
R(
    lauf(
        "C1: zwei Module, eines ohne Spec -> failure",
        "fail",
        [datei("src/chimport/jahr.py"), datei("src/chimport/neu.py")],
        akz=spec("test_jahr.py"),
        check=["check failure"],
        writes=D,
    )
)
R(
    lauf(
        "C1: zwei Module mit Spec -> ok",
        "pass",
        [datei("src/chimport/jahr.py"), datei("src/chimport/neu.py"), datei("tests/test_neu.py")],
        akz=spec("test_jahr.py", "test_neu.py"),
        check=["check success"],
        writes=A,
    )
)
R(
    lauf(
        "C1: __init__/__main__/_privat brauchen keine Spec",
        "pass",
        [
            datei("src/chimport/__init__.py"),
            datei("src/chimport/__main__.py"),
            datei("src/chimport/_hilfe.py"),
        ],
        akz=[],
        check=["check success"],
        writes=A,
    )
)
R(
    lauf(
        "C1: nur Tests geaendert -> ok ohne Spec",
        "pass",
        [datei("tests/test_jahr.py")],
        akz=[],
        check=["check success"],
        writes=A,
    )
)
R(
    lauf(
        "C1: geloeschtes Modul braucht keine Spec",
        "pass",
        [datei("src/chimport/alt.py", status="removed", patch="@@ -1 +0,0 @@\n-x = 1\n")],
        akz=[],
        check=["check success"],
        writes=A,
    )
)
R(
    lauf(
        "C1: Spec-Datei anderer Name zaehlt nicht",
        "fail",
        [datei("src/chimport/jahr.py")],
        akz=spec("jahr.py", "test_jahr_alt.py", "README.md"),
        check=["check failure"],
        writes=D,
    )
)
R(
    lauf(
        "C1: Auto-Merge aus + Spec fehlt -> failure",
        "fail",
        [datei("src/chimport/jahr.py")],
        akz=[],
        repo={"default_branch": "main", "allow_auto_merge": False},
        check=["check failure"],
        writes=D,
    )
)
R(
    lauf(
        "C1: App-PR ohne Spec -> failure",
        "fail",
        [datei("src/chimport/jahr.py")],
        prd=pr(user=APP),
        akz=[],
        check=["check failure"],
        writes=D,
    )
)
R(
    lauf(
        "C1: Mensch-PR ohne Spec: ignoriert",
        "pass",
        [datei("src/chimport/jahr.py")],
        prd=pr(user={"login": "Inzaghi1983b", "type": "User"}),
        akz=[],
        check=["check success"],
        writes=[],
    )
)


# --- A2: Kill-Switch, Nach-Merge (CI, Issues, Branch), Neubewertung nach gruener CI auf main ---
def mainlauf(
    status="completed",
    conclusion="success",
    sha=MAIN,
    event="push",
    alter="2026-10-18T10:00:00Z",
    nr=1,
):
    return {
        "id": nr,
        "event": event,
        "head_sha": sha,
        "status": status,
        "conclusion": conclusion,
        "created_at": alter,
    }


def liste(*laeufe):
    return {"workflow_runs": list(laeufe)}


def issues(*nummern, zustand="OPEN", repo="o/r"):
    knoten = [
        {"number": n, "state": zustand, "repository": {"nameWithOwner": repo}} for n in nummern
    ]
    return {"data": {"repository": {"pullRequest": {"closingIssuesReferences": {"nodes": knoten}}}}}


def mit_ref(ref="feature/issue-1-x", repo_pr="o/r", merged=False, **kw):
    p = pr(**kw)
    p["head"] = {"sha": SHA, "ref": ref, "repo": {"full_name": repo_pr}}
    if merged:
        p["merged"] = True
        p["state"] = "closed"
    return p


def gemergt(**kw):
    return mit_ref(merged=True, **kw)


MENSCH = {"login": "Inzaghi1983b", "type": "User"}
ROT = liste(mainlauf(conclusion="failure"))
NEU_OHNE_CI = liste()
BRANCH = "branch-delete feature/issue-1-x"

# Kill-Switch
R(lauf("A2 Kill-Switch: main-CI gruen -> weiter", "pass", check=["check success"], writes=A))
R(
    lauf(
        "A2 Kill-Switch: main-CI rot -> failure",
        "fail",
        mainruns=ROT,
        check=["check failure"],
        writes=D,
        stdout=["Kill-Switch", "nicht gruen"],
    )
)
R(
    lauf(
        "A2 Kill-Switch: main-CI cancelled -> failure",
        "fail",
        mainruns=liste(mainlauf(conclusion="cancelled")),
        check=["check failure"],
        writes=D,
    )
)
R(
    lauf(
        "A2 Kill-Switch: main-CI laeuft -> failure",
        "fail",
        mainruns=liste(mainlauf(status="in_progress", conclusion=None)),
        check=["check failure"],
        writes=D,
        stdout=["laeuft noch"],
    )
)
R(
    lauf(
        "A2 Kill-Switch: keine CI fuer main-HEAD -> failure",
        "fail",
        mainruns=NEU_OHNE_CI,
        check=["check failure"],
        writes=D,
        stdout=["keine CI auf main"],
    )
)
R(
    lauf(
        "A2 Kill-Switch: CI nur fuer anderen Commit -> failure",
        "fail",
        mainruns=liste(mainlauf(sha="z" * 40)),
        check=["check failure"],
        writes=D,
    )
)
R(
    lauf(
        "A2 Kill-Switch: neuester Lauf rot, aelterer gruen -> failure",
        "fail",
        mainruns=liste(
            mainlauf(nr=1), mainlauf(conclusion="failure", alter="2026-10-18T11:00:00Z", nr=2)
        ),
        check=["check failure"],
        writes=D,
    )
)
R(
    lauf(
        "A2 Kill-Switch: neuester Lauf gruen, aelterer rot -> weiter",
        "pass",
        mainruns=liste(
            mainlauf(conclusion="failure", nr=1), mainlauf(alter="2026-10-18T11:00:00Z", nr=2)
        ),
        check=["check success"],
        writes=A,
    )
)
R(
    lauf(
        "A2 Kill-Switch: workflow_dispatch-Lauf zaehlt",
        "pass",
        mainruns=liste(mainlauf(event="workflow_dispatch")),
        check=["check success"],
        writes=A,
    )
)
R(
    lauf(
        "A2 Kill-Switch: pull_request-Lauf auf main-SHA zaehlt nicht",
        "fail",
        mainruns=liste(mainlauf(event="pull_request")),
        check=["check failure"],
        writes=D,
    )
)
R(
    lauf(
        "A2 Kill-Switch: Antwort kaputt -> failure (fail closed)",
        "fail",
        mainruns={"x": 1},
        check=["check failure"],
        writes=D,
        stdout=["nicht lesbar"],
    )
)
R(
    lauf(
        "A2 Kill-Switch: main rot, Mensch-PR -> success",
        "pass",
        prd=pr(user=MENSCH),
        mainruns=ROT,
        check=["check success"],
        writes=[],
    )
)
R(
    lauf(
        "A2 Kill-Switch: Auto-Merge aus + main rot -> failure",
        "fail",
        mainruns=ROT,
        repo={"default_branch": "main", "allow_auto_merge": False},
        check=["check failure"],
        writes=D,
    )
)
R(
    lauf(
        "A2 Kill-Switch: Verstoss hat Vorrang (Meldung)",
        "fail",
        [datei("pyproject.toml")],
        mainruns=ROT,
        check=["check failure"],
        writes=D,
        stdout=["Gate NICHT bestanden"],
    )
)

# Nach sofortigem Merge: CI auf main, Issues, Branch
VOLL = A + ["ci-dispatch main", "issue-close 7", BRANCH]
R(
    lauf(
        "A2 Nach-Merge: CI, Issue und Branch",
        "pass",
        prd=mit_ref(),
        nach=gemergt(),
        closing=issues(7),
        mainruns_nach=NEU_OHNE_CI,
        check=["check success"],
        writes=VOLL,
    )
)
R(
    lauf(
        "A2 Nach-Merge: Draft wird ready, dann alles",
        "pass",
        prd=mit_ref(draft=True),
        nach=gemergt(),
        closing=issues(7),
        mainruns_nach=NEU_OHNE_CI,
        writes=["ready"] + VOLL,
    )
)
R(
    lauf(
        "A2 Nach-Merge: CI fuer neuen Stand schon da -> kein zweiter Dispatch",
        "pass",
        prd=mit_ref(),
        nach=gemergt(),
        closing=issues(7),
        writes=A + ["issue-close 7", BRANCH],
    )
)
R(
    lauf(
        "A2 Nach-Merge: CI laeuft schon -> kein zweiter Dispatch",
        "pass",
        prd=mit_ref(),
        nach=gemergt(),
        closing=issues(7),
        mainruns_nach=liste(mainlauf(status="in_progress", conclusion=None)),
        writes=A + ["issue-close 7", BRANCH],
    )
)
R(
    lauf(
        "A2 Nach-Merge: zwei Issues",
        "pass",
        prd=mit_ref(),
        nach=gemergt(),
        closing=issues(7, 8),
        mainruns_nach=NEU_OHNE_CI,
        writes=A + ["ci-dispatch main", "issue-close 7", "issue-close 8", BRANCH],
    )
)
R(
    lauf(
        "A2 Nach-Merge: keine verknuepften Issues",
        "pass",
        prd=mit_ref(),
        nach=gemergt(),
        mainruns_nach=NEU_OHNE_CI,
        writes=A + ["ci-dispatch main", BRANCH],
    )
)
R(
    lauf(
        "A2 Nach-Merge: Issue schon geschlossen -> nicht erneut",
        "pass",
        prd=mit_ref(),
        nach=gemergt(),
        closing=issues(7, zustand="CLOSED"),
        mainruns_nach=NEU_OHNE_CI,
        writes=A + ["ci-dispatch main", BRANCH],
    )
)
R(
    lauf(
        "A2 Nach-Merge: Issue aus anderem Repo -> nicht anfassen",
        "pass",
        prd=mit_ref(),
        nach=gemergt(),
        closing=issues(7, repo="x/y"),
        mainruns_nach=NEU_OHNE_CI,
        writes=A + ["ci-dispatch main", BRANCH],
    )
)
R(
    lauf(
        "A2 Nach-Merge: Auto-Merge wartet (nicht gemergt) -> kein Nachlauf",
        "pass",
        prd=mit_ref(),
        closing=issues(7),
        writes=A,
    )
)
R(
    lauf(
        "A2 Nach-Merge: Branch im Fork -> nicht loeschen",
        "pass",
        prd=mit_ref(),
        nach=gemergt(repo_pr="x/y"),
        closing=issues(7),
        mainruns_nach=NEU_OHNE_CI,
        writes=A + ["ci-dispatch main", "issue-close 7"],
    )
)
R(
    lauf(
        "A2 Nach-Merge: Head-Branch heisst wie Standard-Branch -> nicht loeschen",
        "pass",
        prd=mit_ref(),
        nach=gemergt(ref="main"),
        closing=issues(7),
        mainruns_nach=NEU_OHNE_CI,
        writes=A + ["ci-dispatch main", "issue-close 7"],
    )
)
R(
    lauf(
        "A2 Nach-Merge: Branch weitergezogen -> nicht loeschen",
        "pass",
        prd=mit_ref(),
        nach=gemergt(),
        closing=issues(7),
        ref={"object": {"sha": "9" * 40}},
        mainruns_nach=NEU_OHNE_CI,
        writes=A + ["ci-dispatch main", "issue-close 7"],
    )
)
R(
    lauf(
        "A2 Nach-Merge: Branch schon weg (404) -> ok",
        "pass",
        prd=mit_ref(),
        nach=gemergt(),
        closing=issues(7),
        marker=["ref_404"],
        mainruns_nach=NEU_OHNE_CI,
        writes=A + ["ci-dispatch main", "issue-close 7"],
    )
)
R(
    lauf(
        "A2 Nach-Merge: Branch-Branch mit Sonderzeichen wird kodiert",
        "pass",
        prd=mit_ref(ref="feature/a b#c"),
        nach=gemergt(ref="feature/a b#c"),
        closing=issues(7),
        mainruns_nach=NEU_OHNE_CI,
        writes=A + ["ci-dispatch main", "issue-close 7", "branch-delete feature/a%20b%23c"],
    )
)

# Fehlende Berechtigungen / Fehler: Merge bleibt, Rest laeuft weiter, Job wird rot
R(
    lauf(
        "A2 Fehler: CI-Dispatch verboten -> Rest laeuft, exit 1",
        "fail",
        prd=mit_ref(),
        nach=gemergt(),
        closing=issues(7),
        marker=["fail_dispatch"],
        mainruns_nach=NEU_OHNE_CI,
        check=["check success"],
        writes=A + ["issue-close 7", BRANCH],
        stdout=["NICHT ausgeloest"],
    )
)
R(
    lauf(
        "A2 Fehler: Issue schliessen verboten -> Rest laeuft, exit 1",
        "fail",
        prd=mit_ref(),
        nach=gemergt(),
        closing=issues(7),
        marker=["fail_issue"],
        mainruns_nach=NEU_OHNE_CI,
        writes=A + ["ci-dispatch main", BRANCH],
        stdout=["NICHT geschlossen"],
    )
)
R(
    lauf(
        "A2 Fehler: Branch loeschen verboten -> exit 1",
        "fail",
        prd=mit_ref(),
        nach=gemergt(),
        closing=issues(7),
        marker=["fail_delete"],
        mainruns_nach=NEU_OHNE_CI,
        writes=A + ["ci-dispatch main", "issue-close 7"],
        stdout=["NICHT geloescht"],
    )
)
R(
    lauf(
        "A2 Fehler: GraphQL verboten -> exit 1, Branch trotzdem",
        "fail",
        prd=mit_ref(),
        nach=gemergt(),
        marker=["fail_graphql"],
        mainruns_nach=NEU_OHNE_CI,
        writes=A + ["ci-dispatch main", BRANCH],
    )
)
R(
    lauf(
        "A2 Fehler: Branch-Abfrage 403 -> exit 1, nicht loeschen",
        "fail",
        prd=mit_ref(),
        nach=gemergt(),
        closing=issues(7),
        marker=["fail_ref_403"],
        mainruns_nach=NEU_OHNE_CI,
        writes=A + ["ci-dispatch main", "issue-close 7"],
    )
)

# Wiederholung nach bereits erfolgtem Merge (idempotent)
R(
    lauf(
        "A2 Wiederholung: gemergter PR, Rest nachholen",
        "pass",
        prd=gemergt(),
        closing=issues(7),
        writes=["issue-close 7", BRANCH],
        check=[],
    )
)
R(
    lauf(
        "A2 Wiederholung: nichts mehr zu tun",
        "pass",
        prd=gemergt(),
        closing=issues(7, zustand="CLOSED"),
        marker=["ref_404"],
        writes=[],
        check=[],
    )
)
R(
    lauf(
        "A2 Wiederholung: CI fehlt noch -> Dispatch",
        "pass",
        prd=gemergt(),
        mainruns=NEU_OHNE_CI,
        closing=issues(),
        marker=["ref_404"],
        writes=["ci-dispatch main"],
        check=[],
    )
)
R(
    lauf(
        "A2 Wiederholung: gemergter Mensch-PR ignoriert",
        "pass",
        prd=gemergt(user=MENSCH),
        closing=issues(7),
        writes=[],
        check=[],
    )
)

# Neubewertung nach gruener CI auf main
BOT_PR = {
    "number": 5,
    "user": {"login": "github-actions[bot]", "type": "Bot"},
    "head": {"sha": SHA, "repo": {"full_name": "o/r"}},
}
PRRUN = liste(
    {"id": 900, "head_sha": SHA, "conclusion": "success", "created_at": "2026-10-18T09:00:00Z"}
)
MAINRUN = {
    "repository": {"full_name": "o/r"},
    "name": "CI",
    "path": ".github/workflows/ci.yml",
    "event": "push",
    "status": "completed",
    "conclusion": "success",
    "head_sha": MAIN,
    "head_branch": "main",
    "head_repository": {"full_name": "o/r"},
}


def n_lauf(name, erwartet, **kw):
    kw.setdefault("rund", None)
    kw.setdefault("mainrun", MAINRUN)
    kw.setdefault("pulls", [BOT_PR])
    kw.setdefault("prruns", PRRUN)
    return lauf(name, erwartet, run_id="main", head=MAIN, **kw)


R(
    n_lauf(
        "A2 Neubewertung: gruener PR wird gemergt + aufgeraeumt",
        "pass",
        prd=mit_ref(),
        nach=gemergt(),
        closing=issues(7),
        mainruns_nach=NEU_OHNE_CI,
        check=["check success"],
        writes=VOLL,
    )
)
R(
    n_lauf(
        "A2 Neubewertung: Auto-Merge aus -> nur Check success",
        "pass",
        prd=mit_ref(),
        repo={"default_branch": "main", "allow_auto_merge": False},
        check=["check success"],
        writes=[],
    )
)
R(
    n_lauf(
        "A2 Neubewertung: Check wird aktualisiert statt doppelt",
        "pass",
        prd=mit_ref(),
        repo={"default_branch": "main", "allow_auto_merge": False},
        chk={
            "check_runs": [
                dict(checks()["check_runs"][0]),
                {
                    "name": "agent-gate",
                    "conclusion": "failure",
                    "head_sha": SHA,
                    "app": {"id": 15368},
                    "id": 99,
                },
            ]
        },
        check=["check-patch success"],
        writes=[],
    )
)
R(n_lauf("A2 Neubewertung: keine offenen PRs", "pass", pulls=[], writes=[], check=[]))
R(
    n_lauf(
        "A2 Neubewertung: PR ohne gruene CI -> uebersprungen",
        "pass",
        prruns=liste(),
        writes=[],
        check=[],
    )
)
R(
    n_lauf(
        "A2 Neubewertung: CI-Lauf fuer anderen Commit -> uebersprungen",
        "pass",
        prruns=liste(
            {
                "id": 900,
                "head_sha": "q" * 40,
                "conclusion": "success",
                "created_at": "2026-10-18T09:00:00Z",
            }
        ),
        writes=[],
        check=[],
    )
)
R(
    n_lauf(
        "A2 Neubewertung: Mensch-PR in Liste ignoriert",
        "pass",
        pulls=[dict(BOT_PR, user=MENSCH)],
        writes=[],
        check=[],
    )
)
R(
    n_lauf(
        "A2 Neubewertung: Fork-PR ignoriert",
        "pass",
        pulls=[dict(BOT_PR, head={"sha": SHA, "repo": {"full_name": "x/y"}})],
        writes=[],
        check=[],
    )
)
R(
    n_lauf(
        "A2 Neubewertung: Fork ohne Repo (geloescht) ignoriert",
        "pass",
        pulls=[dict(BOT_PR, head={"sha": SHA, "repo": None})],
        writes=[],
        check=[],
    )
)
R(
    n_lauf(
        "A2 Neubewertung: main-CI rot -> nichts",
        "pass",
        mainrun=dict(MAINRUN, conclusion="failure"),
        writes=[],
        check=[],
    )
)
R(
    n_lauf(
        "A2 Neubewertung: Lauf nicht zum aktuellen main-Stand -> nichts",
        "pass",
        mainrun=dict(MAINRUN, head_sha="y" * 40),
        writes=[],
        check=[],
    )
)
R(
    n_lauf(
        "A2 Neubewertung: Lauf eines anderen Branches -> nichts",
        "pass",
        mainrun=dict(MAINRUN, head_branch="dev"),
        writes=[],
        check=[],
    )
)
R(
    n_lauf(
        "A2 Neubewertung: Lauf aus Fork -> nichts",
        "pass",
        mainrun=dict(MAINRUN, head_repository={"full_name": "x/y"}),
        writes=[],
        check=[],
    )
)
R(
    n_lauf(
        "A2 Neubewertung: falscher Workflow -> stopp",
        "fail",
        mainrun=dict(MAINRUN, name="Evil"),
        writes=[],
        check=[],
    )
)
R(
    n_lauf(
        "A2 Neubewertung: main-CI laeuft (neuer Lauf) -> nichts",
        "pass",
        mainruns=liste(
            mainlauf(),
            mainlauf(status="in_progress", conclusion=None, alter="2026-10-18T12:00:00Z", nr=2),
        ),
        writes=[],
        check=[],
    )
)
R(
    n_lauf(
        "A2 Neubewertung: Verstoss im PR -> failure, kein Merge",
        "pass",
        prd=mit_ref(),
        dateien=[datei("pyproject.toml")],
        check=["check failure"],
        writes=D,
    )
)
R(
    n_lauf(
        "A2 Neubewertung: kaputte PR-Antwort -> Fehler, exit 1",
        "fail",
        prraw="{kaputt",
        writes=[],
        check=[],
    )
)
R(
    n_lauf(
        "A2 Neubewertung: nur ein Merge je main-CI (zwei PRs)",
        "pass",
        prd=mit_ref(),
        nach=gemergt(),
        pulls=[BOT_PR, dict(BOT_PR, number=6)],
        closing=issues(7),
        mainruns_nach=NEU_OHNE_CI,
        check=["check success"],
        writes=VOLL,
    )
)
R(
    lauf(
        "A2: Push-CI auf Nicht-Standard-Branch -> uebersprungen",
        "pass",
        run_id="main",
        head=MAIN,
        mainrun=dict(MAINRUN, head_branch="dev"),
        writes=[],
        check=[],
    )
)
R(
    lauf(
        "A2: Lauf eines unbekannten Ereignisses -> uebersprungen",
        "pass",
        run_id="main",
        head=MAIN,
        mainrun=dict(MAINRUN, event="schedule"),
        writes=[],
        check=[],
    )
)

R(
    n_lauf(
        "A2 Neubewertung: Fehler im Nach-Merge -> exit 1",
        "fail",
        prd=mit_ref(),
        nach=gemergt(),
        closing=issues(7),
        marker=["fail_dispatch"],
        mainruns_nach=NEU_OHNE_CI,
        check=["check success"],
        writes=A + ["issue-close 7", BRANCH],
    )
)
R(
    n_lauf(
        "A2 Neubewertung: Issue-Fehler im Nach-Merge -> exit 1",
        "fail",
        prd=mit_ref(),
        nach=gemergt(),
        closing=issues(7),
        marker=["fail_issue"],
        mainruns_nach=NEU_OHNE_CI,
        writes=A + ["ci-dispatch main", BRANCH],
    )
)
R(
    n_lauf(
        "A2 Neubewertung: anderer Bot (dependabot) in Liste ignoriert",
        "pass",
        pulls=[dict(BOT_PR, user={"login": "dependabot[bot]", "type": "Bot"})],
        writes=[],
        check=[],
    )
)


# --- A2b: PR-Zuordnung nach dem Merge, begrenztes Warten auf verzoegertes Auto-Merge ---
def commit_pr(nr=5, merged=True, sha=SHA, repo_name="o/r", base_repo="o/r"):
    return {
        "number": nr,
        "state": "closed" if merged else "open",
        "merged_at": "2026-10-18T10:00:00Z" if merged else None,
        "head": {"sha": sha, "repo": {"full_name": repo_name}},
        "base": {"repo": {"full_name": base_repo}},
    }


OHNE = run(pull_requests=[])
WARTET = {"x": 1}


def mit_head(p, sha):
    p["head"]["sha"] = sha
    return p


# Zuordnung ueber den Commit (CI-Re-Run nach dem Merge: pull_requests ist leer)
R(
    lauf(
        "A2b Retry: gemergter Bot-PR ueber Commit gefunden, Rest nachgeholt",
        "pass",
        rund=OHNE,
        commitpulls=[commit_pr()],
        prd=gemergt(),
        closing=issues(7),
        writes=["issue-close 7", BRANCH],
        check=[],
    )
)
R(
    lauf(
        "A2b Retry: App-PR ueber Commit gefunden",
        "pass",
        rund=OHNE,
        commitpulls=[commit_pr()],
        prd=gemergt(user=APP),
        closing=issues(7),
        writes=["issue-close 7", BRANCH],
        check=[],
    )
)
R(
    lauf(
        "A2b Retry: CI auf main fehlt -> Dispatch nachgeholt",
        "pass",
        rund=OHNE,
        commitpulls=[commit_pr()],
        prd=gemergt(),
        mainruns=NEU_OHNE_CI,
        closing=issues(),
        marker=["ref_404"],
        writes=["ci-dispatch main"],
        check=[],
    )
)
R(
    lauf(
        "A2b Retry: alles schon erledigt -> keine Schreibaufrufe (idempotent)",
        "pass",
        rund=OHNE,
        commitpulls=[commit_pr()],
        prd=gemergt(),
        closing=issues(7, zustand="CLOSED"),
        marker=["ref_404"],
        writes=[],
        check=[],
    )
)
R(
    lauf(
        "A2b Retry: kein gemergter PR zum Commit -> nichts, kein Check",
        "pass",
        rund=OHNE,
        commitpulls=[],
        writes=[],
        check=[],
    )
)
R(
    lauf(
        "A2b Retry: nur offener PR zum Commit -> nichts, kein Check",
        "pass",
        rund=OHNE,
        commitpulls=[commit_pr(merged=False)],
        writes=[],
        check=[],
    )
)
R(
    lauf(
        "A2b Retry: zwei gemergte PRs (mehrdeutig) -> exit 1, kein Check",
        "fail",
        rund=OHNE,
        commitpulls=[commit_pr(5), commit_pr(6)],
        prd=gemergt(),
        closing=issues(7),
        writes=[],
        check=[],
    )
)
R(
    lauf(
        "A2b Retry: PR mit anderem Head-Commit wird ignoriert",
        "pass",
        rund=OHNE,
        commitpulls=[commit_pr(sha="b" * 40)],
        writes=[],
        check=[],
    )
)
R(
    lauf(
        "A2b Retry: Fork-PR wird ignoriert",
        "pass",
        rund=OHNE,
        commitpulls=[commit_pr(repo_name="x/y")],
        writes=[],
        check=[],
    )
)
R(
    lauf(
        "A2b Retry: PR-Zuordnung unlesbar -> exit 1, kein Check",
        "fail",
        rund=OHNE,
        commitpulls={"message": "Server Error"},
        writes=[],
        check=[],
    )
)
R(
    lauf(
        "A2b Retry: gemergter PR mit anderem HEAD -> nichts",
        "pass",
        rund=OHNE,
        commitpulls=[commit_pr()],
        prd=mit_head(gemergt(), "b" * 40),
        closing=issues(7),
        writes=[],
        check=[],
    )
)
R(
    lauf(
        "A2b gemergter PR, CI-Re-Run rot -> kein Failure-Check, Rest nachgeholt",
        "pass",
        rund=run(conclusion="failure"),
        prd=gemergt(),
        closing=issues(7),
        writes=["issue-close 7", BRANCH],
        check=[],
    )
)
R(
    lauf(
        "A2b geschlossener (nicht gemergter) Bot-PR mit roter CI -> kein Check",
        "pass",
        rund=run(conclusion="failure"),
        prd=pr(state="closed"),
        writes=[],
        check=[],
    )
)
R(
    lauf(
        "A2b offener Bot-PR mit roter CI -> weiter Failure-Check",
        "fail",
        rund=run(conclusion="failure"),
        check=["check failure"],
        writes=[],
    )
)

# Begrenztes Warten, wenn GitHub den Merge verzoegert
R(
    lauf(
        "A2b Warten: Merge nach 2 Abfragen -> Nachlauf",
        "pass",
        prd=mit_ref(),
        wartet=mit_ref(auto_merge=WARTET),
        nach=gemergt(),
        abfragen=2,
        closing=issues(7),
        mainruns_nach=NEU_OHNE_CI,
        check=["check success"],
        writes=VOLL,
    )
)
R(
    lauf(
        "A2b Warten: Draft, Merge nach 1 Abfrage -> ready, Nachlauf",
        "pass",
        prd=mit_ref(draft=True),
        wartet=mit_ref(auto_merge=WARTET),
        nach=gemergt(),
        abfragen=1,
        closing=issues(7),
        mainruns_nach=NEU_OHNE_CI,
        writes=["ready"] + VOLL,
    )
)
R(
    lauf(
        "A2b Warten: nie gemergt -> exit 0, kein Nachlauf, Hinweis",
        "pass",
        prd=mit_ref(),
        wartet=mit_ref(auto_merge=WARTET),
        writes=A,
        stdout=["Nicht innerhalb", "CI-Re-Run"],
    )
)
R(
    lauf(
        "A2b Warten: Auto-Merge zurueckgenommen -> Abbruch ohne Warten",
        "pass",
        prd=mit_ref(),
        wartet=mit_ref(),
        writes=A,
        stdout=["kein Warten"],
    )
)
R(
    lauf(
        "A2b Warten: HEAD geaendert -> Abbruch",
        "pass",
        prd=mit_ref(),
        wartet=mit_head(mit_ref(auto_merge=WARTET), "b" * 40),
        writes=A,
        stdout=["kein Warten"],
    )
)
R(
    lauf(
        "A2b Warten: PR geschlossen -> Abbruch",
        "pass",
        prd=mit_ref(),
        wartet=mit_ref(auto_merge=WARTET, state="closed"),
        writes=A,
        stdout=["kein Warten"],
    )
)
R(
    lauf(
        "A2b Warten: Zustand unlesbar -> exit 1",
        "fail",
        prd=mit_ref(),
        wartet="kaputt",
        writes=A,
        stdout=["nicht lesbar"],
    )
)
R(
    lauf(
        "A2b Warten: Auto-Merge schon aktiv -> kein zweiter Aufruf, kein Warten",
        "pass",
        prd=mit_ref(auto_merge=WARTET),
        writes=[],
    )
)
R(
    n_lauf(
        "A2b Neubewertung: verzoegerter Merge zaehlt (nur ein PR je CI-Zyklus)",
        "pass",
        prd=mit_ref(),
        pulls=[BOT_PR, dict(BOT_PR, number=6)],
        wartet=mit_ref(auto_merge=WARTET),
        writes=A,
        stdout=["Es wurde schon gemergt"],
    )
)
R(
    n_lauf(
        "A2b Neubewertung: verzoegerter Merge, dann Nachlauf-Schritte",
        "pass",
        prd=mit_ref(),
        wartet=mit_ref(auto_merge=WARTET),
        nach=gemergt(),
        abfragen=1,
        closing=issues(7),
        mainruns_nach=NEU_OHNE_CI,
        check=["check success"],
        writes=VOLL,
    )
)


# --- G1: Merge mit App-Token (Token-Trennung, fail closed, YAML-Gates, Push-CI-Wartezeit) ---
CHK = "tok check default"
MERGE_APP = "tok merge-auto app"
READY_APP = "tok ready app"
NACH = ["tok ci-dispatch default", "tok issue-close default", "tok branch-delete default"]

# Token-Trennung: ready/merge nur mit dem App-Token, alles andere mit dem Standard-Token
R(
    lauf(
        "G1 Token: Merge mit App-Token, Check mit Standard-Token",
        "pass",
        toks=[CHK, MERGE_APP],
        check=["check success"],
        writes=A,
    )
)
R(
    lauf(
        "G1 Token: Draft -> ready und merge mit App-Token",
        "pass",
        prd=pr(draft=True),
        toks=[CHK, READY_APP, MERGE_APP],
        writes=["ready"] + A,
    )
)
R(
    lauf(
        "G1 Token: voller Ablauf, Nachlauf-Schritte mit Standard-Token",
        "pass",
        prd=mit_ref(),
        nach=gemergt(),
        closing=issues(7),
        mainruns_nach=NEU_OHNE_CI,
        toks=[CHK, MERGE_APP] + NACH,
        writes=VOLL,
    )
)
R(
    lauf(
        "G1 Token: Verstoss -> nur disable-auto mit Standard-Token, kein App-Token",
        "fail",
        [datei("pyproject.toml")],
        toks=["tok merge-disable default", CHK],
        writes=D,
    )
)
R(lauf("G1 Token: Mensch-PR -> kein App-Token", "pass", prd=pr(user=MENSCH), toks=[CHK], writes=[]))
R(
    lauf(
        "G1 Token: Auto-Merge schon aktiv -> kein weiterer Merge",
        "pass",
        prd=mit_ref(auto_merge=WARTET),
        toks=[CHK],
        writes=[],
    )
)
R(
    lauf(
        "G1 Token: Retry gemergter PR nutzt nie das App-Token",
        "pass",
        prd=gemergt(),
        closing=issues(7),
        toks=["tok issue-close default", "tok branch-delete default"],
        writes=["issue-close 7", BRANCH],
    )
)
R(
    n_lauf(
        "G1 Token: Neubewertung mergt mit App-Token",
        "pass",
        prd=mit_ref(),
        nach=gemergt(),
        closing=issues(7),
        mainruns_nach=NEU_OHNE_CI,
        toks=[CHK, MERGE_APP] + NACH,
        writes=VOLL,
    )
)

# Fail closed: ohne App-Token weder Ready noch Merge
R(
    lauf(
        "G1 Fail closed: App-Token fehlt -> kein Merge, Exit 1, Check bleibt success",
        "fail",
        mtoken="",
        toks=[CHK],
        check=["check success"],
        writes=[],
        stdout=["App-Token fuer Ready/Merge fehlt"],
    )
)
R(
    lauf(
        "G1 Fail closed: App-Token fehlt bei Draft -> auch kein ready",
        "fail",
        mtoken="",
        prd=pr(draft=True),
        toks=[CHK],
        writes=[],
    )
)
R(
    lauf(
        "G1 Ohne App aber Auto-Merge aus -> weiter ok (nur Check)",
        "pass",
        mtoken="",
        repo={"default_branch": "main", "allow_auto_merge": False},
        toks=[CHK],
        check=["check success"],
        writes=[],
    )
)
R(
    lauf(
        "G1 Fail closed: App-Token fehlt, Verstoss -> Check failure und disable-auto wie bisher",
        "fail",
        [datei("pyproject.toml")],
        mtoken="",
        toks=["tok merge-disable default", CHK],
        writes=D,
    )
)
R(
    lauf(
        "G1 Fail closed: Merge scheitert (403) -> Exit 1, nichts gemergt",
        "fail",
        marker=["fail_merge"],
        toks=[CHK],
        check=["check success"],
        writes=[],
    )
)
R(
    n_lauf(
        "G1 Fail closed: Neubewertung ohne App-Token -> kein Merge, Exit 1",
        "fail",
        mtoken="",
        prd=mit_ref(),
        toks=[CHK],
        writes=[],
    )
)

# Push-CI von main nach dem App-Merge: warten, Dispatch nur als Fallback
R(
    lauf(
        "G1 Push-CI erscheint nach 2 Abfragen -> kein Dispatch",
        "pass",
        prd=mit_ref(),
        nach=gemergt(),
        closing=issues(7),
        mainruns_nach=NEU_OHNE_CI,
        spaeter=GRUEN_MAIN,
        spaeter_ab=2,
        toks=[CHK, MERGE_APP, "tok issue-close default", "tok branch-delete default"],
        writes=A + ["issue-close 7", BRANCH],
    )
)
R(
    lauf(
        "G1 Push-CI bleibt aus -> Dispatch als Fallback mit Standard-Token",
        "pass",
        prd=mit_ref(),
        nach=gemergt(),
        closing=issues(7),
        mainruns_nach=NEU_OHNE_CI,
        toks=[CHK, MERGE_APP] + NACH,
        writes=VOLL,
    )
)


# YAML-Gates (statische Pruefung der Workflow-Datei)
def yaml_fall(name, bedingung):
    print(f"{'OK  ' if bedingung else 'FEHL'} {name}")
    return bool(bedingung)


MINT = re.search(r"- name: App-Token nur fuer Ready und Merge.*?(?=\n      - name:)", yml, re.S)
MINT_BLOCK = MINT.group(0) if MINT else ""
JOB_PERM = re.search(r"\n    permissions:\n(.*?)\n    steps:", yml, re.S)
JOB_PERM_ZEILEN = [
    z.strip().split(" #")[0] for z in (JOB_PERM.group(1).split("\n") if JOB_PERM else [])
]
R(yaml_fall("G1 YAML: Mint-Schritt vorhanden", bool(MINT_BLOCK)))
R(
    yaml_fall(
        "G1 YAML: genau eine Mint-Action, SHA-gepinnt",
        yml.count("actions/create-github-app-token@64ab729a6294000f5aa4a4bc0b73d1f32bc45510") == 1,
    )
)
R(
    yaml_fall(
        "G1 YAML: Mint-Schritt hat genau contents + pull-requests: write",
        sorted(re.findall(r"permission-[a-z-]+: \w+", MINT_BLOCK))
        == ["permission-contents: write", "permission-pull-requests: write"],
    )
)
R(
    yaml_fall(
        "G1 YAML: Mint auf dieses Repo beschraenkt",
        "repositories: ${{ github.event.repository.name }}" in MINT_BLOCK,
    )
)
R(
    yaml_fall(
        "G1 YAML: Mint scheitert weich (continue-on-error) und nur mit App-Variable",
        "continue-on-error: true" in MINT_BLOCK
        and "if: ${{ vars.AGENT_APP_ID != '' }}" in MINT_BLOCK,
    )
)
R(
    yaml_fall(
        "G1 YAML: Private Key nur im Mint-Schritt",
        yml.count("secrets.AGENT_APP_KEY") == 1
        and "secrets.AGENT_APP_KEY" in MINT_BLOCK
        and "AGENT_APP_KEY" not in code,
    )
)
R(
    yaml_fall(
        "G1 YAML: Job-Rechte unveraendert (keine neuen dauerhaften Rechte)",
        sorted(JOB_PERM_ZEILEN)
        == sorted(
            [
                "actions: write",
                "checks: write",
                "contents: write",
                "issues: write",
                "pull-requests: write",
            ]
        ),
    )
)
R(yaml_fall("G1 YAML: globale Rechte leer", "\npermissions: {}\n" in yml))
R(
    yaml_fall(
        "G1 YAML: Standard-Token und Merge-Token getrennt uebergeben",
        yml.count("GH_TOKEN: ${{ github.token }}") == 1
        and yml.count("MERGE_TOKEN: ${{ steps.merge-token.outputs.token }}") == 1,
    )
)
R(
    yaml_fall(
        "G1 YAML: Trigger unveraendert (workflow_run nach CI)",
        "workflows: [CI]" in yml
        and "types: [completed]" in yml
        and "pull_request_target:" not in yml,
    )
)

print("ALLE OK" if all(res) else f"{res.count(False)} FEHLER", f"({len(res)} Faelle)")
sys.exit(0 if all(res) else 1)
