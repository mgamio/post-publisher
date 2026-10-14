"""Chooses the next post for a platform.

Per platform, each content type has a "bag" of post ids still to be posted in
this round. A type is drawn by weight, then the next id is taken from its bag;
an empty bag is refilled with all eligible ids in a new random order. So every
post of a type is used once before any repeats, and the state survives between
runs because it is stored in state/<platform>.json.

Posts marked priority=new are posted first, once per platform, before the rotation.
"""
import json
import random
from datetime import datetime, timezone
from pathlib import Path

HISTORY_LIMIT = 500


def empty_state():
    return {"bags": {}, "announced": [], "history": []}


def load_state(path):
    path = Path(path)
    if not path.exists():
        return empty_state()
    state = json.loads(path.read_text(encoding="utf-8"))
    for key, value in empty_state().items():
        state.setdefault(key, value)
    return state


def save_state(path, state):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def pick(posts, weights, state, rng=random):
    """Return the next post to publish, updating the bags in state. None if nothing is eligible."""
    announced = set(state["announced"])
    for post in posts:
        if post.priority == "new" and post.id not in announced:
            return post

    by_type = {}
    for post in posts:
        if weights.get(post.type, 0) > 0:
            by_type.setdefault(post.type, []).append(post)
    if not by_type:
        return None

    types = sorted(by_type)
    chosen = rng.choices(types, weights=[weights[t] for t in types])[0]
    candidates = {p.id: p for p in by_type[chosen]}

    bag = [i for i in state["bags"].get(chosen, []) if i in candidates]
    if not bag:
        bag = list(candidates)
        rng.shuffle(bag)
        last = state["history"][-1]["id"] if state["history"] else None
        if len(bag) > 1 and bag[0] == last:
            bag.append(bag.pop(0))
    next_id = bag.pop(0)
    state["bags"][chosen] = bag
    return candidates[next_id]


def record(state, post, url=None, now=None):
    now = now or datetime.now(timezone.utc)
    if post.priority == "new" and post.id not in state["announced"]:
        state["announced"].append(post.id)
    state["history"].append({
        "id": post.id,
        "type": post.type,
        "at": now.isoformat(timespec="seconds"),
        "url": url,
    })
    del state["history"][:-HISTORY_LIMIT]
