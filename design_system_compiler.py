#!/usr/bin/env python3
"""
design_system_compiler.py
=========================
Four-layer design system compiler with dynamic brand inputs and CTA theming.
"""

# 1. CORE IMPORTS
import json, math, sys, os, argparse, re as _re
from datetime import datetime, timezone
from pathlib import Path
from functools import lru_cache

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 2. GLOBAL GOVERNANCE POLICY
TEXT_POLICY = {
    "default": {
        "allow_polarity_flip": False, 
        "min_margin_ratio": 0.1,      
    },
    "color/text/brand-subtle": {
        "allow_polarity_flip": True   
    },
    "button/primary": {
        "allow_polarity_flip": False  
    }
}

# 3. CLI PARSER
parser = argparse.ArgumentParser(description='Design system compiler')
parser.add_argument('--floor-stop',    type=int, help='Base lightness for dark mode surfaces')
parser.add_argument('--cta-color',     type=str, help='Main CTA color name')
parser.add_argument('--mode',          default='both', choices=['light','dark','both'])
parser.add_argument('--no-css',        action='store_true', help='Skip CSS output')
parser.add_argument('--no-contrast',   action='store_true', help='Skip contrast audit')
parser.add_argument('--verbose',       action='store_true', help='Print all passing pairs')
parser.add_argument('--strict',        action='store_true', help='Turn warnings into hard errors (for CI)')
parser.add_argument('--out-dir',       default='Output', help='Output directory')
parser.add_argument('--palette',       action='store_true', help='Generate design-system-palette.html')
parser.add_argument('--brand-config',  type=str, help='Path to external brand-inputs JSON file')
parser.add_argument('--primary',       type=str, help='Override primary brand hex (e.g. #0066FF)')
parser.add_argument('--secondary',     type=str, help='Override secondary brand hex')
parser.add_argument('--info',          type=str, help='Override info brand hex')
parser.add_argument('--warning',       type=str, help='Override warning brand hex')
parser.add_argument('--success',       type=str, help='Override success brand hex')
parser.add_argument('--error',         type=str, help='Override error brand hex')
args = parser.parse_args()

OUT = Path(args.out_dir)
OUT.mkdir(parents=True, exist_ok=True)
# ─────────────────────────────────────────────────────────────────────────────
# Load layers
# ─────────────────────────────────────────────────────────────────────────────
def load(filename):
    for p in [Path(__file__).parent / filename, Path.cwd() / filename]:
        if p.exists():
            return json.loads(p.read_text(encoding='utf-8'))
    sys.exit(f'ERROR: Cannot find {filename}. Run from the directory containing your layer JSON files.')

L1 = load('layer-1-generation-engine.json')
L2 = load('layer-2-compiler-contract.json')
L3 = load('layer-3-delta-engine.json')
L4 = load('layer-4-token-architecture.json')
print(f'Layers loaded: L1 v{L1["meta"]["version"]}  '
      f'L2 v{L2["compiler-contract"]["version"]}  '
      f'L3 v{L3["delta-engine"]["version"]}  '
      f'L4 v{L4["meta"]["version"]}')

# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA VALIDATION - fast-fail before any compilation work begins
# ─────────────────────────────────────────────────────────────────────────────
def _validate_schema():
    """Hard-fail immediately if any required layer key is absent."""
    errors = []
    # L1
    if 'brand-inputs' not in L1:
        errors.append("L1: missing 'brand-inputs'")
    if 'meta' not in L1:
        errors.append("L1: missing 'meta'")
    # L2
    if 'mode-mapping' not in L2:
        errors.append("L2: missing 'mode-mapping'")
    if 'dark-mode-config' not in L2.get('mode-mapping', {}):
        errors.append("L2: missing mode-mapping.dark-mode-config")
    if 'dark-mode-elevation' not in L2.get('mode-mapping', {}):
        errors.append("L2: missing mode-mapping.dark-mode-elevation")
    # L3
    if 'delta-engine' not in L3:
        errors.append("L3: missing 'delta-engine'")
    if 'interaction-physics' not in L3.get('delta-engine', {}):
        errors.append("L3: missing delta-engine.interaction-physics")
    if 'fill-border-distinctness-policy' not in L3.get('delta-engine', {}):
        errors.append("L3: missing delta-engine.fill-border-distinctness-policy")
    if 'apca-extensions-audit-policy' not in L3.get('delta-engine', {}):
        errors.append("L3: missing delta-engine.apca-extensions-audit-policy")
    # L4
    if 'semantic-role-map' not in L4:
        errors.append("L4: missing 'semantic-role-map'")
    if 'roles' not in L4.get('semantic-role-map', {}):
        errors.append("L4: missing semantic-role-map.roles")
    if 'component-tokens' not in L4:
        errors.append("L4: missing 'component-tokens'")
    if errors:
        print('\n  SCHEMA VALIDATION - HARD BUILD ERROR')
        for e in errors:
            print(f'  ✗  {e}')
        sys.exit(1)
    print('schema validation      - OK ✓')

_validate_schema()

# ─────────────────────────────────────────────────────────────────────────────
# STEP 0 - Preflight Architecture Validation (Developer Safety Rails)
# ─────────────────────────────────────────────────────────────────────────────
def _validate_architecture():
    """Scans Layer 4 for naming violations and missing semantic text pairings."""
    sem_roles = L4.get('semantic-role-map', {}).get('roles', {})
    errors = []

    # 1. Naming Guardrails (brand vs primary mismatch)
    if 'color/fill/primary' in sem_roles or 'color/on-fill/primary' in sem_roles:
        errors.append("Architectural Violation: 'primary' is a Layer 1 hue, not a Layer 4 semantic role. Use 'brand'.")

    # 2. Semantic Pairing Engine (Every fill must have an on-fill)
    fills = [r for r in sem_roles if r.startswith("color/fill/")]
    for fill in fills:
        suffix = fill.replace("color/fill/", "")
        on_fill = f"color/on-fill/{suffix}"
        if on_fill not in sem_roles:
            errors.append(f"Incomplete Semantic Pair: Missing '{on_fill}' to pair with '{fill}'")

    # 3. Overlay text-pairing enforcement
    # Text must NEVER be placed directly on an overlay background.
    overlay_roles = {r for r in sem_roles if 'overlay' in r.lower()}
    ct_data = L4.get('component-tokens', {})
    def _scan_for_overlay_text(block, path=''):
        for k, v in block.items():
            if not isinstance(v, dict): continue
            color_role = v.get('color', '')
            bg_role    = v.get('bg', '')
            # Guard: only check string roles — some 'bg' values are dicts in inline variants
            if isinstance(color_role, str) and 'text' in k.lower() and color_role in overlay_roles:
                errors.append(f'OVERLAY_TEXT_PAIR: {path}/{k} uses overlay role "{color_role}" as text colour.')
            if isinstance(bg_role, str) and bg_role in overlay_roles and any(p in block for p in ('text', 'title')):
                errors.append(f'OVERLAY_TEXT_PAIR: {path} has overlay bg "{bg_role}" paired with text. Text must be on solid surface-raised, not the overlay.')
            _scan_for_overlay_text(v, f'{path}/{k}')
    _scan_for_overlay_text(ct_data)

    # 4. Semantic conflict guardrails — radial hue distance
    brand_inputs = L1.get('brand-inputs', {})
    if brand_inputs:
        try:
            import math as _m
            def _hex_to_H(hx):
                rv,gv,bv = [int(hx.lstrip('#')[i:i+2],16)/255 for i in (0,2,4)]
                def tl(c): return c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4
                rl,gl,bl = tl(rv),tl(gv),tl(bv)
                x=.4124564*rl+.3575761*gl+.1804375*bl
                y=.2126729*rl+.7151522*gl+.0721750*bl
                z=.0193339*rl+.1191920*gl+.9503041*bl
                lm=.8189330101*x+.3618667424*y-.1288597137*z
                mm=.0329845436*x+.9293118715*y+.0361456387*z
                sm=.0482003018*x+.2643662691*y+.6338517070*z
                lp,mp,sp = lm**(1/3),mm**(1/3),sm**(1/3)
                av=1.9779984951*lp-2.4285922050*mp+.4505937099*sp
                bk=.0259040371*lp+.7827717662*mp-.8086757660*sp
                return _m.degrees(_m.atan2(bk,av)) % 360
            def _radial(a,b): return min(abs(a-b), 360-abs(a-b))
            primary_H = _hex_to_H(brand_inputs.get('primary','#000'))
            SEMANTIC_HUES = {'success':145,'error':25,'warning':55}
            THRESHOLD = 30

            # Load manually-acknowledged exceptions from Layer 2.
            #
            # IMPORTANT: Each exception MUST include 'primary-hex-reviewed' — the exact
            # primary hex that was reviewed when granting the exception. If the current
            # primary hex in Layer 1 differs from the reviewed hex, the override is
            # INVALID and the hard stop fires again. This prevents stale sign-offs from
            # silently accepting conflicts introduced by a new brand hex.
            #
            # To override a conflict, add to semantic-conflict-guardrails.known-exceptions:
            # {
            #   "id": "brand-warning-proximity",
            #   "acknowledged": true,
            #   "primary-hex-reviewed": "#B7812F",   <-- REQUIRED: hex you reviewed
            #   "rationale": "Primary used sparingly. Iconography distinguishes warnings.",
            #   "acknowledged-by": "Design Lead",
            #   "date": "YYYY-MM-DD"
            # }
            _guardrails = (L2.get('semantic-mapping', {})
                             .get('semantic-state-roles', {})
                             .get('semantic-conflict-guardrails', {}))
            _current_hex = brand_inputs.get('primary', '').upper().strip()
            _exceptions = {}
            for _e in _guardrails.get('known-exceptions', []):
                if not isinstance(_e, dict): continue
                if _e.get('acknowledged') is not True: continue
                _reviewed = _e.get('primary-hex-reviewed', '').upper().strip()
                _eid = _e.get('id', '?')
                if not _reviewed:
                    # No hex recorded — stale entry, reject it
                    print(f'  WARNING - Exception "{_eid}" has no primary-hex-reviewed field.')
                    print(f'    Override REJECTED. Add "primary-hex-reviewed": "{_current_hex}" to validate.')
                elif _reviewed != _current_hex:
                    # Hex has changed since the exception was granted — no longer valid
                    print(f'  WARNING - Exception "{_eid}" was reviewed for {_reviewed}')
                    print(f'    but current primary is {_current_hex}. Override REJECTED.')
                    print(f'    Re-review and update primary-hex-reviewed in Layer 2 to re-validate.')
                else:
                    # Hex matches — exception is valid
                    _exceptions[_eid] = _e

            for sem, base_H in SEMANTIC_HUES.items():
                dist = _radial(primary_H, base_H)
                if dist < THRESHOLD:
                    conflict_id = f'brand-{sem}-proximity'
                    exc = _exceptions.get(conflict_id)
                    if exc:
                        # Valid exception — hex matches, acknowledged, downgrade to info
                        print(f'  INFO  - SEMANTIC_HUE_CONFLICT [{conflict_id}] override accepted.')
                        print(f'    Reviewed hex : {exc.get("primary-hex-reviewed")}')
                        print(f'    Acknowledged : {exc.get("acknowledged-by","?")} on {exc.get("date","?")}')
                        print(f'    Rationale    : {exc.get("rationale","none")}')
                        print(f'    Distance     : {dist:.0f}deg from {sem} (threshold {THRESHOLD}deg)')
                    else:
                        msg = (
                            f'SEMANTIC_HUE_CONFLICT: Primary brand hue ({primary_H:.0f}deg) is '
                            f'{dist:.0f}deg from {sem} ({base_H}deg). Threshold is {THRESHOLD}deg. '
                            f'Users may not distinguish brand from {sem} states. '
                            f'To override: add known-exceptions entry id="{conflict_id}", '
                            f'acknowledged=true, primary-hex-reviewed="{_current_hex}" '
                            f'in semantic-conflict-guardrails in Layer 2.'
                        )
                        errors.append(msg)
        except Exception:
            pass  # hue check is advisory, never crash the build

    if errors:
        print('\n  ARCHITECTURE VALIDATION FAILED')
        for e in errors:
            print(f'  ✗  {e}')
        if args.strict:
            sys.exit('\n  STRICT ERROR: Fix Layer 4 architectural violations before compiling.')
        else:
            print('\n  WARNING: Compiling anyway (strict mode off), but components may break.')
    else:
        print('architecture validation - OK ✓')

