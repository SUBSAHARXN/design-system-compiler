# From Olive Sludge to First Principles: How I Built an Autonomous OKLCH Color Compiler with Claude and Antigravity

*How overcompensating for accessibility contrast in an autonomous color compiler backfired into olive mud, alienated our developers, and what it took to fix the math.*

---

This project didn't start a few weeks ago. It started back in **April**.

And contrary to what most design system tutorials preach, I never handpicked 11-stop color scales in Figma. Nobody has the patience or visual precision to manually tweak 50 through 1000 lightness steps and somehow guarantee they pass WCAG 2.2 AA contrast across both light and dark themes. 

**The only color I ever handpicked was the primary 500.**

To build out the rest of the palette, I was using Figma plugins—specifically tools like **HSL Shader** and similar lighting generators. If you’ve ever used HSL Shader, you know how straightforward the premise is: you select a single target hex anchor (your 500), and the plugin generates:
1. A **lighting ramp** (stepping from 1000 down to 50)
2. A **paired grayscale ramp** (showing the lightness distribution of each step)

> 📷 **[Insert Screenshot: Original Figma HSL Shader Exploration from April]**  
> *Top: Chromatic lighting ramp generated from 1000 to 50. Bottom: Paired grayscale luminance ramp.*

HSL Shader was our stepping stone. But plugins are just static visual generators on a Figma canvas. They don't give you code, they don't validate WCAG or APCA contrast, they don't handle dark mode glare on OLED screens, and they don't map abstract scales into living UI component tokens.

I wanted something far more ambitious: an **autonomous color physics compiler**. A deterministic pipeline where you feed in your raw brand hex seeds, and it compiles an entire 4-layer design system with mathematical certainty.

To build it, I paired with **Claude** and **Antigravity** (Google DeepMind’s agentic coding environment). 

We architected a decoupled four-layer JSON specification:
- **Layer 1:** Generation Engine (pure color physics & OKLCH math)
- **Layer 2:** Compiler Contract & CI Gates (contrast gates & accessibility validation)
- **Layer 3:** Interaction Physics (hover states, focus rings, shadow physics)
- **Layer 4:** Semantic Taxonomy (mapping primitives to 36 concrete UI component roles)

We thought pure mathematical determinism would solve color forever. 

**We were completely wrong. And our own compiler proved it.**

---

## 1. The Skillbeek Revolt: When Our Own Compiler Caused the Mud

The first production trial for the compiler was **Skillbeek**, an education platform built around a vivid purple primary (`#A952DB`) and green (`#4CB33C`).

We ran the compiler, generated the tokens, and handed them to the development team. 

Then the revolt happened.

When we inspected the Skillbeek codebase weeks later, we discovered **over 39 rogue, hardcoded hex values** (`#2563eb`, `#e67e22`, `#00832D`) scattered across star ratings, active badges, and call-to-action buttons. The developers had completely bypassed the compiler's tokens.

Why? **Because the compiler’s output was dull, earthy, and rotted into mud.**

When developers needed a vibrant active badge or a punchy amber warning button, the compiler gave them swamp water. They weren't rebelling out of malice—they bypassed the design system because the compiler forced them to put ugly mud on production user interfaces.

When automated cleanup scripts later attempted to force those rogue hexes back into the compiler's rigid tokens, the build blew up: eight structural errors, APCA contrast failures on buttons, and completely flat elevation surfaces in dark mode.

---

## 2. The Yellow Mud Trap: Born from Accessibility Overcompensation

How did the compiler end up generating mud in the first place?

Looking back at our logs and equations, the truth was embarrassing: **the yellow mud was caused by our compiler violently overcompensating for accessibility.**

Here is the trap:
1. Saturated yellow (`#FFD400`) has an extremely high natural lightness (~0.90 in OKLCH).
2. Our Layer 2 accessibility gates demanded that text and button fills hit strict WCAG 4.5:1 and APCA Lc 60 contrast against light backgrounds.
3. Because yellow at stop 500 physically cannot hit that contrast on white, the compiler's algorithm did what math does: **it dragged yellow’s lightness way down to 0.40 to force the contrast score.**
4. But the algorithm kept the hue angle locked static at 94°. 

