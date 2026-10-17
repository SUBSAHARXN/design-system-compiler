# From Olive Sludge to First Principles: How I Built an Autonomous OKLCH Color Compiler with Claude and Antigravity

*The journey from April with Figma plugins like HSL Shader to an autonomous 4-layer compiler that solved the yellow mud trap, fixed our accessibility bias, and surged into the industry top 3.*

---

This project didn't start a few weeks ago. It started back in **April**.

And contrary to what most design system guides tell you, I never handpicked 11-stop color scales in Figma. Nobody has the patience or visual precision to manually tweak 50 through 1000 lightness steps and somehow guarantee they pass WCAG 2.2 AA contrast across both light and dark themes. 

**The only color I ever handpicked was the primary 500.**

To build out the rest of the palette, I was relying on Figma plugins—specifically tools like **HSL Shader** and similar palette generators. If you’ve ever used HSL Shader, you know how seductive the workflow is: you select a single target hex anchor (your 500), and the plugin immediately calculates:
1. A **lighting ramp** (chromatic steps stepping from 1000 down to 50)
2. A **paired grayscale ramp** (showing the luminance distribution of each step)

> 📷 **[Insert Screenshot: Original Figma HSL Shader Exploration]**  
> *Top: Chromatic lighting ramp from 1000 down to 50. Bottom: Paired grayscale luminance ramp.*

On paper, HSL Shader works on the exact same premise as this compiler: **one seed in, an entire lighting ramp out.**

But as soon as you look closely at that screenshot, you see the catastrophic flaw that has plagued design systems for a decade.

Look at stops **700, 800, 900, 950, and 1000** on that top lime/green ramp. 

They don't look like deep, rich brand shadows. **They look like dirty, swampy army-green sludge.**

### Why Palette Plugins Hit an Unavoidable Wall

1. **HSL is mathematically non-perceptual:** HSL treats all hues equally. In HSL math, yellow at 50% lightness is treated as having the exact same luminosity as blue at 50% lightness—even though human photoreceptors perceive yellow as emitting over four times more light.
2. **The static hue trap:** When HSL Shader steps down lightness, it keeps the hue angle locked in place. Pulling lightness down on a green or yellow without rotating the hue forces the color directly into human vision's brown/olive sensitivity trap.
3. **Static pixels vs. living software:** A Figma plugin draws rectangles on a canvas. It doesn't validate contrast. It doesn't know if your button text will be legible on an OLED screen. It doesn't generate CSS variables, Tailwind tokens, or Figma DTCG design tokens.

I realized that plugins weren't enough. What we needed wasn't another Figma widget—we needed an autonomous, deterministic **color compiler** built on first principles. A system where:
- You feed in a brand hex 500 anchor.
- It operates in **OKLCH** (perceptually uniform color space).
- It enforces strict mathematical CI gates that refuse to compile if contrast fails.
- It maps abstract ramps into 36 concrete UI component tokens without manual tweaking.