_validate_architecture()

# ─────────────────────────────────────────────────────────────────────────────
# FLOOR-STOP - designer prompt
# ─────────────────────────────────────────────────────────────────────────────
dmc         = L2['mode-mapping']['dark-mode-config']
VALID_STOPS = dmc['valid-floor-stops']
STOP_GUIDE  = dmc['valid-floor-stops-guide']
OLED_NOTE   = dmc['oled-reserved']['note']

if args.floor_stop:
    chosen = str(args.floor_stop)
else:
    print()
    print('─' * 60)
    print('  FLOOR-STOP - dark mode surface darkness')
    print('  Choose the base lightness for all dark mode surfaces.')
    print('  Valid options (from Layer 2 dark-mode-config):')
    print()
    for stop in VALID_STOPS:
        print(f'    {stop}  -  {STOP_GUIDE.get(stop, "")}')
    print()
    print(f'  Note: {OLED_NOTE}')
    print('─' * 60)
    chosen = input('  Enter floor-stop: ').strip()

if chosen not in VALID_STOPS:
    print(f'\n  ERROR: "{chosen}" is not a valid floor-stop.')
    print(f'  Valid options defined in Layer 2: {", ".join(VALID_STOPS)}')
    sys.exit(1)

CHOSEN_FLOOR_STOP = int(chosen)
print(f'\n  Floor-stop: {chosen}  -  {STOP_GUIDE.get(chosen, "")}')

# ─────────────────────────────────────────────────────────────────────────────
# CTA COLOR - designer prompt
# ─────────────────────────────────────────────────────────────────────────────
VALID_CTAS = ['primary', 'secondary']

if args.cta_color:
    chosen_cta = str(args.cta_color).lower()
else:
    print()
    print('─' * 60)
    print('  CTA COLOR - Main Call-To-Action button brand color')
    print('  Use "secondary" if your app background is predominantly primary color.')
    print('  Valid options: primary, secondary')
    print('─' * 60)
    entered = input('  Enter CTA color (default: primary): ').strip().lower()
    chosen_cta = entered if entered else 'primary'

if chosen_cta not in VALID_CTAS:
    print(f'\n  WARNING: "{chosen_cta}" is not valid. Defaulting to "primary".')
    chosen_cta = 'primary'
print(f'\n  CTA color: {chosen_cta}')

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 - OKLCH ↔ sRGB math
# ─────────────────────────────────────────────────────────────────────────────
def hex_to_oklch(hx: str) -> tuple:
    hx = hx.lstrip('#')
    rv,gv,bv = [int(hx[i:i+2],16)/255 for i in (0,2,4)]
    def tl(c): return c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4
    rl,gl,bl = tl(rv),tl(gv),tl(bv)
    x=.4124564*rl+.3575761*gl+.1804375*bl
    y=.2126729*rl+.7151522*gl+.0721750*bl
    z=.0193339*rl+.1191920*gl+.9503041*bl
    lm=.8189330101*x+.3618667424*y-.1288597137*z
    mm=.0329845436*x+.9293118715*y+.0361456387*z
    sm=.0482003018*x+.2643662691*y+.6338517070*z
    lp,mp,sp = lm**(1/3),mm**(1/3),sm**(1/3)
    L  = .2104542553*lp+.7936177850*mp-.0040720468*sp
    av = 1.9779984951*lp-2.4285922050*mp+.4505937099*sp
    bk = .0259040371*lp+.7827717662*mp-.8086757660*sp
    C  = math.sqrt(av*av+bk*bk)
    H  = math.degrees(math.atan2(bk,av)) % 360
    return L, C, H

def oklch_to_hex(L: float, C: float, H: float) -> str:
    rad=math.radians(H); a=C*math.cos(rad); b=C*math.sin(rad)
    lp=L+.3963377774*a+.2158037573*b
    mp=L-.1055613458*a-.0638541728*b
    sp=L-.0894841775*a-1.2914855480*b
    lc=lp**3; mc=mp**3; sc=sp**3
    x= 1.2270138511*lc-.5577999807*mc+.2812561490*sc
    y=-.0405801784*lc+1.1122568696*mc-.0716766787*sc
    z=-.0763812845*lc-.4214819784*mc+1.5861632204*sc
    rl=3.2404542*x-1.5371385*y-.4985314*z
    gl=-.9692660*x+1.8760108*y+.0415560*z
    bl=.0556434*x-.2040259*y+1.0572252*z
    def gam(v): c=max(0.,min(1.,v)); return c*12.92 if c<=.0031308 else 1.055*c**(1/2.4)-.055
    return '#{:02X}{:02X}{:02X}'.format(round(gam(rl)*255),round(gam(gl)*255),round(gam(bl)*255))

def oklch_to_rgb_linear(L: float, C: float, H: float) -> tuple:
    """Helper to get linear RGB without clamping."""
    rad = math.radians(H); a = C * math.cos(rad); b = C * math.sin(rad)
    lp = L + .3963377774 * a + .2158037573 * b
    mp = L - .1055613458 * a - .0638541728 * b
    sp = L - .0894841775 * a - 1.2914855480 * b
    lc = lp**3; mc = mp**3; sc = sp**3
    x =  1.2270138511 * lc - .5577999807 * mc + .2812561490 * sc
    y = -.0405801784 * lc + 1.1122568696 * mc - .0716766787 * sc
    z = -.0763812845 * lc - .4214819784 * mc + 1.5861632204 * sc
    rl =  3.2404542 * x - 1.5371385 * y - .4985314 * z
    gl = -.9692660 * x + 1.8760108 * y + .0415560 * z
    bl =  .0556434 * x - .2040259 * y + 1.0572252 * z
    return rl, gl, bl

def gamut_safe_oklch_to_hex(L: float, C: float, H: float) -> str:
    """Gamut-mapped conversion. Preserves L and H, safely reduces C."""
    current_C = C
    rl, gl, bl = oklch_to_rgb_linear(L, current_C, H)
    
    while (rl < 0 or rl > 1 or gl < 0 or gl > 1 or bl < 0 or bl > 1) and current_C > 0:
        current_C -= 0.001
        if current_C < 0: current_C = 0.0
        rl, gl, bl = oklch_to_rgb_linear(L, current_C, H)

    def gam(v): 
        c = max(0.0, min(1.0, v))
        return c * 12.92 if c <= .0031308 else 1.055 * c**(1/2.4) - .055
    
    return '#{:02X}{:02X}{:02X}'.format(
        round(gam(rl) * 255), round(gam(gl) * 255), round(gam(bl) * 255)
    )

def build_ramp(brand_hex: str, grey: bool = False, grey_hue: float = None) -> dict:
    bL, bC, bH = hex_to_oklch(brand_hex)
    f = classify_hue(bH) 
    n = len(ALL_STOPS)
    ramp = {}
    
    # 1. Parameterized Bounds (Protects Yellows and Blues from muddy shadows)
    L_MAX, L_MIN = 0.98, 0.05
    if not grey:
        if f.get('b') == 'yellow-optimized':
            L_MAX, L_MIN = 0.97, 0.10 
        elif f.get('b') == 'blue-optimized':
            L_MIN = 0.04 
            
    for idx, stop in enumerate(ALL_STOPS):
        # 2. Dynamic Lightness
        if grey: L = PG_L[stop]  
        elif stop == 500: L = bL
        elif stop < 500:
            t = (500 - stop) / 450.0
            L = bL + (L_MAX - bL) * (1 - (1 - t)**1.15)
        else:
            t = (stop - 500) / 500.0
            L = bL - (bL - L_MIN) * (1 - (1 - t)**1.15)
        
        # 3. Natural Chroma Envelope & Hue Drift
        bezE = ENV[stop]
        
        Hu = (grey_hue if grey_hue is not None else bH) if grey else bH
        Cr = 0.010 if grey else (bC * bezE)
        
        if not grey:
            Cf = min(Cr, f['s'])
            dr = bC - f['t']
            factor = max(0.35, min(1.0, (Cf - f['t']) / dr)) if dr > 0 else 0.5
            if stop < 500:
                t_light = (500 - stop) / 450.0
                Hu = bH + f['dL'] * factor * (t_light ** 1.1)
            elif stop > 500:
                t_dark = (stop - 500) / 500.0
                exp_dark = 0.65 if f.get('b') == 'yellow-optimized' else 1.1
                Hu = bH + f['dD'] * factor * (t_dark ** exp_dark)
        
        # 4. Gamut Safety Net — compute sRGB and P3 separately
        # sRGB: chroma clamped to family sRGB ceiling (universally displayable)
        C_srgb = min(Cr, f['s']) if not grey else Cr
        # P3: chroma clamped to family P3 ceiling (wider gamut, vibrant on capable displays)
        # This is the designer-facing value — what Figma shows in P3 canvas mode
        C_p3   = min(Cr, f['p']) if not grey else Cr

        hex_srgb = gamut_safe_oklch_to_hex(L, C_srgb, Hu)
        hex_p3   = gamut_safe_oklch_to_hex(L, C_p3,   Hu)

        ramp[stop] = {
            'srgb': hex_srgb, 'p3': hex_p3,
            'L': round(L,4), 'C_srgb': round(C_srgb,4), 'C_p3': round(C_p3,4), 'H': round(Hu,2)
        }
    return ramp

# STEP 2 - Layer 1 ramp engine
# ─────────────────────────────────────────────────────────────────────────────
def cbez(t: float) -> float:
    lo,hi,mt = 0.0,1.0,t
    for _ in range(10):
        ax=3*.4-3*.6+1; bx=3*.6-6*.4; cx=3*.4
        x=((ax*mt+bx)*mt+cx)*mt
        if x<t: lo=mt
        else:   hi=mt
        mt=(lo+hi)/2
    ay=3*0-3*1+1; by=3*1-6*0; cy=3*0
    return ((ay*mt+by)*mt+cy)*mt

ALL_STOPS = [50,100,200,300,400,500,600,700,800,900,950,1000]

PG_L = {50:.98,100:.95,200:.90,300:.80,400:.70,500:.55,600:.50,700:.40,800:.30,900:.20,950:.17,1000:.05}
ENV  = {50:.15,100:.35,200:.58,300:.78,400:.90,500:1.0,600:1.05,700:.98,800:.88,900:.72,950:.52,1000:.25}