```
The Accessibility Overcompensation Trap:
Target: Pass APCA Lc 60 on light background
Pure Yellow (#FFD400, Lightness 0.90, Hue ~94°)
Compiler forces Lightness down to 0.40 at static Hue 94°
Compiler Output: #625002 (Rotting army-green mud)
```

Human vision evolved under sunlight. We have three cone photoreceptors in our retinas (L, M, and S), with our highest sensitivity clustered tightly around green wavelengths. In nature, "dark yellow" does not exist—when yellow objects move into shadow, human vision expects the hue to drift naturally toward warm amber, ochre, or burnt orange.

By locking hue at 94° while crushing lightness to pass accessibility tests, our compiler dragged the color directly through the human eye's peak green sensitivity curve. The math said it was "accessible." The human eye saw vomit.

### How We Fixed It: Convective Hue Drift

We didn't fix this by hand-tweaking hex codes in Figma. We fixed it by encoding human optical biology directly into the compiler's **Layer 3 (Interaction Physics)**:

```python
# Convective Hue Drift Algorithm (Layer 3)
if 55.0 <= hue <= 125.0:  # Yellow / Lime hazard band
    lightness_deficit = max(0.0, 0.70 - current_lightness)
    # Dynamically rotate hue toward warm amber (45°) as lightness drops
    convective_hue_shift = (45.0 - hue) * (lightness_deficit / 0.70) * 0.45
    corrected_hue = hue + convective_hue_shift
```

Whenever the compiler darkens a hue between 55° and 125° (for hover states, active borders, or dark mode surfaces), it dynamically rotates the hue toward warm orange/amber (`45°`). 

The mud instantly vanished. Yellows now degrade into rich honey, cognac, and amber tones.

---

## 3. The Benchmark Wake-Up Call: Auditing 9 Design Systems

With the mud eliminated and contrast passing, we wanted to see how our compiler measured up against the industry.

To be clear: **no consortium or standards body handed us a trophy.** We built our own automated, open-source Python benchmark suite (`benchmarks/expanded_rigorous_benchmark.py`) to pit our compiler against nine widely used design systems under identical mathematical scrutiny:
- IBM Carbon
- Google Material Design 3 (M3)
- GitHub Primer
- Microsoft Fluent 2
- Adobe Spectrum
- Tailwind CSS
- Apple Human Interface Guidelines (HIG)
- Radix Colors

We scored each system across six reproducible dimensions:
1. **WCAG 2.2 AA Pass Rate** (% of semantic pairs passing 4.5:1 / 3:1)
2. **APCA Mean Readability (Lc)** (Advanced Perceptual Contrast Algorithm score)
3. **Linearity Error (StdDev)** (Lightness step uniformity across ramps)
4. **Muddy Shadow Stops** (Stops trapped in the olive mud zone)
5. **CVD Deutan Separation (ΔE)** (Readability under red-green colorblindness)
6. **OLED Glare Ceiling Compliance** (Preventing 100% pitch-black eye strain)

### The First Run: Blinded by Accessibility

When the benchmark finished, our compiler took **#1 in APCA Readability (101.9 Lc)** and **#1 in WCAG 2.2 AA (100.0%)**.

**Yet our overall composite score was mediocre.** We ranked near the middle of the pack.

Why? **Accessibility bias.**

We had become so fanatical about guaranteeing contrast that we were distorting the lightness curve to force every token pair to pass. We shoved stop 400 higher and pulled stop 600 lower. The contrast passed, but the lightness steps became erratic. IBM Carbon destroyed us on linearity error (Carbon: `0.0133`, Our initial build: `0.0520`).

We had built a system with maximum contrast horsepower, but completely broken suspension.

### The Data-Driven Fix: The 1.15 Power Curve

We went back into Layer 1 with Claude and Antigravity. Instead of piecewise hacks, we replaced the ramp math with a continuous **1.15 Power Curve**:

```
Lightness(step) = 1.0 - (step / 1000) ^ 1.15
```

This single continuous curve smoothed the delta-L transition while naturally hitting contrast thresholds at key semantic anchor stops.

We re-ran the benchmark across all nine systems.

**The result in our audit suite:**
- Linearity error dropped from `0.0520` down to `0.0333`
- WCAG 2.2 AA held steady at **100.0%**
- APCA Readability led the 9 audited systems at **101.9 Lc**
- **Composite Score rose to 78.5 / 100**, placing the compiler at **#3 in the test suite**, behind IBM Carbon (83.6) and Google Material 3 (81.7), and ahead of Primer (78.3), Fluent (77.4), and Tailwind (76.3).

