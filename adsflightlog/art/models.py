"""Aircraft specs by ICAO type code.

Dimensions are in metres, taken from manufacturers' airport planning
documents and three-view drawings where available, rounded to what is visible
at card size. Variants are built from their family base with ``replace``, so
the differences between them are explicit here.
"""

from __future__ import annotations

from dataclasses import replace

from .draw import Engine, Spec

SPECS: dict[str, Spec] = {}


def add(code: str, spec: Spec) -> Spec:
    SPECS[code] = spec
    return spec


def fan(z, dia, length, fwd=0.65, drop=0.2, chevrons=False):
    return Engine("wing", z=z, dia=dia, length=length, fwd=fwd, drop=drop, chevrons=chevrons)


# ------------------------------------------------------------ Boeing 737
B737NG = Spec(
    "Boeing 737-800", L=39.5, D=4.01, W=3.76, span=35.8,
    nose_top=((0.0, 0.33), (0.25, 0.41), (0.5, 0.46), (1.0, 0.52), (1.5, 0.57), (1.75, 0.63), (2.0, 0.69),
              (2.5, 0.77), (3.0, 0.81), (3.5, 0.85), (4.0, 0.88), (4.5, 0.91), (5.0, 0.94), (6.0, 0.97), (7.0, 0.98),
              (8.25, 1.0)),
    nose_bot=((0.0, 0.31), (0.25, 0.22), (0.5, 0.19), (1.0, 0.13), (1.5, 0.09), (2.0, 0.05), (2.5, 0.02), (3.0, 0.0)),
    ck=(1.5, 2.95, 0.58, 0.65, 0.65, 0.53),
    tail_len=3.1, tail_top=0.80, tail_bot=0.62,
    wing_x=0.385, root=7.3, kink=0.33, kink_chord=4.3, tip=1.25, sweep=27, dihedral=6,
    wingtip="winglet", winglet_h=2.4,
    fin_x=0.80, fin_root=6.6, fin_tip=1.6, fin_h=6.6, fin_sweep=37, dorsal=0.45,
    stab_x=0.875, stab_span=14.35, stab_root=3.8, stab_tip=1.1, stab_sweep=31, stab_y=0.62,
    win_y=0.60, win_from=0.13, win_to=0.81, win_pitch=0.51,
    doors=(0.11, 0.82), exits=(0.415, 0.445),
    engines=[Engine("wing", z=0.19, dia=2.0, length=3.6, fwd=0.72, gc=0.46)],
    gear_h=1.10, nose_gear=0.101, main_gear=(0.47,), wheel_d=1.14,
    belly_fairing=0.25,
)
add("B738", B737NG)
add("B737", replace(B737NG, name="Boeing 737-700", L=33.6, doors=(0.11, 0.81), exits=(0.43,), wing_x=0.37))
add("B739", replace(B737NG, name="Boeing 737-900", L=42.1, doors=(0.09, 0.83), exits=(0.40, 0.44, 0.71)))
add("B736", replace(B737NG, name="Boeing 737-600", L=31.2, wingtip="plain", span=34.3, doors=(0.12, 0.81), exits=(0.43,), wing_x=0.36))

B737MAX = replace(
    B737NG, name="Boeing 737 MAX 8", span=35.9, wingtip="at", winglet_h=2.0,
    tail_len=3.3, tail_top=0.78, tail_bot=0.66,
    engines=[Engine("wing", z=0.19, dia=2.25, length=4.2, fwd=0.80, gc=0.43, chevrons=True)],
    gear_h=1.25,
)
add("B38M", B737MAX)
add("B37M", replace(B737MAX, name="Boeing 737 MAX 7", L=35.6, doors=(0.11, 0.81), exits=(0.43,), wing_x=0.37))
add("B39M", replace(B737MAX, name="Boeing 737 MAX 9", L=42.2, doors=(0.09, 0.83), exits=(0.40, 0.44, 0.71)))
add("B3XM", replace(B737MAX, name="Boeing 737 MAX 10", L=43.8, doors=(0.09, 0.84), exits=(0.39, 0.43, 0.71), gear_h=1.4))

# ------------------------------------------------------------ Airbus A320 family
A320 = Spec(
    "Airbus A320", L=37.57, D=4.14, W=3.95, span=34.1,
    nose_top=((0.0, 0.4), (0.25, 0.49), (0.5, 0.53), (0.75, 0.57), (1.0, 0.59), (1.25, 0.62), (1.5, 0.68),
              (1.75, 0.74), (2.0, 0.79), (2.5, 0.86), (3.0, 0.92), (3.5, 0.96), (4.0, 0.98), (4.5, 1.0)),
    nose_bot=((0.0, 0.32), (0.25, 0.23), (0.5, 0.2), (1.0, 0.14), (1.5, 0.11), (2.0, 0.09), (3.0, 0.07),
              (4.0, 0.04), (5.0, 0.0)),
    ck=(1.35, 3.45, 0.59, 0.75, 0.75, 0.59, 0.60), ck_frames=(0.38, 0.72),
    tail_len=3.0, tail_top=0.80, tail_bot=0.63,
    wing_x=0.39, root=7.0, kink=0.34, kink_chord=4.4, tip=1.5, sweep=27, dihedral=5.1,
    wingtip="fence",
    fin_x=0.80, fin_root=6.1, fin_tip=2.0, fin_h=6.0, fin_sweep=34, dorsal=0.18,
    stab_x=0.875, stab_span=12.45, stab_root=3.5, stab_tip=1.2, stab_sweep=30, stab_y=0.62,
    win_y=0.66, win_from=0.16, win_to=0.80, win_pitch=0.53,
    doors=(0.125, 0.82), exits=(0.41, 0.44), door_y=0.39, door_h=0.46,
    engines=[Engine("wing", z=0.25, dia=2.1, length=4.1, fwd=0.62, gc=0.58)],
    gear_h=1.60, nose_gear=0.12, main_gear=(0.47,), wheel_d=1.17,
    belly_fairing=0.3,
)
add("A320", A320)
add("A319", replace(A320, name="Airbus A319", L=33.84, doors=(0.11, 0.80), exits=(0.43,), wing_x=0.375))
add("A318", replace(A320, name="Airbus A318", L=31.44, doors=(0.12, 0.79), exits=(0.44,), wing_x=0.36, fin_h=6.8))
add("A321", replace(A320, name="Airbus A321", L=44.51, doors=(0.08, 0.27, 0.56, 0.84), wing_x=0.40, main_gear=(0.48,)))

A20N = replace(A320, name="Airbus A320neo", span=35.8, wingtip="sharklet", winglet_h=2.4,
               engines=[Engine("wing", z=0.25, dia=2.45, length=4.6, fwd=0.70, gc=0.50)])
add("A20N", A20N)
add("A19N", replace(A20N, name="Airbus A319neo", L=33.84, doors=(0.11, 0.80), exits=(0.43,), wing_x=0.375))
add("A21N", replace(A20N, name="Airbus A321neo", L=44.51, doors=(0.08, 0.27, 0.56, 0.84), wing_x=0.40, main_gear=(0.48,)))

# ------------------------------------------------------------ Embraer E-Jets
E190 = Spec(
    "Embraer E190", L=36.24, D=3.35, W=3.01, span=28.72,
    nose_len=1.75, nose_blen=1.15, nose_tip=0.36, nose_e=1.8,
    tail_len=3.3, tail_top=0.80, tail_bot=0.62,
    wing_x=0.40, root=5.8, kink=0.34, kink_chord=3.6, tip=1.3, sweep=25, dihedral=5,
    wingtip="winglet", winglet_h=1.7,
    fin_x=0.79, fin_root=5.4, fin_tip=2.0, fin_h=5.6, fin_sweep=36, dorsal=0.35,
    stab_x=0.88, stab_span=12.1, stab_root=3.0, stab_tip=1.2, stab_sweep=32, stab_y=0.62,
    win_y=0.60, win_from=0.13, win_to=0.80, win_pitch=0.50, win_w=0.26, win_h=0.38,
    doors=(0.105, 0.83), exits=(0.43,),
    engines=[Engine("wing", z=0.27, dia=1.75, length=3.6, fwd=0.68, gc=0.55)],
    gear_h=1.25, nose_gear=0.085, main_gear=(0.50,), wheel_d=1.05,
    belly_fairing=0.22,
)
add("E190", E190)
add("E195", replace(E190, name="Embraer E195", L=38.65, doors=(0.10, 0.84), exits=(0.44,)))
add("E170", replace(E190, name="Embraer E170", L=29.90, span=26.0, doors=(0.12, 0.82), exits=(0.42,), wing_x=0.38,
                    engines=[Engine("wing", z=0.27, dia=1.55, length=3.2, fwd=0.68, gc=0.55)]))
add("E75L", replace(SPECS["E170"], name="Embraer E175", L=31.68, doors=(0.115, 0.82), exits=(0.43,)))
add("E75S", replace(SPECS["E75L"], name="Embraer E175 (short wing)", span=26.0))

E290 = replace(E190, name="Embraer E190-E2", span=33.72, root=6.0, kink_chord=3.7, tip=1.15, wingtip="raked",
               engines=[Engine("wing", z=0.27, dia=2.25, length=4.0, fwd=0.68, gc=0.55)], gear_h=1.45)
add("E290", E290)
add("E295", replace(E290, name="Embraer E195-E2", L=41.5, span=35.12, doors=(0.095, 0.85), exits=(0.44,), fin_h=6.0))

add("B733", replace(B737NG, name="Boeing 737-300", L=33.4, span=28.9, root=6.6, kink_chord=3.9, tip=1.6, sweep=26,
                    wingtip="plain", dorsal=0.25, fin_h=6.3, stab_span=12.7, nose_tip=0.34,
                    doors=(0.11, 0.81), exits=(0.43,), wing_x=0.37,
                    engines=[Engine("wing", z=0.19, dia=2.0, length=3.3, fwd=0.75, gc=0.46)], gear_h=1.1))
add("B734", replace(SPECS["B733"], name="Boeing 737-400", L=36.4, doors=(0.10, 0.82), exits=(0.42, 0.45), wing_x=0.38))
add("B735", replace(SPECS["B733"], name="Boeing 737-500", L=31.0, doors=(0.115, 0.80), exits=(0.43,), wing_x=0.36))
add("P8", replace(B737NG, name="Boeing P-8 Poseidon", L=39.5, span=37.6, wingtip="raked", windows=False, doors=(0.095,), exits=()))

# ------------------------------------------------------------ Airbus A220
BCS3 = Spec(
    "Airbus A220-300", L=38.7, D=3.7, W=3.51, span=35.1,
    nose_len=1.75, nose_blen=1.1, nose_tip=0.37, nose_e=1.85,
    tail_len=3.2, tail_top=0.80, tail_bot=0.63,
    wing_x=0.405, root=6.6, kink=0.33, kink_chord=4.0, tip=1.3, sweep=27, dihedral=5, wingtip="raked",
    fin_x=0.80, fin_root=6.3, fin_tip=2.2, fin_h=6.4, fin_sweep=38, dorsal=0.3,
    stab_x=0.875, stab_span=12.2, stab_root=3.3, stab_tip=1.2, stab_sweep=31,
    win_y=0.60, win_from=0.13, win_to=0.81, win_pitch=0.52, win_w=0.30, win_h=0.42,
    doors=(0.10, 0.83), exits=(0.43, 0.46),
    engines=[Engine("wing", z=0.27, dia=2.3, length=4.3, fwd=0.70, gc=0.52)],
    gear_h=1.3, nose_gear=0.08, main_gear=(0.50,), wheel_d=1.15, belly_fairing=0.25,
)
add("BCS3", BCS3)
add("BCS1", replace(BCS3, name="Airbus A220-100", L=35.0, doors=(0.11, 0.82), exits=(0.44,), wing_x=0.39))