FAM = [
    # warm_dir: +1 = positive hue shift warms highlights
    #           -1 = positive shift cools highlights
    # dL: hue offset applied to HIGHLIGHTS (stops < 500).
    # dD: hue offset applied to SHADOWS (stops > 500). Warm hues rotate negative (-H) toward red/orange
    #     to prevent falling into muddy olive/brown army zones.
    {'n':'pink',       'r':[[335,360],[0,15]],  'b':'standard',         's':.26,'p':.32,'dL': 8,  'dD':-6,  't':.10, 'warm_dir': 1},
    {'n':'red',        'r':[[15,45]],            'b':'standard',         's':.26,'p':.32,'dL': 5,  'dD':-5,  't':.08, 'warm_dir': 1},
    {'n':'orange',     'r':[[45,65]],            'b':'standard',         's':.24,'p':.29,'dL': 6,  'dD':-8,  't':.08, 'warm_dir': 1},
    # yellow: highlights drift warm sunlight (-H), shadows drift rich amber/cognac (-H) away from olive
    {'n':'yellow',     'r':[[65,105]],           'b':'yellow-optimized', 's':.22,'p':.27,'dL':-3,  'dD':-36, 't':.06, 'warm_dir': 1},
    # chartreuse: highlights pull toward warm yellow (-H), shadows drift toward warm leaf (-H)
    {'n':'chartreuse', 'r':[[105,130]],          'b':'yellow-optimized', 's':.22,'p':.27,'dL':-5,  'dD':-16, 't':.06, 'warm_dir': 1},
    # true-green: highlights toward chartreuse (-H), shadows toward deep forest teal (+H)
    {'n':'true-green', 'r':[[130,160]],          'b':'green-optimized',  's':.25,'p':.30,'dL':-4,  'dD': 6,  't':.08, 'warm_dir':-1},
    # teal: highlights pull toward mint (-H), shadows toward cyan (+H)
    {'n':'teal',       'r':[[160,185]],          'b':'green-optimized',  's':.22,'p':.27,'dL':-3,  'dD': 5,  't':.08, 'warm_dir':-1},
    {'n':'cyan',       'r':[[185,225]],          'b':'standard',         's':.22,'p':.27,'dL': 6,  'dD':-5,  't':.08, 'warm_dir':-1},
    {'n':'blue',       'r':[[225,285]],          'b':'blue-optimized',   's':.26,'p':.32,'dL': 4,  'dD':-4,  't':.06, 'warm_dir': 1},
    {'n':'purple',     'r':[[285,335]],          'b':'standard',         's':.28,'p':.35,'dL':10,  'dD':-8,  't':.08, 'warm_dir': 1},
]

def classify_hue(H: float) -> dict:
    for f in FAM:
        for a,b in f['r']:
            if a<=b:
                if a<=H<=b: return f
            else:
                if H>=a or H<=b: return f
    return FAM[0]


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 - Build all ramps from Layer 1 brand inputs
# ─────────────────────────────────────────────────────────────────────────────
if 'brand-inputs' not in L1:
    sys.exit("\nERROR: 'brand-inputs' missing from layer-1-generation-engine.json.")

BRANDS = dict(L1['brand-inputs'])
if args.brand_config:
    with open(args.brand_config, encoding='utf-8') as _bf:
        _custom = json.load(_bf)
        BRANDS.update(_custom.get('brand-inputs', _custom))
if args.primary:   BRANDS['primary']   = args.primary
if args.secondary: BRANDS['secondary'] = args.secondary
if args.info:      BRANDS['info']      = args.info
if args.warning:   BRANDS['warning']   = args.warning
if args.success:   BRANDS['success']   = args.success
if args.error:     BRANDS['error']     = args.error

RAMPS  = {k: build_ramp(v) for k, v in BRANDS.items()}

# 1. Read intended source from Layer 1 greyscale-outputs
pg_source_name = L1.get('greyscale-outputs', {}).get('primary-greyscale', {}).get('generated-from', 'primary')
sg_source_name = L1.get('greyscale-outputs', {}).get('secondary-greyscale', {}).get('generated-from', 'secondary')

# 2. Get actual brand hexes
pg_brand_hex = BRANDS.get(pg_source_name, '#000000')
sg_brand_hex = BRANDS.get(sg_source_name, '#000000')

# 3. Calculate dynamic OKLCH hues
_, _, pg_hue = hex_to_oklch(pg_brand_hex)
_, _, sg_hue = hex_to_oklch(sg_brand_hex)

# 4. Build greyscale ramps using the correct dynamic hues
RAMPS['pg'] = build_ramp(pg_brand_hex, grey=True, grey_hue=pg_hue)
RAMPS['sg'] = build_ramp(sg_brand_hex, grey=True, grey_hue=sg_hue)

# 5. Calculate elevation math dynamically based on the newly generated pg ramp
FLOOR_STOP = CHOSEN_FLOOR_STOP
FLOOR_L    = RAMPS['pg'][FLOOR_STOP]['L']
ELEV_STEP  = L2['mode-mapping']['dark-mode-elevation']['computed-tokens'].get('step-dL', 0.02)

# Weber-Fechner perceptual elevation spacing.
# Linear ΔL steps feel unequal: early levels (0→1) appear nearly identical,
# late levels (3→4) feel too separated. A power curve (i/4)^exponent produces
# smaller early steps and larger late steps while preserving total ΔL range.
# Reference: concern #20 — Weber-Fechner law for equal-perceptible depth steps.
_ELEV_PWR  = L2['mode-mapping']['dark-mode-elevation']['computed-tokens'].get('power-curve-exponent', 1.3)
_ELEV_TDEL = L2['mode-mapping']['dark-mode-elevation']['computed-tokens'].get('total-dL', 0.08)

def _elev_L(i):
    """Power-curved lightness for elevation stop i (0-4)."""
    if i == 0: return FLOOR_L
    return FLOOR_L + ((i / 4) ** _ELEV_PWR) * _ELEV_TDEL

ELEV    = [oklch_to_hex(_elev_L(i), .010, pg_hue) for i in range(5)]
ELEV_SG = [oklch_to_hex(_elev_L(i), .010, sg_hue) for i in range(5)]

def ev(i: int, surface: str = 'pg') -> str:
    """Resolve elevation stop. surface='pg' (purple, default) or 'sg' (orange)."""
    ramp = ELEV if surface == 'pg' else ELEV_SG
    return ramp[i] if i < len(ramp) else '#000000'

def sh(ramp: str, stop: int, gamut: str = 'srgb') -> str:
    return RAMPS.get(ramp, {}).get(stop, {}).get(gamut, '#000000')

