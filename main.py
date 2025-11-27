# Improved main.py rewritten with a robust maze generator, cleaner wall alignment,
# smooth player movement, and stable collision.
# NOTE: This is a full replacement for your previous main.py

import pygame
import random
import sys
import os
from collections import deque

# ---------------- CONFIG ----------------
WIDTH, HEIGHT = 900, 600
TILE = 40
FPS = 60
MAX_LEVEL = 5
ASSETS_DIR = "assets"
BG_IMG_PATH = None

WHITE = (255,255,255)
BLACK = (0,0,0)
FLOOR = (230,229,220)
WALL_TOP = (30,80,220)
WALL_SIDE = (20,50,150)
GREEN = (50,205,50)
RED = (220,20,60)
GOLD = (255,215,0)

pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Campus Maze — Improved")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 20)
big_font = pygame.font.SysFont("Arial", 48, bold=True)

# ---------------- HELPERS ----------------
def load_image(name, fallback_color=(120,120,120), size=(32,32)):
    path = os.path.join(ASSETS_DIR, name)
    try:
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.scale(img, size)
    except Exception:
        surf = pygame.Surface(size, pygame.SRCALPHA)
        surf.fill(fallback_color)
        return surf

def load_sound(name):
    path = os.path.join(ASSETS_DIR, name)
    try:
        return pygame.mixer.Sound(path)
    except:
        return None

# ---------------- NEW MAZE GENERATOR ----------------
# Full grid-perfect maze using DFS with clean alignment