# ------------------------------------------------------------ Boeing 757
B752 = Spec(
    "Boeing 757-200", L=47.3, D=4.0, W=3.76, span=38.05,
    nose_top=((0.0, 0.28), (0.25, 0.37), (0.5, 0.42), (1.0, 0.51), (1.25, 0.55), (1.5, 0.61), (1.75, 0.68),
              (2.0, 0.73), (2.5, 0.8), (3.0, 0.86), (3.5, 0.9), (4.0, 0.93), (4.5, 0.96), (5.25, 0.99), (6.0, 1.0)),
    nose_bot=((0.0, 0.21), (0.25, 0.14), (0.5, 0.1), (1.0, 0.06), (1.5, 0.04), (2.0, 0.03), (2.75, 0.0)),
    ck=(1.25, 3.05, 0.58, 0.67, 0.68, 0.53, 0.54), ck_frames=(0.3, 0.62),
    tail_len=3.2, tail_top=0.80, tail_bot=0.62,
    wing_x=0.38, root=8.2, kink=0.3, kink_chord=4.8, tip=1.6, sweep=27, dihedral=6, wingtip="plain",
    fin_x=0.82, fin_root=7.2, fin_tip=2.2, fin_h=7.4, fin_sweep=39, dorsal=0.25,
    stab_x=0.88, stab_span=15.2, stab_root=4.0, stab_tip=1.3, stab_sweep=31,
    win_y=0.64, win_from=0.13, win_to=0.84, win_pitch=0.51,
    doors=(0.103, 0.22, 0.60, 0.86), exits=(0.43, 0.46), door_y=0.39, door_h=0.47,
    engines=[Engine("wing", z=0.26, dia=2.6, length=5.0, fwd=0.62, gc=0.66)],
    gear_h=2.2, nose_gear=0.128, main_gear=(0.49,), axles=(2,), wheel_d=1.17, belly_fairing=0.3,
)
add("B752", B752)
add("B753", replace(B752, name="Boeing 757-300", L=54.5, doors=(0.089, 0.20, 0.51, 0.67, 0.87), nose_gear=0.111))

# ------------------------------------------------------------ Boeing 767
B763 = Spec(
    "Boeing 767-300", L=54.9, D=5.41, W=5.03, span=47.6,
    nose_top=((0.0, 0.49), (0.25, 0.53), (0.5, 0.57), (1.0, 0.62), (1.25, 0.67), (1.5, 0.7), (2.0, 0.78),
              (2.5, 0.83), (3.0, 0.88), (3.5, 0.9), (4.0, 0.93), (4.5, 0.95), (5.0, 0.97), (5.75, 0.99), (6.5, 1.0)),
    nose_bot=((0.0, 0.4), (0.25, 0.34), (0.5, 0.31), (1.0, 0.26), (1.5, 0.22), (2.0, 0.17), (2.5, 0.14),
              (3.0, 0.11), (3.5, 0.08), (4.0, 0.05), (4.75, 0.0)),
    ck=(1.0, 3.05, 0.62, 0.80, 0.80, 0.62, 0.63), ck_frames=(0.45,),
    tail_len=3.0, tail_top=0.80, tail_bot=0.63,
    wing_x=0.38, root=10.5, kink=0.3, kink_chord=6.5, tip=2.3, sweep=33, dihedral=6, wingtip="plain",
    fin_x=0.82, fin_root=8.4, fin_tip=2.8, fin_h=8.3, fin_sweep=41, dorsal=0.2,
    stab_x=0.885, stab_span=18.6, stab_root=5.0, stab_tip=1.7, stab_sweep=33,
    win_y=0.62, win_from=0.15, win_to=0.85, win_pitch=0.53,
    doors=(0.097, 0.21, 0.86), exits=(0.50,), door_w=1.07, door_y=0.44, door_h=0.34,
    engines=[Engine("wing", z=0.26, dia=2.95, length=5.4, fwd=0.62, gc=0.85)],
    gear_h=1.95, nose_gear=0.082, main_gear=(0.50,), axles=(2,), wheel_d=1.17, belly_fairing=0.35, track=9.3,
)
add("B763", B763)
add("B762", replace(B763, name="Boeing 767-200", L=48.5, doors=(0.11, 0.86), exits=(0.49,), nose_gear=0.093))
add("B764", replace(B763, name="Boeing 767-400ER", L=61.4, span=51.9, wingtip="raked", doors=(0.087, 0.19, 0.57, 0.87), exits=(),
                    gear_h=2.0, nose_gear=0.073))

# ------------------------------------------------------------ Boeing 777
B77W = Spec(
    "Boeing 777-300ER", L=73.9, D=6.2, W=6.19, span=64.8,
    nose_top=((0.0, 0.43), (0.25, 0.48), (0.5, 0.51), (1.0, 0.56), (1.5, 0.64), (2.0, 0.69), (2.5, 0.73),
              (3.0, 0.77), (3.5, 0.81), (4.0, 0.83), (4.5, 0.85), (5.0, 0.87), (5.5, 0.89), (6.0, 0.91),
              (6.5, 0.93), (7.0, 0.94), (7.5, 0.95), (8.0, 0.96), (8.75, 0.98), (10.0, 1.0)),
    nose_bot=((0.0, 0.35), (0.25, 0.3), (0.5, 0.27), (1.0, 0.23), (1.5, 0.19), (2.0, 0.17), (2.5, 0.14),
              (3.0, 0.12), (3.5, 0.09), (4.0, 0.07), (4.5, 0.04), (5.25, 0.0)),
    ck=(1.2, 2.9, 0.55, 0.66, 0.65, 0.55, 0.55), ck_frames=(0.45,),
    tail_len=2.9, tail_top=0.82, tail_bot=0.70, tail_be=1.2,
    wing_x=0.37, root=13.6, kink=0.3, kink_chord=8.4, tip=2.2, sweep=33, dihedral=6, wingtip="raked",
    fin_x=0.835, fin_root=11.0, fin_tip=3.6, fin_h=9.5, fin_sweep=42, dorsal=0.12,
    stab_x=0.89, stab_span=21.5, stab_root=6.6, stab_tip=2.2, stab_sweep=35,
    win_y=0.59, win_from=0.10, win_to=0.87, win_pitch=0.53, win_w=0.27, win_h=0.40,
    doors=(0.081, 0.225, 0.48, 0.66, 0.84), door_w=1.07, door_y=0.40, door_h=0.36,
    engines=[Engine("wing", z=0.22, dia=4.0, length=7.3, fwd=0.60, gc=0.9)],
    gear_h=2.3, nose_gear=0.08, main_gear=(0.49,), axles=(3,), wheel_d=1.33, belly_fairing=0.45, track=11.0,
)
add("B77W", B77W)
add("B773", replace(B77W, name="Boeing 777-300", span=60.9, wingtip="plain", engines=[Engine("wing", z=0.22, dia=3.7, length=6.8, fwd=0.6, gc=0.95)]))
add("B77L", replace(B77W, name="Boeing 777-200LR / 777F", L=63.7, doors=(0.094, 0.32, 0.62, 0.85), nose_gear=0.093,
                    win_from=0.115))
add("B772", replace(SPECS["B77L"], name="Boeing 777-200", span=60.9, wingtip="plain",
                    engines=[Engine("wing", z=0.22, dia=3.6, length=6.7, fwd=0.6, gc=0.95)]))
add("B779", replace(B77W, name="Boeing 777-9", L=76.7, span=71.8, wingtip="raked", root=14.2, tip=2.0, nose_gear=0.077,
                    engines=[Engine("wing", z=0.22, dia=4.4, length=7.6, fwd=0.62, gc=0.8)], doors=(0.078, 0.26, 0.47, 0.66, 0.85)))

# ------------------------------------------------------------ Boeing 787
B789 = Spec(
    "Boeing 787-9 Dreamliner", L=62.8, D=5.9, W=5.77, span=60.1,
    nose_top=((0.0, 0.31), (0.25, 0.38), (0.5, 0.42), (1.0, 0.51), (1.5, 0.58), (2.0, 0.65), (2.5, 0.71),
              (3.0, 0.77), (3.5, 0.82), (4.0, 0.86), (4.5, 0.89), (5.0, 0.91), (5.5, 0.94), (6.0, 0.96),
              (6.5, 0.97), (7.25, 0.99), (8.5, 1.0)),
    nose_bot=((0.0, 0.26), (0.25, 0.2), (0.5, 0.18), (1.0, 0.14), (1.5, 0.11), (2.0, 0.09), (3.0, 0.06),
              (4.0, 0.04), (5.0, 0.02), (6.0, 0.01), (7.25, 0.0)),
    ck=(1.6, 3.2, 0.55, 0.66, 0.66, 0.56, 0.56), ck_frames=(0.45,),
    tail_len=3.0, tail_top=0.80, tail_bot=0.64,
    wing_x=0.38, root=12.0, kink=0.3, kink_chord=7.2, tip=1.6, sweep=34, dihedral=7, wingtip="raked",
    fin_x=0.83, fin_root=10.0, fin_tip=3.3, fin_h=9.0, fin_sweep=41, dorsal=0.15,
    stab_x=0.885, stab_span=19.8, stab_root=6.0, stab_tip=2.0, stab_sweep=35,
    win_y=0.63, win_from=0.11, win_to=0.86, win_pitch=0.62, win_w=0.29, win_h=0.47,
    doors=(0.083, 0.31, 0.60, 0.85), door_w=1.07, door_y=0.40, door_h=0.38,
    engines=[Engine("wing", z=0.22, dia=3.5, length=6.2, fwd=0.62, gc=0.85, chevrons=True)],
    gear_h=1.8, nose_gear=0.083, main_gear=(0.50,), axles=(2,), wheel_d=1.28, belly_fairing=0.4, track=9.8,
)
add("B789", B789)
add("B788", replace(B789, name="Boeing 787-8 Dreamliner", L=56.7, doors=(0.092, 0.33, 0.62, 0.85), nose_gear=0.092,
                    win_from=0.12))
add("B78X", replace(B789, name="Boeing 787-10 Dreamliner", L=68.3, doors=(0.076, 0.28, 0.58, 0.86), nose_gear=0.076,
                    win_from=0.10))

# ------------------------------------------------------------ Boeing 747
def hump(flat_to: float, end: float) -> tuple:
    """747 nose and upper-deck contour (traced): rise, flat 1.16 D crown, fairing back to the barrel."""
    rise = ((0.0, 0.51), (0.5, 0.61), (1.0, 0.67), (1.5, 0.71), (2.0, 0.74), (2.5, 0.78), (3.0, 0.82),
            (3.5, 0.85), (4.0, 0.89), (4.5, 0.93), (5.0, 1.0), (5.5, 1.06), (6.0, 1.1), (6.5, 1.13), (7.0, 1.15),
            (7.5, 1.16))
    fair = ((0.0, 1.16), (0.12, 1.13), (0.25, 1.12), (0.38, 1.09), (0.5, 1.06), (0.62, 1.04), (0.75, 1.02),
            (0.88, 1.01), (1.0, 1.0))
    return rise + tuple((round(flat_to + f * (end - flat_to), 2), y) for f, y in fair)


B744 = Spec(
    "Boeing 747-400", L=70.7, D=6.5, W=6.5, span=64.4,
    nose_top=hump(22.5, 31.0),
    nose_bot=((0.0, 0.48), (0.5, 0.38), (1.0, 0.32), (1.5, 0.28), (2.0, 0.24), (2.5, 0.21), (3.0, 0.17),
              (3.5, 0.15), (4.0, 0.13), (4.5, 0.11), (5.0, 0.09), (5.5, 0.07), (6.0, 0.05), (6.5, 0.04), (7.0, 0.0)),
    ck=(5.0, 6.3, 0.97, 1.05, 1.05, 0.96, 0.97), ck_frames=(0.55,),
    tail_len=3.0, tail_top=0.82, tail_bot=0.66,
    wing_x=0.36, root=15.0, kink=0.3, kink_chord=9.6, tip=3.6, sweep=40, dihedral=7, wingtip="winglet", winglet_h=1.8,
    fin_x=0.80, fin_root=13.0, fin_tip=4.2, fin_h=9.9, fin_sweep=45, dorsal=0.1,
    stab_x=0.875, stab_span=22.2, stab_root=7.0, stab_tip=2.4, stab_sweep=37,
    win_y=0.58, win_from=0.017, win_to=0.84, win_pitch=0.53, win_w=0.27, win_h=0.40,
    upper_deck=0.44, upper_win_to=0.31, upper_h=0.18, upper_win_from=9.8,
    doors=(0.127, 0.26, 0.44, 0.63, 0.82), door_w=1.07, door_y=0.40, door_h=0.34,
    engines=[Engine("wing", z=0.22, dia=2.9, length=5.3, fwd=0.62, gc=1.2),
             Engine("wing", z=0.58, dia=2.9, length=5.3, fwd=0.62, drop=0.15)],
    gear_h=2.2, nose_gear=0.113, main_gear=(0.47, 0.53), axles=(2, 2), wheel_d=1.25, belly_fairing=0.4, track=11.0,
)
add("B744", B744)
add("B743", replace(B744, name="Boeing 747-300", span=59.6, wingtip="plain"))
add("B742", replace(B744, name="Boeing 747-200", span=59.6, wingtip="plain", nose_top=hump(16.5, 24.0), upper_win_to=0.21))
add("B748", replace(B744, name="Boeing 747-8", L=76.3, span=68.4, wingtip="raked", nose_top=hump(25.5, 33.5), upper_win_to=0.33,
                    root=15.6, doors=(0.118, 0.26, 0.44, 0.63, 0.83), nose_gear=0.105,
                    engines=[Engine("wing", z=0.22, dia=3.3, length=5.8, fwd=0.62, gc=1.0, chevrons=True),
                             Engine("wing", z=0.58, dia=3.3, length=5.8, fwd=0.62, drop=0.12, chevrons=True)]))

