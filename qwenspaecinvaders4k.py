import pygame
import sys
import random
import io
import wave
import struct
import math

# --- SETUP ---
pygame.mixer.pre_init(22050, -16, 1, 1024)
pygame.init()
pygame.mixer.set_num_channels(12)
screen = pygame.display.set_mode((640, 480))
pygame.display.set_caption("AC's Space Invaders — ChatGPT + Qwen + Cursor")
clock = pygame.time.Clock()
FPS = 60
WIDTH, HEIGHT = 640, 480

# OG Space Invaders–style pacing (slow lockstep formation, one player shot).
PLAYER_SPEED = 2
PLAYER_BULLET_SPEED = 3
ENEMY_BULLET_SPEED = 2
INVADER_STEP_X = 4
INVADER_DROP_Y = 8
INVADER_START_COUNT = 8 * 4
# Frames between whole-formation moves; speeds up as fewer invaders remain (like OG).
def invader_move_delay(enemy_count: int) -> int:
    return max(6, int(8 + 44 * (enemy_count / INVADER_START_COUNT)))

ENEMY_SHOOT_CHANCE = 0.05
MAX_PLAYER_BULLETS = 1

BLACK, WHITE, GREEN, RED, YELLOW = (0,0,0), (255,255,255), (0,255,0), (255,0,0), (255,255,0)
font = pygame.font.SysFont('monospace', 24, bold=True)
big_font = pygame.font.SysFont('monospace', 36, bold=True)

# --- PROCEDURAL AUDIO (files=off) ---
def make_tone(freq, duration_ms, vol=0.4):
    sr = 22050
    frames = max(1, int(sr * duration_ms / 1000))
    amp = int(32767 * vol)
    buf = b"".join(
        struct.pack(
            "<h",
            int(amp if math.sin(2 * math.pi * freq * i / sr) >= 0 else -amp),
        )
        for i in range(frames)
    )
    bio = io.BytesIO()
    with wave.open(bio, 'wb') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr); wf.writeframes(buf)
    bio.seek(0)
    return pygame.mixer.Sound(bio)

snd_shoot = make_tone(880, 80, 0.3)
snd_hit = make_tone(220, 150, 0.5)
snd_e_shoot = make_tone(330, 100, 0.3)
snd_menu = make_tone(1000, 50, 0.2)
snd_over = make_tone(150, 400, 0.4)

# --- GAME STATE ---
STATE_MENU, STATE_PLAY, STATE_ABOUT, STATE_CREDITS, STATE_GAMEOVER = range(5)
state = STATE_MENU
menu_idx = 0
menu_items = ["Play Game", "About", "Credits", "Exit"]

player, enemies, bullets, enemy_bullets = None, [], [], []
score, lives, enemy_dir, enemy_move_timer = 0, 3, 1, 0
game_over, win = False, False

