const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const { FaRocket, FaUsers, FaDollarSign, FaShieldAlt, FaLightbulb, FaChartLine, FaHandshake, FaExclamationTriangle, FaCheckCircle, FaArrowRight, FaCog, FaBalanceScale } = require("react-icons/fa");

// --- Icon helper ---
function renderIconSvg(IconComponent, color = "#000000", size = 256) {
  return ReactDOMServer.renderToStaticMarkup(
    React.createElement(IconComponent, { color, size: String(size) })
  );
}
async function iconToBase64Png(IconComponent, color, size = 256) {
  const svg = renderIconSvg(IconComponent, color, size);
  const pngBuffer = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + pngBuffer.toString("base64");
}

// --- Colours ---
const C = {
  darkNavy: "1A2332",
  navy: "243447",
  teal: "0D9488",
  tealLight: "14B8A6",
  tealPale: "CCFBF1",
  slate: "1E293B",
  slateLight: "64748B",
  grey: "F0F4F8",
  greyMid: "E2E8F0",
  white: "FFFFFF",
  amber: "D97706",
  amberPale: "FEF3C7",
  red: "DC2626",
  redPale: "FEE2E2",
  green: "059669",
  greenPale: "D1FAE5",
};

// --- Reusable style factories ---
const makeShadow = () => ({ type: "outer", color: "000000", blur: 6, offset: 2, angle: 135, opacity: 0.12 });
const makeCardShadow = () => ({ type: "outer", color: "000000", blur: 4, offset: 1, angle: 135, opacity: 0.10 });

