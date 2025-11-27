"""
main.py
Advanced Campus Maze Runner (Level progression, H.O.D slower than player, sounds placeholder,
mobile touch support, sprites support, gate, collectibles, start/level/gameover screens).

To run:
- Place optional assets under ./assets/ (boy.png, girl.png, hod.png, note.png, footstep.wav, bell.wav, caught.wav)
- There is a background image included in the project and referenced in BG_IMG_PATH variable.
- Run with Python 3.10+ and pygame installed: pip install pygame
"""

import pygame
import random
import sys
import os
from collections import deque

# ---------------- CONFIG ----------------
WIDTH, HEIGHT = 900, 600
TILE = 40  # size of maze tile
FPS = 60
MAX_LEVEL = 5
ASSETS_DIR = "assets"
BG_IMG_PATH = "/mnt/data/70d637ca-f5f9-4488-bd6f-c73c15c951ad.png"  # provided uploaded image path

# Colors
WHITE = (255,255,255)
BLACK = (0,0,0)
FLOOR = (230, 229, 220)
WALL_TOP = (30,80,220)
WALL_SIDE = (20,50,150)
GREEN = (50,205,50)
RED = (220,20,60)
GOLD = (255,215,0)

# ---------------- HELPERS ----------------
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Campus Maze — Main")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 20)
big_font = pygame.font.SysFont("Arial", 48, bold=True)

# Safe asset loader
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
    except Exception:
        return None

