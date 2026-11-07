"""A one-level, standard-library raycasting shooter."""
import math
import time
import tkinter as tk

LEVEL = (
    "1111111111111111",
    "1.....2........1",
    "1.P...2...M....1",
    "1.....2........1",
    "1........222...1",
    "122.222........1",
    "1.....2....M...1",
    "1..M..2........1",
    "1.....222.222..1",
    "1..............1",
    "1.....M.....M..1",
    "1111111111111111",
)
WIDTH, HEIGHT = 800, 480
STRIP = 5
FOV = math.radians(66)
FOCAL = WIDTH / (2 * math.tan(FOV / 2))
WALLS = {"1": (153, 91, 68), "2": (85, 119, 132)}


def tile(x, y):
    return LEVEL[math.floor(y)][math.floor(x)]


def ray(x, y, dx, dy):
    """Find the first wall by stepping from grid boundary to grid boundary."""
    cell_x, cell_y = math.floor(x), math.floor(y)
    step_x, step_y = (1 if dx > 0 else -1), (1 if dy > 0 else -1)
    delta_x = abs(1 / dx) if dx else math.inf
    delta_y = abs(1 / dy) if dy else math.inf
    edge_x = abs(cell_x + (step_x > 0) - x) * delta_x if dx else math.inf
    edge_y = abs(cell_y + (step_y > 0) - y) * delta_y if dy else math.inf
    while True:
        side = edge_y < edge_x
        if side:
            cell_y += step_y
            distance = edge_y
            edge_y += delta_y
        else:
            cell_x += step_x
            distance = edge_x
            edge_x += delta_x
        wall = LEVEL[cell_y][cell_x]
        if wall in WALLS:
            return distance, wall, side


class Monster:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.hp = 2
        self.attack_delay = 0.0


