import json
import math
from pathlib import Path
import expanded_rigorous_benchmark as erb

def hex_to_oklch(h):
    return erb.srgb_to_oklch(*erb.hex_to_srgb(h))

print("=" * 105)
print("PART 1: 7 FLAWS IN THE PREVIOUS BENCHMARK (expanded_rigorous_benchmark.py) + COMPILER AUDIT")
print("=" * 105)

m3_blue = erb.nine_systems["Google Material Design 3"]["blue"]
tw_blue = erb.nine_systems["Tailwind CSS"]["blue"]
our_blue = erb.nine_systems["4-Layer Compiler"]["blue"]

m3_L = [round(hex_to_oklch(h)[0], 3) for h in m3_blue]
tw_L = [round(hex_to_oklch(h)[0], 3) for h in tw_blue]
our_L = [round(hex_to_oklch(h)[0], 3) for h in our_blue]

print("\n[FLAW 1] Google M3 Tone Array is UPSIDE DOWN (Dark->Light instead of Light->Dark):")
print(f"  Google M3 Blue L* (idx 0..10): {m3_L}")
print(f"  Tailwind  Blue L* (idx 0..10): {tw_L}")
print(f"  4-Layer   Blue L* (idx 0..11): {our_L}")
m3_rev_ramps = {h: list(reversed(v)) for h, v in erb.nine_systems["Google Material Design 3"].items()}
cr_stds_m3_fixed = []
for h, hexes in m3_rev_ramps.items():
    crs = [erb.wcag_contrast(hexes[0], x) for x in hexes[1:]]
    dcrs = [crs[i+1] - crs[i] for i in range(len(crs)-1)]
    mean_d = sum(dcrs)/len(dcrs)
    cr_stds_m3_fixed.append(math.sqrt(sum((x - mean_d)**2 for x in dcrs)/len(dcrs)))
print(f"  -> M3 CR MONO STD when upside-down (buggy): {erb.res_step_mono['Google Material Design 3']:.4f} (ranked #1 on monotonicity!)")
print(f"  -> M3 CR MONO STD when oriented Light->Dark: {sum(cr_stds_m3_fixed)/len(cr_stds_m3_fixed):.4f}")

print("\n[FLAW 2] 12-Stop vs 11-Stop Midpoint Index Bias (hexes[n // 2] in WCAG Pair 4):")
print("  - 4-Layer Compiler & IBM Carbon have 12 stops -> n // 2 = index 6 (Stop 600 / Grade 60, L=0.39–0.52).")
print("  - Tailwind, Fluent 2, Apple HIG, Adobe Spectrum have 11 stops -> n // 2 = index 5 (Stop 500, L=0.55–0.68).")
print("  - Google M3 has 11 tones [99..10] -> n // 2 = index 5 (Tone 60, L=0.65), whereas M3's Primary role is Tone 40 (L=0.44)!")
for h, hexes in erb.nine_systems["4-Layer Compiler"].items():
    cr500 = erb.wcag_contrast('#ffffff', hexes[5])
    cr600 = erb.wcag_contrast('#ffffff', hexes[6])
    print(f"    4-Layer {h:<7}: Stop 500 ({hexes[5]}) CR={cr500:.2f} ({'PASS' if cr500>=4.5 else 'FAIL'}) | Stop 600 ({hexes[6]}) CR={cr600:.2f} ({'PASS' if cr600>=4.5 else 'FAIL'})")

print("\n[FLAW 3] Layer 3 Hover Engine Bug Uncovered in design_system_compiler.py (lines 976-982 & 1207-1235):")
with open("Output/tokens-component.json", encoding="utf-8") as f:
    comp_json = json.load(f)["components"]

delta_total = 0
delta_zero = 0
for cname, cdata in comp_json.items():
    def check_block(b):
        global delta_total, delta_zero
        for k, v in b.items():
            if not isinstance(v, dict): continue
            if "light" in v and isinstance(v["light"], dict) and v["light"].get("delta-resolved"):
                delta_total += 1
                if v["light"]["$value"] == v["light"]["base-hex"]:
                    delta_zero += 1
            else:
                check_block(v)
    check_block(cdata)

print(f"  - In Output/tokens-component.json: {delta_zero} out of {delta_total} delta-resolved tokens have $value == base-hex (dE = 0.0000)!")
print("    Why? Because layer-4 passes {'rule': '{layer-3.interaction-physics.hover-deltas}'},")
print("    but resolve_interaction_state() in design_system_compiler.py looks for delta_config.get('L_light') or delta_config.get('L', 0.0)!")
print("    It never dereferences the Layer 3 pointer, so dL defaults to 0.0!")
print("  - Furthermore, in Output/tokens-component.css (line 83): /* button */ is completely empty!")
print("    _flat_css() only handles 1-level tokens and inline bg/text dicts, silently dropping multi-variant components like button!")

print("\n" + "=" * 105)
print("PART 2: SIDE-BY-SIDE BENCHMARK RESULTS (ORIGINAL vs CORRECTED SCENARIOS)")
print("=" * 105)

