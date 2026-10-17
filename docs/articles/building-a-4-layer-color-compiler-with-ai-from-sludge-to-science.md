# From Olive Sludge to First Principles: How I Built an Autonomous OKLCH Color Compiler with Claude and Antigravity

*How overcompensating for accessibility contrast in an autonomous color compiler backfired into olive mud, alienated our developers, and what it took to fix the math.*

---

This project didn't start a few weeks ago. It started back in April.

I never handpicked 11-stop color scales in Figma. Nobody has the patience or visual precision to manually tweak 50 through 1000 lightness steps and somehow guarantee they pass WCAG 2.2 AA contrast across both light and dark themes. 

The only color I ever handpicked was the primary 500.

To get the rest of the palette, I used Figma plugins like HSL Shader. You select a single target hex (your 500), and the plugin generates:
1. A lighting ramp (stepping from 1000 down to 50)
2. A paired grayscale ramp showing the lightness distribution of each step

> 📷 **[IMAGE STOP 1: Figma Canvas Exploration with HSL Shader]**  
> **What to capture:** A screenshot of your Figma canvas from April showing a single 500 hex anchor driving HSL Shader to output the 1000–50 chromatic lighting ramp and paired grayscale ramp.  
> **Caption:** *Figure 1: My original Figma exploration in April using HSL Shader. Selecting a single 500 anchor automatically generated an 11-stop lighting ramp and a grayscale comparison strip.*

HSL Shader was great, and plugins can obviously spit out tokens and Figma variables. 

The catch was what happened when you actually tried to build with them. HSL doesn't care about human eyes; it treats a 50% yellow as if it has the exact same brightness as a 50% blue, even though yellow blazes on your screen. Once a plugin generates those variables, you're on your own. If a button fails contrast or a dark mode border causes glare on an OLED screen, the plugin won't warn you. It just hands you the tokens and lets you ship broken UI.

I didn't want to keep checking contrast tools and tweaking variables by hand. I wanted a compiler: something that takes brand hexes, uses real color physics (OKLCH), and refuses to build if the contrast is broken.

To build it, I paired with Claude and Antigravity (Google DeepMind’s agentic coding environment). 

We broke the system down into four layers:
- **Layer 1:** Generation Engine (color physics and OKLCH math)
- **Layer 2:** Compiler Contract & CI Gates (contrast gates and accessibility validation)
- **Layer 3:** Interaction Physics (hover states, focus rings, and shadow physics)
- **Layer 4:** Semantic Taxonomy (mapping primitives to 36 concrete UI component roles)

We expected pure math to handle every edge case out of the box, but real production UI quickly proved our assumptions wrong.

---

## 1. The Skillbeek Revolt: When Our Own Compiler Caused the Mud

