import pygame, sys, random, math, os

# ================= Basic Settings =================
WIDTH, HEIGHT = 800, 600
GROUND_Y = 570
FPS = 60

RABBIT_W, RABBIT_H = 56, 46      # 1080p下略大
BASE_SPEED = 8.0
GRAVITY = 1.02

# Jump tuning（整体更低 + 小跳更明显）
JUMP_V0 = -13.2
MAX_JUMP_HOLD_MS = 200
HOLD_GRAVITY_SCALE = 0.42
JUMP_CUT_FACTOR = 0.5            # 松手截断，使小跳更明显
MAX_JUMPS = 2
CEILING_Y = 90                   # 限高，防止飞出屏幕

# Score -> speed（3000后极缓慢提速）
RAMP_START_SCORE = 3000
RAMP_SLOPE = 0.00055

# Wings（≈每500分一枚；更大）
WING_SCORE_BUDGET = 600.0        # 以得分增速折算的“飞行时间”
WING_GRAVITY = 0.30
WING_ASCEND_VEL = -0.85
WING_JITTER_MS = (800, 2000)     # 达阈值后少许延迟掉落
WING_PICKUP_SIZE = (48, 36)      # 更大

# Super（50胡萝卜 → 8s无敌，变大一点）
SUPER_DURATION_MS = 8000
SUPER_SCALE = 1.18

# 复活
REVIVE_COUNTDOWN_MS = 3000
POST_REVIVE_IFRAME_MS = 1200

# Carrots（更贴地）
CARROT_LOW_CHOICES = [GROUND_Y-84, GROUND_Y-68, GROUND_Y-52]
CARROT_ROW_MIN, CARROT_ROW_MAX = 3, 6

# 障碍更稀疏（1080p更宽）
OBST_MIN_GAP = 1600
OBST_MAX_GAP = 2400
OBST_GAP_SCORE_FACTOR = 0.35

# Rock（更高，大小不一）
ROCK_W_MIN, ROCK_W_MAX = 44, 90
ROCK_H_MIN, ROCK_H_MAX = 48, 110

# Fox（更精致）
FOX_W, FOX_H = 78, 56

# 场景
SCENE_GRASS, SCENE_HELL, SCENE_HEAVEN = "grass", "hell", "heaven"

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("HAPPY RABBIT")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 32)
big_font = pygame.font.SysFont(None, 84)

# ================= Utils =================
def lerp(a, b, t):
    return a + (b - a) * t

def load_best(path="best_score.txt"):
    try:
        if os.path.exists(path):
            with open(path, "r") as f:
                return int(f.read().strip() or "0")
    except:
        pass
    return 0

def save_best(score, path="best_score.txt"):
    try:
        with open(path, "w") as f:
            f.write(str(int(score)))
    except:
        pass

# 把“基于得分的翅膀剩余量”换算成秒（每秒≈+35分，因为 score_gain = dt*0.035）
def wings_seconds_left(score_budget):
    return max(0, int(score_budget / 35.0 + 0.5))

