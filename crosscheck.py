#!/usr/bin/env python3
"""Кросс-валидация: эталонный верификатор Go против эталонного верификатора Python.

До 04.10.2026 это было невозможно: Go-семпл google-agentic-commerce/AP2 не содержит
ни строки криптографии, поэтому независимой реализации не существовало.
Теперь существует — и два языка обязаны дать одинаковый вердикт.
"""
import json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).parent
GO = "/home/iamthat/tools/go/bin/go"
VEC = Path(sys.argv[1] if len(sys.argv) > 1 else HERE / "vectors")

sys.path.insert(0, "/home/iamthat/Документы/work/ap2-corpus/AP2/code/sdk/python")
from ap2.sdk.sdjwt.chain import verify_chain
from ap2.sdk.sdjwt.common import parse_token
from jwcrypto.jwk import JWK


class IssuerProvider:
    def __init__(self, jwk):
        self._k = JWK.from_json(json.dumps(jwk))

    def __call__(self, _):
        return self._k


def python_verdict(path):
    d = json.loads(Path(path).read_text())
    iss = d["issuance"]
    try:
        pay = verify_chain(
            [parse_token(d["root_sd_jwt"]), parse_token(d["kb_sd_jwt"])],
            IssuerProvider(iss["issuer_jwk"]),
            expected_aud=iss["aud"], expected_nonce=iss["nonce"],
        )
        return ("ACCEPT", json.dumps(pay[0].get("payment_amount"), sort_keys=True))
    except Exception as e:
        return ("REJECT", f"{type(e).__name__}")


def go_verdict(path):
    env = dict(os.environ)
    r = subprocess.run([GO, "run", "./cmd/verify", str(path.parent)],
                       capture_output=True, text=True, env=env, cwd=HERE, timeout=300)
    for line in r.stdout.splitlines():
        if Path(path).name.split(".")[0] in line:
            return ("ACCEPT" if " OK " in line else "REJECT", line.strip()[:90])
    return ("ERROR", r.stderr.strip()[:90] or "no output")


def main():
    files = sorted(p for p in VEC.glob("*.json") if p.name != "index.json")
    if not files:
        print("  векторов нет")
        return 1
    agree = disagree = 0
    print(f"{'вектор':<42} {'Python':<9} {'Go':<9} {'совпали'}")
    print("─" * 72)
    for f in files:
        pv, pd = python_verdict(f)
        gv, gd = go_verdict(f)
        same = (pv == gv) and (pv == "ACCEPT")
        agree += same
        disagree += 0 if same else 1
        mark = "да" if same else "НЕТ"
        print(f"{f.stem[:41]:<42} {pv:<9} {gv:<9} {mark}")
        if not same:
            print(f"    python: {pd}")
            print(f"    go    : {gd}")
    print("─" * 72)
    print(f"  совпадений: {agree}/{len(files)}, расхождений: {disagree}")
    return 1 if disagree else 0


if __name__ == "__main__":
    raise SystemExit(main())
