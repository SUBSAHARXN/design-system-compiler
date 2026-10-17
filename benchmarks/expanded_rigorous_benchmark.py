import json, math, sys, subprocess
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# ─────────────────────────────────────────────────────────────────────────────
# 1. COLOR SCIENCE & CONVERSIONS
# ─────────────────────────────────────────────────────────────────────────────
def hex_to_srgb(hex_str):
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 3:
        hex_str = ''.join(c*2 for c in hex_str)
    return [int(hex_str[i:i+2], 16) / 255.0 for i in (0, 2, 4)]

def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def srgb_to_oklab(r, g, b):
    lr, lg, lb = srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b)
    l = 0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb
    m = 0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb
    s = 0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb
    l_, m_, s_ = l**(1/3), m**(1/3), s**(1/3)
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b_ = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return L, a, b_

def srgb_to_oklch(r, g, b):
    L, a, b_ = srgb_to_oklab(r, g, b)
    C = math.sqrt(a * a + b_ * b_)
    H = math.degrees(math.atan2(b_, a)) % 360
    return L, C, H

def relative_luminance(r, g, b):
    lr, lg, lb = srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b)
    return 0.2126 * lr + 0.7152 * lg + 0.0722 * lb

def wcag_contrast(hex1, hex2):
    l1 = relative_luminance(*hex_to_srgb(hex1))
    l2 = relative_luminance(*hex_to_srgb(hex2))
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)

def apca_contrast(txt_hex, bg_hex):
    Ytxt = relative_luminance(*hex_to_srgb(txt_hex))
    Ybg = relative_luminance(*hex_to_srgb(bg_hex))
    if Ybg > Ytxt:
        return ((Ybg ** 0.56) - (Ytxt ** 0.62)) * 1.14 * 100
    else:
        return ((Ybg ** 0.65) - (Ytxt ** 0.55)) * 1.14 * 100

def delta_e_oklab(hex1, hex2):
    L1, a1, b1 = srgb_to_oklab(*hex_to_srgb(hex1))
    L2, a2, b2 = srgb_to_oklab(*hex_to_srgb(hex2))
    return math.sqrt((L1 - L2)**2 + (a1 - a2)**2 + (b1 - b2)**2)

def simulate_deuteranopia(r, g, b):
    lr, lg, lb = srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b)
    dr = 0.367322 * lr + 0.860646 * lg - 0.227968 * lb
    dg = 0.280085 * lr + 0.672501 * lg + 0.047413 * lb
    db = -0.011820 * lr + 0.042940 * lg + 0.968881 * lb
    dr, dg, db = max(0, min(1, dr)), max(0, min(1, dg)), max(0, min(1, db))
    ur, ug, ub = dr**(1/2.2), dg**(1/2.2), db**(1/2.2)
    return srgb_to_oklab(ur, ug, ub)

def simulate_protanopia(r, g, b):
    lr, lg, lb = srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b)
    r2 = 0.10889 * lr + 0.89111 * lg
    g2 = 0.10889 * lr + 0.89111 * lg
    b2 = lb
    r2, g2, b2 = max(0, min(1, r2)), max(0, min(1, g2)), max(0, min(1, b2))
    ur, ug, ub = r2**(1/2.2), g2**(1/2.2), b2**(1/2.2)
    return srgb_to_oklab(ur, ug, ub)

# ─────────────────────────────────────────────────────────────────────────────
# 2. SYSTEM RAMPS LOADER
# ─────────────────────────────────────────────────────────────────────────────
# 1. 4-Layer Compiler (Load generated tokens-primitives.json)
with open(r'C:\Users\austi\OneDrive\Documents\Compiler\Design-system\Output\tokens-primitives.json', encoding='utf-8') as f:
    comp_json = json.load(f)
compiler_ramps = {}
for name, key in [('amber', 'primary'), ('blue', 'info'), ('green', 'success'), ('red', 'error'), ('slate', 'pg')]:
    stops = comp_json['ramps'][key]
    sorted_stops = sorted(stops.keys(), key=lambda x: int(x))
    compiler_ramps[name] = [stops[k]['$value'] for k in sorted_stops]

