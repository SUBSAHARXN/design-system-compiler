// 4-Layer OKLCH Design System Compiler Showcase Logic

// Constant ramp stops and envelopes from Layer 1 v10.5
const ALL_STOPS = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950, 1000];
const ENV = {
  50: 0.16, 100: 0.38, 200: 0.62, 300: 0.83, 400: 0.95,
  500: 1.00, 600: 0.95, 700: 0.84, 800: 0.65, 900: 0.42,
  950: 0.25, 1000: 0.10
};

const PG_L = {
  50: 0.98, 100: 0.94, 200: 0.88, 300: 0.75, 400: 0.62,
  500: 0.48, 600: 0.40, 700: 0.30, 800: 0.22, 900: 0.19,
  950: 0.17, 1000: 0.05
};

// ── OKLCH ↔ sRGB Mathematical Engine ──
function hexToRgb(hex) {
  hex = hex.replace('#', '');
  if (hex.length === 3) hex = hex.split('').map(c => c + c).join('');
  const num = parseInt(hex, 16);
  return [(num >> 16) / 255, ((num >> 8) & 255) / 255, (num & 255) / 255];
}

function rgbToHex(r, g, b) {
  const toHex = v => Math.round(Math.max(0, Math.min(1, v)) * 255).toString(16).padStart(2, '0').toUpperCase();
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

function toLinear(c) {
  return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}

function fromLinear(c) {
  c = Math.max(0, Math.min(1, c));
  return c <= 0.0031308 ? c * 12.92 : 1.055 * Math.pow(c, 1 / 2.4) - 0.055;
}

function hexToOklch(hex) {
  const [r, g, b] = hexToRgb(hex);
  const rl = toLinear(r), gl = toLinear(g), bl = toLinear(b);

  const x = 0.4124564 * rl + 0.3575761 * gl + 0.1804375 * bl;
  const y = 0.2126729 * rl + 0.7151522 * gl + 0.0721750 * bl;
  const z = 0.0193339 * rl + 0.1191920 * gl + 0.9503041 * bl;

  const lm = 0.8189330101 * x + 0.3618667424 * y - 0.1288597137 * z;
  const mm = 0.0329845436 * x + 0.9293118715 * y + 0.0361456387 * z;
  const sm = 0.0482003018 * x + 0.2643662691 * y + 0.6338517070 * z;

  const lp = Math.cbrt(lm);
  const mp = Math.cbrt(mm);
  const sp = Math.cbrt(sm);

  const L = 0.2104542553 * lp + 0.7936177850 * mp - 0.0040720468 * sp;
  const a = 1.9779984951 * lp - 2.4285922050 * mp + 0.4505937099 * sp;
  const bk = 0.0259040371 * lp + 0.7827717662 * mp - 0.8086757660 * sp;

  const C = Math.sqrt(a * a + bk * bk);
  let H = (Math.atan2(bk, a) * 180 / Math.PI);
  if (H < 0) H += 360;

  return { L, C, H };
}

function oklchToLinearRgb(L, C, H) {
  const rad = H * Math.PI / 180;
  const a = C * Math.cos(rad);
  const b = C * Math.sin(rad);

  const lp = L + 0.3963377774 * a + 0.2158037573 * b;
  const mp = L - 0.1055613458 * a - 0.0638541728 * b;
  const sp = L - 0.0894841775 * a - 1.2914855480 * b;

  const lc = lp * lp * lp;
  const mc = mp * mp * mp;
  const sc = sp * sp * sp;

  const x = 1.2270138511 * lc - 0.5577999807 * mc + 0.2812561490 * sc;
  const y = -0.0405801784 * lc + 1.1122568696 * mc - 0.0716766787 * sc;
  const z = -0.0763812845 * lc - 0.4214819784 * mc + 1.5861632204 * sc;

  const rl = 3.2404542 * x - 1.5371385 * y - 0.4985314 * z;
  const gl = -0.9692660 * x + 1.8760108 * y + 0.0415560 * z;
  const bl = 0.0556434 * x - 0.2040259 * y + 1.0572252 * z;

  return [rl, gl, bl];
}

function gamutSafeOklchToHex(L, C, H) {
  let curC = C;
  let [rl, gl, bl] = oklchToLinearRgb(L, curC, H);

  while ((rl < 0 || rl > 1 || gl < 0 || gl > 1 || bl < 0 || bl > 1) && curC > 0) {
    curC -= 0.001;
    if (curC < 0) curC = 0;
    [rl, gl, bl] = oklchToLinearRgb(L, curC, H);
  }

  return rgbToHex(fromLinear(rl), fromLinear(gl), fromLinear(bl));
}

function classifyHue(H) {
  if (H >= 85 && H < 110) {
    // Yellow zone: anti-mud convex rotation to warm amber (H 45°-48°)
    return { s: 0.22, p: 0.26, t: 0.16, dL: 8, dD: -36, b: 'yellow-optimized' };
  } else if (H >= 240 && H < 290) {
    return { s: 0.25, p: 0.32, t: 0.20, dL: -8, dD: 10, b: 'blue-optimized' };
  } else if (H >= 110 && H < 170) {
    // Green zone (e.g. Subtle Shoppers 61F300)
    return { s: 0.25, p: 0.28, t: 0.18, dL: 6, dD: -8, b: 'green-optimized' };
  } else {
    return { s: 0.24, p: 0.28, t: 0.17, dL: 0, dD: 0, b: 'standard' };
  }
}

// ── Dynamic 11-Stop Ramp Builder ──
function buildRamp(brandHex, grey = false, greyHue = 138) {
  const { L: bL, C: bC, H: bH } = hexToOklch(brandHex);
  const f = classifyHue(bH);
  const ramp = {};

  let L_MAX = 0.98, L_MIN = 0.05;
  if (!grey && f.b === 'yellow-optimized') {
    L_MAX = 0.97; L_MIN = 0.10;
  }

  ALL_STOPS.forEach(stop => {
    let L;
    if (grey) {
      L = PG_L[stop];
    } else if (stop === 500) {
      L = bL;
    } else if (stop < 500) {
      const t = (500 - stop) / 450.0;
      L = bL + (L_MAX - bL) * (1 - Math.pow(1 - t, 1.15)); // Linear exponent 1.15
    } else {
      const t = (stop - 500) / 500.0;
      L = bL - (bL - L_MIN) * (1 - Math.pow(1 - t, 1.15));
    }

    const bezE = ENV[stop];
    let Hu = grey ? greyHue : bH;
    let Cr = grey ? 0.010 : (bC * bezE);

    if (!grey) {
      const Cf = Math.min(Cr, f.s);
      const dr = bC - f.t;
      const factor = dr > 0 ? Math.max(0.35, Math.min(1.0, (Cf - f.t) / dr)) : 0.5;
      if (stop < 500) {
        const t_light = (500 - stop) / 450.0;
        Hu = bH + f.dL * factor * Math.pow(t_light, 1.1);
      } else if (stop > 500) {
        const t_dark = (stop - 500) / 500.0;
        const exp_dark = f.b === 'yellow-optimized' ? 0.65 : 1.1;
        Hu = bH + f.dD * factor * Math.pow(t_dark, exp_dark);
      }
    }

    const C_srgb = grey ? Cr : Math.min(Cr, f.s);
    const hex = gamutSafeOklchToHex(L, C_srgb, Hu);

    ramp[stop] = {
      hex,
      L: Math.round(L * 1000) / 1000,
      C: Math.round(C_srgb * 1000) / 1000,
      H: Math.round(Hu * 10) / 10,
      p3Expanded: bC > f.s
    };
  });

  return ramp;
}

// ── Application State ──
const STATE = {
  theme: 'dark',
  primaryHex: '#61F300',
  secondaryHex: '#F3A600',
  cvdFilter: 'none',
  ramps: {}
};

// ── Recompute All Ramps & Bindings ──
function recompileDesignSystem() {
  const pRamp = buildRamp(STATE.primaryHex);
  const sRamp = buildRamp(STATE.secondaryHex);
  const infoRamp = buildRamp('#3758BF');
  const successRamp = buildRamp('#2FA836'); // Layer 2 anchor: Deutan separation 0.1016
  const errorRamp = buildRamp('#BA3430');   // Layer 2 anchor: Protan separation 0.2600
  const warningRamp = buildRamp('#B85F38'); // Shifted to avoid yellow collision
  const pgRamp = buildRamp(STATE.primaryHex, true, 138); // Neutral slate
  const sgRamp = buildRamp(STATE.secondaryHex, true, 74); // Neutral warm

  STATE.ramps = {
    primary: pRamp,
    secondary: sRamp,
    info: infoRamp,
    success: successRamp,
    warning: warningRamp,
    error: errorRamp,
    pg: pgRamp,
    sg: sgRamp
  };

  renderRamps();
  injectSemanticTokens();
  updateCvdLens();
}

// ── Render Swatches UI ──
function renderRamps() {
  const container = document.getElementById('ramps-container');
  if (!container) return;
  container.innerHTML = '';

  Object.entries(STATE.ramps).forEach(([rampName, stops]) => {
    const card = document.createElement('div');
    card.className = 'ramp-card';

    const header = document.createElement('div');
    header.className = 'ramp-header';
    header.innerHTML = `
      <div class="ramp-meta">
        <span class="ramp-name">${rampName}</span>
        <span class="ramp-badge">Stop 500: ${stops[500].hex}</span>
        <span class="ramp-badge">L: ${stops[500].L} · C: ${stops[500].C} · H: ${stops[500].H}°</span>
      </div>
    `;

    const strip = document.createElement('div');
    strip.className = 'swatches-strip';

    ALL_STOPS.forEach(stop => {
      const data = stops[stop];
      const isLight = data.L > 0.65;
      const swatch = document.createElement('div');
      swatch.className = 'swatch';
      swatch.style.backgroundColor = data.hex;
      swatch.style.color = isLight ? '#0d100c' : '#ffffff';
      swatch.title = `Stop ${stop}: ${data.hex} (Click to copy)\nOKLCH: L=${data.L}, C=${data.C}, H=${data.H}°`;

      swatch.innerHTML = `
        <span class="swatch-stop">${stop}</span>
        <span class="swatch-hex">${data.hex}</span>
        ${data.p3Expanded && stop >= 400 && stop <= 700 ? '<span class="p3-dot" title="Wide-gamut P3 enhanced"></span>' : ''}
      `;

      swatch.addEventListener('click', () => {
        navigator.clipboard.writeText(data.hex);
        showToast(`Copied ${rampName}.${stop}: ${data.hex}`);
      });

      strip.appendChild(swatch);
    });

    card.appendChild(header);
    card.appendChild(strip);
    container.appendChild(card);
  });
}

// ── Inject CSS Custom Properties into Sandbox ──
function injectSemanticTokens() {
  const p = STATE.ramps.primary;
  const s = STATE.ramps.secondary;
  const pg = STATE.ramps.pg;
  const success = STATE.ramps.success;
  const error = STATE.ramps.error;
  const warning = STATE.ramps.warning;
  const info = STATE.ramps.info;

  const root = document.documentElement;

  if (STATE.theme === 'dark') {
    root.style.setProperty('--color-bg', pg[950].hex);
    root.style.setProperty('--color-surface', '#10130f');
    root.style.setProperty('--color-surface-raised', '#141813');
    root.style.setProperty('--color-surface-subtle', '#10130f');
    root.style.setProperty('--color-text-primary', pg[50].hex);
    root.style.setProperty('--color-text-secondary', pg[200].hex);
    root.style.setProperty('--color-border-default', pg[600].hex);
    root.style.setProperty('--color-border-subtle', pg[700].hex);

    root.style.setProperty('--color-fill-brand', p[400].hex);
    root.style.setProperty('--color-on-fill-brand', p[950].hex);
    root.style.setProperty('--color-fill-secondary', s[500].hex);
    root.style.setProperty('--color-on-fill-secondary', s[950].hex);

    root.style.setProperty('--color-fill-success', success[500].hex);
    root.style.setProperty('--color-fill-success-subtle', success[900].hex);
    root.style.setProperty('--color-text-success', success[200].hex);
    root.style.setProperty('--color-border-success', success[500].hex);

    root.style.setProperty('--color-fill-error', error[500].hex);
    root.style.setProperty('--color-fill-error-subtle', error[900].hex);
    root.style.setProperty('--color-text-error', error[200].hex);
    root.style.setProperty('--color-border-error', error[500].hex);

    root.style.setProperty('--color-fill-warning', warning[500].hex);
    root.style.setProperty('--color-fill-warning-subtle', warning[900].hex);
    root.style.setProperty('--color-text-warning', warning[200].hex);
    root.style.setProperty('--color-border-warning', warning[500].hex);

    root.style.setProperty('--color-fill-info', info[500].hex);
    root.style.setProperty('--color-fill-info-subtle', info[900].hex);
    root.style.setProperty('--color-text-info', info[200].hex);
    root.style.setProperty('--color-border-info', info[500].hex);
  } else {
    root.style.setProperty('--color-bg', pg[50].hex);
    root.style.setProperty('--color-surface', '#ffffff');
    root.style.setProperty('--color-surface-raised', '#ffffff');
    root.style.setProperty('--color-surface-subtle', pg[100].hex);
    root.style.setProperty('--color-text-primary', pg[950].hex);
    root.style.setProperty('--color-text-secondary', pg[700].hex);
    root.style.setProperty('--color-border-default', pg[300].hex);
    root.style.setProperty('--color-border-subtle', pg[200].hex);

    root.style.setProperty('--color-fill-brand', p[500].hex);
    root.style.setProperty('--color-on-fill-brand', p[950].hex);
    root.style.setProperty('--color-fill-secondary', s[300].hex);
    root.style.setProperty('--color-on-fill-secondary', s[900].hex);

    root.style.setProperty('--color-fill-success', success[500].hex);
    root.style.setProperty('--color-fill-success-subtle', success[50].hex);
    root.style.setProperty('--color-text-success', success[700].hex);
    root.style.setProperty('--color-border-success', success[400].hex);

    root.style.setProperty('--color-fill-error', error[500].hex);
    root.style.setProperty('--color-fill-error-subtle', error[50].hex);
    root.style.setProperty('--color-text-error', error[700].hex);
    root.style.setProperty('--color-border-error', error[400].hex);

    root.style.setProperty('--color-fill-warning', warning[500].hex);
    root.style.setProperty('--color-fill-warning-subtle', warning[50].hex);
    root.style.setProperty('--color-text-warning', warning[800].hex);
    root.style.setProperty('--color-border-warning', warning[400].hex);

    root.style.setProperty('--color-fill-info', info[500].hex);
    root.style.setProperty('--color-fill-info-subtle', info[50].hex);
    root.style.setProperty('--color-text-info', info[700].hex);
    root.style.setProperty('--color-border-info', info[400].hex);
  }
}

// ── CVD Simulation Filter Handler ──
function updateCvdLens() {
  const stage = document.getElementById('cvd-stage');
  if (!stage) return;

  switch (STATE.cvdFilter) {
    case 'deuteranopia':
      stage.style.filter = 'url(#deuteranopia-filter)';
      break;
    case 'protanopia':
      stage.style.filter = 'url(#protanopia-filter)';
      break;
    case 'tritanopia':
      stage.style.filter = 'url(#tritanopia-filter)';
      break;
    case 'achromatopsia':
      stage.style.filter = 'grayscale(100%)';
      break;
    default:
      stage.style.filter = 'none';
  }
}

// ── Toast Notification ──
function showToast(msg) {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 2400);
}