# ================= Background（多场景） =================
class Background:
    def __init__(self):
        self.t = 0.0
        self.hills_off = 0
        self.reset_clouds_flowers_birds()

    def reset_clouds_flowers_birds(self):
        self.clouds = [[random.randint(0, WIDTH), random.randint(60, 220), random.randint(120, 280)] for _ in range(10)]
        self.flowers = [[random.randint(0, WIDTH), random.randint(GROUND_Y+10, HEIGHT-12),
                         random.choice([(245,215,0),(255,160,160),(200,255,200),(200,220,255)])] for _ in range(90)]
        self.birds = [[random.randint(0, WIDTH), random.randint(90, 200), random.choice([1, -1])] for _ in range(5)]

    def update(self, world_speed, dt):
        self.t += dt
        self.hills_off = (self.hills_off + world_speed * 0.25) % (WIDTH+200)
        for c in self.clouds:
            c[0] -= world_speed * 0.35
            if c[0] + c[2] < -20:
                c[0] = WIDTH + random.randint(30, 200)
                c[1] = random.randint(60, 220)
                c[2] = random.randint(120, 280)
        for f in self.flowers:
            f[0] -= world_speed * 0.5
            if f[0] < -6:
                f[0] = WIDTH + random.randint(0, 120)
                f[1] = random.randint(GROUND_Y+10, HEIGHT-12)
        for b in self.birds:
            b[0] += b[2] * 0.8
            if b[0] < -20:
                b[0] = WIDTH + 10; b[1] = random.randint(90, 200); b[2] = -1
            if b[0] > WIDTH+20:
                b[0] = -10; b[1] = random.randint(90, 200); b[2] = 1

    def draw(self, surf, scene):
        if scene == SCENE_GRASS:
            top, bottom = (160,210,255), (225,248,255)
            grass1, grass2 = (120,190,90), (95,170,75)
            hill1, hill2 = (120,160,120), (110,150,115)
            sun = (255,235,150)
        elif scene == SCENE_HELL:
            top, bottom = (60, 10, 10), (120, 20, 20)
            grass1, grass2 = (90, 35, 35), (75, 25, 25)
            hill1, hill2 = (90, 30, 30), (110, 40, 40)
            sun = (255, 90, 60)
        else:  # HEAVEN
            top, bottom = (220,235,255), (255,255,255)
            grass1, grass2 = (185, 225, 185), (165, 210, 170)
            hill1, hill2 = (170, 210, 230), (155, 200, 220)
            sun = (255, 255, 255)

        # sky gradient + sun
        for i in range(HEIGHT):
            t = i/HEIGHT
            col = (int(lerp(top[0], bottom[0], t)),
                   int(lerp(top[1], bottom[1], t)),
                   int(lerp(top[2], bottom[2], t)))
            pygame.draw.line(surf, col, (0,i), (WIDTH,i))
        pygame.draw.circle(surf, sun, (120, 120), 50)

        # hills
        off = int(self.hills_off)
        pts = [(0-off,GROUND_Y-110),(240-off,GROUND_Y-220),(480-off,GROUND_Y-110),
               (720-off,GROUND_Y-240),(1000-off,GROUND_Y-110),(1280-off,GROUND_Y-220),(1580-off,GROUND_Y-110)]
        pygame.draw.polygon(surf, hill1, pts+[(WIDTH,GROUND_Y),(0,GROUND_Y)])
        pts2 = [(x+100, y+36) for (x,y) in pts]
        pygame.draw.polygon(surf, hill2, pts2+[(WIDTH,GROUND_Y),(0,GROUND_Y)])

        # clouds
        for x,y,w in self.clouds:
            ccol = (255,255,255) if scene!=SCENE_HELL else (220,180,180)
            pygame.draw.ellipse(surf, ccol, (x,y,w,int(w*0.5)))
            pygame.draw.ellipse(surf, ccol, (x+int(w*0.3),y-12,int(w*0.8),int(w*0.45)))

        # ground
        pygame.draw.rect(surf, grass1, (0,GROUND_Y, WIDTH, HEIGHT-GROUND_Y))
        pygame.draw.rect(surf, grass2, (0,GROUND_Y+24, WIDTH, HEIGHT-(GROUND_Y+24)))
        pygame.draw.line(surf, (60,90,60) if scene!=SCENE_HELL else (120,30,30), (0,GROUND_Y), (WIDTH,GROUND_Y), 4)

        # flowers / embers / sparkles
        for x,y,c in self.flowers:
            if scene == SCENE_HELL:
                c = (255,120,80) if random.random()<0.5 else (255,180,120)
            elif scene == SCENE_HEAVEN:
                c = (255,255,255)
            pygame.draw.circle(surf, c, (x,y), 2)

        # far birds/souls
        for x,y,d in self.birds:
            col = (100,130,160) if scene!=SCENE_HELL else (200,90,90)
            pygame.draw.lines(surf, col, False, [(x, y), (x+10*d, y+5), (x+20*d, y)], 2)

