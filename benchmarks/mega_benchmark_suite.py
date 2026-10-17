import json, math, sys, subprocess
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# --- Color Conversion Math ---
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
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)

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

# --- 1. Load 4-Layer Compiler ---
with open(r'C:\Users\austi\OneDrive\Documents\Compiler\Design-system\Output\tokens-primitives.json', encoding='utf-8') as f:
    comp_json = json.load(f)
compiler_ramps = {}
for name, key in [('amber', 'primary'), ('blue', 'info'), ('green', 'success'), ('red', 'error'), ('slate', 'pg')]:
    stops = comp_json['ramps'][key]
    sorted_stops = sorted(stops.keys(), key=lambda x: int(x))
    compiler_ramps[name] = [stops[k]['$value'] for k in sorted_stops]

# --- 2. Load Google M3 (HCT) ---
google_m3_node = """
import { argbFromHex, themeFromSourceColor, hexFromArgb } from '@material/material-color-utilities';
const seeds = { amber: '#B7812F', blue: '#3758BF', green: '#349024', red: '#BA3430', slate: '#716978' };
const tones = [10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 99];
const out = {};
for (const [k, hex] of Object.entries(seeds)) {
  const theme = themeFromSourceColor(argbFromHex(hex));
  out[k] = tones.map(t => hexFromArgb(theme.palettes.primary.tone(t)));
}
console.log(JSON.stringify(out));
"""
google_ramps = json.loads(subprocess.check_output(['node', '--input-type=module', '-e', google_m3_node], cwd='C:/Users/austi/tools/radix_temp'))

# --- 3. Apple HIG ---
apple_ramps = {
    'amber': ['#FFF8E1', '#FFECB3', '#FFE082', '#FFD54F', '#FFCA28', '#FF9500', '#FF9F0A', '#F57C00', '#E65100', '#BF360C', '#3E1400'],
    'blue':  ['#E1F5FE', '#B3E5FC', '#81D4FA', '#4FC3F7', '#29B6F6', '#007AFF', '#0A84FF', '#0288D1', '#01579B', '#0A2540', '#030D18'],
    'green': ['#E8F5E9', '#C8E6C9', '#A5D6A7', '#81C784', '#66BB6A', '#34C759', '#30D158', '#388E3C', '#1B5E20', '#0D3813', '#041707'],
    'red':   ['#FFEBEE', '#FFCDD2', '#EF9A9A', '#E57373', '#EF5350', '#FF3B30', '#FF453A', '#D32F2F', '#B71C1C', '#5C0B0B', '#2B0404'],
    'slate': ['#F2F2F7', '#E5E5EA', '#D1D1D6', '#C7C7CC', '#AEAEB2', '#8E8E93', '#636366', '#48484A', '#3A3A3C', '#2C2C2E', '#1C1C1E']
}

# --- 4. Tailwind CSS ---
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

# --- 5. Radix Colors ---
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

# --- 6. IBM Carbon (@carbon/colors) ---
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

# --- 7. GitHub Primer ---
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

# --- 8. Microsoft Fluent 2 ---
fluent_ramps = {
    'amber': ['#FFFDF5', '#FFF7D6', '#FFF1B2', '#FFE680', '#FFD333', '#FCE100', '#EAA300', '#C27800', '#945300', '#663600', '#381B00'],
    'blue':  ['#EBF3FC', '#CFE4FA', '#B9D7F8', '#96C6FA', '#6CB8F6', '#479EF5', '#2886DE', '#115EA3', '#0F548C', '#0C3B5E', '#092C47'],
    'green': ['#F1FAF1', '#D6F0D7', '#B5E4B7', '#87D28B', '#54BC5A', '#107C41', '#0E703B', '#0C5E32', '#094927', '#06331B', '#031D0F'],
    'red':   ['#FDF3F4', '#F9D9DC', '#F4B9BE', '#EE8F98', '#E55F6D', '#D13438', '#B1272C', '#8F1D21', '#6E1317', '#4D0C0F', '#2C0507'],
    'slate': ['#FAFAFA', '#F5F5F5', '#EBEBEB', '#E0E0E0', '#D1D1D1', '#BDBDBD', '#8D8D8D', '#616161', '#424242', '#242424', '#141414']
}

