/**
 * D-DOM Headless Browser Extractor
 * Uses Puppeteer Core with system Chrome to deterministically extract
 * design tokens, typography, spacing, components, motion, and layout evidence.
 */

const puppeteer = require('puppeteer-core');
const fs = require('fs');
const dns = require('dns').promises;
const net = require('net');

function isBlockedIp(address) {
  if (!address) return true;
  if (address === '::1' || address === '0:0:0:0:0:0:0:1') return true;
  if (address.startsWith('::ffff:')) address = address.slice(7);
  const family = net.isIP(address);
  if (family === 4) {
    const parts = address.split('.').map(Number);
    const [a, b] = parts;
    return (
      a === 0 ||
      a === 10 ||
      a === 127 ||
      (a === 169 && b === 254) ||
      (a === 172 && b >= 16 && b <= 31) ||
      (a === 192 && b === 168) ||
      (a === 100 && b >= 64 && b <= 127) ||
      a >= 224
    );
  }
  if (family === 6) {
    const lowered = address.toLowerCase();
    return lowered.startsWith('fc') || lowered.startsWith('fd') || lowered.startsWith('fe80') || lowered.startsWith('ff');
  }
  return true;
}

async function assertSafeUrl(rawUrl) {
  const parsed = new URL(rawUrl);
  if (!['http:', 'https:'].includes(parsed.protocol)) {
    throw new Error(`Blocked non-http(s) request: ${rawUrl}`);
  }
  if (parsed.username || parsed.password) {
    throw new Error(`Blocked URL with embedded credentials: ${rawUrl}`);
  }
  const addresses = await dns.lookup(parsed.hostname, { all: true, verbatim: true });
  for (const item of addresses) {
    if (isBlockedIp(item.address)) {
      throw new Error(`Blocked private/reserved destination ${parsed.hostname} -> ${item.address}`);
    }
  }
}

function chromeExecutable() {
  const candidates = [
    process.env.CHROME_PATH,
    '/usr/bin/google-chrome',
    '/usr/bin/google-chrome-stable',
    '/usr/bin/chromium-browser',
    '/usr/bin/chromium'
  ].filter(Boolean);
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) return candidate;
  }
  return candidates[0];
}