// ── Initialization & Event Listeners ──
document.addEventListener('DOMContentLoaded', () => {
  // Theme toggle
  const themeToggle = document.getElementById('theme-toggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      STATE.theme = STATE.theme === 'dark' ? 'light' : 'dark';
      document.body.setAttribute('data-theme', STATE.theme);
      themeToggle.textContent = STATE.theme === 'dark' ? '☀️ Light' : '🌙 Dark';
      injectSemanticTokens();
    });
  }

  // Brand Color Inputs
  const pInput = document.getElementById('primary-picker');
  const pHex = document.getElementById('primary-hex');
  const sInput = document.getElementById('secondary-picker');
  const sHex = document.getElementById('secondary-hex');

  function syncPrimary(hex) {
    if (!/^#[0-9A-Fa-f]{6}$/.test(hex)) return;
    STATE.primaryHex = hex;
    pInput.value = hex;
    pHex.value = hex;
    recompileDesignSystem();
  }

  function syncSecondary(hex) {
    if (!/^#[0-9A-Fa-f]{6}$/.test(hex)) return;
    STATE.secondaryHex = hex;
    sInput.value = hex;
    sHex.value = hex;
    recompileDesignSystem();
  }

  pInput.addEventListener('input', e => syncPrimary(e.target.value));
  pHex.addEventListener('change', e => syncPrimary(e.target.value.startsWith('#') ? e.target.value : '#' + e.target.value));
  sInput.addEventListener('input', e => syncSecondary(e.target.value));
  sHex.addEventListener('change', e => syncSecondary(e.target.value.startsWith('#') ? e.target.value : '#' + e.target.value));

  // Presets
  const presets = {
    'subtleshoppers': { p: '#61F300', s: '#F3A600' },
    'skillbeek': { p: '#B7812F', s: '#3B82F6' },
    'cyberpunk': { p: '#00F5D4', s: '#7B2CBF' },
    'nordic': { p: '#4361EE', s: '#F72585' }
  };

  document.querySelectorAll('[data-preset]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('[data-preset]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const key = btn.getAttribute('data-preset');
      const target = presets[key];
      if (target) {
        syncPrimary(target.p);
        syncSecondary(target.s);
      }
    });
  });

  // CVD Filter Buttons
  document.querySelectorAll('[data-cvd]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('[data-cvd]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      STATE.cvdFilter = btn.getAttribute('data-cvd');
      updateCvdLens();
    });
  });

  // Initial Compile
  document.body.setAttribute('data-theme', STATE.theme);
  recompileDesignSystem();
});
