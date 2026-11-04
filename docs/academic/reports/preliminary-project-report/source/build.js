// ArogyaRakshak Preliminary Project Report — DOCX builder.
// Usage: node build.js <contentDir> <figPngDir> <shotsDir> <out.docx>
const fs = require("fs");
const path = require("path");
const D = require("docx");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, ShadingType,
  AlignmentType, BorderStyle, HeadingLevel, PageBreak, Header, Footer, PageNumber, NumberFormat,
  TableOfContents, StyleLevel, TabStopType, LevelFormat, VerticalAlign, TableLayoutType, SectionType,
} = D;

const [contentDir, figDir, shotDir, outFile] = process.argv.slice(2);

const C = { forest: "1F4A37", forest2: "3A6B53", brass: "8C7346", sage: "E4EBE2", sageDark: "C9D5C6",
  graph: "222725", grey: "5F6762", terra: "A4513B", rule: "9AA59C" };
const FONT = "Times New Roman";
const MONO = "Consolas";
const PAGE_W = 11906, PAGE_H = 16838;
const M = { top: 1300, bottom: 1250, left: 1800, right: 1300, header: 620, footer: 560 };
const TEXT_W = PAGE_W - M.left - M.right; // 8806 DXA ≈ 6.1 in
const TITLE_SHORT = "ArogyaRakshak — Preliminary Project Report";
const FOOT = "PESMCOE, Department of Computer Engineering 2026–27";

// ---------- inline formatting ----------
function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const t = m[0];
    if (t.startsWith("**")) out.push(new TextRun({ text: t.slice(2, -2), bold: true, ...base }));
    else if (t.startsWith("`")) out.push(new TextRun({ text: t.slice(1, -1), font: MONO, size: (base.size || 24) - 3, ...base, ...{ font: MONO } }));
    else out.push(new TextRun({ text: t.slice(1, -1), italics: true, ...base }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
  return out;
}

function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}

// ---------- counters ----------
let chapter = 0, figN = 0, tabN = 0, eqN = 0, listInstance = 0;
const appendixMode = { on: false };

function p(text, opts = {}) {
  return new Paragraph({ children: runs(text, opts.run || {}), alignment: opts.align || AlignmentType.JUSTIFIED,
    spacing: opts.spacing, style: opts.style, keepNext: opts.keepNext, indent: opts.indent });
}

function chapterHeading(num, title) {
  const children = [];
  if (num) {
    children.push(new TextRun({ text: String(num), color: C.brass, size: 52, bold: true, font: FONT }));
    children.push(new TextRun({ text: "\t" }));
  }
  children.push(new TextRun({ text: title }));
  return new Paragraph({ heading: HeadingLevel.HEADING_1, children, pageBreakBefore: true,
    tabStops: [{ type: TabStopType.LEFT, position: 720 }] });
}

function figure(file, caption, widthIn) {
  let fp = path.join(figDir, file);
  if (!fs.existsSync(fp)) fp = path.join(shotDir, file);
  if (!fs.existsSync(fp)) throw new Error("missing figure " + file);
  const { w, h } = pngSize(fp);
  const wpx = Math.round(widthIn * 96), hpx = Math.round(wpx * h / w);
  figN += 1;
  const label = appendixMode.on ? `Figure ${appendixMode.letter}.${figN}` : `Figure ${chapter}.${figN}`;
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 },
      children: [new ImageRun({ type: "png", data: fs.readFileSync(fp), transformation: { width: wpx, height: hpx },
        altText: { title: label, description: caption, name: file } })] }),
    new Paragraph({ style: "FigureCaption", children: [new TextRun({ text: label + ": ", bold: true }), ...runs(caption)] }),
  ];
}