# ------------------------------------------------------------ Airbus widebodies
A333 = Spec(
    "Airbus A330-300", L=63.7, D=5.64, W=5.64, span=60.3,
    nose_top=((0.0, 0.45), (0.25, 0.49), (0.5, 0.52), (1.0, 0.58), (1.25, 0.59), (1.5, 0.63), (1.75, 0.69),
              (2.0, 0.71), (2.5, 0.77), (3.0, 0.81), (3.5, 0.84), (4.0, 0.87), (4.5, 0.89), (5.0, 0.92),
              (5.5, 0.94), (6.0, 0.95), (6.75, 0.98), (7.5, 0.99), (8.5, 1.0)),
    nose_bot=((0.0, 0.37), (0.25, 0.31), (0.5, 0.28), (1.0, 0.22), (1.5, 0.18), (2.0, 0.14), (2.5, 0.11),
              (3.0, 0.08), (3.5, 0.06), (4.0, 0.04), (4.5, 0.02), (5.25, 0.0)),
    ck=(1.3, 3.45, 0.59, 0.70, 0.70, 0.59, 0.59), ck_frames=(0.38, 0.72),
    tail_len=3.0, tail_top=0.80, tail_bot=0.64,
    wing_x=0.37, root=11.0, kink=0.3, kink_chord=7.0, tip=1.7, sweep=31, dihedral=5.5, wingtip="winglet", winglet_h=2.7,
    fin_x=0.82, fin_root=9.0, fin_tip=3.1, fin_h=8.3, fin_sweep=42, dorsal=0.18,
    stab_x=0.88, stab_span=19.4, stab_root=5.6, stab_tip=2.0, stab_sweep=33,
    win_y=0.64, win_from=0.11, win_to=0.86, win_pitch=0.53,
    doors=(0.079, 0.22, 0.54, 0.85), door_w=1.07, door_y=0.39, door_h=0.42,
    engines=[Engine("wing", z=0.26, dia=3.0, length=5.4, fwd=0.62, gc=0.95)],
    gear_h=2.4, nose_gear=0.106, main_gear=(0.50,), axles=(2,), wheel_d=1.27, belly_fairing=0.4, track=10.7,
)
add("A333", A333)
add("A332", replace(A333, name="Airbus A330-200", L=58.8, fin_h=8.8, doors=(0.086, 0.24, 0.56, 0.85), wing_x=0.36,
                    nose_gear=0.115))
add("A339", replace(A333, name="Airbus A330-900", span=64.0, wingtip="sharklet", winglet_h=3.6,
                    engines=[Engine("wing", z=0.26, dia=3.65, length=5.9, fwd=0.66, gc=0.75)]))
add("A338", replace(SPECS["A332"], name="Airbus A330-800", span=64.0, wingtip="sharklet", winglet_h=3.6,
                    engines=[Engine("wing", z=0.26, dia=3.65, length=5.9, fwd=0.66, gc=0.75)]))
add("MRTT", replace(SPECS["A332"], name="Airbus A330 MRTT", doors=(0.085, 0.85), windows=True))
A343 = replace(A333, name="Airbus A340-300", span=60.3,
               engines=[Engine("wing", z=0.23, dia=2.2, length=4.2, fwd=0.65, gc=1.25),
                        Engine("wing", z=0.56, dia=2.2, length=4.2, fwd=0.65, drop=0.2)],
               main_gear=(0.48, 0.53), axles=(2, 1))
add("A343", A343)
add("A342", replace(A343, name="Airbus A340-200", L=59.4, doors=(0.085, 0.24, 0.56, 0.85), nose_gear=0.114))
add("A346", replace(A343, name="Airbus A340-600", L=75.4, span=63.45, fin_h=9.0, doors=(0.067, 0.20, 0.45, 0.65, 0.86),
                    nose_gear=0.09,
                    engines=[Engine("wing", z=0.23, dia=2.9, length=5.3, fwd=0.62, gc=1.0),
                             Engine("wing", z=0.56, dia=2.9, length=5.3, fwd=0.62, drop=0.15)], axles=(2, 2)))
add("A345", replace(SPECS["A346"], name="Airbus A340-500", L=67.9, doors=(0.074, 0.22, 0.50, 0.85), nose_gear=0.1))

A359 = Spec(
    "Airbus A350-900", L=66.8, D=6.1, W=5.96, span=64.75,
    nose_len=1.8, nose_blen=1.1, nose_tip=0.40, nose_e=1.9,
    tail_len=3.0, tail_top=0.80, tail_bot=0.64,
    wing_x=0.37, root=13.0, kink=0.3, kink_chord=8.0, tip=1.9, sweep=33, dihedral=6, wingtip="canted", winglet_h=2.4,
    fin_x=0.83, fin_root=10.0, fin_tip=3.4, fin_h=9.0, fin_sweep=42, dorsal=0.15,
    stab_x=0.885, stab_span=18.9, stab_root=6.0, stab_tip=2.0, stab_sweep=35,
    win_y=0.60, win_from=0.09, win_to=0.86, win_pitch=0.56, win_w=0.28, win_h=0.44,
    doors=(0.085, 0.30, 0.60, 0.86),
    engines=[Engine("wing", z=0.24, dia=3.65, length=6.6, fwd=0.62, gc=0.85)],
    gear_h=2.2, nose_gear=0.075, main_gear=(0.50,), axles=(2,), wheel_d=1.37, belly_fairing=0.45, track=10.6,
)
add("A359", A359)
add("A35K", replace(A359, name="Airbus A350-1000", L=73.8, doors=(0.075, 0.29, 0.58, 0.86), axles=(3,),
                    engines=[Engine("wing", z=0.24, dia=3.75, length=6.8, fwd=0.62, gc=0.85)]))

A388 = Spec(
    "Airbus A380-800", L=72.7, D=8.4, W=7.14, span=79.75,
    nose_top=((0.0, 0.34), (0.25, 0.39), (0.5, 0.42), (1.0, 0.48), (1.5, 0.52), (2.0, 0.58), (2.5, 0.64),
              (3.0, 0.69), (3.5, 0.73), (4.0, 0.78), (4.5, 0.81), (5.0, 0.84), (5.5, 0.86), (6.0, 0.88), (7.0, 0.92),
              (8.0, 0.94), (9.0, 0.96), (10.0, 0.98), (11.0, 0.99), (12.5, 1.0)),
    nose_bot=((0.0, 0.26), (0.25, 0.2), (0.5, 0.18), (1.0, 0.14), (1.5, 0.12), (2.0, 0.1), (2.5, 0.08),
              (3.0, 0.07), (3.75, 0.04), (5.0, 0.0)),
    ck=(1.8, 3.65, 0.51, 0.64, 0.64, 0.51, 0.52), ck_frames=(0.4, 0.75),
    tail_len=2.6, tail_top=0.78, tail_bot=0.62,
    wing_x=0.35, root=17.5, kink=0.3, kink_chord=11.0, tip=4.0, sweep=35, dihedral=5.5, wingtip="fence", winglet_h=1.3,
    fin_x=0.81, fin_root=12.5, fin_tip=4.5, fin_h=10.0, fin_sweep=42, dorsal=0.1,
    stab_x=0.875, stab_span=30.4, stab_root=8.0, stab_tip=3.0, stab_sweep=35, stab_y=0.55,
    win_y=0.44, win_from=0.107, win_to=0.85, win_pitch=0.53, win_w=0.30, win_h=0.44, double_deck=True,
    doors=(0.08, 0.215, 0.44, 0.63, 0.83), door_y=0.29, door_h=0.28, door_w=1.07,
    engines=[Engine("wing", z=0.23, dia=3.5, length=6.4, fwd=0.62, gc=1.35),
             Engine("wing", z=0.55, dia=3.5, length=6.4, fwd=0.62, drop=0.15)],
    gear_h=2.2, nose_gear=0.072, main_gear=(0.47, 0.53), axles=(2, 3), wheel_d=1.4, belly_fairing=0.5, track=12.5,
)
add("A388", A388)

A306 = Spec(
    "Airbus A300-600", L=54.1, D=5.64, W=5.64, span=44.84,
    nose_top=((0.0, 0.42), (0.25, 0.49), (0.5, 0.51), (1.0, 0.56), (1.5, 0.62), (1.75, 0.67), (2.0, 0.71),
              (2.5, 0.76), (3.0, 0.8), (3.5, 0.83), (4.0, 0.86), (4.5, 0.89), (5.0, 0.91), (5.5, 0.93), (6.0, 0.95),
              (6.5, 0.96), (7.0, 0.97), (7.5, 0.99), (8.5, 1.0)),
    nose_bot=((0.0, 0.39), (0.25, 0.31), (0.5, 0.27), (1.0, 0.21), (1.5, 0.17), (2.0, 0.14), (2.5, 0.11),
              (3.0, 0.09), (3.5, 0.06), (4.0, 0.04), (4.5, 0.02), (5.25, 0.0)),
    ck=(1.4, 3.55, 0.57, 0.69, 0.69, 0.57, 0.58), ck_frames=(0.38, 0.72),
    tail_len=2.9, tail_top=0.80, tail_bot=0.64,
    wing_x=0.37, root=10.0, kink=0.3, kink_chord=6.0, tip=2.0, sweep=30, dihedral=5.5, wingtip="fence", winglet_h=1.0,
    fin_x=0.82, fin_root=8.6, fin_tip=3.0, fin_h=8.0, fin_sweep=42, dorsal=0.15,
    stab_x=0.88, stab_span=16.3, stab_root=5.0, stab_tip=1.8, stab_sweep=33,
    win_y=0.63, win_from=0.125, win_to=0.85, win_pitch=0.53,
    doors=(0.088, 0.22, 0.86), exits=(0.52,), door_w=1.07, door_y=0.39, door_h=0.41,
    engines=[Engine("wing", z=0.27, dia=2.95, length=5.4, fwd=0.62, gc=0.9)],
    gear_h=2.4, nose_gear=0.112, main_gear=(0.50,), axles=(2,), wheel_d=1.24, belly_fairing=0.4, track=9.6,
)
add("A306", A306)
add("A30B", replace(A306, name="Airbus A300B4", wingtip="plain"))
add("A310", replace(A306, name="Airbus A310", L=46.66, span=43.9, doors=(0.102, 0.86), exits=(0.52,), nose_gear=0.13,
                    win_from=0.145))

# ------------------------------------------------------------ tail-engined jets
def tailjet(name, L, D, span, eng_dia, eng_len, eng_x, *, W=0.0, root=None, tip=None, sweep=15, dihedral=3,
            wingtip="plain", winglet_h=0.0, ttail=True, stab_on_fin=0.0, fin_h=None, fin_root=None, fin_tip=None,
            fin_sweep=40, stab_span=None, wing_x=0.43, gear_h=None, wheel_d=None, cockpit="bizjet", windows_oval=False,
            win_pitch=None, doors=(0.09,), exits=(), eng_y=0.62, nose_len=2.1, nose_tip=0.33, win_to=0.65, win_from=0.2,
            tail_len=3.0, **kw) -> Spec:
    root = root or span * 0.16
    tip = tip or root * 0.42
    fin_h = fin_h or D * 1.55
    fin_root = fin_root or fin_h * 1.15
    fin_tip = fin_tip or fin_root * 0.55
    stab_span = stab_span or span * 0.36
    gear_h = gear_h if gear_h is not None else D * 0.30
    wheel_d = wheel_d or max(0.45, D * 0.30)
    ww, wh = (0.42, 0.34) if windows_oval else (0.28, 0.36)
    ww, wh = kw.pop("win_w", ww), kw.pop("win_h", wh)
    return Spec(
        name, L=L, D=D, W=W or D * 0.95, span=span, nose_len=nose_len, nose_blen=1.2, nose_tip=nose_tip, nose_e=1.7,
        tail_len=tail_len, tail_top=0.78, tail_bot=0.62,
        wing_x=wing_x, root=root, tip=tip, sweep=sweep, dihedral=dihedral, wingtip=wingtip, winglet_h=winglet_h,
        fin_x=0.80 if ttail else 0.82, fin_root=fin_root, fin_tip=fin_tip, fin_h=fin_h, fin_sweep=fin_sweep, dorsal=0.2,
        ttail=ttail, stab_on_fin=stab_on_fin, stab_x=0.86, stab_span=stab_span, stab_root=fin_root * 0.5,
        stab_tip=fin_root * 0.22, stab_sweep=fin_sweep * 0.8, stab_y=0.62,
        win_y=0.58, win_from=win_from, win_to=win_to, win_pitch=win_pitch or (0.75 if windows_oval else 0.55),
        win_w=ww, win_h=wh, win_round=0.5, doors=doors, exits=exits, door_h=0.62, door_y=0.15, door_w=0.75,
        cockpit=cockpit,
        engines=[Engine("tail", x=eng_x, y=eng_y, dia=eng_dia, length=eng_len)],
        gear_h=gear_h, nose_gear=0.10, main_gear=(wing_x + 0.13,), wheel_d=wheel_d, **kw)