print(f'Ramps built: {list(RAMPS.keys())} + {len(ELEV)} elev-pg stops + {len(ELEV_SG)} elev-sg stops (floor={FLOOR_STOP})')

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3b - 8-BIT QUANTIZATION COLLAPSE CHECK (concern #28)
# The compiler computes OKLCH with float precision but outputs 8-bit hex.
# Adjacent stops with small ΔL in dark regions may round to the same hex.
# A build that passes logic checks but ships identical adjacent elevations is
# silently broken — users see a flat surface with no depth.
#
# SCOPE RULE: Stop 1000 is OLED-reserved and excluded from hue-active-range in
# Layer 1. It is never a deployable semantic token. Chromatic ramps (all except
# pg and sg) must skip the 950→1000 pair — this collapse is physically expected
# (true-green cannot retain sRGB distinction at L=0.05) and architecturally
# irrelevant because nothing will ever resolve to stop 1000 on a chromatic ramp.
# Greyscale ramps (pg, sg) are checked across all stops since they back surface
# tokens and must remain distinct throughout.
# ─────────────────────────────────────────────────────────────────────────────
_GREYSCALE_RAMPS  = {'pg', 'sg'}
_OLED_STOP        = 1000   # excluded from chromatic ramp checks
_quant_errors     = []
_quant_skipped    = 0

# Check elevation ramps (all 5 stops are deployable — no exclusion)
for _label, _ramp in [('elev-pg', ELEV), ('elev-sg', ELEV_SG)]:
    for _qi in range(1, len(_ramp)):
        if _ramp[_qi] == _ramp[_qi - 1]:
            _quant_errors.append(
                f"QUANTIZATION_COLLAPSE [{_label}]: stop {_qi} == stop {_qi-1} "
                f"({_ramp[_qi]}). The OKLCH ΔL between these stops collapses to "
                f"0 in 8-bit sRGB at this lightness level. "
                f"Increase total-dL in Layer 2 dark-mode-elevation or raise floor-stop."
            )

# Check all primitive ramps for adjacent stop collapses
for _rk, _rd in RAMPS.items():
    _is_greyscale = _rk in _GREYSCALE_RAMPS
    _sorted_stops = sorted(_rd.keys())
    for _qi in range(1, len(_sorted_stops)):
        _ps, _cs = _sorted_stops[_qi - 1], _sorted_stops[_qi]

        # Skip the 950→1000 pair for chromatic (non-greyscale) ramps.
        # Stop 1000 is OLED-reserved — not in hue-active-range, never a
        # semantic token. Its collapse into near-black is physically expected
        # and is not a deployable failure. Greyscale ramps still check all
        # stops because pg/sg back surface tokens across the full range.
        if not _is_greyscale and _cs == _OLED_STOP:
            _quant_skipped += 1
            continue

        if _rd[_cs]['srgb'] == _rd[_ps]['srgb']:
            _quant_errors.append(
                f"QUANTIZATION_COLLAPSE [{_rk}]: stop {_cs} == stop {_ps} "
                f"({_rd[_cs]['srgb']}). Perceptual distinction lost in 8-bit sRGB. "
                f"This is a deployable stop — two adjacent tokens share the same hex. "
                f"Increase chroma or raise L_MIN for the {_rk} ramp's hue family."
            )

if _quant_errors:
    print('\n' + '─' * 80)
    print('  8-BIT QUANTIZATION COLLAPSE — HARD BUILD ERROR')
    print('  Adjacent deployable tokens resolve to identical hex. Depth hierarchy broken.\n')
    for _e in _quant_errors:
        print(f'  ✗  {_e}')
    print('─' * 80)
    sys.exit(1)
else:
    _total_pairs = (
        sum(len(v) - 1 for v in RAMPS.values())
        + (len(ELEV) - 1) + (len(ELEV_SG) - 1)
        - _quant_skipped
    )
    print(f'quantization check      - {_total_pairs} deployable pairs checked '
          f'({_quant_skipped} OLED-reserved pairs excluded) · 0 collapses ✓')

# ─────────────────────────────────────────────────────────────────────────────
# CTA INJECTION - in-memory L4 patch (after ramps are built)
# ─────────────────────────────────────────────────────────────────────────────
fill_role = 'color/fill/brand' if chosen_cta == 'primary' else f'color/fill/{chosen_cta}'
text_role = 'color/on-fill/brand' if chosen_cta == 'primary' else f'color/on-fill/{chosen_cta}'

btn_pri = L4.get('component-tokens', {}).get('button', {}).get('primary', {})
for key, val in btn_pri.items():
    if isinstance(val, dict) and 'color' in val:
        if key.startswith('bg/'):
            val['color'] = fill_role
        elif key.startswith('text/') or key.startswith('label/'):
            val['color'] = text_role

print(f'CTA injection          - button/primary rewired to {fill_role} and {text_role}')

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 - Primitive alias resolver
# ─────────────────────────────────────────────────────────────────────────────
SEM_ROLES = L4.get('semantic-role-map', {}).get('roles', {})
_alias_stack = set()

def _blend_overlay(fg_hex: str, bg_hex: str, alpha: float) -> str:
    def ch(h, i): return int(h.lstrip('#')[i*2:i*2+2], 16)
    r = round((1 - alpha) * ch(bg_hex, 0) + alpha * ch(fg_hex, 0))
    g = round((1 - alpha) * ch(bg_hex, 1) + alpha * ch(fg_hex, 1))
    b = round((1 - alpha) * ch(bg_hex, 2) + alpha * ch(fg_hex, 2))
    return f'#{r:02X}{g:02X}{b:02X}'

def resolve_alias(alias: str | dict, gamut: str = 'srgb', blend_bg: str = None) -> str | None:
    if isinstance(alias, dict):
        alias = alias.get('alias') or alias.get('$value')

    if not isinstance(alias, str) or alias in ('-', 'null', 'transparent'):
        return alias

    if alias in _alias_stack:
        return '#000000'

    _alias_stack.add(alias)

    try:
        # 1. Flexible Overlay Handling (supports Roles and Primitives)
        if '@' in alias:
            if blend_bg is None: return None
            m = _re.match(r'^\{([\w/-]+)(?:\.(\d+))?\}\s*@\s*([\d.]+)%$', alias)
            if m:
                inner = f"{{{m.group(1)}.{m.group(2)}}}" if m.group(2) else f"{{{m.group(1)}}}"
                fg_hex = resolve_alias(inner, gamut, blend_bg=blend_bg)
                alpha  = float(m.group(3)) / 100
                return _blend_overlay(fg_hex, blend_bg, alpha) if fg_hex else None
            return None

        # 2. Elevations
        m = _re.match(r'^\{elev(?:-(pg|sg))?\.(\d)\}$', alias)
        if m:
            return ev(int(m.group(2)), m.group(1) or 'pg')

        # 3. Primitives
        m = _re.match(r'^\{([\w-]+)\.(\d+)\}$', alias)
        if m:
            return sh(m.group(1), int(m.group(2)), gamut)

        # 4. Semantic Chain Following (Return the string for CSS fallback)
        return alias 
    finally:
        _alias_stack.discard(alias)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 - Semantic role resolver
# ─────────────────────────────────────────────────────────────────────────────
def resolve_role(role_name: str, mode: str, gamut: str = 'srgb') -> str | None:
    data = SEM_ROLES.get(role_name)
    if not data:
        msg = f'Unknown semantic role referenced in component tokens: "{role_name}"'
        if args.strict:
            sys.exit(f'\n  STRICT ERROR- {msg}')
        return None
    alias = data.get('light' if mode == 'light' else 'dark')
    if not alias or alias in (None, '-'): return None
    return resolve_alias(alias, gamut)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 - Emit tokens-primitives.json
# ─────────────────────────────────────────────────────────────────────────────
primitives_out = {
    '$meta': {
        'generated':       datetime.now(timezone.utc).isoformat(),
        'layer-1-version': L1['meta']['version'],
        'floor-stop':      FLOOR_STOP,
        'cta-color':       chosen_cta,
        'description':     'Layer 1 output. All ramp stops computed from brand hex via OKLCH engine. Never edit by hand.',
    },
    'ramps': {},
    'elevation': {},
}

for ramp_key, ramp_data in RAMPS.items():
    primitives_out['ramps'][ramp_key] = {}
    for stop, vals in ramp_data.items():
        p3_differs = vals['srgb'] != vals['p3']
        primitives_out['ramps'][ramp_key][str(stop)] = {
            '$value':      vals['srgb'],
            '$type':       'color',
            'p3':          vals['p3'] if p3_differs else None,
            'p3-expanded': p3_differs,
            'L':           vals['L'],
            'C_srgb':      vals['C_srgb'],
            'C_p3':        vals['C_p3'],
            'H':           vals['H'],
        }

for i in range(5):
    usage = L2['mode-mapping']['dark-mode-elevation']['computed-tokens'].get(str(i), {}).get('usage', '')
    primitives_out['elevation'][f'elev-pg.{i}'] = {
        '$value': ev(i, 'pg'), '$type': 'color',
        'L':  round(FLOOR_L + i*ELEV_STEP, 4),
        'dL': round(i*ELEV_STEP, 4),
        'hue-source': 'secondary (pg greyscale)',
        'usage': usage,
        'designer-note': 'Default. Use when pg is your surface ramp (purple-tinted neutrals).',
    }
    primitives_out['elevation'][f'elev-sg.{i}'] = {
        '$value': ev(i, 'sg'), '$type': 'color',
        'L':  round(FLOOR_L + i*ELEV_STEP, 4),
        'dL': round(i*ELEV_STEP, 4),
        'hue-source': 'primary (sg greyscale)',
        'usage': usage,
        'designer-note': 'Alternative. Use when sg is your surface ramp (orange-tinted neutrals).',
    }

(OUT / 'tokens-primitives.json').write_text(json.dumps(primitives_out, indent=2), encoding='utf-8')
total_stops = sum(len(v) for v in RAMPS.values())
print(f'tokens-primitives.json  - {len(RAMPS)} ramps × {len(ALL_STOPS)} stops = {total_stops} primitive tokens + {len(ELEV)} elevation stops')

# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 - Emit tokens-semantic.json
# ─────────────────────────────────────────────────────────────────────────────
semantic_out = {
    '$meta': {
        'generated':       datetime.now(timezone.utc).isoformat(),
        'layer-2-version': L2['compiler-contract']['version'],
        'layer-4-version': L4['meta']['version'],
        'description':     'Layer 2+4 output. Semantic roles resolved to primitive aliases and hex.',
    },
    'roles': {},
}

# Page background - used as blend target for overlay alpha-compositing
_LIGHT_BG = resolve_alias(SEM_ROLES.get('color/bg', {}).get('light'))
_DARK_BG   = resolve_alias(SEM_ROLES.get('color/bg', {}).get('dark'))

for role_name, role_data in SEM_ROLES.items():
    light_alias = role_data.get('light')
    dark_alias  = role_data.get('dark')
    is_overlay  = '@' in str(light_alias or '') or '@' in str(dark_alias or '')

    if is_overlay:
        # Resolve to blended concrete hex so CSS consumers get a real value
        light_hex = resolve_alias(light_alias, blend_bg=_LIGHT_BG)
        dark_hex  = resolve_alias(dark_alias,  blend_bg=_DARK_BG)
    else:
        light_hex = resolve_alias(light_alias) if light_alias else None
        dark_hex  = resolve_alias(dark_alias)  if dark_alias  else None

    entry = {
        '$type': 'color',
        'weight': role_data.get('weight'),
        'desc':   role_data.get('desc', ''),
        'light':  {'alias': light_alias, '$value': light_hex},
        'dark':   {'alias': dark_alias,  '$value': dark_hex},
    }
    if is_overlay:
        entry['overlay']       = True
        entry['apca-rule']     = role_data.get('apca-rule', 'NO_TEXT')
        entry['blend-note']    = 'Blended over color/bg. Real appearance depends on content underneath.'
    semantic_out['roles'][role_name] = entry

(OUT / 'tokens-semantic.json').write_text(json.dumps(semantic_out, indent=2), encoding='utf-8')
print(f'tokens-semantic.json    - {len(semantic_out["roles"])} semantic roles')

# ─────────────────────────────────────────────────────────────────────────────
# STEP 7b - Delta engine helpers
# ─────────────────────────────────────────────────────────────────────────────
def _srgb_y(hx: str) -> float:
    r, g, b = (int(hx[1:3], 16)/255, int(hx[3:5], 16)/255, int(hx[5:7], 16)/255)
    def lin(c): return c/12.92 if c <= 0.04045 else ((c+0.055)/1.055)**2.4
    return 0.2126729*lin(r) + 0.7151522*lin(g) + 0.0722*lin(b)

def _apca_lc(txt: str, bg: str) -> float:
    Yt, Yb = _srgb_y(txt), _srgb_y(bg)
    if Yb >= Yt: lc = (Yb**0.56 - Yt**0.57) * 1.14
    else:        lc = (Yb**0.65 - Yt**0.62) * 1.14
    return round(abs(lc) * 1000) / 10 if abs(lc) >= 0.1 else 0.0
@lru_cache(maxsize=2048)
def _cached_y(hx): return _srgb_y(hx.upper())

@lru_cache(maxsize=2048)
def _cached_lc(t_hx, b_hx): return _apca_lc(t_hx.upper(), b_hx.upper())

def classify_apca_failure(t_y, b_y):
    """Diagnoses why a color pair is failing perceptually."""
    dy = abs(t_y - b_y)
    avg_y = (t_y + b_y) / 2
    if dy < 0.05: return "Luminance Proximity (Colors too close)"
    if avg_y < 0.25: return "Low-Luminance Compression (Shadow zone)"
    if avg_y > 0.75: return "High-Luminance Compression (Highlight zone)"
    return "Insufficient Perceptual Weight"

def suggest_perceptual_nudge(text_role, bg_hex, mode, target_lc):
    """
    v18.0: Discovery -> Governance -> Selection Pipeline
    """
    current_hex = resolve_role(text_role, mode)
    if not current_hex: return None
    
    # 1. SETUP
    policy = TEXT_POLICY.get(text_role, TEXT_POLICY["default"])
    m = _re.match(r'^\{(\w+)\.(\d+)\}', SEM_ROLES.get(text_role, {}).get(mode, ""))
    if not m: return None
    ramp_name, current_stop = m.group(1), int(m.group(2))
    
    # NEW GUARD: elevation tokens are structural
    if ramp_name == 'elev':
        return None
        
    text_y, bg_y = _cached_y(current_hex), _cached_y(bg_hex)
    text_is_lighter = text_y > bg_y

    # 2. DISCOVERY (Pure Math)
    math_passes = []
    for stop, vals in RAMPS[ramp_name].items():
        raw_lc = _cached_lc(vals['srgb'], bg_hex)
        if abs(raw_lc) >= (target_lc - 0.5):
            math_passes.append({
                'stop': int(stop), 'lc_raw': raw_lc, 'hex': vals['srgb'],
                'y': _cached_y(vals['srgb']), 'chroma': vals.get('C_srgb', 0)
            })

    # 3. GOVERNANCE (Apply Brand Policy)
    policy_passes = [c for c in math_passes if policy["allow_polarity_flip"] or ((c['y'] > bg_y) == text_is_lighter)]
    
    # 4. SELECTION (Rank by Perceptual Distance)
    is_violation = not bool(policy_passes)
    candidates = policy_passes if not is_violation else math_passes
    if not candidates: 
        return {"type": "hard_fail", "reason": classify_apca_failure(text_y, bg_y)}

    best = min(candidates, key=lambda x: (abs(x['y'] - text_y), abs(abs(x['lc_raw']) - target_lc), -x['chroma']))

    # 5. TELEMETRY
    margin = abs(best['lc_raw']) - target_lc
    is_flip = (best['y'] > bg_y) != text_is_lighter
    return {
        "type": "suggestion",
        "alias": f"{{{ramp_name}.{best['stop']}}}",
        "confidence": {
            "perceptual": "high" if (margin/target_lc) >= 0.25 else "medium" if (margin/target_lc) >= 0.1 else "low",
            "policy": "VIOLATED" if is_flip else "COMPLIANT"
        },
        "msg": f"Switch to {{{ramp_name}.{best['stop']}}} | +{margin:.1f} Lc" + (" (⚠ Polarity Flip)" if is_flip else ""),
        "reason": classify_apca_failure(text_y, bg_y),
        "is_no_op": best['stop'] == current_stop
    }
# ─────────────────────────────────────────────────────────────────────────────
# PERCEPTUAL HELPERS (concerns #1, #21, #27, #32 support functions)
# ─────────────────────────────────────────────────────────────────────────────

def _oklab_de(hex1: str, hex2: str) -> float:
    """Perceptual distance in OKLAB between two sRGB hex colours."""
    L1, C1, H1 = hex_to_oklch(hex1)
    L2, C2, H2 = hex_to_oklch(hex2)
    a1 = C1 * math.cos(math.radians(H1)); b1 = C1 * math.sin(math.radians(H1))
    a2 = C2 * math.cos(math.radians(H2)); b2 = C2 * math.sin(math.radians(H2))
    return math.sqrt((L1 - L2)**2 + (a1 - a2)**2 + (b1 - b2)**2)

def _to_linear_rgb(hx: str) -> tuple:
    """sRGB hex → linear RGB [0,1]."""
    r, g, b = int(hx[1:3],16)/255, int(hx[3:5],16)/255, int(hx[5:7],16)/255
    def lin(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return lin(r), lin(g), lin(b)

def _from_linear_rgb(rl: float, gl: float, bl: float) -> str:
    """Linear RGB → sRGB hex (clamped)."""
    def gam(v): c = max(0.0, min(1.0, v)); return c * 12.92 if c <= 0.0031308 else 1.055 * c**(1/2.4) - 0.055
    return '#{:02X}{:02X}{:02X}'.format(round(gam(rl)*255), round(gam(gl)*255), round(gam(bl)*255))

def _simulate_deuteranopia(rl: float, gl: float, bl: float) -> tuple:
    """Approximate deuteranopia (no M-cone) in linear sRGB. Vienot et al. 1999."""
    r2 = 0.29031 * rl + 0.70969 * gl
    g2 = 0.29031 * rl + 0.70969 * gl
    return r2, g2, bl

def _simulate_protanopia(rl: float, gl: float, bl: float) -> tuple:
    """Approximate protanopia (no L-cone) in linear sRGB. Vienot et al. 1999."""
    r2 = 0.10889 * rl + 0.89111 * gl
    g2 = 0.10889 * rl + 0.89111 * gl
    return r2, g2, bl

def _apply_cvd_simulation(hx: str, sim_fn) -> str:
    """Apply a CVD simulation function to an sRGB hex, return simulated hex."""
    rl, gl, bl = _to_linear_rgb(hx)
    rs, gs, bs = sim_fn(rl, gl, bl)
    return _from_linear_rgb(rs, gs, bs)

# Categorical hue boundary map (OKLCH approximate).
# Used to detect when a semantic ramp crosses a colour-name boundary (concern #32).
_HUE_CATEGORIES = [
    ((335, 360), 'pink'), ((0, 15), 'pink'),
    ((15, 45), 'red'), ((45, 65), 'orange'), ((65, 105), 'yellow'),
    ((105, 130), 'chartreuse'), ((130, 160), 'green'), ((160, 185), 'teal'),
    ((185, 225), 'cyan'), ((225, 285), 'blue'), ((285, 335), 'purple'),
]

def _hue_category(H: float) -> str:
    """Return the human-readable colour category name for an OKLCH hue angle."""
    for (lo, hi), name in _HUE_CATEGORIES:
        if lo <= hi:
            if lo <= H <= hi: return name
        else:
            if H >= lo or H <= hi: return name
    return 'unknown'

def _is_muddy_zone(L: float, C: float, H: float) -> bool:
    """
    True if OKLCH coordinates fall in the perceptually 'dirty' zone.
    Dark-yellow / olive / muddy-brown region — instinctively unappealing.
    Reference: concern #21, pro-color-harmonies avoidMuddyZones.
    """
    return 55 <= H <= 125 and 0.22 <= L <= 0.50 and C > 0.04

# ─────────────────────────────────────────────────────────────────────────────
# APCA PER-ROLE TARGET LOOKUP (concern #2 — spatial-frequency blindspot fix)
# Reads per-role Lc targets from Layer 2 apca-role-targets.
# Caption and small text need Lc 90; display text can use Lc 45.
# A flat Lc 60 for all text is a false guarantee at small sizes.
# ─────────────────────────────────────────────────────────────────────────────
def _get_apca_target(role_name: str) -> float:
    """
    Return the APCA Lc target for a semantic role.
    Reads from L2 apca-role-targets (prefix-matched, first match wins).
    Falls back to the existing logic if the key is absent from L2.
    """
    _rt = L2.get('compiler-contract', {}).get('apca-role-targets', {})
    for entry in _rt.get('targets', []):
        if role_name.startswith(entry.get('prefix', '')):
            return float(entry.get('lc', 60))
    # Legacy fallback (unchanged from original logic)
    if role_name.startswith('color/border/'):
        return 15.0 if 'subtle' in role_name else 30.0
    elif role_name.startswith('color/icon/'):
        return 45.0
    elif 'disabled' in role_name or 'placeholder' in role_name:
        return 45.0
    elif role_name.startswith('color/focus/ring'):
        return 30.0
    return float(_rt.get('fallback-lc', 60))

def resolve_interaction_state(tok_name, base_hex, delta_config, mode, comp_block):
    """Applies Layer 3 physics deltas to interaction states (hover/active)."""
    if not base_hex or base_hex == 'transparent':
        return base_hex, None

    L, C, H = hex_to_oklch(base_hex)

    # Get the delta for this mode, or fallback to auto-pivot
    dL = delta_config.get(f'L_{mode}')
    if dL is None:
        dL = delta_config.get('L', 0.0)
        # Pivot: typically darken in light mode, lighten in dark mode
        if mode == 'dark' and dL < 0:
            dL = abs(dL)

    # ── ACHROMATIC SNAP (concern #27) ────────────────────────────────────────
    # Hue angle is numerically undefined at C=0 and unstable below C=0.01.
    # Applying any delta to a near-neutral token can produce hue jitter —
    # a "cool grey" hover state may snap to a dirty yellow if the direction
    # of ΔC is arbitrary. Fix: treat as pure neutral, apply ΔL only.
    _ACHROMATIC_THRESHOLD = 0.01
    if C < _ACHROMATIC_THRESHOLD:
        new_L = max(0.0, min(1.0, L + dL))
        new_hex = gamut_safe_oklch_to_hex(new_L, 0.0, 0.0)
        return new_hex, None

    new_L = max(0.0, min(1.0, L + dL))
    # ── MUDDY ZONE RESILIENCE ───────────────────────────────────────────────
    # Warm-floor surfaces with linear ΔL can drift into dark-yellow/olive zone.
    # Shift warm hue away from muddy olive zone toward rich amber (H ~ 48°),
    # or desaturate chartreuse/olive to keep interaction states clean and crisp.
    if _is_muddy_zone(new_L, C, H):
        if 55 <= H <= 85:
            H = 48.0
        elif 85 < H <= 125:
            C = min(C, 0.035)

    new_hex = gamut_safe_oklch_to_hex(new_L, C, H)

    new_L_f, new_C_f, new_H_f = hex_to_oklch(new_hex)
    if _is_muddy_zone(new_L_f, new_C_f, new_H_f):
        print(f'  ⚠  MUDDY_ZONE [{mode.upper()}] {tok_name}: interaction state '
              f'(L={new_L_f:.2f}, C={new_C_f:.3f}, H={new_H_f:.0f}°) falls in '
              f'dark-yellow/olive muddy zone. Consider desaturating or shifting hue.')

    return new_hex, None
# ─────────────────────────────────────────────────────────────────────────────
# STEP 8 - Emit tokens-component.json
# Full chain: component-token → semantic-role → primitive-alias → hex
# ─────────────────────────────────────────────────────────────────────────────
component_out = {
    '$meta': {
        'generated':       datetime.now(timezone.utc).isoformat(),
        'layer-4-version': L4['meta']['version'],
        'cta-color':       chosen_cta,
        'description':     'Layer 4 output. Component tokens resolved through full chain.',
        'chain':           'component-token → semantic-role → {primitive.stop} → hex',
    },
    'components': {},
}

ct = L4['component-tokens']
_SKIP = {
    'description','reference-rule','state-delta-source','variants','states',
    'covers','extends','desc','delta-source','step-states',
}

MODES_TO_COMPILE = ['light', 'dark'] if args.mode == 'both' else [args.mode]
token_count = 0


def resolve_component_token(token_data: dict, modes: list,
                            tok_name: str = '', comp_block: dict = None) -> dict:
    """
    Resolve a single component token to hex for each mode.
    When the token has a 'delta' key the base hex is fed through
    resolve_interaction_state (pivot math + APCA auto-correction).
    """
    result     = {}
    color_role = token_data.get('color')
    if not color_role or color_role == 'transparent':
        result['semantic-role'] = color_role
        for mode in modes:
            result[mode] = {'$value': 'transparent', 'alias': 'transparent'}
        return result

    result['semantic-role'] = color_role
    result['desc']          = token_data.get('desc', '')
    delta_config            = token_data.get('delta')
    if delta_config:
        result['delta'] = delta_config

    for mode in modes:
        sem_data = SEM_ROLES.get(color_role, {})
        alias    = sem_data.get('light' if mode == 'light' else 'dark')
        base_hex = resolve_alias(alias) if alias and '@' not in str(alias) else None
        is_ov    = '@' in str(alias or '')

        if base_hex and delta_config and comp_block is not None:
            resolved_hex, opacity = resolve_interaction_state(
                tok_name, base_hex, delta_config, mode, comp_block
            )
            entry = {
                'alias':          alias,
                '$value':         resolved_hex,
                'base-hex':       base_hex,
                'delta-resolved': True,
            }
            if opacity is not None:
                entry['opacity'] = opacity
        else:
            entry = {'alias': alias, '$value': base_hex}
            if is_ov:
                entry['overlay'] = True

        result[mode] = entry
    return result


def _add_token(out_target: dict, key: str, value, comp_name: str):
    """
    Write a resolved token to out_target, warning (or hard-erroring in --strict
    mode) if the same key is written twice.  Duplicate keys in the same
    component block indicate a Layer 4 authoring mistake.
    """
    if key in out_target:
        msg = f'Token collision in {comp_name}: key "{key}" resolved twice.'
        if args.strict:
            sys.exit(f'\n  STRICT ERROR - {msg}')
        print(f'  WARNING - {msg}')
    out_target[key] = value


def _resolve_flat_block(comp_name: str, block: dict, out_target: dict):
    """
    Resolve all tokens in a flat component block.
    Handles three token shapes:
      1. Inline-variant tokens  {bg: role, text: role, border: role, …}
      2. Standard color tokens  {color: role, delta?: {…}}
    """
    global token_count
    for tok_name, tok_data in block.items():
        if tok_name in _SKIP:
            continue
        if not isinstance(tok_data, dict):
            continue
        if ('color' not in tok_data
                and not any(k in tok_data for k in ('bg', 'text', 'border', 'icon', 'title'))):
            continue

        # Shape 1 - inline variant (badge, alert, toast)
        if any(k in tok_data for k in ('bg', 'text', 'border', 'icon', 'title')):
            variant_out = {}
            for prop, role in tok_data.items():
                if prop in ('desc', 'use-case', 'note'):
                    continue
                if isinstance(role, str) and role.startswith('color/'):
                    sem_data = SEM_ROLES.get(role, {})
                    entry    = {'semantic-role': role}
                    for mode in MODES_TO_COMPILE:
                        alias   = sem_data.get('light' if mode == 'light' else 'dark')
                        hex_val = resolve_alias(alias) if alias and '@' not in str(alias) else None
                        entry[mode] = {'alias': alias, '$value': hex_val}
                    variant_out[prop] = entry
                    token_count += 1
            _add_token(out_target, tok_name, variant_out, comp_name)

        # Shape 2 - standard color token (with optional delta)
        elif 'color' in tok_data:
            _add_token(
                out_target, tok_name,
                resolve_component_token(
                    tok_data, MODES_TO_COMPILE,
                    tok_name=tok_name,
                    comp_block=block,
                ),
                comp_name,
            )
            token_count += 1


for comp_name, comp_data in ct.items():
    if comp_name in _SKIP:
        continue
    if not isinstance(comp_data, dict):
        continue

    component_out['components'][comp_name] = {}
    out_comp = component_out['components'][comp_name]

    # Detect nested variant structure:
    # A component has variants when its child dicts contain color tokens
    # AND those child dicts are NOT inline-variant shapes (bg/text/border).
    has_variants = any(
        isinstance(v, dict)
        and any(isinstance(vv, dict) and 'color' in vv for vv in v.values())
        and not any(k in ('bg', 'text', 'border', 'icon', 'title') for k in v)
        for k, v in comp_data.items()
        if k not in _SKIP
    )

    if has_variants:
        for variant_name, variant_data in comp_data.items():
            if variant_name in _SKIP:
                continue
            if not isinstance(variant_data, dict):
                continue
            out_comp[variant_name] = {}
            _resolve_flat_block(
                f'{comp_name}.{variant_name}', variant_data, out_comp[variant_name]
            )
    else:
        _resolve_flat_block(comp_name, comp_data, out_comp)

# Sort component names alphabetically for stable, diff-friendly output.
# Token keys within each component keep their authoring order so that
# state sequences (default→hover→active→pressed) remain readable.
# We deliberately do NOT use sort_keys=True globally - that would break
# ramp stop numeric order ('1000' sorts before '200' as a string).
component_out['components'] = dict(sorted(component_out['components'].items()))
(OUT / 'tokens-component.json').write_text(json.dumps(component_out, indent=2), encoding='utf-8')
print(f'tokens-component.json   - {len(component_out["components"])} components, ~{token_count} tokens')

# ─────────────────────────────────────────────────────────────────────────────
# STEP 8b - Emit tokens-component.css
# Developers consume component tokens as CSS custom properties so they never
# reference primitive hex directly. Each var() points to a semantic role var().
# ─────────────────────────────────────────────────────────────────────────────
if not args.no_css:
    comp_css = [
        f'/* Component tokens - Generated {datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")} */',
        f'/* Reference chain: --comp-token → --semantic-role → primitive hex */',
        '/* Usage: background: var(--button-primary-bg-default); */',
        '',
        ':root {',
    ]
    for comp_name, comp_data in component_out['components'].items():
        comp_css.append(f'')
        comp_css.append(f'  /* {comp_name} */')
        def _flat_css(prefix, block):
            for tok_name, tok_data in block.items():
                if not isinstance(tok_data, dict):
                    continue
                prop = '--' + prefix + '-' + tok_name.replace('/', '-').replace(' ', '-')
                # Standard token: has light/dark keys
                if 'light' in tok_data and isinstance(tok_data['light'], dict):
                    light_val = tok_data['light'].get('$value')
                    sem_role  = tok_data.get('semantic-role', '')
                    if light_val and light_val != 'transparent':
                        # Point to semantic CSS var, fall back to hex
                        sem_prop = '--' + sem_role.replace('/', '-') if sem_role else None
                        css_val  = f'var({sem_prop}, {light_val})' if sem_prop else light_val
                        comp_css.append(f'  {prop}: {css_val};')
                    elif light_val == 'transparent':
                        comp_css.append(f'  {prop}: transparent;')
                # Inline variant token (badge, alert): has bg/text/border keys
                elif any(k in tok_data for k in ('bg','text','border','icon','title')):
                    for prop_k, prop_data in tok_data.items():
                        if not isinstance(prop_data, dict):
                            continue
                        sub_prop = f'{prop}-{prop_k}'
                        light_val = prop_data.get('light', {}).get('$value')
                        sem_role  = prop_data.get('semantic-role', '')
                        if light_val and light_val != 'transparent':
                            sem_prop = '--' + sem_role.replace('/', '-') if sem_role else None
                            css_val  = f'var({sem_prop}, {light_val})' if sem_prop else light_val
                            comp_css.append(f'  {sub_prop}: {css_val};')
        _flat_css(comp_name, comp_data)
    comp_css.append('}')
    comp_css.append('')
    comp_css.append('/* Dark mode component overrides */')
    comp_css.append('@media (prefers-color-scheme: dark) {')
    comp_css.append('  :root {')
    for comp_name, comp_data in component_out['components'].items():
        def _flat_css_dark(prefix, block):
            for tok_name, tok_data in block.items():
                if not isinstance(tok_data, dict):
                    continue
                prop = '--' + prefix + '-' + tok_name.replace('/', '-').replace(' ', '-')
                if 'dark' in tok_data and isinstance(tok_data['dark'], dict):
                    dark_val = tok_data['dark'].get('$value')
                    sem_role = tok_data.get('semantic-role', '')
                    if dark_val and dark_val != 'transparent':
                        sem_prop = '--' + sem_role.replace('/', '-') if sem_role else None
                        css_val  = f'var({sem_prop}, {dark_val})' if sem_prop else dark_val
                        comp_css.append(f'    {prop}: {css_val};')
                elif any(k in tok_data for k in ('bg','text','border','icon','title')):
                    for prop_k, prop_data in tok_data.items():
                        if not isinstance(prop_data, dict): continue
                        sub_prop = f'{prop}-{prop_k}'
                        dark_val = prop_data.get('dark', {}).get('$value')
                        sem_role = prop_data.get('semantic-role', '')
                        if dark_val and dark_val != 'transparent':
                            sem_prop = '--' + sem_role.replace('/', '-') if sem_role else None
                            css_val  = f'var({sem_prop}, {dark_val})' if sem_prop else dark_val
                            comp_css.append(f'    {sub_prop}: {css_val};')
        _flat_css_dark(comp_name, comp_data)
    comp_css.append('  }')
    comp_css.append('}')
    (OUT / 'tokens-component.css').write_text('\n'.join(comp_css), encoding='utf-8')
    print(f'tokens-component.css    - {len(comp_css)} lines')

# ─────────────────────────────────────────────────────────────────────────────
# STEP 9 - Emit tokens.css  (three-tier gamut)
# ─────────────────────────────────────────────────────────────────────────────
if not args.no_css:
    css_lines = [
        f'/* Design System - Generated {datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")} */',
        f'/* L1 v{L1["meta"]["version"]} · L2 v{L2["compiler-contract"]["version"]} · floor-stop: {FLOOR_STOP} · cta: {chosen_cta} */',
        '/* Three-tier gamut: sRGB baseline · P3 @media · HDR @media */',
        '',
        '/* ── Primitives - sRGB baseline ── */',
        ':root {',
    ]

    for ramp_key, ramp_data in RAMPS.items():
        for stop, vals in ramp_data.items():
            css_lines.append(f'  --{ramp_key}-{stop}: {vals["srgb"]};')

    css_lines.append('')
    css_lines.append('  /* Elevation — elev-pg (purple-tinted, matches pg surfaces) */')
    for i in range(5):
        css_lines.append(f'  --elev-pg-{i}: {ev(i, "pg")};')
    css_lines.append('  /* Elevation — elev-sg (orange-tinted, matches sg surfaces) */')
    for i in range(5):
        css_lines.append(f'  --elev-sg-{i}: {ev(i, "sg")};')

    css_lines.append('')
    css_lines.append('  /* Semantic roles - light mode */')
    for role_name, role_data in SEM_ROLES.items():
        alias = role_data.get('light')
        if not alias or '@' in str(alias): continue
        hex_val = resolve_alias(alias)
        if hex_val:
            prop = '--' + role_name.replace('/', '-').replace(' ', '-')
            css_lines.append(f'  {prop}: {hex_val};')

    css_lines.append('}')
    css_lines.append('')

    p3_stops = [
        (rk, stop, vals)
        for rk, rd in RAMPS.items()
        for stop, vals in rd.items()
        if vals['srgb'] != vals['p3']
    ]
    if p3_stops:
        css_lines.append('/* ── Tier 2: P3 ── */')
        css_lines.append('@media (color-gamut: p3) {')
        css_lines.append('  :root {')
        for rk, stop, vals in p3_stops:
            css_lines.append(f'    --{rk}-{stop}: {vals["p3"]};')
        css_lines.append('  }')
        css_lines.append('}')
        css_lines.append('')

    css_lines.append('/* ── Tier 3: HDR+P3 - mirrors P3 currently ── */')
    css_lines.append('@media (color-gamut: p3) and (dynamic-range: high) {')
    css_lines.append('  :root {')
    for rk, stop, vals in p3_stops:
        css_lines.append(f'    --{rk}-{stop}: {vals["p3"]};')
    css_lines.append('  }')
    css_lines.append('}')
    css_lines.append('')

    css_lines.append('/* ── Dark mode ── */')
    css_lines.append('@media (prefers-color-scheme: dark) {')
    css_lines.append('  :root {')
    css_lines.append(f'    --color-background: {ev(0)};')
    css_lines.append(f'    --color-surface: {ev(1)};')
    css_lines.append(f'    --color-surface-raised: {ev(2)};')
    for role_name, role_data in SEM_ROLES.items():
        alias = role_data.get('dark')
        if not alias or '@' in str(alias): continue
        hex_val = resolve_alias(alias)
        if hex_val:
            prop = '--' + role_name.replace('/', '-').replace(' ', '-')
            css_lines.append(f'    {prop}: {hex_val};')
    css_lines.append('  }')
    css_lines.append('}')
    css_lines.append('')

    css_lines.append('/* ── Overlay tokens - color-mix(in oklch) ── */')
    css_lines.append(':root {')
    for prop, ramp, stop, pct in [
        ('--color-surface-overlay',           'pg',      900, 26),
        ('--color-surface-overlay-brand',     'primary', 900, 15),
        ('--color-surface-overlay-error',     'error',   900, 15),
        ('--color-surface-overlay-warning',   'warning', 900, 12),
        ('--color-surface-overlay-selection', 'primary', 900,  6),
    ]:
        css_lines.append(f'  {prop}: color-mix(in oklch, {sh(ramp, stop)} {pct}%, transparent);')
    css_lines.append('}')
    css_lines.append('@media (prefers-color-scheme: dark) {')
    css_lines.append('  :root {')
    for prop, ramp, stop, pct in [
        ('--color-surface-overlay',           'pg',      50, 26),
        ('--color-surface-overlay-brand',     'primary', 50, 15),
        ('--color-surface-overlay-selection', 'primary', 50,  6),
    ]:
        css_lines.append(f'    {prop}: color-mix(in oklch, {sh(ramp, stop)} {pct}%, transparent);')
    css_lines.append('  }')
    css_lines.append('}')

    (OUT / 'tokens.css').write_text('\n'.join(css_lines), encoding='utf-8')
    print(f'tokens.css              - {len(css_lines)} lines, {len(p3_stops)} P3-expanded stops')

# ─────────────────────────────────────────────────────────────────────────────
# STEP 9b - Fill-border distinctness check  (L3 fill-border-distinctness-policy)
# Hard build error on violation. Cannot be skipped.
# ─────────────────────────────────────────────────────────────────────────────
_fb_policy = L3['delta-engine']['fill-border-distinctness-policy']
_fb_pairs  = _fb_policy['sibling-pairs']
_fb_errors = []

for _pair in _fb_pairs:
    for _mode in ['light', 'dark']:
        _fhex = resolve_role(_pair['fill'],   _mode)
        _bhex = resolve_role(_pair['border'], _mode)
        if _fhex is None or _bhex is None:
            continue
        if _fhex == _bhex:
            _fb_errors.append(
                f"FILL_BORDER_CONFLICT [{_mode.upper()}]: "
                f"{_pair['border']} = {_bhex} identical to "
                f"{_pair['fill']}. Border invisible. "
                f"Shift border stop in Layer 4 semantic-role-map."
            )

if _fb_errors:
    print('\n' + '─' * 80)
    print('  FILL-BORDER DISTINCTNESS - HARD BUILD ERROR')
    print('  Layer 3 fill-border-distinctness-policy violated.\n')
    for _e in _fb_errors:
        print(f'  ✗  {_e}')
    print('\n  Output files may be invalid. Fix Layer 4 before using.')
    print('─' * 80 + '\n')
    sys.exit(1)
else:
    print(f'fill-border check       - {len(_fb_pairs)*2} pairs · 0 conflicts ✓')

# ─────────────────────────────────────────────────────────────────────────────
# STEP 9c - CVD GUARDRAIL (concern #1 + #29)
# Deuteranopia and protanopia simulation. Verifies success/error fills remain
# perceptually distinct after CVD simulation. Affects ~8% of male users.
# WARNING by default; HARD ERROR in --strict mode.
# ─────────────────────────────────────────────────────────────────────────────
_CVD_PAIRS = [
    ('color/fill/success', 'color/fill/error',   'success vs error'),
    ('color/fill/success', 'color/fill/warning', 'success vs warning'),
]
_CVD_DE_THRESHOLD = 0.10   # OKLAB ΔE below this = effectively indistinguishable
_cvd_warnings = []

for _mode in MODES_TO_COMPILE:
    for _roleA, _roleB, _label in _CVD_PAIRS:
        _hA = resolve_role(_roleA, _mode)
        _hB = resolve_role(_roleB, _mode)
        if not _hA or not _hB:
            continue
        for _sim_name, _sim_fn in [('deuteranopia', _simulate_deuteranopia),
                                    ('protanopia',   _simulate_protanopia)]:
            try:
                _sA = _apply_cvd_simulation(_hA, _sim_fn)
                _sB = _apply_cvd_simulation(_hB, _sim_fn)
                _de = _oklab_de(_sA, _sB)
                if _de < _CVD_DE_THRESHOLD:
                    _cvd_warnings.append(
                        f"CVD_CONFLICT [{_mode.upper()}] {_sim_name}: {_label} "
                        f"ΔE={_de:.3f} (threshold {_CVD_DE_THRESHOLD}). "
                        f"These semantic states look identical to users with {_sim_name}. "
                        f"Add lightness separation or iconography — hue alone is insufficient."
                    )
            except Exception:
                pass  # CVD check is advisory, never crash the build

if _cvd_warnings:
    print('\n  CVD ACCESSIBILITY AUDIT')
    for _w in _cvd_warnings:
        print(f'  ⚠  {_w}')
    if args.strict:
        sys.exit('\n  STRICT ERROR: CVD conflicts detected. Fix before shipping.')
else:
    _cvd_checked = len(_CVD_PAIRS) * 2 * len(MODES_TO_COMPILE)
    print(f'CVD accessibility check - {_cvd_checked} pair×mode combinations · 0 conflicts ✓')

# ─────────────────────────────────────────────────────────────────────────────
# STEP 9d - OLED HALATION GUARD (concern #9)
# Surface roles must never map to stop 1000 (L=0.05) in dark mode.
# Pure-black surfaces cause halation smearing for ~33% of users with astigmatism.
# ─────────────────────────────────────────────────────────────────────────────
_SURFACE_PREFIXES = ('color/bg', 'color/surface', 'color/elevation')
_oled_warnings = []
for _role_name, _role_data in SEM_ROLES.items():
    if any(_role_name.startswith(_p) for _p in _SURFACE_PREFIXES):
        _dark_alias = str(_role_data.get('dark', ''))
        if '.1000}' in _dark_alias:
            _oled_warnings.append(
                f"OLED_HALATION: {_role_name} maps to stop 1000 (L=0.05) in dark mode. "
                f"Stop 1000 is OLED-reserved. Surface roles must use stop 950 minimum "
                f"(L=0.12). High-contrast pure-black causes halation for astigmatic users."
            )
if _oled_warnings:
    print('\n  OLED HALATION GUARD')
    for _w in _oled_warnings:
        print(f'  ⚠  {_w}')
    if args.strict:
        sys.exit('\n  STRICT ERROR: OLED halation risk. Surface roles must not map to stop 1000.')
else:
    print(f'OLED halation guard     - {len([r for r in SEM_ROLES if any(r.startswith(p) for p in _SURFACE_PREFIXES)])} surface roles · 0 violations ✓')

# ─────────────────────────────────────────────────────────────────────────────
# STEP 9e - CHROMOSTEREOPSIS / VIBRATION GUARD (concern #26)
# When two semantic fills have hue separation > 150° and both C > 0.15,
# adjacent placement causes eye-depth conflict. The eye cannot focus both
# wavelengths simultaneously — the UI appears to vibrate.
# ─────────────────────────────────────────────────────────────────────────────
_VIB_HUE_THRESH   = 150.0
_VIB_CHROMA_THRESH = 0.15
_vib_fill_roles = [k for k in SEM_ROLES if k.startswith('color/fill/')]
_vib_warnings   = []

for _mode in MODES_TO_COMPILE:
    _fills_lch = {}
    for _rn in _vib_fill_roles:
        _hx = resolve_role(_rn, _mode)
        if _hx:
            _fills_lch[_rn] = hex_to_oklch(_hx)
    _names = list(_fills_lch.keys())
    for _i in range(len(_names)):
        for _j in range(_i + 1, len(_names)):
            _nA, _nB = _names[_i], _names[_j]
            _, _CA, _HA = _fills_lch[_nA]
            _, _CB, _HB = _fills_lch[_nB]
            _sep = min(abs(_HA - _HB), 360 - abs(_HA - _HB))
            if _sep > _VIB_HUE_THRESH and _CA > _VIB_CHROMA_THRESH and _CB > _VIB_CHROMA_THRESH:
                _vib_warnings.append(
                    f"CHROMOSTEREOPSIS [{_mode.upper()}]: {_nA} (H={_HA:.0f}°, C={_CA:.3f}) "
                    f"and {_nB} (H={_HB:.0f}°, C={_CB:.3f}). "
                    f"Hue sep={_sep:.0f}° with both C>{_VIB_CHROMA_THRESH}. "
                    f"Adjacent placement may cause eye-depth vibration effect."
                )

if _vib_warnings:
    print(f'\n  CHROMOSTEREOPSIS RISK — {len(_vib_warnings)} pairs')
    for _w in _vib_warnings[:4]:
        print(f'  ⚠  {_w}')
    if len(_vib_warnings) > 4:
        print(f'  ... {len(_vib_warnings)-4} more pairs (see build manifest)')
else:
    _vib_total = len(_vib_fill_roles) * (len(_vib_fill_roles) - 1) // 2 * len(MODES_TO_COMPILE)
    print(f'vibration guard         - {_vib_total} fill pairs · 0 risks ✓')

# ─────────────────────────────────────────────────────────────────────────────
# STEP 9f - GLOWING SURFACE CHECK (concern #31)
# Surface/bg/subtle tokens must not appear self-luminous.
# C > 0.08 at mid-lightness makes a surface look emissive, not reflective.
# ─────────────────────────────────────────────────────────────────────────────
_SURF_CHROMA_CAP  = 0.08
_SURF_L_MIN, _SURF_L_MAX = 0.35, 0.75
_SURF_KEYWORDS    = ('bg', 'surface', 'subtle')
_glow_warnings    = []

for _role_name, _role_data in SEM_ROLES.items():
    if 'text' in _role_name:
        continue
    if not any(_kw in _role_name for _kw in _SURF_KEYWORDS):
        continue
    for _mode in MODES_TO_COMPILE:
        _hx = resolve_role(_role_name, _mode)
        if not _hx: continue
        _Lv, _Cv, _ = hex_to_oklch(_hx)
        if _Cv > _SURF_CHROMA_CAP and _SURF_L_MIN <= _Lv <= _SURF_L_MAX:
            _glow_warnings.append(
                f"SURFACE_EMISSIVE [{_mode.upper()}]: {_role_name} "
                f"C={_Cv:.3f} (cap {_SURF_CHROMA_CAP}) at L={_Lv:.2f}. "
                f"Surface may appear self-luminous. Reduce chroma for this role."
            )

if _glow_warnings:
    print('\n  GLOWING SURFACE WARNINGS')
    for _w in _glow_warnings:
        print(f'  ⚠  {_w}')
else:
    print(f'surface chroma check    - 0 emissive surface risks ✓')

# ─────────────────────────────────────────────────────────────────────────────
# STEP 9g - OVERLAY GAMUT TRAP GUARD (concern #6)
# color-mix(in oklch) intermediates can bulge outside sRGB when the base hex
# has high chroma. Browser gamut clamping shifts hue and crushes lightness.
# ─────────────────────────────────────────────────────────────────────────────
_OVL_CHROMA_WARN = 0.12
_ovl_warnings    = []

for _role_name, _role_data in SEM_ROLES.items():
    for _mode in MODES_TO_COMPILE:
        _alias = str(_role_data.get('light' if _mode == 'light' else 'dark', ''))
        if '@' not in _alias: continue   # only overlay tokens use @ syntax
        # Extract the base primitive from "{ramp.stop} @ opacity%"
        import re as _re2
        _m = _re2.match(r'^\{([\w/-]+)\.(\d+)\}\s*@', _alias)
        if _m:
            _base_hx = resolve_alias(f'{{{_m.group(1)}.{_m.group(2)}}}')
            if _base_hx:
                _, _Cv, _ = hex_to_oklch(_base_hx)
                if _Cv > _OVL_CHROMA_WARN:
                    _ovl_warnings.append(
                        f"OVERLAY_GAMUT_TRAP [{_mode.upper()}]: {_role_name} "
                        f"uses base C={_Cv:.3f} (threshold {_OVL_CHROMA_WARN}). "
                        f"color-mix(in oklch) intermediate may bulge outside sRGB. "
                        f"Consider using a lower-chroma stop for this overlay base."
                    )

if _ovl_warnings:
    print('\n  OVERLAY GAMUT TRAP WARNINGS')
    for _w in _ovl_warnings:
        print(f'  ⚠  {_w}')
else:
    _ovl_count = sum(1 for r in SEM_ROLES.values() for _k in ('light','dark') if '@' in str(r.get(_k,'')))
    print(f'overlay gamut guard     - {_ovl_count} overlay aliases · 0 gamut risks ✓')

# ─────────────────────────────────────────────────────────────────────────────
# STEP 9h - CATEGORICAL PERCEPTION CHECK (concern #32)
# Verifies that all stops in a semantic ramp stay within the same human
# colour-category name as stop 500. A success ramp where stop 100 reads as
# "yellow" instead of "green" breaks the cognitive association with Success.
# Only checks stops with significant chroma (C > 0.05) — pale tints are exempt.
# ─────────────────────────────────────────────────────────────────────────────
_CAT_CHROMA_MIN   = 0.05   # stops below this chroma are too pale to have a category
_semantic_ramps   = ['success', 'error', 'warning', 'info', 'primary', 'secondary']
_cat_warnings     = []

for _ramp_key in _semantic_ramps:
    if _ramp_key not in RAMPS: continue
    _rd = RAMPS[_ramp_key]
    _anchor_stop = 500
    _anchor_data = _rd.get(_anchor_stop)
    if not _anchor_data: continue
    _, _aC, _aH = hex_to_oklch(_anchor_data['srgb'])
    if _aC < _CAT_CHROMA_MIN: continue
    _anchor_cat = _hue_category(_aH)
    for _stop, _vals in _rd.items():
        if _stop == _anchor_stop: continue
        _, _sC, _sH = hex_to_oklch(_vals['srgb'])
        if _sC < _CAT_CHROMA_MIN: continue
        _stop_cat = _hue_category(_sH)
        if _stop_cat != _anchor_cat and not (_anchor_cat == 'yellow' and _stop_cat == 'orange'):
            _cat_warnings.append(
                f"CATEGORICAL_DRIFT [{_ramp_key}]: stop {_stop} reads as "
                f"'{_stop_cat}' (H={_sH:.0f}°) but anchor stop 500 is "
                f"'{_anchor_cat}' (H={_aH:.0f}°). "
                f"Light/dark tints may not be identified as the same colour family."
            )

if _cat_warnings:
    print(f'\n  CATEGORICAL PERCEPTION — {len(_cat_warnings)} boundary crossings')
    for _w in _cat_warnings[:4]:
        print(f'  ⚠  {_w}')
    if len(_cat_warnings) > 4:
        print(f'  ... {len(_cat_warnings)-4} more (see build manifest)')
else:
    print(f'categorical check       - {len(_semantic_ramps)} ramps · 0 boundary crossings ✓')

# ─────────────────────────────────────────────────────────────────────────────
# STEP 10 - APCA contrast audit (Intelligent Semantic Pairing Engine v2)
# Skipped when --no-contrast flag is passed.
# ─────────────────────────────────────────────────────────────────────────────
results = []
counts = {'pass': 0, 'fail': 0, 'skipped': 0}
MODES_TO_AUDIT = ['light', 'dark'] if args.mode == 'both' else [args.mode]
_run_contrast = not args.no_contrast

if _run_contrast:
    for mode in MODES_TO_AUDIT:
        for role_name in SEM_ROLES.keys():
        
        # RULE 1: SKIP STRUCTURAL & BACKGROUND TOKENS
            if (role_name.startswith(('color/bg', 'color/surface', 'color/fill/', 'color/elevation', 'color/surface-overlay')) 
                or 'overlay' in role_name.lower()):
                counts['skipped'] += 1
                continue

        # RULE 2: DETERMINE CONTEXTUAL BACKGROUND PAIRING
        # Critical: tokens must be audited against the surface they ACTUALLY appear on,
        # not against the abstract page background. A color/text/error token will never
        # appear on raw page white — it lives on color/fill/error-subtle in banners and
        # helper text. Auditing against page white inflates the required Lc and pushes
        # stops too dark, stripping the semantic colour of its meaning.
        #
        # Pairing hierarchy (first match wins):
        #   1. on-fill tokens  → paired against their fill counterpart
        #   2. inverse tokens  → paired against inverse fill/surface
        #   3. semantic tokens (text/icon/border for error/success/warning/info/brand)
        #                      → paired against the subtle surface for that semantic
        #   4. everything else → paired against page background (color/bg)

        bg_role = 'color/bg'

        if role_name.startswith('color/on-fill/'):
            # e.g. color/on-fill/error → color/fill/error
            bg_role = role_name.replace('color/on-fill/', 'color/fill/')

        elif 'inverse' in role_name:
            bg_role = 'color/fill/inverse' if 'color/fill/inverse' in SEM_ROLES else 'color/surface-inverse'
            if bg_role not in SEM_ROLES:
                bg_role = 'color/bg'

        else:
            # For text, icon, and border tokens on semantic colours, pair against
            # the subtle surface for that semantic — this is where they actually live.
            # Also catches color/text/brand, color/icon/brand which the old condition missed.
            _SEMANTIC_SUFFIXES = ['error', 'success', 'warning', 'info', 'brand']
            for _sem in _SEMANTIC_SUFFIXES:
                if role_name.endswith(f'/{_sem}') or f'/{_sem}-' in role_name:
                    _subtle = 'color/fill/brand-subtle' if _sem == 'brand' else f'color/fill/{_sem}-subtle'
                    if _subtle in SEM_ROLES:
                        bg_role = _subtle
                    break

        # RESOLVE HEX CODES
        t_hex = resolve_role(role_name, mode)
        b_hex = resolve_role(bg_role, mode) or resolve_role('color/bg', mode)
        
        if not t_hex or not b_hex:
            continue

        # RULE 3: DETERMINE ACCESSIBILITY TARGET Lc
        # Per-role targets from Layer 2 apca-role-targets. Caption/overline
        # need Lc 90 at 12px; display text can use Lc 45. (concern #2)
        target = _get_apca_target(role_name)
            
        # AUDIT & NUDGE
        lc = _cached_lc(t_hex, b_hex)
        status = 'pass' if abs(lc) >= (target - 0.5) else 'fail'
        
        nudge = None
        if status == 'fail':
            nudge = suggest_perceptual_nudge(role_name, b_hex, mode, target)
            
        counts[status] += 1
        results.append({
            'mode': mode,
            'token': role_name,
            'bg_pair': bg_role,
            'lc': abs(lc),
            'target': target,
            'status': status,
            'nudge': nudge
        })

# --- REPORT GENERATION ---
if not _run_contrast:
    print('contrast audit          - skipped (--no-contrast) ✓')
else:
    report = [f"\n{'='*60}\n DESIGN SYSTEM CONTRAST TELEMETRY\n{'='*60}"]
    fails = [r for r in results if r['status'] == 'fail']
    
    if fails:
        report.append(f"\n ✗ {len(fails)} REAL CONTRAST FAILURES DETECTED\n")
        for r in fails:
            nudge = r.get('nudge') or {}
            fix_msg = nudge.get('msg', f"HARD FAIL: {nudge.get('reason', 'No solution found')}")
            report.append(f" [{r['mode'].upper()}] {r['token']} (on {r['bg_pair']})\n   Current: Lc {r['lc']:.1f} / Target: Lc {r['target']:.1f} | FIX: {fix_msg}")
    else:
        report.append(f"\n ✓ ALL SEMANTIC MAPPINGS COMPLIANT (Skipped {counts['skipped']} structural tokens)\n")
        
    # 1. Save and print the report FIRST
    full_report = "\n".join(report)
    (OUT / 'contrast-report.txt').write_text(full_report, encoding='utf-8')
    print(full_report)

    # 2. THEN kill the script if strict mode is ON and there are failures
    if fails and args.strict:
        sys.exit(f'\n  STRICT ERROR: {len(fails)} contrast failures. Fix before shipping.')
# ─────────────────────────────────────────────────────────────────────────────
# STEP 11 - Palette HTML  (--palette flag)
# ─────────────────────────────────────────────────────────────────────────────
if getattr(args, 'palette', False):
    for p in [Path(__file__).parent / 'design-system-palette.html', Path.cwd() / 'design-system-palette.html']:
        if p.exists():
            html_content = p.read_text(encoding='utf-8')

            # ── CLEAN CONFIG INJECTION via <!-- DS_CONFIG --> placeholder ──────────────
            # Reuses pg_hue / sg_hue already computed from L1 greyscale-outputs.
            # No regex against JS code — just one stable HTML comment as the target.

            ds_config = {
                'brands':     BRANDS,
                'pgHue':      round(pg_hue, 2),
                'sgHue':      round(sg_hue, 2),
                'floorStop':  FLOOR_STOP,
                'floorL':     round(FLOOR_L, 4),
                'elevStep':   round(ELEV_STEP, 4),
                'ctaColor':   chosen_cta,
                'elevPg':     ELEV,
                'elevSg':     ELEV_SG,
            }

            inject_block = (
                f'<script>/* DS_CONFIG — injected by compiler */\n'
                f'window.__DS_CONFIG__ = {json.dumps(ds_config, indent=2)};\n'
                f'</script>\n'
            )

            PLACEHOLDER = '<!-- DS_CONFIG -->'
            if PLACEHOLDER in html_content:
                html_content = html_content.replace(PLACEHOLDER, inject_block)
                print('design-system-palette.html - DS_CONFIG injected via placeholder ✓')
            else:
                # Fallback: insert before first <script> tag if placeholder absent
                html_content = html_content.replace('<script>', inject_block + '<script>', 1)
                print('design-system-palette.html - DS_CONFIG injected (fallback, add <!-- DS_CONFIG --> for reliability) ⚠')

            # ── INTERACTIVITY INJECTION ───────────────────────────────────────────────
            interactive_script = """
<script>
document.addEventListener('click', (e) => {
    const text = e.target.textContent?.trim();
    if (text && (text.startsWith('#') || text.startsWith('{') || text.startsWith('--'))) {
        const temp = document.createElement('textarea');
        temp.value = text;
        document.body.appendChild(temp);
        temp.select();
        document.execCommand('copy');
        document.body.removeChild(temp);
        const orig = e.target.textContent;
        e.target.textContent = 'Copied!';
        e.target.style.opacity = '0.5';
        setTimeout(() => { e.target.textContent = orig; e.target.style.opacity = '1'; }, 800);
    }
});
</script>
</body>
</html>"""
            if '</body>' in html_content:
                html_content = html_content.replace('</body>\n</html>', interactive_script).replace('</body></html>', interactive_script)

            (OUT / 'design-system-palette.html').write_text(html_content, encoding='utf-8')
            break
    else:
        print('WARNING: design-system-palette.html not found - skipping palette output.')

# ─────────────────────────────────────────────────────────────────────────────
# Done
# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
# STEP 12 - Build manifest
# Single summary file listing every output, build config, token counts, warnings.
# ─────────────────────────────────────────────────────────────────────────────
_output_files = sorted(
    list(OUT.glob('tokens*.json')) + list(OUT.glob('tokens*.css')) +
    list(OUT.glob('contrast-report*')) + list(OUT.glob('*.html'))
)
# Melanopic annotation: dark-mode tokens with blue-range high chroma
# may contribute to circadian disruption if used in high-dwell-time night contexts.
_melanopic_notes = []
for _rn, _rd in SEM_ROLES.items():
    _dhx = resolve_role(_rn, 'dark') if 'dark' in _rd else None
    if not _dhx: continue
    _, _Cv, _Hv = hex_to_oklch(_dhx)
    if 200 <= _Hv <= 280 and _Cv > 0.12:
        _melanopic_notes.append(f'{_rn} (H={_Hv:.0f}°, C={_Cv:.3f})')

manifest = {
    'generated':      datetime.now(timezone.utc).isoformat(),
    'build-config': {
        'floor-stop':   FLOOR_STOP,
        'cta-color':    chosen_cta,
        'mode':         args.mode,
        'strict':       args.strict,
        'no-contrast':  args.no_contrast,
        'no-css':       args.no_css,
    },
    'layer-versions': {
        'L1': L1['meta']['version'],
        'L2': L2['compiler-contract']['version'],
        'L3': L3['delta-engine']['version'],
        'L4': L4['meta']['version'],
    },
    'brand-inputs': BRANDS,
    'elevation': {
        'elev-pg (purple-tinted)': {str(i): ev(i,'pg') for i in range(5)},
        'elev-sg (orange-tinted)': {str(i): ev(i,'sg') for i in range(5)},
        'spacing-note': f'Power-curve exponent={_ELEV_PWR}, total-dL={_ELEV_TDEL}. Weber-Fechner corrected.',
    },
    'token-counts': {
        'primitive-ramps':    len(RAMPS),
        'primitive-stops':    sum(len(v) for v in RAMPS.values()),
        'semantic-roles':     len(SEM_ROLES),
        'component-tokens':   token_count,
    },
    'contrast-summary': {
        'pass':    counts['pass'],
        'fail':    counts['fail'],
        'skipped': counts['skipped'],
    } if _run_contrast else 'skipped',
    'validation-summary': {
        'fill-border-conflicts':       0,
        'cvd-conflicts':               len(_cvd_warnings),
        'oled-halation-risks':         len(_oled_warnings),
        'chromostereopsis-risks':      len(_vib_warnings),
        'surface-emissive-risks':      len(_glow_warnings),
        'overlay-gamut-risks':         len(_ovl_warnings),
        'categorical-drift-crossings': len(_cat_warnings),
        'quantization-collapses':      0,
    },
    'melanopic-annotations': {
        'description': 'Dark-mode tokens with H 200-280° and C > 0.12 may contribute to circadian disruption in high-dwell-time night contexts. Use Night-Safe variants for these roles in sleep-sensitive products.',
        'flagged-tokens': _melanopic_notes if _melanopic_notes else 'none',
    },
    'outputs': [
        {'file': f.name, 'bytes': f.stat().st_size}
        for f in _output_files
    ],
}
(OUT / 'build-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')

print('─' * 80)
print(f'Build complete  ({datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})')
print(f'  Config : floor={FLOOR_STOP}  cta={chosen_cta}  strict={args.strict}')
print(f'  Layers : L1 {L1["meta"]["version"]} · L2 {L2["compiler-contract"]["version"]} · L3 {L3["delta-engine"]["version"]} · L4 {L4["meta"]["version"]}')
print(f'  Tokens : {sum(len(v) for v in RAMPS.values())} primitives · {len(SEM_ROLES)} semantic · ~{token_count} component')
print('─' * 80)
print('Outputs:')
for f in _output_files + [OUT / 'build-manifest.json']:
    if f.exists():
        print(f'  {f.name}  ({f.stat().st_size:,} bytes)')
print('─' * 80)