function tableBlock(caption, widths, rows, compact = false) {
  tabN += 1;
  const label = appendixMode.on ? `Table ${appendixMode.letter}.${tabN}` : `Table ${chapter}.${tabN}`;
  const total = widths.reduce((a, b) => a + b, 0);
  const cw = widths.map(x => Math.floor(TEXT_W * x / total));
  cw[cw.length - 1] += TEXT_W - cw.reduce((a, b) => a + b, 0);
  const border = { style: BorderStyle.SINGLE, size: 4, color: C.rule };
  const trs = rows.map((cells, ri) => new TableRow({
    tableHeader: ri === 0, cantSplit: true,
    children: cells.map((txt, ci) => new TableCell({
      width: { size: cw[ci], type: WidthType.DXA },
      shading: ri === 0 ? { type: ShadingType.CLEAR, fill: C.sage, color: "auto" } : undefined,
      margins: compact ? { top: 15, bottom: 15, left: 90, right: 90 } : { top: 50, bottom: 50, left: 90, right: 90 },
      verticalAlign: VerticalAlign.CENTER,
      borders: { top: border, bottom: border, left: border, right: border },
      children: txt.split(" // ").map(seg => new Paragraph({ alignment: AlignmentType.LEFT, keepNext: rows.length <= 16 && ri < rows.length - 1, spacing: { before: 0, after: 0, line: compact ? 228 : 240 },
        children: runs(seg, { size: 19, bold: ri === 0 ? true : undefined, color: ri === 0 ? C.forest : undefined }) })),
    })),
  }));
  return [
    new Paragraph({ style: "TableCaption", keepNext: true, children: [new TextRun({ text: label + ": ", bold: true }), ...runs(caption)] }),
    new Table({ width: { size: TEXT_W, type: WidthType.DXA }, columnWidths: cw, rows: trs, layout: TableLayoutType.FIXED }),
    new Paragraph({ spacing: { before: 0, after: 80 }, children: [] }),
  ];
}

function equation(expr, tag) {
  eqN += 1;
  const num = `(${appendixMode.on ? appendixMode.letter : chapter}.${eqN})`;
  return new Paragraph({ spacing: { before: 100, after: 140 }, keepLines: true,
    tabStops: [{ type: TabStopType.CENTER, position: Math.round(TEXT_W / 2) }, { type: TabStopType.RIGHT, position: TEXT_W }],
    children: [new TextRun({ text: "\t" }), new TextRun({ text: expr, font: "Cambria Math", size: 23, italics: false }),
      new TextRun({ text: "\t" + num })] });
}

function callout(title, body) {
  const b = { style: BorderStyle.SINGLE, size: 6, color: C.forest2, space: 6 };
  const out = [new Paragraph({ shading: { type: ShadingType.CLEAR, fill: "EEF2EC", color: "auto" },
    border: { top: b, left: b, right: b }, spacing: { before: 120, after: 0 }, keepNext: true,
    indent: { left: 140, right: 140 }, children: [new TextRun({ text: title, bold: true, color: C.forest, size: 22 })] })];
  body.forEach((line, i) => out.push(new Paragraph({ shading: { type: ShadingType.CLEAR, fill: "EEF2EC", color: "auto" },
    border: i === body.length - 1 ? { bottom: b, left: b, right: b } : { left: b, right: b },
    spacing: { before: 40, after: i === body.length - 1 ? 160 : 0, line: 264 }, indent: { left: 140, right: 140 },
    keepNext: i < body.length - 1, alignment: AlignmentType.LEFT, children: runs(line, { size: 21 }) })));
  return out;
}