The first production trial for the compiler was Skillbeek, an education platform I recently published on Binance (open-source on GitHub at [SUBSAHARXN/Skillbeek-App](https://github.com/SUBSAHARXN/Skillbeek-App) and deployed live on Vercel at [skillbeek-app.vercel.app](https://skillbeek-app.vercel.app)). Its brand identity used a bright purple primary (`#A952DB`) and green (`#4CB33C`).

We ran the compiler, generated the tokens, and handed them to the development team to wire into the live React components. 

When we inspected the Skillbeek codebase weeks later, we discovered over 39 hardcoded hex values (`#2563eb`, `#e67e22`, `#00832D`) scattered across star ratings, badges, buttons, and card borders. The developers had completely bypassed the compiler's tokens because the output looked dull, earthy, and rotted into mud. When they needed an amber warning button or an active badge, the compiler handed them swamp water. They bypassed the design system simply because shipping ugly mud on production screens was not an option.

When automated cleanup scripts later attempted to force those rogue hexes back into the compiler's tokens, the build blew up with eight structural errors and failed APCA contrast tests. Dark mode surfaces had turned completely flat.

> 📷 **[IMAGE STOP 2: Skillbeek Live Production UI]**  
> **What to capture:** A screenshot of the Skillbeek live web app ([skillbeek-app.vercel.app](https://skillbeek-app.vercel.app)) showing the purple primary navigation/CTAs, green success tags, or session cards where developers rebelled against dull tokens.  
> **Caption:** *Figure 2: Skillbeek running in production on Vercel. When the early compiler generated dull, muddy tokens, developers bypassed the design system and hardcoded 39+ raw hexes directly into the UI.*

---

## 2. The Yellow Mud Trap: Born from Accessibility Overcompensation

Looking back at our logs and equations, the yellow mud came directly from our compiler overcompensating for accessibility.

Saturated yellow (`#FFD400`) naturally sits at a high lightness of around 0.90 in OKLCH. When our Layer 2 accessibility gates demanded that text and button fills hit strict WCAG 4.5:1 and APCA Lc 60 against light backgrounds, yellow at stop 500 physically could not pass on white. The compiler solved that by dragging yellow's lightness down to 0.40 while leaving the hue angle locked at 94°.

```
The Accessibility Overcompensation Trap:
Target: Pass APCA Lc 60 on light background
Pure Yellow (#FFD400, Lightness 0.90, Hue ~94°)
Compiler forces Lightness down to 0.40 at static Hue 94°
Compiler Output: #625002 (Rotting army-green mud)
```

Human vision evolved under sunlight. We have three cone photoreceptors in our retinas (L, M, and S), with our highest sensitivity clustered tightly around green wavelengths. In nature, "dark yellow" does not exist. When yellow objects move into shadow, human vision expects the hue to drift naturally toward warm amber or burnt orange.

By locking hue at 94° while crushing lightness to pass accessibility tests, our compiler dragged the color directly through the eye's peak green sensitivity curve. The math said it was accessible. The human eye saw vomit.

### How We Fixed It: Convective Hue Drift

We didn't fix this by hand-tweaking hex codes in Figma. We fixed it by encoding human optical biology directly into the compiler's Layer 3 (Interaction Physics):

```python
# Convective Hue Drift Algorithm (Layer 3)
if 55.0 <= hue <= 125.0:  # Yellow / Lime hazard band
    lightness_deficit = max(0.0, 0.70 - current_lightness)
    # Dynamically rotate hue toward warm amber (45°) as lightness drops
    convective_hue_shift = (45.0 - hue) * (lightness_deficit / 0.70) * 0.45
    corrected_hue = hue + convective_hue_shift
```

Whenever the compiler darkens a hue between 55° and 125° (for hover states, active borders, or dark mode surfaces), it rotates the hue toward warm amber (`45°`). 

The mud vanished. Yellows now degrade into warm honey and amber tones.

> 📷 **[IMAGE STOP 3: Visual Swatch Comparison — Mud Trap vs. Convective Drift]**  
> **What to capture:** Two horizontal color strips side by side or stacked:  
> 1. *Top strip:* Yellow `#FFD400` stepping down in lightness at static hue 94°, ending in swampy `#625002` olive mud.  
> 2. *Bottom strip:* Yellow `#FFD400` stepping down with Convective Hue Drift, rotating hue toward 45° warm amber to produce rich, luminous cognac tones.  
> **Caption:** *Figure 3: The Yellow-to-Olive trap solved. Top: Naive lightness reduction produces swampy `#625002` olive mud. Bottom: Layer 3 Convective Hue Drift curves hue toward warm amber (45°), keeping shadow states rich.*

---

## 3. The Benchmark Wake-Up Call: Auditing 9 Design Systems

With the mud eliminated and contrast passing, we wanted to see how our compiler measured up against existing systems.

To be clear: no consortium or standards body handed us a trophy. We built our own automated Python benchmark suite (`benchmarks/expanded_rigorous_benchmark.py`) to pit our compiler against nine widely used design systems under identical mathematical rules:
- IBM Carbon
- Google Material Design 3 (M3)
- GitHub Primer
- Microsoft Fluent 2
- Adobe Spectrum
- Tailwind CSS
- Apple Human Interface Guidelines (HIG)
- Radix Colors

We scored each system across six dimensions:
1. **WCAG 2.2 AA Pass Rate** (% of semantic pairs passing 4.5:1 / 3:1)
2. **APCA Mean Readability (Lc)** (Advanced Perceptual Contrast Algorithm score)
3. **Linearity Error (StdDev)** (Lightness step uniformity across ramps)
4. **Muddy Shadow Stops** (Stops trapped in the olive mud zone)
5. **CVD Deutan Separation (ΔE)** (Readability under red-green colorblindness)
6. **OLED Glare Ceiling Compliance** (Preventing 100% pitch-black eye strain)

### The First Run: Blinded by Accessibility

When the benchmark finished, our compiler took #1 in APCA Readability (101.9 Lc) and #1 in WCAG 2.2 AA (100.0%), yet the overall composite score landed near the middle of the pack. 

The issue was pure accessibility bias: we had focused so heavily on guaranteeing contrast that we distorted the lightness curves to force every token pair to pass. Shoving stop 400 higher and pulling stop 600 lower kept contrast legal, but made lightness steps erratic. IBM Carbon beat us handily on linearity error (Carbon: `0.0133`, Our initial build: `0.0520`). We had built a system with maximum contrast horsepower, but broken suspension.

### The Data-Driven Fix: The 1.15 Power Curve

We went back into Layer 1 with Claude and Antigravity. Instead of piecewise hacks, we replaced the ramp math with a continuous 1.15 Power Curve:

```
Lightness(step) = 1.0 - (step / 1000) ^ 1.15
```

This smoothed the delta-L transition while naturally hitting contrast thresholds at key semantic anchor stops.

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

> 📷 **[IMAGE STOP 4: Automated Benchmark Table from the Showcase Site]**  
> **What to capture:** A screenshot of the Peer-Reproducible Industry Benchmark table from the showcase site (`#benchmark` section), showing IBM Carbon, Material 3, and the 4-Layer Compiler in the top 3 with WCAG pass rates, APCA Lc scores, and linearity error.  
> **Caption:** *Figure 4: Audit matrix generated by `expanded_rigorous_benchmark.py`. The 4-Layer Compiler takes #1 in APCA Readability (101.9 Lc) and ties Carbon at 100% WCAG AA, ranking #3 overall.*

---

## 4. Test It Live: Hosted on Subtle Shoppers

We are hosting the interactive compiler test bench live as a dedicated subdomain of Subtle Shoppers:

👉 **Live Test Bench:** `compiler.subtleshoppers.com` *(or test locally in the repo)*  
👉 **GitHub Repository:** [SUBSAHARXN/design-system-compiler](https://github.com/SUBSAHARXN/design-system-compiler)

On the live site, you can:
- **Input your own brand seeds:** Toggle between standard sRGB Hex and native OKLCH sliders (Lightness, Chroma, Hue).
- **Inspect P3 Gamut Boundaries:** The compiler automatically detects wide-gamut Display P3 colors and clips out-of-gamut values cleanly.
- **Audit CVD Colorblindness:** Toggle Deuteranopia, Protanopia, and Tritanopia filters in real-time to see how your palette holds up under human visual deficiencies.
- **Export 36 Component Tokens:** Copy ready-to-use CSS variables, Tailwind tokens, and DTCG design tokens.

> 📷 **[IMAGE STOP 5: Live Brand Test Bench with Dual-Mode Hex / OKLCH Native Sliders]**  
> **What to capture:** A screenshot of the Live Brand Test Bench on `compiler.subtleshoppers.com` showing the interactive sRGB hex picker and native OKLCH Lightness/Chroma/Hue sliders with the Display P3 gamut badge.  
> **Caption:** *Figure 5: The live compiler studio running on the Subtle Shoppers subdomain, featuring dual-mode sRGB and native OKLCH sliders with automatic Display P3 wide-gamut detection.*

> 📷 **[IMAGE STOP 6: Real-Time CVD Colorblindness Simulation & UI Token Storefront]**  
> **What to capture:** A screenshot of the live CVD matrix toggle (Deuteranopia / Protanopia / Tritanopia) or the 36-token interactive UI preview showing buttons, cards, and badges holding their contrast in light and dark modes.  
> **Caption:** *Figure 6: Real-time CVD colorblindness simulation and component testing ensuring primary and secondary brand roles remain clearly distinguishable across all visual conditions.*

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

Input your weirdest, hardest brand colors: the saturated teals, the neon greens, and the bright yellows that usually break every design system. 

Find where our 1.15 curve fails. Criticize our APCA assumptions. Tell me where the tokens feel too opinionated, or open an issue on GitHub to help improve the math.

---

- **Live Compiler Test Bench:** `compiler.subtleshoppers.com`
- **Compiler GitHub Repository:** [SUBSAHARXN/design-system-compiler](https://github.com/SUBSAHARXN/design-system-compiler)
- **Skillbeek Reference App (Live on Vercel):** [skillbeek-app.vercel.app](https://skillbeek-app.vercel.app) · [GitHub Repo](https://github.com/SUBSAHARXN/Skillbeek-App)

*Test the compiler live on the Subtle Shoppers subdomain, inspect the code on [GitHub](https://github.com/SUBSAHARXN/design-system-compiler), and drop your feedback, name ideas, and critique below.*