async function build() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.author = "Troy Outtram";
  pres.title = "AI Uplift Models";

  // Pre-render icons
  const icons = {
    rocket: await iconToBase64Png(FaRocket, "#FFFFFF", 256),
    users: await iconToBase64Png(FaUsers, "#FFFFFF", 256),
    dollar: await iconToBase64Png(FaDollarSign, "#FFFFFF", 256),
    shield: await iconToBase64Png(FaShieldAlt, "#FFFFFF", 256),
    lightbulb: await iconToBase64Png(FaLightbulb, "#0D9488", 256),
    chart: await iconToBase64Png(FaChartLine, "#FFFFFF", 256),
    handshake: await iconToBase64Png(FaHandshake, "#FFFFFF", 256),
    warning: await iconToBase64Png(FaExclamationTriangle, "#D97706", 256),
    check: await iconToBase64Png(FaCheckCircle, "#059669", 256),
    arrow: await iconToBase64Png(FaArrowRight, "#0D9488", 256),
    cog: await iconToBase64Png(FaCog, "#FFFFFF", 256),
    balance: await iconToBase64Png(FaBalanceScale, "#FFFFFF", 256),
    rocketTeal: await iconToBase64Png(FaRocket, "#0D9488", 256),
    usersTeal: await iconToBase64Png(FaUsers, "#0D9488", 256),
    dollarTeal: await iconToBase64Png(FaDollarSign, "#0D9488", 256),
    shieldTeal: await iconToBase64Png(FaShieldAlt, "#0D9488", 256),
    chartTeal: await iconToBase64Png(FaChartLine, "#0D9488", 256),
    cogTeal: await iconToBase64Png(FaCog, "#64748B", 256),
    warningWhite: await iconToBase64Png(FaExclamationTriangle, "#FFFFFF", 256),
    checkWhite: await iconToBase64Png(FaCheckCircle, "#FFFFFF", 256),
    balanceWhite: await iconToBase64Png(FaBalanceScale, "#FFFFFF", 256),
  };

  // ============================================================
  // SLIDE 1 — Title
  // ============================================================
  let s1 = pres.addSlide();
  s1.background = { color: C.darkNavy };
  // Subtle teal accent bar at top
  s1.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.teal } });
  // Rocket icon
  s1.addImage({ data: icons.rocket, x: 4.5, y: 1.0, w: 1.0, h: 1.0 });
  s1.addText("AI Uplift Models", {
    x: 0.5, y: 2.2, w: 9, h: 1.0,
    fontSize: 42, fontFace: "Georgia", color: C.white, bold: true, align: "center", margin: 0,
  });
  s1.addText("Transforming Delivery Through Agentic Engineering", {
    x: 0.5, y: 3.2, w: 9, h: 0.6,
    fontSize: 18, fontFace: "Calibri", color: C.tealLight, align: "center", margin: 0,
  });
  // Baseline stat
  s1.addShape(pres.shapes.RECTANGLE, { x: 3.0, y: 4.2, w: 4.0, h: 0.5, fill: { color: C.navy } });
  s1.addText("Baseline: 10-person squad  ·  ~2,000 story points / year", {
    x: 3.0, y: 4.2, w: 4.0, h: 0.5,
    fontSize: 11, fontFace: "Calibri", color: C.slateLight, align: "center", valign: "middle", margin: 0,
  });

  // ============================================================
  // SLIDE 2 — Three Key Decisions (overview)
  // ============================================================
  let s2 = pres.addSlide();
  s2.background = { color: C.grey };
  s2.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.teal } });
  s2.addText("Three Decisions to Make", {
    x: 0.5, y: 0.3, w: 9, h: 0.7,
    fontSize: 32, fontFace: "Georgia", color: C.slate, bold: true, margin: 0,
  });
  s2.addText("Each decision shapes the engagement differently — and each requires alignment from both sides.", {
    x: 0.5, y: 1.0, w: 9, h: 0.5,
    fontSize: 14, fontFace: "Calibri", color: C.slateLight, margin: 0,
  });

  // Three cards
  const decisions = [
    { icon: icons.rocketTeal, num: "01", title: "Integration Depth", desc: "How aggressively do we embed AI into the delivery model?" },
    { icon: icons.dollarTeal, num: "02", title: "Commercial Model", desc: "How is the engagement priced and who carries the risk?" },
    { icon: icons.shieldTeal, num: "03", title: "Value & Risk", desc: "How do we prove it works and protect both sides?" },
  ];
  decisions.forEach((d, i) => {
    const x = 0.5 + i * 3.1;
    s2.addShape(pres.shapes.RECTANGLE, { x, y: 1.8, w: 2.85, h: 3.2, fill: { color: C.white }, shadow: makeCardShadow() });
    s2.addShape(pres.shapes.RECTANGLE, { x, y: 1.8, w: 2.85, h: 0.06, fill: { color: C.teal } });
    s2.addImage({ data: d.icon, x: x + 1.05, y: 2.15, w: 0.7, h: 0.7 });
    s2.addText(d.num, {
      x, y: 3.05, w: 2.85, h: 0.4,
      fontSize: 14, fontFace: "Calibri", color: C.teal, bold: true, align: "center", margin: 0,
    });
    s2.addText(d.title, {
      x: x + 0.2, y: 3.4, w: 2.45, h: 0.5,
      fontSize: 18, fontFace: "Georgia", color: C.slate, bold: true, align: "center", margin: 0,
    });
    s2.addText(d.desc, {
      x: x + 0.2, y: 3.9, w: 2.45, h: 0.8,
      fontSize: 12, fontFace: "Calibri", color: C.slateLight, align: "center", margin: 0,
    });
  });

  // ============================================================
  // SLIDE 3 — Section Divider: AI Integration Depth
  // ============================================================
  let s3 = pres.addSlide();
  s3.background = { color: C.darkNavy };
  s3.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.teal } });
  s3.addText("01", {
    x: 0.5, y: 1.2, w: 9, h: 0.6,
    fontSize: 48, fontFace: "Calibri", color: C.teal, bold: true, margin: 0,
  });
  s3.addText("AI Integration Depth", {
    x: 0.5, y: 1.9, w: 9, h: 0.8,
    fontSize: 36, fontFace: "Georgia", color: C.white, bold: true, margin: 0,
  });
  s3.addText("How aggressively do we embed AI into the delivery model?", {
    x: 0.5, y: 2.8, w: 6, h: 0.5,
    fontSize: 16, fontFace: "Calibri", color: C.slateLight, margin: 0,
  });
  // Spectrum visual
  s3.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 3.8, w: 9, h: 0.08, fill: { color: C.teal } });
  const specLabels = ["Embed & Learn", "Hybrid Squad", "All-In AI-First"];
  specLabels.forEach((label, i) => {
    const cx = 0.5 + i * 4.5;
    s3.addShape(pres.shapes.OVAL, { x: cx + 0.1, y: 3.65, w: 0.35, h: 0.35, fill: { color: C.teal } });
    s3.addText(label, {
      x: cx - 0.5, y: 4.15, w: 1.6, h: 0.4,
      fontSize: 11, fontFace: "Calibri", color: C.slateLight, align: "center", margin: 0,
    });
  });

  // ============================================================
  // SLIDE 4 — Option A: Embed & Learn
  // ============================================================
  let s4 = pres.addSlide();
  s4.background = { color: C.grey };
  s4.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.teal } });
  s4.addText("Option A — Embed & Learn", {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 28, fontFace: "Georgia", color: C.slate, bold: true, margin: 0,
  });
  s4.addText("One AI-enabled engineer replaces a traditional dev role. Builds AI tooling while delivering against the existing backlog.", {
    x: 0.5, y: 0.9, w: 9, h: 0.5,
    fontSize: 13, fontFace: "Calibri", color: C.slateLight, margin: 0,
  });
  // Big number callout
  s4.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.6, w: 2.5, h: 1.4, fill: { color: C.white }, shadow: makeCardShadow() });
  s4.addText("1", { x: 0.5, y: 1.7, w: 2.5, h: 0.8, fontSize: 48, fontFace: "Georgia", color: C.teal, bold: true, align: "center", margin: 0 });
  s4.addText("AI-enabled engineer\nin a 10-person squad", { x: 0.5, y: 2.4, w: 2.5, h: 0.5, fontSize: 11, fontFace: "Calibri", color: C.slateLight, align: "center", margin: 0 });
  // Two-column considerations
  // Us column
  s4.addShape(pres.shapes.RECTANGLE, { x: 3.3, y: 1.6, w: 3.1, h: 3.2, fill: { color: C.white }, shadow: makeCardShadow() });
  s4.addShape(pres.shapes.RECTANGLE, { x: 3.3, y: 1.6, w: 3.1, h: 0.06, fill: { color: C.teal } });
  s4.addText("Us (Consulting)", { x: 3.5, y: 1.75, w: 2.7, h: 0.35, fontSize: 14, fontFace: "Georgia", color: C.teal, bold: true, margin: 0 });
  s4.addText([
    { text: "Low investment risk", options: { bullet: true, breakLine: true } },
    { text: "Proves concept with real delivery metrics", options: { bullet: true, breakLine: true } },
    { text: "Limited upside — selling one seat, not a model", options: { bullet: true, breakLine: true } },
    { text: "Engineer stretched between delivery and tooling", options: { bullet: true } },
  ], { x: 3.5, y: 2.2, w: 2.7, h: 2.4, fontSize: 11, fontFace: "Calibri", color: C.slate, paraSpaceAfter: 6, margin: 0 });
  // Client column
  s4.addShape(pres.shapes.RECTANGLE, { x: 6.6, y: 1.6, w: 3.1, h: 3.2, fill: { color: C.white }, shadow: makeCardShadow() });
  s4.addShape(pres.shapes.RECTANGLE, { x: 6.6, y: 1.6, w: 3.1, h: 0.06, fill: { color: C.navy } });
  s4.addText("Client", { x: 6.8, y: 1.75, w: 2.7, h: 0.35, fontSize: 14, fontFace: "Georgia", color: C.navy, bold: true, margin: 0 });
  s4.addText([
    { text: "Minimal disruption to existing squad", options: { bullet: true, breakLine: true } },
    { text: "Easy to approve internally", options: { bullet: true, breakLine: true } },
    { text: "Hard to see transformational ROI", options: { bullet: true, breakLine: true } },
    { text: "No dependency on new ways of working", options: { bullet: true } },
  ], { x: 6.8, y: 2.2, w: 2.7, h: 2.4, fontSize: 11, fontFace: "Calibri", color: C.slate, paraSpaceAfter: 6, margin: 0 });

  // ============================================================
  // SLIDE 5 — Option B: Hybrid Squad
  // ============================================================
  let s5 = pres.addSlide();
  s5.background = { color: C.grey };
  s5.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.teal } });
  s5.addText("Option B — Hybrid Squad", {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 28, fontFace: "Georgia", color: C.slate, bold: true, margin: 0,
  });
  s5.addText("Blend of AI-enabled and traditional roles. Gradually replace manual effort with agentic tooling as it matures.", {
    x: 0.5, y: 0.9, w: 9, h: 0.5,
    fontSize: 13, fontFace: "Calibri", color: C.slateLight, margin: 0,
  });
  // Composition visual
  s5.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.6, w: 2.5, h: 1.4, fill: { color: C.white }, shadow: makeCardShadow() });
  s5.addText("7 + 3", { x: 0.5, y: 1.7, w: 2.5, h: 0.8, fontSize: 44, fontFace: "Georgia", color: C.teal, bold: true, align: "center", margin: 0 });
  s5.addText("Traditional + AI-enabled\nin a 10-person squad", { x: 0.5, y: 2.4, w: 2.5, h: 0.5, fontSize: 11, fontFace: "Calibri", color: C.slateLight, align: "center", margin: 0 });
  // Us column
  s5.addShape(pres.shapes.RECTANGLE, { x: 3.3, y: 1.6, w: 3.1, h: 3.2, fill: { color: C.white }, shadow: makeCardShadow() });
  s5.addShape(pres.shapes.RECTANGLE, { x: 3.3, y: 1.6, w: 3.1, h: 0.06, fill: { color: C.teal } });
  s5.addText("Us (Consulting)", { x: 3.5, y: 1.75, w: 2.7, h: 0.35, fontSize: 14, fontFace: "Georgia", color: C.teal, bold: true, margin: 0 });
  s5.addText([
    { text: "Balanced risk profile", options: { bullet: true, breakLine: true } },
    { text: "Time to build & iterate tooling", options: { bullet: true, breakLine: true } },
    { text: "Creates migration path to All-In", options: { bullet: true, breakLine: true } },
    { text: "Harder to define commercially", options: { bullet: true } },
  ], { x: 3.5, y: 2.2, w: 2.7, h: 2.4, fontSize: 11, fontFace: "Calibri", color: C.slate, paraSpaceAfter: 6, margin: 0 });
  // Client column
  s5.addShape(pres.shapes.RECTANGLE, { x: 6.6, y: 1.6, w: 3.1, h: 3.2, fill: { color: C.white }, shadow: makeCardShadow() });
  s5.addShape(pres.shapes.RECTANGLE, { x: 6.6, y: 1.6, w: 3.1, h: 0.06, fill: { color: C.navy } });
  s5.addText("Client", { x: 6.8, y: 1.75, w: 2.7, h: 0.35, fontSize: 14, fontFace: "Georgia", color: C.navy, bold: true, margin: 0 });
  s5.addText([
    { text: "Feels progressive but safe", options: { bullet: true, breakLine: true } },
    { text: "Velocity should hold or improve", options: { bullet: true, breakLine: true } },
    { text: "Some change management required", options: { bullet: true, breakLine: true } },
    { text: "Benefits are incremental, not headline-grabbing", options: { bullet: true } },
  ], { x: 6.8, y: 2.2, w: 2.7, h: 2.4, fontSize: 11, fontFace: "Calibri", color: C.slate, paraSpaceAfter: 6, margin: 0 });

  // ============================================================
  // SLIDE 6 — Option C: All-In AI-First
  // ============================================================
  let s6 = pres.addSlide();
  s6.background = { color: C.grey };
  s6.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.teal } });
  s6.addText("Option C — All-In AI-First Squad", {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 28, fontFace: "Georgia", color: C.slate, bold: true, margin: 0,
  });
  s6.addText("Dedicated 5-person AI-native squad. Purpose-built to maximise throughput. Tooling reusable across all squads.", {
    x: 0.5, y: 0.9, w: 9, h: 0.5,
    fontSize: 13, fontFace: "Calibri", color: C.slateLight, margin: 0,
  });
  // Big number
  s6.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.6, w: 2.5, h: 1.4, fill: { color: C.white }, shadow: makeCardShadow() });
  s6.addText("5", { x: 0.5, y: 1.7, w: 2.5, h: 0.8, fontSize: 48, fontFace: "Georgia", color: C.teal, bold: true, align: "center", margin: 0 });
  s6.addText("AI-native engineers\ndoing the work of 10", { x: 0.5, y: 2.4, w: 2.5, h: 0.5, fontSize: 11, fontFace: "Calibri", color: C.slateLight, align: "center", margin: 0 });
  // Us column
  s6.addShape(pres.shapes.RECTANGLE, { x: 3.3, y: 1.6, w: 3.1, h: 3.2, fill: { color: C.white }, shadow: makeCardShadow() });
  s6.addShape(pres.shapes.RECTANGLE, { x: 3.3, y: 1.6, w: 3.1, h: 0.06, fill: { color: C.teal } });
  s6.addText("Us (Consulting)", { x: 3.5, y: 1.75, w: 2.7, h: 0.35, fontSize: 14, fontFace: "Georgia", color: C.teal, bold: true, margin: 0 });
  s6.addText([
    { text: "Highest upside — selling capability, not headcount", options: { bullet: true, breakLine: true } },
    { text: "Reusable IP across other clients", options: { bullet: true, breakLine: true } },
    { text: "Higher delivery risk if tooling underperforms", options: { bullet: true, breakLine: true } },
    { text: "Need strong proof points early", options: { bullet: true } },
  ], { x: 3.5, y: 2.2, w: 2.7, h: 2.4, fontSize: 11, fontFace: "Calibri", color: C.slate, paraSpaceAfter: 6, margin: 0 });
  // Client column
  s6.addShape(pres.shapes.RECTANGLE, { x: 6.6, y: 1.6, w: 3.1, h: 3.2, fill: { color: C.white }, shadow: makeCardShadow() });
  s6.addShape(pres.shapes.RECTANGLE, { x: 6.6, y: 1.6, w: 3.1, h: 0.06, fill: { color: C.navy } });
  s6.addText("Client", { x: 6.8, y: 1.75, w: 2.7, h: 0.35, fontSize: 14, fontFace: "Georgia", color: C.navy, bold: true, margin: 0 });
  s6.addText([
    { text: "Potentially transformational", options: { bullet: true, breakLine: true } },
    { text: "5 doing the work of 10 is a compelling story", options: { bullet: true, breakLine: true } },
    { text: "High trust required — unproven model", options: { bullet: true, breakLine: true } },
    { text: "Tooling compounds across squads over time", options: { bullet: true } },
  ], { x: 6.8, y: 2.2, w: 2.7, h: 2.4, fontSize: 11, fontFace: "Calibri", color: C.slate, paraSpaceAfter: 6, margin: 0 });

  // ============================================================
  // SLIDE 7 — Section Divider: Commercial Model
  // ============================================================
  let s7 = pres.addSlide();
  s7.background = { color: C.darkNavy };
  s7.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.teal } });
  s7.addText("02", {
    x: 0.5, y: 1.5, w: 9, h: 0.6,
    fontSize: 48, fontFace: "Calibri", color: C.teal, bold: true, margin: 0,
  });
  s7.addText("Commercial Model", {
    x: 0.5, y: 2.2, w: 9, h: 0.8,
    fontSize: 36, fontFace: "Georgia", color: C.white, bold: true, margin: 0,
  });
  s7.addText("How is the engagement priced and who carries the risk?", {
    x: 0.5, y: 3.1, w: 6, h: 0.5,
    fontSize: 16, fontFace: "Calibri", color: C.slateLight, margin: 0,
  });

  // ============================================================
  // SLIDE 8 — Model A: Fixed Cost
  // ============================================================
  let s8 = pres.addSlide();
  s8.background = { color: C.grey };
  s8.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.teal } });
  s8.addText("Model A — Fixed Cost (We Absorb Risk)", {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 26, fontFace: "Georgia", color: C.slate, bold: true, margin: 0,
  });
  s8.addText("Same price as current squad. We deliver using AI-enabled people, absorb tooling costs, keep the margin upside.", {
    x: 0.5, y: 0.9, w: 9, h: 0.5,
    fontSize: 13, fontFace: "Calibri", color: C.slateLight, margin: 0,
  });
  // Risk gauge
  s8.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.6, w: 2.5, h: 1.2, fill: { color: C.white }, shadow: makeCardShadow() });
  s8.addText("Risk Split", { x: 0.5, y: 1.65, w: 2.5, h: 0.35, fontSize: 12, fontFace: "Calibri", color: C.slateLight, align: "center", margin: 0 });
  s8.addText("100% Us", { x: 0.5, y: 2.0, w: 2.5, h: 0.5, fontSize: 22, fontFace: "Georgia", color: C.teal, bold: true, align: "center", margin: 0 });
  s8.addText("0% Client", { x: 0.5, y: 2.45, w: 2.5, h: 0.3, fontSize: 12, fontFace: "Calibri", color: C.slateLight, align: "center", margin: 0 });
  // Us column
  s8.addShape(pres.shapes.RECTANGLE, { x: 3.3, y: 1.6, w: 3.1, h: 3.2, fill: { color: C.white }, shadow: makeCardShadow() });
  s8.addShape(pres.shapes.RECTANGLE, { x: 3.3, y: 1.6, w: 3.1, h: 0.06, fill: { color: C.teal } });
  s8.addText("Us (Consulting)", { x: 3.5, y: 1.75, w: 2.7, h: 0.35, fontSize: 14, fontFace: "Georgia", color: C.teal, bold: true, margin: 0 });
  s8.addText([
    { text: "Full control over delivery method", options: { bullet: true, breakLine: true } },
    { text: "If AI works, margins expand significantly", options: { bullet: true, breakLine: true } },
    { text: "If it doesn't, we eat the cost", options: { bullet: true, breakLine: true } },
    { text: "Clean commercial story", options: { bullet: true } },
  ], { x: 3.5, y: 2.2, w: 2.7, h: 2.4, fontSize: 11, fontFace: "Calibri", color: C.slate, paraSpaceAfter: 6, margin: 0 });
  // Client column
  s8.addShape(pres.shapes.RECTANGLE, { x: 6.6, y: 1.6, w: 3.1, h: 3.2, fill: { color: C.white }, shadow: makeCardShadow() });
  s8.addShape(pres.shapes.RECTANGLE, { x: 6.6, y: 1.6, w: 3.1, h: 0.06, fill: { color: C.navy } });
  s8.addText("Client", { x: 6.8, y: 1.75, w: 2.7, h: 0.35, fontSize: 14, fontFace: "Georgia", color: C.navy, bold: true, margin: 0 });
  s8.addText([
    { text: "Zero risk — same cost, same or better output", options: { bullet: true, breakLine: true } },
    { text: "Easy to approve internally", options: { bullet: true, breakLine: true } },
    { text: "No skin in the game", options: { bullet: true, breakLine: true } },
    { text: "Less incentive to champion the engagement", options: { bullet: true } },
  ], { x: 6.8, y: 2.2, w: 2.7, h: 2.4, fontSize: 11, fontFace: "Calibri", color: C.slate, paraSpaceAfter: 6, margin: 0 });

  // ============================================================
  // SLIDE 9 — Model B: 50/50 Investment
  // ============================================================
  let s9 = pres.addSlide();
  s9.background = { color: C.grey };
  s9.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.teal } });
  s9.addText("Model B — 50/50 Shared Investment", {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 26, fontFace: "Georgia", color: C.slate, bold: true, margin: 0,
  });
  s9.addText("Split the cost of AI uplift. Savings from efficiency gains are shared 50/50.", {
    x: 0.5, y: 0.9, w: 9, h: 0.5,
    fontSize: 13, fontFace: "Calibri", color: C.slateLight, margin: 0,
  });
  // Example callout
  s9.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.6, w: 2.5, h: 1.6, fill: { color: C.white }, shadow: makeCardShadow() });
  s9.addText("Example", { x: 0.5, y: 1.65, w: 2.5, h: 0.3, fontSize: 12, fontFace: "Calibri", color: C.slateLight, align: "center", margin: 0 });
  s9.addText("4 testers", { x: 0.5, y: 1.95, w: 1.1, h: 0.35, fontSize: 14, fontFace: "Georgia", color: C.slate, bold: true, align: "center", margin: 0 });
  s9.addImage({ data: icons.arrow, x: 1.65, y: 2.0, w: 0.25, h: 0.25 });
  s9.addText("2 AI", { x: 1.9, y: 1.95, w: 1.1, h: 0.35, fontSize: 14, fontFace: "Georgia", color: C.teal, bold: true, align: "center", margin: 0 });
  s9.addText("Savings split 50/50\nPremium on AI testers\n(2x efficiency)", { x: 0.5, y: 2.4, w: 2.5, h: 0.7, fontSize: 10, fontFace: "Calibri", color: C.slateLight, align: "center", margin: 0 });
  // Us column
  s9.addShape(pres.shapes.RECTANGLE, { x: 3.3, y: 1.6, w: 3.1, h: 3.2, fill: { color: C.white }, shadow: makeCardShadow() });
  s9.addShape(pres.shapes.RECTANGLE, { x: 3.3, y: 1.6, w: 3.1, h: 0.06, fill: { color: C.teal } });
  s9.addText("Us (Consulting)", { x: 3.5, y: 1.75, w: 2.7, h: 0.35, fontSize: 14, fontFace: "Georgia", color: C.teal, bold: true, margin: 0 });
  s9.addText([
    { text: "Reduces upfront investment risk", options: { bullet: true, breakLine: true } },
    { text: "Aligns incentives — both parties win", options: { bullet: true, breakLine: true } },
    { text: "Requires transparent metrics", options: { bullet: true, breakLine: true } },
    { text: "More complex commercial negotiation", options: { bullet: true } },
  ], { x: 3.5, y: 2.2, w: 2.7, h: 2.4, fontSize: 11, fontFace: "Calibri", color: C.slate, paraSpaceAfter: 6, margin: 0 });
  // Client column
  s9.addShape(pres.shapes.RECTANGLE, { x: 6.6, y: 1.6, w: 3.1, h: 3.2, fill: { color: C.white }, shadow: makeCardShadow() });
  s9.addShape(pres.shapes.RECTANGLE, { x: 6.6, y: 1.6, w: 3.1, h: 0.06, fill: { color: C.navy } });
  s9.addText("Client", { x: 6.8, y: 1.75, w: 2.7, h: 0.35, fontSize: 14, fontFace: "Georgia", color: C.navy, bold: true, margin: 0 });
  s9.addText([
    { text: "Signals partnership, not vendor relationship", options: { bullet: true, breakLine: true } },
    { text: "Gets AI capability at half cost", options: { bullet: true, breakLine: true } },
    { text: "Requires internal budget approval", options: { bullet: true, breakLine: true } },
    { text: "Savings must be measurable and auditable", options: { bullet: true } },
  ], { x: 6.8, y: 2.2, w: 2.7, h: 2.4, fontSize: 11, fontFace: "Calibri", color: C.slate, paraSpaceAfter: 6, margin: 0 });

  // ============================================================
  // SLIDE 10 — Model C: Client-Funded Uplift
  // ============================================================
  let s10 = pres.addSlide();
  s10.background = { color: C.grey };
  s10.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.teal } });
  s10.addText("Model C — Client-Funded Uplift", {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 26, fontFace: "Georgia", color: C.slate, bold: true, margin: 0,
  });
  s10.addText("Client funds the AI tooling build directly. They own the output uplift.", {
    x: 0.5, y: 0.9, w: 9, h: 0.5,
    fontSize: 13, fontFace: "Calibri", color: C.slateLight, margin: 0,
  });
  // Uplift stat
  s10.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.6, w: 2.5, h: 1.2, fill: { color: C.white }, shadow: makeCardShadow() });
  s10.addText("5–10%", { x: 0.5, y: 1.7, w: 2.5, h: 0.6, fontSize: 36, fontFace: "Georgia", color: C.teal, bold: true, align: "center", margin: 0 });
  s10.addText("Estimated output uplift", { x: 0.5, y: 2.3, w: 2.5, h: 0.35, fontSize: 11, fontFace: "Calibri", color: C.slateLight, align: "center", margin: 0 });
  // Us column
  s10.addShape(pres.shapes.RECTANGLE, { x: 3.3, y: 1.6, w: 3.1, h: 3.2, fill: { color: C.white }, shadow: makeCardShadow() });
  s10.addShape(pres.shapes.RECTANGLE, { x: 3.3, y: 1.6, w: 3.1, h: 0.06, fill: { color: C.teal } });
  s10.addText("Us (Consulting)", { x: 3.5, y: 1.75, w: 2.7, h: 0.35, fontSize: 14, fontFace: "Georgia", color: C.teal, bold: true, margin: 0 });
  s10.addText([
    { text: "Funded R&D — lowest financial risk", options: { bullet: true, breakLine: true } },
    { text: "Client owns the IP narrative", options: { bullet: true, breakLine: true } },
    { text: "Harder to reuse tooling elsewhere", options: { bullet: true, breakLine: true } },
    { text: "5–10% uplift may underwhelm vs. investment", options: { bullet: true } },
  ], { x: 3.5, y: 2.2, w: 2.7, h: 2.4, fontSize: 11, fontFace: "Calibri", color: C.slate, paraSpaceAfter: 6, margin: 0 });
  // Client column
  s10.addShape(pres.shapes.RECTANGLE, { x: 6.6, y: 1.6, w: 3.1, h: 3.2, fill: { color: C.white }, shadow: makeCardShadow() });
  s10.addShape(pres.shapes.RECTANGLE, { x: 6.6, y: 1.6, w: 3.1, h: 0.06, fill: { color: C.navy } });
  s10.addText("Client", { x: 6.8, y: 1.75, w: 2.7, h: 0.35, fontSize: 14, fontFace: "Georgia", color: C.navy, bold: true, margin: 0 });
  s10.addText([
    { text: "Full ownership of AI capability", options: { bullet: true, breakLine: true } },
    { text: "Can apply beyond this engagement", options: { bullet: true, breakLine: true } },
    { text: "Paying for uncertain returns", options: { bullet: true, breakLine: true } },
    { text: '"Why are we funding a consultancy\'s R&D?"', options: { bullet: true } },
  ], { x: 6.8, y: 2.2, w: 2.7, h: 2.4, fontSize: 11, fontFace: "Calibri", color: C.slate, paraSpaceAfter: 6, margin: 0 });

  // ============================================================
  // SLIDE 11 — Section Divider: Value & Risk
  // ============================================================
  let s11 = pres.addSlide();
  s11.background = { color: C.darkNavy };
  s11.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.teal } });
  s11.addText("03", {
    x: 0.5, y: 1.5, w: 9, h: 0.6,
    fontSize: 48, fontFace: "Calibri", color: C.teal, bold: true, margin: 0,
  });
  s11.addText("Value Realisation & Risk", {
    x: 0.5, y: 2.2, w: 9, h: 0.8,
    fontSize: 36, fontFace: "Georgia", color: C.white, bold: true, margin: 0,
  });
  s11.addText("How do we prove it works and protect both sides?", {
    x: 0.5, y: 3.1, w: 6, h: 0.5,
    fontSize: 16, fontFace: "Calibri", color: C.slateLight, margin: 0,
  });

  // ============================================================
  // SLIDE 12 — Risk Matrix
  // ============================================================
  let s12 = pres.addSlide();
  s12.background = { color: C.grey };
  s12.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.teal } });
  s12.addText("Risk Matrix", {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 28, fontFace: "Georgia", color: C.slate, bold: true, margin: 0,
  });

  const riskHeader = [
    [
      { text: "Risk", options: { fill: { color: C.darkNavy }, color: C.white, bold: true, fontSize: 12, fontFace: "Calibri", align: "left" } },
      { text: "Impact", options: { fill: { color: C.darkNavy }, color: C.white, bold: true, fontSize: 12, fontFace: "Calibri", align: "left" } },
      { text: "Mitigation", options: { fill: { color: C.darkNavy }, color: C.white, bold: true, fontSize: 12, fontFace: "Calibri", align: "left" } },
    ],
  ];
  const riskRows = [
    ["AI tooling underdelivers", "Velocity drops, client loses confidence", "Pilot period with clear exit criteria"],
    ["Team resistance / skill gap", "Slow adoption, shadow processes", "Upskilling plan, pair with AI engineers"],
    ["Commercial complexity", "Deal stalls in procurement", "Start with fixed cost, graduate to 50/50"],
    ["IP disputes", "Legal friction post-engagement", "Define ownership upfront in SOW"],
    ["Over-promise on efficiency", "Credibility damage", "Conservative estimates, let results speak"],
  ];
  const riskData = riskRows.map(row => row.map(cell => ({
    text: cell, options: { fontSize: 11, fontFace: "Calibri", color: C.slate, align: "left", fill: { color: C.white } }
  })));

  s12.addTable([...riskHeader, ...riskData], {
    x: 0.5, y: 1.1, w: 9, colW: [2.8, 2.8, 3.4],
    border: { pt: 0.5, color: C.greyMid },
    rowH: [0.4, 0.5, 0.5, 0.5, 0.5, 0.5],
  });

  // ============================================================
  // SLIDE 13 — Key Decisions Summary
  // ============================================================
  let s13 = pres.addSlide();
  s13.background = { color: C.grey };
  s13.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.teal } });
  s13.addText("Key Decisions", {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 28, fontFace: "Georgia", color: C.slate, bold: true, margin: 0,
  });

  // Our decisions — left column
  s13.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.1, w: 4.3, h: 4.0, fill: { color: C.white }, shadow: makeCardShadow() });
  s13.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.1, w: 4.3, h: 0.06, fill: { color: C.teal } });
  s13.addText("We Need to Decide", {
    x: 0.7, y: 1.25, w: 3.9, h: 0.4,
    fontSize: 16, fontFace: "Georgia", color: C.teal, bold: true, margin: 0,
  });
  s13.addText([
    { text: "How much do we invest upfront?", options: { bullet: true, breakLine: true, bold: true } },
    { text: "Are we willing to absorb all risk for higher margin?", options: { breakLine: true, color: C.slateLight } },
    { text: "", options: { breakLine: true, fontSize: 6 } },
    { text: "Do we lead with Option A or Option C?", options: { bullet: true, breakLine: true, bold: true } },
    { text: "Prove-then-scale vs. bold transformation pitch?", options: { breakLine: true, color: C.slateLight } },
    { text: "", options: { breakLine: true, fontSize: 6 } },
    { text: "What commercial model do we propose first?", options: { bullet: true, breakLine: true, bold: true } },
    { text: "Fixed cost is easiest to sell — but limits upside sharing.", options: { breakLine: true, color: C.slateLight } },
    { text: "", options: { breakLine: true, fontSize: 6 } },
    { text: "Who owns the IP we build?", options: { bullet: true, breakLine: true, bold: true } },
    { text: "Critical for reusability across other clients.", options: { color: C.slateLight } },
  ], { x: 0.7, y: 1.75, w: 3.9, h: 3.2, fontSize: 12, fontFace: "Calibri", color: C.slate, paraSpaceAfter: 2, margin: 0 });

  // Client decisions — right column
  s13.addShape(pres.shapes.RECTANGLE, { x: 5.2, y: 1.1, w: 4.3, h: 4.0, fill: { color: C.white }, shadow: makeCardShadow() });
  s13.addShape(pres.shapes.RECTANGLE, { x: 5.2, y: 1.1, w: 4.3, h: 0.06, fill: { color: C.navy } });
  s13.addText("Client Needs to Decide", {
    x: 5.4, y: 1.25, w: 3.9, h: 0.4,
    fontSize: 16, fontFace: "Georgia", color: C.navy, bold: true, margin: 0,
  });
  s13.addText([
    { text: "How much disruption can they tolerate?", options: { bullet: true, breakLine: true, bold: true } },
    { text: "Minimal (Option A) vs. transformational (Option C).", options: { breakLine: true, color: C.slateLight } },
    { text: "", options: { breakLine: true, fontSize: 6 } },
    { text: "Will they co-invest or expect fixed cost?", options: { bullet: true, breakLine: true, bold: true } },
    { text: "Budget approval for AI uplift vs. status quo pricing.", options: { breakLine: true, color: C.slateLight } },
    { text: "", options: { breakLine: true, fontSize: 6 } },
    { text: "What does success look like for them?", options: { bullet: true, breakLine: true, bold: true } },
    { text: "Velocity? Cost reduction? Innovation narrative?", options: { breakLine: true, color: C.slateLight } },
    { text: "", options: { breakLine: true, fontSize: 6 } },
    { text: "Are they willing to pilot for 4–6 weeks?", options: { bullet: true, breakLine: true, bold: true } },
    { text: "A contained proof point before full commitment.", options: { color: C.slateLight } },
  ], { x: 5.4, y: 1.75, w: 3.9, h: 3.2, fontSize: 12, fontFace: "Calibri", color: C.slate, paraSpaceAfter: 2, margin: 0 });

  // ============================================================
  // SLIDE 14 — Suggested Path Forward
  // ============================================================
  let s14 = pres.addSlide();
  s14.background = { color: C.darkNavy };
  s14.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.teal } });
  s14.addText("Suggested Path Forward", {
    x: 0.5, y: 0.4, w: 9, h: 0.7,
    fontSize: 32, fontFace: "Georgia", color: C.white, bold: true, margin: 0,
  });

  // Step cards
  const steps = [
    { num: "1", title: "Start with Fixed Cost", desc: "Lowest friction. Client pays the same. We prove the model works on our own dime." },
    { num: "2", title: "Run a 4–6 Week Pilot", desc: "Contained scope. Clear before/after metrics. Build confidence on both sides." },
    { num: "3", title: "Graduate to Shared Model", desc: "Once proven, move to 50/50 investment. Align incentives for scaling." },
    { num: "4", title: "Scale Across Squads", desc: "Tooling built in one squad compounds. Extend AI-enabled delivery to Squads 1 and 3." },
  ];
  steps.forEach((step, i) => {
    const y = 1.4 + i * 1.0;
    s14.addShape(pres.shapes.RECTANGLE, { x: 0.5, y, w: 9, h: 0.8, fill: { color: C.navy } });
    s14.addShape(pres.shapes.RECTANGLE, { x: 0.5, y, w: 0.06, h: 0.8, fill: { color: C.teal } });
    s14.addText(step.num, {
      x: 0.8, y, w: 0.5, h: 0.8,
      fontSize: 24, fontFace: "Georgia", color: C.teal, bold: true, valign: "middle", margin: 0,
    });
    s14.addText(step.title, {
      x: 1.5, y: y + 0.08, w: 3, h: 0.35,
      fontSize: 16, fontFace: "Georgia", color: C.white, bold: true, margin: 0,
    });
    s14.addText(step.desc, {
      x: 1.5, y: y + 0.4, w: 7.5, h: 0.35,
      fontSize: 11, fontFace: "Calibri", color: C.slateLight, margin: 0,
    });
  });

  // ============================================================
  // Write
  // ============================================================
  const outPath = "/Users/touttram/CODE/AAGLOBAL/Projects/SuperExtension/ai-uplift-models.pptx";
  await pres.writeFile({ fileName: outPath });
  console.log("Done: " + outPath);
}

build().catch(err => { console.error(err); process.exit(1); });