def generate_maze(cols, rows):
    # force odd dims
    if cols % 2 == 0: cols += 1
    if rows % 2 == 0: rows += 1

    maze = [[1 for _ in range(cols)] for _ in range(rows)]

    def neighbors(cx, cy):
        dirs = [(0,2),(0,-2),(2,0),(-2,0)]
        random.shuffle(dirs)
        for dx, dy in dirs:
            nx, ny = cx+dx, cy+dy
            if 1 <= nx < cols-1 and 1 <= ny < rows-1:
                yield nx, ny, dx, dy

    stack = [(1,1)]
    maze[1][1] = 0

    while stack:
        x, y = stack[-1]
        carved = False

        for nx, ny, dx, dy in neighbors(x,y):
            if maze[ny][nx] == 1:
                maze[y + dy//2][x + dx//2] = 0
                maze[ny][nx] = 0
                stack.append((nx,ny))
                carved = True
                break

        if not carved:
            stack.pop()

    # ensure exit
    maze[rows-2][cols-2] = 0
    return maze

# ---------------- SPRITES ----------------
class Wall(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((TILE, TILE))
        self.image.fill(WALL_SIDE)
        pygame.draw.rect(self.image, WALL_TOP, (0,0,TILE,TILE-12))
        self.rect = self.image.get_rect(topleft=(x,y))

class Gate(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((TILE, TILE))
        self.image.fill(GOLD)
        pygame.draw.rect(self.image, (200,180,0), (4,4,TILE-8,TILE-8), 3)
        self.rect = self.image.get_rect(topleft=(x,y))

class Note(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        size = (TILE//2, TILE//2)
        self.image = load_image("note.png", (40,200,40), size)
        self.rect = self.image.get_rect(center=(x+TILE//2, y+TILE//2))

class Player(pygame.sprite.Sprite):
    def __init__(self, name, gender, x, y):
        super().__init__()
        size = (30,30)
        if gender.lower().startswith('m'):
            self.image = load_image('boy.png', (60,120,220), size)
        else:
            self.image = load_image('girl.png', (220,100,120), size)

        self.rect = self.image.get_rect(topleft=(x,y))
        self.base_speed = 3.5
        self.speed = self.base_speed
        self.name = name
        self.gender = gender
        self.lives = 3
        self.score = 0
        self.boost_timer = 0

    def move_axis(self, dx, dy, walls):
        self.rect.x += dx
        for w in walls:
            if self.rect.colliderect(w.rect):
                if dx > 0: self.rect.right = w.rect.left
                if dx < 0: self.rect.left = w.rect.right

        self.rect.y += dy
        for w in walls:
            if self.rect.colliderect(w.rect):
                if dy > 0: self.rect.bottom = w.rect.top
                if dy < 0: self.rect.top = w.rect.bottom

    def update(self, keys, walls):
        dx = dy = 0
        if keys[pygame.K_LEFT]: dx = -self.speed
        if keys[pygame.K_RIGHT]: dx = self.speed
        if keys[pygame.K_UP]: dy = -self.speed
        if keys[pygame.K_DOWN]: dy = self.speed
        self.move_axis(dx, dy, walls)

        if self.boost_timer > 0:
            self.boost_timer -= 1
            if self.boost_timer <= 0:
                self.speed = self.base_speed

    def boost(self, amount=2.0, duration=180):
        self.speed = min(self.base_speed + amount, 7.5)
        self.boost_timer = duration

class HOD(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = load_image('hod.png', (200,60,60), (34,34))
        self.rect = self.image.get_rect(topleft=(x,y))
        self.base_speed = 1.0
        self.speed = self.base_speed

    def update(self, target, walls, level):
        self.speed = self.base_speed + 0.12*(level-1)
        dx = 1 if self.rect.centerx < target.centerx else -1
        dy = 1 if self.rect.centery < target.centery else -1

        self.rect.x += dx*self.speed
        for w in walls:
            if self.rect.colliderect(w.rect): self.rect.x -= dx*self.speed

        self.rect.y += dy*self.speed
        for w in walls:
            if self.rect.colliderect(w.rect): self.rect.y -= dy*self.speed

# ---------------- GAME ----------------
class Game:
    def __init__(self):
        self.level = 1
        self.state = 'TITLE'
        self.player_name = 'Player'
        self.gender = 'Male'

        self.walls = pygame.sprite.Group()
        self.notes = pygame.sprite.Group()
        self.hod_group = pygame.sprite.Group()
        self.all_sprites = pygame.sprite.Group()

        self.snd_bell = load_sound('bell.wav')
        self.snd_caught = load_sound('caught.wav')
        self.snd_foot = load_sound('footstep.wav')

        self.bg = None

    def start_level(self, level):
        self.walls.empty(); self.notes.empty(); self.hod_group.empty(); self.all_sprites.empty()

        cols = WIDTH // TILE
        rows = HEIGHT // TILE
        grid = generate_maze(cols, rows)

        free_tiles = []
        for r in range(rows):
            for c in range(cols):
                x, y = c*TILE, r*TILE
                if grid[r][c] == 1:
                    w = Wall(x,y)
                    self.walls.add(w)
                    self.all_sprites.add(w)
                else:
                    free_tiles.append((x,y))

        start = free_tiles[0]
        end = free_tiles[-1]

        self.player = Player(self.player_name, self.gender, start[0]+4, start[1]+4)
        self.all_sprites.add(self.player)

        self.gate = Gate(end[0], end[1])
        self.all_sprites.add(self.gate)

        mid = free_tiles[len(free_tiles)//2]
        self.hod = HOD(mid[0], mid[1])
        self.hod_group.add(self.hod)
        self.all_sprites.add(self.hod)

        for _ in range(6 + level*2):
            px, py = random.choice(free_tiles)
            n = Note(px, py)
            self.notes.add(n)
            self.all_sprites.add(n)

        self.state = 'PLAY'

    def update(self, keys):
        if self.state == 'PLAY':
            self.player.update(keys, self.walls.sprites())
            self.hod.update(self.player.rect, self.walls.sprites(), self.level)

            for n in pygame.sprite.spritecollide(self.player, self.notes, True):
                self.player.score += 100
                self.player.boost()

            if pygame.sprite.collide_rect(self.player, self.hod):
                self.player.lives -= 1
                if self.player.lives <= 0:
                    self.state = 'GAMEOVER'
                else:
                    self.state = 'HIT'

            if pygame.sprite.collide_rect(self.player, self.gate):
                self.player.score += 500
                self.level += 1
                if self.level > MAX_LEVEL: self.level = MAX_LEVEL
                self.state = 'LEVELCLEAR'

    def draw(self):
        screen.fill(FLOOR)
        self.walls.draw(screen)
        self.notes.draw(screen)
        screen.blit(self.gate.image, self.gate.rect)
        screen.blit(self.player.image, self.player.rect)
        screen.blit(self.hod.image, self.hod.rect)

        tag = font.render(self.player.name, True, WHITE)
        screen.blit(tag, (self.player.rect.centerx-tag.get_width()//2, self.player.rect.top-18))

        hud = font.render(f"Score:{self.player.score}  Lvl:{self.level}  Lives:{self.player.lives}", True, WHITE)
        screen.blit(hud, (8,8))

    def title_screen(self):
        screen.fill(BLACK)
        screen.blit(big_font.render("SHRAVANI & MEDHA PROJECT RUNNER", True, WHITE), (160,120))
        screen.blit(font.render("Lets Go", True, WHITE), (360,260))
        screen.blit(font.render(f"Selected: {self.gender} (M/F)", True, WHITE), (340,300))
        screen.blit(font.render(f"Name: {self.player_name}", True, WHITE), (340,340))

    def gameover_screen(self):
        screen.fill(BLACK)
        screen.blit(big_font.render("Hey, You missed this time , lets try again ?", True, RED), (300,180))
        screen.blit(font.render("Press R to Restart", True, WHITE), (360,260))

# ---------------- MAIN ----------------
def main():
    game = Game()
    running = True
    input_name = ''

    while running:
        clock.tick(FPS)
        keys = pygame.key.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if game.state == 'TITLE':
                    if event.key == pygame.K_RETURN:
                        if input_name.strip(): game.player_name = input_name.strip()
                        game.start_level(1)
                    elif event.key == pygame.K_BACKSPACE:
                        input_name = input_name[:-1]
                    elif event.key == pygame.K_m:
                        game.gender = 'Male'
                    elif event.key == pygame.K_f:
                        game.gender = 'Female'
                    else:
                        if len(input_name) < 12 and event.unicode.isprintable():
                            input_name += event.unicode

                elif game.state == 'GAMEOVER':
                    if event.key == pygame.K_r:
                        game = Game()

                elif game.state == 'LEVELCLEAR':
                    if event.key == pygame.K_RETURN:
                        game.start_level(game.level)

                elif game.state == 'HIT':
                    if event.key == pygame.K_RETURN:
                        game.player.rect.topleft = (10,10)
                        game.hod.rect.topleft = (WIDTH-60, HEIGHT-60)
                        game.state = 'PLAY'

        if game.state == 'TITLE':
            game.title_screen()
            txt = font.render(f"Name: {input_name}_", True, WHITE)
            screen.blit(txt, (320,380))

        elif game.state == 'PLAY':
            game.update(keys)
            game.draw()

        elif game.state == 'HIT':
            screen.fill(BLACK)
            t = font.render("You were caught! Press ENTER", True, WHITE)
            screen.blit(t, (260,260))

        elif game.state == 'LEVELCLEAR':
            screen.fill(BLACK)
            t = font.render("Level Clear! Press ENTER", True, WHITE)
            screen.blit(t, (260,260))

        elif game.state == 'GAMEOVER':
            game.gameover_screen()

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()
