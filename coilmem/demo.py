"""Two-agent demo against a running coilmem server.

Shows agent `writer` using context that agent `researcher` produced, via the
shared workspace scope — context `writer` never computed itself.

Prereqs: server running (see README), env COILMEM_URL, COILMEM_KEY set.
Run: python -m coilmem.demo
"""
import os

import httpx

from .config import load_env

load_env()  # populate os.environ from ./.env before reading any var

URL = os.environ.get("COILMEM_URL", "http://127.0.0.1:8000")
KEY = os.environ.get("COILMEM_KEY", "")
WS = "demo-workspace"
H = {"X-API-Key": KEY}


def write(agent_id, scope, text):
    r = httpx.post(f"{URL}/memory", headers=H,
                   json={"workspace": WS, "agent_id": agent_id, "scope": scope, "text": text})
    r.raise_for_status()
    return r.json()["id"]


def search(agent_id, query, k=5):
    r = httpx.get(f"{URL}/memory/search", headers=H,
                  params={"workspace": WS, "agent_id": agent_id, "query": query, "k": k})
    r.raise_for_status()
    return r.json()["results"]


def main():
    # researcher agent records findings into SHARED scope
    print("[researcher] writing findings to shared memory...")
    write("researcher", "shared", "The customer's production DB is Postgres 16 on port 5433.")
    write("researcher", "shared", "Their peak traffic is 9am-11am US Eastern.")
    write("researcher", "private", "note to self: double-check the port later")  # stays private

    # writer agent — fresh, never saw the research — pulls shared context
    print("[writer] querying shared memory (writer computed none of this itself)...")
    hits = search("writer", "what database does the customer run and when is peak load")
    for h in hits:
        print(f"   <- [{h['agent_id']}/{h['scope']}] {h['text']}  (score={h['score']:.3f})")

    texts = [h["text"] for h in hits]
    assert any("Postgres" in t for t in texts), "writer should see researcher's shared DB finding"
    assert all("note to self" not in t for t in texts), "researcher's private note must not leak"
    print("\nOK: writer used researcher's shared context; private note stayed private.")


if __name__ == "__main__":
    main()
