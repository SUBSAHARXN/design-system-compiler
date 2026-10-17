import json, math, sys
from pathlib import Path

# Mock sys.argv before importing design_system_compiler
sys.argv = ['design_system_compiler.py', '--floor-stop', '950', '--cta-color', 'primary', '--no-css', '--no-contrast']
sys.path.append(r'C:\Users\austi\OneDrive\Documents\Compiler\Design-system')
from design_system_compiler import build_ramp, hex_to_oklch, gamut_safe_oklch_to_hex

from expanded_rigorous_benchmark import hex_to_srgb, srgb_to_oklab, srgb_to_oklch, wcag_contrast, apca_contrast, simulate_deuteranopia, simulate_protanopia

SEEDS_TO_TEST = {
    'Enterprise Amber': {'primary': '#B7812F', 'info': '#3758BF', 'success': '#2FA836', 'error': '#BA3430'},
    'Tech Indigo':     {'primary': '#6366F1', 'info': '#06B6D4', 'success': '#10B981', 'error': '#F43F5E'},
    'Biotech Emerald': {'primary': '#059669', 'info': '#2563EB', 'success': '#16A34A', 'error': '#DC2626'},
    'Coral Crimson':   {'primary': '#E11D48', 'info': '#0284C7', 'success': '#22C55E', 'error': '#D97706'}
}

ALL_STOPS = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950, 1000]

print("\n" + "="*105)
print("MULTI-SEED STABILITY & ROBUSTNESS TEST ACROSS 4 BRAND ARCHETYPES")
print("="*105)
print(f'{"BRAND SEED":<18} | {"WCAG AA":<8} | {"APCA Lc":<8} | {"LINEARITY":<10} | {"DEUTAN dE":<10} | {"PROTAN dE":<10} | {"CLIPPING":<9}')
print("-"*105)

for label, suite in SEEDS_TO_TEST.items():
    ramps = {k: build_ramp(v) for k, v in suite.items()}
    ramps['pg'] = build_ramp(suite['primary'], grey=True)
    
    # 1. WCAG AA Pass Rate
    aa, total = 0, 0
    for k, r in ramps.items():
        hexes = [r[s]['srgb'] for s in ALL_STOPS]
        n = len(hexes)
        p1 = wcag_contrast(hexes[-1], hexes[0])
        p2 = wcag_contrast(hexes[-2], hexes[1])
        p3 = wcag_contrast(hexes[-3], hexes[2])
        p4 = wcag_contrast('#ffffff', hexes[n//2])
        for cr in [p1, p2, p3, p4]:
            total += 1
            if cr >= 4.5: aa += 1
    wcag_pct = (aa / total) * 100

    # 2. APCA mean Lc
    lcs = [abs(apca_contrast(ramps[k][900]['srgb'], ramps[k][100]['srgb'])) for k in ramps]
    apca_mean = sum(lcs) / len(lcs)

    # 3. Linearity StdDev
    stds = []
    for k, r in ramps.items():
        ls = [r[s]['L'] for s in ALL_STOPS]
        dls = [abs(ls[i] - ls[i+1]) for i in range(len(ls)-1)]
        m = sum(dls)/len(dls)
        stds.append(math.sqrt(sum((x - m)**2 for x in dls)/len(dls)))
    lin_mean = sum(stds)/len(stds)

    # 4. CVD Separation (Success vs Error)
    s_mid = ramps['success'][500]['srgb']
    e_mid = ramps['error'][500]['srgb']
    sd = simulate_deuteranopia(*hex_to_srgb(s_mid))
    ed = simulate_deuteranopia(*hex_to_srgb(e_mid))
    de_d = math.sqrt((sd[0]-ed[0])**2 + (sd[1]-ed[1])**2 + (sd[2]-ed[2])**2)
    sp = simulate_protanopia(*hex_to_srgb(s_mid))
    ep = simulate_protanopia(*hex_to_srgb(e_mid))
    de_p = math.sqrt((sp[0]-ep[0])**2 + (sp[1]-ep[1])**2 + (sp[2]-ep[2])**2)

    # 5. Gamut Clipping Check (P3 vs sRGB delta)
    clipped_stops = 0
    total_stops = 0
    for k, r in ramps.items():
        for s in ALL_STOPS:
            total_stops += 1
            if r[s]['C_srgb'] < r[s]['C_p3'] * 0.70:
                clipped_stops += 1
    clip_rate = f"{clipped_stops}/{total_stops} ({clipped_stops*100/total_stops:.1f}%)"

    print(f'{label:<18} | {wcag_pct:<7.1f}% | {apca_mean:<8.1f} | {lin_mean:<10.4f} | {de_d:<10.4f} | {de_p:<10.4f} | {clip_rate:<9}')

print("="*105)