bg = Background()
# ================= Player (Rabbit) =================
class Rabbit:
    def __init__(self, x, ground_y):
        self.base_w, self.base_h = RABBIT_W, RABBIT_H
        self.scale = 1.0
        self.x, self.ground_y = x, ground_y
        self.w, self.h = RABBIT_W, RABBIT_H
        self.y = ground_y - self.h
        self.vy = 0.0
        self.on_ground = True
        # jumping
        self.jump_holding = False
        self.jump_hold_time = 0
        self.jump_count = 0
        self.jump_cut_applied = False
        # wings
        self.has_wings = False
        self.wing_score_left = 0.0
        # super
        self.super_active = False
        self.super_timer = 0
        # visuals
        self.ear_phase = random.random()*math.tau
        # i-frames
        self.iframe_ms = 0

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), int(self.w), int(self.h))

    def start_jump(self):
        if not self.has_wings and self.jump_count < MAX_JUMPS:
            self.vy = JUMP_V0
            self.on_ground = False
            self.jump_holding = True
            self.jump_hold_time = 0
            self.jump_cut_applied = False
            self.jump_count += 1

    def set_jump_hold(self, is_down):
        self.jump_holding = is_down and (self.vy < 0) and (self.jump_hold_time < MAX_JUMP_HOLD_MS)

    def release_jump(self):
        if not self.has_wings and (self.vy < 0) and not self.jump_cut_applied:
            self.vy *= JUMP_CUT_FACTOR
            self.jump_cut_applied = True
        self.jump_holding = False

    def give_wings(self):
        self.has_wings = True
        self.wing_score_left = WING_SCORE_BUDGET

    def start_super(self):
        self.super_active = True
        self.super_timer = SUPER_DURATION_MS
        self.scale = SUPER_SCALE
        self.w = int(self.base_w * self.scale)
        self.h = int(self.base_h * self.scale)
        self.y = min(self.y, self.ground_y - self.h)

    def end_super(self):
        self.super_active = False
        self.scale = 1.0
        self.w = self.base_w
        self.h = self.base_h
        self.y = min(self.y, self.ground_y - self.h)

    def update_physics(self, dt, score_gain, space_held):
        if self.iframe_ms > 0:
            self.iframe_ms -= dt

        if self.super_active:
            self.super_timer -= dt
            if self.super_timer <= 0:
                self.end_super()

        if self.has_wings:
            self.wing_score_left -= score_gain
            if self.wing_score_left <= 0:
                self.has_wings = False
            if space_held:
                self.vy += WING_ASCEND_VEL
            self.vy += WING_GRAVITY
        else:
            if self.jump_holding and (self.vy < 0) and (self.jump_hold_time < MAX_JUMP_HOLD_MS):
                self.vy += GRAVITY*HOLD_GRAVITY_SCALE
                self.jump_hold_time += dt
            else:
                self.jump_holding = False
                self.vy += GRAVITY

        self.y += self.vy

        # ceiling clamp
        if self.y < CEILING_Y:
            self.y = CEILING_Y
            if self.vy < 0:
                self.vy = 0

        # floor
        if self.y + self.h >= self.ground_y:
            self.y = self.ground_y - self.h
            self.vy = 0
            self.on_ground = True
            self.jump_count = 0
            self.jump_cut_applied = False
        else:
            self.on_ground = False

    def draw(self, surf, t_ms, scene):
        r = self.rect
        flicker = (self.iframe_ms > 0) and (int(t_ms / 80) % 2 == 0)
        shadow = pygame.Rect(r.centerx-26, self.ground_y-8, 52, 8)
        pygame.draw.ellipse(surf, (65,85,65) if scene!=SCENE_HELL else (110,50,50), shadow)
        body_col = (220, 245, 255) if self.super_active else (240,240,245)
        outline_col = (120,170,220) if self.super_active else (160,160,170)

        if not flicker:
            pygame.draw.ellipse(surf, body_col, r)
            pygame.draw.ellipse(surf, outline_col, r, 2)
            head = pygame.Rect(r.x+10, r.y-14, 30, 30)
            pygame.draw.ellipse(surf, body_col, head); pygame.draw.ellipse(surf, outline_col, head, 2)
            wob = int(4*math.sin(t_ms*0.012 + self.ear_phase))
            ear1 = pygame.Rect(head.centerx-16, head.y-22+wob, 12, 26)
            ear2 = pygame.Rect(head.centerx+6, head.y-18-wob, 12, 24)
            pygame.draw.ellipse(surf, body_col, ear1); pygame.draw.ellipse(surf, body_col, ear2)
            pygame.draw.ellipse(surf, (255,190,210), ear1.inflate(-6,-8)); pygame.draw.ellipse(surf, (255,190,210), ear2.inflate(-6,-8))
            pygame.draw.ellipse(surf, outline_col, ear1, 1); pygame.draw.ellipse(surf, outline_col, ear2, 1)
            pygame.draw.circle(surf, (20,20,20), (head.centerx+8, head.centery), 3)
            pygame.draw.circle(surf, (255,120,130), (head.centerx+12, head.centery+6), 3)
            pygame.draw.circle(surf, outline_col, (r.right-8, r.centery+10), 7, 1)

        if self.has_wings and not flicker:
            wing = [(r.x-14, r.y+8), (r.x-34, r.y+4), (r.x-22, r.y+20)]
            pygame.draw.polygon(surf, (220,240,255), wing); pygame.draw.polygon(surf, (140,170,200), wing, 1)