# 2. Google Material Design 3 (M3 HCT)
google_m3_node = """
import { argbFromHex, themeFromSourceColor, hexFromArgb } from '@material/material-color-utilities';
const seeds = { amber: '#B7812F', blue: '#3758BF', green: '#2FA836', red: '#BA3430', slate: '#716978' };
const tones = [10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 99];
const out = {};
for (const [k, hex] of Object.entries(seeds)) {
  const theme = themeFromSourceColor(argbFromHex(hex));
  out[k] = tones.map(t => hexFromArgb(theme.palettes.primary.tone(t)));
}
console.log(JSON.stringify(out));
"""
google_ramps = json.loads(subprocess.check_output(['node', '--input-type=module', '-e', google_m3_node], cwd='C:/Users/austi/tools/radix_temp'))

# 3. Apple HIG
apple_ramps = {
    'amber': ['#FFF8E1', '#FFECB3', '#FFE082', '#FFD54F', '#FFCA28', '#FF9500', '#FF9F0A', '#F57C00', '#E65100', '#BF360C', '#3E1400'],
    'blue':  ['#E1F5FE', '#B3E5FC', '#81D4FA', '#4FC3F7', '#29B6F6', '#007AFF', '#0A84FF', '#0288D1', '#01579B', '#0A2540', '#030D18'],
    'green': ['#E8F5E9', '#C8E6C9', '#A5D6A7', '#81C784', '#66BB6A', '#34C759', '#30D158', '#388E3C', '#1B5E20', '#0D3813', '#041707'],
    'red':   ['#FFEBEE', '#FFCDD2', '#EF9A9A', '#E57373', '#EF5350', '#FF3B30', '#FF453A', '#D32F2F', '#B71C1C', '#5C0B0B', '#2B0404'],
    'slate': ['#F2F2F7', '#E5E5EA', '#D1D1D6', '#C7C7CC', '#AEAEB2', '#8E8E93', '#636366', '#48484A', '#3A3A3C', '#2C2C2E', '#1C1C1E']
}

# 4. Tailwind CSS
tw_node = """
const colors = require('C:/Users/austi/Skillbeek-App/node_modules/tailwindcss/colors');
console.log(JSON.stringify({
  amber: Object.values(colors.amber),
  blue: Object.values(colors.blue),
  green: Object.values(colors.emerald),
  red: Object.values(colors.red),
  slate: Object.values(colors.slate)
}));
"""
tw_ramps = json.loads(subprocess.check_output(['node', '-e', tw_node]))

# 5. Radix Colors
radix_node = """
const r = require('C:/Users/austi/tools/radix_temp/node_modules/@radix-ui/colors');
console.log(JSON.stringify({
  amber: Object.values(r.amber),
  blue: Object.values(r.blue),
  green: Object.values(r.green),
  red: Object.values(r.red),
  slate: Object.values(r.slate)
}));
"""
radix_ramps = json.loads(subprocess.check_output(['node', '-e', radix_node]))

# 6. IBM Carbon
carbon_node = """
const c = require('@carbon/colors');
const colors = c.colors || c;
console.log(JSON.stringify({
  amber: Object.values(colors.yellow),
  blue: Object.values(colors.blue),
  green: Object.values(colors.green),
  red: Object.values(colors.red),
  slate: Object.values(colors.gray)
}));
"""
carbon_ramps = json.loads(subprocess.check_output(['node', '-e', carbon_node], cwd='C:/Users/austi/tools/radix_temp'))

# 7. GitHub Primer
primer_path = r'C:\Users\austi\tools\radix_temp\node_modules\@primer\primitives\dist\figma\scales\light.json'
with open(primer_path, encoding='utf-8') as f:
    primer_items = json.load(f)

def rgb_to_hex(v):
    r = int(round(v['r'] * 255))
    g = int(round(v['g'] * 255))
    b = int(round(v['b'] * 255))
    return f"#{r:02x}{g:02x}{b:02x}"

primer_dict = {}
for it in primer_items:
    name = it['name']
    if 'base/color/' in name and isinstance(it.get('value'), dict) and 'r' in it['value']:
        parts = name.replace('base/color/', '').split('/')
        if len(parts) == 2:
            family, step = parts[0], int(parts[1])
            if family not in primer_dict:
                primer_dict[family] = {}
            primer_dict[family][step] = rgb_to_hex(it['value'])

