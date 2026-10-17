import json, math, sys
from pathlib import Path

# Setup paths and environment
sys.argv = ['design_system_compiler.py', '--floor-stop', '950', '--cta-color', 'primary', '--no-css', '--no-contrast']
sys.path.append(r'C:\Users\austi\OneDrive\Documents\Compiler\Design-system')
from design_system_compiler import build_ramp, hex_to_oklch, gamut_safe_oklch_to_hex, _is_muddy_zone

sys.path.append(r'C:\Users\austi\tools')
from expanded_rigorous_benchmark import (
    hex_to_srgb, srgb_to_oklab, srgb_to_oklch, wcag_contrast, 
    apca_contrast, delta_e_oklab, simulate_deuteranopia, simulate_protanopia
)

sys.stdout.reconfigure(encoding='utf-8')

def simulate_tritanopia(r, g, b):
    # Vienot et al. 1999 Tritanopia
    from expanded_rigorous_benchmark import srgb_to_linear
    lr, lg, lb = srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b)
    r2 = 0.95014 * lr + 0.04986 * lg
    g2 = 0.00000 * lr + 0.43333 * lg + 0.56667 * lb
    b2 = 0.00000 * lr + 0.47500 * lg + 0.52500 * lb
    r2, g2, b2 = max(0, min(1, r2)), max(0, min(1, g2)), max(0, min(1, b2))
    return srgb_to_oklab(r2**(1/2.2), g2**(1/2.2), b2**(1/2.2))

ALL_STOPS = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950, 1000]

# ─────────────────────────────────────────────────────────────────────────────
# 1. REALITY PROJECT: SKILLBEEK PRODUCTION TOKEN AUDIT
# ─────────────────────────────────────────────────────────────────────────────
print("="*110)
print("PART 1: REAL-WORLD KNOCKED-REALITY AUDIT — SKILLBEEK SPREADSHEET TOKENS")
print("="*110)

with open(r'C:\Users\austi\OneDrive\Documents\Compiler\Design-system\Output\tokens-primitives.json', encoding='utf-8') as f:
    prims = json.load(f)['ramps']

skillbeek_pairs = [
    ('Badge Provisional Text/Bg', prims['primary']['700']['$value'], prims['primary']['100']['$value']),
    ('Success Chip Text/Bg',      prims['success']['700']['$value'], prims['success']['50']['$value']),
    ('Success Icon (Arch Role: {success.600})', prims['success']['600']['$value'], prims['pg']['50']['$value']),
    ('Success Icon (Raw Shortcut: {success.500})', prims['success']['500']['$value'], prims['pg']['50']['$value']),
    ('Error Chip Text/Bg',        prims['error']['700']['$value'],   prims['error']['50']['$value']),
    ('Error Icon on Surface',     prims['error']['500']['$value'],   prims['pg']['50']['$value']),
    ('Warning Chip Text/Bg',      prims['warning']['700']['$value'], prims['warning']['50']['$value']),
    ('Information Chip Text/Bg',  prims['info']['700']['$value'],    prims['info']['50']['$value']),
    ('Table Cell Text/Surface',   prims['pg']['900']['$value'],      prims['pg']['50']['$value']),
    ('Table Header Text/Bg',      prims['pg']['800']['$value'],      prims['pg']['100']['$value']),
    ('Active Row Selection',      prims['primary']['900']['$value'], prims['primary']['100']['$value']),
]

print(f'{"SKILLBEEK TOKEN PAIR":<28} | {"TEXT HEX":<8} | {"BG HEX":<8} | {"WCAG CR":<9} | {"APCA Lc":<9} | {"STATUS":<6}')
print("-"*110)

skillbeek_all_pass = True
for name, txt, bg in skillbeek_pairs:
    cr = wcag_contrast(txt, bg)
    lc = abs(apca_contrast(txt, bg))
    status = "PASS" if cr >= 4.5 and lc >= 60 else "FAIL"
    if status == "FAIL": skillbeek_all_pass = False
    print(f'{name:<28} | {txt:<8} | {bg:<8} | {cr:<9.2f} | {lc:<9.1f} | {status:<6}')

print(f"\nSKILLBEEK AUDIT VERDICT: {'100% BULLETPROOF PASS' if skillbeek_all_pass else 'FAILURES DETECTED'}")

