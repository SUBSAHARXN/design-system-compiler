# Benchmarking 9 Industry Design Systems: An Empirical Test Suite

*By Subtle Shoppers Engineering & Open Color Science*

---

Design system marketing often claims "universal accessibility" and "harmonious color science." But when tested under automated, mathematical scrutiny, how do industry giants actually perform?

We built an open-source, automated benchmarking harness (`benchmarks/expanded_rigorous_benchmark.py`) to evaluate 9 production color palettes:
1. **IBM Carbon** (`@carbon/colors`)
2. **Google Material Design 3** (`@material/material-color-utilities`)
3. **4-Layer OKLCH Compiler** (Subtle Shoppers Baseline)
4. **GitHub Primer** (`@primer/primitives`)
5. **Microsoft Fluent 2**
6. **Adobe Spectrum / Leonardo**
7. **Tailwind CSS** (`tailwindcss/colors`)
8. **Apple Human Interface Guidelines (HIG)**
9. **Radix Colors** (`@radix-ui/colors`)

---

## The 6 Quantitative Test Dimensions

Every system was tested across 6 automated metrics using paired semantic token scales:

### 1. WCAG 2.2 AA Compliance Rate (%)
Evaluates text-to-surface contrast ratios against standard minimums:
- Normal text: $\ge 4.5:1$
- Large text: $\ge 3.0:1$
- Evaluated across paired stops (e.g. 50 on 900, 500 on 50, 100 on 800).

### 2. APCA Readability Metric (Mean Lc)
The Advanced Perceptual Contrast Algorithm (APCA) accounts for spatial frequency, text weight, and non-linear photoreceptor response in human vision. Higher positive scores indicate stronger legibility. Targets:
- Body text: $\text{Lc} \ge 75$
- Headlines: $\text{Lc} \ge 60$

### 3. Perceptual Linearity Error (Residual Variance)
Measures whether lightness steps in a ladder descend smoothly or create sudden contrast spikes. Evaluated by fitting stops 50–950 to an exponential curve and calculating residual variance:
- Ideal: $\le 0.02$
- Poor (uneven jumps): $\ge 0.05$

### 4. CVD Separation: Deuteranopia & Protanopia (dE)
Simulates red-green color blindness using the Vienot 1999 LMS matrix. Measures $\Delta E$ in Oklab space between semantic **Error Red** and **Success Green**:
- Unsafe collision: $\Delta E < 0.05$
- Safe threshold: $\Delta E \ge 0.07$

### 5. OLED Halation Glare Ratio
Measures maximum contrast between dark mode background stops (800–950) and foreground text (50–100):
- Safe ergonomics: $\le 18.6:1$
- Halation risk (severe eye strain on OLED): $> 19.5:1$

### 6. Warm-Hue Chroma Retention
Evaluates whether yellow, gold, and amber hues (55°–125°) retain saturation in middle and shadow stops (600–800) without decaying into army-olive mud.

---

## Detailed Benchmark Results

| Rank | System | Score | WCAG AA | APCA Lc | Linearity | Deutan dE | OLED Glare | Muddy Stops |
|---|---|---|---|---|---|---|---|---|
| 1 | **IBM Carbon** | **83.6** | 100.0% | 86.7 | 0.0133 | 0.0721 | 18.1:1 | 0 |
| 2 | **Google Material 3** | **81.7** | 75.0% | 94.5 | 0.0185 | 0.0517 | 18.6:1 | 0 |
| 3 | **4-Layer OKLCH Compiler** | **78.5** | 100.0% | 101.9 | 0.0333 | 0.0742 | 18.6:1 | 0 |
| 4 | **GitHub Primer** | **78.3** | 85.0% | 77.7 | 0.0265 | 0.0531 | 18.9:1 | 0 |
| 5 | **Microsoft Fluent 2** | **77.4** | 85.0% | 89.8 | 0.0359 | 0.0787 | 18.4:1 | 0 |
| 6 | **Adobe Spectrum** | **76.4** | 65.0% | 86.1 | 0.0307 | 0.0701 | 18.9:1 | 0 |
| 7 | **Tailwind CSS** | **76.3** | 80.0% | 88.0 | 0.0300 | 0.0786 | 20.2:1 | 1 (Yellow 700) |
| 8 | **Apple HIG** | **66.1** | 60.0% | 81.7 | 0.0540 | 0.0671 | 21.0:1 | 1 (Gold dark) |
| 9 | **Radix Colors** | **46.9** | 40.0% | 74.3 | 0.0651 | 0.0185 | 18.9:1 | 0 |

---

## Key Technical Takeaways

1. **IBM Carbon Remains the Contrast Standard:** IBM Carbon’s strict enterprise engineering pedigree shows in its 100% WCAG pass rate and ultra-clean linearity (0.0133). However, its conservative chroma envelopes feel muted for consumer apps.
2. **APCA Superiority of OKLCH:** The 4-Layer Compiler achieved the highest APCA score (101.9 Lc) due to Ottosson OKLCH lightness mapping combined with natural Bezier chroma expansion.
3. **Radix Colors is Not a Semantic Hierarchy:** Radix Colors is exceptional for component tinting, but applying it naively as background/foreground pairs produces a 40% WCAG failure rate unless developers manually cross-reference contrast charts.
4. **The OLED Dark Mode Trap:** Tailwind (20.2:1) and Apple HIG (21.0:1) default to pitch-black backgrounds, triggering photopic halation for astigmatic users.

---

## How to Reproduce These Results

Clone the repository and run the test harness locally:

```bash
git clone https://github.com/SUBSAHARXN/design-system-compiler.git
cd design-system-compiler
python benchmarks/expanded_rigorous_benchmark.py
```

The script runs deterministically in less than 2 seconds, evaluating all raw color arrays and outputting CSV/JSON matrix logs.
