"""Cozy UI: cắt sprite từ assets/ui/cozy_ui.png (panel 9-slice, nút theo 4 bảng màu, ô nhập, icon)."""
import os

import pygame

HERE = os.path.dirname(os.path.abspath(__file__))
# gốc (x, y) của từng bảng màu trong sheet; mỗi icon có 2 trạng thái (thường / nhấn) cách nhau 16px
THEMES = {"cream": (1, 33), "peach": (65, 33), "mauve": (1, 97), "brown": (65, 97)}
GLYPHS = {"play": (0, 0), "pause": (0, 1), "plus": (1, 0), "check": (1, 1),
          "x": (2, 0), "minus": (2, 1), "help": (3, 0), "coin": (3, 1)}
TEXT = {"cream": (62, 44, 36), "peach": (62, 44, 36), "mauve": (255, 244, 238), "brown": (255, 244, 238)}
PANEL_SRC = (164, 167, 47, 80)  # khung trơn, góc 8x8


def nine(src, l, r, t, b, w, h, tile=False):
    sw, sh = src.get_size()
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    mw, mh, cw, ch = sw - l - r, sh - t - b, w - l - r, h - t - b
    part = lambda x, y, pw, ph: src.subsurface((x, y, pw, ph))
    sc = pygame.transform.scale
    if cw > 0 and ch > 0:  # ruột trước, viền vẽ đè sau
        c = part(l, t, mw, mh)
        if tile:
            out.set_clip((l, t, cw, ch))
            for yy in range(t, t + ch, mh):
                for xx in range(l, l + cw, mw):
                    out.blit(c, (xx, yy))
            out.set_clip(None)
        else:
            out.blit(sc(c, (cw, ch)), (l, t))
        out.blit(sc(part(l, 0, mw, t), (cw, t)), (l, 0))
        out.blit(sc(part(l, sh - b, mw, b), (cw, b)), (l, h - b))
        out.blit(sc(part(0, t, l, mh), (l, ch)), (0, t))
        out.blit(sc(part(sw - r, t, r, mh), (r, ch)), (w - r, t))
    out.blit(part(0, 0, l, t), (0, 0))
    out.blit(part(sw - r, 0, r, t), (w - r, 0))
    out.blit(part(0, sh - b, l, b), (0, h - b))
    out.blit(part(sw - r, sh - b, r, b), (w - r, h - b))
    return out


def recolor(s, mapping):
    s = s.copy()
    for y in range(s.get_height()):
        for x in range(s.get_width()):
            c = s.get_at((x, y))
            n = mapping.get(tuple(c)[:3])
            if n and c[3]:
                s.set_at((x, y), (*n, c[3]))
    return s


class CozyUI:
    def __init__(self):
        self.sheet = pygame.image.load(os.path.join(HERE, "assets", "ui", "cozy_ui.png")).convert_alpha()
        self.cache = {}
        self.icons = {}
        idir = os.path.join(HERE, "assets", "ui", "icons")
        if os.path.isdir(idir):
            for f in os.listdir(idir):
                if f.endswith(".png"):
                    self.icons[f[:-4]] = pygame.image.load(os.path.join(idir, f)).convert_alpha()
        self.blank = {}
        self.glyphs = {}
        self.cells = {}
        for th, (bx, by) in THEMES.items():
            for state in (0, 1):
                cell = self.sheet.subsurface((bx + 16 * state, by + 16 + state, 14, 14 - state)).copy()
                face = cell.get_at((6, 1))
                cell.fill(face, (2, 2, 10, 9))  # xoá glyph
                self.blank[(th, state)] = cell
            for name, (r, i) in GLYPHS.items():
                up = self.sheet.subsurface((bx + 32 * i, by + 16 * r, 14, 14)).copy()
                self.cells[(th, name)] = up
                face = up.get_at((6, 1))
                g = up.subsurface((2, 2, 10, 9)).copy()
                for y in range(9):
                    for x in range(10):
                        if tuple(g.get_at((x, y)))[:3] == tuple(face)[:3]:
                            g.set_at((x, y), (0, 0, 0, 0))
                self.glyphs[(th, name)] = g

    # --- tra cứu
    def theme_for(self, col):
        if isinstance(col, str):
            return col
        m = {(238, 142, 50): "peach", (98, 178, 84): "brown", (80, 150, 220): "mauve", (220, 80, 70): "mauve",
             (170, 160, 150): "cream", (80, 190, 190): "cream", (140, 110, 200): "peach",
             (92, 70, 58): "mauve", (246, 196, 50): "peach"}
        return m.get(tuple(col)[:3], "brown")

    def text_col(self, theme):
        return TEXT[theme]

    def glyph(self, theme, name):
        return self.glyphs[(theme, name)]

    def icon(self, theme, name):
        return self.cells[(theme, name)]

    # --- ghép sprite (có cache)
    def button(self, w, h, theme, down=False, hover=False):
        key = ("b", w, h, theme, down, hover)
        s = self.cache.get(key)
        if s is None:
            src = self.blank[(theme, 1 if down else 0)]
            s = nine(src, 4, 4, 3, 3 if down else 4, w, h)
            if hover:
                s.fill((14, 14, 14, 0), special_flags=pygame.BLEND_RGB_ADD)
            self._put(key, s)
        return s

    def field(self, w, h, focus):
        key = ("f", w, h, focus)
        s = self.cache.get(key)
        if s is None:
            src = recolor(self.blank[("cream", 1)], {(0xe6, 0xd5, 0xbe): (255, 250, 243),
                                                    (0xa5, 0x99, 0x89): (0xd0, 0x7a, 0x3c) if focus else (0xa5, 0x99, 0x89)})
            s = nine(src, 4, 4, 3, 3, w, h)
            self._put(key, s)
        return s

    def panel(self, w, h, col=None):
        if w < 16 or h < 16:
            return None
        tint = None
        if col is not None:
            t = tuple(min(255, int(c * 255 / k)) for c, k in zip(col[:3], (255, 252, 244)))
            if min(t) < 247:
                tint = tuple(255 - int((255 - v) * 0.7) for v in t)
        key = ("p", w, h, tint)
        s = self.cache.get(key)
        if s is None:
            s = nine(self.panel_flat(), 8, 8, 8, 8, w, h)
            if tint:
                s.fill(tint, special_flags=pygame.BLEND_RGB_MULT)
            self._put(key, s)
        return s

    def panel_flat(self):
        if "flat" not in self.cache:
            src = self.sheet.subsurface(PANEL_SRC).copy()
            sw, sh = src.get_size()
            px = [tuple(src.get_at((x, y)))[:3] for y in range(10, sh - 10) for x in range(10, sw - 10)]
            mean = tuple(sum(p[i] for p in px) // len(px) for i in range(3))
            src.fill(mean, (8, 8, sw - 16, sh - 16))
            self.cache["flat"] = src
        return self.cache["flat"]

    def _put(self, key, s):
        if len(self.cache) > 300:
            self.cache.clear()
        self.cache[key] = s
