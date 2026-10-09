# /// script
# dependencies = ["pygame-ce"]
# ///
"""PawHabit – game nuôi thú ảo kết hợp habit tracker. 100% pygame, build web bằng pygbag."""
import asyncio
import datetime as dt
import math
import os
import random
import sys
import time

import pygame

import net as netmod
from sprites import BREED_NAMES, BREEDS, STAGE_SCALE, Sprites

W, H = 800, 600
TOP, NAV = 54, 48
HERE = os.path.dirname(os.path.abspath(__file__))

INK, CREAM, CARD, LINE = (62, 44, 36), (252, 246, 232), (255, 252, 244), (226, 208, 178)
ORANGE, GREEN, RED, BLUE = (238, 142, 50), (98, 178, 84), (220, 80, 70), (80, 150, 220)
GOLD, GREY, DARK, WHITE, PINK = (246, 196, 50), (170, 160, 150), (52, 36, 30), (255, 255, 255), (236, 120, 160)
STAT_COL = {"hunger": (230, 140, 60), "happy": (240, 100, 150), "energy": (90, 160, 230), "clean": (80, 190, 190)}
STAT_VN = {"hunger": "No bụng", "happy": "Vui vẻ", "energy": "Năng lượng", "clean": "Sạch sẽ"}
MOOD_VN = {"happy": "Rất vui", "normal": "Bình thường", "sad": "Buồn", "sick": "Ốm yếu"}
KIND_ORDER = {"feed": ["bone", "steak", "treat"], "play": ["ball", "frisbee"], "bathe": ["soap"], "rest": ["bed"]}
ACC_NAMES = {"bandana": "Khăn đỏ", "glasses": "Kính râm", "bow": "Nơ hồng", "crown": "Vương miện"}

TABS = [("home", "Nhà"), ("habits", "Thói quen"), ("quests", "Nhiệm vụ"), ("shop", "Cửa hàng"),
        ("bag", "Túi đồ"), ("stats", "Thống kê"), ("rank", "Xếp hạng"), ("me", "Hồ sơ")]


# ------------------------------------------------------------------ vẽ phụ kiện / icon
def draw_acc(s, kind, hx, hy, k, flip=False):
    sg = -1 if flip else 1

    def P(pts):
        return [(hx + sg * x * k, hy + y * k) for x, y in pts]
    if kind == "crown":
        pts = [(-9, -1), (-9, -11), (-4, -6), (0, -13), (4, -6), (9, -11), (9, -1)]
        pygame.draw.polygon(s, GOLD, P(pts))
        pygame.draw.polygon(s, (190, 130, 20), P(pts), max(1, int(k * 0.5)))
        pygame.draw.circle(s, RED, (hx, hy - 7 * k), max(1, int(1.3 * k)))
    elif kind == "bow":
        pygame.draw.polygon(s, PINK, P([(-1, -3), (-9, -8), (-9, 2)]))
        pygame.draw.polygon(s, PINK, P([(1, -3), (9, -8), (9, 2)]))
        pygame.draw.circle(s, (200, 70, 120), (hx, hy - 3 * k), max(2, int(2 * k)))
    elif kind == "glasses":
        r = pygame.Rect(0, 0, 6 * k, 4 * k)
        for dx in (-7, 1):
            rr = r.copy()
            rr.topleft = (hx + dx * k, hy + 2 * k)
            pygame.draw.rect(s, (20, 20, 30), rr, border_radius=max(1, int(k)))
        pygame.draw.line(s, (20, 20, 30), (hx - 1 * k, hy + 3.5 * k), (hx + 1 * k, hy + 3.5 * k), max(1, int(k * 0.6)))
    elif kind == "bandana":
        tri = [(-17, 9), (-6, 9), (-11.5, 19)]
        pygame.draw.polygon(s, RED, P(tri))
        pygame.draw.polygon(s, (150, 30, 30), P(tri), 1)


