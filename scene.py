"""Everything that gets drawn: multiple duel backdrops, ambient motion, wind & dust, smoke, and gunslingers."""
import math
import random

import pygame

from config import (
    BONE, BONE_DIM, EMBER, FEET, H, INK, LEATHER, SC, SUN, W,
    Arena, ARENAS, ARENA_MAP, get_arena
)


# ---------------------------------------------------------------- helpers
def _lerp(a, b, t):
    return a + (b - a) * t


def _gradient(stops, t):
    t = max(0.0, min(1.0, t))
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            u = (t - t0) / (t1 - t0) if t1 > t0 else 0
            return tuple(int(_lerp(c0[i], c1[i], u)) for i in range(3))
    return stops[-1][1]


def _bezier(p0, p1, p2, steps=8):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        pts.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
                    (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]))
    return pts


def _glow(surf, center, radius, color):
    size = int(radius * 2)
    if size <= 0:
        return
    g = pygame.Surface((size, size), pygame.SRCALPHA)
    for r in range(int(radius), 0, -2):
        alpha = int(255 * (1 - r / radius) ** 1.4)
        pygame.draw.circle(g, (*color, alpha), (radius, radius), r)
    surf.blit(g, (center[0] - radius, center[1] - radius))


# ---------------------------------------------------------------- backdrops
def build_desert_backdrop():
    """Paint the signature static desert. Returns a W x H surface."""
    surf = pygame.Surface((W, H))

    sky = [(0, (43, 14, 14)), (0.45, (143, 47, 23)), (0.8, (224, 102, 42)), (1, (246, 168, 68))]
    for y in range(0, 400):
        pygame.draw.line(surf, _gradient(sky, y / 390), (0, y), (W, y))

    sx, sy, sr = 480, 332, 98
    halo = pygame.Surface((W, 400), pygame.SRCALPHA)
    for r in range(320, 0, -4):
        pygame.draw.circle(halo, (255, 196, 120, int(140 * (1 - r / 320) ** 1.6)), (sx, sy), r)
    surf.blit(halo, (0, 0))

    disc = [(0, (255, 242, 200)), (1, (255, 181, 90))]
    for y in range(sy - sr, sy + sr + 1):
        dy = y - sy
        half = int(math.sqrt(max(0, sr * sr - dy * dy)))
        color = _gradient(disc, (y - (sy - sr)) / (2 * sr))
        for i in range(6):                      # retro bands cut across the lower half
            top = sy + 10 + i * 13
            if top <= y < top + 2 + i * 1.7:
                color = (238, 138, 54)
        pygame.draw.line(surf, color, (sx - half, y), (sx + half, y))

    far = (107, 36, 20)
    pygame.draw.polygon(surf, far, [(0, 384), (0, 332), (60, 332), (80, 302), (170, 302), (190, 332), (262, 337), (300, 384)])
    pygame.draw.polygon(surf, far, [(620, 384), (640, 342), (700, 342), (720, 312), (810, 312), (830, 292), (930, 292), (950, 332), (960, 332), (960, 384)])
    near = (61, 22, 14)
    pygame.draw.polygon(surf, near, [(0, 404), (0, 362), (40, 362), (70, 347), (150, 347), (180, 377), (230, 382), (262, 404)])
    pygame.draw.polygon(surf, near, [(700, 404), (720, 372), (790, 367), (830, 352), (900, 352), (930, 374), (960, 374), (960, 404)])

    ground = [(0, (163, 74, 26)), (0.35, (95, 40, 19)), (1, (26, 11, 7))]
    for y in range(382, H):
        pygame.draw.line(surf, _gradient(ground, (y - 382) / (H - 382)), (0, y), (W, y))
    pygame.draw.line(surf, (190, 104, 52), (0, 382), (W, 382), 3)

    rng = random.Random(7)                      # dry cracks in the ground
    for _ in range(46):
        y = 400 + rng.random() * 130
        x = rng.random() * W
        ln = 8 + (y - 390) * 0.18
        pygame.draw.lines(surf, (40, 18, 10), False,
                          [(x, y), (x + ln, y + (rng.random() - 0.5) * 4), (x + ln * 1.5, y + (rng.random() - 0.3) * 7)], 1)

    def cactus(x, base, h):
        w = h * 0.13
        rad = int(w / 2)
        pygame.draw.rect(surf, INK, (x - w / 2, base - h, w, h), border_radius=rad)
        pygame.draw.rect(surf, INK, (x - w / 2 - h * 0.24, base - h * 0.52, h * 0.24 + w * 0.4, w * 0.8), border_radius=rad)
        pygame.draw.rect(surf, INK, (x - w / 2 - h * 0.24, base - h * 0.52 - h * 0.2, w * 0.8, h * 0.2 + w * 0.8), border_radius=rad)
        pygame.draw.rect(surf, INK, (x + w / 2 - w * 0.4, base - h * 0.7, h * 0.22 + w * 0.4, w * 0.8), border_radius=rad)
        pygame.draw.rect(surf, INK, (x + w / 2 + h * 0.22 - w * 0.4, base - h * 0.7 - h * 0.17, w * 0.8, h * 0.17 + w * 0.8), border_radius=rad)

    cactus(78, 486, 160)
    cactus(896, 478, 138)
    cactus(430, 410, 34)
    return surf


