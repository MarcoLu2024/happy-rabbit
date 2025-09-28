import pygame, random, sys, math

# ========== 基本参数 ==========
WIDTH, HEIGHT = 900, 480
GROUND_Y = 380
FPS = 60

PLAYER_W, PLAYER_H = 44, 56
PLAYER_SLIDE_H = 32
JUMP_V0 = -15.5
GRAVITY = 0.85

COLOR_BG_DAY = (230, 240, 255)
COLOR_BG_NIGHT = (18, 22, 40)

# ========== 初始化 ==========
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("进阶跑酷 - Space/W/Up跳(可二段), S/Down滑铲, H切难度, P暂停")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 26)
big_font = pygame.font.SysFont(None, 60)


# ========== 工具函数 ==========
def lerp(a, b, t):
    return a + (b - a) * t


def draw_text_center(surf, text, font, color, center):
    img = font.render(text, True, color)
    surf.blit(img, img.get_rect(center=center))


# ========== 游戏对象 ==========
class Player:
    def __init__(self, x, ground_y):
        self.x = x
        self.ground_y = ground_y
        self.w = PLAYER_W
        self.h = PLAYER_H
        self.y = ground_y - self.h
        self.vy = 0.0
        self.on_ground = True
        self.jump_count = 0  # 支持二段跳：0/1/2
        self.slide = False
        self.slide_timer = 0.0
        self.invincible_timer = 0.0  # 受击后短暂无敌（闪烁）
        self.shield = False  # 护盾（吃到道具获得一次免死）

    @property
    def rect(self):
        h = PLAYER_SLIDE_H if self.slide else self.h
        y = self.y + (self.h - h)  # 滑铲时降低碰撞箱
        return pygame.Rect(int(self.x), int(y), self.w, h)

    def try_jump(self):
        # 地面或在空中但还未二段跳
        if self.on_ground or self.jump_count < 2:
            self.vy = JUMP_V0
            self.on_ground = False
            self.jump_count += 1

    def set_slide(self, down):
        self.slide = down
        if down:
            self.slide_timer = 0.0

    def update(self, dt, g=GRAVITY):
        # 重力
        self.vy += g
        self.y += self.vy
        # 落地
        if self.y + self.h >= self.ground_y:
            self.y = self.ground_y - self.h
            self.vy = 0
            self.on_ground = True
            self.jump_count = 0
        else:
            self.on_ground = False

        # 滑铲计时（持续按住则一直滑）
        if self.slide:
            self.slide_timer += dt

        # 无敌计时
        if self.invincible_timer > 0:
            self.invincible_timer -= dt

    def draw(self, surf, time_ms):
        # 无敌闪烁
        flicker = (self.invincible_timer > 0) and int(time_ms / 60) % 2 == 0
        color = (120, 170, 255) if not flicker else (255, 255, 255)

        # 护盾描边
        if self.shield:
            pygame.draw.rect(surf, (50, 220, 255), self.rect.inflate(8, 8), 2, border_radius=6)

        pygame.draw.rect(surf, color, self.rect, border_radius=6)


class Obstacle:
    # kind: "box" 地面箱子; "tall" 高墙; "bird" 飞行敌人(在空中)
    def __init__(self, kind, x, y, w, h, vx):
        self.kind = kind
        self.rect = pygame.Rect(x, y, w, h)
        self.vx = vx
        self.osc_phase = random.random() * math.tau  # 飞行/移动障碍用

    def update(self, speed, t):
        # 基础左移
        self.rect.x -= speed

        # 移动物体增加一点上下/左右振荡
        if self.kind == "bird":
            # 鸟上下轻微波动
            self.rect.y += int(2 * math.sin(t * 0.01 + self.osc_phase))
        elif self.kind == "tall":
            # 高墙轻微左右摆（增加判定难度）
            self.rect.x += int(1.5 * math.sin(t * 0.008 + self.osc_phase))

    def draw(self, surf):
        if self.kind == "bird":
            pygame.draw.rect(surf, (220, 80, 80), self.rect, border_radius=4)
            # 简单“翅膀”
            wing = pygame.Rect(self.rect.centerx - 10, self.rect.y - 6, 20, 6)
            pygame.draw.rect(surf, (220, 80, 80), wing, border_radius=3)
        elif self.kind == "tall":
            pygame.draw.rect(surf, (70, 200, 110), self.rect, border_radius=4)
        else:
            pygame.draw.rect(surf, (40, 160, 90), self.rect, border_radius=4)