# ================= 障碍 & 收集 & 传送门 =================
class Obstacle:
    # kind: "rock" or "fox"
    def __init__(self, kind, x, y, w, h):
        self.kind = kind
        self.rect = pygame.Rect(x, y, w, h)
        self.phase = random.random()*math.tau
    def update(self, speed, t_ms):
        self.rect.x -= int(round(speed))
        if self.kind == "fox":
            self.rect.y = (GROUND_Y - self.rect.h) + int(3 * math.sin(t_ms*0.02 + self.phase))
    def draw(self, surf, scene):
        if self.kind == "rock":
            r = self.rect
            peak_dx = random.choice([-4, -2, 0, 2, 4])
            poly = [(r.x, r.bottom-4),(r.x+10, r.y+10),(r.centerx+peak_dx, r.y),
                    (r.right-12, r.y+14),(r.right, r.bottom-4)]
            base_col = (120,120,120) if scene!=SCENE_HELL else (150,90,90)
            edge_col = (80,80,80) if scene!=SCENE_HELL else (120,60,60)
            pygame.draw.polygon(surf, base_col, poly)
            pygame.draw.polygon(surf, edge_col, poly, 2)
            pygame.draw.ellipse(surf, (60,80,60) if scene!=SCENE_HELL else (120,50,50), (r.centerx-22, r.bottom-4, 44, 8))
        else:
            r = self.rect
            body_col = (230,120,60) if scene!=SCENE_HELL else (210,80,50)
            line_col = (200,90,45) if scene!=SCENE_HELL else (180,60,40)
            pygame.draw.ellipse(surf, body_col, (r.x, r.y+8, r.w, r.h-8))
            pygame.draw.ellipse(surf, line_col, (r.x, r.y+8, r.w, r.h-8), 2)
            head = pygame.Rect(r.x-14, r.y-6, 28, 24)
            pygame.draw.ellipse(surf, body_col, head); pygame.draw.ellipse(surf, line_col, head, 2)
            ear1 = pygame.Rect(head.x+2, head.y-10, 10, 14); ear2 = pygame.Rect(head.x+12, head.y-8, 10, 12)
            pygame.draw.ellipse(surf, body_col, ear1); pygame.draw.ellipse(surf, body_col, ear2)
            pygame.draw.ellipse(surf, line_col, ear1, 1); pygame.draw.ellipse(surf, line_col, ear2, 1)
            pygame.draw.circle(surf, (30,15,10), (head.centerx+4, head.centery), 2)
            pygame.draw.polygon(surf, (255,210,140), [(r.right-8, r.centery+6), (r.right+14, r.centery+2), (r.right-2, r.centery+14)])
            pygame.draw.ellipse(surf, (60,80,60) if scene!=SCENE_HELL else (120,50,50), (r.centerx-22, r.bottom-4, 44, 8))

