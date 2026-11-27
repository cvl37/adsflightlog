"""Card editions: lock rarities in, and issue a new edition when things change.

Before lock-in, every card's rarity is provisional and recalculated live.
``lock`` freezes the current state of every card as **edition 1**: rarity,
score, reasons, special-livery status, registration, type and operator.

After lock-in, ``sync`` (run hourly by the web server) compares each card's
live assessment with its active edition and issues a new edition when:

* a special livery was added, removed or changed  -> immediately
* the aircraft was re-registered                  -> immediately
* the rarity tier changed and stayed changed for ``stable_days`` days
  (default 7, so noise around a threshold doesn't produce a stream of editions)

The previous edition is **retired**. It keeps its frozen rarity and flags and
stays in the collection. The new edition gets its own card number. Sighting
statistics belong to the aircraft, so every edition shows the live counts.

Airframes caught after lock-in get edition 1 right away.

CLI:
    python3 -m adsflightlog.editions status|review|lock|sync [config.toml]
"""

from __future__ import annotations

import json
import sqlite3
import sys
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS card_editions (
    id            INTEGER PRIMARY KEY,
    hex           TEXT NOT NULL,
    edition       INTEGER NOT NULL,
    card_no       INTEGER NOT NULL UNIQUE,
    rarity        TEXT NOT NULL,
    score         REAL,
    reasons       TEXT,          -- JSON list, frozen at issue
    special       TEXT,          -- JSON {title, note, one_off} or NULL, frozen at issue
    reg           TEXT,
    type          TEXT,
    model         TEXT,
    operator      TEXT,
    issued        REAL NOT NULL,
    issue_reason  TEXT,
    retired       REAL,
    retire_reason TEXT,
    UNIQUE (hex, edition)
);
CREATE INDEX IF NOT EXISTS card_editions_hex ON card_editions(hex, edition);

-- A tier change waiting to prove itself stable.
CREATE TABLE IF NOT EXISTS edition_pending (
    hex    TEXT PRIMARY KEY,
    rarity TEXT NOT NULL,
    since  REAL NOT NULL
) WITHOUT ROWID;
"""

DEFAULT_STABLE_DAYS = 7


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)


def locked_at(conn: sqlite3.Connection) -> float | None:
    row = conn.execute("SELECT value FROM meta WHERE key='editions_locked'").fetchone()
    return float(row[0]) if row else None


def next_card_no(conn: sqlite3.Connection) -> int:
    return conn.execute(
        """SELECT COALESCE(MAX(n), 0) + 1 FROM (
               SELECT MAX(card_no) AS n FROM airframes
               UNION ALL SELECT MAX(card_no) FROM card_editions)"""
    ).fetchone()[0]


def _special_key(sp: dict | None):
    return (sp.get("title"), bool(sp.get("one_off"))) if sp else None


def _issue(conn, card: dict, edition: int, card_no: int, now: float, reason: str | None) -> None:
    sp = card.get("special")
    conn.execute(
        """INSERT INTO card_editions (hex, edition, card_no, rarity, score, reasons, special,
               reg, type, model, operator, issued, issue_reason)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (card["hex"], edition, card_no, card["rarity"], card.get("rarity_score"),
         json.dumps(card.get("rarity_reasons") or []),
         json.dumps({k: sp.get(k) for k in ("title", "note", "one_off")}) if sp else None,
         card.get("reg"), card.get("type"), card.get("model") or card.get("type_name"),
         card.get("operator"), now, reason),
    )


def by_hex(conn: sqlite3.Connection) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    cur = conn.execute("SELECT * FROM card_editions ORDER BY hex, edition")
    cols = [c[0] for c in cur.description]
    for r in cur:
        d = dict(zip(cols, r))
        out.setdefault(d["hex"], []).append(d)
    return out


def lock(conn: sqlite3.Connection, cards: list[dict], now: float | None = None) -> int:
    """Freeze every card (that has no edition yet) as edition 1 and mark the collection locked."""
    now = now or time.time()
    ensure_schema(conn)
    have = {h for (h,) in conn.execute("SELECT DISTINCT hex FROM card_editions")}
    n = 0
    with conn:
        for c in cards:
            if c["hex"] not in have:
                _issue(conn, c, 1, c["card_no"], now, "locked in")
                n += 1
        conn.execute("INSERT OR REPLACE INTO meta VALUES ('editions_locked', ?)", (str(now),))
    return n


def ensure_first_editions(conn: sqlite3.Connection, cards: list[dict], now: float | None = None) -> int:
    """After lock-in: new catches get edition 1 straight away."""
    if not locked_at(conn):
        return 0
    now = now or time.time()
    have = {h for (h,) in conn.execute("SELECT DISTINCT hex FROM card_editions")}
    new = [c for c in cards if c["hex"] not in have]
    with conn:
        for c in new:
            _issue(conn, c, 1, c["card_no"], now, "caught")
    return len(new)