class Game:
    def __init__(self, root):
        self.root = root
        root.title("Bunker 01")
        root.resizable(False, False)
        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, highlightthickness=0)
        self.canvas.pack()
        self.keys = set()
        root.bind("<KeyPress>", self.key_down)
        root.bind("<KeyRelease>", lambda event: self.keys.discard(event.keysym.lower()))
        root.bind("<FocusOut>", lambda event: self.keys.clear())
        self.canvas.bind("<Button-1>", lambda event: self.shoot())
        self.reset()
        self.last_frame = time.monotonic()
        self.tick()

    def reset(self):
        self.monsters = []
        for y, row in enumerate(LEVEL):
            for x, marker in enumerate(row):
                if marker == "P":
                    self.x, self.y = x + 0.5, y + 0.5
                elif marker == "M":
                    self.monsters.append(Monster(x + 0.5, y + 0.5))
        self.angle = 0.0
        self.health = 100
        self.cooldown = 0.0
        self.hurt = 0.0
        self.keys.clear()

    def key_down(self, event):
        key = event.keysym.lower()
        if key == "escape":
            self.root.destroy()
        elif key == "r" and key not in self.keys:
            self.reset()
        self.keys.add(key)

    def move(self, actor, dx, dy, radius):
        def free(x, y):
            return all(tile(x + ox, y + oy) not in WALLS
                       for ox in (-radius, radius) for oy in (-radius, radius))

        if free(actor.x + dx, actor.y):
            actor.x += dx
        if free(actor.x, actor.y + dy):
            actor.y += dy

    def shoot(self):
        if self.cooldown > 0 or self.health <= 0 or not self.monsters:
            return
        self.cooldown = 0.28
        dx, dy = math.cos(self.angle), math.sin(self.angle)
        wall_depth = ray(self.x, self.y, dx, dy)[0]
        targets = []
        for monster in self.monsters:
            mx, my = monster.x - self.x, monster.y - self.y
            depth = mx * dx + my * dy
            offset = my * dx - mx * dy
            if 0 < depth < wall_depth and abs(offset) < 0.28:
                targets.append((depth, monster))
        if targets:
            target = min(targets, key=lambda item: item[0])[1]
            target.hp -= 1
            if target.hp == 0:
                self.monsters.remove(target)

    def update(self, dt):
        if self.health <= 0 or not self.monsters:
            return
        self.cooldown = max(0.0, self.cooldown - dt)
        self.hurt = max(0.0, self.hurt - dt)
        self.angle += 2.3 * dt * (("right" in self.keys) - ("left" in self.keys))
        forward = bool(self.keys & {"w", "up"}) - bool(self.keys & {"s", "down"})
        strafe = ("d" in self.keys) - ("a" in self.keys)
        speed = 3.0 * dt / max(1, math.hypot(forward, strafe))
        dx, dy = math.cos(self.angle), math.sin(self.angle)
        self.move(self, speed * (forward * dx - strafe * dy),
                  speed * (forward * dy + strafe * dx), 0.19)
        if "space" in self.keys:
            self.shoot()

        for monster in self.monsters:
            mx, my = self.x - monster.x, self.y - monster.y
            distance = math.hypot(mx, my)
            monster.attack_delay -= dt
            if distance and ray(monster.x, monster.y, mx, my)[0] < 1:
                continue
            if distance < 0.57:
                if monster.attack_delay <= 0:
                    self.health = max(0, self.health - 12)
                    self.hurt = 0.18
                    monster.attack_delay = 0.8
            elif distance < 8:
                step = 1.1 * dt / distance
                self.move(monster, mx * step, my * step, 0.22)

    def render(self):
        c = self.canvas
        c.delete("all")
        horizon = HEIGHT / 2
        for y in range(0, HEIGHT, 16):
            shade = int(15 + 28 * abs(y - horizon) / horizon)
            c.create_rectangle(0, y, WIDTH, y + 16,
                               fill=f"#{shade:02x}{shade:02x}{shade + 6:02x}", width=0)
        dx, dy = math.cos(self.angle), math.sin(self.angle)
        depths = []
        for x in range(0, WIDTH, STRIP):
            offset = (x + STRIP / 2 - WIDTH / 2) / FOCAL
            distance, wall, side = ray(self.x, self.y, dx - dy * offset, dy + dx * offset)
            depths.append(distance)
            half = min(HEIGHT, FOCAL / (2 * max(distance, 0.01)))
            light = max(0.21, 1 / (1 + distance * 0.17)) * (0.73 if side else 1)
            color = "#%02x%02x%02x" % tuple(int(channel * light) for channel in WALLS[wall])
            c.create_rectangle(x, horizon - half, x + STRIP, horizon + half, fill=color, width=0)

        sprites = []
        for monster in self.monsters:
            mx, my = monster.x - self.x, monster.y - self.y
            depth = mx * dx + my * dy
            if depth > 0.1:
                center = WIDTH / 2 + (my * dx - mx * dy) * FOCAL / depth
                sprites.append((depth, center, monster.hp))
        for depth, center, hp in sorted(sprites, reverse=True):
            scale = FOCAL / depth
            # Draw each part in wall-tested strips so corners can hide a monster.
            parts = (
                (-0.18, 0.18, -0.36, -0.03, "#86944e"),
                (-0.28, 0.28, -0.04, 0.34, "#718439" if hp == 2 else "#a15043"),
                (-0.23, -0.07, 0.32, 0.5, "#454e30"),
                (0.07, 0.23, 0.32, 0.5, "#454e30"),
                (-0.13, -0.045, -0.24, -0.17, "#ff734b"),
                (0.045, 0.13, -0.24, -0.17, "#ff734b"),
            )
            for left, right, top, bottom, color in parts:
                start = max(0, center + left * scale)
                end = min(WIDTH, center + right * scale)
                for column in range(int(start // STRIP), math.ceil(end / STRIP)):
                    if depth < depths[column]:
                        c.create_rectangle(max(start, column * STRIP), horizon + top * scale,
                                           min(end, (column + 1) * STRIP), horizon + bottom * scale,
                                           fill=color, width=0)

        mid = WIDTH / 2
        kick = 10 if self.cooldown > 0.19 else 0
        c.create_polygon(mid - 62, HEIGHT, mid - 38, HEIGHT - 70 + kick,
                         mid - 19, HEIGHT - 100 + kick, mid + 19, HEIGHT - 100 + kick,
                         mid + 38, HEIGHT - 70 + kick, mid + 62, HEIGHT,
                         fill="#444c57", outline="#15171c", width=4)
        c.create_rectangle(mid - 13, HEIGHT - 94 + kick, mid + 13, HEIGHT - 76 + kick,
                           fill="#161920", width=0)
        if kick:
            c.create_polygon(mid, HEIGHT - 153, mid + 11, HEIGHT - 119,
                             mid + 31, HEIGHT - 122, mid + 12, HEIGHT - 89,
                             mid - 12, HEIGHT - 89, mid - 31, HEIGHT - 122,
                             mid - 11, HEIGHT - 119, fill="#ffc75d")
        c.create_line(mid - 6, horizon, mid + 6, horizon, fill="white")
        c.create_line(mid, horizon - 6, mid, horizon + 6, fill="white")
        if self.hurt:
            c.create_rectangle(4, 4, WIDTH - 4, HEIGHT - 4, outline="#c34838", width=8)
        c.create_text(18, 20, anchor="w", fill="white", font=("TkFixedFont", 15, "bold"),
                      text=f"Здоровье {self.health:3}    Монстры {len(self.monsters)}")
        c.create_text(18, HEIGHT - 19, anchor="w", fill="#ddd", font=("TkDefaultFont", 11),
                      text="WASD · ← → · Пробел / клик · R")
        if not self.monsters or self.health <= 0:
            c.create_rectangle(200, 170, 600, 300, fill="#171a20", outline="#af895c", width=2)
            c.create_text(mid, 216, fill="white", font=("TkDefaultFont", 24, "bold"),
                          text="Уровень пройден!" if not self.monsters else "Вы погибли")
            c.create_text(mid, 264, fill="#ddd", text="R — заново     Esc — выход")

    def tick(self):
        now = time.monotonic()
        self.update(min(now - self.last_frame, 0.05))
        self.last_frame = now
        self.render()
        self.root.after(16, self.tick)


if __name__ == "__main__":
    root = tk.Tk()
    Game(root)
    root.mainloop()
