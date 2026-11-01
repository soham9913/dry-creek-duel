"""Shared UI pieces for the front-end screens: fonts, cached text, ornaments,
and OptionPanel, the wooden-sign list of options used by every menu."""

import pygame

from config import BONE, BONE_DIM, EMBER, INK, LINE, PANEL, RES_ROOT, RUST, SCREEN, SUN

DISPLAY_FONT = RES_ROOT / "assets" / "fonts" / "Rye-Regular.ttf"
FULL_H = SCREEN[1]

# Gunmetal & brass tones for the revolver cylinder, kept warm to sit in the palette.
STEEL = (54, 36, 28)
STEEL_LIGHT = (96, 64, 44)
STEEL_DARK = (28, 16, 11)
BRASS = (198, 144, 64)
BRASS_LIGHT = (232, 186, 102)
PRIMER = (244, 214, 152)
INNER_RULE = (52, 28, 19)          # LINE blended into PANEL, drawn opaque


# ---------------------------------------------------------------- helpers
def load_font(size, display=False):
    """Rye for display lettering when the font file exists, the built-in face otherwise."""
    if display and DISPLAY_FONT.is_file():
        try:
            return pygame.font.Font(str(DISPLAY_FONT), size)
        except (OSError, pygame.error):
            pass
    return pygame.font.Font(None, int(size * (1.25 if display else 1)))


def clamp01(t):
    return max(0.0, min(1.0, t))


def ease_out(t):
    t = clamp01(t)
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    t = clamp01(t)
    return t * t * (3 - 2 * t)


class TextCache:
    """Renders text once and reuses the surface; menus redraw the same strings every frame."""

    def __init__(self):
        self._cache = {}

    def plain(self, font, text, color):
        key = ("p", id(font), text, color)
        surf = self._cache.get(key)
        if surf is None:
            surf = self._cache[key] = font.render(text, True, color)
        return surf

    def spaced(self, font, text, color, spacing):
        """Letter-spaced text, for the engraved look of the small-caps headings."""
        key = ("s", id(font), text, color, spacing)
        surf = self._cache.get(key)
        if surf is None:
            glyphs = [font.render(ch, True, color) for ch in text]
            width = sum(g.get_width() for g in glyphs) + spacing * max(0, len(glyphs) - 1)
            surf = pygame.Surface((max(1, width), font.get_height()), pygame.SRCALPHA)
            x = 0
            for g in glyphs:
                surf.blit(g, (x, 0))
                x += g.get_width() + spacing
            self._cache[key] = surf
        return surf

    def outlined(self, font, text, fill, outline, width):
        key = ("o", id(font), text, fill, outline, width)
        surf = self._cache.get(key)
        if surf is None:
            body = font.render(text, True, fill)
            edge = font.render(text, True, outline)
            surf = pygame.Surface((body.get_width() + width * 2, body.get_height() + width * 2), pygame.SRCALPHA)
            for dx in range(-width, width + 1):
                for dy in range(-width, width + 1):
                    if dx * dx + dy * dy <= width * width:
                        surf.blit(edge, (width + dx, width + dy))
            surf.blit(body, (width, width))
            self._cache[key] = surf
        return surf