primer_ramps = {
    'amber': [primer_dict['yellow'][i] for i in sorted(primer_dict.get('yellow', {}).keys())[:10]],
    'blue':  [primer_dict['blue'][i]   for i in sorted(primer_dict.get('blue', {}).keys())[:10]],
    'green': [primer_dict['green'][i]  for i in sorted(primer_dict.get('green', {}).keys())[:10]],
    'red':   [primer_dict['red'][i]    for i in sorted(primer_dict.get('red', {}).keys())[:10]],
    'slate': [primer_dict['neutral'][i] for i in sorted(primer_dict.get('neutral', {}).keys())[:10]]
}

# 8. Microsoft Fluent 2
fluent_ramps = {
    'amber': ['#FFFDF5', '#FFF7D6', '#FFF1B2', '#FFE680', '#FFD333', '#FCE100', '#EAA300', '#C27800', '#945300', '#663600', '#381B00'],
    'blue':  ['#EBF3FC', '#CFE4FA', '#B9D7F8', '#96C6FA', '#6CB8F6', '#479EF5', '#2886DE', '#115EA3', '#0F548C', '#0C3B5E', '#092C47'],
    'green': ['#F1FAF1', '#D6F0D7', '#B5E4B7', '#87D28B', '#54BC5A', '#107C41', '#0E703B', '#0C5E32', '#094927', '#06331B', '#031D0F'],
    'red':   ['#FDF3F4', '#F9D9DC', '#F4B9BE', '#EE8F98', '#E55F6D', '#D13438', '#B1272C', '#8F1D21', '#6E1317', '#4D0C0F', '#2C0507'],
    'slate': ['#FAFAFA', '#F5F5F5', '#EBEBEB', '#E0E0E0', '#D1D1D1', '#BDBDBD', '#8D8D8D', '#616161', '#424242', '#242424', '#141414']
}

# 9. Adobe Spectrum
spectrum_ramps = {
    'amber': ['#FFF8E6', '#FFECC2', '#FFDE99', '#FFCE6B', '#FFB833', '#F29423', '#E68619', '#CB6F10', '#A85408', '#803B00', '#4D2100'],
    'blue':  ['#F2F9FE', '#DDF0FD', '#BCE3FC', '#8ED0FA', '#52B6F6', '#2680EB', '#1473E6', '#0D66D0', '#095aba', '#06428c', '#032a59'],
    'green': ['#EDFAF5', '#D2F4E6', '#A7E8CE', '#6DD6B0', '#38C093', '#33AB84', '#268E6C', '#12805C', '#0C6647', '#074830', '#03291B'],
    'red':   ['#FFF0F1', '#FED8DA', '#FDB4B8', '#FB858C', '#F6535D', '#E34850', '#D7373F', '#C9252D', '#A9171E', '#7E0C12', '#4B0307'],
    'slate': ['#FFFFFF', '#F5F5F5', '#EAEAEA', '#E1E1E1', '#CACACA', '#B3B3B3', '#8E8E8E', '#6E6E6E', '#464646', '#222222', '#111111']
}

nine_systems = {
    '4-Layer Compiler': compiler_ramps,
    'IBM Carbon': carbon_ramps,
    'Adobe Spectrum': spectrum_ramps,
    'Google Material Design 3': google_ramps,
    'Tailwind CSS': tw_ramps,
    'Microsoft Fluent 2': fluent_ramps,
    'GitHub Primer': primer_ramps,
    'Apple HIG': apple_ramps,
    'Radix Colors': radix_ramps
}

# ─────────────────────────────────────────────────────────────────────────────
# 3. BENCHMARK TESTS (10 DIMENSIONS)
# ─────────────────────────────────────────────────────────────────────────────