# Bombardier CRJ & Embraer ERJ
add("CRJ9", tailjet("Bombardier CRJ-900", 36.2, 2.69, 24.9, 1.45, 3.4, 0.70, root=4.6, tip=1.2, sweep=27, dihedral=4,
                    wingtip="winglet", winglet_h=1.2, fin_h=4.4, fin_root=4.4, fin_tip=3.0, fin_sweep=45, stab_span=8.5,
                    wing_x=0.43, gear_h=0.95, wheel_d=0.9, cockpit="airliner", doors=(0.09, 0.66), exits=(0.42, 0.45),
                    win_from=0.12, win_to=0.66, win_pitch=0.51, win_w=0.22, nose_len=1.9))
add("CRJX", replace(SPECS["CRJ9"], name="Bombardier CRJ-1000", L=39.1, span=26.2))
add("CRJ7", replace(SPECS["CRJ9"], name="Bombardier CRJ-700", L=32.5, span=23.2, doors=(0.10, 0.65), exits=(0.44,)))
add("CRJ2", replace(SPECS["CRJ9"], name="Bombardier CRJ-200", L=26.8, span=21.2, root=3.9, sweep=25,
                    engines=[Engine("tail", x=0.68, y=0.62, dia=1.3, length=3.2)], doors=(0.11, 0.66), exits=(0.45,)))
add("CRJ1", replace(SPECS["CRJ2"], name="Bombardier CRJ-100"))
add("E145", tailjet("Embraer ERJ-145", 29.87, 2.28, 20.04, 1.3, 3.0, 0.70, root=3.9, tip=1.0, sweep=22, wingtip="winglet",
                    winglet_h=0.8, fin_h=3.6, fin_root=3.8, fin_tip=2.6, fin_sweep=45, stab_span=7.55, gear_h=0.85,
                    wheel_d=0.75, cockpit="airliner", doors=(0.08,), exits=(0.45,), win_from=0.11, win_to=0.66,
                    win_pitch=0.48, win_w=0.22, nose_len=2.4, nose_tip=0.30))
add("E135", replace(SPECS["E145"], name="Embraer ERJ-135", L=26.33))
add("E35L", replace(SPECS["E145"], name="Embraer Legacy 600", L=26.33, wingtip="winglet", winglet_h=1.0, win_w=0.38, win_h=0.32,
                    win_pitch=0.85, win_from=0.16))
add("E45X", replace(SPECS["E145"], name="Embraer ERJ-145XR"))
add("F100", tailjet("Fokker 100", 35.5, 3.3, 28.1, 1.6, 4.4, 0.69, root=5.3, tip=1.4, sweep=19, fin_h=4.8, fin_root=5.2,
                    fin_tip=3.2, fin_sweep=42, stab_span=10.0, gear_h=1.0, wheel_d=1.0, cockpit="airliner",
                    doors=(0.08, 0.68), exits=(0.42,), win_from=0.11, win_to=0.66, win_pitch=0.51, win_w=0.24, nose_len=1.8))
add("F70", replace(SPECS["F100"], name="Fokker 70", L=30.9))

# Business jets
add("C56X", tailjet("Cessna Citation XLS", 15.79, 1.9, 17.17, 0.95, 2.6, 0.62, ttail=False, stab_on_fin=0.35, sweep=4,
                    root=2.4, tip=1.1, fin_h=2.9, fin_root=3.0, fin_tip=1.4, stab_span=6.5, wing_x=0.43, gear_h=0.45, win_from=0.25,
                    win_to=0.6, windows_oval=False, win_pitch=0.85, win_w=0.45, win_h=0.40))
add("C560", replace(SPECS["C56X"], name="Cessna Citation V", L=14.9, span=15.9))
add("C550", replace(SPECS["C56X"], name="Cessna Citation II", L=14.4, span=15.9, stab_on_fin=0.0))
add("C55B", replace(SPECS["C550"], name="Cessna Citation Bravo"))
add("C25A", tailjet("Cessna Citation CJ2", 14.53, 1.75, 15.1, 0.85, 2.3, 0.62, ttail=False, sweep=0, root=2.3, tip=1.0,
                    fin_h=2.6, fin_root=2.6, fin_tip=1.2, stab_span=6.3, wing_x=0.44, gear_h=0.42, win_from=0.26, win_to=0.6,
                    win_pitch=0.85, win_w=0.42, win_h=0.38, dihedral=4))
add("C25B", replace(SPECS["C25A"], name="Cessna Citation CJ3", L=15.59, span=16.26))
add("C25C", replace(SPECS["C25A"], name="Cessna Citation CJ4", L=16.26, span=15.49, sweep=12))
add("C525", replace(SPECS["C25A"], name="Cessna CitationJet", L=12.98, span=14.26))
add("C25M", replace(SPECS["C525"], name="Cessna Citation M2", span=14.4))
add("C510", replace(SPECS["C25A"], name="Cessna Citation Mustang", L=12.37, span=13.16, D=1.6, gear_h=0.4))
add("C68A", tailjet("Cessna Citation Latitude", 18.97, 2.1, 22.05, 1.1, 2.9, 0.64, sweep=14, root=3.0, tip=1.2, fin_h=3.4,
                    fin_root=3.4, fin_tip=1.9, stab_span=8.4, wing_x=0.44, gear_h=0.5, win_from=0.22, win_to=0.62,
                    win_pitch=0.9, win_w=0.42, win_h=0.45, wingtip="winglet", winglet_h=0.5))
add("C700", replace(SPECS["C68A"], name="Cessna Citation Longitude", L=22.3, span=20.6, sweep=27, wingtip="winglet", winglet_h=0.9))
add("C680", tailjet("Cessna Citation Sovereign", 19.35, 1.95, 22.04, 1.05, 2.9, 0.64, ttail=False, stab_on_fin=0.4, sweep=16,
                    root=3.1, tip=1.2, fin_h=3.3, fin_root=3.4, fin_tip=1.6, stab_span=8.2, wing_x=0.44, gear_h=0.48,
                    win_from=0.22, win_to=0.62, win_pitch=0.85, win_w=0.42, win_h=0.40))
add("C650", tailjet("Cessna Citation III", 16.9, 1.9, 16.3, 1.0, 2.8, 0.63, sweep=25, root=3.0, tip=1.1, fin_h=3.2,
                    fin_root=3.2, fin_tip=1.8, stab_span=6.6, gear_h=0.48, win_from=0.22, win_to=0.62, win_pitch=0.85,
                    win_w=0.42, win_h=0.40))
add("C750", replace(SPECS["C650"], name="Cessna Citation X", L=22.0, span=19.4, sweep=37))
add("E55P", tailjet("Embraer Phenom 300", 15.64, 1.8, 16.2, 0.9, 2.5, 0.63, sweep=11, root=2.6, tip=1.0, fin_h=2.9,
                    fin_root=3.0, fin_tip=1.7, fin_sweep=42, stab_span=6.2, wingtip="winglet", winglet_h=0.8, gear_h=0.48,
                    win_from=0.24, win_to=0.6, win_pitch=0.82, win_w=0.44, win_h=0.38))
add("E50P", replace(SPECS["E55P"], name="Embraer Phenom 100", L=12.82, span=12.3, wingtip="plain", D=1.65))
add("E550", tailjet("Embraer Praetor 600", 20.74, 2.1, 21.5, 1.15, 3.0, 0.65, sweep=20, root=3.2, tip=1.1, fin_h=3.4,
                    fin_root=3.5, fin_tip=2.0, fin_sweep=44, stab_span=7.9, wingtip="winglet", winglet_h=1.0, gear_h=0.5,
                    win_from=0.22, win_to=0.63, win_pitch=0.85, win_w=0.44, win_h=0.40))
add("E545", replace(SPECS["E550"], name="Embraer Praetor 500", L=19.68))
add("CL35", tailjet("Bombardier Challenger 350", 20.9, 2.1, 21.0, 1.2, 3.2, 0.64, sweep=27, root=3.3, tip=1.1, fin_h=3.5,
                    fin_root=3.6, fin_tip=2.1, fin_sweep=44, stab_span=7.8, wingtip="canted", winglet_h=1.1, gear_h=0.5,
                    win_from=0.22, win_to=0.64, win_pitch=0.9, win_w=0.42, win_h=0.42))
add("CL30", replace(SPECS["CL35"], name="Bombardier Challenger 300", span=19.46, wingtip="winglet", winglet_h=0.9))
add("CL60", tailjet("Bombardier Challenger 600/650", 20.85, 2.5, 19.61, 1.45, 3.4, 0.65, sweep=25, root=3.6, tip=1.2, fin_h=3.6,
                    fin_root=3.8, fin_tip=2.4, fin_sweep=45, stab_span=6.2, wingtip="winglet", winglet_h=1.0, gear_h=0.55,
                    win_from=0.22, win_to=0.63, win_pitch=0.9, win_w=0.42, win_h=0.45))
add("GLEX", tailjet("Bombardier Global 6000/6500", 30.3, 2.6, 28.65, 1.5, 4.0, 0.68, sweep=31, root=5.0, tip=1.3, fin_h=4.4,
                    fin_root=4.6, fin_tip=2.6, fin_sweep=45, stab_span=9.8, wingtip="winglet", winglet_h=1.3, gear_h=0.65,
                    win_from=0.2, win_to=0.66, win_pitch=0.95, win_w=0.42, win_h=0.48, nose_len=2.0))
add("GL5T", replace(SPECS["GLEX"], name="Bombardier Global 5000/5500", L=29.5))
add("GL7T", replace(SPECS["GLEX"], name="Bombardier Global 7500", L=33.8, span=31.7, wingtip="canted", winglet_h=1.5,
                    engines=[Engine("tail", x=0.69, y=0.62, dia=1.6, length=4.1)]))
add("GLF6", tailjet("Gulfstream G650", 30.4, 2.6, 30.4, 1.55, 4.2, 0.68, sweep=33, root=5.3, tip=1.3, fin_h=4.8,
                    fin_root=4.8, fin_tip=2.6, fin_sweep=45, stab_span=10.4, wingtip="winglet", winglet_h=1.4, gear_h=0.7,
                    windows_oval=True, win_from=0.17, win_to=0.65, win_pitch=1.05, nose_len=2.0))
add("GA7C", replace(SPECS["GLF6"], name="Gulfstream G700", L=33.5, span=31.4))
add("GA8C", replace(SPECS["GLF6"], name="Gulfstream G800", L=31.4, span=31.4))
add("GA6C", replace(SPECS["GLF6"], name="Gulfstream G600", L=29.4, span=28.9))
add("GA5C", replace(SPECS["GLF6"], name="Gulfstream G500", L=27.2, span=26.3))
add("GLF5", replace(SPECS["GLF6"], name="Gulfstream G550 / GV", L=29.4, span=28.5, sweep=28))
add("GLF4", replace(SPECS["GLF6"], name="Gulfstream IV / G450", L=26.9, span=23.7, sweep=27, winglet_h=1.1))
add("G280", tailjet("Gulfstream G280", 20.3, 2.1, 19.2, 1.2, 3.1, 0.64, sweep=29, root=3.3, tip=1.0, fin_h=3.6, fin_root=3.7,
                    fin_tip=2.0, fin_sweep=45, stab_span=7.8, wingtip="winglet", winglet_h=0.9, gear_h=0.5,
                    windows_oval=True, win_from=0.22, win_to=0.63, win_pitch=0.95))
add("GALX", replace(SPECS["G280"], name="Gulfstream G200", L=18.97, span=17.7, ttail=False, stab_on_fin=0.0, wingtip="winglet"))
add("ASTR", replace(SPECS["C650"], name="Gulfstream G100", L=16.9, span=16.6, ttail=False, stab_on_fin=0.0))
add("F2TH", tailjet("Dassault Falcon 2000", 20.2, 2.3, 19.3, 1.2, 3.1, 0.65, ttail=False, stab_on_fin=0.25, sweep=27, root=3.6,
                    tip=1.2, fin_h=3.8, fin_root=4.0, fin_tip=1.8, fin_sweep=48, stab_span=7.6, gear_h=0.5,
                    win_from=0.22, win_to=0.62, win_pitch=0.85, win_w=0.38, win_h=0.38, wingtip="winglet", winglet_h=1.2))
