"""Tiny SVG helper kit for the ArogyaRakshak report figures (consistent visual language)."""
import html, os, subprocess, pathlib

FOREST = "#244C3A"; FOREST2 = "#3A6B53"; SAGE = "#E9EEE7"; SAGE2 = "#D7E3D4"
BRASS = "#A58A57"; BRASSL = "#F4EEDF"; TERRA = "#B85D43"; TERRAL = "#F7E5DE"
GRAPH = "#252A27"; GREY = "#69716B"; LINE = "#9AA59C"; BORDER = "#C9D1C6"
SLATE = "#3E5C76"; SLATEL = "#E6EDF3"; WHITE = "#FFFFFF"; MUTED = "#F5F6F2"
FONT = "Segoe UI, Arial, sans-serif"


def esc(s):
    return html.escape(str(s), quote=True)


class Fig:
    def __init__(self, w, h):
        self.w, self.h, self.items = w, h, []

    def add(self, s):
        self.items.append(s)

    # ---- primitives -------------------------------------------------
    def text(self, x, y, s, fs=14, anchor="middle", color=GRAPH, weight="normal", italic=False, family=FONT):
        st = ' font-style="italic"' if italic else ""
        self.add(f'<text x="{x}" y="{y}" font-family="{family}" font-size="{fs}" text-anchor="{anchor}" '
                 f'fill="{color}" font-weight="{weight}"{st}>{esc(s)}</text>')

    def rect(self, x, y, w, h, fill=SAGE, stroke=FOREST, r=8, sw=1.4, dash=False, opacity=1):
        d = ' stroke-dasharray="6 4"' if dash else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" '
                 f'stroke-width="{sw}"{d} fill-opacity="{opacity}"/>')

    def box(self, x, y, w, h, title, lines=(), fill=SAGE, stroke=FOREST, tc=GRAPH, fs=15, lfs=12.5,
            r=8, dash=False, sw=1.4, bold=True, lc=GREY, valign="center"):
        self.rect(x, y, w, h, fill, stroke, r, sw, dash)
        n = len(lines)
        total = fs + n * (lfs + 4)
        y0 = y + (h - total) / 2 + fs - 2 if valign == "center" else y + fs + 8
        self.text(x + w / 2, y0, title, fs, "middle", tc, "600" if bold else "normal")
        for i, ln in enumerate(lines):
            self.text(x + w / 2, y0 + (i + 1) * (lfs + 4) + 1, ln, lfs, "middle", lc)

    def group(self, x, y, w, h, label, fill=MUTED, stroke=BORDER, lc=FOREST, fs=13, dash=False):
        self.rect(x, y, w, h, fill, stroke, 10, 1.2, dash)
        self.text(x + 12, y + 20, label.upper(), fs, "start", lc, "700")

    def line(self, x1, y1, x2, y2, color=LINE, sw=1.6, dash=False, arrow=True, both=False):
        d = ' stroke-dasharray="6 4"' if dash else ""
        m = ' marker-end="url(#ah)"' if arrow else ""
        if both:
            m += ' marker-start="url(#ahs)"'
        self.add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}"{d}{m}/>')

    def path(self, pts, color=LINE, sw=1.6, dash=False, arrow=True):
        d = ' stroke-dasharray="6 4"' if dash else ""
        m = ' marker-end="url(#ah)"' if arrow else ""
        p = "M " + " L ".join(f"{a} {b}" for a, b in pts)
        self.add(f'<path d="{p}" fill="none" stroke="{color}" stroke-width="{sw}"{d}{m} stroke-linejoin="round"/>')

    def label(self, x, y, s, fs=11.5, color=GREY, anchor="middle", bg=True, italic=False):
        if bg:
            wpx = len(str(s)) * fs * 0.56 + 10
            ax = {"middle": x - wpx / 2, "start": x - 5, "end": x - wpx + 5}[anchor]
            self.add(f'<rect x="{ax}" y="{y - fs}" width="{wpx}" height="{fs + 6}" rx="4" fill="{WHITE}" fill-opacity="0.92"/>')
        self.text(x, y, s, fs, anchor, color, "normal", italic)

    def pill(self, x, y, s, fill=FOREST, color=WHITE, fs=11.5, pad=10):
        w = len(str(s)) * fs * 0.58 + 2 * pad
        self.rect(x, y, w, fs + 10, fill, fill, (fs + 10) / 2, 1)
        self.text(x + w / 2, y + fs + 2, s, fs, "middle", color, "600")
        return w

    def svg(self):
        defs = (f'<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
                f'orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="{GREY}"/></marker>'
                f'<marker id="ahs" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
                f'<path d="M10 0 L0 5 L10 10 z" fill="{GREY}"/></marker></defs>')
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}">{defs}<rect width="100%" height="100%" fill="white"/>'
                + "".join(self.items) + "</svg>")

    def save(self, name, outdir):
        src = pathlib.Path(outdir) / "src"; png = pathlib.Path(outdir) / "png"
        src.mkdir(parents=True, exist_ok=True); png.mkdir(parents=True, exist_ok=True)
        hp = src / f"{name}.html"
        hp.write_text('<!doctype html><html><head><meta charset="utf-8"></head>'
                      f'<body style="margin:0;background:#fff;overflow:hidden">{self.svg()}</body></html>', encoding="utf-8")
        out = png / f"{name}.png"
        edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        subprocess.run([edge, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--window-size={self.w},{self.h}",
                        f"--screenshot={out}", hp.as_uri()], check=True, capture_output=True)
        return out
