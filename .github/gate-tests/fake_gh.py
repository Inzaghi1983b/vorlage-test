"""Fake-gh fuer die Gate-Tests: liefert Fixtures aus $FIXDIR und protokolliert Schreibaufrufe.

Fehler lassen sich per Marker-Datei erzwingen: fail_dispatch, fail_issue, fail_delete, fail_graphql,
fail_ref_403 (Branch-Abfrage mit HTTP 403), ref_404 (Branch existiert nicht mehr), akzeptanz_404.
"""

import json
import os
import sys
from urllib.parse import parse_qs, urlparse

fx = os.environ["FIXDIR"]
a = sys.argv[1:]


def load(n):
    return open(os.path.join(fx, n), encoding="utf-8").read()


def hat(n):
    return os.path.exists(os.path.join(fx, n))


def log(t):
    open(os.path.join(fx, "writes.log"), "a").write(t + "\n")


def geschrieben(praefix):
    p = os.path.join(fx, "writes.log")
    return os.path.exists(p) and any(z.startswith(praefix) for z in open(p).read().splitlines())


def zaehle():
    """Zaehlt Abfragen des PR nach dem Auto-Merge-Aufruf (simuliert verzoegerten Merge)."""
    p = os.path.join(fx, "zaehler")
    n = int(open(p).read()) if os.path.exists(p) else 0
    open(p, "w").write(str(n + 1))
    return n


def fehler(text, code=1):
    print(text, file=sys.stderr)
    sys.exit(code)


if a[0] == "api":
    path = [x for x in a[1:] if x.startswith("repos/") or x == "graphql"][0]
    roh = path.split("?")[0]
    query = parse_qs(urlparse(path).query)
    methode = a[a.index("-X") + 1] if "-X" in a else "GET"
    if methode in ("POST", "PATCH") and "check-runs" in path:
        concl = [x.split("=", 1)[1] for x in a if x.startswith("conclusion=")][0]
        log(("check-patch " if methode == "PATCH" else "check ") + concl)
    elif methode == "DELETE" and "/git/refs/heads/" in path:
        if hat("fail_delete"):
            fehler("HTTP 403: Resource not accessible by integration", 1)
        log("branch-delete " + path.split("/git/refs/heads/")[1])
    elif path == "graphql":
        if hat("fail_graphql"):
            fehler("HTTP 403", 1)
        print(load("closing.json"))
    elif "/git/ref/heads/" in path:
        if hat("ref_404"):
            print('{"message": "Not Found"}')
            fehler("gh: Not Found (HTTP 404)", 1)
        if hat("fail_ref_403"):
            fehler("gh: Forbidden (HTTP 403)", 1)
        print(load("ref.json"))
    elif "/contents/tests/akzeptanz" in path:
        if hat("akzeptanz_404"):
            print('{"message": "Not Found"}')
            sys.exit(1)
        print(load("akzeptanz.json"))
    elif "/actions/workflows/" in path and roh.endswith("/runs"):
        sha = query.get("head_sha", [""])[0]
        if sha == json.loads(load("main.json"))["sha"]:
            nach = hat("mainruns_nach.json") and geschrieben("auto")
            print(load("mainruns_nach.json" if nach else "mainruns.json"))
        else:
            print(load("prruns.json"))
    elif "/actions/runs/" in path:
        # Lauf-Abfrage: je nach angefragter ID Standard-Branch-Lauf (main_run.json) oder PR-Lauf
        if roh.endswith("/runs/main") and hat("main_run.json"):
            print(load("main_run.json"))
        else:
            print(load("run.json"))
    elif "/check-runs" in path:
        print(load("checks.json"))
    elif roh.endswith("/files"):
        d = json.loads(load("files.json"))
        for i in range(0, max(len(d), 1), 30):
            print(json.dumps(d[i : i + 30]))
    elif roh.endswith("/pulls") and "/commits/" in roh:
        print(load("commit_pulls.json"))
    elif roh.endswith("/pulls") and hat("pulls.json"):
        print(load("pulls.json"))
    elif "/pulls/" in path:
        if geschrieben("auto") and (hat("pr_nach.json") or hat("pr_wartet.json")):
            k = int(load("merge_nach_abfragen")) if hat("merge_nach_abfragen") else 0
            z = zaehle()
            if z < k or not hat("pr_nach.json"):
                print(load("pr_wartet.json" if hat("pr_wartet.json") else "pr.json"))
            else:
                print(load("pr_nach.json"))
        else:
            print(load("pr.json"))
    elif roh.count("/") == 4 and "/commits/" in roh:
        print(load("main.json"))
    elif roh.count("/") == 2:
        print(load("repo.json"))
    else:
        fehler(f"unbekannt {a}", 2)
elif a[:2] == ["pr", "ready"]:
    log("ready")
elif a[:2] == ["pr", "merge"] and "--disable-auto" in a:
    log("disable-auto")
elif a[:2] == ["pr", "merge"] and "--auto" in a:
    log("auto " + a[a.index("--match-head-commit") + 1])
elif a[:2] == ["workflow", "run"]:
    if hat("fail_dispatch"):
        fehler("HTTP 403: Resource not accessible by integration", 1)
    log("ci-dispatch " + a[a.index("--ref") + 1])
elif a[:2] == ["issue", "close"]:
    if hat("fail_issue"):
        fehler("HTTP 403: Resource not accessible by integration", 1)
    log("issue-close " + a[2])
else:
    fehler(f"unbekannter Aufruf {a}", 2)
