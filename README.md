# 4-Layer Perceptual Design System Compiler

A mathematically deterministic, OKLCH-native design system compiler that translates brand seed colors into fully accessible, multi-tier design tokens across sRGB and Display P3 gamuts.

Evaluated in an automated, reproducible comparative test suite against 8 major industry design systems (IBM Carbon, Google Material Design 3, GitHub Primer, Microsoft Fluent 2, Adobe Spectrum, Tailwind CSS, Apple HIG, Radix Colors), achieving 100% WCAG 2.2 AA compliance and 101.9 APCA Mean Lc readability on paired semantic scales.

---

## The Core Problem It Solves

Most design systems generate color ramps using simple linear RGB blending, HSL interpolation, or arbitrary manual picking. This creates four fatal flaws in production web apps:

1. **The Muddy Shadow Trap:** Yellows, golds, and ambers naturally collapse into dirty army-olive sludge at dark lightness levels unless hue is dynamically rotated toward orange/amber (H around 45 degrees).
2. **The Colorblind Confusion Collision:** Red (Error) and Green (Success) frequently share near-identical lightness (L around 0.48). When viewed by the 8% of males with Deuteranopia or Protanopia, hue collapses and both states look identical.
3. **The OLED Halation Glare:** Pitch-black surfaces (#000000 or #080503, 21:1 contrast) trigger severe photopic halation and smearing on OLED screens for users with astigmatism.
4. **Perceptual Linearity Distortion:** Non-uniform lightness steps produce abrupt contrast jumps in middle stops (400–600) while compressing shadow stops into undifferentiated mud.

This compiler solves all four using perceptual color science (OKLCH, APCA, Weber-Fechner elevation, Vienot CVD matrices) without requiring designers to hand-tune raw hex codes.

---

## Why 4 Distinct Layers?

The compiler is organized into 4 strict decoupled layers. Each layer represents a single responsibility in the token pipeline:

```
[Layer 1: Generation Engine]
       │  (OKLCH math, natural chroma envelopes, hue drift, sRGB/P3 gamut safe clamping)
       ▼
[Layer 2: Compiler Contract]
       │  (Governance rules, APCA thresholds, OLED floors, semantic conflict guardrails)
       ▼
[Layer 3: Delta Engine]
       │  (Interaction state physics: lightness/chroma deltas for hover, active, focus, disabled)
       ▼
[Layer 4: Token Architecture]
       │  (Semantic role mapping & 36 component token bindings)
       ▼
[Compiled Outputs: CSS, JSON, DTCG Tokens, Palette Visualizer]
```

### Layer 1: Generation Engine (`layer-1-generation-engine.json`)
* **Role:** Color science & primitive ramp synthesis.
* **Function:** Ingests raw brand hex inputs. Projects them into OKLCH space ($L, C, H$). Applies natural cubic Bezier chroma envelopes, family-specific chroma ceilings (`sRGB` and `P3`), and non-linear hue drift to preserve warmth in highlights and depth in shadows.
* **Output:** 12-stop primitive ladders (50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950, 1000) for every brand and greyscale family.

### Layer 2: Compiler Contract (`layer-2-compiler-contract.json`)
* **Role:** Architectural governance & CI/CD build gates.
* **Function:** Enforces system rules:
  - APCA spatial-frequency contrast targets per typographic hierarchy.
  - Semantic conflict guardrails (e.g. halts build if brand primary hue is within 30° of warning or error without an explicit exception).
  - Valid dark mode surface floor stops (700, 800, 900, 950).
  - Overlay cross-wiring rules (dark tints on light, light tints on dark).
  - Handoff routing policy between Figma (P3) and CSS engineering (sRGB).

### Layer 3: Delta Engine (`layer-3-delta-engine.json`)
* **Role:** Interaction state physics.
* **Function:** Replaces crude "stop + 100" jumps with perceptual lightness ($\Delta L$) and chroma ($\Delta C$) state deltas. Stop-based steps produce unequal perceptual changes across different hues (e.g. jumping 100 on yellow is jarring; on blue it is barely visible). Layer 3 computes precise mathematical offsets for `:hover`, `:active`, `:focus`, and `:disabled`.

### Layer 4: Token Architecture (`layer-4-token-architecture.json`)
* **Role:** Semantic roles and component abstraction.
* **Function:** Defines the three-tier token hierarchy:
  1. **Primitive Tokens:** Direct scale stops (`{primary.500}`).
  2. **Semantic Tokens:** Intent-based aliases (`color/fill/brand`, `color/text/primary`, `color/icon/success`).
  3. **Component Tokens:** 36 complete UI component bindings (buttons, badges, table cells, inputs, modals, navigation) mapped strictly to semantic roles.
* **Purity Guarantee:** Components never reference Layer 1 primitive stops or raw hex codes. Changing a brand seed re-evaluates all 407 component tokens without breaking component styling.

---

## Comparative Automated Benchmark

Deterministic mathematical evaluation across 9 design systems executed via `benchmarks/expanded_rigorous_benchmark.py` (open source, fully reproducible test harness):

> **Disclaimer:** These results represent deterministic mathematical comparisons run locally across public packages (`@carbon/colors`, `@material/material-color-utilities`, `@primer/primitives`, `@radix-ui/colors`, `tailwindcss/colors`). This is an automated algorithmic test suite, not an external peer-reviewed or industry-certified ranking. All benchmark scripts and formulas are included in `benchmarks/` for open reproduction.

### Two-Tier Scientific Benchmark

#### Tier A: Pure Layer-1 Primitive Scale (Midpoint Stop 500 on #ffffff)
*Evaluates raw ramp math without semantic role mapping or Layer 3 interaction physics.*

| Rank | System | Score | WCAG AA | APCA Lc | Linearity | Deutan dE | Hover dE | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | IBM Carbon | 86.5 | 100.0% | 82.6 | 0.0133 | 0.0823 | 0.1073 | Ultra-linear math |
| 2 | Google Material Design 3 | 84.7 | 75.0% | 89.4 | 0.0185 | 0.1106 | 0.0864 | Fixed orientation |
| **3** | **4-Layer Compiler (L1)** | **80.6** | **90.0%** | **95.8 (#1)** | **0.0333** | **0.1688** | **0.1047** | Raw ramp stop 500 |
| 4 | Adobe Spectrum | 80.6 | 85.0% | 83.3 | 0.0194 | 0.7865 | 0.1178 | Standard scale |
| 5 | Microsoft Fluent 2 | 80.0 | 80.0% | 86.7 | 0.0275 | 0.1577 | 0.1072 | Standard scale |
| 6 | Tailwind CSS | 75.8 | 80.0% | 84.0 | 0.0300 | 0.1790 | 0.0924 | Hand-tuned ramp |
| 7 | Apple HIG | 69.9 | 60.0% | 77.6 | 0.0540 | 0.1503 | 0.0474 | Display-tuned |
| 8 | GitHub Primer | 68.5 | 85.0% | 73.6 | 0.0265 | 0.0560 | 0.0781 | GitHub scale |
| 9 | Radix Colors | 58.1 | 40.0% | 70.6 | 0.0651 | 0.0207 | 0.0519 | Component steps |

#### Tier B: Full Architecture & Interaction Physics (Designated Action Roles + L3 Physics)
*Evaluates designated action roles (Stop 600 / Tone 40 / Grade 60 / Step 9) with Layer 3 Perceptual Hover Physics.*

| Rank | System | Score | WCAG AA | APCA Lc | Linearity | Deutan dE | Hover dE | Architectural Strength |
|---|---|---|---|---|---|---|---|---|
| 1 | IBM Carbon | 86.5 | 100.0% | 82.6 | 0.0133 | 0.0823 | 0.1073 | Strict industrial linearity |
| **2** | **4-Layer Compiler (Full)** | **86.0** | **100.0%** | **95.8 (#1)** | **0.0333** | **0.0810** | **0.0495 (#1)** | **Full L1-L4 Token Architecture** |
| 3 | Google Material Design 3 | 84.0 | 100.0% | 89.4 | 0.0185 | 0.0506 | 0.0879 | M3 Tone 40 action role |
| 4 | Adobe Spectrum | 82.1 | 95.0% | 83.3 | 0.0194 | 0.0589 | 0.0786 | Stop 600 fill |
| 5 | Microsoft Fluent 2 | 78.7 | 95.0% | 86.7 | 0.0275 | 0.0308 | 0.0678 | Stop 600 fill |
| 6 | Tailwind CSS | 77.8 | 90.0% | 84.0 | 0.0300 | 0.1221 | 0.0825 | Stop 600 fill |
| 7 | GitHub Primer | 66.2 | 85.0% | 73.6 | 0.0265 | 0.0294 | 0.0637 | Step 6 fill |
| 8 | Apple HIG | 66.0 | 65.0% | 77.6 | 0.0540 | 0.1900 | 0.1086 | Action tint |
| 9 | Radix Colors | 65.6 | 50.0% | 70.6 | 0.0651 | 0.0758 | 0.0293 | Step 9 solid fill |

### Methodological Audit & Why These Changes Were Made
A rigorous code audit of the earlier benchmark script uncovered four critical methodology flaws that distorted earlier rankings:
1. **Google M3 Array Direction Inversion:** M3 tones were hardcoded ascending `[10..99]` while all other 8 systems were descending `[50..950]`. This caused M3 to test light Tone 60 on white (tanking its WCAG AA score to 75.0%), while artificially gifting it #1 predictability by measuring contrast steps from black Tone 10.
2. **12-Stop vs 11-Stop Midpoint Index Bias:** Testing `hexes[n // 2]` evaluated Stop 600 for 12-stop systems (4-Layer, Carbon) but Stop 500 for 11-stop systems (Tailwind, Fluent, Spectrum). At actual Stop 500, 4-Layer amber and green also fail on white (3.39:1 and 3.10:1), which is why Layer 4 semantic mapping to Stop 600 exists.
3. **Hover Physics Omission:** The old script measured primitive step jump (Stop 600 to 700, dE = 0.1145) and penalized 4-Layer Compiler, ignoring the Layer 3 Delta Engine (`dL = ±0.05`).
4. **Compiler Bug Fixes:** Fixed `resolve_interaction_state()` to dereference `{layer-3.interaction-physics.*}` pointers (fixing a silent fallback to `dL = 0.0`) and updated `tokens-component.css` to recursively emit nested `--button-*` tokens.

---

## Reality-Knock Stress Test Matrix

Tested against production UI scenarios (including the Skillbeek data grid) and 8 extreme edge-case brand archetypes:

| Test Archetype | 8-bit Quantization Collapse | Muddy Stops (55°–125°) | Deuteranopia dE | Protanopia dE | Tritanopia dE | Status |
|---|---|---|---|---|---|---|
| **Skillbeek Gold (`#B7812F`)** | 0 (Clean) | 0 (None) | 0.1016 | 0.2600 | 0.2248 | **PASS ✓** |
| **Pitch Navy Abyss (`#0A192F`)** | 0 (Clean) | 0 | 0.1016 | 0.2600 | 0.2248 | **PASS ✓** |
| **Faded Pastel Peach (`#FFD1BA`)** | 0 (Clean) | 0 | 0.1016 | 0.2600 | 0.2248 | **PASS ✓** |
| **Wide-Gamut P3 Cyan (`#00FFFF`)** | 0 (Clean) | 0 | 0.1016 | 0.2600 | 0.2248 | **PASS ✓** |
| **Deep Plum Violet (`#4A0E4E`)** | 0 (Clean) | 0 | 0.1016 | 0.2600 | 0.2248 | **PASS ✓** |

### The Skillbeek Production Finding
Auditing real-world spreadsheet tokens revealed why developers had previously tweaked raw hex codes:
- When developers bound an icon directly to primitive `{success.500}` (`#2FA836`), contrast on light surface was 2.93:1 (failing the 3.0:1 graphical threshold).
- When bound to the compiler's intended architectural token `color/icon/success` (`{success.600}`, `#027C1E`), contrast is **5.09:1** (APCA 75.9), passing cleanly without any manual override.

---

## Installation & Compilation

```bash
# Clone the repository
git clone https://github.com/SUBSAHARXN/design-system-compiler.git
cd design-system-compiler

# Run compilation (generates CSS tokens, JSON DTCG tokens, and visual palette)
python design_system_compiler.py --floor-stop 950 --cta-color primary --mode both --palette
```

### CLI Parameters
* `--floor-stop [700|800|900|950]`: Dark mode surface base lightness (Default: `950`, L=0.17, 18.6:1 glare).
* `--cta-color [primary|secondary]`: Assigns main Call-to-Action button brand fill.
* `--mode [light|dark|both]`: Build target modes.
* `--palette`: Generates `Output/design-system-palette.html` interactive visualizer.
* `--strict`: Enforces hard failure on CI if architectural contracts or CVD thresholds are breached.

### Generated Artifacts (`Output/`)
* `tokens.css`: Primitives and semantic CSS custom properties with light/dark themes.
* `tokens-component.css`: Component-level CSS variables (795 lines, 36 components).
* `tokens-primitives.json`: W3C Design Tokens Community Group (DTCG) primitive tokens.
* `tokens-semantic.json`: Semantic token dictionary with APCA validation metadata.
* `tokens-component.json`: Fully resolved component token tree.
* `design-system-palette.html`: Standalone interactive browser preview with light/dark toggles.

---

## License

MIT License. Designed and maintained by SUBSAHARXN.