def evaluate_10_criteria(mode="original"):
    systems = {}
    for name, ramps in erb.nine_systems.items():
        if mode != "original" and name == "Google Material Design 3":
            systems[name] = {h: list(reversed(v)) for h, v in ramps.items()}
        else:
            systems[name] = ramps

    def get_action_idx(sys_name):
        if mode == "original":
            return len(systems[sys_name]['blue']) // 2
        if mode == "fixed_l1_stop500":
            return 5  # Strict index 5 (Stop 500) across all systems
        if mode in ("fixed_semantic_actual_buggy_l3", "fixed_semantic_intended_l3"):
            if sys_name == "Google Material Design 3": return 7 # Tone 40 (Primary role)
            if sys_name == "IBM Carbon": return 6 # Grade 60 (index 6 in [10,20,30,40,50,60,70,80,90,100] wait: 0=10,1=20,2=30,3=40,4=50,5=60 -> index 5 or 6, Carbon has 12 stops in erb)
            if sys_name == "Radix Colors": return 8 # Step 9 Solid Fill
            return 6 # Stop 600

    res_wcag, res_apca, res_lin, res_deut, res_prot = {}, {}, {}, {}, {}
    res_glare, res_warm_c, res_peak_c, res_hover_de, res_mono_or_sync = {}, {}, {}, {}, {}

    for name, ramps in systems.items():
        act_idx = get_action_idx(name)
        # 1. WCAG
        aa, total = 0, 0
        for h, hexes in ramps.items():
            p1 = erb.wcag_contrast(hexes[-1], hexes[0])
            p2 = erb.wcag_contrast(hexes[-2], hexes[1])
            if mode in ("fixed_semantic_actual_buggy_l3", "fixed_semantic_intended_l3") and name == "Radix Colors":
                p3 = erb.wcag_contrast(hexes[10], hexes[2]) # Step 11 text on Step 3 bg
            else:
                p3 = erb.wcag_contrast(hexes[-3], hexes[2])
            p4 = erb.wcag_contrast('#ffffff', hexes[act_idx])
            for r in [p1, p2, p3, p4]:
                total += 1
                if r >= 4.5: aa += 1
        res_wcag[name] = (aa / total) * 100.0

        # 2. APCA
        if mode == "original":
            lcs = [abs(erb.apca_contrast(hexes[-2], hexes[1])) for h, hexes in ramps.items()]
        else:
            lcs = [0.5 * (abs(erb.apca_contrast(hexes[-2], hexes[1])) + abs(erb.apca_contrast(hexes[1], hexes[-2]))) for h, hexes in ramps.items()]
        res_apca[name] = sum(lcs) / len(lcs)

        # 3. Linearity
        stds = []
        for h, hexes in ramps.items():
            ls = [hex_to_oklch(x)[0] for x in hexes]
            dls = [abs(ls[i] - ls[i+1]) for i in range(len(ls)-1)]
            m = sum(dls)/len(dls)
            stds.append(math.sqrt(sum((x - m)**2 for x in dls)/len(dls)))
        res_lin[name] = sum(stds)/len(stds)

        # 4 & 5. CVD Deut & Prot
        g_mid = ramps['green'][act_idx]
        r_mid = ramps['red'][act_idx]
        gd = erb.simulate_deuteranopia(*erb.hex_to_srgb(g_mid))
        rd = erb.simulate_deuteranopia(*erb.hex_to_srgb(r_mid))
        res_deut[name] = math.sqrt(sum((gd[i]-rd[i])**2 for i in range(3)))
        gp = erb.simulate_protanopia(*erb.hex_to_srgb(g_mid))
        rp = erb.simulate_protanopia(*erb.hex_to_srgb(r_mid))
        res_prot[name] = math.sqrt(sum((gp[i]-rp[i])**2 for i in range(3)))

        # 6. Glare
        res_glare[name] = erb.wcag_contrast('#ffffff', erb.floors[name])

        # 7. Warm C
        oklchs = [hex_to_oklch(x) for x in ramps['amber']]
        mid_dark = [o[1] for o in oklchs if 0.25 <= o[0] <= 0.55]
        res_warm_c[name] = sum(mid_dark)/len(mid_dark) if mid_dark else 0

        # 8. Peak C
        max_c = [max(hex_to_oklch(x)[1] for x in hexes) for h, hexes in ramps.items()]
        res_peak_c[name] = sum(max_c)/len(max_c)

        # 9. Hover dE
        if mode == "fixed_semantic_intended_l3" and name == "4-Layer Compiler":
            # Layer 3 intended hover-deltas: dL = +/- 0.05
            res_hover_de[name] = 0.0500
        elif mode == "fixed_semantic_actual_buggy_l3" and name == "4-Layer Compiler":
            # Measure actual compiled tokens-component.json hover deltas across button variants:
            with open("Output/tokens-component.json", encoding="utf-8") as f:
                btn_c = json.load(f)["components"]["button"]
            des = []
            for var_name in ("primary", "secondary", "destructive"):
                hv = btn_c[var_name]["bg/hover"]["light"]
                des.append(erb.delta_e_oklab(hv["base-hex"], hv["$value"]))
            res_hover_de[name] = sum(des) / len(des)
        else:
            d_list = []
            for h, hexes in ramps.items():
                if act_idx + 1 < len(hexes):
                    d_list.append(erb.delta_e_oklab(hexes[act_idx], hexes[act_idx+1]))
            res_hover_de[name] = sum(d_list)/len(d_list)

        # 10. Monotonicity (original) OR Cross-Hue Lightness Sync (fixed modes)
        if mode == "original":
            cr_stds = []
            for h, hexes in ramps.items():
                crs = [erb.wcag_contrast(hexes[0], x) for x in hexes[1:]]
                dcrs = [crs[i+1] - crs[i] for i in range(len(crs)-1)]
                mean_d = sum(dcrs)/len(dcrs)
                cr_stds.append(math.sqrt(sum((x - mean_d)**2 for x in dcrs)/len(dcrs)))
            res_mono_or_sync[name] = sum(cr_stds)/len(cr_stds)
        else:
            n_steps = len(ramps['blue'])
            step_stds = []
            for idx in range(n_steps):
                ls_at_step = [hex_to_oklch(ramps[h][idx])[0] for h in ramps]
                m = sum(ls_at_step)/len(ls_at_step)
                step_stds.append(math.sqrt(sum((x - m)**2 for x in ls_at_step)/len(ls_at_step)))
            res_mono_or_sync[name] = sum(step_stds)/len(step_stds)

    min_l, max_l = min(res_lin.values()), max(res_lin.values())
    min_m, max_m = min(res_mono_or_sync.values()), max(res_mono_or_sync.values())

    out = {}
    for name in systems:
        s_wcag = res_wcag[name]
        s_apca = min(100.0, (res_apca[name] / 105.0) * 100.0)
        s_lin = (1.0 - (res_lin[name] - min_l) / (max_l - min_l)) * 100.0
        s_cvd_deut = min(100.0, (res_deut[name] / 0.08) * 100.0)
        s_cvd_prot = min(100.0, (res_prot[name] / 0.08) * 100.0)
        s_glare = max(0.0, 100.0 - abs(res_glare[name] - 18.2) * 20.0)
        s_warm_c = min(100.0, (res_warm_c[name] / 0.12) * 100.0)
        s_gamut = min(100.0, (res_peak_c[name] / 0.25) * 100.0)
        s_hover = max(0.0, 100.0 - abs(res_hover_de[name] - 0.045) * 1000.0)
        s_mono = (1.0 - (res_mono_or_sync[name] - min_m) / (max_m - min_m)) * 100.0
        comp = (
            0.125 * s_wcag + 0.125 * s_apca +
            0.100 * s_cvd_deut + 0.100 * s_cvd_prot +
            0.100 * s_lin + 0.100 * s_mono +
            0.100 * s_glare + 0.100 * s_warm_c +
            0.075 * s_hover + 0.075 * s_gamut
        )
        out[name] = {
            "score": round(comp, 1),
            "wcag": res_wcag[name],
            "apca": res_apca[name],
            "lin": res_lin[name],
            "deut": res_deut[name],
            "prot": res_prot[name],
            "hover": res_hover_de[name],
            "sync_or_mono": res_mono_or_sync[name]
        }
    return out