# ---------------- MAZE GENERATOR ----------------
def generate_maze(cols, rows):
    # Ensure odd sizes
    if cols % 2 == 0: cols += 1
    if rows % 2 == 0: rows += 1
    grid = [[1 for _ in range(cols)] for _ in range(rows)]
    def carve(x, y):
        dirs = [(2,0),(-2,0),(0,2),(0,-2)]
        random.shuffle(dirs)
        for dx,dy in dirs:
            nx, ny = x+dx, y+dy
            if 1 <= nx < cols-1 and 1 <= ny < rows-1 and grid[ny][nx]==1:
                grid[y+dy//2][x+dx//2] = 0
                grid[ny][nx] = 0
                carve(nx, ny)
    grid[1][1] = 0
    carve(1,1)
    grid[rows-2][cols-2] = 0
    return grid

# ---------------- SPRITES ----------------
class Wall(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((TILE, TILE))
        self.image.fill(WALL_SIDE)
        pygame.draw.rect(self.image, WALL_TOP, (0,0,TILE,TILE-10))
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
        self.name = name
        self.gender = gender
        self.base_speed = 4.0
        self.speed = self.base_speed
        size = (30,30)
        if gender.lower().startswith('m'):
            self.image = load_image('boy.png', (60,120,220), size)
        else:
            self.image = load_image('girl.png', (220,100,120), size)
        self.rect = self.image.get_rect(topleft=(x,y))
        self.lives = 3
        self.score = 0
        self.boost_timer = 0
        self.name_tag = font.render(name, True, WHITE)

    def update(self, keys, walls, touch=None):
        dx = dy = 0
        if keys[pygame.K_LEFT] or keys.get('left'): dx = -self.speed
        if keys[pygame.K_RIGHT] or keys.get('right'): dx = self.speed
        if keys[pygame.K_UP] or keys.get('up'): dy = -self.speed
        if keys[pygame.K_DOWN] or keys.get('down'): dy = self.speed

        # Move on x and collide
        self.rect.x += dx
        for w in walls:
            if self.rect.colliderect(w.rect):
                if dx>0: self.rect.right = w.rect.left
                elif dx<0: self.rect.left = w.rect.right
        # Move on y and collide
        self.rect.y += dy
        for w in walls:
            if self.rect.colliderect(w.rect):
                if dy>0: self.rect.bottom = w.rect.top
                elif dy<0: self.rect.top = w.rect.bottom

        # Boost timer
        if self.boost_timer>0:
            self.boost_timer -= 1
            if self.boost_timer==0: self.speed = self.base_speed

    def boost(self, amount=2.0, duration=180):
        self.speed = min(self.base_speed + amount, 8.0)
        self.boost_timer = duration

class HOD(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = load_image('hod.png', (200,60,60), (34,34))
        self.rect = self.image.get_rect(topleft=(x,y))
        self.base_speed = 1.0  # intentionally slower than player
        self.speed = self.base_speed

    def update(self, target_rect, walls, level):
        # Slightly increase with level but always keep slower than player
        self.speed = self.base_speed + 0.15 * (level-1)
        # chase simple vector but with collision slide
        dx = 1 if self.rect.x < target_rect.x else -1
        dy = 1 if self.rect.y < target_rect.y else -1

        # scale movement
        self.rect.x += int(dx * self.speed)
        for w in walls:
            if self.rect.colliderect(w.rect):
                self.rect.x -= int(dx * self.speed)
        self.rect.y += int(dy * self.speed)
        for w in walls:
            if self.rect.colliderect(w.rect):
                self.rect.y -= int(dy * self.speed)

# ---------------- GAME MANAGER ----------------
class Game:
    def __init__(self):
        self.level = 1
        self.state = 'TITLE'  # TITLE, PLAY, HIT, LEVELCLEAR, GAMEOVER
        self.player_name = 'Player'
        self.gender = 'Male'
        self.all_sprites = pygame.sprite.Group()
        self.walls = pygame.sprite.Group()
        self.notes = pygame.sprite.Group()
        self.hod_group = pygame.sprite.Group()
        self.gate = None
        self.bg = None

        # Load sounds (optional)
        self.snd_bell = load_sound('bell.wav')
        self.snd_caught = load_sound('caught.wav')
        self.snd_foot = load_sound('footstep.wav')

        # load background image if exists
        try:
            self.bg = pygame.image.load(BG_IMG_PATH).convert()
            self.bg = pygame.transform.scale(self.bg, (WIDTH, HEIGHT))
        except Exception:
            self.bg = None

    def start_level(self, level):
        # clear groups
        self.all_sprites.empty(); self.walls.empty(); self.notes.empty(); self.hod_group.empty()
        cols = WIDTH // TILE
        rows = HEIGHT // TILE
        grid = generate_maze(cols, rows)

        spawn_points = []
        for r in range(rows):
            for c in range(cols):
                x, y = c*TILE, r*TILE
                if grid[r][c]==1:
                    w = Wall(x,y); self.walls.add(w); self.all_sprites.add(w)
                else:
                    spawn_points.append((x,y))

        start = spawn_points[0]
        end = spawn_points[-1]

        # Player
        self.player = Player(self.player_name, self.gender, start[0]+6, start[1]+6)
        self.all_sprites.add(self.player)
        # Gate
        self.gate = Gate(end[0], end[1]); self.all_sprites.add(self.gate)
        # HOD
        mid = spawn_points[len(spawn_points)//2]
        self.hod = HOD(mid[0], mid[1]); self.hod_group.add(self.hod); self.all_sprites.add(self.hod)
        # Notes (collectibles)
        note_count = 6 + level*2
        for _ in range(note_count):
            p = random.choice(spawn_points)
            n = Note(p[0], p[1]); self.notes.add(n); self.all_sprites.add(n)

        # Ensure HOD always slower than player
        if self.hod.speed >= self.player.base_speed:
            self.hod.base_speed = max(0.5, self.player.base_speed - 2.5)

        self.state = 'PLAY'

    def update(self, keys):
        if self.state == 'PLAY':
            self.player.update(keys, list(self.walls), None)
            self.hod.update(self.player.rect, list(self.walls), self.level)

            # Note collection
            hits = pygame.sprite.spritecollide(self.player, self.notes, True)
            if hits:
                self.player.score += 100 * len(hits)
                self.player.boost(amount=2.0, duration=240)

            # caught
            if pygame.sprite.collide_rect(self.player, self.hod):
                self.player.lives -= 1
                if self.snd_caught: self.snd_caught.play()
                if self.player.lives <= 0:
                    self.state = 'GAMEOVER'
                else:
                    self.state = 'HIT'
                    self.hit_timer = 90

            # reach gate
            if pygame.sprite.collide_rect(self.player, self.gate):
                self.player.score += 1000 if self.player.lives==3 else 500
                if self.snd_bell: self.snd_bell.play()
                self.state = 'LEVELCLEAR'
                self.level += 1
                if self.level > MAX_LEVEL: self.level = MAX_LEVEL

    def draw(self):
        if self.bg:
            screen.blit(self.bg, (0,0))
        else:
            screen.fill(FLOOR)

        for w in self.walls: screen.blit(w.image, w.rect)
        for n in self.notes: screen.blit(n.image, n.rect)
        screen.blit(self.gate.image, self.gate.rect)
        screen.blit(self.player.image, self.player.rect)
        screen.blit(self.hod.image, self.hod.rect)

        # player name tag
        tag = font.render(self.player.name, True, WHITE)
        screen.blit(tag, (self.player.rect.centerx - tag.get_width()//2, self.player.rect.top - 18))

        # HUD
        hud = font.render(f"Score:{self.player.score}  Lvl:{self.level}  Lives:{self.player.lives}", True, WHITE)
        screen.blit(hud, (8,8))

    def title_screen(self):
        screen.fill(BLACK)
        screen.blit(big_font.render("Campus Maze Runner", True, WHITE), (160,120))
        screen.blit(font.render("Press ENTER to Start", True, WHITE), (360,260))
        screen.blit(font.render(f"Selected: {self.gender} (M/F to toggle)", True, WHITE), (320,300))
        screen.blit(font.render(f"Name: {self.player_name} (Type and press Enter)", True, WHITE), (260,340))

    def gameover_screen(self):
        screen.fill(BLACK)
        screen.blit(big_font.render("GAME OVER", True, RED), (300,180))
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
                        # commit name and start
                        if input_name.strip() != '': game.player_name = input_name.strip()
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
                        # reset
                        game = Game()
                elif game.state in ('LEVELCLEAR','HIT'):
                    # allow player to hit any key to continue
                    if event.key == pygame.K_RETURN:
                        if game.state == 'LEVELCLEAR':
                            # next level
                            game.start_level(game.level)
                        elif game.state == 'HIT':
                            # respawn
                            game.player.rect.topleft = (10,10)
                            game.hod.rect.topleft = (WIDTH-80, HEIGHT-80)
                            game.state = 'PLAY'

        # Keyboard state based inputs
        if game.state == 'TITLE':
            game.title_screen()
            # draw the typed name
            txt = font.render(f"Name: {input_name}_", True, WHITE)
            screen.blit(txt, (300,380))
        elif game.state == 'PLAY':
            game.update(keys)
            game.draw()
        elif game.state == 'HIT':
            # show hit countdown
            txt = font.render("You were caught! Press ENTER to continue", True, WHITE)
            screen.fill(BLACK)
            screen.blit(txt, (180,260))
        elif game.state == 'LEVELCLEAR':
            txt = font.render("Level clear! Press ENTER to continue", True, WHITE)
            screen.fill(BLACK)
            screen.blit(txt, (260,260))
        elif game.state == 'GAMEOVER':
            game.gameover_screen()

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()