// ---------- markup parser ----------
function parseFile(text) {
  const out = [];
  const lines = text.replace(/\r/g, "").split("\n");
  let para = [];
  const flush = () => { if (para.length) { out.push(p(para.join(" "))); para = []; } };
  let currentList = null;
  for (let i = 0; i < lines.length; i++) {
    const raw = lines[i];
    const line = raw.trimEnd();
    if (line.startsWith("%")) continue; // comment
    if (!line.trim()) { flush(); currentList = null; continue; }
    let m;
    if ((m = line.match(/^@chapter\s+(\d+)\s*\|\s*(.+)$/))) {
      flush(); chapter = +m[1]; figN = tabN = eqN = 0; appendixMode.on = false;
      out.push(chapterHeading(chapter, m[2].trim())); continue;
    }
    if ((m = line.match(/^@unnumbered\s+(.+)$/))) { flush(); out.push(chapterHeading(null, m[1].trim())); continue; }
    if ((m = line.match(/^@appendix\s+([A-Z])\s*\|\s*(.+)$/))) {
      flush(); appendixMode.on = true; appendixMode.letter = m[1]; figN = tabN = eqN = 0;
      out.push(chapterHeading(null, `Appendix ${m[1]} — ${m[2].trim()}`)); continue;
    }
    if ((m = line.match(/^### (.+)$/))) { flush(); out.push(new Paragraph({ heading: HeadingLevel.HEADING_3, children: runs(m[1]) })); continue; }
    if ((m = line.match(/^## (.+)$/))) { flush(); out.push(new Paragraph({ heading: HeadingLevel.HEADING_2, children: runs(m[1]) })); continue; }
    if ((m = line.match(/^!figure\s+(\S+)\s*\|\s*(.+?)\s*\|\s*([\d.]+)\s*$/))) { flush(); out.push(...figure(m[1], m[2], +m[3])); continue; }
    if ((m = line.match(/^!eq\s+(.+)$/))) { flush(); out.push(equation(m[1])); continue; }
    if (line.startsWith("!pagebreak")) { flush(); out.push(new Paragraph({ children: [new PageBreak()] })); continue; }
    if ((m = line.match(/^!callout\s+(.+)$/))) {
      flush(); const body = [];
      while (i + 1 < lines.length && lines[i + 1].trim() && !lines[i + 1].startsWith("!endcallout")) body.push(lines[++i].trim());
      if (lines[i + 1] && lines[i + 1].startsWith("!endcallout")) i++;
      out.push(...callout(m[1], body)); continue;
    }
    if ((m = line.match(/^\[(\d+)\] (.+)$/))) {
      flush();
      out.push(new Paragraph({ alignment: AlignmentType.LEFT, spacing: { before: 0, after: 70, line: 252 },
        indent: { left: 620, hanging: 620 }, tabStops: [{ type: TabStopType.LEFT, position: 620 }],
        children: [new TextRun({ text: `[${m[1]}]\t`, size: 21 }), ...runs(m[2], { size: 21 })] }));
      continue;
    }
    if ((m = line.match(/^!plaintable\s*\|\s*([\d,\s]+)$/))) {
      flush(); const rows = [];
      while (i + 1 < lines.length && lines[i + 1].trim().startsWith("|")) {
        rows.push(lines[++i].trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map(s => s.trim()));
      }
      const blk = tableBlock("", m[1].split(",").map(Number), rows, true); tabN -= 1;
      out.push(...blk.slice(1)); continue;
    }
    if ((m = line.match(/^!table\s+(.+?)\s*\|\s*([\d,\s]+)$/))) {
      flush(); const rows = [];
      while (i + 1 < lines.length && lines[i + 1].trim().startsWith("|")) {
        const r = lines[++i].trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map(s => s.trim());
        rows.push(r);
      }
      out.push(...tableBlock(m[1], m[2].split(",").map(Number), rows)); continue;
    }
    if ((m = line.match(/^(\s*)- (.+)$/))) {
      flush(); const lvl = m[1].length >= 2 ? 1 : 0;
      out.push(new Paragraph({ numbering: { reference: "bullets", level: lvl }, alignment: AlignmentType.JUSTIFIED,
        spacing: { before: 0, after: 60 }, children: runs(m[2]) })); continue;
    }
    if ((m = line.match(/^(\d+)\) (.+)$/))) {
      flush(); if (currentList === null || m[1] === "1") { listInstance += 1; currentList = listInstance; }
      out.push(new Paragraph({ numbering: { reference: "numbers", level: 0, instance: currentList }, alignment: AlignmentType.JUSTIFIED,
        spacing: { before: 0, after: 60 }, children: runs(m[2]) })); continue;
    }
    para.push(line.trim());
  }
  flush();
  return out;
}

// ---------- front matter ----------
const CC = AlignmentType.CENTER;
function cp(text, size, opts = {}) {
  return new Paragraph({ alignment: CC, spacing: { before: opts.before || 0, after: opts.after || 0, line: opts.line || 276 },
    children: [new TextRun({ text, size, bold: opts.bold, italics: opts.italics, color: opts.color, font: opts.font || FONT,
      characterSpacing: opts.cs })] });
}

const team = [["Viraj Jadhao", "45515"], ["Anurag Pawar", "42520"], ["Sanjali Paygude", "________"], ["Raj Janvekar", "________"], ["Arya Chandak", "42507"]];
const GUIDE = "Prof. Deipali V. Gore";
const TITLE = "ArogyaRakshak: A Multi-Agent, Evidence-Grounded Decision-Support Platform for Hospital Bill Auditing, Insurance Claim Assistance, Government Scheme Discovery and Medicine Price Verification";

function teamTable(withRoll = true) {
  const none = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
  const nb = { top: none, bottom: none, left: none, right: none };
  return new Table({ alignment: AlignmentType.CENTER, width: { size: 5200, type: WidthType.DXA }, columnWidths: [3400, 1800],
    rows: team.map(([n, r]) => new TableRow({ children: [
      new TableCell({ width: { size: 3400, type: WidthType.DXA }, borders: nb, children: [new Paragraph({ children: [new TextRun({ text: n, size: 26 })] })] }),
      new TableCell({ width: { size: 1800, type: WidthType.DXA }, borders: nb, children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: withRoll ? r : "", size: 26 })] })] }),
    ] })) });
}