class Carrot:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 22, 32); self.t = 0.0
    def update(self, speed, dt):
        self.rect.x -= int(round(speed)); self.t += dt
    def draw(self, surf, scene):
        r = self.rect
        body = [(r.centerx, r.y), (r.x, r.bottom), (r.right, r.bottom)]
        pygame.draw.polygon(surf, (255,150,50) if scene!=SCENE_HELL else (255,120,80), body)
        pygame.draw.polygon(surf, (180,90,30), body, 1)
        pygame.draw.ellipse(surf, (70,170,80) if scene!=SCENE_HELL else (180,90,90), (r.centerx-12, r.y-12, 10, 14))
        pygame.draw.ellipse(surf, (70,170,80) if scene!=SCENE_HELL else (180,90,90), (r.centerx+2, r.y-14, 12, 16))

class WingsPickup:
    def __init__(self, x, y):
        w,h = WING_PICKUP_SIZE
        self.rect = pygame.Rect(x, y, w, h); self.phase = random.random()*math.tau
    def update(self, speed, t_ms):
        self.rect.x -= int(round(speed)); self.rect.y += int(1.4*math.sin(t_ms*0.01 + self.phase))
    def draw(self, surf, scene):
        r = self.rect
        left = [(r.centerx-10, r.centery), (r.x, r.y+6), (r.x+12, r.bottom-6)]
        right = [(r.centerx+10, r.centery), (r.right, r.y+6), (r.right-12, r.bottom-6)]
        fill = (220,240,255) if scene!=SCENE_HELL else (240,210,210)
        edge = (140,170,200) if scene!=SCENE_HELL else (170,120,120)
        pygame.draw.polygon(surf, fill, left);  pygame.draw.polygon(surf, fill, right)
        pygame.draw.polygon(surf, edge, left, 2); pygame.draw.polygon(surf, edge, right, 2)

class Portal:
    # kind: "hell" or "heaven"
    def __init__(self, kind, x, y):
        self.kind = kind
        self.rect = pygame.Rect(x, y, 70, 140)
        self.phase = random.random()*math.tau
    def update(self, speed, t_ms):
        self.rect.x -= int(round(speed))
    def draw(self, surf):
        r = self.rect
        if self.kind == "hell":
            core = (160, 0, 160)   # 紫色
            border = (0, 0, 0)
        else:
            core = (80, 140, 255)  # 蓝核
            border = (255, 255, 255)
        pygame.draw.ellipse(surf, core, r.inflate(-12, -12))
        pygame.draw.ellipse(surf, border, r, 6)