add("FA6X", replace(SPECS["F2TH"], name="Dassault Falcon 6X", L=25.7, span=25.9, D=2.5, wingtip="plain"))
FA7X = replace(SPECS["F2TH"], name="Dassault Falcon 7X", L=23.2, span=26.2, sweep=30, wingtip="winglet", winglet_h=1.1,
               engines=[Engine("tail", x=0.66, y=0.62, dia=1.05, length=3.0), Engine("center", x=0.72, dia=1.0, length=3.0)])
add("FA7X", FA7X)
add("FA8X", replace(FA7X, name="Dassault Falcon 8X", L=24.5, span=26.3))
add("F900", replace(FA7X, name="Dassault Falcon 900", L=20.2, span=19.3, sweep=27))
add("FA50", replace(FA7X, name="Dassault Falcon 50", L=18.5, span=18.9, sweep=27, wingtip="plain"))
add("LJ45", tailjet("Learjet 45", 17.7, 1.8, 14.6, 1.0, 2.6, 0.64, sweep=13, root=2.6, tip=1.0, fin_h=3.0, fin_root=3.1,
                    fin_tip=2.0, fin_sweep=48, stab_span=5.8, wingtip="winglet", winglet_h=0.7, gear_h=0.45,
                    win_from=0.24, win_to=0.6, win_pitch=0.8, win_w=0.40, win_h=0.36))
add("LJ40", replace(SPECS["LJ45"], name="Learjet 40", L=16.9))
add("LJ60", replace(SPECS["LJ45"], name="Learjet 60", L=17.9, span=13.3))
add("LJ35", replace(SPECS["LJ45"], name="Learjet 35", L=14.8, span=12.0, D=1.6, wingtip="tank", root=2.3,
                    engines=[Engine("tail", x=0.64, y=0.62, dia=0.85, length=2.5)]))
add("H25B", tailjet("Hawker 800", 15.6, 1.9, 15.66, 0.95, 2.6, 0.63, ttail=False, stab_on_fin=0.7, sweep=20, root=2.9,
                    tip=1.1, fin_h=3.1, fin_root=3.1, fin_tip=1.5, stab_span=6.1, gear_h=0.45, win_from=0.24, win_to=0.6,
                    win_pitch=0.8, win_w=0.42, win_h=0.42, wingtip="winglet", winglet_h=0.6))
add("H25C", replace(SPECS["H25B"], name="Hawker 1000", wingtip="plain"))
add("HA4T", replace(SPECS["C680"], name="Hawker 4000", L=21.1, span=18.8, sweep=28, stab_on_fin=0.0))
add("PRM1", replace(SPECS["E50P"], name="Beechcraft Premier I", L=14.0, span=13.6, sweep=20, wingtip="plain"))
add("BE40", replace(SPECS["LJ45"], name="Beechjet 400", L=14.75, span=13.25, wingtip="plain", sweep=20))
add("PC24", replace(SPECS["E55P"], name="Pilatus PC-24", L=16.85, span=17.0, wingtip="plain", sweep=8,
                    engines=[Engine("tail", x=0.63, y=0.74, dia=0.95, length=2.6)]))
add("HDJT", replace(SPECS["C25A"], name="HondaJet", L=12.99, span=12.12, wingtip="plain",
                    engines=[Engine("tail", x=0.50, y=1.05, dia=0.85, length=2.4)]))
add("EA50", replace(SPECS["C510"], name="Eclipse 550", L=10.1, span=11.4, D=1.4, wingtip="tank",
                    engines=[Engine("tail", x=0.60, y=0.65, dia=0.6, length=1.8)]))

# ------------------------------------------------------------ turboprops
def tprop(name, L, D, span, *, n=2, wing_pos="low", ttail=False, prop_d=2.5, blades=4, eng_z=0.3, nac_d=0.9,
          nac_len=3.0, root=None, tip=None, sweep=2, dihedral=5, fin_h=None, fin_root=None, fin_sweep=35,
          stab_span=None, wing_x=0.38, gear_h=None, wheel_d=None, doors=(0.75,), win_from=0.22, win_to=0.7,
          win_pitch=0.65, win_w=0.3, win_h=0.38, cockpit="bizjet", nose_len=1.8, nose_tip=0.33, **kw) -> Spec:
    root = root or span * 0.13
    tip = tip or root * 0.55
    fin_h = fin_h or D * 1.5
    fin_root = fin_root or fin_h * 1.1
    stab_span = stab_span or span * 0.38
    gear_h = gear_h if gear_h is not None else D * 0.35
    wheel_d = wheel_d or max(0.5, D * 0.3)
    if n == 1:
        engines = [Engine("nose", kind="prop", dia=D * 0.8, length=2.0, prop_d=prop_d, blades=blades)]
    else:
        engines = [Engine("wing", z=eng_z, kind="prop", dia=nac_d, length=nac_len, prop_d=prop_d, blades=blades,
                          over=(wing_pos == "high"))]
        if n == 4:
            engines.append(Engine("wing", z=eng_z + 0.32, kind="prop", dia=nac_d, length=nac_len, prop_d=prop_d,
                                  blades=blades, over=(wing_pos == "high")))
    return Spec(
        name, kind="prop", L=L, D=D, span=span, nose_len=nose_len, nose_blen=1.1, nose_tip=nose_tip, nose_e=1.8,
        tail_len=3.0, tail_top=0.82, tail_bot=0.62, wing_x=wing_x, wing_pos=wing_pos, root=root, tip=tip, sweep=sweep,
        dihedral=dihedral, fin_x=0.80, fin_root=fin_root, fin_tip=fin_root * 0.5, fin_h=fin_h, fin_sweep=fin_sweep,
        dorsal=0.35, ttail=ttail, stab_x=0.87, stab_span=stab_span, stab_root=fin_root * 0.45, stab_tip=fin_root * 0.25,
        stab_sweep=12, stab_y=0.62, win_y=0.58, win_from=win_from, win_to=win_to, win_pitch=win_pitch, win_w=win_w,
        win_h=win_h, doors=doors, door_h=0.6, door_y=0.15, door_w=0.75, cockpit=cockpit, engines=engines,
        gear_h=gear_h, nose_gear=0.10, main_gear=(wing_x + 0.1,), wheel_d=wheel_d, **kw)

AT76 = tprop("ATR 72-600", 27.17, 2.6, 27.05, wing_pos="high", ttail=True, prop_d=3.93, blades=6, eng_z=0.27, nac_d=1.1,
             nac_len=4.6, root=2.6, tip=1.4, sweep=3, dihedral=2.5, fin_h=4.6, fin_root=4.6, fin_sweep=36, stab_span=7.3,
             wing_x=0.41, gear_h=0.75, wheel_d=0.84, doors=(0.08, 0.83), win_from=0.12, win_to=0.78, win_pitch=0.53,
             win_w=0.24, win_h=0.36, cockpit="airliner", nose_len=1.7, belly_fairing=0.55)
add("AT76", AT76)
add("AT75", replace(AT76, name="ATR 72-500", engines=[replace(AT76.engines[0], blades=4)]))
add("AT72", replace(AT76, name="ATR 72", engines=[replace(AT76.engines[0], blades=4)]))
add("AT46", replace(AT76, name="ATR 42-600", L=22.67, span=24.57, doors=(0.09, 0.80), win_to=0.74))
add("AT45", replace(SPECS["AT46"], name="ATR 42-500", engines=[replace(AT76.engines[0], blades=6, prop_d=3.93)]))
add("AT43", replace(SPECS["AT46"], name="ATR 42-300", engines=[replace(AT76.engines[0], blades=4, prop_d=3.96)]))
DH8D = tprop("De Havilland Canada Dash 8-400", 32.8, 2.7, 28.4, wing_pos="high", ttail=True, prop_d=4.1, blades=6,
             eng_z=0.26, nac_d=1.25, nac_len=6.0, root=3.0, tip=1.4, sweep=3, dihedral=2.5, fin_h=5.3, fin_root=4.8,
             fin_sweep=36, stab_span=8.8, wing_x=0.43, gear_h=1.2, wheel_d=0.95, doors=(0.08, 0.84), win_from=0.12,
             win_to=0.80, win_pitch=0.53, win_w=0.24, win_h=0.38, cockpit="airliner", nose_len=1.9)
add("DH8D", DH8D)
add("DH8C", replace(DH8D, name="De Havilland Canada Dash 8-300", L=25.68, span=27.43,
                    engines=[replace(DH8D.engines[0], blades=4, prop_d=3.96, length=5.0)]))
add("DH8A", replace(SPECS["DH8C"], name="De Havilland Canada Dash 8-100", L=22.25, span=25.9))
add("DH8B", replace(SPECS["DH8A"], name="De Havilland Canada Dash 8-200"))
add("D328", tprop("Dornier 328", 21.28, 2.2, 20.98, wing_pos="high", ttail=True, prop_d=3.6, blades=6, eng_z=0.27,
                  nac_d=1.0, nac_len=4.2, root=2.3, tip=1.3, dihedral=2, wing_x=0.40, gear_h=0.7, doors=(0.1, 0.82),
                  win_from=0.14, win_to=0.75, win_pitch=0.6, cockpit="airliner", belly_fairing=0.4))
add("J328", replace(SPECS["D328"], name="Dornier 328JET", kind="jet",
                    engines=[Engine("wing", z=0.27, dia=1.2, length=3.2, fwd=0.7, drop=0.3)]))
add("SW4", tprop("Swearingen Metro", 18.09, 1.8, 17.37, prop_d=2.69, blades=4, eng_z=0.25, nac_d=0.8, nac_len=3.2,
                 fin_h=2.9, stab_span=4.9, wing_x=0.45, gear_h=0.55, doors=(0.08, 0.72), win_from=0.18, win_to=0.65,
                 win_pitch=0.65, nose_len=3.0, nose_tip=0.30))
add("B190", tprop("Beechcraft 1900", 17.63, 1.9, 17.67, ttail=True, prop_d=2.78, blades=4, eng_z=0.22, nac_d=0.8,
                  nac_len=3.0, fin_h=3.0, stab_span=5.6, wing_x=0.42, gear_h=0.6, doors=(0.09, 0.80), win_from=0.2,
                  win_to=0.72, win_pitch=0.68, nose_len=2.0))
add("BE20", tprop("Beechcraft King Air 200", 13.36, 1.7, 16.61, ttail=True, prop_d=2.5, blades=4, eng_z=0.22, nac_d=0.75,
                  nac_len=2.8, fin_h=2.6, stab_span=5.6, wing_x=0.38, gear_h=0.55, doors=(0.68,), win_from=0.30,
                  win_to=0.62, win_pitch=0.72, nose_len=2.0, nose_tip=0.30))
add("B350", replace(SPECS["BE20"], name="Beechcraft King Air 350", L=14.22, span=17.65, wingtip="winglet", winglet_h=0.6))
add("BE30", replace(SPECS["BE20"], name="Beechcraft King Air 300"))
add("BE9L", tprop("Beechcraft King Air 90", 10.82, 1.65, 15.32, prop_d=2.4, blades=4, eng_z=0.22, nac_d=0.72, nac_len=2.6,
                  fin_h=2.5, stab_span=5.2, wing_x=0.36, gear_h=0.55, doors=(0.66,), win_from=0.32, win_to=0.6,
                  win_pitch=0.7, nose_len=1.9, nose_tip=0.30))
add("C425", replace(SPECS["BE9L"], name="Cessna 425 Corsair", L=10.93, span=13.45))
add("C441", replace(SPECS["BE9L"], name="Cessna 441 Conquest II", L=11.89, span=15.04))
add("P180", tprop("Piaggio P.180 Avanti", 14.41, 1.9, 14.03, wing_pos="mid", ttail=True, prop_d=2.16, blades=5, eng_z=0.25,
                  nac_d=0.7, nac_len=3.5, fin_h=3.0, stab_span=4.3, wing_x=0.55, gear_h=0.45, doors=(0.12,),
                  win_from=0.22, win_to=0.55, win_pitch=0.7, nose_len=2.4))
add("PC12", tprop("Pilatus PC-12", 14.4, 1.75, 16.28, n=1, ttail=True, prop_d=2.67, blades=4, root=2.4, tip=1.2,
                  fin_h=2.9, stab_span=5.2, wing_x=0.38, gear_h=0.55, doors=(0.72,), win_from=0.34, win_to=0.65,
                  win_pitch=0.7, wingtip="winglet", winglet_h=0.6, nose_len=2.2, nose_tip=0.45))