def build_saloon_backdrop():
    """Paint the dusty main street outside a western saloon."""
    surf = pygame.Surface((W, H))

    # Late afternoon dusty sky
    sky = [(0, (68, 28, 16)), (0.35, (148, 62, 28)), (0.75, (218, 118, 48)), (1, (246, 178, 88))]
    for y in range(0, 390):
        pygame.draw.line(surf, _gradient(sky, y / 390), (0, y), (W, y))

    # Distant western mesas and ridges
    far = (88, 38, 22)
    pygame.draw.polygon(surf, far, [(0, 380), (0, 340), (140, 320), (220, 335), (320, 310), (450, 335), (550, 325), (680, 340), (820, 315), (960, 330), (960, 380)])

    # Silhouetted windmill tower in mid-distance
    wx, wy = 490, 275
    pygame.draw.polygon(surf, (48, 22, 14), [(wx - 14, 380), (wx - 6, wy + 26), (wx + 6, wy + 26), (wx + 14, 380)], 2)
    pygame.draw.line(surf, (48, 22, 14), (wx - 10, 335), (wx + 10, 335), 2)
    pygame.draw.circle(surf, (48, 22, 14), (wx, wy + 24), 16, 2)
    for a in range(8):
        ang = a * math.pi / 4
        pygame.draw.line(surf, (48, 22, 14), (wx, wy + 24), (wx + int(16 * math.cos(ang)), wy + 24 + int(16 * math.sin(ang))), 2)

    # ---------------- Saloon Building (Left side) ----------------
    saloon_col = (38, 18, 12)
    trim_col = (62, 30, 20)
    # Main 2-story false front facade
    pygame.draw.rect(surf, saloon_col, (0, 140, 360, 242))
    # False-front stepped decorative parapet header
    pygame.draw.polygon(surf, saloon_col, [(0, 140), (40, 140), (40, 115), (140, 115), (140, 95), (260, 95), (260, 115), (340, 115), (340, 140), (360, 140), (360, 382), (0, 382)])
    # Cornice trim line
    pygame.draw.line(surf, trim_col, (0, 142), (360, 142), 4)
    pygame.draw.line(surf, trim_col, (40, 116), (340, 116), 3)
    pygame.draw.line(surf, trim_col, (140, 96), (260, 96), 3)

    # Horizontal wood clapboard siding lines
    for ly in range(150, 380, 12):
        pygame.draw.line(surf, trim_col, (0, ly), (360, ly), 1)

    # Upper floor windows with warm amber mullions
    for wx_pos in (70, 160, 250):
        pygame.draw.rect(surf, (22, 10, 6), (wx_pos, 160, 38, 52))
        pygame.draw.rect(surf, (225, 155, 60), (wx_pos + 4, 164, 30, 44))
        # Window mullions
        pygame.draw.line(surf, saloon_col, (wx_pos + 19, 164), (wx_pos + 19, 208), 2)
        pygame.draw.line(surf, saloon_col, (wx_pos + 4, 186), (wx_pos + 34, 186), 2)

    # Saloon Porch roof
    pygame.draw.polygon(surf, (48, 22, 14), [(0, 255), (355, 255), (370, 275), (0, 275)])
    pygame.draw.line(surf, trim_col, (0, 255), (355, 255), 3)

    # Porch vertical support posts
    for px in (30, 125, 235, 345):
        pygame.draw.rect(surf, (30, 14, 8), (px - 5, 275, 10, 107))
        # Decorative support brackets at top of post
        pygame.draw.line(surf, (30, 14, 8), (px - 14, 275), (px, 290), 2)
        pygame.draw.line(surf, (30, 14, 8), (px + 14, 275), (px, 290), 2)

    # Balcony railing on top of porch roof
    pygame.draw.line(surf, trim_col, (0, 235), (355, 235), 2)
    for bx in range(10, 355, 14):
        pygame.draw.line(surf, trim_col, (bx, 235), (bx, 255), 1)

    # Double swinging saloon batwing doors on ground floor
    door_x, door_y = 150, 298
    pygame.draw.rect(surf, (18, 8, 4), (door_x - 4, door_y - 4, 68, 86))
    # Warm golden interior light leaking from saloon
    glow_surf = pygame.Surface((60, 80), pygame.SRCALPHA)
    glow_surf.fill((255, 205, 90, 180))
    surf.blit(glow_surf, (door_x, door_y))
    # Batwing saloon half-doors
    pygame.draw.rect(surf, (55, 26, 16), (door_x, door_y + 16, 26, 48), border_radius=3)
    pygame.draw.rect(surf, (55, 26, 16), (door_x + 34, door_y + 16, 26, 48), border_radius=3)
    for s_i in range(5):
        pygame.draw.line(surf, (36, 16, 10), (door_x + 3, door_y + 22 + s_i * 8), (door_x + 23, door_y + 22 + s_i * 8), 1)
        pygame.draw.line(surf, (36, 16, 10), (door_x + 37, door_y + 22 + s_i * 8), (door_x + 57, door_y + 22 + s_i * 8), 1)

    # Carved "SALOON" sign board hanging over porch
    pygame.draw.rect(surf, (22, 10, 6), (110, 118, 140, 24), border_radius=2)
    pygame.draw.rect(surf, (215, 165, 85), (112, 120, 136, 20), 2, border_radius=2)

    # Hitching rail in front of saloon
    pygame.draw.rect(surf, (28, 14, 8), (60, 362, 180, 5))
    pygame.draw.rect(surf, (28, 14, 8), (65, 365, 7, 24))
    pygame.draw.rect(surf, (28, 14, 8), (145, 365, 7, 24))
    pygame.draw.rect(surf, (28, 14, 8), (230, 365, 7, 24))
    # Wooden water trough
    pygame.draw.polygon(surf, (34, 16, 10), [(250, 370), (320, 370), (315, 386), (255, 386)])
    pygame.draw.line(surf, (90, 120, 140), (254, 372), (316, 372), 2)  # water surface reflection

    # ---------------- Right Side Town Buildings ----------------
    r_saloon = (32, 15, 10)
    pygame.draw.polygon(surf, r_saloon, [(780, 175), (860, 175), (860, 155), (960, 155), (960, 382), (780, 382)])
    pygame.draw.line(surf, trim_col, (780, 176), (960, 176), 3)
    # Right store awning
    pygame.draw.polygon(surf, (45, 20, 12), [(770, 270), (960, 270), (960, 290), (760, 290)])
    pygame.draw.rect(surf, (25, 11, 7), (800, 290, 8, 92))
    pygame.draw.rect(surf, (25, 11, 7), (910, 290, 8, 92))
    # Barrels beside store
    pygame.draw.ellipse(surf, (42, 20, 12), (745, 360, 22, 26))
    pygame.draw.ellipse(surf, (36, 16, 10), (760, 364, 20, 22))

    # ---------------- Ground: Dusty Main Street ----------------
    ground = [(0, (148, 82, 34)), (0.35, (86, 44, 20)), (1, (24, 12, 7))]
    for y in range(382, H):
        pygame.draw.line(surf, _gradient(ground, (y - 382) / (H - 382)), (0, y), (W, y))
    pygame.draw.line(surf, (175, 96, 44), (0, 382), (W, 382), 3)

    # Wooden sidewalk boardwalk planks under the saloon porch
    for plank_x in range(0, 360, 18):
        pygame.draw.line(surf, (48, 24, 14), (plank_x, 382), (plank_x, 400), 2)
    pygame.draw.line(surf, (70, 35, 20), (0, 400), (360, 400), 2)

    # Wagon wheel ruts in the dusty road
    rng = random.Random(42)
    for rut_offset in (-12, 12, -45, 45):
        pts = [(x, 440 + rut_offset + rng.uniform(-2, 2)) for x in range(350, W, 40)]
        if len(pts) >= 2:
            pygame.draw.lines(surf, (44, 22, 12), False, pts, 2)

    return surf