# ================= Game =================
class Game:
    def __init__(self):
        self.best = load_best()
        self.reset()

    def reset(self):
        self.scene = SCENE_GRASS
        self.player = Rabbit(180, GROUND_Y)
        self.obstacles = []
        self.carrots = []
        self.wings = []
        self.portals = []
        self.special_charges = 0  # 地狱=火球5发；天堂=魔法棒5次
        self.playing = True
        self.gameover = False
        self.revive_used = False
        self.reviving = False
        self.revive_timer = 0
        self.score = 0.0
        self.time_ms = 0
        # timers
        self.spawn_cd = 1200
        self.carrot_cd = 1200
        # wings by score threshold (~ every 500)
        self.next_wing_threshold = 500
        self.pending_wing_at = None
        # energy
        self.energy = 0  # 0..50
        self.coins = 0
        # portals trigger
        self.spawned_hell_portal = False
        self.spawned_heaven_portal = False

    # ---------- speed curve ----------
    def current_speed(self):
        if self.score < RAMP_START_SCORE:
            return BASE_SPEED
        extra = (self.score - RAMP_START_SCORE)
        return BASE_SPEED + extra * RAMP_SLOPE

    # ---------- helpers ----------
    def rightmost_obstacle_x(self):
        return max([o.rect.right for o in self.obstacles], default=0)

    def shift_x_to_avoid_overlap(self, rect, margin=120):
        for _ in range(8):
            overlap = False
            for o in self.obstacles:
                if rect.colliderect(o.rect):
                    rect.x = o.rect.right + margin
                    overlap = True
            if not overlap:
                break
        return rect.x

    def destroy_front_obstacle(self):
        # 消除前方最近的障碍
        ahead = [o for o in self.obstacles if o.rect.centerx > self.player.rect.centerx + 30]
        if not ahead:
            return False
        target = min(ahead, key=lambda o: o.rect.centerx)
        self.obstacles.remove(target)
        return True

    # ---------- spawners ----------
    def spawn_obstacle(self):
        kind = random.choices(["rock", "fox"], weights=[0.64, 0.36], k=1)[0]
        if kind == "rock":
            w = random.randint(ROCK_W_MIN, ROCK_W_MAX)
            h = random.randint(ROCK_H_MIN, ROCK_H_MAX)
            rect = pygame.Rect(WIDTH + 40, GROUND_Y - h, w, h)
        else:
            w = FOX_W;
            h = FOX_H
            rect = pygame.Rect(WIDTH + 40, GROUND_Y - h, w, h)
        self.obstacles.append(Obstacle(kind, rect.x, rect.y, rect.w, rect.h))

    def spawn_carrots(self):
        n = random.randint(CARROT_ROW_MIN, CARROT_ROW_MAX)
        y = random.choice(CARROT_LOW_CHOICES)
        start_x = WIDTH + 80
        rmo = self.rightmost_obstacle_x()
        if rmo > 0:
            start_x = max(start_x, rmo + 140)
        for i in range(n):
            c = Carrot(start_x + i * 34, y + random.randint(-8, 8))
            if any(c.rect.colliderect(o.rect) for o in self.obstacles):
                c.rect.x = self.shift_x_to_avoid_overlap(c.rect, margin=140)
            self.carrots.append(c)

    def schedule_wing_after_threshold(self):
        self.pending_wing_at = self.time_ms + random.randint(*WING_JITTER_MS)

    def actually_spawn_wing(self):
        y = random.choice([GROUND_Y - 180, GROUND_Y - 140, GROUND_Y - 110])
        x = WIDTH + 80
        rmo = self.rightmost_obstacle_x()
        if rmo > 0:
            x = max(x, rmo + 160)
        w = WingsPickup(x, y)
        if any(w.rect.colliderect(o.rect) for o in self.obstacles):
            w.rect.x = self.shift_x_to_avoid_overlap(w.rect, margin=160)
        self.wings.append(w)

    def spawn_portal(self, kind):
        x = WIDTH + 120
        y = GROUND_Y - 180
        p = Portal(kind, x, y)
        # 避开重叠
        if any(p.rect.colliderect(o.rect) for o in self.obstacles):
            p.rect.x = self.shift_x_to_avoid_overlap(p.rect, margin=200)
        self.portals.append(p)

    # ---------- update ----------
    def update(self, dt, keys_held):
        if not self.playing or self.gameover:
            return

        if self.reviving:
            self.revive_timer -= dt
            if self.revive_timer <= 0:
                self.reviving = False
                self.player.iframe_ms = POST_REVIVE_IFRAME_MS
            return

        self.time_ms += dt
        score_gain = dt * 0.035
        self.score += score_gain

        speed = self.current_speed()
        bg.update(speed, dt)

        # player physics
        space_held = keys_held.get("space", False)
        self.player.update_physics(dt, score_gain, space_held)

        # portals trigger
        if (self.score >= 3000) and (not self.spawned_hell_portal) and (self.scene == SCENE_GRASS):
            self.spawn_portal("hell");
            self.spawned_hell_portal = True
        if (self.score >= 6000) and (not self.spawned_heaven_portal) and (self.scene != SCENE_HEAVEN):
            self.spawn_portal("heaven");
            self.spawned_heaven_portal = True

        # schedule wings（地狱不刷翅膀）
        if self.scene in (SCENE_GRASS, SCENE_HEAVEN):
            if self.score >= self.next_wing_threshold:
                if self.pending_wing_at is None:
                    self.schedule_wing_after_threshold()
                while self.next_wing_threshold <= self.score:
                    self.next_wing_threshold += 500
            if (self.pending_wing_at is not None) and (self.time_ms >= self.pending_wing_at):
                self.actually_spawn_wing()
                self.pending_wing_at = None

        # spawn obstacles
        self.spawn_cd -= dt
        if self.spawn_cd <= 0:
            self.spawn_obstacle()
            gap = random.randint(OBST_MIN_GAP, OBST_MAX_GAP) - int(self.score * OBST_GAP_SCORE_FACTOR)
            self.spawn_cd = max(1000, gap)

        # spawn carrots
        self.carrot_cd -= dt
        if self.carrot_cd <= 0:
            self.spawn_carrots()
            self.carrot_cd = random.randint(1100, 1900)

        # move & clean
        for o in self.obstacles:
            o.update(speed, self.time_ms)
        self.obstacles = [o for o in self.obstacles if o.rect.right > -80]

        for c in self.carrots:
            c.update(speed, dt)
        self.carrots = [c for c in self.carrots if c.rect.right > -40]

        for w in self.wings:
            w.update(speed, self.time_ms)
        self.wings = [w for w in self.wings if w.rect.right > -40]

        for p in self.portals:
            p.update(speed, self.time_ms)
        self.portals = [p for p in self.portals if p.rect.right > -40]

        # --------- 碰撞/拾取 ----------
        prect = self.player.rect

        # 传送门
        for p in self.portals[:]:
            if prect.colliderect(p.rect):
                self.portals.remove(p)
                if p.kind == "hell":
                    self.scene = SCENE_HELL
                    self.special_charges = 5  # 火球5发
                else:
                    self.scene = SCENE_HEAVEN
                    self.special_charges = 5  # 魔法棒5次
                break

        # 碰障碍（飞行≠无敌；只有SUPER无敌）
        hit_obstacle = any(prect.colliderect(o.rect) for o in self.obstacles)
        if hit_obstacle and (not self.player.super_active) and (self.player.iframe_ms <= 0):
            if not self.revive_used:
                self.revive_used = True
                self.reviving = True
                self.revive_timer = REVIVE_COUNTDOWN_MS
            else:
                self.gameover = True
                self.best = max(self.best, int(self.score))
                save_best(self.best)

        # 胡萝卜→能量
        for c in self.carrots[:]:
            if prect.colliderect(c.rect):
                self.carrots.remove(c)
                self.coins += 1
                self.score += 10
                if not self.player.super_active:
                    self.energy = min(50, self.energy + 1)
                    if self.energy >= 50:
                        self.energy = 0
                        self.player.start_super()

        # 翅膀
        for w in self.wings[:]:
            if prect.colliderect(w.rect):
                self.wings.remove(w)
                self.player.give_wings()