function coverPage() {
  const rule = { bottom: { style: BorderStyle.DOUBLE, size: 6, color: C.forest, space: 6 } };
  return [
    cp("A PRELIMINARY PROJECT REPORT ON", 24, { before: 200, after: 260, cs: 40 }),
    new Paragraph({ alignment: CC, spacing: { after: 120 }, children: [new TextRun({ text: "ArogyaRakshak (आरोग्यरक्षक)", size: 40, bold: true, color: C.forest })] }),
    new Paragraph({ alignment: CC, spacing: { after: 360, line: 300 }, border: rule, children: [new TextRun({ text: "A Multi-Agent, Evidence-Grounded Decision-Support Platform for Hospital Bill Auditing, Insurance Claim Assistance, Government Scheme Discovery and Medicine Price Verification", size: 25, italics: true })] }),
    cp("SUBMITTED TO THE SAVITRIBAI PHULE PUNE UNIVERSITY, PUNE", 24),
    cp("IN THE PARTIAL FULFILLMENT OF THE REQUIREMENTS", 24),
    cp("FOR THE AWARD OF THE DEGREE OF", 24, { after: 200 }),
    cp("BACHELOR OF ENGINEERING", 27, { bold: true }),
    cp("(COMPUTER ENGINEERING)", 25, { bold: true, after: 300 }),
    cp("SUBMITTED BY", 24, { after: 120 }),
    teamTable(),
    cp("Group ID: C2", 23, { before: 160, after: 300, italics: true }),
    cp("UNDER THE GUIDANCE OF", 24, { after: 60 }),
    cp(GUIDE, 26, { bold: true, after: 700 }),
    cp("DEPARTMENT OF COMPUTER ENGINEERING", 24),
    cp("PROGRESSIVE EDUCATION SOCIETY'S MODERN COLLEGE OF ENGINEERING", 24),
    cp("SHIVAJINAGAR, PUNE – 411005", 24),
    cp("SAVITRIBAI PHULE PUNE UNIVERSITY", 25, { bold: true }),
    cp("2026 – 27", 24, { before: 60 }),
  ];
}

function sigTable(cols) {
  const none = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
  const nb = { top: none, bottom: none, left: none, right: none };
  const w = Math.floor(TEXT_W / cols.length);
  return new Table({ width: { size: w * cols.length, type: WidthType.DXA }, columnWidths: cols.map(() => w),
    rows: [new TableRow({ children: cols.map(lines => new TableCell({ width: { size: w, type: WidthType.DXA }, borders: nb,
      children: [new Paragraph({ alignment: CC, children: [new TextRun({ text: "______________________", color: C.grey })] }),
        ...lines.map((l, i) => new Paragraph({ alignment: CC, children: [new TextRun({ text: l, size: 22, bold: i === 0 })] }))] })) })] });
}