# ─────────────────────────────────────────────────────────────────────────────
# 2. BRUTAL 8-ARCHETYPE STRESS MATRIX
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*110)
print("PART 2: EXCRUCIATING 8-ARCHETYPE STRESS MATRIX (EDGE CASES & REALITY KNOCKS)")
print("="*110)

BRUTAL_ARCHETYPES = {
    '1. Skillbeek Gold':      {'primary': '#B7812F', 'success': '#2FA836', 'error': '#BA3430'},
    '2. Neon Acid Yellow':    {'primary': '#FFE600', 'success': '#2FA836', 'error': '#BA3430'},
    '3. Mud Monster Olive':   {'primary': '#556B2F', 'success': '#2FA836', 'error': '#BA3430'},
    '4. Pitch Navy Abyss':    {'primary': '#0A192F', 'success': '#2FA836', 'error': '#BA3430'},
    '5. Faded Pastel Peach':  {'primary': '#FFD1BA', 'success': '#2FA836', 'error': '#BA3430'},
    '6. Same-Lum CVD Red/Grn':{'primary': '#4F46E5', 'success': '#008542', 'error': '#BA3430'},
    '7. Wide-Gamut P3 Cyan':  {'primary': '#00FFFF', 'success': '#2FA836', 'error': '#BA3430'},
    '8. Deep Plum Violet':    {'primary': '#4A0E4E', 'success': '#2FA836', 'error': '#BA3430'},
}

print(f'{"ARCHETYPE":<25} | {"QUANT COLLAPSE":<14} | {"MUDDY STOPS":<11} | {"DEUTAN dE":<10} | {"PROTAN dE":<10} | {"TRITAN dE":<10} | {"STATUS"}')
print("-"*110)

matrix_pass = True
for label, suite in BRUTAL_ARCHETYPES.items():
    ramps = {k: build_ramp(v) for k, v in suite.items()}
    primary_ramp = ramps['primary']
    
    # Check 1: 8-bit Quantization Collapses (Adjacent stops having same hex)
    collapses = []
    for i in range(len(ALL_STOPS)-1):
        s1, s2 = ALL_STOPS[i], ALL_STOPS[i+1]
        if primary_ramp[s1]['srgb'].upper() == primary_ramp[s2]['srgb'].upper():
            collapses.append(f"{s1}={s2}")
    quant_status = f"{len(collapses)} collapses" if collapses else "0 (Clean)"
    
    # Check 2: Muddy Zone Incursion (55 <= H <= 125 and 0.22 <= L <= 0.50 and C > 0.04)
    muddy_count = 0
    for s in ALL_STOPS:
        d = primary_ramp[s]
        if _is_muddy_zone(d['L'], d['C_srgb'], d['H']):
            muddy_count += 1
            
    # Check 3: CVD Separation (Success 500 vs Error 500)
    s_mid = ramps['success'][500]['srgb']
    e_mid = ramps['error'][500]['srgb']
    sd = simulate_deuteranopia(*hex_to_srgb(s_mid))
    ed = simulate_deuteranopia(*hex_to_srgb(e_mid))
    de_deut = math.sqrt((sd[0]-ed[0])**2 + (sd[1]-ed[1])**2 + (sd[2]-ed[2])**2)
    
    sp = simulate_protanopia(*hex_to_srgb(s_mid))
    ep = simulate_protanopia(*hex_to_srgb(e_mid))
    de_prot = math.sqrt((sp[0]-ep[0])**2 + (sp[1]-ep[1])**2 + (sp[2]-ep[2])**2)

    st = simulate_tritanopia(*hex_to_srgb(s_mid))
    et = simulate_tritanopia(*hex_to_srgb(e_mid))
    de_trit = math.sqrt((st[0]-et[0])**2 + (st[1]-et[1])**2 + (st[2]-et[2])**2)
    
    # Verdict
    is_safe = (len(collapses) == 0) and (muddy_count == 0) and (de_deut >= 0.08) and (de_prot >= 0.08) and (de_trit >= 0.08)
    if not is_safe: matrix_pass = False
    status_str = "PASS ✓" if is_safe else "FAIL ✗"
    
    print(f'{label:<25} | {quant_status:<14} | {muddy_count:<11} | {de_deut:<10.4f} | {de_prot:<10.4f} | {de_trit:<10.4f} | {status_str}')

print("="*110)
print(f"OVERALL STRESS MATRIX VERDICT: {'ALL 8 ARCHETYPES PASSED HARD GATES' if matrix_pass else 'FAILURES DETECTED'}")
