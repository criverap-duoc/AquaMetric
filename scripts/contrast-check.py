"""WCAG contrast checker for oklch design tokens (AquaMetric)."""
import math, sys, json

def oklch_to_srgb(L, C, h):
    a = C * math.cos(math.radians(h)); b = C * math.sin(math.radians(h))
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_**3, m_**3, s_**3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bl = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return [min(1, max(0, x)) for x in (r, g, bl)]  # linear, clipped

def lum(o):
    r, g, b = oklch_to_srgb(*o)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def ratio(a, b):
    la, lb = lum(a), lum(b)
    if la < lb: la, lb = lb, la
    return (la + 0.05) / (lb + 0.05)

def gamut_ok(o):
    L, C, h = o
    a = C * math.cos(math.radians(h)); b = C * math.sin(math.radians(h))
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_**3, m_**3, s_**3
    rgb = [4.0767416621*l-3.3077115913*m+0.2309699292*s,
           -1.2684380046*l+2.6097574011*m-0.3413193965*s,
           -0.0041960863*l-0.7034186147*m+1.7076147010*s]
    return all(-0.002 <= x <= 1.002 for x in rgb)

P = {
 "aquametric-light": {
  "background": [
   0.985,
   0.004,
   235
  ],
  "foreground": [
   0.21,
   0.03,
   250
  ],
  "card": [
   1,
   0,
   0
  ],
  "primary": [
   0.44,
   0.12,
   250
  ],
  "primary_fg": [
   0.985,
   0.004,
   235
  ],
  "secondary": [
   0.94,
   0.03,
   195
  ],
  "secondary_fg": [
   0.3,
   0.054,
   205
  ],
  "muted": [
   0.96,
   0.006,
   240
  ],
  "muted_fg": [
   0.47,
   0.03,
   245
  ],
  "accent": [
   0.88,
   0.07,
   195
  ],
  "accent_fg": [
   0.28,
   0.052,
   210
  ],
  "destructive": [
   0.5,
   0.19,
   25
  ],
  "destructive_fg": [
   0.985,
   0,
   0
  ],
  "success": [
   0.48,
   0.11,
   160
  ],
  "success_fg": [
   0.985,
   0,
   0
  ],
  "warning": [
   0.82,
   0.15,
   85
  ],
  "warning_fg": [
   0.28,
   0.06,
   70
  ],
  "info": [
   0.5,
   0.15,
   275
  ],
  "info_fg": [
   0.985,
   0,
   0
  ],
  "success_soft": [
   0.95,
   0.05,
   160
  ],
  "success_soft_fg": [
   0.34,
   0.08,
   160
  ],
  "warning_soft": [
   0.96,
   0.05,
   90
  ],
  "warning_soft_fg": [
   0.38,
   0.08,
   70
  ],
  "danger_soft": [
   0.95,
   0.024,
   25
  ],
  "danger_soft_fg": [
   0.42,
   0.16,
   25
  ],
  "info_soft": [
   0.95,
   0.024,
   275
  ],
  "info_soft_fg": [
   0.4,
   0.13,
   275
  ],
  "input": [
   0.62,
   0.025,
   245
  ],
  "ring": [
   0.55,
   0.12,
   250
  ],
  "chart1": [
   0.52,
   0.148,
   250
  ],
  "chart2": [
   0.62,
   0.106,
   195
  ],
  "chart3": [
   0.66,
   0.16,
   55
  ],
  "chart4": [
   0.55,
   0.17,
   305
  ],
  "chart5": [
   0.58,
   0.02,
   245
  ],
  "spc_limit": [
   0.55,
   0.19,
   27
  ],
  "spc_spec": [
   0.62,
   0.146,
   60
  ]
 },
 "aquametric-dark": {
  "background": [
   0.16,
   0.025,
   250
  ],
  "foreground": [
   0.96,
   0.005,
   235
  ],
  "card": [
   0.2,
   0.03,
   250
  ],
  "primary": [
   0.72,
   0.12,
   245
  ],
  "primary_fg": [
   0.16,
   0.03,
   250
  ],
  "secondary": [
   0.27,
   0.04,
   215
  ],
  "secondary_fg": [
   0.92,
   0.03,
   200
  ],
  "muted": [
   0.24,
   0.025,
   250
  ],
  "muted_fg": [
   0.72,
   0.025,
   240
  ],
  "accent": [
   0.78,
   0.11,
   195
  ],
  "accent_fg": [
   0.2,
   0.04,
   210
  ],
  "destructive": [
   0.68,
   0.19,
   25
  ],
  "destructive_fg": [
   0.17,
   0.03,
   25
  ],
  "success": [
   0.74,
   0.15,
   160
  ],
  "success_fg": [
   0.17,
   0.03,
   160
  ],
  "warning": [
   0.84,
   0.14,
   85
  ],
  "warning_fg": [
   0.22,
   0.04,
   80
  ],
  "info": [
   0.74,
   0.12,
   275
  ],
  "info_fg": [
   0.17,
   0.03,
   275
  ],
  "success_soft": [
   0.3,
   0.06,
   160
  ],
  "success_soft_fg": [
   0.88,
   0.1,
   160
  ],
  "warning_soft": [
   0.32,
   0.06,
   90
  ],
  "warning_soft_fg": [
   0.9,
   0.1,
   90
  ],
  "danger_soft": [
   0.3,
   0.07,
   25
  ],
  "danger_soft_fg": [
   0.88,
   0.062,
   25
  ],
  "info_soft": [
   0.3,
   0.07,
   275
  ],
  "info_soft_fg": [
   0.88,
   0.058,
   275
  ],
  "input": [
   0.58,
   0.03,
   250
  ],
  "ring": [
   0.65,
   0.12,
   245
  ],
  "chart1": [
   0.72,
   0.12,
   245
  ],
  "chart2": [
   0.78,
   0.11,
   195
  ],
  "chart3": [
   0.76,
   0.15,
   55
  ],
  "chart4": [
   0.72,
   0.15,
   305
  ],
  "chart5": [
   0.7,
   0.02,
   245
  ],
  "spc_limit": [
   0.7,
   0.19,
   27
  ],
  "spc_spec": [
   0.8,
   0.14,
   65
  ]
 }
}
P = {n: {k: tuple(v) for k, v in t.items()} for n, t in P.items()}