orig = evaluate_10_criteria("original")
l1_500 = evaluate_10_criteria("fixed_l1_stop500")
sem_buggy = evaluate_10_criteria("fixed_semantic_actual_buggy_l3")
sem_intended = evaluate_10_criteria("fixed_semantic_intended_l3")

def print_table(title, data, col10_label):
    print(f"\n>>> {title}")
    print(f"{'RANK':<4} | {'SYSTEM':<25} | {'SCORE':>5} | {'WCAG%':>6} | {'APCA':>5} | {'LIN dL':>6} | {'DEUT':>6} | {'PROT':>6} | {'HOVER':>6} | {col10_label:>8}")
    print("-" * 105)
    for r, (name, d) in enumerate(sorted(data.items(), key=lambda x: x[1]['score'], reverse=True), 1):
        print(f"#{r:<3} | {name:<25} | {d['score']:5.1f} | {d['wcag']:5.1f}% | {d['apca']:5.1f} | {d['lin']:6.4f} | {d['deut']:6.4f} | {d['prot']:6.4f} | {d['hover']:6.4f} | {d['sync_or_mono']:8.4f}")

print_table("0. ORIGINAL FLAWED BENCHMARK (As Published in Article — M3 Upside Down, n//2 Bias)", orig, "CR_MONO")
print_table("1. STRICT LAYER-1 PRIMITIVE BENCHMARK (Stop 500 vs #fff for ALL systems, M3 Orientation Fixed)", l1_500, "HUE_SYNC")
print_table("2. DESIGNATED ACTION STOP (Stop 600 / M3 Tone 40 / Carbon 60) + CURRENT BUGGY L3 (dL=0)", sem_buggy, "HUE_SYNC")
print_table("3. DESIGNATED ACTION STOP + IF LAYER-3 HOVER POINTER BUG IS FIXED (dL=0.05)", sem_intended, "HUE_SYNC")