def reset_game():
    global player, enemies, bullets, enemy_bullets, score, lives, enemy_dir, enemy_move_timer, game_over, win
    player = pygame.Rect(WIDTH//2 - 20, HEIGHT - 50, 40, 20)
    enemies = [pygame.Rect(80 + c*60, 60 + r*40, 40, 20) for r in range(4) for c in range(8)]
    bullets, enemy_bullets = [], []
    score, lives, enemy_dir, enemy_move_timer, game_over, win = 0, 3, 1, 0, False, False

def draw_txt(t, x, y, c=WHITE, f=font):
    screen.blit(f.render(t, True, c), (x, y))

# --- MAIN LOOP ---
running = True
while running:
    for e in pygame.event.get():
        if e.type == pygame.QUIT: running = False
        elif e.type == pygame.KEYDOWN:
            if state == STATE_MENU:
                if e.key in (pygame.K_UP, pygame.K_DOWN):
                    menu_idx = (menu_idx + (-1 if e.key == pygame.K_UP else 1)) % len(menu_items)
                    snd_menu.play()
                elif e.key == pygame.K_RETURN:
                    choice = menu_items[menu_idx]
                    if choice == "Play Game": reset_game(); state = STATE_PLAY
                    elif choice == "About": state = STATE_ABOUT; snd_menu.play()
                    elif choice == "Credits": state = STATE_CREDITS; snd_menu.play()
                    elif choice == "Exit": running = False
            elif e.key == pygame.K_ESCAPE:
                state = STATE_MENU; snd_menu.play()
            elif state == STATE_PLAY and e.key == pygame.K_SPACE and len(bullets) < MAX_PLAYER_BULLETS:
                bullets.append(pygame.Rect(player.x + 18, player.y - 10, 4, 10))
                snd_shoot.play()
            elif state == STATE_GAMEOVER and e.key == pygame.K_RETURN:
                state = STATE_MENU

    keys = pygame.key.get_pressed()
    if state == STATE_PLAY:
        player.x += (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * PLAYER_SPEED
        player.x = max(0, min(WIDTH - player.width, player.x))

        new_bullets = []
        for b in bullets:
            b.y -= PLAYER_BULLET_SPEED
            hit = False
            for en in enemies:
                if b.colliderect(en):
                    enemies.remove(en); score += 50; hit = True; snd_hit.play(); break
            if not hit and b.y >= 0: new_bullets.append(b)
        bullets = new_bullets

        new_eb = []
        for b in enemy_bullets:
            b.y += ENEMY_BULLET_SPEED
            if b.y < HEIGHT:
                if b.colliderect(player):
                    lives -= 1; snd_over.play()
                    if lives <= 0: game_over = True
                else: new_eb.append(b)
        enemy_bullets = new_eb

        if enemies:
            delay = invader_move_delay(len(enemies))
            enemy_move_timer += 1
            if enemy_move_timer >= delay:
                enemy_move_timer = 0
                if any(en.x <= 0 or en.x + en.width >= WIDTH for en in enemies):
                    enemy_dir *= -1
                    for en in enemies:
                        en.y += INVADER_DROP_Y
                else:
                    for en in enemies:
                        en.x += INVADER_STEP_X * enemy_dir
                if random.random() < ENEMY_SHOOT_CHANCE:
                    sh = random.choice(enemies)
                    enemy_bullets.append(pygame.Rect(sh.x + 18, sh.bottom, 4, 10))
                    snd_e_shoot.play()

        for en in enemies:
            if en.y + en.height >= player.y: game_over = True
        if not enemies: win = True
        if game_over or win: state = STATE_GAMEOVER; snd_over.play()

    # --- RENDER ---
    screen.fill(BLACK)
    if state == STATE_MENU:
        draw_txt("SPACE INVADERS", WIDTH//2 - 150, 120, GREEN, big_font)
        for i, it in enumerate(menu_items):
            draw_txt(it, WIDTH//2 - 90, 220 + i*40, YELLOW if i == menu_idx else WHITE)
    elif state == STATE_PLAY:
        pygame.draw.rect(screen, GREEN, player)
        for en in enemies: pygame.draw.rect(screen, WHITE, en)
        for b in bullets: pygame.draw.rect(screen, YELLOW, b)
        for b in enemy_bullets: pygame.draw.rect(screen, RED, b)
        draw_txt(f"SCORE: {score}", 10, 10)
        draw_txt(f"LIVES: {lives}", WIDTH - 140, 10)
    elif state == STATE_ABOUT:
        draw_txt("ABOUT", WIDTH//2 - 40, 100, GREEN, big_font)
        for i, line in enumerate(
            [
                "Move: LEFT / RIGHT",
                "Shoot: SPACE (one shot at a time, OG style)",
                "Destroy all aliens!",
                "AC's Space Invaders — ChatGPT + Qwen + Cursor",
                "Press ESC for menu",
            ]
        ):
            draw_txt(line, WIDTH//2 - 220, 180 + i * 35)
    elif state == STATE_CREDITS:
        draw_txt("CREDITS", WIDTH//2 - 60, 100, GREEN, big_font)
        draw_txt("ChatGPT + Qwen + Cursor + AC Holdings", WIDTH//2 - 220, 180)
        draw_txt("Press ESC", WIDTH//2 - 50, 300)
    elif state == STATE_GAMEOVER:
        draw_txt("YOU WIN!" if win else "GAME OVER", WIDTH//2 - 80, 180, GREEN if win else RED, big_font)
        draw_txt(f"SCORE: {score}", WIDTH//2 - 70, 240)
        draw_txt("ENTER for menu", WIDTH//2 - 90, 300)

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()