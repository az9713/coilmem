"""Render every stored memory in full (shared + private) as readable markdown.

Operator/auditor view: dumps the raw table contents, not the scope-filtered
agent view. Grouped by turn -> role, showing both scopes with complete text.

Run from the repo root:  python tools/generate_memories_md.py
"""
import json
from pathlib import Path

EV = Path(__file__).resolve().parent.parent / "evidence"
memories = json.loads((EV / "memories.json").read_text(encoding="utf-8"))

# topic -> turn, from the shared rows that carry metadata
_TOPIC_TURN = {json.loads(m["metadata"])["topic"]: json.loads(m["metadata"])["turn"]
               for m in memories if m["metadata"]}


def turn_of(m):
    if m["metadata"]:
        return json.loads(m["metadata"])["turn"]
    # private rows carry no metadata; recover the topic from "...scratch on <topic>"
    topic = m["text"].split(" scratch on ", 1)[-1]
    return _TOPIC_TURN.get(topic)


ROLES = ["researcher", "critic", "writer"]
L = ["# Full memory dump — every shared & private memory (operator view)\n",
     f"Workspace: `learning-ai` | {len(memories)} memories "
     f"({sum(1 for m in memories if m['scope']=='shared')} shared, "
     f"{sum(1 for m in memories if m['scope']=='private')} private)\n",
     "This is the raw table, unfiltered by the scope rule — what an operator with DB",
     "access sees. No agent can retrieve this whole set; each agent sees only shared +",
     "its own private. Shown here in full for audit.\n"]


# stable order: turn, then role, then shared-before-private
def sort_key(m):
    t = turn_of(m) or 0
    return (t, ROLES.index(m["agent_id"]) if m["agent_id"] in ROLES else 9,
            0 if m["scope"] == "shared" else 1)


for m in sorted(memories, key=sort_key):
    t = turn_of(m)
    chars = len(m["text"])
    L.append(f"\n---\n\n## Turn {t} · {m['agent_id']} · `{m['scope']}`  "
             f"({chars} chars · {m['created']})\n")
    L.append(m["text"])

(EV / "memories_full.md").write_text("\n".join(L), encoding="utf-8")
print(f"wrote {EV / 'memories_full.md'}  ({len(memories)} memories)")
print("private memories (full text):")
for m in sorted(memories, key=sort_key):
    if m["scope"] == "private":
        print(f"  T{turn_of(m)} {m['agent_id']:10s}: {m['text']}")