class Coin:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 18, 18)
        self.t = 0.0

    def update(self, speed, dt):
        self.rect.x -= speed
        self.t += dt

    def draw(self, surf, t):
        # 轻微上下跳动与旋转感
        bob = int(3 * math.sin((self.t) * 0.02))
        r = self.rect.move(0, bob)
        pygame.draw.ellipse(surf, (255, 210, 40), r)
        pygame.draw.ellipse(surf, (255, 255, 255), r.inflate(-8, -8), 2)


class PowerUp:
    # 护盾道具
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 22, 22)
        self.t = 0.0

    def update(self, speed, dt):
        self.rect.x -= speed
        self.t += dt

    def draw(self, surf):
        glow = self.rect.inflate(8, 8)
        pygame.draw.ellipse(surf, (120, 240, 255), glow, 1)
        pygame.draw.ellipse(surf, (80, 220, 255), self.rect)
        pygame.draw.ellipse(surf, (255, 255, 255), self.rect.inflate(-10, -10), 2)


# 视差背景（云/远山）
class Parallax:
    def __init__(self):
        self.clouds = []
        for _ in range(8):
            x = random.randint(0, WIDTH)
            y = random.randint(40, 160)
            w = random.randint(60, 150)
            self.clouds.append([x, y, w])

    def update(self, base_speed):
        for c in self.clouds:
            c[0] -= base_speed * 0.3
            if c[0] + c[2] < 0:
                c[0] = WIDTH + random.randint(0, 200)
                c[1] = random.randint(40, 160)
                c[2] = random.randint(60, 150)

    def draw(self, surf, sky_color):
        # 天空
        surf.fill(sky_color)
        # 远山
        pygame.draw.polygon(surf, (120, 140, 180), [(0, GROUND_Y - 80), (120, GROUND_Y - 140), (240, GROUND_Y - 80)])
        pygame.draw.polygon(surf, (100, 130, 170), [(240, GROUND_Y - 80), (380, GROUND_Y - 160), (520, GROUND_Y - 80)])
        pygame.draw.polygon(surf, (110, 135, 175), [(520, GROUND_Y - 80), (680, GROUND_Y - 150), (860, GROUND_Y - 80)])
        # 云
        for x, y, w in self.clouds:
            pygame.draw.ellipse(surf, (255, 255, 255), (x, y, w, w * 0.55))
            pygame.draw.ellipse(surf, (255, 255, 255), (x + int(w * 0.3), y - 10, int(w * 0.8), int(w * 0.5)))


parallax = Parallax()


