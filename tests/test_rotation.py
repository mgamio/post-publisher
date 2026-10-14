import random

from publisher.content import Post
from publisher.rotation import empty_state, load_state, pick, record, save_state

WEIGHTS = {"article": 1, "quote": 1, "ad": 0}


def make_posts():
    return ([Post(id=f"a{i}", type="article", text=f"article {i}") for i in range(5)]
            + [Post(id=f"q{i}", type="quote", text=f"quote {i}") for i in range(3)]
            + [Post(id="ad0", type="ad", text="ad")])


def run(posts, state, n, seed=1):
    rng = random.Random(seed)
    picked = []
    for _ in range(n):
        post = pick(posts, WEIGHTS, state, rng)
        record(state, post)
        picked.append(post)
    return picked


def test_every_post_of_a_type_is_used_before_any_repeats():
    state = empty_state()
    picked = run(make_posts(), state, 40)
    articles = [p.id for p in picked if p.type == "article"]
    for start in range(0, len(articles) - 4, 5):
        assert len(set(articles[start:start + 5])) == 5


def test_zero_weight_types_are_never_picked():
    picked = run(make_posts(), empty_state(), 100)
    assert all(p.type != "ad" for p in picked)


def test_new_posts_go_first_and_only_once():
    posts = make_posts() + [Post(id="n1", type="article", text="brand new", priority="new")]
    state = empty_state()
    picked = run(posts, state, 10)
    assert picked[0].id == "n1"
    assert state["announced"] == ["n1"]


def test_removed_posts_are_dropped_from_saved_bags():
    posts = make_posts()
    state = empty_state()
    run(posts, state, 3)
    remaining = [p for p in posts if p.id not in ("a1", "a2")]
    picked = run(remaining, state, 20)
    assert not {"a1", "a2"} & {p.id for p in picked}


def test_state_round_trip(tmp_path):
    state = empty_state()
    run(make_posts(), state, 3)
    save_state(tmp_path / "s.json", state)
    assert load_state(tmp_path / "s.json") == state
    assert load_state(tmp_path / "missing.json") == empty_state()
