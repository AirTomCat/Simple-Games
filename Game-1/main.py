import pygame
import sys
import os
import math

# --- Constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)

# Player properties
PLAYER_ACC = 0.5
PLAYER_FRICTION = -0.12
PLAYER_GRAV = 0.8
PLAYER_JUMP = -15

# --- Game Classes ---

class Player(pygame.sprite.Sprite):
    def __init__(self, game):
        super().__init__()
        self.game = game
        self.image = pygame.Surface((30, 40))
        self.image.fill(BLUE)
        self.rect = self.image.get_rect()
        self.rect.center = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)

        # Motion vectors
        self.pos = pygame.math.Vector2(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
        self.vel = pygame.math.Vector2(0, 0)
        self.acc = pygame.math.Vector2(0, 0)
        
        # Player state
        self.on_ground = False
        self.last_shot = 0

    def shoot(self):
        now = pygame.time.get_ticks()
        if now - self.last_shot > 250: # Cooldown of 250ms
            self.last_shot = now
            # Get mouse position to aim
            mouse_pos = pygame.mouse.get_pos()
            player_center = self.rect.center
            
            # Calculate direction vector
            direction = pygame.math.Vector2(mouse_pos[0] - player_center[0], mouse_pos[1] - player_center[1])
            if direction.length() == 0:
                direction = pygame.math.Vector2(1, 0) # Default to right if no direction
            direction.normalize_ip()

            bullet = Bullet(self.rect.centerx, self.rect.centery, direction)
            self.game.all_sprites.add(bullet)
            self.game.bullets.add(bullet)


    def jump(self):
        # Jump only if standing on a platform
        self.rect.y += 2
        hits = pygame.sprite.spritecollide(self, self.game.platforms, False)
        self.rect.y -= 2
        if hits:
            self.vel.y = PLAYER_JUMP

    def update(self):
        # Apply gravity
        self.acc = pygame.math.Vector2(0, PLAYER_GRAV)
        
        # Check for key presses
        keys = pygame.key.get_pressed()
        if keys[pygame.K_a]:
            self.acc.x = -PLAYER_ACC
        if keys[pygame.K_d]:
            self.acc.x = PLAYER_ACC

        # Apply friction
        self.acc.x += self.vel.x * PLAYER_FRICTION
        
        # Equations of motion
        self.vel += self.acc
        self.pos += self.vel + 0.5 * self.acc

        # Wrap around the sides of the screen
        if self.pos.x > SCREEN_WIDTH:
            self.pos.x = 0
        if self.pos.x < 0:
            self.pos.x = SCREEN_WIDTH

        self.rect.midbottom = self.pos

    def check_platform_collisions(self, platforms):
        # Vertical collision
        self.rect.y += self.vel.y
        hits = pygame.sprite.spritecollide(self, platforms, False)
        if hits:
            if self.vel.y > 0: # Falling down
                self.pos.y = hits[0].rect.top + 1
                self.vel.y = 0
                self.on_ground = True
            elif self.vel.y < 0: # Moving up
                self.rect.top = hits[0].rect.bottom
                self.vel.y = 0
        self.rect.y = self.pos.y

class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, w, h):
        super().__init__()
        self.image = pygame.Surface((w, h))
        self.image.fill(GREEN)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, direction):
        super().__init__()
        self.image = pygame.Surface((10, 10))
        self.image.fill(RED)
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.speed = 10
        self.vel = direction * self.speed
        self.spawn_time = pygame.time.get_ticks()

    def update(self):
        self.rect.x += self.vel.x
        self.rect.y += self.vel.y
        # Remove bullet if it goes off-screen
        if not pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT).colliderect(self.rect):
            self.kill()
            
class Enemy(pygame.sprite.Sprite):
    def __init__(self, platform):
        super().__init__()
        self.platform = platform
        self.image = pygame.Surface((30, 30))
        self.image.fill(WHITE)
        self.rect = self.image.get_rect()
        self.rect.bottom = self.platform.rect.top
        self.rect.centerx = self.platform.rect.centerx
        self.vx = 3

    def update(self):
        self.rect.x += self.vx
        # Patrol back and forth on the platform
        if self.rect.right > self.platform.rect.right or self.rect.left < self.platform.rect.left:
            self.vx *= -1

# --- Game Main Class ---

class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init() # For sound
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Pixel Contra")
        self.clock = pygame.time.Clock()
        self.running = True

    def new(self):
        # Start a new game
        self.all_sprites = pygame.sprite.Group()
        self.platforms = pygame.sprite.Group()
        self.bullets = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()

        # Create player
        self.player = Player(self)
        self.all_sprites.add(self.player)

        # Create platforms
        p1 = Platform(0, SCREEN_HEIGHT - 40, SCREEN_WIDTH, 40)
        p2 = Platform(SCREEN_WIDTH / 2 - 100, SCREEN_HEIGHT * 3 / 4, 200, 20)
        p3 = Platform(150, SCREEN_HEIGHT / 2 - 50, 150, 20)
        self.platforms.add(p1, p2, p3)
        self.all_sprites.add(p1, p2, p3)
        
        # Create an enemy on a platform
        enemy = Enemy(p2)
        self.all_sprites.add(enemy)
        self.enemies.add(enemy)

        self.run()

    def run(self):
        # Game Loop
        self.playing = True
        while self.playing:
            self.clock.tick(FPS)
            self.events()
            self.update()
            self.draw()

    def update(self):
        # Game Loop - Update
        self.all_sprites.update()
        
        # Player-platform collision (a bit more complex due to physics)
        # We need to check for collisions after the player has moved.
        self.player.check_platform_collisions(self.platforms)
        
        # Bullet-enemy collision
        hits = pygame.sprite.groupcollide(self.enemies, self.bullets, True, True)
        # The 'True, True' arguments make both the enemy and bullet disappear on collision.
        
        # Player-enemy collision
        hits = pygame.sprite.spritecollide(self.player, self.enemies, False)
        if hits:
            self.playing = False # End game on collision

    def events(self):
        # Game Loop - Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if self.playing:
                    self.playing = False
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.player.jump()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # Left mouse button
                    self.player.shoot()

    def draw(self):
        # Game Loop - Draw
        self.screen.fill(BLACK)
        self.all_sprites.draw(self.screen)
        # *after* drawing everything, flip the display
        pygame.display.flip()

    def show_start_screen(self):
        pass # To be implemented
        
    def show_go_screen(self):
        pass # To be implemented

g = Game()
g.show_start_screen()
while g.running:
    g.new()
    g.show_go_screen()

pygame.quit()
sys.exit()