add("TBM9", tprop("Daher TBM 900", 10.74, 1.5, 12.83, n=1, prop_d=2.31, blades=5, root=2.2, tip=1.1, fin_h=2.2,
                  stab_span=4.4, wing_x=0.37, gear_h=0.55, doors=(0.62,), win_from=0.4, win_to=0.62, win_pitch=0.6,
                  wingtip="winglet", winglet_h=0.35, nose_len=2.6, nose_tip=0.45))
add("TBM7", replace(SPECS["TBM9"], name="Socata TBM 700", engines=[replace(SPECS["TBM9"].engines[0], blades=4)], wingtip="plain"))
add("TBM8", replace(SPECS["TBM7"], name="Socata TBM 850"))
add("M600", tprop("Piper M600", 9.0, 1.4, 13.1, n=1, prop_d=2.08, blades=4, fin_h=2.0, stab_span=4.4, wing_x=0.38,
                  gear_h=0.5, doors=(0.6,), win_from=0.4, win_to=0.62, win_pitch=0.55, nose_len=2.6, nose_tip=0.45))
add("M700", replace(SPECS["M600"], name="Piper M700 Fury"))
add("P46T", replace(SPECS["M600"], name="Piper Malibu Meridian"))
add("C208", tprop("Cessna 208 Caravan", 11.46, 1.7, 15.88, n=1, wing_pos="high", prop_d=2.69, blades=3, fin_h=2.6,
                  stab_span=6.2, wing_x=0.33, gear_h=0.7, doors=(0.6,), win_from=0.35, win_to=0.65, win_pitch=0.65,
                  strut=True, nose_len=2.4, nose_tip=0.45, cockpit="ga", cockpit_x=0.24))
add("C30J", tprop("Lockheed Martin C-130J Hercules", 29.8, 4.3, 40.4, n=4, wing_pos="high", prop_d=4.11, blades=6,
                  eng_z=0.22, nac_d=1.2, nac_len=5.2, root=4.9, tip=2.7, dihedral=2, fin_h=7.5, fin_root=6.6,
                  stab_span=16.0, wing_x=0.40, gear_h=0.45, wheel_d=1.1, doors=(0.12,), windows=False,
                  cockpit="airliner", nose_len=1.4, nose_tip=0.42, belly_fairing=0.9))
add("C130", replace(SPECS["C30J"], name="Lockheed C-130 Hercules",
                    engines=[replace(e, blades=4, prop_d=4.11) for e in SPECS["C30J"].engines]))
add("A400", tprop("Airbus A400M Atlas", 45.1, 5.6, 42.4, n=4, wing_pos="high", ttail=True, prop_d=5.33, blades=8,
                  eng_z=0.2, nac_d=1.5, nac_len=6.0, root=6.5, tip=2.6, sweep=15, dihedral=-1, fin_h=9.0, fin_root=8.0,
                  stab_span=19.6, wing_x=0.40, gear_h=0.6, wheel_d=1.3, doors=(0.12,), windows=False,
                  cockpit="airliner", nose_len=1.3, nose_tip=0.42, belly_fairing=1.0, axles=(3,)))

# ------------------------------------------------------------ light aircraft
def ga(name, L, span, *, wing_pos="low", ttail=False, twin=False, prop_d=1.9, blades=2, D=1.35, W=1.15, root=1.5,
       tip=None, fin_h=1.35, fin_root=1.4, stab_span=3.4, wing_x=0.32, gear_h=0.35, wheel_d=0.42, strut=False,
       dihedral=6, cockpit_x=0.30, sweep=1, wingtip="plain", winglet_h=0.0, retract=False, **kw) -> Spec:
    tip = tip or root * 0.8
    if twin:
        engines = [Engine("wing", z=0.32, kind="prop", dia=0.55, length=1.9, prop_d=prop_d, blades=blades)]
    else:
        engines = [Engine("nose", kind="prop", dia=D * 0.7, length=1.5, prop_d=prop_d, blades=blades)]
    return Spec(
        name, kind="prop", L=L, D=D, W=W, span=span, nose_len=1.6 if not twin else 1.9, nose_blen=1.1,
        nose_tip=0.48, nose_e=2.4, nose_be=1.8, tail_len=0.55 * L / D, tail_top=0.60, tail_bot=0.36, tail_te=1.15, tail_be=0.9,
        wing_x=wing_x, wing_pos=wing_pos, root=root, tip=tip, sweep=sweep, dihedral=dihedral, wingtip=wingtip,
        winglet_h=winglet_h, strut=strut, fin_x=0.80, fin_root=fin_root, fin_tip=fin_root * 0.55, fin_h=fin_h,
        fin_sweep=35, dorsal=0.3, ttail=ttail, stab_x=0.84, stab_span=stab_span, stab_root=fin_root * 0.65,
        stab_tip=fin_root * 0.5, stab_sweep=4, stab_y=0.45, windows=False, cockpit="ga", cockpit_x=cockpit_x,
        engines=engines, gear_h=gear_h, nose_gear=0.10, main_gear=(wing_x + 0.10,), wheel_d=wheel_d, **kw)

add("C172", ga("Cessna 172 Skyhawk", 8.28, 11.0, wing_pos="high", strut=True, root=1.63, tip=1.13, fin_h=1.45, fin_root=1.6,
               stab_span=3.4, wing_x=0.30, gear_h=0.45, dihedral=1.7, cockpit_x=0.28))
add("C152", replace(SPECS["C172"], name="Cessna 152", L=7.34, span=10.17))
add("C150", replace(SPECS["C152"], name="Cessna 150"))
add("C182", replace(SPECS["C172"], name="Cessna 182 Skylane", L=8.84, engines=[Engine("nose", kind="prop", dia=0.95, length=1.5, prop_d=2.08, blades=3)]))
add("C82R", replace(SPECS["C182"], name="Cessna 182RG"))
add("C206", replace(SPECS["C182"], name="Cessna 206 Stationair", L=8.61))
add("C210", replace(SPECS["C182"], name="Cessna 210 Centurion", strut=False))
add("P28A", ga("Piper PA-28 Cherokee", 7.25, 10.67, root=1.6, tip=1.1, fin_h=1.3, stab_span=3.8, wing_x=0.31, gear_h=0.38))
add("P28B", replace(SPECS["P28A"], name="Piper PA-28-201T Dakota"))
add("P28R", replace(SPECS["P28A"], name="Piper PA-28R Arrow"))
add("P28T", replace(SPECS["P28A"], name="Piper PA-28RT Arrow IV", ttail=True))
add("P32R", replace(SPECS["P28A"], name="Piper PA-32R Saratoga", L=8.44, span=11.02))
add("PA46", replace(SPECS["P28A"], name="Piper PA-46 Malibu", L=8.72, span=13.11))
add("PA44", ga("Piper PA-44 Seminole", 8.41, 11.77, twin=True, ttail=True, root=1.6, fin_h=1.7, stab_span=3.9, wing_x=0.33))
add("PA34", ga("Piper PA-34 Seneca", 8.72, 11.86, twin=True, root=1.6, fin_h=1.6, stab_span=4.1, wing_x=0.33, D=1.4))
add("PA31", ga("Piper PA-31 Navajo", 9.94, 12.4, twin=True, root=1.9, fin_h=1.9, stab_span=5.5, wing_x=0.34, D=1.5))
add("BE58", ga("Beechcraft Baron 58", 9.09, 11.53, twin=True, root=1.9, fin_h=1.8, stab_span=4.9, wing_x=0.33, D=1.4))
add("BE36", ga("Beechcraft Bonanza A36", 8.38, 10.21, root=2.1, fin_h=1.6, stab_span=4.0, wing_x=0.31, blades=3, prop_d=2.03))
add("DA40", ga("Diamond DA40", 8.06, 11.94, ttail=True, root=1.4, tip=0.9, fin_h=1.55, fin_root=1.35, stab_span=3.2,
               wing_x=0.35, gear_h=0.35, blades=3, prop_d=1.88, D=1.25, W=1.15, cockpit_x=0.26))
add("DA50", replace(SPECS["DA40"], name="Diamond DA50", L=9.07, span=13.42, D=1.35))
add("DV20", replace(SPECS["DA40"], name="Diamond DV20 Katana", L=7.17, span=10.87))
add("DA42", ga("Diamond DA42 Twin Star", 8.56, 13.55, twin=True, ttail=True, root=1.4, tip=0.9, fin_h=1.7, fin_root=1.4,
               stab_span=3.6, wing_x=0.36, blades=3, prop_d=1.9, D=1.3, cockpit_x=0.26))
add("DA62", replace(SPECS["DA42"], name="Diamond DA62", L=9.19, span=14.55, D=1.4))
add("SR22", ga("Cirrus SR22", 7.92, 11.68, root=1.6, tip=0.8, fin_h=1.6, stab_span=3.9, wing_x=0.34, blades=3, prop_d=1.98,
               D=1.35, W=1.27, cockpit_x=0.27))
add("S22T", replace(SPECS["SR22"], name="Cirrus SR22T"))
add("SR20", replace(SPECS["SR22"], name="Cirrus SR20"))
add("SF50", replace(SPECS["SR22"], name="Cirrus SF50 Vision Jet", L=9.42, span=11.79, kind="jet",
                    engines=[Engine("tail", x=0.55, y=1.15, dia=0.65, length=2.0)]))
add("SIRA", ga("Tecnam P2002 Sierra", 6.61, 8.6, root=1.2, tip=1.2, fin_h=1.2, fin_root=1.2, stab_span=2.9, wing_x=0.33,
               gear_h=0.35, D=1.15, W=1.1, cockpit_x=0.28))
add("P208", replace(SPECS["SIRA"], name="Tecnam P2008", wing_pos="high", strut=False, L=6.93))
add("TFUN", ga("Valentin Taifun 17E", 7.8, 17.0, ttail=True, root=1.1, tip=0.5, fin_h=1.35, fin_root=1.2, stab_span=2.8,
               wing_x=0.33, gear_h=0.35, D=1.1, W=1.1, cockpit_x=0.27))
add("RV7", ga("Van's RV-7", 6.2, 7.7, root=1.25, tip=1.25, fin_h=1.2, stab_span=3.0, wing_x=0.33, gear_h=0.35, D=1.1, W=1.05,
              cockpit_x=0.34))
add("RV8", replace(SPECS["RV7"], name="Van's RV-8"))
add("RV10", replace(SPECS["RV7"], name="Van's RV-10", L=7.4, span=9.6, D=1.3, W=1.2))
add("PC21", ga("Pilatus PC-21", 11.23, 9.11, root=1.9, tip=1.0, fin_h=2.0, fin_root=1.8, stab_span=4.0, wing_x=0.40,
               gear_h=0.55, blades=5, prop_d=2.39, D=1.4, W=1.0, cockpit_x=0.3))
add("PC7", replace(SPECS["PC21"], name="Pilatus PC-7", L=9.78, span=10.4, engines=[Engine("nose", kind="prop", dia=0.9, length=1.5, prop_d=2.36, blades=3)]))
add("J3", ga("Piper J-3 Cub", 6.83, 10.74, wing_pos="high", strut=True, tailwheel=True, root=1.6, tip=1.6, fin_h=1.2,
             stab_span=3.0, wing_x=0.27, gear_h=0.65, wheel_d=0.55, cockpit_x=0.26))
add("PA18", replace(SPECS["J3"], name="Piper PA-18 Super Cub"))
add("C170", replace(SPECS["J3"], name="Cessna 170", L=7.6, span=10.97))
add("CH7A", replace(SPECS["J3"], name="Champion Citabria", L=6.9, span=10.2, strut=True))

# gliders
add("GLID", Spec("Glider", kind="prop", L=6.7, D=0.95, W=0.65, span=18.0, nose_len=2.4, nose_tip=0.45, nose_e=2.2,
                 tail_len=4.6, tail_top=0.42, tail_bot=0.30, tail_te=0.9, tail_be=0.8, wing_x=0.40, wing_pos="mid",
                 root=1.0, tip=0.38, sweep=0, dihedral=3, wingtip="winglet", winglet_h=0.35, fin_x=0.86, fin_root=1.0,
                 fin_tip=0.6, fin_h=1.2, fin_sweep=20, ttail=True, stab_span=2.8, stab_root=0.6, stab_tip=0.35,
                 stab_sweep=3, windows=False, cockpit="ga", cockpit_x=0.10, engines=[], gear_h=0.08, nose_gear=0.12,
                 main_gear=(0.34,), wheel_d=0.38, tailwheel=True))