# Standard 1: WCAG 2.2 AA Pass Rate
res_wcag = {}
for name, ramps in nine_systems.items():
    aa, total = 0, 0
    for h, hexes in ramps.items():
        n = len(hexes)
        p1 = wcag_contrast(hexes[-1], hexes[0])
        p2 = wcag_contrast(hexes[-2], hexes[1])
        p3 = wcag_contrast(hexes[-3], hexes[2])
        p4 = wcag_contrast('#ffffff', hexes[n//2])
        for r in [p1, p2, p3, p4]:
            total += 1
            if r >= 4.5: aa += 1
    res_wcag[name] = (aa / total) * 100

# Standard 2: APCA Mean Lc Readability
res_apca = {}
for name, ramps in nine_systems.items():
    lcs = [abs(apca_contrast(hexes[-2], hexes[1])) for h, hexes in ramps.items()]
    res_apca[name] = sum(lcs) / len(lcs)

# Standard 3: Perceptual OKLCH Linearity (Step dL StdDev, lower = better)
res_lin = {}
for name, ramps in nine_systems.items():
    stds = []
    for h, hexes in ramps.items():
        ls = [srgb_to_oklch(*hex_to_srgb(x))[0] for x in hexes]
        dls = [abs(ls[i] - ls[i+1]) for i in range(len(ls)-1)]
        m = sum(dls)/len(dls)
        stds.append(math.sqrt(sum((x - m)**2 for x in dls)/len(dls)))
    res_lin[name] = sum(stds)/len(stds)

# Standard 4: CVD Deuteranopia Separation (Success Green vs Error Red)
res_cvd_deut = {}
for name, ramps in nine_systems.items():
    g_mid = ramps['green'][len(ramps['green'])//2]
    r_mid = ramps['red'][len(ramps['red'])//2]
    gd = simulate_deuteranopia(*hex_to_srgb(g_mid))
    rd = simulate_deuteranopia(*hex_to_srgb(r_mid))
    res_cvd_deut[name] = math.sqrt((gd[0]-rd[0])**2 + (gd[1]-rd[1])**2 + (gd[2]-rd[2])**2)

# Standard 5: CVD Protanopia Separation (Success Green vs Error Red)
res_cvd_prot = {}
for name, ramps in nine_systems.items():
    g_mid = ramps['green'][len(ramps['green'])//2]
    r_mid = ramps['red'][len(ramps['red'])//2]
    gp = simulate_protanopia(*hex_to_srgb(g_mid))
    rp = simulate_protanopia(*hex_to_srgb(r_mid))
    res_cvd_prot[name] = math.sqrt((gp[0]-rp[0])**2 + (gp[1]-rp[1])**2 + (gp[2]-rp[2])**2)

# Innovative 6: OLED Glare / Photopic Halation Index (Ideal: 18.0:1)
floors = {
    '4-Layer Compiler': '#141216',  # 950 base surface stop (L=0.17)
    'Google Material Design 3': '#141218',
    'Apple HIG': '#000000',
    'Tailwind CSS': '#020617',
    'Radix Colors': '#111113',
    'IBM Carbon': '#161616',
    'GitHub Primer': '#0d1117',
    'Microsoft Fluent 2': '#141414',
    'Adobe Spectrum': '#111111'
}
res_glare = {name: wcag_contrast('#ffffff', floors[name]) for name in nine_systems}

# Innovative 7: Mud Resistance / Warm Chroma Retention in Mid-Darks (L in [0.25, 0.55])
res_warm_c = {}
for name, ramps in nine_systems.items():
    oklchs = [srgb_to_oklch(*hex_to_srgb(x)) for x in ramps['amber']]
    mid_dark = [o[1] for o in oklchs if 0.25 <= o[0] <= 0.55]
    res_warm_c[name] = sum(mid_dark)/len(mid_dark) if mid_dark else 0

# Innovative 8: Wide-Gamut Utilization (Peak Chroma)
res_peak_c = {}
for name, ramps in nine_systems.items():
    max_c = []
    for h, hexes in ramps.items():
        cs = [srgb_to_oklch(*hex_to_srgb(x))[1] for x in hexes]
        max_c.append(max(cs))
    res_peak_c[name] = sum(max_c)/len(max_c)

# Innovative 9: Interaction Hover State Uniformity (Delta-E target ~0.045)
res_hover_de = {}
for name, ramps in nine_systems.items():
    d_list = []
    for h, hexes in ramps.items():
        n = len(hexes)
        mid = n // 2
        if mid + 1 < n:
            d_list.append(delta_e_oklab(hexes[mid], hexes[mid+1]))
    res_hover_de[name] = sum(d_list) / len(d_list)

# Innovative 10: Step Contrast Monotonicity & Predictability (Variance of CR steps, lower = better)
res_step_mono = {}
for name, ramps in nine_systems.items():
    cr_stds = []
    for h, hexes in ramps.items():
        crs = [wcag_contrast(hexes[0], x) for x in hexes[1:]]
        dcrs = [crs[i+1] - crs[i] for i in range(len(crs)-1)]
        mean_d = sum(dcrs)/len(dcrs) if dcrs else 1
        cr_stds.append(math.sqrt(sum((x - mean_d)**2 for x in dcrs)/len(dcrs)) if dcrs else 0)
    res_step_mono[name] = sum(cr_stds)/len(cr_stds)

# ─────────────────────────────────────────────────────────────────────────────
# 4. COMPOSITE SCORING
# ─────────────────────────────────────────────────────────────────────────────
min_l, max_l = min(res_lin.values()), max(res_lin.values())
min_mono, max_mono = min(res_step_mono.values()), max(res_step_mono.values())

scores = {}
for name in nine_systems:
    s_wcag = res_wcag[name]
    s_apca = min(100.0, (res_apca[name] / 105.0) * 100.0)
    s_lin = (1.0 - (res_lin[name] - min_l) / (max_l - min_l)) * 100.0
    s_cvd_deut = min(100.0, (res_cvd_deut[name] / 0.08) * 100.0)
    s_cvd_prot = min(100.0, (res_cvd_prot[name] / 0.08) * 100.0)
    s_glare = max(0.0, 100.0 - abs(res_glare[name] - 18.2) * 20.0)
    s_warm_c = min(100.0, (res_warm_c[name] / 0.12) * 100.0)
    s_gamut = min(100.0, (res_peak_c[name] / 0.25) * 100.0)
    s_hover = max(0.0, 100.0 - abs(res_hover_de[name] - 0.045) * 1000.0)
    s_mono = (1.0 - (res_step_mono[name] - min_mono) / (max_mono - min_mono)) * 100.0

    # Weights:
    # 25% Core Accessibility (WCAG 12.5%, APCA 12.5%)
    # 20% Colorblind Inclusion (Deuteranopia 10%, Protanopia 10%)
    # 20% Visual Science & Uniformity (Linearity 10%, Step Predictability 10%)
    # 20% Visual Ergonomics & Mud Resistance (Glare 10%, Warm Chroma 10%)
    # 15% Interactive UI Physics (Hover Delta 7.5%, Gamut Utilization 7.5%)
    composite = (
        0.125 * s_wcag +
        0.125 * s_apca +
        0.100 * s_cvd_deut +
        0.100 * s_cvd_prot +
        0.100 * s_lin +
        0.100 * s_mono +
        0.100 * s_glare +
        0.100 * s_warm_c +
        0.075 * s_hover +
        0.075 * s_gamut
    )
    scores[name] = round(composite, 1)

sorted_ranks = sorted(scores.items(), key=lambda x: x[1], reverse=True)

print("="*125)
print("EXPANDED 9-SYSTEM WORLD DESIGN BENCHMARK (10 STANDARD & INNOVATIVE CRITERIA)")
print("="*125)
header = f'{"RANK":<4} | {"SYSTEM":<25} | {"SCORE":<6} | {"WCAG AA":<7} | {"APCA Lc":<7} | {"LINEAR":<7} | {"DEUTAN":<7} | {"PROTAN":<7} | {"GLARE":<7} | {"WARM C":<7}'
print(header)
print("-"*125)

for r, (name, sc) in enumerate(sorted_ranks, 1):
    print(f'{r:<4} | {name:<25} | {sc:<6.1f} | {res_wcag[name]:<6.1f}% | {res_apca[name]:<7.1f} | {res_lin[name]:<7.4f} | {res_cvd_deut[name]:<7.4f} | {res_cvd_prot[name]:<7.4f} | {res_glare[name]:<5.1f}:1 | {res_warm_c[name]:<7.4f}')

print("\n" + "="*125)
print("INDIVIDUAL DETAILED BENCHMARK BREAKDOWN")
print("="*125)
print(f'{"SYSTEM":<25} | {"PEAK GAMUT C":<12} | {"HOVER dE":<9} | {"CR MONO STD":<11}')
print("-"*65)
for name, _ in sorted_ranks:
    print(f'{name:<25} | {res_peak_c[name]:<12.4f} | {res_hover_de[name]:<9.4f} | {res_step_mono[name]:<11.4f}')