# ========== 游戏状态 ==========
class Game:
    def __init__(self):
        self.reset(hard=False)

    def reset(self, hard=False):
        self.player = Player(140, GROUND_Y)
        self.obstacles = []
        self.coins = []
        self.powerups = []
        self.score = 0.0
        self.coins_collected = 0
        self.time_ms = 0
        self.playing = False  # 先在开始界面
        self.gameover = False
        self.paused = False
        self.best = 0
        self.hard = hard

        # 速度&生成
        self.base_speed = 7.0 if not hard else 8.8
        self.spawn_cd = 0
        self.coin_cd = 0
        self.power_cd = 8000  # 8秒一个护盾（随机）
        self.day_cycle = 0.0  # 昼夜渐变

    def start(self):
        self.playing = True
        self.gameover = False
        self.paused = False

    def difficulty_scale(self):
        # 随时间/分数增长速度（困难模式更快）
        return (self.score / 700.0) + (0.3 if self.hard else 0.0)

    def current_speed(self):
        return self.base_speed + self.difficulty_scale() * 3.0

    def update_spawn(self, dt):
        self.spawn_cd -= dt
        if self.spawn_cd <= 0:
            # 障碍生成（越到后面越密集）
            min_gap = 500 if not self.hard else 420
            max_gap = 1100 if not self.hard else 950
            gap = random.randint(min_gap, max_gap) - int(self.difficulty_scale() * 120)
            self.spawn_cd = max(320, gap)

            # 随机类型
            speed = self.current_speed()
            choices = ["box", "tall", "bird"]
            # 初期少出bird，后期/困难更容易出
            weights = [0.5, 0.32, 0.18] if not self.hard else [0.42, 0.30, 0.28]
            kind = random.choices(choices, weights=weights, k=1)[0]

            if kind == "box":
                w = random.randint(26, 58)
                h = random.randint(28, 56)
                r = pygame.Rect(WIDTH + 20, GROUND_Y - h, w, h)
                self.obstacles.append(Obstacle("box", r.x, r.y, r.w, r.h, -speed))
            elif kind == "tall":
                w = random.randint(30, 42)
                h = random.randint(90, 140)
                r = pygame.Rect(WIDTH + 20, GROUND_Y - h, w, h)
                self.obstacles.append(Obstacle("tall", r.x, r.y, r.w, r.h, -speed))
            else:  # bird
                h = 26
                w = 40
                fly_y = random.choice([GROUND_Y - 150, GROUND_Y - 115, GROUND_Y - 80])
                r = pygame.Rect(WIDTH + 20, fly_y, w, h)
                self.obstacles.append(Obstacle("bird", r.x, r.y, r.w, r.h, -speed))

        # 金币生成：在障碍之间穿插
        self.coin_cd -= dt
        if self.coin_cd <= 0:
            n = random.randint(3, 6)
            base_y = random.choice([GROUND_Y - 120, GROUND_Y - 80, GROUND_Y - 40])
            for i in range(n):
                x = WIDTH + 60 + i * 26
                y = base_y + random.randint(-6, 6)
                self.coins.append(Coin(x, y))
            self.coin_cd = random.randint(1300, 2100)

        # 护盾
        self.power_cd -= dt
        if self.power_cd <= 0:
            y = random.choice([GROUND_Y - 130, GROUND_Y - 90])
            self.powerups.append(PowerUp(WIDTH + 40, y))
            self.power_cd = random.randint(7000, 11000)

    def update(self, dt):
        if not self.playing or self.gameover or self.paused:
            return

        self.time_ms += dt
        self.score += dt * 0.035 * (1.15 if self.hard else 1.0)  # 困难模式得分略快
        parallax.update(self.current_speed())

        # 昼夜颜色循环
        self.day_cycle += dt * 0.00005  # 慢慢变
        t = (math.sin(self.day_cycle * math.tau) + 1) / 2  # 0~1
        sky_color = (
            int(lerp(COLOR_BG_NIGHT[0], COLOR_BG_DAY[0], t)),
            int(lerp(COLOR_BG_NIGHT[1], COLOR_BG_DAY[1], t)),
            int(lerp(COLOR_BG_NIGHT[2], COLOR_BG_DAY[2], t)),
        )
        self.sky_color = sky_color

        # 玩家
        self.player.update(dt)

        # 生成物体
        self.update_spawn(dt)

        # 移动物体
        speed = self.current_speed()
        for ob in self.obstacles:
            ob.update(speed, self.time_ms)
        for c in self.coins:
            c.update(speed, dt)
        for p in self.powerups:
            p.update(speed, dt)

        # 清理离场
        self.obstacles = [o for o in self.obstacles if o.rect.right > -40]
        self.coins = [c for c in self.coins if c.rect.right > -20]
        self.powerups = [p for p in self.powerups if p.rect.right > -20]

        # 碰撞判定（考虑无敌 & 护盾）
        if self.player.invincible_timer <= 0:
            preg = self.player.rect
            hit = None
            for o in self.obstacles:
                if preg.colliderect(o.rect):
                    hit = o
                    break
            if hit:
                if self.player.shield:
                    # 护盾抵消一次伤害
                    self.player.shield = False
                    self.player.invincible_timer = 1200  # 1.2秒无敌
                else:
                    # 游戏结束
                    self.gameover = True
                    self.best = max(self.best, int(self.score))

        # 吃金币
        for c in self.coins[:]:
            if self.player.rect.colliderect(c.rect):
                self.coins.remove(c)
                self.coins_collected += 1
                self.score += 10  # 金币加分

        # 吃护盾
        for p in self.powerups[:]:
            if self.player.rect.colliderect(p.rect):
                self.powerups.remove(p)
                self.player.shield = True

    def draw(self, surf):
        # 背景 / 地面
        parallax.draw(surf, getattr(self, "sky_color", COLOR_BG_DAY))
        pygame.draw.line(surf, (60, 60, 70), (0, GROUND_Y), (WIDTH, GROUND_Y), 3)

        # 物体
        for c in self.coins:
            c.draw(surf, self.time_ms)
        for p in self.powerups:
            p.draw(surf)
        for o in self.obstacles:
            o.draw(surf)

        # 玩家
        self.player.draw(surf, self.time_ms)

        # UI
        score_s = font.render(
            f"Score: {int(self.score)}    Coins: {self.coins_collected}    Best: {self.best}    Mode: {'HARD' if self.hard else 'NORMAL'}",
            True, (0, 0, 0))
        surf.blit(score_s, (12, 10))

        # 护盾提示
        if self.player.shield:
            surf.blit(font.render("Shield ON", True, (0, 90, 140)), (12, 36))
        if self.paused:
            draw_text_center(surf, " PAUSED ", big_font, (10, 10, 10), (WIDTH // 2, HEIGHT // 2))

        if not self.playing and not self.gameover:
            draw_text_center(surf, "进阶跑酷", big_font, (0, 0, 0), (WIDTH // 2, HEIGHT // 2 - 80))
            info = [
                "空格/↑/W：跳（可二段）   ↓/S：滑铲   P：暂停",
                "H：切换普通/困难   回车：开始",
                "躲避地面箱子、高墙与空中鸟；收集金币，护盾可抵消一次伤害",
                f"当前模式：{'困难' if self.hard else '普通'}"
            ]
            for i, line in enumerate(info):
                draw_text_center(surf, line, font, (0, 0, 0), (WIDTH // 2, HEIGHT // 2 - 20 + i * 28))

        if self.gameover:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, 220))
            surf.blit(overlay, (0, 0))
            draw_text_center(surf, "游戏结束", big_font, (0, 0, 0), (WIDTH // 2, HEIGHT // 2 - 40))
            draw_text_center(surf, f"本局分数：{int(self.score)}   金币：{self.coins_collected}", font, (0, 0, 0),
                             (WIDTH // 2, HEIGHT // 2 + 6))
            draw_text_center(surf, "按 R 重开   ESC 退出", font, (0, 0, 0), (WIDTH // 2, HEIGHT // 2 + 40))


# ========== 主循环 ==========
game = Game()

while True:
    dt = clock.tick(FPS)  # 毫秒
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit();
            sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit();
                sys.exit()

            if not game.playing and not game.gameover:
                # 开始界面
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    game.start()
                elif event.key == pygame.K_h:
                    game.hard = not game.hard

            elif game.playing and not game.gameover:
                # 游戏中
                if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                    game.player.try_jump()
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    game.player.set_slide(True)
                if event.key == pygame.K_p:
                    game.paused = not game.paused

            elif game.gameover:
                if event.key == pygame.K_r:
                    game.reset(hard=game.hard)

        if event.type == pygame.KEYUP:
            if event.key in (pygame.K_DOWN, pygame.K_s):
                game.player.set_slide(False)

    game.update(dt)

    # 绘制
    game.draw(screen)
    pygame.display.flip()