# ------------------------------------------------------------ helicopters
def heli(name, L, rotor, cab, *, D=1.6, W=1.5, tail_rotor=1.8, fenestron=False, wheels=False, blades=4, fin_h=1.1,
         gear_h=0.55, **kw) -> Spec:
    return Spec(name, kind="heli", L=L, D=D, W=W, span=rotor, root=cab, stab_span=tail_rotor, fin_h=fin_h,
                wingtip="fenestron" if fenestron else "rotor", tailwheel=wheels, axles=(blades,), gear_h=gear_h, **kw)

add("EC35", heli("Airbus H135", 10.2, 10.2, 4.6, fenestron=True, blades=4, doors=(1,)))
add("EC45", heli("Airbus H145", 11.6, 11.0, 5.2, D=1.7, fenestron=True, blades=4, doors=(1,)))
add("H145", replace(SPECS["EC45"], name="Airbus H145 D3", axles=(5,)))
add("EC30", heli("Airbus H130", 10.7, 10.69, 4.2, D=1.6, W=1.7, fenestron=True, blades=3))
add("EC20", heli("Airbus H120 Colibri", 9.6, 10.0, 3.7, D=1.45, W=1.3, fenestron=True, blades=3))
add("AS50", heli("Airbus AS350 Écureuil", 10.9, 10.69, 4.1, D=1.55, W=1.5, tail_rotor=1.86, blades=3))
add("AS55", replace(SPECS["AS50"], name="Airbus AS355 Écureuil 2"))
add("AS65", heli("Airbus AS365 Dauphin", 12.1, 11.94, 5.5, D=1.8, W=1.9, fenestron=True, wheels=True, blades=4, gear_h=0.6))
add("EC55", replace(SPECS["AS65"], name="Airbus EC155"))
add("H160", heli("Airbus H160", 12.6, 13.4, 5.6, D=1.8, W=2.0, fenestron=True, wheels=True, blades=5, gear_h=0.65))
add("EC75", heli("Airbus H175", 15.6, 14.8, 7.0, D=2.1, W=2.3, tail_rotor=3.2, wheels=True, blades=5, gear_h=0.7))
add("EC25", heli("Airbus H225 Super Puma", 16.8, 16.2, 7.8, D=2.3, W=2.4, tail_rotor=3.2, wheels=True, blades=5, gear_h=0.7, fin_h=1.6))
add("NH90", heli("NHIndustries NH90", 16.1, 16.3, 7.6, D=2.3, W=2.3, tail_rotor=3.2, wheels=True, blades=4, gear_h=0.75, fin_h=1.6))
add("R44", heli("Robinson R44", 9.07, 10.06, 3.0, D=1.4, W=1.3, tail_rotor=1.47, blades=2, gear_h=0.45, fin_h=0.9))
add("R22", replace(SPECS["R44"], name="Robinson R22", L=8.76, span=7.67, root=2.5, D=1.25, W=1.1))
add("R66", replace(SPECS["R44"], name="Robinson R66", L=9.07, span=10.06, root=3.3))
add("B06", heli("Bell 206 JetRanger", 9.5, 10.16, 3.4, D=1.45, W=1.3, tail_rotor=1.65, blades=2))
add("B407", replace(SPECS["B06"], name="Bell 407", axles=(4,), span=10.67, root=3.8))
add("B429", heli("Bell 429", 11.0, 10.98, 4.8, D=1.7, W=1.8, tail_rotor=1.9, blades=4))
add("A109", heli("Leonardo AW109", 11.4, 11.0, 4.9, D=1.6, W=1.6, tail_rotor=2.0, wheels=True, blades=4, gear_h=0.6))
add("A119", replace(SPECS["A109"], name="Leonardo AW119 Koala", tailwheel=False))
add("A169", heli("Leonardo AW169", 12.4, 12.12, 5.6, D=1.75, W=1.9, tail_rotor=2.2, wheels=True, blades=5, gear_h=0.65))
add("A139", heli("Leonardo AW139", 13.77, 13.8, 6.2, D=1.9, W=2.1, tail_rotor=2.7, wheels=True, blades=5, gear_h=0.7, doors=(1,)))
add("A189", heli("Leonardo AW189", 14.6, 14.6, 6.8, D=2.0, W=2.2, tail_rotor=2.9, wheels=True, blades=5, gear_h=0.7, doors=(1,)))
add("S92", heli("Sikorsky S-92", 17.1, 17.17, 8.0, D=2.4, W=2.5, tail_rotor=3.35, wheels=True, blades=4, gear_h=0.75, fin_h=1.6))
add("S76", heli("Sikorsky S-76", 13.2, 13.4, 6.0, D=1.8, W=1.9, tail_rotor=2.4, wheels=True, blades=4, gear_h=0.6))
add("H60", heli("Sikorsky UH-60 Black Hawk", 15.3, 16.36, 7.0, D=2.0, W=2.4, tail_rotor=3.35, wheels=True, blades=4, gear_h=0.6))
add("H64", heli("Boeing AH-64 Apache", 15.0, 14.63, 6.0, D=1.8, W=1.3, tail_rotor=2.79, wheels=True, blades=4, gear_h=0.8))

# ------------------------------------------------------------ balloons
add("BALL", Spec("Hot-air balloon", kind="balloon", L=22.0, D=1.0, span=17.0))
add("BE33", replace(SPECS["BE36"], name="Beechcraft Debonair / Bonanza 33", L=7.75))
add("BE35", replace(SPECS["BE36"], name="Beechcraft Bonanza V35", L=8.05))
add("G2CA", heli("Guimbal Cabri G2", 6.31, 7.2, 2.6, D=1.3, W=1.24, fenestron=True, blades=3, gear_h=0.4, fin_h=0.8))
add("GY80", replace(SPECS["P28A"], name="Gardan Horizon", L=6.64, span=9.7))
add("F8L", replace(SPECS["RV7"], name="Sequoia Falco F8L", L=6.5, span=8.0))


# ------------------------------------------------------------ measured noses (traced from drawings)
def patch(codes, **kw):
    """Apply the same measured nose/cockpit to every variant of a family."""
    for c in codes:
        SPECS[c] = replace(SPECS[c], **kw)


ERJ_NOSE = dict(
    nose_top=((0.0, 0.09), (0.5, 0.25), (1.0, 0.33), (1.5, 0.40), (2.0, 0.49), (2.5, 0.60), (3.0, 0.79),
              (3.5, 0.93), (4.0, 0.97), (5.0, 0.99), (6.0, 1.0)),
    nose_bot=((0.0, 0.09), (0.25, 0.03), (0.6, 0.0)),
    ck=(2.5, 3.8, 0.55, 0.78, 0.80, 0.60, 0.60), ck_frames=(0.5,),
    win_y=0.64, door_y=0.17, door_h=0.76, door_w=0.7, gear_h=1.2, nose_gear=0.075,
)
patch(["E145", "E45X"], **ERJ_NOSE, doors=(0.15,), win_from=0.195)
patch(["E135", "E35L"], **{**ERJ_NOSE, "nose_gear": 0.085}, doors=(0.17,), win_from=0.22)

ATR_NOSE = dict(
    nose_top=((0.0, 0.36), (0.25, 0.45), (0.5, 0.52), (0.75, 0.57), (1.0, 0.62), (1.25, 0.68), (1.5, 0.79),
              (1.75, 0.88), (2.0, 0.91), (2.25, 0.95), (2.5, 0.98), (3.0, 1.0)),
    nose_bot=((0.0, 0.27), (0.25, 0.18), (0.5, 0.12), (0.75, 0.09), (1.0, 0.07), (1.25, 0.04), (1.5, 0.02), (2.0, 0.0)),
    ck=(1.25, 2.85, 0.63, 0.80, 0.80, 0.64, 0.65), ck_frames=(0.5,),
    win_y=0.59, door_y=0.13, door_h=0.70, door_w=1.2, gear_h=0.67,
)
patch(["AT76", "AT75", "AT72"], **ATR_NOSE, doors=(0.135, 0.83), win_from=0.215, nose_gear=0.064)
patch(["AT46", "AT45", "AT43"], **ATR_NOSE, doors=(0.16, 0.80), win_from=0.255, nose_gear=0.077)

A220_NOSE = dict(
    nose_top=((0.0, 0.35), (0.25, 0.42), (0.5, 0.47), (0.75, 0.52), (1.0, 0.58), (1.5, 0.67), (2.0, 0.74),
              (2.5, 0.81), (3.0, 0.88), (3.5, 0.92), (4.0, 0.95), (4.5, 0.98), (5.75, 1.0)),
    nose_bot=((0.0, 0.26), (0.25, 0.19), (0.5, 0.16), (1.0, 0.12), (1.5, 0.09), (2.0, 0.07), (3.0, 0.05),
              (4.0, 0.02), (6.75, 0.0)),
    ck=(1.3, 3.1, 0.58, 0.74, 0.74, 0.58, 0.62), ck_frames=(0.4, 0.75),
    win_y=0.66, door_y=0.36, door_h=0.47, wingtip="canted", winglet_h=1.4,
)
patch(["BCS3"], **A220_NOSE, doors=(0.113, 0.83), win_from=0.17, nose_gear=0.09)
patch(["BCS1"], **A220_NOSE, doors=(0.125, 0.82), win_from=0.19, nose_gear=0.10)

EJET_NOSE = dict(
    nose_top=((0.0, 0.21), (0.5, 0.38), (1.0, 0.52), (1.5, 0.63), (2.0, 0.72), (2.5, 0.78), (3.0, 0.83),
              (3.5, 0.87), (4.0, 0.90), (5.0, 0.93), (6.0, 0.96), (8.0, 1.0)),
    nose_bot=((0.0, 0.21), (0.5, 0.10), (1.0, 0.055), (2.0, 0.02), (3.0, 0.0)),
    ck=(1.55, 3.6, 0.60, 0.76, 0.77, 0.60, 0.60), ck_frames=(0.35, 0.7),
    win_y=0.67, door_y=0.33, door_h=0.56,
)
for code in ("E190", "E195", "E170", "E75L", "E75S", "E290", "E295"):
    L_ = SPECS[code].L
    patch([code], **EJET_NOSE, doors=(round(5.05 / L_, 3),) + tuple(SPECS[code].doors[1:]),
          nose_gear=round(4.7 / L_, 3), win_from=round(6.6 / L_, 3))

A350_NOSE = dict(
    nose_top=((0.0, 0.26), (0.5, 0.33), (1.0, 0.39), (1.5, 0.47), (2.0, 0.55), (2.5, 0.62), (3.0, 0.67),
              (4.0, 0.75), (5.0, 0.82), (6.0, 0.87), (7.0, 0.91), (8.0, 0.94), (9.0, 0.97), (10.5, 1.0)),
    nose_bot=((0.0, 0.26), (0.5, 0.17), (1.0, 0.12), (2.0, 0.07), (3.0, 0.04), (4.0, 0.02), (5.5, 0.0)),
    ck=(2.05, 3.5, 0.48, 0.63, 0.61, 0.48, 0.52), ck_frames=(0.5,),
    win_y=0.53, door_y=0.35, door_h=0.32, door_w=1.07,
)
patch(["A359"], **A350_NOSE, doors=(0.087, 0.30, 0.60, 0.86), nose_gear=0.072, win_from=0.115)
patch(["A35K"], **A350_NOSE, doors=(0.079, 0.29, 0.58, 0.86), nose_gear=0.065, win_from=0.105)

DASH8_NOSE = dict(
    nose_top=((0.0, 0.19), (0.5, 0.35), (1.0, 0.46), (1.5, 0.54), (2.0, 0.65), (2.5, 0.76), (3.0, 0.85),
              (3.5, 0.91), (4.0, 0.95), (5.0, 0.98), (6.0, 1.0)),
    nose_bot=((0.0, 0.19), (0.5, 0.08), (1.0, 0.04), (2.0, 0.01), (3.0, 0.0)),
    ck=(2.1, 4.65, 0.65, 0.815, 0.815, 0.65, 0.65), ck_frames=(0.45,),
    win_y=0.60, door_y=0.18, door_h=0.70, door_w=0.9,
)
for code in ("DH8D", "DH8C", "DH8A", "DH8B"):
    L_ = SPECS[code].L
    patch([code], **DASH8_NOSE, doors=(round(5.95 / L_, 3), SPECS[code].doors[-1]),
          nose_gear=round(2.3 / L_, 3), win_from=round(7.3 / L_, 3))