TEXT = [("foreground","background"),("foreground","card"),("primary_fg","primary"),
        ("secondary_fg","secondary"),("muted_fg","background"),("muted_fg","muted"),("muted_fg","card"),
        ("accent_fg","accent"),("destructive_fg","destructive"),("success_fg","success"),
        ("warning_fg","warning"),("info_fg","info"),
        ("success_soft_fg","success_soft"),("warning_soft_fg","warning_soft"),
        ("danger_soft_fg","danger_soft"),("info_soft_fg","info_soft")]
UI = [("input","background"),("input","card"),("ring","background"),("ring","card"),
      ("chart1","card"),("chart2","card"),("chart3","card"),("chart4","card"),("chart5","card"),
      ("primary","background"),("destructive","background"),("success","background"),("info","background")]
UI_EXTRA = [("spc_limit","card"),("spc_spec","card")]

fails = 0
for name, t in P.items():
    print(f"\n== {name} ==")
    for k, v in t.items():
        if not gamut_ok(v): print(f"  [gamut] {k} {v} outside sRGB (will be clipped)")
    for fg, bg in TEXT:
        if fg in t and bg in t:
            r = ratio(t[fg], t[bg]); ok = r >= 4.5
            if not ok: fails += 1
            print(f"  text {fg:16s} on {bg:13s} {r:5.2f} {'OK' if ok else 'FAIL (<4.5)'}")
    for fg, bg in UI + UI_EXTRA:
        if fg in t and bg in t:
            r = ratio(t[fg], t[bg]); ok = r >= 3.0
            if not ok: fails += 1
            print(f"  ui   {fg:16s} on {bg:13s} {r:5.2f} {'OK' if ok else 'FAIL (<3.0)'}")
print(f"\nTOTAL FAILS: {fails}")

sys.exit(1 if fails else 0)