function certificatePage() {
  return [
    cp("Progressive Education Society's", 26, { before: 600 }),
    cp("Modern College of Engineering", 30, { bold: true }),
    cp("Department of Computer Engineering", 26),
    cp("Shivajinagar, Pune – 411005", 26, { after: 500 }),
    new Paragraph({ alignment: CC, spacing: { after: 400 }, children: [new TextRun({ text: "CERTIFICATE", size: 32, bold: true, underline: {}, color: C.forest })] }),
    p("This is to certify that the following students of Final Year Computer Engineering of PES's Modern College of Engineering, Pune, have successfully completed the preliminary analysis and design of the project entitled **“ArogyaRakshak: A Multi-Agent, Evidence-Grounded Decision-Support Platform for Hospital Bill Auditing, Insurance Claim Assistance, Government Scheme Discovery and Medicine Price Verification”** under the guidance of " + GUIDE + ".", { spacing: { after: 240, line: 360 } }),
    p("The group members are:", { spacing: { after: 120 } }),
    teamTable(false),
    p("This work is submitted in partial fulfillment of the requirements for the award of the degree of Bachelor of Engineering (Computer Engineering) of Savitribai Phule Pune University.", { spacing: { before: 240, after: 600, line: 360 } }),
    p("Date: ____________", { spacing: { after: 900 } }),
    sigTable([[GUIDE, "Internal Guide"], ["[Name of HoD]", "Head of Department", "Computer Engineering"], ["", "External Examiner"]]),
  ];
}

function frontHeading(t, toc = true) {
  return new Paragraph({ style: toc ? "FrontHeading" : "FrontHeadingNoToc", pageBreakBefore: true, children: [new TextRun(t)] });
}

function frontText(file) {
  return parseFile(fs.readFileSync(path.join(contentDir, file), "utf8"));
}

// ---------- header / footer ----------
const ruleB = { bottom: { style: BorderStyle.SINGLE, size: 6, color: C.rule, space: 3 } };
const ruleT = { top: { style: BorderStyle.SINGLE, size: 6, color: C.rule, space: 3 } };
const bodyHeader = new Header({ children: [new Paragraph({ border: ruleB, tabStops: [{ type: TabStopType.RIGHT, position: TEXT_W }],
  children: [new TextRun({ text: "ArogyaRakshak (आरोग्यरक्षक)", bold: true, size: 19, color: C.forest }),
    new TextRun({ text: "\tPreliminary Project Report", italics: true, size: 19, color: C.grey })] })] });
const bodyFooter = new Footer({ children: [new Paragraph({ border: ruleT, tabStops: [{ type: TabStopType.RIGHT, position: TEXT_W }],
  children: [new TextRun({ text: FOOT, size: 19, color: C.grey }), new TextRun({ text: "\t", size: 20 }),
    new TextRun({ children: [PageNumber.CURRENT], size: 21, bold: true })] })] });
const frontFooter = new Footer({ children: [new Paragraph({ alignment: CC, children: [new TextRun({ children: [PageNumber.CURRENT], size: 21 })] })] });

// ---------- assemble ----------
const pageProps = (extra = {}) => ({ page: { size: { width: PAGE_W, height: PAGE_H }, margin: M, ...extra } });

const frontChildren = [
  ...certificatePage(),
  frontHeading("Declaration", false), ...frontText("00_declaration.txt"),
  frontHeading("Acknowledgement", false), ...frontText("00_ack.txt"),
  frontHeading("Abstract"), ...frontText("00_abstract.txt"),
  frontHeading("Contents", false),
  new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-2", useAppliedParagraphOutlineLevel: true }),
  frontHeading("List of Figures"),
  new TableOfContents("Figures", { hyperlink: true, stylesWithLevels: [new StyleLevel("Figure Caption", 1)] }),
  frontHeading("List of Tables"),
  new TableOfContents("Tables", { hyperlink: true, stylesWithLevels: [new StyleLevel("Table Caption", 1)] }),
  frontHeading("List of Abbreviations"), ...frontText("00_abbrev.txt"),
];