def sync(conn: sqlite3.Connection, cards: list[dict], now: float | None = None,
         stable_days: float = DEFAULT_STABLE_DAYS) -> list[str]:
    """Issue new editions where the situation changed. Returns a log of events."""
    if not locked_at(conn):
        return []
    now = now or time.time()
    ensure_first_editions(conn, cards, now)
    eds = by_hex(conn)
    pending = {r[0]: (r[1], r[2]) for r in conn.execute("SELECT hex, rarity, since FROM edition_pending")}
    events = []
    with conn:
        for c in cards:
            hist = eds.get(c["hex"])
            if not hist:
                continue
            act = next((e for e in reversed(hist) if e["retired"] is None), hist[-1])
            snap_sp = json.loads(act["special"]) if act["special"] else None
            reason = None
            if _special_key(c.get("special")) != _special_key(snap_sp):
                if c.get("special") and not snap_sp:
                    reason = f"Special livery added: {c['special']['title']}"
                elif snap_sp and not c.get("special"):
                    reason = f"Special livery removed (was {snap_sp['title']})"
                else:
                    reason = f"Special livery changed to {c['special']['title']}"
            elif c.get("reg") and act["reg"] and c["reg"] != act["reg"]:
                reason = f"Re-registered {act['reg']} → {c['reg']}"
            elif c["rarity"] != act["rarity"]:
                p = pending.get(c["hex"])
                if p and p[0] == c["rarity"]:
                    if now - p[1] >= stable_days * 86400:
                        reason = f"Rarity changed {act['rarity']} → {c['rarity']}"
                else:
                    conn.execute("INSERT OR REPLACE INTO edition_pending VALUES (?,?,?)",
                                 (c["hex"], c["rarity"], now))
            elif c["hex"] in pending:
                conn.execute("DELETE FROM edition_pending WHERE hex=?", (c["hex"],))

            if reason:
                conn.execute("UPDATE card_editions SET retired=?, retire_reason=? WHERE id=?",
                             (now, reason, act["id"]))
                new_no = next_card_no(conn)
                _issue(conn, c, act["edition"] + 1, new_no, now, reason)
                conn.execute("DELETE FROM edition_pending WHERE hex=?", (c["hex"],))
                events.append(f"{c.get('reg') or c['hex']}: edition {act['edition'] + 1} (#{new_no}): {reason}")
    return events


def apply(cards: list[dict], eds: dict[str, list[dict]], points: dict, pending: dict | None = None,
          relabel=None) -> list[dict]:
    """One card dict per edition: frozen edition fields over the live aircraft stats."""
    out = []
    for c in cards:
        for e in eds.get(c["hex"], []):
            d = dict(c)
            sp = json.loads(e["special"]) if e["special"] else None
            badges = [b for b in c["badges"] if b not in ("special livery", "one of a kind")]
            if sp:
                badges.insert(0, "special livery")
                if sp.get("one_off"):
                    badges.insert(1, "one of a kind")
            d.update({
                "edition": e["edition"], "editions": len(eds[c["hex"]]),
                "card_no": e["card_no"], "rarity": e["rarity"], "rarity_score": e["score"],
                "rarity_reasons": json.loads(e["reasons"] or "[]"), "special": sp,
                "reg": e["reg"] or c.get("reg"), "issued": e["issued"], "issue_reason": e["issue_reason"],
                "retired": e["retired"], "retire_reason": e["retire_reason"],
                "points": points[e["rarity"]] + (100 if c.get("emergency") else 0),
                "badges": badges, "live_rarity": c["rarity"],
            })
            if e["operator"] != c.get("operator") and relabel:
                d.update(relabel(e["operator"]))
            if e["retired"] is None and pending and c["hex"] in pending:
                d["pending_rarity"] = pending[c["hex"]]
            out.append(d)
    return out


def main() -> None:
    from . import config as cfgmod
    from .web import App
    args = [a for a in sys.argv[1:]]
    cmd = args[0] if args else "status"
    cfg = cfgmod.load(args[1] if len(args) > 1 else None)
    app = App(cfg)
    with app.conn() as conn:
        ensure_schema(conn)
        provisional = app.provisional_cards()
        if cmd == "status":
            t = locked_at(conn)
            print("locked:", time.strftime("%Y-%m-%d %H:%M", time.localtime(t)) if t else "no (provisional)")
            n, r = conn.execute("SELECT COUNT(*), COALESCE(SUM(retired IS NOT NULL), 0) FROM card_editions").fetchone()
            print(f"editions: {n} ({r} retired)")
        elif cmd == "review":
            from collections import Counter
            print(Counter(c["rarity"] for c in provisional))
            order = ["common", "uncommon", "rare", "epic", "legendary"]
            for c in sorted(provisional, key=lambda c: (-order.index(c["rarity"]), -(c["rarity_score"] or 0))):
                if c["rarity"] == "common":
                    continue
                print(f"{c['rarity']:9} {c['rarity_score']:.2f} {c.get('reg') or c['hex']:9} "
                      f"{c.get('type') or '?':5} {c.get('operator') or '-':4} "
                      + " | ".join(r for r in c["rarity_reasons"] if not r.startswith("Score")))
        elif cmd == "lock":
            print("locked in", lock(conn, provisional), "cards as edition 1")
        elif cmd == "sync":
            for e in sync(conn, provisional, stable_days=cfg.editions_stable_days):
                print(e)
        else:
            sys.exit("usage: python3 -m adsflightlog.editions status|review|lock|sync [config.toml]")


if __name__ == "__main__":
    main()
