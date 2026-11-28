"""Parametric aircraft drawings in one flat vector style.

Every aircraft is built from the same parts (fuselage, wing, tail, engines,
gear) using real dimensions in metres, so variants of a family differ exactly
where the real aircraft do. All aircraft wear an all-white livery: greys and
near-black are only used for shading, lines, tyres and openings, plus a
blue-grey for glass. No airline colours, ever.

Views: ``side`` (nose left), ``top`` (plan view, nose up), ``front``
(head-on) and ``below`` (belly view, gear down).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# ---------------------------------------------------------------- palette
WHITE = "#f6f7f9"
SHADE = "#d9dde2"      # shaded underside / far surfaces
SHADE2 = "#c2c8cf"     # deeper shadow
WING = "#e6e9ed"       # wing surfaces seen from the side
LINE = "#8d959f"       # panel lines, outlines
DARK = "#4a525c"       # inlets, window glass rows, intakes
INK = "#24282e"        # tyres, deepest openings
METAL = "#a8b0b9"      # exhausts, gear legs
HUB = "#7a838d"
GLASS = "#8eadc4"      # cockpit glass (blue-grey)
GLASS_HI = "#c3d6e4"
WINDOW = "#59636e"     # cabin windows
PROP = "#5a636d"


def f(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


class Canvas:
    """Collects SVG shapes (in drawing units, y up) and tracks the extent."""

    def __init__(self, unit: float):
        self.items: list[str] = []
        self.u = unit  # stroke unit
        self.x0 = self.y0 = math.inf
        self.x1 = self.y1 = -math.inf

    def _ext(self, pts):
        for x, y in pts:
            self.x0, self.x1 = min(self.x0, x), max(self.x1, x)
            self.y0, self.y1 = min(self.y0, y), max(self.y1, y)

    def poly(self, pts, fill=WHITE, stroke=None, sw=1.0, closed=True, opacity=None, join="round", extent=True):
        pts = list(pts)
        if len(pts) < 2:
            return
        if extent:
            self._ext(pts)
        d = "M" + "L".join(f"{f(x)} {f(-y)}" for x, y in pts) + ("Z" if closed else "")
        a = [f'd="{d}"', f'fill="{fill if closed else "none"}"']
        if stroke:
            a.append(f'stroke="{stroke}" stroke-width="{f(sw * self.u)}" stroke-linejoin="{join}" stroke-linecap="round"')
        if opacity is not None:
            a.append(f'opacity="{opacity}"')
        self.items.append(f"<path {' '.join(a)}/>")

    def line(self, pts, stroke=LINE, sw=1.0, opacity=None):
        self.poly(pts, stroke=stroke, sw=sw, closed=False, opacity=opacity, extent=False)

    def ellipse(self, cx, cy, rx, ry, fill=WHITE, stroke=None, sw=1.0, opacity=None, rot=0.0):
        self._ext([(cx - rx, cy - ry), (cx + rx, cy + ry)])
        a = [f'cx="{f(cx)}" cy="{f(-cy)}" rx="{f(abs(rx))}" ry="{f(abs(ry))}" fill="{fill}"']
        if stroke:
            a.append(f'stroke="{stroke}" stroke-width="{f(sw * self.u)}"')
        if opacity is not None:
            a.append(f'opacity="{opacity}"')
        if rot:
            a.append(f'transform="rotate({f(-rot)} {f(cx)} {f(-cy)})"')
        self.items.append(f"<ellipse {' '.join(a)}/>")

    def rrect(self, x, y, w, h, r, fill=WHITE, stroke=None, sw=1.0, opacity=None):
        """Rounded rectangle; (x, y) is the lower-left corner."""
        self._ext([(x, y), (x + w, y + h)])
        a = [f'x="{f(x)}" y="{f(-(y + h))}" width="{f(w)}" height="{f(h)}" rx="{f(r)}" fill="{fill}"']
        if stroke:
            a.append(f'stroke="{stroke}" stroke-width="{f(sw * self.u)}"')
        if opacity is not None:
            a.append(f'opacity="{opacity}"')
        self.items.append(f"<rect {' '.join(a)}/>")

    def svg(self, pad=0.05, title="") -> str:
        w, h = self.x1 - self.x0, self.y1 - self.y0
        p = max(w, h) * pad
        vb = f"{f(self.x0 - p)} {f(-self.y1 - p)} {f(w + 2 * p)} {f(h + 2 * p)}"
        t = f"<title>{title}</title>" if title else ""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}">{t}'
                + "".join(self.items) + "</svg>\n")


def sweep_curve(a: float, b: float, n: int, fn):
    return [fn(a + (b - a) * i / n) for i in range(n + 1)]


def superq(t: float, e: float) -> float:
    """Quarter super-ellipse from 0 (t=0) to 1 (t=1); e=2 is an ellipse."""
    t = min(max(t, 0.0), 1.0)
    return (1 - (1 - t) ** e) ** (1 / e)


# ---------------------------------------------------------------- spec
@dataclass
class Engine:
    mount: str = "wing"          # wing | tail | center | nose | fuselage
    z: float = 0.35              # wing: fraction of semispan; tail: n/a
    dia: float = 1.8
    length: float = 4.0
    fwd: float = 0.65            # wing: share of nacelle ahead of the LE
    drop: float = 0.25           # wing: pylon gap below the wing (in dia)
    x: float = 0.0               # tail/center: nacelle front as fraction of L
    y: float = 0.6               # tail: centre height as fraction of D
    chevrons: bool = False
    kind: str = "fan"            # fan | prop | piston
    prop_d: float = 0.0
    gc: float = 0.0              # wing fan: nacelle ground clearance (m), overrides drop
    blades: int = 4
    over: bool = False           # turboprop nacelle sits over a high wing


@dataclass
class Spec:
    name: str
    L: float
    D: float
    span: float
    W: float = 0.0
    kind: str = "jet"            # jet | prop | heli
    # nose & tail cone (in fuselage heights)
    nose_len: float = 1.7
    nose_blen: float = 1.1
    nose_tip: float = 0.38
    nose_e: float = 2.0
    nose_be: float = 2.0
    tail_len: float = 3.2
    tail_top: float = 0.80
    tail_bot: float = 0.60
    tail_te: float = 2.0
    tail_be: float = 1.35
    # wing
    wing_x: float = 0.40         # root LE as fraction of L
    wing_pos: str = "low"        # low | mid | high
    root: float = 6.0
    tip: float = 1.5
    sweep: float = 25.0
    dihedral: float = 5.0
    kink: float = 0.0            # TE kink at fraction of semispan (0 = none)
    kink_chord: float = 0.0      # chord at the kink
    wingtip: str = "plain"
    winglet_h: float = 0.0
    strut: bool = False
    # tail
    fin_x: float = 0.83
    fin_root: float = 5.5
    fin_tip: float = 1.8
    fin_h: float = 6.0
    fin_sweep: float = 38.0
    dorsal: float = 0.0          # dorsal fillet length (fraction of fin root)
    ttail: bool = False
    stab_on_fin: float = 0.0     # 1.0 = T-tail, 0.3-0.6 = cruciform (set from ttail)
    stab_x: float = 0.86
    stab_span: float = 13.0
    stab_root: float = 3.5
    stab_tip: float = 1.2
    stab_sweep: float = 32.0
    stab_y: float = 0.62
    # cabin
    win_y: float = 0.60
    win_from: float = 0.12
    win_to: float = 0.80
    win_pitch: float = 0.53
    win_w: float = 0.25
    win_h: float = 0.36
    win_round: float = 0.5
    windows: bool = True
    upper_deck: float = 0.0      # 747: hump length fraction of L
    upper_h: float = 0.25        # 747: hump height over the crown (fraction of D)
    upper_win_to: float = 0.0
    double_deck: bool = False
    doors: tuple = ()            # x fractions of L
    exits: tuple = ()            # overwing emergency exits (x fractions)
    door_w: float = 0.85
    door_h: float = 0.48         # fraction of D
    door_y: float = 0.22
    cockpit: str = "airliner"    # airliner | bizjet | ga | heli
    cockpit_x: float = 0.0       # override: start as fraction of nose length
    # engines & gear
    engines: list = field(default_factory=list)
    gear_h: float = 1.6          # fuselage bottom above ground (m)
    nose_gear: float = 0.08      # x fraction of L
    main_gear: tuple = (0.50,)   # x fractions of L, one per visible bogie
    axles: tuple = (1,)          # axles per bogie
    wheel_d: float = 1.1
    nose_wheel_d: float = 0.0
    tailwheel: bool = False
    belly_fairing: float = 0.0   # wing-body fairing bulge depth (m)
    track: float = 0.0           # main gear track (m)
    canopy: bool = False
    freighter: bool = False
    note: str = ""

    def __post_init__(self):
        if not self.W:
            self.W = self.D
        if self.ttail and not self.stab_on_fin:
            self.stab_on_fin = 1.0


# ---------------------------------------------------------------- fuselage
class Body:
    def __init__(self, s: Spec):
        self.s = s
        D, L = s.D, s.L
        self.Ln = s.nose_len * D
        self.Lb = s.nose_blen * D
        self.Lt = s.tail_len * D
        self.xt = L - self.Lt
        self.tip = s.nose_tip * D

    def top(self, x: float) -> float:
        s, D = self.s, self.s.D
        y = D
        if x < self.Ln:
            y = self.tip + (D - self.tip) * superq(x / self.Ln, s.nose_e)
        if s.upper_deck and x < s.upper_deck * s.L:
            # 747 hump: rises from the nose to the upper deck, fairs back into the crown
            xh = s.upper_deck * s.L
            H = D * (1 + s.upper_h)
            rise = self.Ln * 1.5
            if x < rise:
                yh = self.tip + (H - self.tip) * superq(x / rise, 1.9)
            elif x < 0.72 * xh:
                yh = H
            else:
                t = (x - 0.72 * xh) / (0.28 * xh)
                yh = H - (H - D) * (3 * t * t - 2 * t * t * t)
            y = max(y, yh) if x >= self.Ln else yh
        if s.double_deck and x >= self.Ln:
            y = D
        if x > self.xt:
            t = (x - self.xt) / self.Lt
            y = D - (D - s.tail_top * D) * t ** s.tail_te
        return y

    def bot(self, x: float) -> float:
        s, D = self.s, self.s.D
        y = 0.0
        if x < self.Lb:
            y = self.tip * (1 - superq(x / self.Lb, s.nose_be))
        if x > self.xt:
            t = (x - self.xt) / self.Lt
            y = s.tail_bot * D * t ** s.tail_be
        return y

    def outline(self, n=160):
        L = self.s.L
        xs = [L * (1 - math.cos(math.pi * i / n)) / 2 for i in range(n + 1)]
        # denser near the nose
        xs = sorted(set(xs + [self.Ln * superq(i / 40, 1.0) for i in range(41)]))
        return [(x, self.top(x)) for x in xs] + [(x, self.bot(x)) for x in reversed(xs)], xs


# ---------------------------------------------------------------- side view
def side(s: Spec) -> str:
    if s.kind == "balloon":
        return balloon(s)
    if s.kind == "heli":
        return heli_side(s)
    c = Canvas(s.L / 330)
    b = Body(s)
    D, L = s.D, s.L
    K = 0.12 if s.wing_pos == "low" else 0.08  # view from slightly below: near side drops by K per metre of depth

    semi = s.span / 2 - s.W / 2
    wy = {"low": 0.12 * D, "mid": 0.45 * D, "high": D + 0.05 * s.root}[s.wing_pos]
    wx = s.wing_x * L
    tand = math.tan(math.radians(s.dihedral))
    tans = math.tan(math.radians(s.sweep))

    def wing_le(z):  # z = metres outboard of the root
        return wx + z * tans

    def wing_chord(z):
        r = z / semi if semi else 0
        if s.kink and r < s.kink:
            return s.root + (s.kink_chord - s.root) * (r / s.kink)
        c0, r0 = (s.kink_chord, s.kink) if s.kink else (s.root, 0.0)
        return c0 + (s.tip - c0) * (r - r0) / (1 - r0)

    def wing_y(z):
        return wy + z * (tand - K)

    # ---- far horizontal stabiliser (behind the body)
    def stab(near: bool):
        semi_s = s.stab_span / 2 - (0.4 if not s.ttail else 0)
        if s.stab_on_fin:
            fr = s.stab_on_fin
            sx = s.fin_x * L + fr * s.fin_h * math.tan(math.radians(s.fin_sweep)) + 0.1 * s.fin_root * (1 - 0.5 * (1 - fr))
            sy = b.top(s.fin_x * L) + fr * s.fin_h - 0.05
        else:
            sx = s.stab_x * L
            sy = s.stab_y * D
        ts = math.tan(math.radians(s.stab_sweep))
        dz = semi_s * (0.12 - K) if near else semi_s * (0.12 + K)
        th = s.stab_root * 0.10
        tx = sx + semi_s * ts
        pts = [(sx, sy + th * 0.6), (tx, sy + (-dz if near else dz) + th * 0.3),
               (tx + s.stab_tip, sy + (-dz if near else dz)), (sx + s.stab_root, sy - th * 0.1),
               (sx + s.stab_root * 0.15, sy - th * 0.4)]
        if near:
            c.poly(pts, fill=WING, stroke=LINE, sw=0.7)
            # elevator line
            c.line([(sx + s.stab_root * 0.72, sy), (tx + s.stab_tip * 0.65, sy - dz + 0.02)], sw=0.6)
        else:
            c.poly(pts, fill=SHADE2)

    stab(False)

    # ---- gear (drawn early so the body covers the tops of the legs)
    gy = -s.gear_h
    def wheel(x, d):
        r = d / 2
        c.ellipse(x, gy + r, r, r, fill=INK)
        c.ellipse(x, gy + r, r * 0.5, r * 0.5, fill=HUB)
        c.ellipse(x, gy + r, r * 0.18, r * 0.18, fill=METAL)

    def leg(x, top, w):
        c.poly([(x - w / 2, top), (x + w / 2, top), (x + w / 2, gy + 0.3), (x - w / 2, gy + 0.3)], fill=METAL)

    nwd = s.nose_wheel_d or s.wheel_d * 0.75
    if s.tailwheel:
        xn = s.nose_gear * L
        leg(xn, b.bot(xn) + 0.2, s.wheel_d * 0.16)
        wheel(xn, s.wheel_d)
        xt = 0.93 * L
        c.line([(xt, b.bot(xt)), (xt + 0.15, b.bot(xt) - 0.35)], stroke=METAL, sw=1.4)
        c.ellipse(xt + 0.15, b.bot(xt) - 0.45, 0.12, 0.12, fill=INK)
    else:
        xn = s.nose_gear * L
        leg(xn, b.bot(xn) + 0.3, nwd * 0.22)
        wheel(xn, nwd)
        for i, mg in enumerate(s.main_gear):
            xm = mg * L
            n = s.axles[min(i, len(s.axles) - 1)]
            sp = s.wheel_d * 1.25
            xs = [xm + (k - (n - 1) / 2) * sp for k in range(n)]
            top = wy if s.wing_pos == "low" else b.bot(xm) + 0.2
            leg(xm, top, s.wheel_d * 0.22)
            if n > 1:
                c.poly([(xs[0], gy + s.wheel_d / 2 + 0.12), (xs[-1], gy + s.wheel_d / 2 + 0.12),
                        (xs[-1], gy + s.wheel_d / 2 - 0.12), (xs[0], gy + s.wheel_d / 2 - 0.12)], fill=HUB)
            for x in xs:
                wheel(x, s.wheel_d)

    # ---- vertical tail (behind the body outline)
    fx = s.fin_x * L
    fy = b.top(fx)
    tf = math.tan(math.radians(s.fin_sweep))
    ftx = fx + s.fin_h * tf
    fte = min(fx + s.fin_root, L - 0.02 * L)
    fin = [(fx, fy - 0.1), (ftx, fy + s.fin_h), (ftx + s.fin_tip, fy + s.fin_h), (fte, b.top(fte) - 0.05)]
    if s.dorsal:
        dx = fx - s.dorsal * s.fin_root
        fin = [(dx, b.top(dx) - 0.05)] + sweep_curve(0, 1, 10, lambda t: (
            dx + (fx + 0.22 * s.fin_h * tf - dx) * t,
            b.top(dx) + (0.22 * s.fin_h) * t ** 2.2)) + fin[1:]
    c.poly(fin, fill=WHITE, stroke=LINE, sw=0.8)
    # rudder hinge line
    c.line([(fx + 0.68 * s.fin_root, b.top(fx + 0.68 * s.fin_root) + 0.15),
            (ftx + 0.62 * s.fin_tip, fy + s.fin_h - 0.08)], sw=0.6)

    # ---- fuselage
    pts, xs = b.outline()
    c.poly(pts, fill=WHITE)
    # belly shade (lower third), deeper strip at the very bottom
    band = [(x, b.bot(x) + 0.36 * (b.top(x) - b.bot(x))) for x in xs]
    c.poly(band + [(x, b.bot(x)) for x in reversed(xs)], fill=SHADE)
    band2 = [(x, b.bot(x) + 0.10 * (b.top(x) - b.bot(x))) for x in xs]
    c.poly(band2 + [(x, b.bot(x)) for x in reversed(xs)], fill=SHADE2, opacity=0.7)
    # crown highlight line
    c.line([(x, b.top(x) - 0.07 * D) for x in xs if b.Ln * 1.1 < x < b.xt * 0.99], stroke="#ffffff", sw=1.0, opacity=0.9)
    c.poly(pts, fill="none", stroke=LINE, sw=0.8)
    if s.belly_fairing:
        fx0, fx1 = wx - 0.15 * s.root, wx + s.root * 1.15
        curve = sweep_curve(fx0, fx1, 30, lambda x: (x, -s.belly_fairing * max(0.0, math.sin(math.pi * (x - fx0) / (fx1 - fx0))) ** 0.6))
        c.poly(curve + [(fx1, 0.02), (fx0, 0.02)], fill=SHADE2)
        c.line(curve, sw=0.6)

    # ---- doors and overwing exits
    for dxf in s.doors:
        dx = dxf * L
        dyb = max(b.bot(dx), b.bot(dx + s.door_w)) + s.door_y * D
        dh = s.door_h * D
        c.rrect(dx, dyb, s.door_w, dh, s.door_w * 0.22, fill="none", stroke=LINE, sw=0.7)
    for exf in s.exits:
        ex_ = exf * L
        c.rrect(ex_, s.win_y * D - 0.5, 0.5, 0.95, 0.12, fill="none", stroke=LINE, sw=0.6)

    # ---- cabin windows
    if s.freighter:
        cw = min(3.6, 0.07 * L)
        cx = 0.74 * L if not s.upper_deck else 0.70 * L
        c.rrect(cx, 0.36 * D, cw, 0.5 * D, 0.25, fill="none", stroke=LINE, sw=0.8)
        if s.upper_deck:  # 747F nose door hinge line
            c.line([(b.Ln * 0.95, b.top(b.Ln * 0.95) - 0.02), (b.Ln * 1.05, b.bot(b.Ln * 1.05) + 0.4 * D)], sw=0.7)
    if s.windows and not s.freighter:
        def row(y, x0, x1):
            x = x0
            while x < x1:
                if not any(d * L - 0.25 < x < d * L + s.door_w + 0.25 for d in s.doors):
                    c.rrect(x - s.win_w / 2, y - s.win_h / 2, s.win_w, s.win_h, s.win_w * s.win_round, fill=WINDOW)
                x += s.win_pitch
        row(s.win_y * D, s.win_from * L, s.win_to * L)
        if s.upper_deck and s.upper_win_to:
            row(D + 0.16 * D, b.Ln * 1.15, s.upper_win_to * L)
        if s.double_deck:
            row(s.win_y * D + 0.36 * D, s.win_from * L + 1.0, s.win_to * L - 2.0)

    # ---- cockpit glass
    cockpit_side(c, s, b)

    # ---- tail and centre engines (near side, over the body)
    for e in s.engines:
        if e.mount == "tail":
            ex, ey = e.x * L, e.y * D
            # pylon stub
            c.poly([(ex + 0.35 * e.length, ey), (ex + 0.75 * e.length, ey),
                    (ex + 0.85 * e.length, ey + 0.45 * e.dia), (ex + 0.30 * e.length, ey + 0.45 * e.dia)], fill=SHADE, stroke=LINE, sw=0.5)
            nacelle_side(c, ex, ey, e)
        elif e.mount == "center":
            ex = e.x * L
            ty = b.top(ex)
            c.poly([(ex, ty + 0.05)] + sweep_curve(0, 1, 16, lambda t: (
                ex + t * 0.55 * e.length, ty + e.dia * 0.62 * superq(t, 2.2))) + [(ex + 1.2 * e.length, b.top(ex + 1.2 * e.length))],
                fill=WHITE, stroke=LINE, sw=0.7)
            c.ellipse(ex + 0.04 * e.length, ty + e.dia * 0.32, 0.06 * e.length, e.dia * 0.26, fill=DARK)

    # ---- near stabiliser
    stab(True)

    # ---- near wing
    zt = semi
    zk = s.kink * semi if s.kink else None
    le = [(wing_le(0), wing_y(0)), (wing_le(zt), wing_y(zt))]
    te = [(wing_le(zt) + s.tip, wing_y(zt))]
    if zk:
        te.append((wing_le(zk) + wing_chord(zk), wing_y(zk)))
    te.append((wx + s.root, wing_y(0)))
    th = 0.11 * s.root
    if s.wing_pos == "high":
        th = 0.16 * s.root
        wpts = [(le[0][0], le[0][1] + th * 0.5)] + le[1:] + te + [(le[0][0] + 0.1 * s.root, le[0][1] - th * 0.4)]
    else:
        wpts = [(le[0][0], le[0][1] + th)] + [(le[1][0], le[1][1] + th * 0.25)] + te
    c.poly(wpts, fill=WING, stroke=LINE, sw=0.7)
    # leading-edge highlight & flap line
    c.line([(le[0][0] + 0.02 * s.root, le[0][1] + th * 0.7), (le[1][0] + 0.05, le[1][1] + th * 0.15)], stroke="#ffffff", sw=1.0)
    fl = [(wing_le(z) + 0.72 * wing_chord(z), wing_y(z)) for z in (0.05 * semi, 0.7 * semi)]
    c.line(fl, sw=0.55)
    if s.strut:
        sx = wing_le(0.55 * semi) + 0.4 * wing_chord(0.55 * semi)
        c.line([(wx + 0.3 * s.root, 0.12 * D), (sx, wing_y(0.55 * semi))], stroke=LINE, sw=1.6)
        c.line([(wx + 0.3 * s.root, 0.12 * D), (sx, wing_y(0.55 * semi))], stroke=WHITE, sw=0.8)

    # ---- winglet at the near tip
    winglet_side(c, s, wing_le(zt), wing_y(zt), s.tip)

    # ---- wing engines (inboard first; outboard is nearer the eye)
    for e in sorted([e for e in s.engines if e.mount == "wing"], key=lambda e: e.z):
        z = e.z * semi
        lx = wing_le(z)
        wyz = wing_y(z)
        if e.kind == "fan":
            ex = lx - e.fwd * e.length
            ey = wyz - e.drop * e.dia - e.dia / 2
            if e.gc:
                ey = -s.gear_h + e.gc + e.dia / 2
            # pylon
            c.poly([(ex + 0.35 * e.length, ey + e.dia * 0.42), (lx + 0.25 * wing_chord(z), wyz + 0.05),
                    (lx + 0.55 * wing_chord(z), wyz), (ex + 0.95 * e.length, ey + e.dia * 0.30)], fill=WHITE, stroke=LINE, sw=0.6)
            nacelle_side(c, ex, ey, e)
        else:
            prop_nacelle_side(c, s, e, lx, wyz, wing_chord(z))
    for e in s.engines:
        if e.mount == "nose":
            nose_prop_side(c, s, b, e)

    return c.svg(title=s.name)


def nacelle_side(c: Canvas, ex: float, ey: float, e: Engine):
    """Turbofan nacelle, inlet at ex, centre height ey."""
    r, Ln = e.dia / 2, e.length
    noz = 0.80 * Ln

    def prof(t):  # radius along the cowl: rounded lip, fat fan case, tapering nozzle
        lip = 0.88 + 0.12 * superq(min(t / 0.22, 1), 2.2)
        taper = 1 - 0.30 * max(0.0, (t - 0.40) / 0.60) ** 1.7
        return r * lip * taper

    top = sweep_curve(0, 1, 24, lambda t: (ex + t * noz, ey + prof(t)))
    bot = [(x, ey - (y - ey)) for x, y in top]
    body = top + list(reversed(bot))
    # exhaust: core cowl then plug
    rc = prof(1) * 0.78
    c.poly([(ex + noz - 0.05, ey + rc), (ex + noz + 0.12 * Ln, ey + rc * 0.62), (ex + noz + 0.12 * Ln, ey - rc * 0.62),
            (ex + noz - 0.05, ey - rc)], fill=SHADE, stroke=LINE, sw=0.5)
    pr = rc * 0.55
    c.poly([(ex + noz + 0.11 * Ln, ey + pr), (ex + Ln + 0.06 * Ln, ey), (ex + noz + 0.11 * Ln, ey - pr)], fill=METAL, stroke=LINE, sw=0.4)
    c.poly(body, fill=WHITE)
    c.poly([(x, ey - 0.15 * (y - ey)) for x, y in top] + list(reversed(bot)), fill=SHADE)
    c.poly([(x, ey - 0.75 * (y - ey)) for x, y in top] + list(reversed(bot)), fill=SHADE2, opacity=0.6)
    c.line([(x, ey + 0.72 * (y - ey)) for x, y in top[2:-3]], stroke="#ffffff", sw=1.2)
    c.poly(body, fill="none", stroke=LINE, sw=0.7)
    # inlet: dark opening seen nearly edge-on, with a lighter lip
    c.ellipse(ex + 0.035 * Ln, ey, 0.045 * Ln, r * 0.80, fill=INK)
    c.ellipse(ex + 0.012 * Ln, ey, 0.022 * Ln, r * 0.86, fill=SHADE2)
    # fan cowl split line
    c.line([(ex + 0.45 * Ln, ey + prof(0.45) * 0.98), (ex + 0.45 * Ln, ey - prof(0.45) * 0.98)], sw=0.45)
    if e.chevrons:
        n = 7
        xr = ex + noz
        yr = r * 0.78
        pts = []
        for i in range(n + 1):
            y = yr - 2 * yr * i / n
            pts.append((xr + (0.05 * Ln if i % 2 else 0), y))
        c.line(pts, stroke=LINE, sw=0.6)


def prop_nacelle_side(c: Canvas, s: Spec, e: Engine, lx: float, wyz: float, chord: float):
    """Turboprop/piston nacelle on the wing, propeller in front."""
    r = e.dia / 2
    over = e.over or s.wing_pos == "high"
    ey = wyz - r * 0.55 if over else wyz + r * 0.25
    Ln = max(e.length, chord * 1.25)
    ex = lx - 0.38 * Ln

    def prof(t):
        return r * superq(min(t / 0.2, 1.0), 2.2) * (1 - 0.88 * max(0.0, (t - 0.5) / 0.5) ** 1.7)

    top = sweep_curve(0, 1, 24, lambda t: (ex + t * Ln, ey + prof(t)))
    bot = [(x, ey - (y - ey)) for x, y in top]
    body = top + list(reversed(bot))
    c.poly(body, fill=WHITE)
    c.poly([(x, ey - 0.2 * (y - ey)) for x, y in top] + list(reversed(bot)), fill=SHADE)
    c.poly(body, fill="none", stroke=LINE, sw=0.7)
    c.ellipse(ex + 0.16 * Ln, ey - r * 0.72, 0.07 * Ln, r * 0.18, fill=DARK)   # chin intake
    c.ellipse(ex + 0.62 * Ln, ey + r * 0.25, 0.06 * Ln, r * 0.12, fill=DARK)   # exhaust stub
    propeller_side(c, ex, ey, e)


def propeller_side(c: Canvas, x: float, y: float, e: Engine):
    R = e.prop_d / 2
    c.ellipse(x - 0.06, y, max(0.08, R * 0.05), R, fill=PROP, opacity=0.22)
    for k in (-1, 1):
        c.poly([(x - 0.05, y + k * R * 0.12), (x - 0.02, y + k * R * 0.95), (x - 0.13, y + k * R * 0.98), (x - 0.15, y + k * R * 0.12)],
               fill=PROP, opacity=0.85)
    sr = max(e.dia * 0.28, 0.18)
    c.poly(sweep_curve(-1, 1, 20, lambda t: (x - sr * 1.5 * math.cos(t * math.pi / 2) ** 1.3, y + sr * t)) , fill=WHITE, stroke=LINE, sw=0.6)


def nose_prop_side(c: Canvas, s: Spec, b: Body, e: Engine):
    y = b.tip
    propeller_side(c, 0.0, y, e)


def cockpit_side(c: Canvas, s: Spec, b: Body):
    D = s.D
    if s.cockpit == "ga":
        # canopy/side windows of a light aircraft: greenhouse over the cabin
        x0 = (s.cockpit_x or 0.30) * s.L
        x1 = x0 + 0.24 * s.L
        y0 = 0.52 * D
        top = sweep_curve(x0 + 0.25, x1, 14, lambda x: (x, b.top(x) - 0.06 * D))
        pts = [(x0, y0)] + top + [(x1 + 0.25, y0)]
        c.poly(pts, fill=GLASS, stroke=DARK, sw=0.6)
        c.line([(x0 + 0.45 * (x1 - x0), y0), (x0 + 0.42 * (x1 - x0), b.top(x0 + 0.42 * (x1 - x0)) - 0.06 * D)], stroke=WHITE, sw=1.4)
        c.poly([(x0 + 0.2, y0 + 0.08), (x0 + 0.5, b.top(x0 + 0.5) - 0.12 * D), (x0 + 0.75, b.top(x0 + 0.75) - 0.12 * D), (x0 + 0.5, y0 + 0.08)],
               fill=GLASS_HI, opacity=0.7)
        return
    Ln = b.Ln
    if s.cockpit == "bizjet":
        xa, xb, depth, slope = 0.45, 0.93, 0.24, 0.10
    else:
        xa, xb, depth, slope = 0.50, 0.97, 0.20, 0.16
    if s.cockpit_x:
        xa, xb = s.cockpit_x, s.cockpit_x + 0.45
    xb_ = xb * Ln
    m = 0.045 * D
    yb = b.top(xb_) - m - depth * D
    # front point where the inset top line meets the slanted bottom
    xf = xa * Ln
    for i in range(200):
        x = xa * Ln + (xb_ - xa * Ln) * i / 200
        if b.top(x) - m >= yb + slope * (xb_ - x) * 0.5:
            xf = x
            break
    top = sweep_curve(xf, xb_, 16, lambda x: (x, b.top(x) - m))
    bot = [(xb_, yb), (xf, yb + slope * (xb_ - xf) * 0.5)]
    c.poly(top + bot, fill=GLASS, stroke=DARK, sw=0.7)
    # frames
    for t in (0.33, 0.66):
        x = xf + (xb_ - xf) * t
        c.line([(x, b.top(x) - m), (x + 0.05 * Ln, yb + slope * (xb_ - x - 0.05 * Ln) * 0.5)], stroke=DARK, sw=0.6)
    # highlight
    x = xf + (xb_ - xf) * 0.08
    c.poly([(x, b.top(x) - m * 1.6), (x + 0.12 * (xb_ - xf), b.top(x + 0.12 * (xb_ - xf)) - m * 1.6),
            (x + 0.05 * (xb_ - xf), yb + slope * (xb_ - x) * 0.5 + 0.03)], fill=GLASS_HI, opacity=0.8)


def winglet_side(c: Canvas, s: Spec, x: float, y: float, chord: float):
    t = s.wingtip
    h = s.winglet_h or {"winglet": 2.4, "blended": 2.4, "scimitar": 2.4, "at": 2.0, "sharklet": 2.4,
                        "fence": 0.9, "canted": 1.8, "tank": 0, "tipwing": 0.9}.get(t, 0)
    if t in ("plain", "raked") or not h:
        if t == "tank":
            c.ellipse(x + chord * 0.5, y, chord * 0.75, chord * 0.18, fill=WHITE, stroke=LINE, sw=0.6)
        return
    if t == "fence":
        c.poly([(x + 0.1 * chord, y + 0.05), (x + 0.65 * chord, y + h), (x + 0.95 * chord, y + h), (x + chord, y),
                (x + 0.8 * chord, y - h * 0.6), (x + 0.55 * chord, y - h * 0.6)], fill=WHITE, stroke=LINE, sw=0.6)
        return
    if t in ("winglet", "blended", "scimitar", "canted", "tipwing"):
        sweep_x = h * 0.55
        pts = [(x, y)] + sweep_curve(0, 1, 12, lambda u: (x + 0.1 * chord + sweep_x * u ** 1.4 + 0.2 * chord * u, y + h * superq(u, 1.6))) + \
              [(x + sweep_x + 0.75 * chord, y + h), (x + chord, y + 0.1)]
        c.poly(pts, fill=WHITE, stroke=LINE, sw=0.6)
        c.line([(x + 0.5 * chord, y + 0.2), (x + sweep_x * 0.9 + 0.6 * chord, y + h * 0.92)], sw=0.45)
        if t == "scimitar":
            c.poly([(x + 0.25 * chord, y), (x + 0.55 * chord + 0.5, y - 0.85), (x + 0.75 * chord + 0.6, y - 0.85), (x + 0.9 * chord, y)],
                   fill=WHITE, stroke=LINE, sw=0.6)
        return
    if t == "sharklet":
        # blended curve up out of the tip, then a straight swept blade
        top_x = x + 0.55 * chord + h * 0.35
        le = sweep_curve(0, 1, 16, lambda u: (x + 0.05 * chord + (top_x - x - 0.05 * chord) * u ** 1.6, y + h * math.sin(u * math.pi / 2) ** 0.8))
        te = sweep_curve(1, 0, 16, lambda u: (x + chord + (top_x + 0.35 * chord - x - chord) * u ** 1.1, y + h * u ** 1.2))
        pts = le + te
        c.poly(pts, fill=WHITE, stroke=LINE, sw=0.6)
        return
    if t == "at":
        # 737 MAX "dual feather": upper and lower fins
        c.poly([(x + 0.05 * chord, y), (x + 0.4 * chord + 1.2, y + h), (x + 0.4 * chord + 1.55, y + h), (x + chord, y)],
               fill=WHITE, stroke=LINE, sw=0.6)
        c.poly([(x + 0.2 * chord, y), (x + 0.45 * chord + 0.65, y - 0.85 * h * 0.5), (x + 0.6 * chord + 0.8, y - 0.85 * h * 0.5),
                (x + 0.95 * chord, y)], fill=WHITE, stroke=LINE, sw=0.6)


# ---------------------------------------------------------------- top view
def below(s: Spec) -> str:
    """Belly view, nose up, gear down: the aircraft passing overhead."""
    if s.kind == "balloon":
        return balloon(s, plan=True)
    if s.kind == "heli":
        return heli_top(s, below=True)
    return top(s, below=True)


def top(s: Spec, below: bool = False) -> str:
    if s.kind == "balloon":
        return balloon(s, plan=True)
    if s.kind == "heli":
        return heli_top(s)
    c = Canvas(max(s.L, s.span) / 330)
    b = Body(s)
    L, W = s.L, s.W
    semi = s.span / 2 - W / 2
    wx = s.wing_x * L
    tans = math.tan(math.radians(s.sweep))

    # plan coordinates: X = spanwise (right +), Y = -x (nose up)
    def P(x, z):
        return (z, -x)

    # fuselage half-width along x
    def hw(x):
        if x < b.Ln * 1.15:
            t = x / (b.Ln * 1.15)
            return W / 2 * superq(t, 1.8 if s.cockpit != "ga" else 2.4)
        if x > b.xt:
            t = (x - b.xt) / b.Lt
            return W / 2 * (1 - 0.86 * t ** 1.5)
        return W / 2

    def chord(z):
        r = z / semi if semi else 0
        if s.kink and r < s.kink:
            return s.root + (s.kink_chord - s.root) * (r / s.kink)
        c0, r0 = (s.kink_chord, s.kink) if s.kink else (s.root, 0.0)
        return c0 + (s.tip - c0) * (r - r0) / (1 - r0)

    def le(z):
        return wx + z * tans

    rake = s.wingtip == "raked"

    def half_wing(sign):
        zs = [0.0] + ([s.kink * semi] if s.kink else []) + [semi]
        lep = [(le(0), W / 2 * 0.95)]
        if rake:
            lep.append((le(semi * 0.9), W / 2 + semi * 0.9))
            lep.append((le(semi) + s.tip * 0.75, W / 2 + semi))
            tep = [(le(semi) + s.tip, W / 2 + semi), ]
        else:
            lep.append((le(semi), W / 2 + semi))
            tep = [(le(semi) + s.tip, W / 2 + semi)]
        for z in reversed(zs[:-1]):
            tep.append((le(z) + chord(z), W / 2 + z if z else W / 2 * 0.95))
        pts = [P(x, sign * z) for x, z in lep + tep]
        c.poly(pts, fill=WHITE, stroke=LINE, sw=0.8)
        # flaps & ailerons
        fz = [0.04 * semi, 0.62 * semi, 0.95 * semi]
        c.line([P(le(z) + 0.76 * chord(z), sign * (W / 2 + z)) for z in fz[:2]], sw=0.55)
        c.line([P(le(z) + 0.78 * chord(z), sign * (W / 2 + z)) for z in fz[1:]], sw=0.55)
        for z in fz[:2]:
            c.line([P(le(z) + 0.76 * chord(z), sign * (W / 2 + z)), P(le(z) + chord(z), sign * (W / 2 + z))], sw=0.45)
        # winglet seen from above: small swept tip
        if s.wingtip in ("winglet", "blended", "scimitar", "sharklet", "at", "canted", "fence"):
            x0 = le(semi)
            zz = W / 2 + semi
            ww = 0.12 if s.wingtip == "fence" else 0.28
            c.poly([P(x0 + 0.15 * s.tip, sign * zz), P(x0 + 0.75 * s.tip + 0.6, sign * (zz + ww)),
                    P(x0 + s.tip + 0.6, sign * (zz + ww)), P(x0 + s.tip, sign * zz)], fill=SHADE, stroke=LINE, sw=0.5)
        if s.wingtip == "tank":
            c.ellipse(*P(le(semi) + s.tip * 0.5, sign * (W / 2 + semi)), 0.25, s.tip * 0.8, fill=WHITE, stroke=LINE, sw=0.6)
        if s.strut:
            c.line([P(wx + 0.3 * s.root, sign * W / 2), P(le(0.55 * semi) + 0.4 * chord(0.55 * semi), sign * (W / 2 + 0.55 * semi))],
                   stroke=SHADE2, sw=1.2)

    def stab_half(sign):
        semi_s = s.stab_span / 2
        ts = math.tan(math.radians(s.stab_sweep))
        if s.stab_on_fin:
            fr = s.stab_on_fin
            sx = s.fin_x * L + fr * s.fin_h * math.tan(math.radians(s.fin_sweep)) + 0.1 * s.fin_root * (1 - 0.5 * (1 - fr))
            z0 = 0.15
        else:
            sx = s.stab_x * L
            z0 = hw(sx) * 0.9
        pts = [(sx, z0), (sx + (semi_s - z0) * ts, semi_s), (sx + (semi_s - z0) * ts + s.stab_tip, semi_s), (sx + s.stab_root, z0)]
        c.poly([P(x, sign * z) for x, z in pts], fill=WHITE, stroke=LINE, sw=0.7)
        c.line([P(sx + 0.7 * s.stab_root, sign * z0), P(sx + (semi_s - z0) * ts + 0.6 * s.stab_tip, sign * semi_s * 0.97)], sw=0.5)

    # engines under the wing (from above the wing covers their rear)
    def wing_engines():
      for e in s.engines:
        if e.mount != "wing":
            continue
        z = e.z * semi
        for sign in (1, -1):
            zc = sign * (W / 2 + z)
            if e.kind == "fan":
                ex = le(z) - e.fwd * e.length
                r = e.dia / 2
                pts = [P(ex + 0.02, zc - r * 0.92), P(ex + 0.78 * e.length, zc - r * 0.78), P(ex + e.length, zc - r * 0.3),
                       P(ex + e.length, zc + r * 0.3), P(ex + 0.78 * e.length, zc + r * 0.78), P(ex + 0.02, zc + r * 0.92)]
                c.poly(pts, fill=WHITE, stroke=LINE, sw=0.7)
                c.poly([P(ex, zc - r * 0.92), P(ex, zc + r * 0.92), P(ex + 0.06 * e.length, zc + r * 0.95), P(ex + 0.06 * e.length, zc - r * 0.95)],
                       fill=DARK)
            else:
                ex = le(z) - 0.45 * e.length
                r = e.dia / 2
                c.poly([P(ex, zc - r * 0.6), P(ex + 0.3 * e.length, zc - r), P(ex + e.length * 1.05, zc - r * 0.6),
                        P(ex + e.length * 1.25, zc), P(ex + e.length * 1.05, zc + r * 0.6), P(ex + 0.3 * e.length, zc + r), P(ex, zc + r * 0.6)],
                       fill=WHITE, stroke=LINE, sw=0.7)
                prop_top(c, P(ex - 0.1, zc), e)

    if not below:
        wing_engines()
    for sign in (1, -1):
        stab_half(sign)
        if not s.wing_pos == "high" or below:
            half_wing(sign)
    if below:
        wing_engines()

    # fuselage
    xs = [L * i / 140 for i in range(141)]
    right = [P(x, hw(x)) for x in xs]
    left = [P(x, -hw(x)) for x in reversed(xs)]
    c.poly(right + left, fill=WHITE)
    c.poly(right + [P(x, hw(x) * 0.45) for x in reversed(xs)], fill=SHADE, opacity=0.75)
    if below:
        c.poly(right + left, fill=SHADE2, opacity=0.35)
    c.poly(right + left, fill="none", stroke=LINE, sw=0.8)
    # spine highlight
    c.line([P(x, -hw(x) * 0.3) for x in xs if b.Ln < x < b.xt], stroke="#ffffff", sw=1.0)

    if below:
        if s.belly_fairing:
            c.ellipse(*P(wx + s.root * 0.5, 0), W * 0.62, s.root * 0.75, fill=SHADE, stroke=LINE, sw=0.5)
        # gear down
        tr = (s.track or W * 1.5) / 2
        def tyre(x, z, n):
            for k in range(n):
                xx = x + (k - (n - 1) / 2) * s.wheel_d * 1.25
                for dz in ((-0.28, 0.28) if s.wheel_d > 0.8 else (0,)):
                    c.rrect(z + dz - 0.17, -xx - s.wheel_d / 2, 0.34, s.wheel_d, 0.12, fill=INK)
        if not s.tailwheel:
            tyre(s.nose_gear * L, 0, 1)
        for i, mg in enumerate(s.main_gear):
            n = s.axles[min(i, len(s.axles) - 1)]
            zz = tr if i == 0 else tr * 0.45
            for sign in (1, -1):
                tyre(mg * L, sign * zz, n)
        if s.tailwheel:
            tyre(0.93 * L, 0, 1)
    if s.wing_pos == "high" and not below:
        for sign in (1, -1):
            half_wing(sign)
        # wing centre section over the fuselage
        c.poly([P(wx, -W / 2), P(wx, W / 2), P(wx + s.root, W / 2), P(wx + s.root, -W / 2)], fill=WHITE, stroke=LINE, sw=0.6)

    # cockpit windows
    if below:
        pass
    elif s.cockpit in ("airliner", "bizjet"):
        y0 = b.Ln * 0.62
        for sign in (1, -1):
            c.poly([P(y0, sign * hw(y0) * 0.15), P(y0 - 0.05 * b.Ln, sign * hw(y0) * 0.7), P(y0 + 0.16 * b.Ln, sign * hw(y0 + 0.16 * b.Ln) * 0.95),
                    P(y0 + 0.2 * b.Ln, sign * hw(y0 + 0.2 * b.Ln) * 0.3)], fill=GLASS, stroke=DARK, sw=0.5)
    elif s.cockpit == "ga":
        x0 = (s.cockpit_x or 0.30) * L
        c.poly([P(x0, -W * 0.38), P(x0 + 0.25 * L * 0.9, -W * 0.36), P(x0 + 0.25 * L * 0.9, W * 0.36), P(x0, W * 0.38)],
               fill=GLASS, stroke=DARK, sw=0.5)

    # tail-mounted and centre engines
    for e in s.engines:
        if e.mount == "tail":
            ex = e.x * L
            r = e.dia / 2
            for sign in (1, -1):
                zc = sign * (hw(ex + 0.5 * e.length) + r * 0.95)
                c.poly([P(ex + 0.3 * e.length, sign * hw(ex + 0.3 * e.length) * 0.8), P(ex + 0.3 * e.length, zc),
                        P(ex + 0.75 * e.length, zc), P(ex + 0.8 * e.length, sign * hw(ex + 0.8 * e.length) * 0.8)], fill=SHADE, stroke=LINE, sw=0.5)
                c.poly([P(ex, zc - r * 0.9), P(ex + 0.8 * e.length, zc - r * 0.75), P(ex + e.length, zc - r * 0.35),
                        P(ex + e.length, zc + r * 0.35), P(ex + 0.8 * e.length, zc + r * 0.75), P(ex, zc + r * 0.9)],
                       fill=WHITE, stroke=LINE, sw=0.7)
                c.poly([P(ex, zc - r * 0.9), P(ex, zc + r * 0.9), P(ex + 0.06 * e.length, zc + r * 0.92), P(ex + 0.06 * e.length, zc - r * 0.92)], fill=DARK)
        elif e.mount == "center" and not below:
            ex = e.x * L
            c.ellipse(*P(ex + 0.35 * e.length, 0), e.dia * 0.42, 0.45 * e.length, fill=WHITE, stroke=LINE, sw=0.6)
            c.ellipse(*P(ex + 0.05 * e.length, 0), e.dia * 0.3, 0.06 * e.length, fill=DARK)
        elif e.mount == "nose":
            prop_top(c, P(-0.05, 0), e)

    if below:
        return c.svg(title=s.name)
    # fin seen edge-on
    fx = s.fin_x * L
    ft = max(0.12, s.fin_root * 0.07)
    fin_end = min(fx + s.fin_root, L)
    c.poly([P(fx - (s.dorsal * s.fin_root), 0)] + [P(fx + s.fin_root * 0.35, ft)] + [P(fin_end, ft * 0.4), P(fin_end, -ft * 0.4),
           P(fx + s.fin_root * 0.35, -ft)], fill=SHADE2, stroke=LINE, sw=0.5)
    if s.stab_on_fin:
        stab_half(1)
        stab_half(-1)
    return c.svg(title=s.name)


def prop_top(c: Canvas, at, e: Engine):
    R = e.prop_d / 2
    x, y = at
    c.ellipse(x, y, R, max(0.07, R * 0.05), fill=PROP, opacity=0.22)
    c.poly([(x - R * 0.95, y + 0.06), (x + R * 0.95, y + 0.06), (x + R * 0.95, y - 0.06), (x - R * 0.95, y - 0.06)], fill=PROP, opacity=0.8)
    c.ellipse(x, y - 0.12, e.dia * 0.22, 0.25, fill=WHITE, stroke=LINE, sw=0.5)


# ---------------------------------------------------------------- helicopters
def heli_side(s: Spec) -> str:
    """Helicopters reuse Spec loosely: L = fuselage length incl. tail boom,
    D = cabin height, span = main rotor diameter, root = cabin length."""
    c = Canvas(s.span / 330)
    L, D = s.L, s.D
    cab = s.root  # cabin pod length
    gy = -s.gear_h
    # skids or wheels
    if s.tailwheel:  # used as 'wheels' flag for helicopters
        for x in (0.12 * L, 0.42 * L):
            c.poly([(x - 0.06, 0.2), (x + 0.06, 0.2), (x + 0.06, gy + 0.3), (x - 0.06, gy + 0.3)], fill=METAL)
            c.ellipse(x, gy + 0.3, 0.3, 0.3, fill=INK)
            c.ellipse(x, gy + 0.3, 0.13, 0.13, fill=HUB)
    else:
        c.line([(0.12 * cab, gy + 0.05), (0.2 * cab, 0.1)], stroke=METAL, sw=1.8)
        c.line([(0.78 * cab, gy + 0.05), (0.7 * cab, 0.1)], stroke=METAL, sw=1.8)
        c.poly([(-0.05 * cab, gy + 0.22), (0.02 * cab, gy), (0.95 * cab, gy), (0.95 * cab, gy + 0.09), (0.02 * cab, gy + 0.09)], fill=INK)
    # tail boom
    bx0, by = cab * 0.75, D * 0.62
    boom = [(bx0, by + 0.32 * D), (L - 0.6, by + 0.14 * D + 0.35), (L - 0.6, by + 0.02 * D + 0.25), (bx0, by - 0.2 * D)]
    c.poly(boom, fill=WHITE, stroke=LINE, sw=0.8)
    c.poly([boom[0][0:2], boom[1], (L - 0.6, by + 0.08 * D + 0.3), (bx0, by + 0.05 * D)], fill="none")
    c.poly([(bx0, by - 0.2 * D), (L - 0.6, by + 0.02 * D + 0.25), (L - 0.6, by + 0.08 * D + 0.25), (bx0, by - 0.05 * D)], fill=SHADE)
    # tail: fin + fenestron or rotor
    tx = L - 0.9
    ty = by + 0.25
    fin_h = s.fin_h
    c.poly([(tx - 0.9, ty), (tx - 0.2, ty + fin_h), (tx + 0.35, ty + fin_h), (tx + 0.6, ty - 0.2), (tx - 0.1, ty - 0.55 * fin_h * 0.5)],
           fill=WHITE, stroke=LINE, sw=0.8)
    c.poly([(tx - 1.6, ty + 0.15), (tx - 1.2, ty + 0.3), (tx - 0.5, ty + 0.3), (tx - 0.9, ty + 0.12)], fill=SHADE, stroke=LINE, sw=0.5)
    if s.wingtip == "fenestron":
        c.ellipse(tx, ty + 0.25, 0.42, 0.42, fill=DARK)
        c.ellipse(tx, ty + 0.25, 0.32, 0.32, fill=SHADE2)
        for a in range(0, 180, 30):
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            c.line([(tx - 0.32 * ca, ty + 0.25 - 0.32 * sa), (tx + 0.32 * ca, ty + 0.25 + 0.32 * sa)], stroke=DARK, sw=0.4)
    else:
        rr = s.stab_span / 2
        c.ellipse(tx + 0.15, ty + fin_h * 0.6, rr, rr, fill=PROP, opacity=0.18)
        c.line([(tx + 0.15 - rr * 0.9, ty + fin_h * 0.6 - rr * 0.3), (tx + 0.15 + rr * 0.9, ty + fin_h * 0.6 + rr * 0.3)], stroke=PROP, sw=1.0)
        c.ellipse(tx + 0.15, ty + fin_h * 0.6, 0.08, 0.08, fill=DARK)
    # cabin pod
    def ctop(x):
        t = x / cab
        if t < 0.38:
            return D * (0.45 + 0.55 * superq(t / 0.38, 2.0))
        return D * (1 - 0.18 * ((t - 0.38) / 0.62) ** 2)
    def cbot(x):
        t = x / cab
        if t < 0.25:
            return D * 0.3 * (1 - superq(t / 0.25, 2.0))
        return D * 0.04 * (t - 0.25) / 0.75 + (D * 0.3 * max(0, (t - 0.82) / 0.18) ** 1.5)
    xs = [cab * i / 60 for i in range(61)]
    pod = [(x, ctop(x)) for x in xs] + [(x, cbot(x)) for x in reversed(xs)]
    c.poly(pod, fill=WHITE)
    c.poly([(x, cbot(x) + 0.32 * (ctop(x) - cbot(x))) for x in xs] + [(x, cbot(x)) for x in reversed(xs)], fill=SHADE)
    c.poly(pod, fill="none", stroke=LINE, sw=0.8)
    # engine cowling / hump
    hx0, hx1 = 0.35 * cab, 0.95 * cab
    c.poly([(hx0, ctop(hx0) - 0.05)] + sweep_curve(hx0, hx1, 14, lambda x: (x, ctop(x) + 0.28 * D * max(0.0, math.sin(math.pi * (x - hx0) / (hx1 - hx0))) ** 0.5))
           + [(hx1, ctop(hx1) - 0.05)], fill=WHITE, stroke=LINE, sw=0.7)
    c.ellipse(0.8 * cab, ctop(0.8 * cab) + 0.12 * D, 0.18, 0.08 * D, fill=DARK)
    # glass: big wrap-around windscreen + cabin window
    wpts = [(0.06 * cab, 0.42 * D)] + sweep_curve(0.08 * cab, 0.36 * cab, 12, lambda x: (x, ctop(x) - 0.06 * D)) + [(0.36 * cab, 0.45 * D), (0.18 * cab, 0.3 * D)]
    c.poly(wpts, fill=GLASS, stroke=DARK, sw=0.6)
    c.poly([(0.1 * cab, 0.52 * D), (0.14 * cab, ctop(0.14 * cab) - 0.12 * D), (0.2 * cab, ctop(0.2 * cab) - 0.12 * D), (0.15 * cab, 0.48 * D)], fill=GLASS_HI, opacity=0.8)
    c.rrect(0.42 * cab, 0.42 * D, 0.2 * cab, 0.36 * D, 0.12, fill=GLASS, stroke=DARK, sw=0.6)
    c.rrect(0.42 * cab - 0.05, 0.12 * D, 0.2 * cab + 0.1, 0.72 * D, 0.1, fill="none", stroke=LINE, sw=0.6)
    if s.doors:
        c.rrect(0.66 * cab, 0.45 * D, 0.13 * cab, 0.3 * D, 0.1, fill=GLASS, stroke=DARK, sw=0.6)
    # rotor mast, hub, blades
    mx = 0.55 * cab
    my = ctop(mx) + 0.28 * D
    c.poly([(mx - 0.1, my - 0.05), (mx + 0.1, my - 0.05), (mx + 0.08, my + 0.35), (mx - 0.08, my + 0.35)], fill=METAL)
    c.ellipse(mx, my + 0.4, 0.35, 0.13, fill=DARK)
    R = s.span / 2
    c.poly([(mx - R, my + 0.38), (mx + R, my + 0.5), (mx + R, my + 0.43), (mx - R, my + 0.31)], fill=PROP, opacity=0.9)
    c.ellipse(mx, my + 0.42, R, 0.22, fill=PROP, opacity=0.12)
    return c.svg(title=s.name)


def heli_top(s: Spec, below: bool = False) -> str:
    c = Canvas(s.span / 330)
    L, W, cab = s.L, s.W, s.root
    def P(x, z):
        return (z, -x)
    def hw(x):
        t = x / cab
        if t < 0.35:
            return W / 2 * superq(t / 0.35, 2.0)
        if t < 1:
            return W / 2 * (1 - 0.5 * ((t - 0.35) / 0.65) ** 2)
        return 0.18
    xs = [cab * 1.05 * i / 60 for i in range(61)]
    # boom
    c.poly([P(cab * 0.8, -0.3), P(L - 0.5, -0.14), P(L - 0.5, 0.14), P(cab * 0.8, 0.3)], fill=WHITE, stroke=LINE, sw=0.7)
    c.poly([P(L - 1.7, -s.stab_span * 0.0 - 0.9), P(L - 1.3, -0.9), P(L - 1.1, 0.9), P(L - 1.5, 0.9)], fill=WHITE, stroke=LINE, sw=0.6)
    c.poly([P(L - 1.6, -1.0), P(L - 1.2, -1.0), P(L - 1.2, 1.0), P(L - 1.6, 1.0)], fill=WHITE, stroke=LINE, sw=0.6)
    if s.wingtip != "fenestron":
        c.ellipse(*P(L - 0.8, 0.35), 0.1, s.stab_span / 2, fill=PROP, opacity=0.25)
    pod = [P(x, hw(x)) for x in xs] + [P(x, -hw(x)) for x in reversed(xs)]
    c.poly(pod, fill=WHITE)
    c.poly([P(x, hw(x)) for x in xs] + [P(x, hw(x) * 0.4) for x in reversed(xs)], fill=SHADE, opacity=0.75)
    c.poly(pod, fill="none", stroke=LINE, sw=0.8)
    c.poly([P(0.06 * cab, 0)] + [P(x, hw(x) * 0.85) for x in xs if 0.06 * cab < x < 0.32 * cab] + [P(0.32 * cab, 0)] +
           [P(x, -hw(x) * 0.85) for x in reversed(xs) if 0.06 * cab < x < 0.32 * cab], fill=GLASS, stroke=DARK, sw=0.5)
    c.rrect(-W * 0.32, -0.95 * cab, W * 0.64, 0.5 * cab, W * 0.25, fill=WHITE, stroke=LINE, sw=0.6)
    if not s.tailwheel:
        for sign in (1, -1):
            c.rrect(sign * W * 0.62 - 0.07, -cab * 0.98, 0.14, cab * 1.0, 0.07, fill=INK)
    R = s.span / 2
    mx = 0.55 * cab
    hub = P(mx, 0)
    c.ellipse(hub[0], hub[1], R, R, fill=PROP, opacity=0.12)
    nb = s.axles[0] if s.axles else 4
    for k in range(nb):
        a = math.radians(30 + 360 * k / nb)
        ca, sa = math.cos(a), math.sin(a)
        w = R * 0.035
        c.poly([(hub[0] - sa * w, hub[1] + ca * w), (hub[0] + ca * R - sa * w, hub[1] + sa * R + ca * w),
                (hub[0] + ca * R + sa * w, hub[1] + sa * R - ca * w), (hub[0] + sa * w, hub[1] - ca * w)], fill=PROP, opacity=0.9)
    c.ellipse(hub[0], hub[1], 0.3, 0.3, fill=DARK)
    return c.svg(title=s.name)


# ---------------------------------------------------------------- front view
def front(s: Spec) -> str:
    """Head-on view: the aircraft coming straight at you, gear down."""
    if s.kind == "balloon":
        return balloon(s)
    if s.kind == "heli":
        return heli_front(s)
    c = Canvas(s.span / 330)
    D, W, L = s.D, s.W, s.L
    semi = s.span / 2 - W / 2
    wy = {"low": 0.14 * D, "mid": 0.45 * D, "high": 0.95 * D}[s.wing_pos]
    tand = math.tan(math.radians(s.dihedral))
    gy = -s.gear_h

    def wyz(z):
        return wy + z * tand

    # vertical fin (behind everything)
    fb = max(0.25, s.fin_root * 0.09)
    fin_top = D + s.fin_h
    c.poly([(-fb / 2, D * 0.9), (-fb * 0.3, fin_top), (fb * 0.3, fin_top), (fb / 2, D * 0.9)], fill=WHITE, stroke=LINE, sw=0.7)
    c.poly([(0, D * 0.9), (0, fin_top), (fb * 0.3, fin_top), (fb / 2, D * 0.9)], fill=SHADE, opacity=0.8)

    # horizontal stabiliser
    ss = s.stab_span / 2
    sy = (D * 0.9 + s.stab_on_fin * s.fin_h - 0.1) if s.stab_on_fin else s.stab_y * D
    st = max(0.12, s.stab_root * 0.09)
    sd = math.tan(math.radians(0 if s.stab_on_fin else 6))
    for k in (1, -1):
        c.poly([(0, sy + st / 2), (k * ss, sy + ss * sd + st * 0.2), (k * ss, sy + ss * sd - st * 0.2), (0, sy - st / 2)],
               fill=SHADE, stroke=LINE, sw=0.6)

    # wings
    rt, tt = 0.12 * s.root, 0.12 * s.tip
    for k in (1, -1):
        z0, z1 = W / 2 * 0.9, W / 2 + semi
        top_ = [(k * z0, wy + rt * 0.6), (k * z1, wyz(semi) + tt * 0.6)]
        bot_ = [(k * z1, wyz(semi) - tt * 0.4), (k * z0, wy - rt * 0.4)]
        c.poly(top_ + bot_, fill=WHITE, stroke=LINE, sw=0.7)
        c.poly([(k * z0, wy), (k * z1, wyz(semi))] + bot_, fill=SHADE)
        c.poly(top_ + bot_, fill="none", stroke=LINE, sw=0.7)
        if s.strut:
            c.line([(k * W * 0.45, 0.1 * D), (k * (W / 2 + 0.55 * semi), wyz(0.55 * semi))], stroke=LINE, sw=1.2)
        # winglets
        x, y = k * z1, wyz(semi)
        t = s.wingtip
        h = s.winglet_h or {"winglet": 2.4, "blended": 2.4, "scimitar": 2.4, "at": 2.0, "sharklet": 2.4,
                            "fence": 0.9, "canted": 1.8, "tipwing": 0.9}.get(t, 0)
        if h and t not in ("plain", "raked", "tank"):
            cant = {"sharklet": 0.25, "canted": 0.45, "winglet": 0.15, "blended": 0.15, "scimitar": 0.15, "at": 0.1}.get(t, 0.0)
            w = max(0.12, tt * 0.6)
            if t == "sharklet" or t == "canted":
                c.poly(sweep_curve(0, 1, 10, lambda u: (x + k * (cant * h * u + 0.25 * (1 - (1 - u) ** 2)), y + h * u ** 1.1))
                       + [(x + k * (cant * h + 0.25) - k * w, y + h)]
                       + sweep_curve(1, 0, 10, lambda u: (x + k * (cant * h * u) - k * w * 1.4, y + h * u)), fill=WHITE, stroke=LINE, sw=0.6)
            else:
                c.poly([(x, y), (x + k * cant * h, y + h), (x + k * (cant * h - w), y + h), (x - k * w * 1.6, y)], fill=WHITE, stroke=LINE, sw=0.6)
            if t in ("scimitar", "at", "fence"):
                hl = 0.8 if t != "fence" else h * 0.6
                c.poly([(x, y), (x + k * 0.15 * hl, y - hl), (x - k * (w - 0.15 * hl), y - hl), (x - k * w * 1.4, y)],
                       fill=WHITE, stroke=LINE, sw=0.6)
        if t == "tank":
            c.ellipse(x, y, s.tip * 0.18, s.tip * 0.18, fill=WHITE, stroke=LINE, sw=0.6)

    # main gear (behind the fuselage nose but in front of the wing)
    tr = (s.track or W * 1.5) / 2
    def gear_front(z, top, twin):
        c.poly([(z - 0.09, top), (z + 0.09, top), (z + 0.09, gy + s.wheel_d / 2), (z - 0.09, gy + s.wheel_d / 2)], fill=METAL)
        tw = max(0.22, s.wheel_d * 0.33)
        for dz in ((-tw * 0.75, tw * 0.75) if twin else (0,)):
            c.rrect(z + dz - tw / 2, gy, tw, s.wheel_d, tw * 0.35, fill=INK)
            c.rrect(z + dz - tw * 0.18, gy + s.wheel_d * 0.3, tw * 0.36, s.wheel_d * 0.4, tw * 0.15, fill=HUB)
    twin = s.wheel_d > 0.8
    if s.tailwheel:
        for k in (1, -1):
            gear_front(k * tr, 0.15 * D, False)
    else:
        for i, _ in enumerate(s.main_gear):
            zz = tr if i == 0 else tr * 0.45
            for k in (1, -1):
                gear_front(k * zz, wy if s.wing_pos == "low" else 0.1 * D, twin)

    # fuselage cross-section
    c.ellipse(0, D / 2, W / 2, D / 2, fill=WHITE)
    lo = sweep_curve(math.pi, 2 * math.pi, 30, lambda a: (W / 2 * math.cos(a), D / 2 + D / 2 * math.sin(a)))
    c.poly(lo + sweep_curve(0, math.pi, 30, lambda a: (W / 2 * 0.96 * math.cos(math.pi - a) * -1, D / 2 - D * 0.18 * math.sin(a)))[::-1],
           fill=SHADE, opacity=0.9)
    if s.upper_deck:
        H = D * (1 + s.upper_h)
        c.poly(sweep_curve(0, math.pi, 30, lambda a: (W * 0.36 * math.cos(a), D * 0.75 + (H - D * 0.75) * math.sin(a))), fill=WHITE, stroke=LINE, sw=0.7)
    c.ellipse(0, D / 2, W / 2, D / 2, fill="none", stroke=LINE, sw=0.8)
    # radome & nose highlight
    rr = W * 0.24
    c.ellipse(0, D * 0.42, rr, rr * 0.95, fill="#eef0f3", stroke=LINE, sw=0.4)
    c.ellipse(-rr * 0.35, D * 0.52, rr * 0.25, rr * 0.18, fill="#ffffff", opacity=0.8)
    # windscreen
    cy = (D * (1 + s.upper_h) - 0.12 * D) if s.upper_deck else (0.70 * D if s.cockpit != "ga" else 0.74 * D)
    if s.cockpit == "ga":
        c.poly([(-W * 0.4, cy - D * 0.12), (-W * 0.3, cy + D * 0.17), (W * 0.3, cy + D * 0.17), (W * 0.4, cy - D * 0.12)], fill=GLASS, stroke=DARK, sw=0.6)
    else:
        pw = W * 0.13
        for i, k in enumerate((-1.5, -0.5, 0.5, 1.5)):
            x0 = k * pw * 1.08
            slope = 0.05 * D * (abs(k) - 0.5)
            c.poly([(x0 - pw / 2, cy - slope - D * 0.05), (x0 - pw / 2 + 0.03, cy - slope + D * 0.06 - 0.02 * abs(k)),
                    (x0 + pw / 2 - 0.03, cy - slope + D * 0.06 - 0.02 * abs(k)), (x0 + pw / 2, cy - slope - D * 0.05)],
                   fill=GLASS, stroke=DARK, sw=0.5)

    # nose gear
    if not s.tailwheel:
        nwd = s.nose_wheel_d or s.wheel_d * 0.75
        c.poly([(-0.08, 0.15 * D), (0.08, 0.15 * D), (0.08, gy + nwd / 2), (-0.08, gy + nwd / 2)], fill=METAL)
        tw = max(0.18, nwd * 0.3)
        for dz in ((-tw * 0.7, tw * 0.7) if s.wheel_d > 0.8 else (0,)):
            c.rrect(dz - tw / 2, gy, tw, nwd, tw * 0.35, fill=INK)

    # engines (nearest to the eye)
    for e in sorted(s.engines, key=lambda e: -e.z):
        r = e.dia / 2
        if e.mount == "wing":
            z = e.z * semi
            ey = wyz(z) - e.drop * e.dia - r
            if e.gc and e.kind == "fan":
                ey = gy + e.gc + r
            if e.kind != "fan":
                ey = wyz(z) - (0.1 if (e.over or s.wing_pos == "high") else 0.3) * e.dia
            for k in (1, -1):
                zc = k * (W / 2 + z)
                c.poly([(zc - r * 0.18, ey + r * 0.8), (zc + r * 0.18, ey + r * 0.8), (zc + r * 0.12, wyz(z)), (zc - r * 0.12, wyz(z))], fill=SHADE, stroke=LINE, sw=0.5)
                engine_face(c, zc, ey, e)
        elif e.mount == "tail":
            ey = e.y * D
            for k in (1, -1):
                zc = k * (W / 2 + r * 1.05)
                c.poly([(k * W * 0.4, ey - r * 0.2), (zc, ey - r * 0.2), (zc, ey + r * 0.2), (k * W * 0.4, ey + r * 0.2)], fill=SHADE, stroke=LINE, sw=0.5)
                engine_face(c, zc, ey, e)
        elif e.mount == "center":
            ey = D + e.dia * 0.35
            c.ellipse(0, ey, e.dia * 0.42, e.dia * 0.32, fill=WHITE, stroke=LINE, sw=0.6)
            c.ellipse(0, ey, e.dia * 0.32, e.dia * 0.22, fill=INK)
        elif e.mount == "nose":
            engine_face(c, 0, s.nose_tip * D, e)
    return c.svg(title=s.name)


def engine_face(c: Canvas, x: float, y: float, e: Engine):
    r = e.dia / 2
    if e.kind == "fan":
        c.ellipse(x, y, r, r, fill=WHITE, stroke=LINE, sw=0.7)
        c.ellipse(x, y, r * 0.84, r * 0.84, fill=INK)
        c.ellipse(x, y, r * 0.78, r * 0.78, fill=DARK)
        n = 18
        for i in range(n):
            a = 2 * math.pi * i / n
            c.line([(x + r * 0.2 * math.cos(a), y + r * 0.2 * math.sin(a)),
                    (x + r * 0.76 * math.cos(a + 0.35), y + r * 0.76 * math.sin(a + 0.35))], stroke="#6b737d", sw=0.35)
        c.ellipse(x, y, r * 0.2, r * 0.2, fill=METAL)
        c.line(sweep_curve(0, 1, 8, lambda t: (x + r * 0.17 * t * math.cos(5 * t), y + r * 0.17 * t * math.sin(5 * t))), stroke=WHITE, sw=0.5)
        c.ellipse(x - r * 0.55, y + r * 0.55, r * 0.12, r * 0.06, fill="#ffffff", opacity=0.6, rot=-45)
    else:
        R = e.prop_d / 2
        c.ellipse(x, y, r * 0.8, r, fill=WHITE, stroke=LINE, sw=0.6)
        c.ellipse(x, y - r * 0.55, r * 0.35, r * 0.18, fill=INK)
        c.ellipse(x, y, R, R, fill=PROP, opacity=0.18)
        nb = e.blades or 4
        for i in range(nb):
            a = math.pi / 2 + 2 * math.pi * i / nb + 0.3
            ca, sa = math.cos(a), math.sin(a)
            w = R * 0.07
            c.poly([(x - sa * w * 0.6, y + ca * w * 0.6), (x + ca * R - sa * w * 0.4, y + sa * R + ca * w * 0.4),
                    (x + ca * R + sa * w * 0.4, y + sa * R - ca * w * 0.4), (x + sa * w * 0.6, y - ca * w * 0.6)], fill=PROP, opacity=0.85)
        c.ellipse(x, y, max(0.12, r * 0.3), max(0.12, r * 0.3), fill=WHITE, stroke=LINE, sw=0.5)


def heli_front(s: Spec) -> str:
    c = Canvas(s.span / 330)
    D, W = s.D, s.W
    gy = -s.gear_h
    R = s.span / 2
    # skids / wheels
    if s.tailwheel:
        for k in (1, -1):
            c.line([(k * W * 0.3, 0.2), (k * W * 0.7, gy + 0.3)], stroke=METAL, sw=1.8)
            c.rrect(k * W * 0.7 - 0.12, gy, 0.24, 0.6, 0.1, fill=INK)
    else:
        for k in (1, -1):
            c.line([(k * W * 0.25, 0.3), (k * W * 0.6, gy + 0.08)], stroke=METAL, sw=1.8)
            c.rrect(k * W * 0.6 - 0.1, gy, 0.2, 0.14, 0.06, fill=INK)
    # tail fin behind
    c.poly([(-0.08, D * 0.6), (-0.06, D * 0.6 + s.fin_h + 0.6), (0.06, D * 0.6 + s.fin_h + 0.6), (0.08, D * 0.6)], fill=SHADE, stroke=LINE, sw=0.5)
    # cabin
    c.poly(sweep_curve(0, 2 * math.pi, 48, lambda a: (W / 2 * math.cos(a) * (1 - 0.12 * max(0, math.sin(a))), D / 2 + D / 2 * math.sin(a))),
           fill=WHITE, stroke=LINE, sw=0.8)
    c.poly(sweep_curve(math.pi * 1.05, math.pi * 1.95, 20, lambda a: (W / 2 * math.cos(a), D / 2 + D / 2 * math.sin(a))), fill=SHADE)
    c.poly([(-W * 0.42, D * 0.35), (-W * 0.36, D * 0.82), (W * 0.36, D * 0.82), (W * 0.42, D * 0.35), (0, D * 0.3)], fill=GLASS, stroke=DARK, sw=0.6)
    c.line([(0, D * 0.3), (0, D * 0.82)], stroke=DARK, sw=0.8)
    c.poly([(-W * 0.36, D * 0.45), (-W * 0.3, D * 0.75), (-W * 0.2, D * 0.75), (-W * 0.28, D * 0.45)], fill=GLASS_HI, opacity=0.7)
    # engine hump, mast, rotor
    c.poly(sweep_curve(0, math.pi, 20, lambda a: (W * 0.32 * math.cos(a), D * 0.95 + D * 0.3 * math.sin(a))), fill=WHITE, stroke=LINE, sw=0.7)
    my = D * 1.25
    c.poly([(-0.1, my), (0.1, my), (0.08, my + 0.35), (-0.08, my + 0.35)], fill=METAL)
    c.ellipse(0, my + 0.4, 0.35, 0.12, fill=DARK)
    c.poly([(-R, my + 0.36), (R, my + 0.36), (R, my + 0.44), (-R, my + 0.44)], fill=PROP, opacity=0.85)
    return c.svg(title=s.name)


# ---------------------------------------------------------------- balloons
WICKER = "#9a8468"


def balloon(s: Spec, plan: bool = False) -> str:
    """Hot-air balloon: s.span = envelope diameter, s.L = envelope height."""
    c = Canvas(s.span / 200)
    R = s.span / 2
    if plan:
        c.ellipse(0, 0, R, R, fill=WHITE, stroke=LINE, sw=0.8)
        c.poly(sweep_curve(-math.pi / 2, math.pi / 2, 30, lambda a: (R * math.cos(a), R * math.sin(a))), fill=SHADE, opacity=0.6)
        for k in range(16):
            a = 2 * math.pi * k / 16
            c.line([(0, 0), (R * math.cos(a), R * math.sin(a))], sw=0.5)
        c.ellipse(0, 0, R * 0.18, R * 0.18, fill=SHADE2, stroke=LINE, sw=0.5)
        return c.svg(title=s.name)
    H = s.L
    yc = H - R  # centre of the round top

    def env(t):  # t from -1 (left mouth) over the top to +1 (right mouth)
        a = math.pi / 2 - t * math.pi * 0.62
        if abs(t) <= 0.8:
            return (R * math.cos(a), yc + R * math.sin(a))
        # taper down to the mouth
        a0 = math.pi / 2 - math.copysign(0.8, t) * math.pi * 0.62
        x0, y0 = R * math.cos(a0), yc + R * math.sin(a0)
        u = (abs(t) - 0.8) / 0.2
        return (x0 + (math.copysign(R * 0.16, t) - x0) * u ** 0.9, y0 + (1.6 - y0) * u)

    pts = sweep_curve(-1, 1, 80, env)
    c.poly(pts, fill=WHITE)
    c.poly(sweep_curve(0, 1, 40, env) + [(0, 1.6)], fill=SHADE, opacity=0.7)
    for k in range(-4, 5):
        g = k / 5
        c.line(sweep_curve(-1, 1, 40, lambda t: (env(t)[0] * g if True else 0, env(t)[1]))[20:61], sw=0.5)
    c.line([(env(t)[0], env(t)[1]) for t in (-0.98, 0.98)], sw=0.8)
    c.poly(pts, fill="none", stroke=LINE, sw=0.8)
    # load lines, burner, basket
    for k in (-1, 1):
        c.line([(k * R * 0.16, 1.6), (k * 0.55, 0.15 + 1.1)], stroke=DARK, sw=0.5)
    c.rrect(-0.35, 1.0, 0.7, 0.35, 0.05, fill=METAL, stroke=DARK, sw=0.4)
    c.rrect(-0.6, -0.1, 1.2, 1.05, 0.12, fill=WICKER, stroke=DARK, sw=0.5)
    for y in (0.25, 0.6):
        c.line([(-0.58, y), (0.58, y)], stroke="#7d6a52", sw=0.6)
    return c.svg(title=s.name)