# --- 9. Adobe Spectrum / Leonardo ---
spectrum_ramps = {
    'amber': ['#FFF8E6', '#FFECC2', '#FFDE99', '#FFCE6B', '#FFB833', '#F29423', '#E68619', '#CB6F10', '#A85408', '#803B00', '#4D2100'],
    'blue':  ['#F2F9FE', '#DDF0FD', '#BCE3FC', '#8ED0FA', '#52B6F6', '#2680EB', '#1473E6', '#0D66D0', '#095aba', '#06428c', '#032a59'],
    'green': ['#EDFAF5', '#D2F4E6', '#A7E8CE', '#6DD6B0', '#38C093', '#33AB84', '#268E6C', '#12805C', '#0C6647', '#074830', '#03291B'],
    'red':   ['#FFF0F1', '#FED8DA', '#FDB4B8', '#FB858C', '#F6535D', '#E34850', '#D7373F', '#C9252D', '#A9171E', '#7E0C12', '#4B0307'],
    'slate': ['#FFFFFF', '#F5F5F5', '#EAEAEA', '#E1E1E1', '#CACACA', '#B3B3B3', '#8E8E8E', '#6E6E6E', '#464646', '#222222', '#111111']
}

nine_systems = {
    '4-Layer Compiler': compiler_ramps,
    'Google Material Design 3': google_ramps,
    'Apple HIG': apple_ramps,
    'Tailwind CSS': tw_ramps,
    'Radix Colors': radix_ramps,
    'IBM Carbon': carbon_ramps,
    'GitHub Primer': primer_ramps,
    'Microsoft Fluent 2': fluent_ramps,
    'Adobe Spectrum': spectrum_ramps
}

# --- RUN ALL 8 BENCHMARKS ---

# 1. Linearity StdDev
b1_res = {}
for name, ramps in nine_systems.items():
    stds = []
    for h, hexes in ramps.items():
        ls = [srgb_to_oklch(*hex_to_srgb(x))[0] for x in hexes]
        dls = [abs(ls[i] - ls[i+1]) for i in range(len(ls)-1)]
        m = sum(dls)/len(dls)
        stds.append(math.sqrt(sum((x - m)**2 for x in dls)/len(dls)))
    b1_res[name] = sum(stds)/len(stds)

# 2. WCAG 2.2 AA Pass Rate
b2_res = {}
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
    b2_res[name] = (aa / total) * 100

# 3. APCA Mean Lc
b3_res = {}
for name, ramps in nine_systems.items():
    lcs = [abs(apca_contrast(hexes[-2], hexes[1])) for h, hexes in ramps.items()]
    b3_res[name] = sum(lcs)/len(lcs)

# 4. Warm Chroma (Amber L in [0.25, 0.55])
b4_res = {}
for name, ramps in nine_systems.items():
    oklchs = [srgb_to_oklch(*hex_to_srgb(x)) for x in ramps['amber']]
    mid_dark = [o[1] for o in oklchs if 0.25 <= o[0] <= 0.55]
    b4_res[name] = sum(mid_dark)/len(mid_dark) if mid_dark else 0

