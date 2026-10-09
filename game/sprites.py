import os
import pygame

BREEDS = ["golden", "akita", "great_dane", "schnauzer", "saint_bernard", "husky"]
BREED_NAMES = {"golden": "Golden Retriever", "akita": "Akita", "great_dane": "Great Dane",
               "schnauzer": "Schnauzer", "saint_bernard": "Saint Bernard", "husky": "Siberian Husky"}
ANIMS = ["idle", "walk", "run", "sitting", "sleeping", "lying-down", "bark",
         "itching", "licking1", "licking2", "stretching"]
STAGE_SCALE = [3, 4, 4.5, 5.5]

HERE = os.path.dirname(os.path.abspath(__file__))


class Frame:
    __slots__ = ("surf", "head")

    def __init__(self, surf, head):
        self.surf, self.head = surf, head  # head: điểm gần đầu chó (x, y) trong frame


class DogSheet:
    """Một giống chó: mọi animation, đã cắt về cùng bbox để chân luôn thẳng hàng."""

    def __init__(self, breed):
        self.breed = breed
        raw = {}
        union = None
        for a in ANIMS:
            img = pygame.image.load(os.path.join(HERE, "assets", "dogs", breed, a + ".png")).convert_alpha()
            n = img.get_width() // 100
            frames = [img.subsurface((i * 100, 0, 100, 100)).copy() for i in range(n)]
            raw[a] = frames
            for f in frames:
                bb = f.get_bounding_rect()
                union = bb.copy() if union is None else union.union(bb)
        self.box = union.inflate(4, 4).clip(pygame.Rect(0, 0, 100, 100))
        self.raw = {}
        for a, frames in raw.items():
            out = []
            for f in frames:
                bb = f.get_bounding_rect()
                # đầu chó = điểm cao nhất trong 30% bên phải thân (chó quay mặt sang phải)
                x0 = bb.right - max(2, int(bb.w * 0.3))
                hb = f.subsurface((x0, 0, bb.right - x0, 100)).get_bounding_rect()
                head = (bb.right - self.box.x - bb.w * 0.15, hb.top - self.box.y)
                out.append((f.subsurface(self.box).copy(), head))
            self.raw[a] = out
        self.cache = {}

    def frames(self, anim, scale, flip):
        key = (anim, scale, flip)
        if key not in self.cache:
            lst = []
            for surf, head in self.raw[anim]:
                w, h = surf.get_size()
                s = pygame.transform.scale(surf, (int(w * scale), int(h * scale)))
                hx, hy = head[0] * scale, head[1] * scale
                if flip:
                    s = pygame.transform.flip(s, True, False)
                    hx = s.get_width() - hx
                lst.append(Frame(s, (hx, hy)))
            self.cache[key] = lst
        return self.cache[key]

    def size(self, scale):
        return int(self.box.w * scale), int(self.box.h * scale)


class Sprites:
    def __init__(self):
        self.dogs = {}
        for b in BREEDS:
            self.dogs[b] = DogSheet(b)
        self.bg = pygame.image.load(os.path.join(HERE, "assets", "background.png")).convert()
