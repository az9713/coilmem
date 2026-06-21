"""Researcher -> critic -> writer team on a shared coilmem workspace (LangGraph).

Each turn (one topic) the three agents run in order. Each agent:
  - reads team context: memory mode = coilmem recall (top-k of `shared` + its OWN `private`);
    naive mode = the full running transcript of everything produced so far.
  - acts (LLM/stub) and writes its output to `shared` + a scratch note to `private`.

coilmem's scope rule does the work: an agent recalling sees shared + its own private, never
another agent's private — so the critic/writer get the researcher's *shared* finding but not
its private scratch. The two modes let us measure the cost of memory vs naive context-stuffing
honestly (memory bounded ~O(k) vs naive O(turns)).
"""
from langgraph.graph import END, START, StateGraph

from coilmem import store

from .config import ROLE_INSTR, ROLES
from .llm import CostMeter, call


def _grounding(conn, workspace, role, query, mode, transcript, k, embed_fn):
    if mode == "memory":
        hits = store.search(conn, workspace, role, query, k=k, embed_fn=embed_fn)
        return "\n".join(f"- {h['text']}" for h in hits)
    return "\n".join(f"- {t}" for t in transcript)  # naive: everything so far


def run_team(conn, workspace, topics, seats, mode="memory", k=5, embed_fn=None, cost=None):
    """Run the team over a list of topics (turns). Returns sections + the CostMeter.
    `seats` maps role -> chat object. `mode` is 'memory' or 'naive'."""
    cost = cost if cost is not None else CostMeter()
    transcript = []      # shared outputs so far (for naive grounding)
    sections = []
    last_ctx = {}        # role -> grounding block it last received (for the parity guardrail)

    g = _build_graph(conn, workspace, seats, mode, k, embed_fn, cost, transcript, last_ctx, sections)
    for turn, topic in enumerate(topics, 1):
        g.invoke({"topic": topic, "turn": turn})
    return {"sections": sections, "cost": cost, "last_ctx": last_ctx}


def _build_graph(conn, workspace, seats, mode, k, embed_fn, cost, transcript, last_ctx, sections):
    from typing import TypedDict

    class TurnState(TypedDict, total=False):
        topic: str
        turn: int
        outputs: dict

    def make_node(role):
        def node(state):
            topic = state["topic"]
            ctx = _grounding(conn, workspace, role, topic, mode, transcript, k, embed_fn)
            last_ctx[role] = ctx
            msgs = [("system", f"You are the {role}. {ROLE_INSTR[role]}"),
                    ("human", f"Topic: {topic}\n\nTeam context:\n{ctx}")]
            text, usage = call(seats[role], msgs)
            cost.record(mode, role, usage)
            store.add(conn, workspace, role, "shared", text,
                      metadata={"turn": state["turn"], "topic": topic}, embed_fn=embed_fn)
            store.add(conn, workspace, role, "private",
                      f"{role} private scratch on {topic}", embed_fn=embed_fn)
            transcript.append(f"[{role}] {text}")
            outputs = dict(state.get("outputs", {}))
            outputs[role] = text
            if role == ROLES[-1]:
                sections.append({"turn": state["turn"], "topic": topic, "outputs": outputs})
            return {"outputs": outputs}
        return node

    g = StateGraph(TurnState)
    for role in ROLES:
        g.add_node(role, make_node(role))
    g.add_edge(START, ROLES[0])
    for a, b in zip(ROLES, ROLES[1:]):
        g.add_edge(a, b)
    g.add_edge(ROLES[-1], END)
    return g.compile()


def live_seats():
    """role -> real chat model, key-aware."""
    from .config import ROLE_MODELS, resolve_model
    from .llm import make_chat

    return {role: make_chat(resolve_model(model)) for role, model in ROLE_MODELS.items()}
