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

| Rank | System | Score | WCAG AA | APCA Lc | Linearity | Deutan dE | Protan dE | OLED Glare | Warm Chroma |
|---|---|---|---|---|---|---|---|---|---|
| 1 | IBM Carbon | 83.6 | 100.0% | 86.7 | 0.0133 | 0.0721 | 0.1266 | 18.1:1 | 0.0817 |
| 2 | Google Material Design 3 | 81.7 | 75.0% | 94.5 | 0.0185 | 0.0517 | 0.1258 | 18.6:1 | 0.0853 |
| **3** | **4-Layer Compiler** | **78.5** | **100.0%** | **101.9** | **0.0333** | **0.0742** | **0.2287** | **18.6:1** | **0.0972** |
| 4 | GitHub Primer | 78.3 | 85.0% | 77.7 | 0.0265 | 0.0531 | 0.1335 | 18.9:1 | 0.0796 |
| 5 | Microsoft Fluent 2 | 77.4 | 85.0% | 89.8 | 0.0359 | 0.0787 | 0.0957 | 18.4:1 | 0.0894 |
| 6 | Adobe Spectrum | 76.4 | 65.0% | 86.1 | 0.0307 | 0.0701 | 0.1895 | 18.9:1 | 0.1083 |
| 7 | Tailwind CSS | 76.3 | 80.0% | 88.0 | 0.0300 | 0.0786 | 0.2250 | 20.2:1 | 0.1014 |
| 8 | Apple HIG | 66.1 | 60.0% | 81.7 | 0.0540 | 0.0671 | 0.2648 | 21.0:1 | 0.1265 |
| 9 | Radix Colors | 46.9 | 40.0% | 74.3 | 0.0651 | 0.0185 | 0.0677 | 18.9:1 | 0.0486 |

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