def draw_face(s, cx, cy, r, mood):
    col = {"happy": (255, 214, 80), "normal": (255, 226, 130), "sad": (180, 200, 230), "sick": (170, 215, 140)}[mood]
    pygame.draw.circle(s, col, (cx, cy), r)
    pygame.draw.circle(s, INK, (cx, cy), r, 2)
    ex = r * 0.38
    for sx in (-1, 1):
        pygame.draw.circle(s, INK, (int(cx + sx * ex), int(cy - r * 0.2)), max(2, r // 7))
    box = pygame.Rect(cx - r * 0.5, cy - r * 0.05, r, r * 0.8)
    if mood == "happy":
        pygame.draw.arc(s, INK, box, math.pi + 0.3, 2 * math.pi - 0.3, 2)
    elif mood == "normal":
        pygame.draw.line(s, INK, (cx - r * 0.35, cy + r * 0.4), (cx + r * 0.35, cy + r * 0.4), 2)
    else:
        box.move_ip(0, r * 0.35)
        pygame.draw.arc(s, INK, box, 0.3, math.pi - 0.3, 2)


def draw_heart(s, x, y, size, col=PINK):
    r = size // 2
    pygame.draw.circle(s, col, (x - r // 2, y), r // 2 + 1)
    pygame.draw.circle(s, col, (x + r // 2, y), r // 2 + 1)
    pygame.draw.polygon(s, col, [(x - r - 1, y + 1), (x + r + 1, y + 1), (x, y + r + 3)])


def draw_coin(s, x, y, r=9):
    pygame.draw.circle(s, GOLD, (x, y), r)
    pygame.draw.circle(s, (200, 140, 20), (x, y), r, 2)
    pygame.draw.circle(s, (255, 230, 120), (x - 2, y - 2), max(1, r // 4))


def draw_flame(s, x, y, h=16, col=ORANGE):
    pts = [(x, y - h), (x + h * 0.45, y - h * 0.35), (x + h * 0.3, y), (x - h * 0.3, y), (x - h * 0.45, y - h * 0.35)]
    pygame.draw.polygon(s, col, pts)
    pygame.draw.polygon(s, GOLD, [(x, y - h * 0.5), (x + h * 0.2, y - h * 0.1), (x - h * 0.2, y - h * 0.1)])


# ------------------------------------------------------------------ nhân vật thú
class Actor:
    def __init__(self):
        self.x, self.dir, self.anim = 400.0, 1, "idle"
        self.t, self.state_t, self.queue = 0.0, 1.5, []
        self.hearts = []
        self.rect = pygame.Rect(0, 0, 0, 0)

    def set(self, anim, dur):
        self.anim, self.state_t, self.t = anim, dur, 0.0
        if anim in ("walk", "run") and random.random() < 0.5:
            self.dir *= -1

    def play(self, seq):
        self.queue = list(seq)
        self.state_t = 0

    def choose(self, p):
        r = random.random()
        if p["energy"] < 20:
            self.set("sleeping", 6)
        elif p["clean"] < 25 and r < 0.5:
            self.set("itching", 3)
        elif p["hunger"] < 25:
            self.set(random.choice(["lying-down", "lying-down", "bark"]), 4)
        elif p["happy"] < 30 or p["mood"] == "sick":
            self.set(random.choice(["sitting", "lying-down"]), 5)
        else:
            a = random.choices(["walk", "idle", "run", "sitting", "stretching", "bark"], [40, 20, 15, 10, 8, 7])[0]
            self.set(a, random.uniform(2.5, 5))

    def cheer(self):
        for i in range(5):
            self.hearts.append([self.rect.centerx + random.randint(-40, 40), self.rect.top + random.randint(0, 30), 0.0])
        self.play([("bark", 1.2)])

    def update(self, dt_, p, scale, width):
        self.t += dt_
        self.state_t -= dt_
        sp = {"walk": 14, "run": 38}.get(self.anim, 0) * scale
        self.x += self.dir * sp * dt_
        lo, hi = 110 + width / 2, 690 - width / 2
        if self.x < lo:
            self.x, self.dir = lo, 1
        elif self.x > hi:
            self.x, self.dir = hi, -1
        if self.state_t <= 0:
            if self.queue:
                a, d = self.queue.pop(0)
                self.set(a, d)
            else:
                self.choose(p)
        for h in self.hearts:
            h[1] -= 40 * dt_
            h[2] += dt_
        self.hearts = [h for h in self.hearts if h[2] < 1.4]

    def draw(self, s, sheet, p, ground, scale=None):
        stage = p.get("stage", 0)
        scale = scale or STAGE_SCALE[stage]
        frames = sheet.frames(self.anim, scale, self.dir < 0)
        fr = frames[int(self.t * 8) % len(frames)]
        w, h = fr.surf.get_size()
        pos = (int(self.x - w / 2), int(ground - h))
        self.rect = pygame.Rect(pos, (w, h))
        if stage >= 3:  # Huyền thoại: hào quang
            pulse = 0.5 + 0.5 * math.sin(time.time() * 2.5)
            aura = pygame.Surface((w + 60, h + 60), pygame.SRCALPHA)
            pygame.draw.ellipse(aura, (255, 220, 90, int(50 + 40 * pulse)), aura.get_rect())
            s.blit(aura, (pos[0] - 30, pos[1] - 30))
        sh = pygame.Surface((w, 14), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 55), sh.get_rect())
        s.blit(sh, (pos[0], ground - 8))
        s.blit(fr.surf, pos)
        acc = p.get("accessory")
        if acc:
            draw_acc(s, acc, pos[0] + fr.head[0], pos[1] + fr.head[1], scale / 3.0, self.dir < 0)
        for hx, hy, life in self.hearts:
            draw_heart(s, int(hx), int(hy), 14 + int(life * 6), PINK)


# ------------------------------------------------------------------ ứng dụng
class App:
    def __init__(self):
        pygame.init()
        pygame.key.set_repeat(400, 40)
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("PawHabit – Nuôi thú, nuôi thói quen")
        self.clock = pygame.time.Clock()
        fp = lambda n: os.path.join(HERE, "assets", "fonts", n)
        self.f_s = pygame.font.Font(fp("DejaVuSans.ttf"), 13)
        self.f_m = pygame.font.Font(fp("DejaVuSans.ttf"), 16)
        self.f_mb = pygame.font.Font(fp("DejaVuSans-Bold.ttf"), 16)
        self.f_l = pygame.font.Font(fp("DejaVuSans-Bold.ttf"), 22)
        self.f_xl = pygame.font.Font(fp("DejaVuSans-Bold.ttf"), 40)
        self.sp = Sprites()
        self.net = netmod.Net()
        self.cache = {}
        self.scene, self.tab = "boot", "home"
        self.st = None
        self.shop = []
        self.toasts = []
        self.fields, self.focus, self.field_order = {}, None, []
        self.click, self.keys, self.wheel, self.down, self.moved = None, [], 0, None, 0
        self.clip = None
        self.scr = {}
        self.actor = Actor()
        self.confirm = (None, 0)
        self.pick = "golden"
        self.new_kind, self.new_hour = "daily", None
        self.rank_by, self.rank_rows, self.stats, self.admin_rows = "xp", [], None, []
        self.reminded = set()
        self.last_sync = time.time()
        self.sync_at = time.time()
        self.overlay = None
        self.mode = "login"
        self.boot_token()

    # ---------------- lưu token
    def boot_token(self):
        tok = ""
        try:
            if netmod.WEB:
                tok = str(netmod.platform.window.eval("(localStorage.getItem('pg_tok')||'')"))
            else:
                with open(os.path.expanduser("~/.pawhabit_token")) as f:
                    tok = f.read().strip()
        except Exception:
            pass
        if tok and tok != "None":
            self.net.token = tok
            self.net.request("GET", "/me", cb=self.on_login_state, err=lambda c, m: self.logout(silent=True))
        else:
            self.scene = "auth"

    def save_token(self, tok):
        try:
            if netmod.WEB:
                netmod.platform.window.eval("localStorage.setItem('pg_tok',%s)" % repr(tok or ""))
            else:
                p = os.path.expanduser("~/.pawhabit_token")
                if tok:
                    with open(p, "w") as f:
                        f.write(tok)
                elif os.path.exists(p):
                    os.remove(p)
        except Exception:
            pass

    # ---------------- helpers: text / ui
    def txt(self, s, pos, font=None, col=INK, anchor="topleft", maxw=None):
        font = font or self.f_m
        s = str(s)
        if maxw:
            while len(s) > 1 and font.size(s)[0] > maxw:
                s = s[:-2] + "…" if not s.endswith("…") else s[:-2] + "…"
        key = (id(font), s, col)
        surf = self.cache.get(key)
        if surf is None:
            if len(self.cache) > 600:
                self.cache.clear()
            surf = self.cache[key] = font.render(s, True, col)
        r = surf.get_rect(**{anchor: pos})
        self.screen.blit(surf, r)
        return r

    def wrap(self, s, font, maxw):
        lines, cur = [], ""
        for w in s.split(" "):
            t = (cur + " " + w).strip()
            if font.size(t)[0] <= maxw:
                cur = t
            else:
                lines.append(cur)
                cur = w
        return lines + [cur]

    def panel(self, rect, col=CARD, r=14, border=LINE, alpha=None):
        rect = pygame.Rect(rect)
        if alpha is not None:
            sf = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(sf, (*col, alpha), sf.get_rect(), border_radius=r)
            self.screen.blit(sf, rect)
        else:
            pygame.draw.rect(self.screen, col, rect, border_radius=r)
        if border:
            pygame.draw.rect(self.screen, border, rect, 2, border_radius=r)

    def hit(self, rect):
        return bool(self.click and rect.collidepoint(self.click) and (not self.clip or self.clip.collidepoint(self.click)))

    def button(self, rect, label, col=ORANGE, enabled=True, font=None, badge=False):
        rect = pygame.Rect(rect)
        mp = pygame.mouse.get_pos()
        hov = enabled and rect.collidepoint(mp) and (not self.clip or self.clip.collidepoint(mp))
        c = col if enabled else (200, 192, 182)
        if hov:
            c = tuple(min(255, v + 18) for v in c)
        pygame.draw.rect(self.screen, (c[0] * 3 // 4, c[1] * 3 // 4, c[2] * 3 // 4), rect.move(0, 3), border_radius=10)
        pygame.draw.rect(self.screen, c, rect, border_radius=10)
        self.txt(label, rect.center, font or self.f_mb, WHITE if enabled else (250, 246, 240), "center", rect.w - 8)
        if badge:
            pygame.draw.circle(self.screen, RED, (rect.right - 8, rect.top + 8), 6)
        if enabled and self.hit(rect):
            self.click = None
            return True
        return False

    def field(self, fid, rect, hint, password=False, maxlen=40):
        rect = pygame.Rect(rect)
        self.field_order.append(fid)
        val = self.fields.setdefault(fid, "")
        if self.hit(rect):
            self.focus = fid
            self.click = None
        foc = self.focus == fid
        pygame.draw.rect(self.screen, WHITE, rect, border_radius=8)
        pygame.draw.rect(self.screen, ORANGE if foc else LINE, rect, 2, border_radius=8)
        shown = "•" * len(val) if password else val
        if not val and not foc:
            self.txt(hint, (rect.x + 10, rect.centery), self.f_m, GREY, "midleft", rect.w - 16)
        else:
            surf = self.f_m.render(shown, True, INK)
            clip = self.screen.get_clip()
            self.screen.set_clip(rect.inflate(-12, 0).clip(clip))
            x = rect.x + 10 - max(0, surf.get_width() - (rect.w - 22))
            self.screen.blit(surf, (x, rect.centery - surf.get_height() // 2))
            if foc and int(time.time() * 2) % 2 == 0:
                cx = x + surf.get_width() + 2
                pygame.draw.line(self.screen, INK, (cx, rect.y + 7), (cx, rect.bottom - 7), 2)
            self.screen.set_clip(clip)
        if foc:
            for e in self.keys:
                if e.key == pygame.K_BACKSPACE:
                    val = val[:-1]
                elif e.key == pygame.K_TAB:
                    i = (self.last_order.index(fid) + 1) % len(self.last_order) if fid in self.last_order else 0
                    self.focus = self.last_order[i]
                elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.enter = True
                elif e.unicode and e.unicode.isprintable() and len(val) < maxlen:
                    val += e.unicode
            self.fields[fid] = val
        return val

    def bar(self, rect, v, vmax, col, bg=(230, 220, 205)):
        rect = pygame.Rect(rect)
        pygame.draw.rect(self.screen, bg, rect, border_radius=rect.h // 2)
        w = int(rect.w * max(0, min(1, v / vmax if vmax else 0)))
        if w > 0:
            pygame.draw.rect(self.screen, col, (rect.x, rect.y, max(w, rect.h), rect.h), border_radius=rect.h // 2)

    def toast(self, msg, kind="ok"):
        self.toasts.append([msg, time.time() + 3.2, {"ok": GREEN, "err": RED, "info": BLUE, "gold": ORANGE}[kind]])
        self.toasts = self.toasts[-3:]

    def scroll_begin(self, key, area, content_h):
        area = pygame.Rect(area)
        off = self.scr.get(key, 0)
        if area.collidepoint(pygame.mouse.get_pos()):
            off -= self.wheel * 32
        off = max(0, min(off, max(0, content_h - area.h)))
        self.scr[key] = off
        self.screen.set_clip(area)
        self.clip = area
        return area.y - off

    def scroll_end(self):
        self.screen.set_clip(None)
        self.clip = None

    # ---------------- gọi API
    def call(self, method, path, body=None, ok=None):
        seq = self.next_seq()

        def _ok(d):
            if "state" in d:
                self.set_state(d["state"], seq)
            if ok:
                ok(d)

        def _err(code, msg):
            if code == 401 and self.scene == "main":
                self.logout(silent=True)
                self.toast("Phiên đăng nhập hết hạn", "err")
            else:
                self.toast(msg, "err")
        self.net.request(method, path, body, _ok, _err)

    seq_issued, seq_applied = 0, 0

    def next_seq(self):
        self.seq_issued += 1
        return self.seq_issued

    def set_state(self, new, seq=None):
        if seq is not None:  # bỏ qua phản hồi cũ đến muộn
            if seq < self.seq_applied:
                return
            self.seq_applied = seq
        old = self.st.get("pet") if self.st else None
        self.st = new
        p = new.get("pet")
        self.sync_at = time.time()
        if old and p:
            if p["level"] > old["level"]:
                self.toast("Lên cấp %d!" % p["level"], "gold")
            if p["stage"] > old["stage"]:
                self.overlay = (time.time() + 3.5, "%s đã tiến hoá thành %s!" % (p["name"], p["stage_name"]))

    def on_login_state(self, d):
        self.set_state(d["state"], self.next_seq())
        self.scene = "main" if self.st["pet"] else "pick"
        self.tab = "home"
        self.mode = "login"
        if self.scene == "main":
            self.after_enter()
        if not self.shop:
            self.net.request("GET", "/shop", cb=lambda r: setattr(self, "shop", r["items"]))

    def after_enter(self):
        pend = [h for h in self.st["habits"] if not h["done"]]
        if pend:
            self.toast("Hôm nay còn %d thói quen chưa làm" % len(pend), "info")

    def logout(self, silent=False):
        self.net.token = None
        self.save_token("")
        self.st, self.scene, self.fields, self.focus = None, "auth", {}, None
        if not silent:
            self.toast("Đã đăng xuất", "info")

    # ---------------- vòng lặp
    def handle_events(self):
        self.click, self.keys, self.wheel = None, [], 0
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return False
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                self.down, self.moved = e.pos, 0
            elif e.type == pygame.MOUSEMOTION and e.buttons[0] and self.down:
                self.moved += abs(e.rel[0]) + abs(e.rel[1])
                if self.moved > 10:
                    self.wheel += e.rel[1] / 32.0
            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1 and self.down:
                if self.moved <= 10:
                    self.click = e.pos
                self.down = None
            elif e.type == pygame.MOUSEWHEEL:
                self.wheel += e.y
            elif e.type == pygame.KEYDOWN:
                self.keys.append(e)
        return True

    def frame(self, dt_):
        self.enter = False
        self.net.poll()
        self.screen.blit(self.sp.bg, (0, 0))
        {"boot": self.s_boot, "auth": self.s_auth, "pick": self.s_pick, "main": self.s_main}[self.scene](dt_)
        self.field_order, self.last_order = [], self.field_order
        self.draw_toasts()
        if self.net.busy:
            a = time.time() * 6
            pygame.draw.arc(self.screen, WHITE, (W - 30, 8, 20, 20), a, a + 4.5, 3)
        if self.overlay:
            self.draw_overlay()

    last_order = []
    enter = False

    def draw_toasts(self):
        now = time.time()
        self.toasts = [t for t in self.toasts if t[1] > now]
        for i, (msg, _u, col) in enumerate(self.toasts):
            w = min(560, self.f_mb.size(msg)[0] + 40)
            r = pygame.Rect(0, 0, w, 34)
            r.midtop = (W // 2, H - NAV - 46 - i * 40 if self.scene == "main" else 12 + i * 40)
            self.panel(r, col, 10, WHITE)
            self.txt(msg, r.center, self.f_mb, WHITE, "center", w - 20)

    def draw_overlay(self):
        until, msg = self.overlay
        if time.time() > until:
            self.overlay = None
            return
        sf = pygame.Surface((W, H), pygame.SRCALPHA)
        sf.fill((0, 0, 0, 120))
        self.screen.blit(sf, (0, 0))
        k = 1 + 0.05 * math.sin(time.time() * 8)
        self.txt("TIẾN HOÁ!", (W // 2, 220), self.f_xl, GOLD, "center")
        self.txt(msg, (W // 2, 280), self.f_l, WHITE, "center")
        for i in range(10):
            a = time.time() * 2 + i * 0.63
            draw_heart(self.screen, int(W / 2 + math.cos(a) * 180 * k), int(250 + math.sin(a) * 60), 14, GOLD)
        if self.click:
            self.click = None
            self.overlay = None

    # ================================================================ scenes
    def s_boot(self, dt_):
        self.txt("Đang tải…", (W // 2, H // 2), self.f_l, WHITE, "center")

    def s_auth(self, dt_):
        reg = self.mode == "register"
        sf = pygame.Surface((W, H), pygame.SRCALPHA)
        sf.fill((0, 0, 0, 60))
        self.screen.blit(sf, (0, 0))
        self.txt("PawHabit", (W // 2, 70), self.f_xl, WHITE, "center")
        self.txt("Làm thói quen tốt – nuôi thú cưng khoẻ mạnh", (W // 2, 112), self.f_m, WHITE, "center")
        # chú chó minh hoạ
        sheet = self.sp.dogs["golden"]
        a = self.actor
        a.update(dt_, {"energy": 100, "clean": 100, "hunger": 100, "happy": 100, "mood": "happy"}, 3, 200)
        a.x = max(a.x, 250)
        a.draw(self.screen, sheet, {"stage": 0}, 585)
        p = pygame.Rect(0, 0, 380, 300 if not reg else 300)
        p.center = (W // 2, 310)
        self.panel(p, CREAM)
        self.txt("Đăng ký tài khoản" if reg else "Đăng nhập", (p.centerx, p.y + 28), self.f_l, INK, "center")
        u = self.field("user", (p.x + 30, p.y + 62, 320, 40), "Tên đăng nhập (3-24 ký tự)", maxlen=24)
        pw = self.field("pass", (p.x + 30, p.y + 112, 320, 40), "Mật khẩu (≥ 6 ký tự)", True, 64)
        if self.focus is None:
            self.focus = "user"
        go = self.button((p.x + 30, p.y + 168, 320, 44), "Tạo tài khoản" if reg else "Đăng nhập", GREEN) or (self.enter and self.focus in ("user", "pass"))
        if go:
            if len(u) < 3 or len(pw) < 6:
                self.toast("Tên ≥ 3 ký tự và mật khẩu ≥ 6 ký tự", "err")
            else:
                self.submit_auth(u, pw, reg)
        sw = "Đã có tài khoản? Đăng nhập" if reg else "Chưa có tài khoản? Đăng ký"
        if self.button((p.x + 30, p.y + 228, 320, 38), sw, BLUE, font=self.f_m):
            self.mode = "login" if reg else "register"
        self.txt(self.net.base, (W - 8, H - 6), self.f_s, WHITE, "bottomright")

    def submit_auth(self, u, pw, reg):
        def ok(d):
            self.net.token = d["token"]
            self.save_token(d["token"])
            self.net.notify("Chào mừng %s!" % d["username"])
            self.net.request("GET", "/me", cb=self.on_login_state, err=lambda c, m: self.toast(m, "err"))
        self.net.request("POST", "/auth/" + ("register" if reg else "login"), {"username": u, "password": pw}, ok,
                         lambda c, m: self.toast(m, "err"))

    def s_pick(self, dt_):
        sf = pygame.Surface((W, H), pygame.SRCALPHA)
        sf.fill((0, 0, 0, 70))
        self.screen.blit(sf, (0, 0))
        self.txt("Chọn người bạn đồng hành", (W // 2, 44), self.f_l, WHITE, "center")
        for i, b in enumerate(BREEDS):
            r = pygame.Rect(60 + (i % 3) * 235, 85 + (i // 3) * 175, 215, 160)
            sel = self.pick == b
            self.panel(r, CREAM if sel else CARD, 14, ORANGE if sel else LINE)
            if sel:
                pygame.draw.rect(self.screen, ORANGE, r, 4, border_radius=14)
            sheet = self.sp.dogs[b]
            fr = sheet.frames("idle", 3, False)
            f = fr[int(time.time() * 8) % len(fr)]
            self.screen.blit(f.surf, (r.centerx - f.surf.get_width() // 2, r.y + 18))
            self.txt(BREED_NAMES[b], (r.centerx, r.bottom - 22), self.f_mb, INK, "center")
            if self.hit(r):
                self.pick, self.click = b, None
        p = pygame.Rect(150, 450, 500, 120)
        self.panel(p, CREAM)
        name = self.field("petname", (p.x + 20, p.y + 20, 300, 40), "Đặt tên cho thú cưng", maxlen=16)
        ok = self.button((p.x + 335, p.y + 20, 145, 40), "Nhận nuôi", GREEN) or (self.enter and self.focus == "petname")
        self.txt("Bạn sẽ nhận 30 coin và vài vật phẩm khởi đầu.", (p.x + 20, p.y + 78), self.f_s, INK)
        if ok:
            if not name.strip():
                self.toast("Hãy đặt tên cho thú cưng", "err")
            else:
                self.call("POST", "/pet", {"name": name.strip(), "breed": self.pick},
                          ok=lambda d: (setattr(self, "scene", "main"), setattr(self, "tab", "habits"),
                                        self.toast("Hãy thêm thói quen đầu tiên!", "info")))
        if self.button((W - 130, H - 44, 112, 32), "Đăng xuất", GREY, font=self.f_s):
            self.logout()

    # ---------------- màn hình chính
    def s_main(self, dt_):
        if not self.st or not self.st.get("pet"):
            self.scene = "pick"
            return
        now = time.time()
        if now - self.sync_at > 60 and not self.net.busy:
            self.sync_at = now
            sq = self.next_seq()
            self.net.request("GET", "/me", cb=lambda d, sq=sq: self.set_state(d["state"], sq))
        self.check_reminders()
        t = self.tab
        if t != "home":
            sf = pygame.Surface((W, H), pygame.SRCALPHA)
            sf.fill((0, 0, 0, 90))
            self.screen.blit(sf, (0, 0))
            self.panel((16, TOP + 8, W - 32, H - TOP - NAV - 16), CREAM)
        getattr(self, "t_" + t)(dt_)
        self.topbar()
        self.navbar()

    def check_reminders(self):
        s = self.st["server"]
        el = time.time() - self.sync_at
        hour = (s["hour"] * 60 + s["minute"] + int(el // 60)) // 60 % 24
        for h in self.st["habits"]:
            rh = h["reminder_hour"]
            key = (s["day"], h["id"])
            if rh is not None and not h["done"] and hour >= rh and key not in self.reminded:
                self.reminded.add(key)
                msg = "Đến giờ rồi: %s" % h["title"]
                self.toast(msg, "info")
                self.net.notify(msg)

    def topbar(self):
        p = self.st["pet"]
        pygame.draw.rect(self.screen, DARK, (0, 0, W, TOP))
        self.txt(p["name"], (14, 7), self.f_mb, WHITE)
        self.txt("Lv %d · %s" % (p["level"], p["stage_name"]), (14, 29), self.f_s, (230, 210, 180))
        self.bar((200, 14, 220, 12), p["xp_cur"], p["xp_need"], GREEN, (90, 70, 60))
        self.txt("XP %d/%d" % (p["xp_cur"], p["xp_need"]), (310, 38), self.f_s, (230, 210, 180), "center")
        draw_flame(self.screen, 470, 32, 20)
        self.txt("%d ngày" % p["streak"], (484, 27), self.f_mb, WHITE)
        draw_coin(self.screen, 590, 27, 11)
        self.txt(str(p["coins"]), (607, 27), self.f_mb, GOLD, "midleft")
        draw_face(self.screen, 690, 27, 14, p["mood"])
        self.txt(MOOD_VN[p["mood"]], (710, 27), self.f_s, WHITE, "midleft")

    def navbar(self):
        pygame.draw.rect(self.screen, DARK, (0, H - NAV, W, NAV))
        tabs = list(TABS)
        if self.st["user"]["role"] == "admin":
            tabs.append(("admin", "Quản trị"))
        w = W // len(tabs)
        pend = any(not h["done"] for h in self.st["habits"])
        claim = any(q["ready"] for q in self.st["quests"])
        for i, (k, label) in enumerate(tabs):
            r = pygame.Rect(i * w + 2, H - NAV + 4, w - 4, NAV - 8)
            sel = self.tab == k
            if self.button(r, label, ORANGE if sel else (92, 70, 58), font=self.f_s,
                           badge=(k == "habits" and pend) or (k == "quests" and claim)):
                self.tab = k
                self.scr.pop("list", None)
                if k == "rank":
                    self.load_rank()
                elif k == "stats":
                    self.net.request("GET", "/stats", cb=lambda d: setattr(self, "stats", d))
                elif k == "admin":
                    self.load_admin()
                elif k == "shop" and not self.shop:
                    self.net.request("GET", "/shop", cb=lambda r_: setattr(self, "shop", r_["items"]))

    # ---------------- tab: Nhà
    def t_home(self, dt_):
        p = self.st["pet"]
        sheet = self.sp.dogs[p["breed"]]
        scale = STAGE_SCALE[p["stage"]]
        a = self.actor
        a.update(dt_, p, scale, sheet.size(scale)[0])
        ground = 440
        a.draw(self.screen, sheet, p, ground)
        if self.hit(a.rect.inflate(20, 20)):
            a.cheer()
            self.click = None
        # nameplate
        np_ = pygame.Rect(0, 0, 230, 34)
        np_.midtop = (W // 2, ground + 14)
        self.panel(np_, CARD, 10, LINE, 210)
        self.txt("%s · %s" % (p["name"], p["stage_name"]), (np_.centerx, np_.centery), self.f_mb, INK, "center", 214)
        # chỉ số
        pn = pygame.Rect(14, TOP + 8, 196, 134)
        self.panel(pn, CARD, 12, LINE, 225)
        for i, k in enumerate(("hunger", "happy", "energy", "clean")):
            y = pn.y + 10 + i * 30
            self.txt(STAT_VN[k], (pn.x + 10, y), self.f_s)
            self.txt(str(int(p[k])), (pn.right - 10, y), self.f_s, INK, "topright")
            self.bar((pn.x + 10, y + 17, 176, 8), p[k], 100, STAT_COL[k] if p[k] > 25 else RED)
        # tiến hoá
        ev = pygame.Rect(W - 210, TOP + 8, 196, 62)
        self.panel(ev, CARD, 12, LINE, 225)
        nxt = p["next_stage_at"]
        self.txt("Tiến hoá: %d%s" % (p["evo_score"], "/%d" % nxt if nxt else " (tối đa)"), (ev.x + 10, ev.y + 8), self.f_s)
        self.bar((ev.x + 10, ev.y + 28, 176, 8), p["evo_score"], nxt or 1, GOLD)
        self.txt("Streak + chăm sóc", (ev.x + 10, ev.y + 40), self.f_s, GREY, "topleft", 180)
        # nhắc nhở
        pend = [h for h in self.st["habits"] if not h["done"]]
        if pend:
            r = pygame.Rect(0, 0, 330, 30)
            r.midtop = (W // 2, TOP + 10)
            if self.button(r, "Còn %d thói quen chưa làm – bấm để mở" % len(pend), ORANGE, font=self.f_s):
                self.tab = "habits"
        # nút hành động nhanh
        acts = [("feed", "Cho ăn", GREEN, [("licking1", 1.4), ("licking2", 1.4), ("licking1", 1)]),
                ("play", "Chơi", BLUE, [("run", 1.8), ("bark", 1.2), ("run", 1.5)]),
                ("bathe", "Tắm", (80, 190, 190), [("itching", 1.6), ("bark", 1.2)]),
                ("rest", "Ngủ", (140, 110, 200), [("sitting", 0.8), ("sleeping", 3.5)])]
        inv = self.st["inventory"]
        for i, (kind, label, col, seq) in enumerate(acts):
            have = next((x for x in KIND_ORDER[kind] if inv.get(x)), None)
            n = sum(inv.get(x, 0) for x in KIND_ORDER[kind])
            r = pygame.Rect(120 + i * 150, H - NAV - 58, 135, 42)
            if self.button(r, "%s (%d)" % (label, n), col, enabled=True):
                if not have:
                    self.toast("Hết đồ – ghé Cửa hàng nhé", "info")
                else:
                    self.call("POST", "/inventory/use", {"item_id": have}, ok=lambda d, s=seq: self.actor.play(s))

    # ---------------- tab: Thói quen
    def t_habits(self, dt_):
        hs = self.st["habits"]
        self.txt("Thói quen của bạn", (36, TOP + 20), self.f_l)
        done = sum(1 for h in hs if h["done"])
        self.txt("Hôm nay: %d/%d" % (done, len(hs)), (W - 36, TOP + 24), self.f_mb, GREEN, "topright")
        area = pygame.Rect(30, TOP + 56, W - 60, 268)
        y0 = self.scroll_begin("list", area, max(len(hs) * 52, area.h))
        if not hs:
            self.txt("Chưa có thói quen nào. Hãy thêm bên dưới!", (area.centerx, area.y + 40), self.f_m, GREY, "center")
        for i, h in enumerate(hs):
            r = pygame.Rect(area.x, y0 + i * 52, area.w - 4, 46)
            self.panel(r, (232, 246, 226) if h["done"] else CARD, 10)
            self.txt(h["title"], (r.x + 14, r.y + 6), self.f_mb, INK, "topleft", 360)
            tag = "Hằng ngày" if h["kind"] == "daily" else "Hằng tuần (x2 thưởng)"
            rm = "" if h["reminder_hour"] is None else "  ·  nhắc lúc %02d:00" % h["reminder_hour"]
            self.txt(tag + rm, (r.x + 14, r.y + 26), self.f_s, GREY)
            if h["done"]:
                self.txt("Đã xong ✓", (r.right - 130, r.centery), self.f_mb, GREEN, "center")
            elif self.button((r.right - 190, r.y + 7, 110, 32), "Hoàn thành", GREEN, font=self.f_m):
                self.call("POST", "/habits/%d/complete" % h["id"], ok=self.on_complete)
            key = ("del", h["id"])
            armed = self.confirm[0] == key and self.confirm[1] > time.time()
            if self.button((r.right - 70, r.y + 7, 58, 32), "Xoá?" if armed else "Xoá", RED if armed else GREY, font=self.f_s):
                if armed:
                    self.call("DELETE", "/habits/%d" % h["id"])
                    self.confirm = (None, 0)
                else:
                    self.confirm = (key, time.time() + 3)
        self.scroll_end()
        # form thêm
        f = pygame.Rect(30, TOP + 336, W - 60, 128)
        self.panel(f, CARD)
        self.txt("Thêm thói quen mới", (f.x + 14, f.y + 8), self.f_mb)
        title = self.field("newhabit", (f.x + 14, f.y + 36, 420, 38), "Ví dụ: Uống 2 lít nước", maxlen=40)
        if self.button((f.x + 446, f.y + 36, 150, 38), "Hằng ngày" if self.new_kind == "daily" else "Hằng tuần", BLUE):
            self.new_kind = "weekly" if self.new_kind == "daily" else "daily"
        self.txt("Nhắc nhở:", (f.x + 14, f.y + 90), self.f_m)
        if self.button((f.x + 100, f.y + 84, 34, 32), "−", GREY):
            self.new_hour = None if self.new_hour in (None, 0) else self.new_hour - 1
            if self.new_hour is None:
                self.new_hour = None
        self.txt("Không nhắc" if self.new_hour is None else "%02d:00" % self.new_hour, (f.x + 190, f.y + 100), self.f_mb, INK, "center")
        if self.button((f.x + 246, f.y + 84, 34, 32), "+", GREY):
            self.new_hour = 7 if self.new_hour is None else min(23, self.new_hour + 1)
        add = self.button((f.x + 446, f.y + 78, 150, 40), "Thêm", GREEN) or (self.enter and self.focus == "newhabit")
        if add:
            if not title.strip():
                self.toast("Nhập tên thói quen", "err")
            else:
                self.fields["newhabit"] = ""
                self.call("POST", "/habits", {"title": title.strip(), "kind": self.new_kind, "reminder_hour": self.new_hour})

    def on_complete(self, d):
        r = d["reward"]
        if r["capped"]:
            self.toast("Đã đạt giới hạn thưởng hôm nay (vẫn tính streak)", "info")
        else:
            self.toast("+%d coin  +%d XP" % (r["coins"], r["xp"]), "gold")
        self.actor.cheer()

    # ---------------- tab: Nhiệm vụ
    def t_quests(self, dt_):
        qs = self.st["quests"]
        area = pygame.Rect(30, TOP + 16, W - 60, H - TOP - NAV - 44)
        y0 = self.scroll_begin("list", area, 40 * 2 + len(qs) * 62 + 20)
        y = y0
        for period, label in (("daily", "Nhiệm vụ hằng ngày"), ("weekly", "Nhiệm vụ hằng tuần")):
            self.txt(label, (area.x + 4, y + 4), self.f_l)
            y += 40
            for q in [x for x in qs if x["period"] == period]:
                r = pygame.Rect(area.x, y, area.w - 4, 54)
                self.panel(r, (255, 244, 214) if q["ready"] else CARD, 10)
                self.txt(q["title"], (r.x + 14, r.y + 6), self.f_mb, INK, "topleft", 380)
                self.bar((r.x + 14, r.y + 34, 260, 10), q["progress"], q["target"], GREEN)
                self.txt("%d/%d" % (q["progress"], q["target"]), (r.x + 284, r.y + 28), self.f_s)
                draw_coin(self.screen, r.x + 420, r.y + 17, 8)
                self.txt("%d  +%d XP" % (q["coins"], q["xp"]), (r.x + 435, r.y + 17), self.f_s, INK, "midleft")
                if q["claimed"]:
                    self.txt("Đã nhận ✓", (r.right - 70, r.centery), self.f_mb, GREEN, "center")
                elif self.button((r.right - 120, r.y + 11, 108, 32), "Nhận thưởng", ORANGE, enabled=q["ready"], font=self.f_s):
                    self.call("POST", "/quests/%s/claim" % q["id"], ok=lambda d: self.toast("+%d coin  +%d XP" % (d["reward"]["coins"], d["reward"]["xp"]), "gold"))
                y += 62
        self.scroll_end()

    # ---------------- tab: Cửa hàng
    def t_shop(self, dt_):
        p, inv = self.st["pet"], self.st["inventory"]
        self.txt("Cửa hàng", (36, TOP + 20), self.f_l)
        draw_coin(self.screen, W - 120, TOP + 36, 11)
        self.txt(str(p["coins"]), (W - 100, TOP + 36), self.f_mb, ORANGE, "midleft")
        if not self.shop:
            self.txt("Đang tải…", (W // 2, 300), self.f_m, GREY, "center")
        rows = (len(self.shop) + 3) // 4
        area = pygame.Rect(26, TOP + 62, W - 52, H - TOP - NAV - 86)
        y0 = self.scroll_begin("list", area, rows * 146 + 10)
        for i, it in enumerate(self.shop):
            r = pygame.Rect(area.x + (i % 4) * 185, y0 + (i // 4) * 146, 175, 138)
            self.panel(r, CARD, 12)
            self.txt(it["name"], (r.centerx, r.y + 12), self.f_mb, INK, "midtop", 160)
            if it["kind"] == "acc":
                pygame.draw.rect(self.screen, (236, 226, 204), (r.x + 12, r.y + 40, 151, 34), border_radius=8)
                draw_acc(self.screen, it["id"], r.centerx + (12 if it["id"] == "bandana" else 0), r.y + 58 + (-6 if it["id"] == "bandana" else 0), 1.5)
                self.txt("Phụ kiện vĩnh viễn", (r.centerx, r.y + 82), self.f_s, GREY, "midtop")
            else:
                eff = "  ".join("%+d %s" % (v, {"hunger": "No", "happy": "Vui", "energy": "Sức", "clean": "Sạch"}[k]) for k, v in it["eff"].items())
                for j, ln in enumerate(self.wrap(eff, self.f_s, 150)[:3]):
                    self.txt(ln, (r.centerx, r.y + 46 + j * 17), self.f_s, INK, "midtop")
                self.txt("Đang có: %d" % inv.get(it["id"], 0), (r.centerx, r.y + 84), self.f_s, GREY, "midtop")
            owned = it["kind"] == "acc" and inv.get(it["id"])
            can = p["coins"] >= it["price"] and not owned
            lab = "Đã sở hữu" if owned else "Mua · %d" % it["price"]
            if self.button((r.x + 12, r.bottom - 38, 151, 30), lab, GREEN if can else GREY, enabled=can, font=self.f_s):
                self.call("POST", "/shop/buy", {"item_id": it["id"]}, ok=lambda d, n=it["name"]: self.toast("Đã mua %s" % n))
        self.scroll_end()

    # ---------------- tab: Túi đồ
    def t_bag(self, dt_):
        inv, p = self.st["inventory"], self.st["pet"]
        names = {i["id"]: i for i in self.shop}
        self.txt("Túi đồ", (36, TOP + 20), self.f_l)
        items = [(k, v) for k, v in inv.items() if v > 0]
        if not items or not self.shop:
            self.txt("Túi trống – hãy ghé Cửa hàng!", (W // 2, 280), self.f_m, GREY, "center")
        area = pygame.Rect(30, TOP + 62, W - 60, H - TOP - NAV - 86)
        y0 = self.scroll_begin("list", area, len(items) * 56)
        for i, (k, n) in enumerate(items):
            it = names.get(k)
            if not it:
                continue
            r = pygame.Rect(area.x, y0 + i * 56, area.w - 4, 50)
            self.panel(r, CARD, 10)
            self.txt(it["name"], (r.x + 14, r.y + 6), self.f_mb)
            if it["kind"] == "acc":
                eq = p["accessory"] == k
                self.txt("Phụ kiện · " + ("đang đeo" if eq else "chưa đeo"), (r.x + 14, r.y + 28), self.f_s, GREEN if eq else GREY)
                if self.button((r.right - 130, r.y + 9, 118, 32), "Bỏ ra" if eq else "Đeo", BLUE if not eq else GREY, font=self.f_m):
                    self.call("POST", "/inventory/equip", {"item_id": k})
            else:
                eff = "  ".join("%+d %s" % (v, {"hunger": "No", "happy": "Vui", "energy": "Sức", "clean": "Sạch"}[s]) for s, v in it["eff"].items())
                self.txt("x%d   %s" % (n, eff), (r.x + 14, r.y + 28), self.f_s, GREY)
                seqs = {"food": [("licking1", 1.4), ("licking2", 1.4)], "toy": [("run", 1.8), ("bark", 1.2)],
                        "soap": [("itching", 1.6), ("bark", 1.0)], "bed": [("sleeping", 3.5)]}
                if self.button((r.right - 130, r.y + 9, 118, 32), "Sử dụng", GREEN, font=self.f_m):
                    self.call("POST", "/inventory/use", {"item_id": k}, ok=lambda d, s=seqs[it["kind"]]: self.actor.play(s))
        self.scroll_end()

    # ---------------- tab: Thống kê
    def t_stats(self, dt_):
        self.txt("Thống kê thói quen", (36, TOP + 20), self.f_l)
        s, p = self.stats, self.st["pet"]
        if not s:
            self.txt("Đang tải…", (W // 2, 280), self.f_m, GREY, "center")
            return
        hs = self.st["habits"]
        cards = [("Tổng đã làm", p["total_done"]), ("Streak hiện tại", p["streak"]), ("Streak dài nhất", p["best_streak"]),
                 ("Hôm nay", "%d/%d" % (sum(1 for h in hs if h["done"]), len(hs)))]
        for i, (lab, val) in enumerate(cards):
            r = pygame.Rect(30 + i * 190, TOP + 62, 178, 62)
            self.panel(r, CARD)
            self.txt(str(val), (r.centerx, r.y + 8), self.f_l, ORANGE, "midtop")
            self.txt(lab, (r.centerx, r.y + 40), self.f_s, GREY, "midtop")
        ch = pygame.Rect(30, TOP + 138, 400, 300)
        self.panel(ch, CARD)
        self.txt("7 ngày gần nhất", (ch.x + 14, ch.y + 8), self.f_mb)
        mx = max(max(s["counts"]), 3)
        base = ch.bottom - 34
        for i, (d, c) in enumerate(zip(s["days"], s["counts"])):
            x = ch.x + 22 + i * 54
            hgt = int((base - ch.y - 56) * c / mx)
            pygame.draw.rect(self.screen, (232, 222, 205), (x, ch.y + 42, 34, base - ch.y - 42), border_radius=6)
            if c:
                pygame.draw.rect(self.screen, GREEN, (x, base - hgt, 34, hgt), border_radius=6)
            self.txt(str(c), (x + 17, base - hgt - 16 if c else base - 16), self.f_s, INK, "center")
            self.txt(dt.date.fromisoformat(d).strftime("%d/%m"), (x + 17, base + 6), self.f_s, GREY, "midtop")
        pl = pygame.Rect(444, TOP + 138, 326, 300)
        self.panel(pl, CARD)
        self.txt("Theo từng thói quen (7 ngày)", (pl.x + 14, pl.y + 8), self.f_mb, INK, "topleft", 300)
        for i, h in enumerate(s["per_habit"][:10]):
            y = pl.y + 40 + i * 25
            self.txt(h["title"], (pl.x + 14, y), self.f_s, INK, "topleft", 200)
            self.bar((pl.x + 220, y + 3, 70, 8), h["count7"], 7, BLUE)
            self.txt(str(h["count7"]), (pl.right - 14, y), self.f_s, INK, "topright")

    # ---------------- tab: Xếp hạng + showcase
    def load_rank(self):
        self.net.request("GET", "/leaderboard?by=" + self.rank_by, cb=lambda d: setattr(self, "rank_rows", d["rows"]))

    def t_rank(self, dt_):
        self.txt("Bảng xếp hạng & Trưng bày", (36, TOP + 20), self.f_l)
        for i, (k, lab) in enumerate((("xp", "Theo XP"), ("streak", "Theo streak"))):
            if self.button((W - 300 + i * 130, TOP + 18, 122, 32), lab, ORANGE if self.rank_by == k else GREY, font=self.f_s):
                self.rank_by = k
                self.load_rank()
        area = pygame.Rect(30, TOP + 62, W - 60, H - TOP - NAV - 86)
        y0 = self.scroll_begin("list", area, len(self.rank_rows) * 58)
        for i, r_ in enumerate(self.rank_rows):
            r = pygame.Rect(area.x, y0 + i * 58, area.w - 4, 54)
            self.panel(r, (255, 244, 214) if r_["me"] else CARD, 10, ORANGE if r_["me"] else LINE)
            col = [GOLD, (190, 190, 200), (200, 140, 90)][r_["rank"] - 1] if r_["rank"] <= 3 else GREY
            pygame.draw.circle(self.screen, col, (r.x + 28, r.centery), 15)
            self.txt(str(r_["rank"]), (r.x + 28, r.centery), self.f_mb, WHITE, "center")
            sheet = self.sp.dogs[r_["breed"]]
            fr = sheet.frames("idle", 1.2, False)[0]
            self.screen.blit(fr.surf, (r.x + 56, r.centery - fr.surf.get_height() // 2 + 4))
            if r_["accessory"]:
                draw_acc(self.screen, r_["accessory"], r.x + 56 + fr.head[0], r.centery - fr.surf.get_height() // 2 + 4 + fr.head[1], 0.5)
            self.txt(r_["username"], (r.x + 140, r.y + 7), self.f_mb, INK, "topleft", 200)
            self.txt("%s · %s · Lv %d" % (r_["pet"], r_["stage_name"], r_["level"]), (r.x + 140, r.y + 30), self.f_s, GREY, "topleft", 300)
            val = ("%d XP" % r_["xp"]) if self.rank_by == "xp" else ("%d ngày" % r_["streak"])
            self.txt(val, (r.right - 16, r.centery), self.f_l, ORANGE, "midright")
        self.scroll_end()

    # ---------------- tab: Hồ sơ
    def t_me(self, dt_):
        u, p = self.st["user"], self.st["pet"]
        self.txt("Hồ sơ", (36, TOP + 20), self.f_l)
        c = pygame.Rect(30, TOP + 62, 360, 250)
        self.panel(c, CARD)
        rows = [("Tài khoản", u["username"]), ("Vai trò", "Quản trị viên" if u["role"] == "admin" else "Người chơi"),
                ("Thú cưng", "%s (%s)" % (p["name"], BREED_NAMES[p["breed"]])), ("Cấp độ", "%d  (%d XP)" % (p["level"], p["xp"])),
                ("Giai đoạn", p["stage_name"]), ("Điểm tiến hoá", str(p["evo_score"])), ("Tâm trạng", MOOD_VN[p["mood"]]),
                ("Streak tốt nhất", "%d ngày" % p["best_streak"])]
        for i, (a, b) in enumerate(rows):
            self.txt(a, (c.x + 16, c.y + 14 + i * 28), self.f_m, GREY)
            self.txt(b, (c.right - 16, c.y + 14 + i * 28), self.f_mb, INK, "topright", 200)
        r = pygame.Rect(410, TOP + 62, 360, 250)
        self.panel(r, CARD)
        self.txt("Đổi tên thú cưng", (r.x + 16, r.y + 12), self.f_mb)
        nm = self.field("rename", (r.x + 16, r.y + 42, 328, 38), p["name"], maxlen=16)
        if self.button((r.x + 16, r.y + 90, 328, 38), "Lưu tên", GREEN):
            if nm.strip():
                self.call("POST", "/pet", {"name": nm.strip(), "breed": p["breed"]}, ok=lambda d: self.toast("Đã đổi tên"))
                self.fields["rename"] = ""
        if self.button((r.x + 16, r.y + 142, 328, 38), "Bật thông báo trình duyệt", BLUE):
            self.net.notify("Đã bật nhắc nhở thói quen!")
            self.toast("Nếu trình duyệt hỏi, hãy bấm Cho phép", "info")
        if self.button((r.x + 16, r.y + 194, 328, 38), "Đăng xuất", RED):
            self.logout()
        self.txt("Mẹo: nhấp vào thú cưng ở màn hình Nhà để vuốt ve. Hoàn thành thói quen mỗi ngày để giữ streak!", (36, TOP + 330), self.f_s, INK, "topleft", 720)

    # ---------------- tab: Quản trị
    def load_admin(self):
        self.net.request("GET", "/admin/users", cb=lambda d: setattr(self, "admin_rows", d["users"]))

    def t_admin(self, dt_):
        self.txt("Quản lý người dùng", (36, TOP + 20), self.f_l)
        self.txt("%d tài khoản" % len(self.admin_rows), (W - 36, TOP + 26), self.f_m, GREY, "topright")
        area = pygame.Rect(30, TOP + 62, W - 60, H - TOP - NAV - 86)
        y0 = self.scroll_begin("list", area, len(self.admin_rows) * 52)
        me = self.st["user"]["id"]

        def done(d):
            self.admin_rows = d["users"]
        for i, u in enumerate(self.admin_rows):
            r = pygame.Rect(area.x, y0 + i * 52, area.w - 4, 46)
            self.panel(r, (250, 225, 220) if u["banned"] else CARD, 10)
            self.txt(u["username"], (r.x + 12, r.y + 5), self.f_mb, INK, "topleft", 170)
            self.txt("%s · %s · %d XP" % (u["role"], u["pet"], u["xp"]), (r.x + 12, r.y + 25), self.f_s, GREY, "topleft", 230)
            if u["id"] == me:
                self.txt("(bạn)", (r.right - 20, r.centery), self.f_s, GREY, "midright")
                continue
            base = "/admin/users/%d" % u["id"]
            if self.button((r.x + 260, r.y + 7, 110, 32), "Mở khoá" if u["banned"] else "Khoá", GREEN if u["banned"] else ORANGE, font=self.f_s):
                self.net.request("POST", base + "/ban", cb=done, err=lambda c, m: self.toast(m, "err"))
            nr = "user" if u["role"] == "admin" else "admin"
            if self.button((r.x + 380, r.y + 7, 150, 32), "Đặt làm " + nr, BLUE, font=self.f_s):
                self.net.request("POST", base + "/role", {"role": nr}, cb=done, err=lambda c, m: self.toast(m, "err"))
            key = ("adel", u["id"])
            armed = self.confirm[0] == key and self.confirm[1] > time.time()
            if self.button((r.x + 540, r.y + 7, 110, 32), "Chắc chắn?" if armed else "Xoá", RED if armed else GREY, font=self.f_s):
                if armed:
                    self.net.request("DELETE", base, cb=done, err=lambda c, m: self.toast(m, "err"))
                    self.confirm = (None, 0)
                else:
                    self.confirm = (key, time.time() + 3)
        self.scroll_end()


async def main():
    app = App()
    running = True
    while running:
        dt_ = min(app.clock.tick(60) / 1000.0, 0.1)
        running = app.handle_events()
        app.frame(dt_)
        pygame.display.flip()
        await asyncio.sleep(0)
    pygame.quit()


asyncio.run(main())