# ---------- draw ----------
    def draw_energy_bar(self, surf):
        # 右上角能量条：0..50
        bar_w, bar_h = 220, 20
        x, y = WIDTH - bar_w - 18, 14
        pygame.draw.rect(surf, (235, 235, 235), (x, y, bar_w, bar_h), border_radius=8)
        pygame.draw.rect(surf, (120, 120, 120), (x, y, bar_w, bar_h), 2, border_radius=8)
        fill = int(bar_w * (self.energy / 50.0))
        if fill > 0:
            pygame.draw.rect(surf, (255, 170, 70), (x, y, fill, bar_h), border_radius=8)
        lbl = font.render("Energy (50 carrots → SUPER)", True, (10, 25, 10))
        surf.blit(lbl, (x, y + bar_h + 6))

    def draw_timers_bottom_left(self, surf):
        # 左下角：Wings剩余秒、Super剩余秒、特殊道具次数
        lines = []
        if self.player.has_wings:
            sec = wings_seconds_left(self.player.wing_score_left)
            lines.append(f"Wings: {sec}s")
        if self.player.super_active:
            sec2 = max(0, int(self.player.super_timer / 1000 + 0.5))
            lines.append(f"SUPER: {sec2}s")
        if self.scene == SCENE_HELL and self.special_charges > 0:
            lines.append(f"Fireballs: {self.special_charges}")
        if self.scene == SCENE_HEAVEN and self.special_charges > 0:
            lines.append(f"Wand: {self.special_charges}")
        if lines:
            x, y = 16, HEIGHT - 20 - len(lines) * 26
            for i, text in enumerate(lines):
                label = font.render(text, True, (0, 0, 0))
                surf.blit(label, (x, y + i * 26))

    def draw(self, surf):
        bg.draw(surf, self.scene)
        for c in self.carrots: c.draw(surf, self.scene)
        for o in self.obstacles: o.draw(surf, self.scene)
        for w in self.wings: w.draw(surf, self.scene)
        for p in self.portals: p.draw(surf)
        self.player.draw(surf, self.time_ms, self.scene)

        # HUD
        best_val = getattr(self, 'best', 0)
        hud = font.render(
            f"Score: {int(self.score)}   Carrots: {self.coins}   Best: {best_val}"
            + ("" if not self.player.has_wings else "   Wings: ON")
            + ("" if not self.player.super_active else "   SUPER!"),
            True, (10, 25, 10) if self.scene != SCENE_HELL else (235, 220, 220)
        )
        surf.blit(hud, (12, 14))
        self.draw_energy_bar(surf)
        self.draw_timers_bottom_left(surf)

        if self.reviving:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, 230) if self.scene != SCENE_HELL else (0, 0, 0, 200))
            surf.blit(overlay, (0, 0))
            sec = max(1, math.ceil(self.revive_timer / 1000))
            txt = big_font.render(f"{sec}", True, (220, 0, 0))
            surf.blit(txt, txt.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

        if self.gameover:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, 210))
            surf.blit(overlay, (0, 0))
            title = big_font.render("GAME OVER", True, (220, 0, 0))
            surf.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 40)))
            msg = font.render("Press SPACE to restart  |  ESC to quit", True, (0, 0, 0))
            surf.blit(msg, msg.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 20)))

# ================= Main Loop =================
def _run():
    game = Game()
    keys_held = {"space": False}

    clock_tick = clock.tick
    while True:
        dt = clock_tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit();
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit();
                    sys.exit()
                if not game.gameover and not game.reviving:
                    if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                        game.player.start_jump()
                        keys_held["space"] = True
                        game.player.set_jump_hold(True)
                elif game.gameover:
                    if event.key in (pygame.K_SPACE, pygame.K_r):
                        game.reset()
                        keys_held["space"] = False

            if event.type == pygame.KEYUP:
                if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                    keys_held["space"] = False
                    game.player.release_jump()
                    game.player.set_jump_hold(False)

            # 左键使用特殊道具
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if (not game.gameover) and (not game.reviving) and game.special_charges > 0:
                    if game.destroy_front_obstacle():
                        game.special_charges -= 1

        game.update(dt, keys_held)
        game.draw(screen)
        pygame.display.flip()

if __name__ == "__main__":
    try:
        _run()
    except Exception as e:
        import traceback
        traceback.print_exc()
        input("\nProgram crashed. Press Enter to close...")