def build_railway_backdrop():
    """Paint the moonlit railway station at midnight."""
    surf = pygame.Surface((W, H))

    # Midnight sky gradient
    sky = [(0, (6, 10, 22)), (0.45, (14, 22, 46)), (0.8, (26, 40, 72)), (1, (44, 62, 98))]
    for y in range(0, 385):
        pygame.draw.line(surf, _gradient(sky, y / 385), (0, y), (W, y))

    # Twinkling stars in the night sky
    star_rng = random.Random(101)
    for _ in range(65):
        sx = int(star_rng.random() * W)
        sy = int(star_rng.random() * 260)
        brightness = star_rng.randint(120, 240)
        surf.set_at((sx, sy), (brightness, brightness, int(min(255, brightness * 1.1))))
        if star_rng.random() < 0.2:
            surf.set_at((sx + 1, sy), (brightness // 2, brightness // 2, brightness // 2))
            surf.set_at((sx, sy + 1), (brightness // 2, brightness // 2, brightness // 2))

    # Brilliant Full Moon with silvery luminous halo
    mx, my, mr = 680, 150, 58
    halo = pygame.Surface((W, 380), pygame.SRCALPHA)
    for r in range(240, 0, -4):
        alpha = int(115 * (1 - r / 240) ** 1.8)
        pygame.draw.circle(halo, (190, 220, 255, alpha), (mx, my), r)
    surf.blit(halo, (0, 0))

    # Silvery lunar disc with subtle lunar mare
    for y in range(my - mr, my + mr + 1):
        dy = y - my
        half = int(math.sqrt(max(0, mr * mr - dy * dy)))
        pygame.draw.line(surf, (235, 244, 255), (mx - half, y), (mx + half, y))
    # Crater shading
    pygame.draw.circle(surf, (208, 222, 240), (mx - 14, my - 10), 15)
    pygame.draw.circle(surf, (208, 222, 240), (mx + 12, my + 14), 18)
    pygame.draw.circle(surf, (195, 212, 232), (mx + 20, my - 6), 11)

    # Distant hills silhouetted in moonlight
    far_hills = (20, 30, 54)
    pygame.draw.polygon(surf, far_hills, [(0, 380), (0, 350), (120, 335), (260, 355), (420, 330), (580, 350), (740, 325), (960, 345), (960, 380)])

    # Telegraph poles with sagging wire lines on right horizon
    wire_col = (30, 42, 68)
    pole_x = [720, 830, 930]
    for px in pole_x:
        pygame.draw.line(surf, (16, 24, 42), (px, 260), (px, 380), 3)
        pygame.draw.line(surf, (16, 24, 42), (px - 14, 275), (px + 14, 275), 2)
        pygame.draw.line(surf, (16, 24, 42), (px - 10, 290), (px + 10, 290), 2)
    for p1, p2 in zip(pole_x, pole_x[1:]):
        pts1 = _bezier((p1, 275), ((p1 + p2) // 2, 283), (p2, 275), 10)
        pts2 = _bezier((p1, 290), ((p1 + p2) // 2, 297), (p2, 290), 10)
        pygame.draw.lines(surf, wire_col, False, pts1, 1)
        pygame.draw.lines(surf, wire_col, False, pts2, 1)

    # ---------------- Steam Locomotive on Siding (Midground) ----------------
    loco = (14, 18, 32)
    # Boiler body
    pygame.draw.rect(surf, loco, (420, 290, 260, 68), border_radius=6)
    # Driver's cab
    pygame.draw.polygon(surf, loco, [(640, 240), (715, 240), (720, 358), (640, 358)])
    # Cab roof overhang
    pygame.draw.line(surf, (28, 38, 62), (635, 240), (722, 240), 3)
    # Cab window with glowing firebox amber light
    pygame.draw.rect(surf, (245, 140, 40), (660, 260, 24, 28))
    # Smokestack funnel
    pygame.draw.polygon(surf, loco, [(455, 290), (450, 242), (475, 242), (470, 290)])
    pygame.draw.line(surf, (28, 38, 62), (446, 242), (479, 242), 3)
    # Steam dome & bell
    pygame.draw.ellipse(surf, loco, (515, 278, 28, 22))
    pygame.draw.ellipse(surf, loco, (585, 280, 22, 18))
    # Cowcatcher grill
    pygame.draw.polygon(surf, loco, [(420, 358), (370, 370), (420, 370)])
    for cg in range(375, 420, 8):
        pygame.draw.line(surf, (28, 38, 62), (cg, 370), (420, 358), 1)
    # Wheels and pistons
    for wx in (450, 520, 590):
        pygame.draw.circle(surf, loco, (wx, 360), 22)
        pygame.draw.circle(surf, (26, 36, 58), (wx, 360), 16, 2)
    pygame.draw.line(surf, (45, 60, 90), (440, 364), (605, 364), 4)

    # Brass headlamp beam casting translucent cone of light
    lamp_beam = pygame.Surface((320, 100), pygame.SRCALPHA)
    pygame.draw.polygon(lamp_beam, (255, 225, 140, 45), [(0, 15), (280, 0), (280, 75), (0, 25)])
    surf.blit(lamp_beam, (120, 275))
    _glow(surf, (410, 295), 18, (255, 220, 120))

    # ---------------- Dry Creek Depot Station (Left side) ----------------
    depot = (12, 16, 28)
    trim = (24, 34, 56)
    # Main depot station structure
    pygame.draw.rect(surf, depot, (0, 190, 300, 192))
    # Steep Victorian gabled roof
    pygame.draw.polygon(surf, depot, [(0, 190), (130, 95), (260, 190)])
    pygame.draw.line(surf, trim, (0, 190), (130, 95), 4)
    pygame.draw.line(surf, trim, (130, 95), (260, 190), 4)
    # Ornamental rooftop finial
    pygame.draw.line(surf, trim, (130, 95), (130, 70), 3)

    # Depot platform roof extension
    pygame.draw.polygon(surf, (18, 24, 40), [(0, 260), (320, 260), (330, 275), (0, 275)])
    pygame.draw.line(surf, trim, (0, 260), (320, 260), 3)
    # Wooden platform posts
    for p_x in (40, 140, 240, 315):
        pygame.draw.rect(surf, depot, (p_x - 4, 275, 8, 107))

    # Warm glowing ticket window
    pygame.draw.rect(surf, (245, 180, 70), (70, 285, 36, 48))
    pygame.draw.line(surf, depot, (88, 285), (88, 333), 2)
    pygame.draw.line(surf, depot, (70, 309), (106, 309), 2)

    # Hanging oil lantern glowing warm golden amber
    _glow(surf, (240, 280), 22, (255, 185, 70))
    pygame.draw.circle(surf, (255, 230, 150), (240, 280), 5)
    pygame.draw.line(surf, (40, 50, 75), (240, 262), (240, 276), 2)

    # ---------------- Ground & Train Tracks ----------------
    ground = [(0, (32, 44, 68)), (0.35, (18, 26, 44)), (1, (8, 12, 22))]
    for y in range(382, H):
        pygame.draw.line(surf, _gradient(ground, (y - 382) / (H - 382)), (0, y), (W, y))
    pygame.draw.line(surf, (55, 75, 110), (0, 382), (W, 382), 2)

    # Railroad cross-ties
    for tie_x in range(0, W, 22):
        pygame.draw.rect(surf, (14, 20, 34), (tie_x, 383, 14, 18))
    # Dual iron rails with moonlit metallic glint
    pygame.draw.line(surf, (95, 125, 170), (0, 385), (W, 385), 3)
    pygame.draw.line(surf, (95, 125, 170), (0, 397), (W, 397), 3)
    pygame.draw.line(surf, (170, 205, 255), (0, 384), (W, 384), 1)  # top rail sheen
    pygame.draw.line(surf, (170, 205, 255), (0, 396), (W, 396), 1)

    return surf


def build_ghost_town_backdrop():
    """Paint the ghost town during a ferocious sandstorm."""
    surf = pygame.Surface((W, H))

    # Violent sepia and rust storm sky
    sky = [(0, (54, 28, 16)), (0.4, (115, 62, 30)), (0.75, (175, 102, 48)), (1, (205, 135, 75))]
    for y in range(0, 390):
        pygame.draw.line(surf, _gradient(sky, y / 390), (0, y), (W, y))

    # Dim, ghostly washed-out sun obscured by dust storm
    sx, sy, sr = 480, 240, 75
    halo = pygame.Surface((W, 380), pygame.SRCALPHA)
    for r in range(180, 0, -4):
        alpha = int(75 * (1 - r / 180) ** 1.5)
        pygame.draw.circle(halo, (245, 190, 110, alpha), (sx, sy), r)
    surf.blit(halo, (0, 0))
    pygame.draw.circle(surf, (240, 205, 150), (sx, sy), sr)

    # Boot Hill graveyard crosses on distant hill ridge
    far = (75, 38, 22)
    pygame.draw.polygon(surf, far, [(0, 380), (0, 340), (120, 325), (280, 345), (420, 320), (560, 340), (700, 315), (840, 335), (960, 325), (960, 380)])
    # Crooked cemetery crosses on ridge
    for cx in (150, 175, 195, 230, 255):
        cy = 338
        pygame.draw.line(surf, (42, 20, 12), (cx, cy - 14), (cx, cy), 2)
        pygame.draw.line(surf, (42, 20, 12), (cx - 5, cy - 10), (cx + 5, cy - 10), 2)

    # ---------------- Ruined Tilting Church / Meeting Hall (Left) ----------------
    # Notice: tilted at an angle, damaged by time and storms
    ruin_col = (34, 18, 12)
    trim_col = (54, 28, 18)
    # Tilting church facade (tilted ~5 degrees)
    church_pts = [(50, 382), (65, 170), (145, 100), (220, 180), (200, 382)]
    pygame.draw.polygon(surf, ruin_col, church_pts)
    pygame.draw.lines(surf, trim_col, True, church_pts, 3)

    # Collapsed roof rafters sticking out
    for rx in range(120, 220, 16):
        pygame.draw.line(surf, (45, 24, 16), (rx, 140), (rx + 25, 90), 2)

    # Crooked belfry with cracked silent bell
    belfry_pts = [(90, 110), (95, 55), (145, 50), (140, 105)]
    pygame.draw.polygon(surf, ruin_col, belfry_pts)
    pygame.draw.lines(surf, trim_col, True, belfry_pts, 2)
    # Belfry window opening
    pygame.draw.rect(surf, (18, 8, 5), (105, 68, 22, 30))
    # Cracked bell silhouette
    pygame.draw.ellipse(surf, (55, 30, 18), (108, 74, 16, 16))

    # Shattered arched window in church facade
    pygame.draw.polygon(surf, (18, 8, 5), [(105, 240), (108, 195), (135, 195), (138, 240)])

    # Weathered missing wallboards where wind whistles through
    for wy in range(260, 370, 14):
        pygame.draw.line(surf, trim_col, (65, wy), (200, wy + 8), 1)
        if wy % 28 == 0:
            pygame.draw.line(surf, (18, 8, 5), (90, wy), (150, wy + 4), 3)

    # ---------------- Abandoned Tilting Buildings (Right) ----------------
    r_ruin = [(760, 382), (770, 210), (890, 195), (960, 220), (960, 382)]
    pygame.draw.polygon(surf, ruin_col, r_ruin)
    pygame.draw.lines(surf, trim_col, True, r_ruin, 2)
    # Collapsed sagging awning
    pygame.draw.polygon(surf, (26, 14, 8), [(750, 290), (900, 275), (910, 295), (745, 315)])
    # Broken leaning support timber
    pygame.draw.line(surf, (45, 24, 16), (750, 315), (785, 382), 4)

    # Half-buried weathered wagon wheel in creeping sand drift
    ww_x, ww_y = 650, 382
    pygame.draw.circle(surf, (40, 20, 12), (ww_x, ww_y), 24, 3)
    for sp in range(6):
        sa = sp * math.pi / 3
        pygame.draw.line(surf, (40, 20, 12), (ww_x, ww_y), (ww_x + int(24 * math.cos(sa)), ww_y + int(24 * math.sin(sa))), 2)

    # ---------------- Ground: Shifting Sand Dunes & Drift Ripples ----------------
    ground = [(0, (170, 105, 52)), (0.35, (105, 58, 28)), (1, (34, 16, 9))]
    for y in range(382, H):
        pygame.draw.line(surf, _gradient(ground, (y - 382) / (H - 382)), (0, y), (W, y))
    pygame.draw.line(surf, (195, 125, 65), (0, 382), (W, 382), 3)

    # Wind-carved sand ripples and dunes
    rng = random.Random(88)
    for _ in range(35):
        ry = 390 + rng.random() * 140
        rx = rng.random() * W
        rlen = 30 + rng.random() * 80
        pygame.draw.line(surf, (135, 75, 36), (rx, ry), (rx + rlen, ry + (rng.random() - 0.5) * 3), 2)

    return surf


def build_canyon_backdrop():
    """Paint the towering canyon gorge and wooden suspension bridge."""
    surf = pygame.Surface((W, H))

    # Twilight canyon sky
    sky = [(0, (28, 14, 34)), (0.35, (86, 32, 48)), (0.7, (175, 74, 52)), (1, (230, 132, 70))]
    for y in range(0, 385):
        pygame.draw.line(surf, _gradient(sky, y / 385), (0, y), (W, y))

    # Soaring golden eagle silhouette circling in the canyon sky
    ex, ey = 470, 140
    pygame.draw.polygon(surf, (30, 12, 18), [
        (ex - 22, ey - 4), (ex - 10, ey - 8), (ex, ey - 2),
        (ex + 10, ey - 8), (ex + 22, ey - 4), (ex + 14, ey + 2),
        (ex, ey + 4), (ex - 14, ey + 2)
    ])

    # ---------------- Canyon Gorge Abyss (Center) ----------------
    # Deep purple chasm falling into darkness
    abyss = [(0, (75, 28, 40)), (0.4, (38, 14, 26)), (1, (12, 6, 16))]
    for y in range(350, H):
        t = (y - 350) / (H - 350)
        pygame.draw.line(surf, _gradient(abyss, t), (160, y), (800, y))

    # River reflection glimmer far down in the gorge bottom
    pygame.draw.ellipse(surf, (95, 45, 65), (410, 500, 140, 16))

    # ---------------- Towering Sandstone Cliffs (Left and Right) ----------------
    cliff_far = (75, 28, 28)
    cliff_mid = (50, 18, 20)
    cliff_near = (32, 12, 14)

    # Left sheer canyon cliff with horizontal strata layers
    pygame.draw.polygon(surf, cliff_near, [(0, 160), (140, 185), (170, 240), (150, 310), (190, 382), (180, H), (0, H)])
    # Left cliff strata bands
    for sy in range(180, 520, 22):
        pygame.draw.line(surf, (48, 18, 22), (0, sy), (170, sy + 6), 3)

    # Right sheer canyon cliff
    pygame.draw.polygon(surf, cliff_near, [(960, 150), (810, 180), (790, 250), (820, 320), (770, 382), (780, H), (960, H)])
    # Right cliff strata bands
    for sy in range(170, 520, 22):
        pygame.draw.line(surf, (48, 18, 22), (780, sy + 4), (960, sy), 3)

    # ---------------- Wooden Trestle Bridge (Spans the gorge) ----------------
    bridge_col = (36, 16, 12)
    beam_col = (54, 26, 18)

    # Vertical bridge trestle bents plunging into the abyss
    for bx in (220, 340, 480, 620, 740):
        pygame.draw.rect(surf, bridge_col, (bx - 6, 382, 12, H - 382))
        # Cross bracing (X-braces) between trestle bents
        if bx < 740:
            next_bx = bx + 120 if bx != 620 else 740
            pygame.draw.line(surf, beam_col, (bx, 400), (next_bx, 480), 3)
            pygame.draw.line(surf, beam_col, (bx, 480), (next_bx, 400), 3)
            pygame.draw.line(surf, beam_col, (bx, 480), (next_bx, 530), 3)
            pygame.draw.line(surf, beam_col, (bx, 530), (next_bx, 480), 3)

    # Suspension cables arching across the gorge
    cable_col = (45, 20, 24)
    cable_pts1 = _bezier((140, 185), (480, 375), (810, 180), 24)
    pygame.draw.lines(surf, cable_col, False, cable_pts1, 3)
    # Vertical suspender ropes
    for hx in range(200, 780, 40):
        # find y on cable
        t_c = (hx - 140) / (810 - 140)
        t_c = max(0.0, min(1.0, t_c))
        cy = int((1 - t_c) ** 2 * 185 + 2 * (1 - t_c) * t_c * 375 + t_c * t_c * 180)
        pygame.draw.line(surf, cable_col, (hx, cy), (hx, 382), 1)

    # Heavy timber safety guardrails
    pygame.draw.line(surf, beam_col, (0, 360), (W, 360), 3)
    pygame.draw.line(surf, beam_col, (0, 372), (W, 372), 2)
    for rx in range(0, W, 28):
        pygame.draw.line(surf, bridge_col, (rx, 358), (rx, 382), 2)

    # ---------------- Ground: Wooden Bridge Decking Planks ----------------
    # Planks spanning the gorge with visible gaps revealing the abyss below!
    pygame.draw.rect(surf, (22, 10, 8), (0, 382, W, H - 382))
    for px in range(0, W, 12):
        # Timber plank with gap
        pygame.draw.line(surf, (58, 28, 18), (px, 382), (px, H), 9)
        # Gap revealing abyss
        pygame.draw.line(surf, (14, 6, 12), (px + 10, 382), (px + 10, H), 3)
        # Iron bolts
        pygame.draw.circle(surf, (20, 10, 8), (px + 4, 390), 2)
        pygame.draw.circle(surf, (20, 10, 8), (px + 4, 460), 2)

    pygame.draw.line(surf, (85, 42, 26), (0, 382), (W, 382), 3)
    return surf


def build_rain_backdrop():
    """Paint the rain-soaked street at night with glowing puddle reflections."""
    surf = pygame.Surface((W, H))

    # Midnight thunderstorm sky
    sky = [(0, (8, 10, 18)), (0.4, (18, 24, 38)), (0.75, (28, 38, 56)), (1, (42, 54, 76))]
    for y in range(0, 385):
        pygame.draw.line(surf, _gradient(sky, y / 385), (0, y), (W, y))

    # Silhouetted stormy rain cloud masses
    cloud_col = (12, 16, 26)
    for cx, cy, cr in [(120, 110, 110), (280, 90, 130), (500, 120, 140), (740, 80, 150), (900, 110, 120)]:
        pygame.draw.circle(surf, cloud_col, (cx, cy), cr)

    # Silhouetted rain-drenched western buildings in the background
    bldg_col = (14, 18, 28)
    trim_col = (26, 34, 50)
    # Left shopfronts
    pygame.draw.polygon(surf, bldg_col, [(0, 180), (160, 180), (160, 155), (320, 155), (320, 382), (0, 382)])
    pygame.draw.line(surf, trim_col, (0, 181), (160, 181), 3)
    pygame.draw.line(surf, trim_col, (160, 156), (320, 156), 3)
    # Overhanging roof awnings dripping with rain
    pygame.draw.polygon(surf, (20, 26, 38), [(0, 270), (330, 270), (340, 285), (0, 285)])

    # Right shopfronts
    pygame.draw.polygon(surf, bldg_col, [(680, 170), (840, 170), (840, 145), (960, 145), (960, 382), (680, 382)])
    pygame.draw.line(surf, trim_col, (680, 171), (840, 171), 3)
    pygame.draw.line(surf, trim_col, (840, 146), (960, 146), 3)

    # Flickering tavern windows casting warm golden amber light
    pygame.draw.rect(surf, (235, 165, 55), (75, 298, 42, 54))
    pygame.draw.line(surf, bldg_col, (96, 298), (96, 352), 2)
    pygame.draw.line(surf, bldg_col, (75, 325), (117, 325), 2)

    pygame.draw.rect(surf, (235, 165, 55), (740, 298, 42, 54))
    pygame.draw.line(surf, bldg_col, (761, 298), (761, 352), 2)
    pygame.draw.line(surf, bldg_col, (740, 325), (782, 325), 2)

    # Street lanterns on iron poles casting glowing warm light
    for lx in (210, 860):
        # Iron lamp post
        pygame.draw.line(surf, (10, 14, 22), (lx, 260), (lx, 382), 4)
        pygame.draw.line(surf, (10, 14, 22), (lx - 12, 260), (lx + 12, 260), 3)
        # Lantern warm glow
        _glow(surf, (lx, 270), 36, (255, 190, 80))
        pygame.draw.circle(surf, (255, 230, 160), (lx, 270), 6)

    # ---------------- Ground: Rain-Slick Mud with Puddle Reflections ----------------
    ground = [(0, (26, 34, 48)), (0.35, (16, 22, 32)), (1, (8, 10, 16))]
    for y in range(382, H):
        pygame.draw.line(surf, _gradient(ground, (y - 382) / (H - 382)), (0, y), (W, y))
    pygame.draw.line(surf, (48, 64, 88), (0, 382), (W, 382), 2)

    # Shimmering wet puddles reflecting lantern & window light
    puddles = [
        (210, 440, 140, 28),   # under left lantern
        (96, 475, 110, 22),    # under left window
        (480, 460, 220, 34),   # central large puddle
        (760, 480, 120, 24),   # under right window
        (860, 445, 150, 30),   # under right lantern
    ]
    for px, py, pw, ph in puddles:
        p_surf = pygame.Surface((pw * 2, ph * 2), pygame.SRCALPHA)
        # Water base (dark glassy blue)
        pygame.draw.ellipse(p_surf, (18, 28, 44, 190), (0, 0, pw * 2, ph * 2))
        # Warm golden reflection column in puddle
        refl_color = (255, 185, 75, 80)
        pygame.draw.ellipse(p_surf, refl_color, (pw - 25, 4, 50, ph * 2 - 8))
        pygame.draw.ellipse(p_surf, (255, 220, 140, 110), (pw - 12, 8, 24, ph * 2 - 16))
        # Water rim
        pygame.draw.ellipse(p_surf, (65, 85, 115, 140), (0, 0, pw * 2, ph * 2), 2)
        surf.blit(p_surf, (px - pw, py - ph))

    return surf


# ---------------------------------------------------------------- backdrop cache
_BACKDROP_CACHE = {}


def get_backdrop(arena_id="desert"):
    """Get the cached W x H surface for the specified arena."""
    if arena_id not in _BACKDROP_CACHE:
        builder = {
            "desert": build_desert_backdrop,
            "saloon": build_saloon_backdrop,
            "railway": build_railway_backdrop,
            "ghost_town": build_ghost_town_backdrop,
            "canyon": build_canyon_backdrop,
            "rain": build_rain_backdrop,
        }.get(arena_id, build_desert_backdrop)
        _BACKDROP_CACHE[arena_id] = builder()
    return _BACKDROP_CACHE[arena_id]


def build_backdrop(arena_id="desert"):
    """Backwards compatible function that returns the backdrop for an arena."""
    return get_backdrop(arena_id)


# ---------------------------------------------------------------- vignettes
_VIGNETTE_CACHE = {}


def get_vignette(tint=(8, 3, 2)):
    """Dark edges tailored to the arena color atmosphere, cached."""
    if tint not in _VIGNETTE_CACHE:
        v = pygame.Surface((W, H), pygame.SRCALPHA)
        v.fill((*tint, 128))
        steps = 40
        for i in range(steps):
            t = i / steps
            grow = 1.0 - t
            w, h = int(W * (0.55 + 0.9 * grow)), int(H * (0.55 + 0.9 * grow))
            alpha = int(128 * grow ** 1.6)
            rect = pygame.Rect(0, 0, w, h)
            rect.center = (W // 2, int(H * 0.58))
            pygame.draw.ellipse(v, (*tint, alpha), rect)
        _VIGNETTE_CACHE[tint] = v
    return _VIGNETTE_CACHE[tint]


def build_vignette(tint=(8, 3, 2)):
    return get_vignette(tint)


# ---------------------------------------------------------------- gun smoke
class SmokePuff:
    def __init__(self, x, y, vx, vy, max_r, duration_ms, start_alpha=180):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.max_r = max_r
        self.duration = duration_ms
        self.age = 0.0
        self.start_alpha = start_alpha


class SmokeSystem:
    def __init__(self):
        self.puffs = []
        self._layer = pygame.Surface((W, H), pygame.SRCALPHA)

    def spawn(self, x, y, direction, wind_speed=0.1):
        """Spawn a billowing cluster of smoke puffs from the gun barrel."""
        for _ in range(15):
            # Forward burst from muzzle + thermal rise + wind
            speed = random.uniform(0.8, 3.2) * direction
            vy = random.uniform(-0.9, -0.2)
            vx = speed + random.uniform(-0.4, 0.4) + wind_speed * 0.35
            vy += random.uniform(-0.35, 0.35)
            dur = random.uniform(800, 1350)
            max_r = random.uniform(16, 32)
            ox = random.uniform(-3, 6) * direction
            oy = random.uniform(-4, 4)
            self.puffs.append(SmokePuff(x + ox, y + oy, vx, vy, max_r, dur))

    def update(self, dt_ms, wind_speed=0.1):
        alive = []
        for p in self.puffs:
            p.age += dt_ms
            if p.age < p.duration:
                # Wind drift & thermal float
                p.vx += wind_speed * (dt_ms * 0.001) * 0.7
                p.vy -= 0.00035 * dt_ms
                p.x += p.vx * (dt_ms * 0.06)
                p.y += p.vy * (dt_ms * 0.06)
                alive.append(p)
        self.puffs = alive

    def draw(self, surf):
        if not self.puffs:
            return
        self._layer.fill((0, 0, 0, 0))
        for p in self.puffs:
            t = p.age / p.duration  # 0 to 1
            # Expanding billow
            r = int(5 + (p.max_r - 5) * (1 - (1 - t) ** 2))
            if r <= 1:
                continue
            alpha = int(p.start_alpha * (1 - t) ** 1.6)
            if alpha <= 0:
                continue
            # Authentic black powder smoke: white-gray with soft edge
            shade = int(215 - 25 * t)
            color = (shade, shade - 4, shade - 8, alpha)
            pygame.draw.circle(self._layer, color, (int(p.x), int(p.y)), r)
        surf.blit(self._layer, (0, 0))

    def clear(self):
        self.puffs.clear()


# ---------------------------------------------------------------- ambient motion
class Ambient:
    def __init__(self, arena_id="desert"):
        self.arena_id = arena_id
        self.arena = get_arena(arena_id)
        self._layer = pygame.Surface((W, H), pygame.SRCALPHA)
        self._lightning_flash = 0.0
        self._next_lightning = 8000.0
        self._init_particles()

    def set_arena(self, arena_id):
        if arena_id != self.arena_id:
            self.arena_id = arena_id
            self.arena = get_arena(arena_id)
            self._init_particles()

    def _init_particles(self):
        rng = random.Random(21)
        # General dust particles
        count = self.arena.dust_density
        self.dust = []
        for _ in range(count):
            x = rng.random() * W
            y = 180 + rng.random() * 340
            speed = 0.015 + rng.random() * 0.06
            r = 0.8 + rng.random() * 2.2
            alpha = int(30 + rng.random() * 65)
            self.dust.append([x, y, speed, r, alpha])

        # Wind streaks: elongated dust wisps flying horizontally
        streak_count = 18 if self.arena.id != "ghost_town" else 48
        self.streaks = []
        for _ in range(streak_count):
            sx = rng.random() * W
            sy = 360 + rng.random() * 160
            slen = 18 + rng.random() * 45
            sv = 0.12 + rng.random() * 0.28
            sa = int(20 + rng.random() * 45)
            self.streaks.append([sx, sy, slen, sv, sa])

        # Rain streaks (for rain arena)
        self.rain_drops = []
        if self.arena.id == "rain":
            for _ in range(130):
                rx = rng.random() * (W + 160) - 80
                ry = rng.random() * H
                rv = 0.75 + rng.random() * 0.45
                rlen = 14 + rng.random() * 16
                ra = int(120 + rng.random() * 90)
                self.rain_drops.append([rx, ry, rv, rlen, ra])
        self.rain_splashes = []

    def draw(self, surf, now, dt_ms=16):
        self._layer.fill((0, 0, 0, 0))

        # Dynamic wind speed with natural gusts
        gust = 0.05 * math.sin(now * 0.0013) + 0.03 * math.sin(now * 0.0031)
        current_wind = self.arena.wind_base + gust

        # Draw ambient dust motes blowing with the wind
        dust_color = self.arena.cowboy_tint
        for d in self.dust:
            # Move particle with wind speed
            d[0] = (d[0] + dt_ms * (d[2] + current_wind * 0.4)) % (W + 40) - 20
            # Subtle vertical floating bob
            py = d[1] + math.sin(now * 0.002 + d[0]) * 1.5
            pygame.draw.circle(self._layer, (*dust_color, d[4]), (int(d[0]), int(py)), d[3])

        # Draw windblown dust streaks skimming across the scene
        for s in self.streaks:
            s[0] = (s[0] + dt_ms * (s[3] + current_wind * 0.8)) % (W + 80) - 40
            streak_col = (*dust_color, s[4])
            pygame.draw.line(self._layer, streak_col, (int(s[0]), int(s[1])), (int(s[0] + s[2]), int(s[1])), 1)

        # ---------------- Arena-specific Atmospheres ----------------
        if self.arena.id in ("desert", "saloon", "ghost_town"):
            # Tumbleweeds rolling past
            tb_count = 1 if self.arena.id != "ghost_town" else 3
            for t_idx in range(tb_count):
                speed_mult = 0.045 if self.arena.id != "ghost_town" else 0.085 + t_idx * 0.02
                offset = t_idx * 380
                cx = ((now + offset) * speed_mult) % (W + 260) - 130
                bounce_freq = 0.008 if self.arena.id != "ghost_town" else 0.014
                cy = FEET + 24 - abs(math.sin((now + offset) * bounce_freq)) * 18
                spin = now * 0.007 * (1.5 if self.arena.id == "ghost_town" else 1.0)
                for k in range(5):
                    rx, ry = 15, 15 if k == 0 else 5 + (k - 1) * 2.4
                    tilt = spin + k * 0.8
                    pts = []
                    for i in range(20):
                        a = i / 20 * math.tau
                        ex, ey = rx * math.cos(a), ry * math.sin(a)
                        pts.append((cx + ex * math.cos(tilt) - ey * math.sin(tilt), cy + ex * math.sin(tilt) + ey * math.cos(tilt)))
                    pygame.draw.polygon(self._layer, (42, 20, 10, 200), pts, 2)

        if self.arena.id == "ghost_town":
            # Dense horizontal sand sheets blowing across the screen
            sheet_alpha = int(32 + 18 * math.sin(now * 0.002))
            sheet = pygame.Surface((W, H), pygame.SRCALPHA)
            sheet.fill((215, 140, 70, sheet_alpha))
            surf.blit(sheet, (0, 0))

        if self.arena.id == "rain":
            # Driving rain streaks angled with the wind
            wind_angle = 0.28
            for r in self.rain_drops:
                r[0] = (r[0] + dt_ms * current_wind * 1.5) % (W + 120) - 60
                r[1] += dt_ms * r[2]
                if r[1] > FEET + 35:
                    r[1] = -10
                    # Chance to spawn splash on ground/puddles
                    if random.random() < 0.25:
                        self.rain_splashes.append([r[0], FEET + random.uniform(10, 50), 0.0, random.uniform(4, 9)])
                dx = int(r[3] * wind_angle)
                pygame.draw.line(self._layer, (180, 210, 255, r[4]), (int(r[0]), int(r[1])), (int(r[0] + dx), int(r[1] + r[3])), 1)

            # Water puddle splashes
            alive_splashes = []
            for sp in self.rain_splashes:
                sp[2] += dt_ms * 0.003
                if sp[2] < 1.0:
                    sr = int(sp[3] * sp[2])
                    alpha = int(140 * (1 - sp[2]))
                    if sr > 0:
                        pygame.draw.ellipse(self._layer, (200, 225, 255, alpha), (sp[0] - sr, sp[1] - sr // 2, sr * 2, sr), 1)
                    alive_splashes.append(sp)
            self.rain_splashes = alive_splashes

            # Lightning flash logic
            if now >= self._next_lightning:
                self._lightning_flash = 1.0
                self._next_lightning = now + random.uniform(7000, 14000)
            if self._lightning_flash > 0:
                self._lightning_flash = max(0.0, self._lightning_flash - dt_ms * 0.007)
                flash_surf = pygame.Surface((W, H), pygame.SRCALPHA)
                flash_alpha = int(180 * self._lightning_flash)
                flash_surf.fill((210, 230, 255, flash_alpha))
                surf.blit(flash_surf, (0, 0))

        surf.blit(self._layer, (0, 0))


# ---------------------------------------------------------------- gunslinger
def get_muzzle_pos(x, direction, arm, fall=0.0, sway=0.0):
    """Compute the exact (mx, my) world coordinates of the gun barrel tip."""
    theta = -fall * 1.5 + sway
    c, s = math.cos(theta), math.sin(theta)
    jump = -math.sin(math.pi * fall) * 14

    def body(px, py):
        rx, ry = px * c - py * s, px * s + py * c
        return (x + direction * SC * rx, FEET + SC * (ry + jump))

    ca, sa = math.cos(-arm), math.sin(-arm)

    def limb(qx, qy):
        return body(8 + qx * ca - qy * sa, -124 + qx * sa + qy * ca)

    return limb(0, 90)


def draw_cowboy(surf, x, direction, arm, fall, flash, sway, accent, star=False, rim_tint=None):
    """Draw one silhouette gunslinger.

    arm   - angle of the gun arm in radians, 0 is hanging down, ~1.55 is pointing at the opponent
    fall  - 0..1, how far the gunslinger has toppled backwards
    flash - 0..1, muzzle flash strength
    """
    theta = -fall * 1.5 + sway
    c, s = math.cos(theta), math.sin(theta)
    jump = -math.sin(math.pi * fall) * 14

    def body(px, py):
        rx, ry = px * c - py * s, px * s + py * c
        return (x + direction * SC * rx, FEET + SC * (ry + jump))

    ca, sa = math.cos(-arm), math.sin(-arm)

    def limb(qx, qy):
        return body(8 + qx * ca - qy * sa, -124 + qx * sa + qy * ca)

    def rect(f, rx, ry, w, h):
        return [f(rx, ry), f(rx + w, ry), f(rx + w, ry + h), f(rx, ry + h)]

    def ellipse(f, cx, cy, rx, ry, n=22):
        return [f(cx + rx * math.cos(i / n * math.tau), cy + ry * math.sin(i / n * math.tau)) for i in range(n)]

    def poly(points, color):
        pygame.draw.polygon(surf, color, points)

    shadow = pygame.Surface((int(100 * SC), int(20 * SC)), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (10, 4, 2, 115), shadow.get_rect())
    surf.blit(shadow, shadow.get_rect(center=(x, FEET + 4)))

    poly(rect(body, -13, -72, 12, 72), INK)
    poly(rect(body, 2, -72, 12, 72), INK)
    poly(rect(body, -15, -8, 18, 8), INK)
    poly(rect(body, 1, -8, 19, 8), INK)

    # the arm that hangs back
    def back(qx, qy):
        a = 0.12
        return body(-8 + qx * math.cos(a) - qy * math.sin(a), -124 + qx * math.sin(a) + qy * math.cos(a))
    poly(rect(back, -5, 0, 10, 56), INK)

    torso = [body(-17, -72), body(-19, -128)] + [body(*p) for p in _bezier((-19, -128), (0, -140), (19, -128))] + [body(19, -128), body(17, -72)]
    poly(torso, INK)
    poly(rect(body, -5, -141, 10, 9), INK)

    poly(rect(body, -17, -79, 34, 6), LEATHER)
    poly(rect(body, -3, -80, 7, 8), accent)
    poly(rect(body, 10, -76, 9, 22), LEATHER)

    poly(ellipse(body, 1, -150, 12.5, 12.5), INK)
    poly([body(-11, -138), body(13, -138), body(1, -122)], accent)
    if star:
        pts = []
        for i in range(10):
            r = 3 if i % 2 else 7
            a = -math.pi / 2 + i * math.pi / 5
            pts.append(body(8 + math.cos(a) * r, -108 + math.sin(a) * r))
        poly(pts, accent)

    poly(ellipse(body, 0, -159, 32, 6.5), INK)
    crown = [body(-15, -160), body(-14, -186)] + [body(*p) for p in _bezier((-14, -186), (0, -178), (14, -186))] + [body(15, -160)]
    poly(crown, INK)
    poly(rect(body, -15, -168, 30, 4), accent)

    # Gun arm, hand, and gun
    poly(rect(limb, -5, 0, 10, 60), INK)
    poly(ellipse(limb, 0, 60, 6.5, 6.5, 14), INK)
    if arm > 0.7:
        poly(rect(limb, -4, 56, 8, 28), LEATHER)
        poly(rect(limb, -5, 52, 10, 12), LEATHER)
        # Enhanced Muzzle Flash
        if flash > 0:
            mx, my = limb(0, 90)
            # Radiant expanding outer glow
            _glow(surf, (int(mx), int(my)), int(52 * flash) + 6, (255, 195, 80))
            # Intense white-gold inner core glow
            _glow(surf, (int(mx), int(my)), int(22 * flash) + 4, (255, 250, 210))
            # Starburst spikes
            spikes = []
            reach = (38 + random.random() * 22) * flash
            for q in range(16):
                rd = 8 if q % 2 else reach + (18 if q % 4 == 0 else 0)
                a = q * math.pi / 8
                spikes.append(limb(math.cos(a) * rd, 90 + math.sin(a) * rd))
            poly(spikes, (255, 245, 190))
            # Solid white core right at the gun muzzle tip
            poly(ellipse(limb, 0, 90, 4.5 * flash + 1, 4.5 * flash + 1, 10), (255, 255, 255))


if __name__ == "__main__":
    import asyncio
    from main import main
    asyncio.run(main())