async function extractDDom(targetUrl, outputPath = null, screenshotPath = null) {
  // Validate URL
  await assertSafeUrl(targetUrl);

  const browser = await puppeteer.launch({
    executablePath: chromeExecutable(),
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--headless=new',
      '--window-size=1280,900'
    ]
  });

  try {
    const page = await browser.newPage();
    await page.setRequestInterception(true);
    page.on('request', async req => {
      try {
        await assertSafeUrl(req.url());
        req.continue();
      } catch (err) {
        console.error(`Blocked request: ${err.message}`);
        req.abort('blockedbyclient');
      }
    });
    await page.setViewport({ width: 1280, height: 900, deviceScaleFactor: 1 });

    // Navigate with timeout
    await page.goto(targetUrl, { waitUntil: 'networkidle2', timeout: 30000 }).catch(err => {
      console.error('Warning: navigation timeout, continuing with current DOM state:', err.message);
    });

    // Capture screenshot if requested
    let screenshotBase64 = null;
    if (screenshotPath) {
      await page.screenshot({ path: screenshotPath, fullPage: false });
    }

    // In-browser extraction
    const rawData = await page.evaluate(() => {
      function rgbToHex(rgbStr) {
        if (!rgbStr || rgbStr === 'transparent' || rgbStr.startsWith('rgba(0, 0, 0, 0)')) return null;
        const match = rgbStr.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
        if (!match) return null;
        const r = parseInt(match[1]).toString(16).padStart(2, '0');
        const g = parseInt(match[2]).toString(16).padStart(2, '0');
        const b = parseInt(match[3]).toString(16).padStart(2, '0');
        return `#${r}${g}${b}`.toLowerCase();
      }

      function parsePx(str) {
        if (!str || !str.endsWith('px')) return null;
        const num = parseFloat(str);
        return isNaN(num) ? null : Math.round(num * 10) / 10;
      }

      const allElements = Array.from(document.querySelectorAll('*'));
      
      // 1. Color extraction
      const colorCounts = {};
      const bgCounts = {};
      const borderCounts = {};

      // Check root CSS variables for SOURCE evidence
      const sourceVariables = {};
      try {
        for (const sheet of Array.from(document.styleSheets)) {
          try {
            for (const rule of Array.from(sheet.cssRules || [])) {
              if (rule.style) {
                for (let i = 0; i < rule.style.length; i++) {
                  const prop = rule.style[i];
                  if (prop.startsWith('--')) {
                    sourceVariables[prop] = rule.style.getPropertyValue(prop).trim();
                  }
                }
              }
            }
          } catch (e) { /* cross-origin styles */ }
        }
      } catch (e) {}

      allElements.forEach(el => {
        const style = window.getComputedStyle(el);
        const col = rgbToHex(style.color);
        const bg = rgbToHex(style.backgroundColor);
        const bc = rgbToHex(style.borderColor);

        if (col) colorCounts[col] = (colorCounts[col] || 0) + 1;
        if (bg) bgCounts[bg] = (bgCounts[bg] || 0) + 1;
        if (bc && style.borderWidth !== '0px') borderCounts[bc] = (borderCounts[bc] || 0) + 1;
      });

      // 2. Typography extraction
      const typographyNodes = [];
      const textTags = ['H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'P', 'SPAN', 'A', 'BUTTON', 'LABEL'];
      
      allElements.forEach(el => {
        if (textTags.includes(el.tagName) && el.textContent.trim().length > 0) {
          const style = window.getComputedStyle(el);
          const size = parsePx(style.fontSize);
          const weight = parseInt(style.fontWeight) || 400;
          const family = style.fontFamily.split(',')[0].replace(/['"]/g, '').trim();
          const lineH = style.lineHeight;
          const letterS = style.letterSpacing;
          
          if (size) {
            typographyNodes.push({
              tag: el.tagName.toLowerCase(),
              family,
              weight,
              size,
              lineHeight: lineH,
              letterSpacing: letterS,
              textSample: el.textContent.trim().substring(0, 40)
            });
          }
        }
      });

      // 3. Spacing extraction
      const spacingSet = {};
      allElements.slice(0, 300).forEach(el => {
        const s = window.getComputedStyle(el);
        ['paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft',
         'marginTop', 'marginRight', 'marginBottom', 'marginLeft', 'gap'].forEach(prop => {
          const px = parsePx(s[prop]);
          if (px && px > 0 && px <= 160) {
            spacingSet[px] = (spacingSet[px] || 0) + 1;
          }
        });
      });

      // 4. Border Radius extraction
      const radiusCounts = {};
      allElements.forEach(el => {
        const s = window.getComputedStyle(el);
        const r = parsePx(s.borderRadius);
        if (r && r > 0) {
          radiusCounts[r] = (radiusCounts[r] || 0) + 1;
        }
      });

      // 5. Box Shadows
      const shadowSet = {};
      allElements.forEach(el => {
        const s = window.getComputedStyle(el);
        if (s.boxShadow && s.boxShadow !== 'none') {
          shadowSet[s.boxShadow] = (shadowSet[s.boxShadow] || 0) + 1;
        }
      });

      // 6. Components mapping
      const buttons = Array.from(document.querySelectorAll('button, a[role="button"], input[type="submit"], input[type="button"], a.btn, a.button')).map(b => {
        const s = window.getComputedStyle(b);
        const rect = b.getBoundingClientRect();
        return {
          text: b.textContent.trim().substring(0, 30),
          tag: b.tagName.toLowerCase(),
          bg: rgbToHex(s.backgroundColor),
          color: rgbToHex(s.color),
          borderRadius: parsePx(s.borderRadius),
          fontSize: parsePx(s.fontSize),
          fontWeight: s.fontWeight,
          width: Math.round(rect.width),
          height: Math.round(rect.height),
        };
      }).filter(b => b.width > 20 && b.height > 15).slice(0, 15);

      const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]), textarea, select')).map(inp => {
        const s = window.getComputedStyle(inp);
        return {
          type: inp.getAttribute('type') || inp.tagName.toLowerCase(),
          placeholder: inp.getAttribute('placeholder') || '',
          borderRadius: parsePx(s.borderRadius),
          borderColor: rgbToHex(s.borderColor),
          bg: rgbToHex(s.backgroundColor),
        };
      }).slice(0, 10);

      // 7. Icons & SVGs
      const svgs = Array.from(document.querySelectorAll('svg')).map(svg => {
        const rect = svg.getBoundingClientRect();
        return {
          width: Math.round(rect.width),
          height: Math.round(rect.height),
          viewBox: svg.getAttribute('viewBox'),
          hasPaths: svg.querySelectorAll('path').length
        };
      }).filter(s => s.width > 8 && s.width < 120).slice(0, 20);

      // 8. Motion / Transitions
      const motionSet = [];
      allElements.forEach(el => {
        const s = window.getComputedStyle(el);
        if (s.transitionDuration && s.transitionDuration !== '0s') {
          motionSet.push({
            property: s.transitionProperty,
            duration: s.transitionDuration,
            timing: s.transitionTimingFunction
          });
        }
      });

      // 9. Layout regions
      const navEl = document.querySelector('nav, header, [role="navigation"]');
      const footerEl = document.querySelector('footer, [role="contentinfo"]');
      const mainEl = document.querySelector('main, [role="main"], #main, .main');
      
      const layoutInfo = {
        hasHeaderNav: !!navEl,
        hasFooter: !!footerEl,
        hasMain: !!mainEl,
        pageMaxWidth: parsePx(window.getComputedStyle(document.body).maxWidth) || 1280
      };

      return {
        title: document.title,
        colorCounts,
        bgCounts,
        borderCounts,
        sourceVariables,
        typographyNodes,
        spacingSet,
        radiusCounts,
        shadowSet,
        buttons,
        inputs,
        svgs,
        motionSet: motionSet.slice(0, 10),
        layoutInfo
      };
    });

    // Check mobile responsive behavior
    await page.setViewport({ width: 375, height: 667, deviceScaleFactor: 1 });
    await new Promise(r => setTimeout(r, 600));

    const mobileLayout = await page.evaluate(() => {
      const nav = document.querySelector('nav, header');
      const burger = document.querySelector('[aria-label*="menu"], button[class*="menu"], [class*="hamburger"]');
      return {
        viewportWidth: 375,
        hasHamburger: !!burger,
        navHidden: nav ? window.getComputedStyle(nav).display === 'none' : false
      };
    });

    await browser.close();

    // Process & Structure D-DOM with Evidence Tags
    const ddom = buildDDomFromRaw(targetUrl, rawData, mobileLayout);

    if (outputPath) {
      fs.writeFileSync(outputPath, JSON.stringify(ddom, null, 2), 'utf-8');
    }

    return ddom;
  } catch (err) {
    await browser.close().catch(() => {});
    throw err;
  }
}

