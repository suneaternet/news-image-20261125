#!/usr/bin/env python3
"""News poster for Wednesday 25 November 2026.

Draws a 1024x1024 summary of the day's world news into out/entry.png.
Standard library only: the PNG file is encoded by hand (zlib + struct)
and the text is rendered with a small built-in 5x7 bitmap font.
Deterministic: identical bytes on every run.
"""

import os
import struct
import sys
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- font ----
# Each glyph is 7 rows of 5 cells; '#' is ink, '.' is empty.
FONT = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": (".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", "..#..", ".#...", ".#..."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".....", "..#.."),
    ",": (".....", ".....", ".....", ".....", ".....", "..#..", ".#..."),
    ":": (".....", "..#..", ".....", ".....", ".....", "..#..", "....."),
    ";": (".....", "..#..", ".....", ".....", "..#..", "..#..", ".#..."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "/": ("....#", "...#.", "...#.", "..#..", ".#...", ".#...", "#...."),
    "%": ("#...#", "#..#.", "...#.", "..#..", ".#...", ".#..#", "#...#"),
    "(": ("...##", "..#..", ".#...", ".#...", ".#...", "..#..", "...##"),
    ")": ("##...", "..#..", "...#.", "...#.", "...#.", "..#..", "##..."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "&": (".##..", "#..#.", "#..#.", ".#...", "#.#.#", "#..#.", ".##.#"),
    "+": (".....", ".....", "..#..", ".###.", "..#..", ".....", "....."),
    "=": (".....", ".....", "#####", ".....", "#####", ".....", "....."),
    "$": ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    "#": (".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".#.#."),
    "@": (".###.", "#...#", "#.###", "#.#.#", "#.##.", "#....", ".###."),
    "'": ("..#..", "..#..", ".....", ".....", ".....", ".....", "....."),
    '"': (".#.#.", ".#.#.", ".....", ".....", ".....", ".....", "....."),
    "\u00b7": (".....", ".....", ".....", "..#..", ".....", ".....", "....."),
}

# ------------------------------------------------------------ png out -----
def _chunk(kind, payload):
    out = struct.pack(">I", len(payload)) + kind + payload
    out += struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    return out


def write_png(path, width, height, rows):
    """rows: list of bytes, each 3*width RGB bytes."""
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + r for r in rows)
    data = sig + _chunk(b"IHDR", ihdr)
    data += _chunk(b"IDAT", zlib.compress(raw, 9))
    data += _chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(data)


# -------------------------------------------------------------- canvas ----
class Poster:
    def __init__(self, width, height, bg):
        self.w, self.h = width, height
        self.px = bytearray(bg * (width * height))

    def _set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = color

    def rect(self, x, y, w, h, color):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self._set(xx, yy, color)

    def hline(self, x, y, w, color, thick=1):
        self.rect(x, y, w, thick, color)

    def text_width(self, s, scale):
        return len(s) * 6 * scale - scale

    def draw_text(self, x, y, s, color, scale=2):
        cx = x
        for ch in s.upper():
            glyph = FONT.get(ch, FONT[" "])
            for gy, row in enumerate(glyph):
                for gx, cell in enumerate(row):
                    if cell == "#":
                        self.rect(cx + gx * scale, y + gy * scale,
                                  scale, scale, color)
            cx += 6 * scale
        return cx

    def draw_centered(self, cx, y, s, color, scale=2):
        w = self.text_width(s, scale)
        self.draw_text(cx - w // 2, y, s, color, scale)

    def wrap_lines(self, s, max_w, scale):
        words = s.split()
        lines, cur = [], ""
        for word in words:
            trial = (cur + " " + word).strip()
            if self.text_width(trial, scale) <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines

    def draw_para(self, x, y, s, color, scale, max_w, leading):
        yy = y
        for line in self.wrap_lines(s, max_w, scale):
            self.draw_text(x, yy, line, color, scale)
            yy += leading
        return yy

    def rows(self):
        stride = self.w * 3
        return [bytes(self.px[i:i + stride])
                for i in range(0, len(self.px), stride)]

# -------------------------------------------------------------- palette ---
INK = bytes((13, 22, 38))        # deep navy page background
CARD = bytes((24, 38, 60))       # story card background
CARD_ALT = bytes((20, 32, 52))   # alternating card background
PAPER = bytes((240, 238, 228))   # headline text
MUTED = bytes((168, 182, 200))   # deck text
GOLD = bytes((232, 184, 64))     # header accent
LINE = bytes((58, 78, 106))      # hairlines

ACCENTS = [
    bytes((232, 84, 84)),    # red    - tech
    bytes((232, 184, 64)),   # gold   - conflict
    bytes((86, 196, 138)),   # green  - climate
    bytes((96, 150, 232)),   # blue   - war
    bytes((196, 120, 232)),  # violet - crime
    bytes((232, 132, 64)),   # orange - sport
]

# -------------------------------------------------------------- stories ----
# Six genuine top stories from Wednesday 25 November 2026.
# Sources: The Daily Brief, Deutsche Welle, Russell Record, Reuters,
# FIFA / U.S. Soccer. Facts checked 25 Nov 2026.
STORIES = [
    {
        "tag": "TECH",
        "headline": "NVIDIA JUMPS 31% AS HUANG RETURNS AS CEO",
        "deck": "Shares surge after Trump intervenes to restore Huang; they ease 5% the next morning.",
    },
    {
        "tag": "CONFLICT",
        "headline": "IRAN CLAIMS THREE TANKERS HIT MINES IN STRAIT OF HORMUZ (UNCONFIRMED)",
        "deck": "Tehran's Revolutionary Guard claims the strikes; no maritime authority has confirmed them.",
    },
    {
        "tag": "CLIMATE",
        "headline": "COP31 TALKS COLLAPSE AS OIL STATES BLOCK FOSSIL-FUEL PHASE-OUT",
        "deck": "Saudi Arabia and other producers push carbon capture instead at the Antalya summit in Turkey.",
    },
    {
        "tag": "WAR",
        "headline": "UKRAINE HITS RUSSIAN WARSHIP OFF LIBYA AS THE WAR WIDENS",
        "deck": "Kyiv says sea drones sank the Russian corvette Merkury off Benghazi.",
    },
    {
        "tag": "PACIFIC",
        "headline": "SOLOMON ISLANDS TELLS CHINA IT WILL NOT RENEW SECURITY PACT",
        "deck": "PM Matthew Wale signs a sweeping treaty making Australia its top security partner.",
    },
    {
        "tag": "SPORT",
        "headline": "2031 WOMEN'S WORLD CUP AWARDED TO USA, MEXICO, COSTA RICA, JAMAICA",
        "deck": "FIFA confirms the first 48-team women's tournament, with 104 matches.",
    },
]

MARKET_LINE = "S&P 500 +4.73%  \u00b7  NASDAQ +6.51%  \u00b7  BRENT $89"
SOURCE_LINE = "SOURCES: REUTERS \u00b7 DEUTSCHE WELLE \u00b7 THE DAILY BRIEF \u00b7 FIFA \u00b7 25 NOV 2026"


# -------------------------------------------------------------- layout ----
def draw_card(poster, x, y, w, h, story, idx, accent, bg):
    poster.rect(x, y, w, h, bg)
    poster.rect(x, y, 10, h, accent)                     # left colour bar
    poster.rect(x, y, w, 2, accent)                      # top hairline
    # index numeral, large and ghosted
    poster.draw_text(x + w - 66, y + 12, str(idx + 1), LINE, 4)
    # tag chip
    tag = " " + story["tag"] + " "
    tw = poster.text_width(tag, 2)
    poster.rect(x + 26, y + 20, tw + 14, 26, accent)
    poster.draw_text(x + 33, y + 25, tag, INK, 2)
    # headline, two-to-three lines
    poster.draw_para(x + 26, y + 62, story["headline"], PAPER, 2,
                     w - 52, 26)
    # deck, wrapped, two lines max worth of space
    poster.draw_para(x + 26, y + h - 80, story["deck"], MUTED, 2,
                     w - 52, 21)


def build():
    p = Poster(W, H, INK)
    # header band
    p.rect(0, 0, W, 148, bytes((10, 17, 30)))
    p.hline(0, 148, W, GOLD, 3)
    p.draw_centered(W // 2, 26, "THE WORLD IN ONE IMAGE", GOLD, 2)
    p.draw_centered(W // 2, 54, "WORLD NEWS", PAPER, 5)
    p.draw_centered(W // 2, 116, "WEDNESDAY \u00b7 25 NOVEMBER 2026",
                    MUTED, 2)
    # story grid: 2 columns x 3 rows
    margin, gap = 28, 24
    cw = (W - 2 * margin - gap) // 2
    ch = 236
    top = 172
    for i, story in enumerate(STORIES):
        col, row = i % 2, i // 2
        x = margin + col * (cw + gap)
        y = top + row * (ch + gap)
        bg = CARD if row % 2 == 0 else CARD_ALT
        draw_card(p, x, y, cw, ch, story, i, ACCENTS[i], bg)
    # footer: markets + sources
    fy = 936
    p.hline(margin, fy, W - 2 * margin, LINE, 2)
    p.draw_centered(W // 2, fy + 16, MARKET_LINE, GOLD, 2)
    p.draw_centered(W // 2, fy + 46, SOURCE_LINE, MUTED, 2)
    return p


def main():
    out_dir = os.environ.get("NEWS_POSTER_OUT", "out")
    os.makedirs(out_dir, exist_ok=True)
    poster = build()
    path = os.path.join(out_dir, "entry.png")
    write_png(path, W, H, poster.rows())
    print("wrote", path, W, "x", H)


if __name__ == "__main__":
    sys.exit(main())
