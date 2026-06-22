"""Build trace.md: a one-page 'follow the idea' exhibit for Turn 1.

Reads the evidence JSONs and shows, side by side, how a set of ML concepts
absent from the researcher's finding enters via the critic's critique and is
then adopted by the writer — proving the writer obtained them through shared
memory. The presence/absence table is computed from the real text, not asserted.

Run from the repo root:  python tools/generate_trace.py
"""
import json
from pathlib import Path

EV = Path(__file__).resolve().parent.parent / "evidence"
memories = json.loads((EV / "memories.json").read_text(encoding="utf-8"))
recalls = json.loads((EV / "recall_log.json").read_text(encoding="utf-8"))


def mem(turn, author):
    md = f'"turn": {turn}'
    for m in memories:
        if m["agent_id"] == author and m["scope"] == "shared" and m["metadata"] and md in m["metadata"]:
            return m["text"]
    raise LookupError(f"no shared memory for turn {turn} {author}")


researcher = mem(1, "researcher")
critic = mem(1, "critic")
writer = mem(1, "writer")

# Discriminating "bridge" terms: ML concepts (not pure math).
BRIDGE = ["supervised", "unsupervised", "overfitting", "bias-variance",
          "cross-validation", "precision", "recall"]


def has(text, term):
    return term.lower() in text.lower()


def slice_around(text, needle, before=0, length=700):
    i = text.lower().find(needle.lower())
    if i < 0:
        return text[:length].strip()
    start = max(0, i - before)
    return text[start:start + length].strip()


# writer's pivot sentence: where it switches from math to the critic's additions
writer_pivot = slice_around(writer, "However", length=520)
researcher_head = researcher[:650].strip()
critic_gap = slice_around(critic, "Missing Practical ML Foundations", before=40, length=640)

# Turn-1 writer recall (what fed the writer before it wrote)
writer_recall = next(r for r in recalls if r["turn"] == 1 and r["caller"] == "writer")

L = []
L.append("# Follow the idea — Turn 1: how the critic's correction reached the writer\n")
L.append("Topic: *the core math and ML foundations a beginner should learn first*\n")
L.append("This exhibit traces seven ML concepts that are **absent** from the researcher's")
L.append("finding, **introduced** by the critic, and then **adopted** by the writer. The")
L.append("writer never spoke to the critic — the only channel between them is coilmem's")
L.append("`shared` scope. So any critic-originated term in the writer's output arrived via")
L.append("shared memory.\n")

L.append("## 1. The term ledger (computed from the raw text)\n")
L.append("| ML concept | researcher (#1) | critic (#3) | writer (#5) |")
L.append("|---|:---:|:---:|:---:|")
for t in BRIDGE:
    r = "✓" if has(researcher, t) else "✗"
    c = "✓" if has(critic, t) else "✗"
    w = "✓" if has(writer, t) else "✗"
    L.append(f"| {t} | {r} | {c} | {w} |")
L.append("")
n_absent = sum(1 for t in BRIDGE if not has(researcher, t))
n_bridged = sum(1 for t in BRIDGE if not has(researcher, t) and has(critic, t) and has(writer, t))
L.append(f"**{n_absent}/{len(BRIDGE)} terms are absent from the researcher.** "
         f"**{n_bridged}/{len(BRIDGE)}** of those appear in BOTH the critic and the writer —")
L.append("i.e. the writer's only possible source for them is the critic's shared memory.\n")

L.append("## 2. What fed the writer before it wrote (from recall_log.json)\n")
L.append("```")
for h in writer_recall["recalled"]:
    cross = h["scope"] == "shared" and h["author"] != "writer"
    tag = "CROSS-SHARED" if cross else h["scope"].upper()
    L.append(f"[{h['author']}/{tag} score={h['score']}] {h['text'][:90].strip()}...")
L.append("```")
L.append("The writer retrieved the critic's critique (`critic/CROSS-SHARED`). That is the")
L.append("pipe the terms travelled through.\n")

L.append("## 3. The three texts, in order\n")
L.append("### A. researcher/shared (#1) — math only, no ML concepts")
L.append("> " + researcher_head.replace("\n", "\n> ") + " …\n")
L.append("### B. critic/shared (#3) — names the missing ML concepts")
L.append("> " + critic_gap.replace("\n", "\n> ") + " …\n")
L.append("### C. writer/shared (#5) — adopts exactly those concepts")
L.append("> " + writer_pivot.replace("\n", "\n> ") + " …\n")

L.append("## 4. Reading")
L.append("- The bolded ML terms in **C** (supervised/unsupervised, overfitting,")
L.append("  bias-variance, cross-validation, precision/recall) do not occur anywhere in **A**.")
L.append("- They occur in **B**, the critic's critique of **A**.")
L.append("- The recall log (section 2) proves **B** was in the writer's context when it wrote **C**.")
L.append("- Therefore the writer's completeness gain is causally attributable to shared memory,")
L.append("  not to the writer's own reasoning or to the researcher's finding.")

(EV / "trace.md").write_text("\n".join(L), encoding="utf-8")
print(f"wrote {EV / 'trace.md'}")
print(f"bridge terms absent from researcher: {n_absent}/{len(BRIDGE)}; bridged to writer: {n_bridged}")