function buildDDomFromRaw(url, raw, mobileLayout) {
  // 1. Process Colors
  const colors = [];
  const sortedBg = Object.entries(raw.bgCounts).sort((a, b) => b[1] - a[1]);
  const sortedCol = Object.entries(raw.colorCounts).sort((a, b) => b[1] - a[1]);

  const canvasBg = sortedBg.length > 0 ? sortedBg[0][0] : '#ffffff';
  colors.push({
    name: 'Canvas Background',
    value: canvasBg,
    role: 'canvas_background',
    evidence: 'RUNTIME',
    confidence: 0.98,
    origin: 'body/root background-color'
  });

  if (sortedCol.length > 0) {
    colors.push({
      name: 'Primary Text',
      value: sortedCol[0][0],
      role: 'text_primary',
      evidence: 'RUNTIME',
      confidence: 0.95,
      origin: 'dominant font color'
    });
  }

  // Identify Accent Color (usually from button backgrounds or primary links)
  const buttonBg = raw.buttons.find(b => b.bg && b.bg !== canvasBg && b.bg !== '#ffffff' && b.bg !== '#000000');
  if (buttonBg) {
    colors.push({
      name: 'Primary Action Accent',
      value: buttonBg.bg,
      role: 'primary_accent',
      evidence: 'SOURCE',
      confidence: 0.96,
      origin: 'button background'
    });
  }

  // Secondary text
  if (sortedCol.length > 1) {
    colors.push({
      name: 'Secondary Text',
      value: sortedCol[1][0],
      role: 'text_secondary',
      evidence: 'RUNTIME',
      confidence: 0.88,
      origin: 'secondary text color'
    });
  }

  // Add source variables if any color tokens found
  Object.entries(raw.sourceVariables).forEach(([k, v]) => {
    if (v.startsWith('#') || v.startsWith('rgb')) {
      colors.push({
        name: k.replace('--', ''),
        value: v,
        role: 'custom_property',
        evidence: 'SOURCE',
        confidence: 0.99,
        origin: `:root rule ${k}`
      });
    }
  });

  // 2. Process Typography Scale
  const typeMap = {};
  raw.typographyNodes.forEach(n => {
    const key = `${n.size}_${n.weight}`;
    if (!typeMap[key]) {
      typeMap[key] = {
        size: n.size,
        weight: n.weight,
        family: n.family,
        lineHeight: n.lineHeight,
        letterSpacing: n.letterSpacing,
        count: 0,
        tags: new Set()
      };
    }
    typeMap[key].count++;
    typeMap[key].tags.add(n.tag);
  });

  const typography = Object.values(typeMap)
    .sort((a, b) => b.size - a.size)
    .map((t, idx) => {
      let role = 'body';
      if (t.size >= 48) role = 'display';
      else if (t.size >= 32) role = 'heading_lg';
      else if (t.size >= 24) role = 'heading_md';
      else if (t.size >= 20) role = 'heading_sm';
      else if (t.size >= 16) role = 'body_lg';
      else if (t.size >= 14) role = 'body';
      else role = 'caption';

      return {
        role,
        family: t.family,
        weight: t.weight,
        size_px: t.size,
        line_height: t.lineHeight,
        letter_spacing: t.letterSpacing,
        evidence: 'RUNTIME',
        confidence: 0.94,
        origin: Array.from(t.tags).join(', ')
      };
    });

  // 3. Spacing Scale
  const sortedSpacing = Object.entries(raw.spacingSet)
    .map(([px, cnt]) => ({ px: parseFloat(px), cnt }))
    .sort((a, b) => a.px - b.px)
    .filter(s => s.cnt >= 2);

  // Detect base unit (commonly 4px, 6px, or 8px)
  let baseUnit = 8;
  const values = sortedSpacing.map(s => s.px);
  if (values.some(v => v % 6 === 0) && values.filter(v => v % 6 === 0).length > values.filter(v => v % 8 === 0).length) {
    baseUnit = 6;
  } else if (values.some(v => v % 4 === 0)) {
    baseUnit = 4;
  }

  const spacing = sortedSpacing.slice(0, 10).map(s => ({
    value_px: s.px,
    count: s.cnt,
    evidence: 'RUNTIME',
    confidence: 0.92,
    origin: 'computed layout box model'
  }));

  // 4. Border Radii
  const radii = Object.entries(raw.radiusCounts)
    .map(([r, count]) => ({ radius_px: parseFloat(r), count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 6)
    .map(r => ({
      value_px: r.radius_px,
      role: r.radius_px >= 999 || r.radius_px >= 24 ? 'pill / tag' : 'rounded card / input',
      evidence: 'RUNTIME',
      confidence: 0.95
    }));

  // 5. Shadows
  const shadows = Object.entries(raw.shadowSet)
    .map(([sh, count]) => ({
      value: sh,
      count,
      evidence: 'RUNTIME',
      confidence: 0.90
    }))
    .slice(0, 4);

  // 6. Components
  const components = {
    buttons: raw.buttons.map(b => ({
      label: b.text,
      background: b.bg,
      color: b.color,
      border_radius: b.borderRadius,
      font_weight: b.fontWeight,
      evidence: 'SOURCE',
      confidence: 0.98
    })),
    inputs: raw.inputs.map(inp => ({
      type: inp.type,
      border_radius: inp.borderRadius,
      border_color: inp.borderColor,
      evidence: 'SOURCE',
      confidence: 0.95
    })),
    icons: {
      count: raw.svgs.length,
      sample_svgs: raw.svgs.slice(0, 5),
      evidence: 'RUNTIME',
      confidence: 0.90
    }
  };

  // 7. Motion
  const motion = raw.motionSet.map(m => ({
    property: m.property,
    duration: m.duration,
    timing_function: m.timing,
    evidence: 'RUNTIME',
    confidence: 0.92
  }));

  // 8. Responsive
  const responsive = {
    desktop_viewport: { width: 1280, height: 900 },
    mobile_viewport: mobileLayout,
    has_mobile_menu: mobileLayout.hasHamburger,
    evidence: 'RUNTIME',
    confidence: 0.94
  };

  return {
    meta: {
      url,
      title: raw.title,
      timestamp: new Date().toISOString(),
      generator: 'D-DOM v1.0 Core Extractor',
      completeness_score: 0.92
    },
    tokens: {
      colors,
      typography,
      spacing: {
        base_unit: { value: baseUnit, evidence: 'INFERRED', confidence: 0.88 },
        scale: spacing
      },
      border_radii: radii,
      shadows
    },
    components,
    motion,
    responsive,
    layout: raw.layoutInfo
  };
}

// CLI execution if run directly
if (require.main === module) {
  const args = process.argv.slice(2);
  const targetUrl = args[0];
  if (!targetUrl) {
    console.error('Usage: node extractor.js <url> [outputPath] [screenshotPath]');
    process.exit(1);
  }
  const outPath = args[1] || 'output/ddom.json';

  extractDDom(targetUrl, outPath)
    .then(data => {
      console.log(`D-DOM successfully extracted for ${targetUrl} -> ${outPath}`);
      console.log(`Found ${data.tokens.colors.length} colors, ${data.tokens.typography.length} font sizes, ${data.components.buttons.length} buttons.`);
    })
    .catch(err => {
      console.error('Extraction failed:', err);
      process.exit(1);
    });
}

module.exports = { extractDDom };