To build it, I paired with **Claude** and **Antigravity** (Google DeepMind's agentic coding environment). 

We designed a formal four-layer decoupled JSON architecture:
- **Layer 1:** Generation Engine (pure color physics & OKLCH math)
- **Layer 2:** Compiler Contract & CI Gates (accessibility thresholds & validation)
- **Layer 3:** Interaction Physics (hover states, focus rings, shadow physics)
- **Layer 4:** Semantic Taxonomy (mapping primitives to 36 concrete UI component roles)

Then came the first real production trial: **The Skillbeek Test.**

---

## 1. The Skillbeek Test: When the Palette Shattered

The system didn't start with high-minded theory. It started in the middle of a mess.

To test our first compiler contracts, I fed in the brand anchors for **Skillbeek**, an education platform I was working with. Its primary identity was built around `#A952DB` (a vivid violet) and `#4CB33C` (a sharp green).

The output was an immediate wake-up call:
1. **Lightness inversion:** Tonal steps were jumping erratically. A 600 button had less perceptual contrast against text than a 500 button.
2. **APCA contrast failure:** The success fill looked bright to the eye but failed modern readability equations on white backgrounds.
3. **Flat elevation:** The dark mode surfaces had zero perceptual depth—they were lifeless grey slabs.

Having four decoupled JSON layers saved the project right here. In a normal Tailwind config or CSS file, you’d tweak random hex values and accidentally break six other components downstream. Because the architecture was separated, we could trace the contrast failure directly to Layer 2 CI gates and fix the elevation math in Layer 3 without touching the raw brand seeds.

Then came the real beast: **The Olive Sludge Problem.**

---

## 2. The "Olive Sludge" Horror Show (Why Yellows Turn to Mud)

Once Skillbeek was behaving, I tested an amber/yellow warning ramp (`#F3A600`) and a neon lime primary (`#61F300`). 

That’s when our dark mode and shadow states turned utterly revolting.

When you take a blue or violet and darken it, it turns into a gorgeous navy or deep indigo. But when you take yellow or amber (hue angles between 55° and 125°) and lower the lightness in standard sRGB or naive OKLCH, it doesn't turn into a "dark yellow." 

**It turns into dirty, rancid army-green mud.**

```
The Yellow-to-Olive Trap:
Pure Yellow (Lightness 0.90, Hue 95°)  --->  Lightness 0.40, Hue 95°
Result: Dirty Camouflage Sludge (Perceived as rotting olive green)
```

Why does this happen? 
Human vision evolved under sunlight. We have three types of cone photoreceptors in our retinas (L, M, and S). In nature, there is almost no such thing as "dark yellow"—when yellow objects move into shadow, the ambient light and human eye perceive a shift in hue toward warm amber, ochre, or brown. In standard color pickers, keeping the hue constant at 95° while pulling lightness down forces the color directly through the eye's maximum sensitivity zone for green, creating sludge.

### How We Solved It: Convective Hue Drift

We didn't solve this by manually nudging hex codes in Figma. We solved it by encoding human optical biology directly into **Layer 3 (Interaction Physics)**:

```python
# Convective Hue Drift Algorithm (Layer 3)
if 55.0 <= hue <= 125.0:  # Yellow / Lime hazard band
    lightness_deficit = max(0.0, 0.70 - current_lightness)
    # Dynamically rotate hue toward warm amber (45°) as lightness drops
    convective_hue_shift = (45.0 - hue) * (lightness_deficit / 0.70) * 0.45
    corrected_hue = hue + convective_hue_shift
```

As an amber or yellow gets darker (like for button hover, active states, or dark-mode borders), the compiler automatically rotates its hue toward warm orange/amber (`45°`). 

The result? The mud vanished. Yellows now degrade into rich, warm cognac, honey, and amber tones that look alive and premium.

---

## 3. The Benchmark Wake-Up Call: Our Accessibility Bias

Once the compiler produced beautiful ramps and passed every WCAG check, we felt invincible. We decided to build a reproducible, automated benchmark suite (`expanded_rigorous_benchmark.py`) to pit our compiler against nine industry giants:
- IBM Carbon
- Google Material Design 3 (M3)
- GitHub Primer
- Microsoft Fluent 2
- Adobe Spectrum
- Tailwind CSS
- Apple Human Interface Guidelines (HIG)
- Radix Colors

We scored each design system across six mathematical metrics:
1. **WCAG 2.2 AA Pass Rate** (% of semantic pairs passing contrast)
2. **APCA Mean Readability (Lc)** (Advanced Perceptual Contrast Algorithm score)
3. **Linearity Error (StdDev)** (How predictable and uniform the lightness steps are)
4. **Muddy Shadow Stops** (Number of hue stops trapped in the olive mud zone)
5. **CVD Deutan Colorblind Separation (ΔE)** (Readability under red-green colorblindness)
6. **OLED Glare Ceiling Compliance** (Preventing 100% pitch-black eye strain)

### The Disappointing First Run

When the Python benchmark finished, our compiler took **#1 in APCA Readability (101.9 Lc)** and **#1 in WCAG 2.2 AA (100.0%)**.

**But our overall composite score was humiliatingly mediocre.** We were sitting way down near the middle of the pack.

Why? **Accessibility bias.**

We had become so obsessed with guaranteeing that *every single token pair* passed APCA Lc 60 and WCAG 4.5:1 that we were violently warping the lightness curve between stops 400, 500, and 600. To pass contrast on dark backgrounds, we shoved stop 400 upward. To pass on light backgrounds, we shoved stop 600 downward. 

The contrast passed, but the **mathematical linearity was destroyed**. The delta-L steps were jagged. IBM Carbon crushed us on linearity error (Carbon: `0.0133`, Our initial build: `0.0520`).

We had built the color equivalent of an engine that had immense horsepower but terrible suspension.

### The Data-Driven Fix

We went back into Layer 1 (Generation Engine) with Claude and Antigravity. Instead of arbitrary piecewise hacks, we replaced the ramp distribution with a continuous **1.15 Power Curve**:

```
Lightness(step) = 1.0 - (step / 1000) ^ 1.15
```

This single mathematical formulation smoothed the delta-L transition while naturally hitting the required contrast thresholds at stops 100, 500, 700, and 900.

We re-ran the automated benchmark across all nine systems.

**The result:**
- Linearity error dropped from `0.0520` down to `0.0333`
- WCAG 2.2 AA stayed at **100.0%**
- APCA Readability held the **#1 industry spot at 101.9 Lc**
- **Composite Score rose to 78.5 / 100**, leaping over GitHub Primer (78.3), Microsoft Fluent 2 (77.4), and Tailwind (76.3) to claim **Rank #3 overall**, right behind IBM Carbon (83.6) and Google Material 3 (81.7).

Here is the exact benchmark table generated by the audit suite:

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

*(Note: IBM Carbon’s ultra-flat linearity won it #1 overall, but our compiler took the undisputed crown for human reading clarity at 101.9 Lc).*

---

## 4. Visuals on Medium: Why Images Beat Code Embeds

A quick note on how I’m formatting this story and how you should share technical color work on Medium.

A lot of engineers reach for interactive CodePens or iframe embeds. On Medium, **interactive canvas or CSS embeds are clunky or completely unsupported**. Readers reading on their phones will hit broken iframes or unreadable code snippets.

For color physics, **high-contrast side-by-side images always win:**
1. **The Before/After Mud Swatch:** A simple visual comparing a 95° yellow darkening into olive sludge versus our convective hue drift darkening into honey amber. You don't need words; the eye immediately understands the bug.
2. **The Dual-Mode Color Picker UI:** A clean screenshot of the test bench showing live Display P3 gamut boundaries and OKLCH Lightness/Chroma/Hue sliders.
3. **The Benchmark Matrix:** The clean table screenshot showing our system standing shoulder-to-shoulder with IBM Carbon and Material 3.

---

## 5. "4-Layer Compiler" is a Terrible Name. Help Me Name It.

Right now, the project repo and architecture are called the **4-Layer OKLCH Design System Compiler**. 

Let’s be honest: that is an excruciatingly boring, utilitarian engineering working title. It sounds like an internal enterprise document from 2004.

I don’t have a good brand name for it yet. Some ideas that floated around:
- *Specter* (or *SpectraCore*)
- *PrismEngine*
- *ChromaLoom*
- *OklchOS*
- *Percepta*

If you have an idea for what a first-principles, mathematical color compiler should be called, drop it in the responses. I'm completely open to suggestions.

---

## 6. Tear It Apart: An Open Invitation

This system wasn't built in an ivory tower. It was built by breaking things in public, finding bugs with Skillbeek, getting humbled by IBM Carbon’s linearity, and rewriting math in Python and JavaScript until the gates turned green.

Everything is public and open source:
- **Interactive Live Showcase & Test Bench:** Test your own brand hex codes or native OKLCH values in real-time, toggle CVD colorblindness filters, and inspect the 36 UI component tokens.
- **GitHub Repository:** [SUBSAHARXN/design-system-compiler](https://github.com/SUBSAHARXN/design-system-compiler)
- **Benchmark Suite:** The complete Python script (`benchmarks/expanded_rigorous_benchmark.py`) is in the repo so you can run the exact same tests on your own design system.

I want you to test this. Input your weirdest, most difficult brand colors—the saturated teals, the neon greens, the hyper-bright yellows that usually break every design system. 

Find where our math fails. Criticize our 1.15 power curve. Tell me why our APCA thresholds are too strict, or open a pull request to make the gamut-mapping faster. 

Good systems aren't built on faith—they're built by compilers that refuse to lie.

---

*Found a bug or want to suggest a name? Drop a response below or open an issue on [GitHub](https://github.com/SUBSAHARXN/design-system-compiler).*