const bodyFiles = fs.readdirSync(contentDir).filter(f => /^\d\d_.*\.txt$/.test(f) && !f.startsWith("00_")).sort();
const bodyChildren = [];
for (const f of bodyFiles) bodyChildren.push(...parseFile(fs.readFileSync(path.join(contentDir, f), "utf8")));
// first chapter heading should not force an extra page after section break
if (bodyChildren[0] && bodyChildren[0].properties) { /* no-op */ }

const doc = new Document({
  creator: "ArogyaRakshak Project Group C2", title: "ArogyaRakshak — Preliminary Project Report",
  description: "Preliminary Project Report, B.E. Computer Engineering, PESMCOE, SPPU, 2026–27",
  features: { updateFields: true },
  styles: {
    default: { document: { run: { font: FONT, size: 24, color: C.graph }, paragraph: { spacing: { after: 120, line: 276 } } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 40, bold: true, color: C.forest },
        paragraph: { spacing: { before: 240, after: 420 }, keepNext: true, outlineLevel: 0,
          border: { top: { style: BorderStyle.SINGLE, size: 18, color: C.forest, space: 10 }, bottom: { style: BorderStyle.DOUBLE, size: 6, color: C.forest, space: 8 } } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 28, bold: true, color: C.forest },
        paragraph: { spacing: { before: 280, after: 120 }, keepNext: true, keepLines: true, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 24, bold: true, italics: true, color: C.graph },
        paragraph: { spacing: { before: 200, after: 80 }, keepNext: true, keepLines: true, outlineLevel: 2 } },
      { id: "FrontHeading", name: "Front Heading", basedOn: "Normal", next: "Normal",
        run: { font: FONT, size: 34, bold: true, color: C.forest },
        paragraph: { alignment: AlignmentType.CENTER, spacing: { before: 360, after: 360 }, outlineLevel: 0,
          border: { bottom: { style: BorderStyle.DOUBLE, size: 6, color: C.forest, space: 8 } } } },
      { id: "FrontHeadingNoToc", name: "Front Heading No TOC", basedOn: "Normal", next: "Normal",
        run: { font: FONT, size: 34, bold: true, color: C.forest },
        paragraph: { alignment: AlignmentType.CENTER, spacing: { before: 360, after: 360 },
          border: { bottom: { style: BorderStyle.DOUBLE, size: 6, color: C.forest, space: 8 } } } },
      { id: "FigureCaption", name: "Figure Caption", basedOn: "Normal", next: "Normal",
        run: { font: FONT, size: 21, color: C.graph },
        paragraph: { alignment: AlignmentType.CENTER, spacing: { before: 0, after: 240, line: 252 } } },
      { id: "TableCaption", name: "Table Caption", basedOn: "Normal", next: "Normal",
        run: { font: FONT, size: 21, color: C.graph },
        paragraph: { alignment: AlignmentType.CENTER, spacing: { before: 160, after: 100, line: 252 }, keepNext: true } },
    ],
  },
  numbering: { config: [
    { reference: "bullets", levels: [
      { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 280 } } } },
      { level: 1, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1000, hanging: 280 } } } }] },
    { reference: "numbers", levels: [
      { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 340 } } } }] },
  ] },
  sections: [
    { properties: pageProps(), children: coverPage() },
    { properties: { ...pageProps(), page: { ...pageProps().page, pageNumbers: { start: 1, formatType: NumberFormat.LOWER_ROMAN } } },
      footers: { default: frontFooter }, children: frontChildren },
    { properties: { ...pageProps(), page: { ...pageProps().page, pageNumbers: { start: 1, formatType: NumberFormat.DECIMAL } } },
      headers: { default: bodyHeader }, footers: { default: bodyFooter }, children: bodyChildren },
  ],
});

Packer.toBuffer(doc).then(buf => { fs.writeFileSync(outFile, buf); console.log("wrote", outFile, "figures/tables last chapter:", chapter); });