# 5. CVD Deuteranopia Red-Green Separation (Higher = Safer)
b5_res = {}
for name, ramps in nine_systems.items():
    g_mid = ramps['green'][len(ramps['green'])//2]
    r_mid = ramps['red'][len(ramps['red'])//2]
    gd = simulate_deuteranopia(*hex_to_srgb(g_mid))
    rd = simulate_deuteranopia(*hex_to_srgb(r_mid))
    b5_res[name] = math.sqrt((gd[0]-rd[0])**2 + (gd[1]-rd[1])**2 + (gd[2]-rd[2])**2)

# 6. OLED Glare / Halation Index
floors = {
    '4-Layer Compiler': '#080503',
    'Google Material Design 3': '#141218',
    'Apple HIG': '#000000',
    'Tailwind CSS': '#020617',
    'Radix Colors': '#111113',
    'IBM Carbon': '#161616',
    'GitHub Primer': '#0d1117',
    'Microsoft Fluent 2': '#141414',
    'Adobe Spectrum': '#111111'
}
b6_res = {name: wcag_contrast('#ffffff', floors[name]) for name in nine_systems}

# 7. INNOVATIVE 3: Wide-Gamut P3 Chroma Headroom (Max Chroma utilized)
b7_res = {}
for name, ramps in nine_systems.items():
    max_c = []
    for h, hexes in ramps.items():
        cs = [srgb_to_oklch(*hex_to_srgb(x))[1] for x in hexes]
        max_c.append(max(cs))
    b7_res[name] = sum(max_c)/len(max_c)

# 8. INNOVATIVE 4: Interaction Hover Delta Distinguishability (Target: 0.03 - 0.06 delta-E)
# Measure delta-E between mid stop and mid+1 stop across ramps
b8_res = {}
for name, ramps in nine_systems.items():
    d_list = []
    for h, hexes in ramps.items():
        n = len(hexes)
        mid = n//2
        if mid + 1 < n:
            d_list.append(delta_e_oklab(hexes[mid], hexes[mid+1]))
    b8_res[name] = sum(d_list)/len(d_list)

# --- OVERALL SCORING & RANKING ---
# Normalization helper (0 to 100)
# Linearity: lower is better
min_l, max_l = min(b1_res.values()), max(b1_res.values())
# WCAG: higher is better
# APCA: higher is better
# Warm Chroma: higher is better
# CVD: higher is better
# Dark Glare: ideal is 18.0 (penalty for distance from 18.0)
# Hover delta: ideal is 0.045 (penalty for distance from 0.045)

scores = {}
for name in nine_systems:
    s_lin = (1.0 - (b1_res[name] - min_l) / (max_l - min_l)) * 100
    s_wcag = b2_res[name]
    s_apca = (b3_res[name] / 105.3) * 100
    s_chroma = (b4_res[name] / 0.1265) * 100
    s_cvd = (b5_res[name] / 0.0786) * 100
    # glare penalty (ideal 18.0)
    s_glare = max(0, 100 - abs(b6_res[name] - 18.0) * 20)
    # hover delta score (ideal 0.045)
    s_hover = max(0, 100 - abs(b8_res[name] - 0.045) * 1000)
    
    # Weighted composite:
    # Accessibility (WCAG + APCA): 30%
    # Science & Linearity: 20%
    # Aesthetics & Mud Resistance (Warm Chroma): 20%
    # Visual Ergonomics (CVD + Glare + Hover): 30%
    composite = (0.15 * s_wcag) + (0.15 * s_apca) + (0.20 * s_lin) + (0.20 * s_chroma) + (0.10 * s_cvd) + (0.10 * s_glare) + (0.10 * s_hover)
    scores[name] = round(composite, 1)

sorted_ranks = sorted(scores.items(), key=lambda x: x[1], reverse=True)

print(f'{"RANK":<4} | {"SYSTEM":<26} | {"SCORE":<6} | {"WCAG AA":<7} | {"APCA Lc":<7} | {"LINEARITY":<9} | {"WARM CHROMA":<11} | {"CVD DEUTAN":<10} | {"DARK GLARE":<10}')
print('-'*110)
for r, (name, sc) in enumerate(sorted_ranks, 1):
    print(f'{r:<4} | {name:<26} | {sc:<6.1f} | {b2_res[name]:<6.1f}% | {b3_res[name]:<7.1f} | {b1_res[name]:<9.4f} | {b4_res[name]:<11.4f} | {b5_res[name]:<10.4f} | {b6_res[name]:<10.1f}:1')