Here are the exact benchmark results output by the Python audit script:

| Rank | Design System | WCAG 2.2 AA | APCA Readability | Linearity Error | Muddy Stops | Overall Score |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **#1** | **IBM Carbon** | 100.0% | 86.7 Lc | 0.0133 (Ultra-linear) | 0 | **83.6 / 100** |
| **#2** | **Google Material 3** | 75.0% | 94.5 Lc | 0.0185 | 0 | **81.7 / 100** |
| **#3** | **4-Layer Compiler** | **100.0%** | **101.9 Lc (#1)** | 0.0333 | 0 | **78.5 / 100** |
| #4 | GitHub Primer | 85.0% | 77.7 Lc | 0.0265 | 0 | 78.3 / 100 |
| #5 | Microsoft Fluent 2 | 85.0% | 89.8 Lc | 0.0359 | 0 | 77.4 / 100 |
| #6 | Adobe Spectrum | 65.0% | 86.1 Lc | 0.0307 | 0 | 76.4 / 100 |
| #7 | Tailwind CSS | 80.0% | 88.0 Lc | 0.0300 | 1 (Yellow 700) | 76.3 / 100 |
| #8 | Apple HIG | 60.0% | 81.7 Lc | 0.0540 | 1 | 66.1 / 100 |
| #9 | Radix Colors | 40.0% | 74.3 Lc | 0.0651 | 0 | 46.9 / 100 |

---

## 4. Test It Live: Hosted on Subtle Shoppers

We are hosting the interactive compiler test bench live as a dedicated subdomain of **Subtle Shoppers**:

👉 **Live Test Bench:** `compiler.subtleshoppers.com` *(or test locally in the repo)*  
👉 **GitHub Repository:** [SUBSAHARXN/design-system-compiler](https://github.com/SUBSAHARXN/design-system-compiler)

On the live site, you can:
- **Input your own brand seeds:** Toggle between standard sRGB Hex and native OKLCH sliders (Lightness, Chroma, Hue).
- **Inspect P3 Gamut Boundaries:** The compiler automatically detects wide-gamut Display P3 colors and clips out-of-gamut values cleanly.
- **Audit CVD Colorblindness:** Toggle Deuteranopia, Protanopia, and Tritanopia filters in real-time to see how your palette holds up under human visual deficiencies.
- **Export 36 Component Tokens:** Copy ready-to-use CSS variables, Tailwind tokens, and DTCG design tokens.

> 📷 **[Insert Screenshot: Live Brand Test Bench UI showing Dual-Mode Hex / OKLCH Picker]**  
> *The live compiler interface running on Subtle Shoppers.*

---

## 5. "4-Layer Compiler" is a Boring Name. Help Me Name It.

Right now, the repo and architecture are called the **4-Layer OKLCH Design System Compiler**. 

That is an excruciatingly boring, utilitarian engineering title. It sounds like a government whitepaper from 2004.

I don’t have a good brand name for it yet. Some ideas:
- *Specter* (or *SpectraCore*)
- *PrismEngine*
- *ChromaLoom*
- *OklchOS*
- *Percepta*

If you have an idea for what an autonomous, first-principles color compiler should be called, leave a comment. I am completely open to suggestions.

---

## 6. Tear It Apart: An Open Invitation for Feedback

This compiler wasn't built in an academic vacuum. It was built by breaking palettes in production with Skillbeek, getting caught by our developers for making muddy yellow buttons, getting humbled by IBM Carbon’s linearity in benchmarks, and pairing with AI to write mathematical proofs that actually hold up.

I want you to test this. 

Input your weirdest, hardest brand colors—the saturated teals, the neon greens, the hyper-bright yellows that usually break every design system. 

Find where our 1.15 curve fails. Criticize our APCA assumptions. Tell me where the tokens feel too opinionated, or open an issue on GitHub to help improve the math.

Good systems aren't built on dogma—they're built by compilers that refuse to produce output that violates their own spec.

---

*Test the compiler live on the Subtle Shoppers subdomain, inspect the code on [GitHub](https://github.com/SUBSAHARXN/design-system-compiler), and drop your feedback, name ideas, and critique below.*