GULF_NOSE = dict(
    nose_top=((0.0, 0.23), (0.5, 0.39), (1.0, 0.48), (1.5, 0.56), (2.0, 0.62), (2.5, 0.73), (3.0, 0.86),
              (3.5, 0.93), (4.0, 0.96), (5.0, 0.99), (6.0, 1.0)),
    nose_bot=((0.0, 0.23), (0.5, 0.12), (1.0, 0.08), (2.0, 0.025), (3.0, 0.01), (3.5, 0.0)),
    ck=(2.0, 3.9, 0.615, 0.80, 0.80, 0.615, 0.615), ck_frames=(0.5,),
    win_y=0.575, door_y=0.08, door_h=0.80, door_w=0.9, cockpit="bizjet",
)
for code in ("GLF6", "GA7C", "GA8C", "GA6C", "GA5C", "GLF5", "GLF4"):
    L_ = SPECS[code].L
    patch([code], **GULF_NOSE, doors=(round(4.85 / L_, 3),), nose_gear=round(2.65 / L_, 3),
          win_from=round(7.0 / L_, 3), win_w=0.62, win_h=0.48)


# ------------------------------------------------------------ light aircraft glazing (from photos)
def ga_patch(codes, ref_L, top, bot, ws=(), side=(), canopy=()):
    """Measured on the reference type; scaled along the length for the other variants."""
    for c in codes:
        k = SPECS[c].L / ref_L
        sc = lambda pts: tuple((round(x * k, 2), y) for x, y in pts)
        SPECS[c] = replace(
            SPECS[c], nose_top=sc(top), nose_bot=sc(bot),
            ga_ws=(ws[0] * k, ws[1] * k, ws[2]) if ws else (),
            ga_side=tuple((a * k, b_ * k, y0, y1) for a, b_, y0, y1 in side),
            ga_canopy=(canopy[0] * k, canopy[1] * k, canopy[2]) if canopy else ())


ga_patch(["C172", "C152", "C150", "C182", "C82R", "C206", "C210"], 8.28,
         top=((0, 0.45), (0.3, 0.56), (0.8, 0.66), (1.4, 0.71), (1.85, 0.73), (2.2, 0.85), (2.55, 0.96), (2.8, 1.0)),
         bot=((0, 0.45), (0.2, 0.3), (0.5, 0.18), (1.0, 0.08), (1.6, 0.0)),
         ws=(1.85, 2.8, 0.73), side=((2.9, 3.75, 0.58, 0.97), (3.85, 4.5, 0.6, 0.95)))
ga_patch(["J3", "PA18", "C170", "CH7A"], 6.83,
         top=((0, 0.5), (0.3, 0.6), (0.8, 0.68), (1.55, 0.74), (1.9, 0.88), (2.2, 1.0)),
         bot=((0, 0.5), (0.2, 0.32), (0.6, 0.15), (1.2, 0.0)),
         ws=(1.55, 2.2, 0.74), side=((2.25, 3.2, 0.55, 0.97),))
ga_patch(["P28A", "P28B", "P28R", "P28T", "P32R", "PA46", "BE36", "BE33", "BE35", "GY80"], 7.25,
         top=((0, 0.48), (0.4, 0.6), (1.0, 0.68), (1.75, 0.72), (2.0, 0.76), (2.4, 0.93), (2.7, 1.0)),
         bot=((0, 0.48), (0.2, 0.32), (0.6, 0.15), (1.2, 0.04), (1.6, 0.0)),
         ws=(1.95, 2.7, 0.74), side=((2.75, 3.6, 0.58, 0.95), (3.7, 4.15, 0.6, 0.9)))
ga_patch(["SR22", "S22T", "SR20"], 7.92,
         top=((0, 0.45), (0.4, 0.58), (1.0, 0.66), (1.6, 0.70), (1.8, 0.73), (2.3, 0.92), (2.7, 1.0)),
         bot=((0, 0.45), (0.2, 0.3), (0.6, 0.15), (1.2, 0.04), (1.6, 0.0)),
         ws=(1.8, 2.6, 0.72), side=((2.65, 3.7, 0.55, 0.96), (3.8, 4.3, 0.58, 0.88)))
ga_patch(["PA44", "PA34", "PA31", "BE58"], 8.41,
         top=((0, 0.45), (0.5, 0.6), (1.2, 0.68), (2.0, 0.72), (2.5, 0.9), (2.85, 1.0)),
         bot=((0, 0.45), (0.3, 0.25), (0.8, 0.1), (1.5, 0.0)),
         ws=(2.0, 2.8, 0.72), side=((2.85, 3.75, 0.58, 0.95), (3.85, 4.35, 0.6, 0.9)))
ga_patch(["DA40", "DA50", "DV20"], 8.06,
         top=((0, 0.42), (0.4, 0.55), (1.0, 0.64), (1.7, 0.70), (2.1, 0.82), (2.6, 0.96), (3.0, 1.0)),
         bot=((0, 0.42), (0.3, 0.25), (0.8, 0.1), (1.5, 0.0)),
         canopy=(1.75, 4.1, 0.66))
ga_patch(["DA42", "DA62"], 8.56,
         top=((0, 0.42), (0.5, 0.58), (1.2, 0.66), (2.0, 0.71), (2.4, 0.83), (2.9, 0.97), (3.3, 1.0)),
         bot=((0, 0.42), (0.3, 0.25), (0.8, 0.1), (1.5, 0.0)),
         canopy=(2.0, 4.4, 0.67))
ga_patch(["SIRA", "P208", "RV7", "RV8", "RV10", "F8L"], 6.61,
         top=((0, 0.45), (0.4, 0.57), (1.0, 0.65), (1.6, 0.70), (2.0, 0.85), (2.4, 0.97), (2.8, 1.0)),
         bot=((0, 0.45), (0.25, 0.28), (0.7, 0.12), (1.3, 0.0)),
         canopy=(1.65, 3.4, 0.66))
ga_patch(["TFUN"], 7.8,
         top=((0, 0.45), (0.4, 0.56), (1.0, 0.63), (1.8, 0.68), (2.2, 0.85), (2.7, 0.98), (3.0, 1.0)),
         bot=((0, 0.45), (0.3, 0.26), (0.8, 0.1), (1.4, 0.0)),
         canopy=(1.85, 3.5, 0.64))
ga_patch(["GLID"], 6.7,
         top=((0, 0.35), (0.3, 0.5), (0.7, 0.62), (1.2, 0.8), (1.8, 0.95), (2.4, 1.0)),
         bot=((0, 0.35), (0.3, 0.18), (0.8, 0.06), (1.4, 0.0)),
         canopy=(0.45, 2.45, 0.56))
ga_patch(["PC21", "PC7"], 11.23,
         top=((0, 0.5), (0.5, 0.6), (1.5, 0.66), (2.4, 0.72), (2.9, 0.92), (3.4, 1.0)),
         bot=((0, 0.5), (0.4, 0.3), (1.0, 0.12), (1.8, 0.0)),
         canopy=(2.45, 5.4, 0.72))


# ------------------------------------------------------------ business jets (from photos)
def scaled_nose(codes, ref_D, top, bot, ck, door_x, win_x, ngear_x, **kw):
    """A measured bizjet nose, scaled by fuselage height to related types."""
    for c in codes:
        s0 = SPECS[c]
        k = s0.D / ref_D
        sc = lambda pts: tuple((round(x * k, 2), y) for x, y in pts)
        SPECS[c] = replace(
            s0, nose_top=sc(top), nose_bot=sc(bot), ck=(ck[0] * k, ck[1] * k) + tuple(ck[2:]),
            doors=(round(door_x * k / s0.L, 3),) + tuple(s0.doors[1:]),
            win_from=round(win_x * k / s0.L, 3), nose_gear=round(ngear_x * k / s0.L, 3), **kw)


CITATION = dict(
    top=((0, 0.20), (0.5, 0.42), (1.0, 0.49), (1.5, 0.58), (2.0, 0.66), (2.5, 0.81), (3.0, 0.91), (3.5, 0.95),
         (4.0, 0.98), (4.6, 1.0)),
    bot=((0, 0.20), (0.3, 0.08), (1.0, 0.03), (2.0, 0.01), (3.0, 0.0)),
    ck=(2.0, 3.9, 0.60, 0.84, 0.84, 0.61, 0.62), door_x=4.0, win_x=5.0, ngear_x=1.6,
)
scaled_nose(["C56X", "C560", "C550", "C55B", "C25A", "C25B", "C25C", "C525", "C25M", "C510", "C68A", "C700", "C680",
             "C650", "C750", "E55P", "E50P", "E550", "E545", "LJ45", "LJ40", "LJ60", "LJ35", "H25B", "H25C", "HA4T",
             "PRM1", "BE40", "PC24", "HDJT", "EA50", "G280", "GALX", "ASTR", "F2TH", "FA6X", "FA7X", "FA8X", "F900",
             "FA50"], 1.9, **CITATION, ck_frames=(0.5, 0.82), win_y=0.70, door_y=0.12, door_h=0.75)
scaled_nose(["GLEX", "GL5T", "GL7T", "CL35", "CL30", "CL60"], 2.6,
            top=GULF_NOSE["nose_top"], bot=GULF_NOSE["nose_bot"], ck=GULF_NOSE["ck"], door_x=4.85, win_x=6.4,
            ngear_x=2.65, ck_frames=(0.5,), win_y=0.6, door_y=0.08, door_h=0.80)

# single turboprops: measured on the PC-12, scaled along the length
for code in ("PC12", "TBM9", "TBM7", "TBM8", "M600", "M700", "P46T"):
    s0 = SPECS[code]
    k = s0.L / 14.4
    sc = lambda pts: tuple((round(x * k, 2), y) for x, y in pts)
    SPECS[code] = replace(
        s0, nose_top=sc(((0, 0.51), (0.7, 0.65), (1.0, 0.70), (2.0, 0.71), (2.9, 0.73), (3.3, 0.86), (3.75, 0.97), (4.5, 1.0))),
        nose_bot=sc(((0, 0.51), (0.7, 0.26), (1.2, 0.2), (2.0, 0.13), (3.0, 0.05), (3.8, 0.0))),
        ck=(3.05 * k, 4.45 * k, 0.66, 0.93, 0.95, 0.70, 0.72), ck_frames=(0.42,),
        win_y=0.66, win_from=round(5.2 / 14.4, 3), nose_gear=round(2.5 / 14.4, 3))

# CRJ and Fokker: from photos (three-quarter views, so positions are estimated to about 0.2 m)
CRJ_NOSE = dict(
    nose_top=((0, 0.30), (0.5, 0.45), (1.0, 0.54), (1.5, 0.62), (2.0, 0.70), (2.5, 0.80), (3.0, 0.88), (3.5, 0.94),
              (4.0, 0.97), (5.0, 1.0)),
    nose_bot=((0, 0.30), (0.4, 0.15), (1.0, 0.06), (2.0, 0.02), (3.0, 0.0)),
    ck=(1.9, 3.5, 0.62, 0.86, 0.84, 0.64, 0.66), ck_frames=(0.45,), win_y=0.62, door_y=0.15, door_h=0.68,
)
for code in ("CRJ9", "CRJX", "CRJ7", "CRJ2", "CRJ1"):
    L_ = SPECS[code].L
    patch([code], **CRJ_NOSE, doors=(round(4.1 / L_, 3),) + tuple(SPECS[code].doors[1:]),
          nose_gear=round(2.0 / L_, 3), win_from=round(5.4 / L_, 3))
F100_NOSE = dict(
    nose_top=((0, 0.38), (0.5, 0.5), (1.0, 0.58), (1.5, 0.66), (2.0, 0.74), (2.5, 0.81), (3.0, 0.87), (3.5, 0.92),
              (4.0, 0.95), (5.0, 0.99), (6.0, 1.0)),
    nose_bot=((0, 0.38), (0.4, 0.24), (1.0, 0.13), (2.0, 0.05), (3.0, 0.01), (3.6, 0.0)),
    ck=(1.3, 3.0, 0.60, 0.76, 0.76, 0.60, 0.62), ck_frames=(0.45,), win_y=0.62, door_y=0.2, door_h=0.6,
)
for code in ("F100", "F70"):
    L_ = SPECS[code].L
    patch([code], **F100_NOSE, doors=(round(3.6 / L_, 3),) + tuple(SPECS[code].doors[1:]),
          nose_gear=round(2.6 / L_, 3), win_from=round(4.9 / L_, 3))

# helicopter cabins: longer pods, measured against an H145 side drawing (cabin ~55% of the length)
for code, sp in list(SPECS.items()):
    if sp.kind == "heli" and code not in ("R44", "R22", "R66", "G2CA"):
        SPECS[code] = replace(sp, root=round(min(sp.L * 0.55, sp.root * 1.25), 2))