def wrap(text, font, max_width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if font.size(trial)[0] <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_diamond(surf, center, r, color):
    x, y = center
    pygame.draw.polygon(surf, color, [(x, y - r), (x + r, y), (x, y + r), (x - r, y)])


def draw_ornament_rule(surf, cx, y, half_width, color, gap=0):
    """A frontier-poster rule:  •——————◆——————•  with an optional gap for text."""
    if gap:
        pygame.draw.line(surf, color, (cx - half_width, y), (cx - gap, y), 1)
        pygame.draw.line(surf, color, (cx + gap, y), (cx + half_width, y), 1)
        draw_diamond(surf, (cx - gap + 4, y), 3, color)
        draw_diamond(surf, (cx + gap - 4, y), 3, color)
    else:
        pygame.draw.line(surf, color, (cx - half_width, y), (cx + half_width, y), 1)
        draw_diamond(surf, (cx, y), 4, color)
    pygame.draw.circle(surf, color, (cx - half_width, y), 2)
    pygame.draw.circle(surf, color, (cx + half_width, y), 2)


def draw_arrow(surf, center, direction, size, color):
    """Solid triangle arrow. The built-in font has no glyph for ◄ ►, so arrows are drawn."""
    x, y = center
    pygame.draw.polygon(surf, color, [(x + direction * size, y), (x - direction * size * 0.6, y - size),
                                      (x - direction * size * 0.6, y + size)])


def draw_cartridge(surf, x, y, scale=1.0, alpha=255):
    """A small horizontal revolver cartridge, used as the menu's selection marker."""
    w, h = int(18 * scale), int(9 * scale)
    layer = pygame.Surface((w + h + 4, h + 4), pygame.SRCALPHA)
    pygame.draw.rect(layer, (*BRASS, alpha), (2, 2, w, h), border_radius=2)
    pygame.draw.rect(layer, (*BRASS_LIGHT, alpha), (2, 2, w, max(1, h // 3)), border_radius=2)
    pygame.draw.rect(layer, (*RUST, alpha), (2, 2, max(2, int(3 * scale)), h))
    pygame.draw.ellipse(layer, (*BONE_DIM, alpha), (w - h // 2, 2, h + 2, h))
    surf.blit(layer, (x, y - layer.get_height() // 2))


def edge_vignette(size, strength=200):
    """Dark corners for a full-screen surface (the arena vignettes cover the scene only)."""
    w, h = size
    v = pygame.Surface(size, pygame.SRCALPHA)
    steps = 36
    v.fill((*INK, strength))
    for i in range(steps):
        t = i / steps
        grow = 1.0 - t
        rect = pygame.Rect(0, 0, int(w * (0.5 + 0.95 * grow)), int(h * (0.5 + 0.95 * grow)))
        rect.center = (w // 2, h // 2)
        pygame.draw.ellipse(v, (*INK, int(strength * grow ** 1.5)), rect)
    return v




def draw_sign(surf, rect, alpha=232):
    """The dark wooden sign every menu sits on: double rule and four nail heads."""
    pygame.draw.rect(surf, (*PANEL, alpha), rect, border_radius=5)
    pygame.draw.rect(surf, LINE, rect, 1, border_radius=5)
    pygame.draw.rect(surf, INNER_RULE, rect.inflate(-8, -8), 1, border_radius=3)
    for nx, ny in ((rect.x + 10, rect.y + 10), (rect.right - 11, rect.y + 10),
                   (rect.x + 10, rect.bottom - 11), (rect.right - 11, rect.bottom - 11)):
        pygame.draw.circle(surf, (60, 34, 22), (nx, ny), 3)
        pygame.draw.circle(surf, (110, 72, 46), (nx - 1, ny - 1), 1)


# ---------------------------------------------------------------- option panel
class Row:
    """One option on a sign.

    kind  'action' - Enter or click runs action(now)
          'toggle' - get() -> bool, set(bool); shows ON / OFF
          'choice' - get() -> str to show; action(delta, now) steps it; drawn with arrows
          'slider' - get() -> int 0..steps, set(int); drawn as a row of notches
    """

    def __init__(self, key, label, kind="action", get=None, set=None, action=None, hint="",
                 visible=None, disabled_text=None, steps=10):
        self.key, self.label, self.kind = key, label, kind
        self.get, self.set, self.action = get, set, action
        self.hint = hint
        self.visible = visible or (lambda: True)
        self.disabled_text = disabled_text      # callable: returns text when the row can't be used
        self.steps = steps

    @property
    def disabled(self):
        return bool(self.disabled_text and self.disabled_text())

    def hint_text(self):
        return self.hint() if callable(self.hint) else self.hint


class OptionPanel:
    """A vertical list of Rows on a wooden sign, with a gliding highlight and a hint line.
    Driven by keys (up/down, left/right, enter) and the mouse (hover, click)."""

    PAD_TOP = 16
    TITLE_H = 52
    HINT_H = 62

    def __init__(self, rows, width=360, row_h=36, title=None, on_tick=None, on_click=None, hint_lines=2,
                 sign_alpha=232):
        self.rows = rows
        self.sign_alpha = sign_alpha
        self.width, self.row_h, self.title = width, row_h, title
        self.on_tick = on_tick or (lambda: None)
        self.on_click = on_click or (lambda: None)
        self.hint_lines = hint_lines
        self.text = TextCache()
        self.f_title = load_font(30, display=True)
        self.f_item = load_font(28)
        self.f_value = load_font(23)
        self.f_hint = load_font(22)
        self.index = 0
        self.hl_y = None
        self.arrow_kick = (0, 0)
        self.rect = pygame.Rect(0, 0, width, self.height)

    # ------------------------------------------------------------ layout
    @property
    def shown(self):
        return [r for r in self.rows if r.visible()]

    @property
    def item(self):
        rows = self.shown
        self.index = min(self.index, len(rows) - 1)
        return rows[self.index]

    @property
    def height(self):
        top = self.PAD_TOP + (self.TITLE_H if self.title else 0)
        return top + self.row_h * len(self.shown) + (self.HINT_H if self.hint_lines else 12)

    def place(self, center_x, top=None, center_y=None):
        h = self.height
        y = top if top is not None else center_y - h // 2
        self.rect = pygame.Rect(center_x - self.width // 2, y, self.width, h)
        return self.rect

    def row_rect(self, i):
        top = self.rect.y + self.PAD_TOP + (self.TITLE_H if self.title else 0)
        return pygame.Rect(self.rect.x + 10, top + i * self.row_h, self.rect.w - 20, self.row_h)

    def index_of(self, key):
        for i, r in enumerate(self.shown):
            if r.key == key:
                return i
        raise KeyError(key)

    def select(self, key):
        self.index = self.index_of(key)

    def arrow_rects(self, i):
        """Hit boxes for a choice row's left and right arrows."""
        r = self.row_rect(i)
        right = pygame.Rect(r.right - 34, r.y, 30, r.h)
        value_w = self.text.plain(self.f_value, self.shown[i].get(), BONE).get_width()
        left = pygame.Rect(right.x - value_w - 30 - 8, r.y, 30, r.h)
        return left, right

    def slider_rect(self, i):
        r = self.row_rect(i)
        steps = self.shown[i].steps
        w = steps * 11 - 4
        return pygame.Rect(r.right - 18 - w, r.centery - 8, w, 16)

    # ------------------------------------------------------------ input
    def move(self, delta):
        self.index = (self.index + delta) % len(self.shown)
        self.on_tick()

    def adjust(self, delta, now):
        row = self.item
        if row.disabled:
            return
        if row.kind == "toggle":
            row.set(not row.get())
            self.on_tick()
        elif row.kind == "choice":
            row.action(delta, now)
            self.arrow_kick = (delta, now)
            self.on_tick()
        elif row.kind == "slider":
            value = max(0, min(row.steps, row.get() + delta))
            if value != row.get():
                row.set(value)
                self.on_tick()

    def activate(self, now):
        row = self.item
        if row.disabled:
            return
        if row.kind == "action":
            self.on_click()
            row.action(now)
        elif row.kind == "toggle":
            row.set(not row.get())
            self.on_click()
        elif row.kind == "choice":
            self.adjust(1, now)

    def handle_key(self, key, now):
        if key in (pygame.K_UP, pygame.K_w):
            self.move(-1)
        elif key in (pygame.K_DOWN, pygame.K_s, pygame.K_TAB):
            self.move(1)
        elif key in (pygame.K_LEFT, pygame.K_a):
            self.adjust(-1, now)
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self.adjust(1, now)
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.activate(now)
        else:
            return False
        return True

    def row_at(self, pos):
        for i in range(len(self.shown)):
            if self.row_rect(i).collidepoint(pos):
                return i
        return None

    def hover(self, pos):
        i = self.row_at(pos)
        if i is not None and i != self.index:
            self.index = i
            self.on_tick()

    def click(self, pos, now):
        """Returns True if the click landed on a row."""
        i = self.row_at(pos)
        if i is None:
            return False
        self.index = i
        row = self.shown[i]
        if row.disabled:
            return True
        if row.kind == "choice":
            left, _ = self.arrow_rects(i)
            self.adjust(-1 if left.collidepoint(pos) else 1, now)
        elif row.kind == "slider":
            bar = self.slider_rect(i)
            if pos[0] < bar.x:
                self.adjust(-1, now)
            else:
                value = max(0, min(row.steps, int((pos[0] - bar.x) / 11) + 1))
                row.set(value)
                self.on_tick()
        else:
            self.activate(now)
        return True

    # ------------------------------------------------------------ drawing
    def draw(self, screen, now, alpha=255, yoff=0):
        p = self.rect
        panel = pygame.Surface(p.size, pygame.SRCALPHA)
        draw_sign(panel, panel.get_rect(), self.sign_alpha)
        rows = self.shown
        self.index = min(self.index, len(rows) - 1)

        top = self.PAD_TOP
        if self.title:
            head = self.text.plain(self.f_title, self.title, SUN)
            panel.blit(head, head.get_rect(midtop=(p.w // 2, 14)))
            draw_ornament_rule(panel, p.w // 2, 14 + head.get_height() + 6, min(140, p.w // 2 - 40), LINE)
            top += self.TITLE_H

        # selection highlight glides between rows
        target_y = top + self.index * self.row_h
        if self.hl_y is None:
            self.hl_y = float(target_y)
        self.hl_y += (target_y - self.hl_y) * 0.25
        hl = pygame.Rect(10, int(self.hl_y) + 3, p.w - 20, self.row_h - 6)
        glow = pygame.Surface(hl.size, pygame.SRCALPHA)        # blended, so the sign stays opaque
        pygame.draw.rect(glow, (*EMBER, 52), glow.get_rect(), border_radius=3)
        pygame.draw.rect(glow, (*EMBER, 120), glow.get_rect(), 1, border_radius=3)
        panel.blit(glow, hl.topleft)
        pygame.draw.rect(panel, EMBER, (hl.x, hl.y + 4, 3, hl.h - 8))

        for i, row in enumerate(rows):
            r = pygame.Rect(10, top + i * self.row_h, p.w - 20, self.row_h)
            selected = i == self.index
            cy = r.centery
            if selected:
                draw_cartridge(panel, r.x + 14, cy, 1.0)
            lcol = BONE_DIM if row.disabled else (SUN if selected else BONE)
            label = self.text.plain(self.f_item, row.label.upper(), lcol)
            panel.blit(label, label.get_rect(midleft=(r.x + 40 + (6 if selected else 0), cy + 1)))
            vcol = SUN if selected and not row.disabled else BONE_DIM
            right_x = r.right - 18
            if row.disabled:
                vs = self.text.plain(self.f_value, row.disabled_text(), BONE_DIM)
                panel.blit(vs, vs.get_rect(midright=(right_x, cy + 1)))
            elif row.kind == "toggle":
                vs = self.text.plain(self.f_value, "ON" if row.get() else "OFF", vcol if row.get() else BONE_DIM)
                panel.blit(vs, vs.get_rect(midright=(right_x, cy + 1)))
            elif row.kind == "choice":
                kick_dir, kick_t = self.arrow_kick
                kick = 4 * (1 - clamp01((now - kick_t) / 160)) if selected else 0
                draw_arrow(panel, (right_x + (kick if kick_dir > 0 else 0), cy), 1, 6, vcol)
                vs = self.text.plain(self.f_value, row.get(), vcol)
                vr = vs.get_rect(midright=(right_x - 14, cy + 1))
                panel.blit(vs, vr)
                draw_arrow(panel, (vr.x - 14 - (kick if kick_dir < 0 else 0), cy), -1, 6, vcol)
            elif row.kind == "slider":
                value = row.get()
                w = row.steps * 11 - 4
                x = right_x - w
                for n in range(row.steps):
                    notch = pygame.Rect(x + n * 11, cy - 8, 7, 16)
                    if n < value:
                        pygame.draw.rect(panel, vcol, notch, border_radius=3)
                    else:
                        pygame.draw.rect(panel, LINE, notch, 1, border_radius=3)

        if self.hint_lines:
            dy = top + self.row_h * len(rows) + 6
            draw_ornament_rule(panel, p.w // 2, dy, p.w // 2 - 30, LINE)
            y = dy + 12
            for line in wrap(self.item.hint_text(), self.f_hint, p.w - 44)[:self.hint_lines]:
                s = self.text.plain(self.f_hint, line, BONE_DIM)
                panel.blit(s, s.get_rect(midtop=(p.w // 2, y)))
                y += s.get_height() + 2

        if alpha < 255:
            panel.set_alpha(alpha)
        screen.blit(panel, (p.x, p.y + yoff))


def build_icon(size=64):
    """The game's icon: a loaded revolver cylinder on a sunset disc.
    Used for the window, the Windows .exe and the browser tab."""
    import math
    big = 256
    s = pygame.Surface((big, big), pygame.SRCALPHA)
    pygame.draw.rect(s, (*INK, 255), s.get_rect(), border_radius=48)
    for y in range(28, 228):                       # banded sunset disc
        dy = y - 128
        half = int(math.sqrt(max(0, 100 * 100 - dy * dy)))
        t = (y - 28) / 200
        color = (int(246 - 40 * t), int(150 - 70 * t), int(70 - 40 * t))
        if y > 140 and (y - 140) % 22 < 5:
            color = INK
        pygame.draw.line(s, color, (128 - half, y), (128 + half, y))
    cx = cy = 128
    pygame.draw.circle(s, STEEL_LIGHT, (cx, cy), 78)
    pygame.draw.circle(s, STEEL, (cx, cy), 74)
    for i in range(6):
        a = -math.pi / 2 + i * math.tau / 6
        fx, fy = cx + math.cos(a + math.pi / 6) * 84, cy + math.sin(a + math.pi / 6) * 84
        pygame.draw.circle(s, (0, 0, 0, 0), (int(fx), int(fy)), 16)
        px, py = int(cx + math.cos(a) * 44), int(cy + math.sin(a) * 44)
        pygame.draw.circle(s, STEEL_DARK, (px, py), 21)
        pygame.draw.circle(s, BRASS, (px, py), 18)
        pygame.draw.circle(s, BRASS_LIGHT, (px, py), 13)
        pygame.draw.circle(s, PRIMER, (px, py), 7)
    pygame.draw.circle(s, STEEL_DARK, (cx, cy), 14)
    pygame.draw.circle(s, STEEL_LIGHT, (cx, cy), 14, 3)
    return pygame.transform.smoothscale(s, (size, size)) if size != big else s
