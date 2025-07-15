import pygame, random, time
from pygame.locals import *
from communication import Communication
from etactilekit import ETactileKit
from force import ForceSensor

# VARIABLES
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SPEED = 30
GRAVITY = 2.5
GAME_SPEED = 15

GROUND_WIDTH = 2 * SCREEN_WIDTH
GROUND_HEIGHT = 108

PIPE_WIDTH = 90
PIPE_HEIGHT = 450

wing = "assets/audio/wing.wav"
hit = "assets/audio/hit.wav"

pygame.mixer.init()

# -----------Initialize the electro-tactile communication----------------#

PORT_1_NAME = 'COM6'  #serial port for ET device
PORT_2_NAME = 'COM11' #serial port for FSR device
BAUDRATE = 921600 #115200

comm1 = Communication(PORT_1_NAME, BAUDRATE)
comm1.connect()

etactilekit = ETactileKit(comm1)
# etactilekit.send_pulse_width(50)  #pulse width
# etactilekit.send_pulse_height(35) #pulse height

etactilekit.send_electrode_number(8) #number of electrodes set to 8

on_pattern  = [1]*8
off_pattern = [0]*8

comm2 = Communication(PORT_2_NAME, BAUDRATE)
comm2.connect()
fsr = ForceSensor(comm2)

# ------------------------------------------------------------------------#

class Bird(pygame.sprite.Sprite):
    def __init__(self):
        pygame.sprite.Sprite.__init__(self)

        bird_size = (70, 70)

        # Load bird images for animation
        self.images = [
            pygame.transform.scale(
                pygame.image.load(
                    "assets/sprites/yellowbird-upflap.png"
                ).convert_alpha(),
                bird_size,
            ),
            pygame.transform.scale(
                pygame.image.load(
                    "assets/sprites/yellowbird-midflap.png"
                ).convert_alpha(),
                bird_size,
            ),
            pygame.transform.scale(
                pygame.image.load(
                    "assets/sprites/yellowbird-downflap.png"
                ).convert_alpha(),
                bird_size,
            ),
        ]

        self.speed = SPEED

        self.current_image = 0
        self.image = pygame.transform.scale(
            pygame.image.load("assets/sprites/yellowbird-upflap.png").convert_alpha(),
            bird_size,
        )
        self.mask = pygame.mask.from_surface(self.image)

        self.rect = self.image.get_rect()
        self.rect[0] = SCREEN_WIDTH / 6
        self.rect[1] = SCREEN_HEIGHT / 2

    def update(self):
        # Update bird animation and position
        self.current_image = (self.current_image + 1) % 3
        self.image = self.images[self.current_image]
        self.speed += GRAVITY

        # Update height
        self.rect[1] += self.speed

    def bump(self, scale=1):
        # Make the bird jump
        self.speed = -scale * SPEED

    def begin(self):
        # Update bird animation for the beginning screen
        self.current_image = (self.current_image + 1) % 3
        self.image = self.images[self.current_image]


class Pipe(pygame.sprite.Sprite):
    def __init__(self, inverted, xpos, ysize):
        pygame.sprite.Sprite.__init__(self)

        # Load and scale pipe image
        self.image = pygame.image.load("assets/sprites/pipe-green.png").convert_alpha()
        self.image = pygame.transform.scale(self.image, (PIPE_WIDTH, PIPE_HEIGHT))

        self.rect = self.image.get_rect()
        self.rect[0] = xpos

        if inverted:
            # Invert pipe for top pipe
            self.image = pygame.transform.flip(self.image, False, True)
            self.rect[1] = -(self.rect[3] - ysize)
        else:
            # Position pipe for bottom pipe
            self.rect[1] = SCREEN_HEIGHT - ysize

        self.mask = pygame.mask.from_surface(self.image)
        # Added by Mansitha
        self.scored = False  # New attribute to track if pipe has been scored

    def update(self):
        # Move pipe to the left
        self.rect[0] -= GAME_SPEED


class Ground(pygame.sprite.Sprite):
    def __init__(self, xpos):
        pygame.sprite.Sprite.__init__(self)
        # Load and scale ground image
        self.image = pygame.image.load("assets/sprites/base.png").convert_alpha()
        self.image = pygame.transform.scale(self.image, (GROUND_WIDTH, GROUND_HEIGHT))

        self.mask = pygame.mask.from_surface(self.image)

        self.rect = self.image.get_rect()
        self.rect[0] = xpos
        self.rect[1] = SCREEN_HEIGHT - GROUND_HEIGHT

    def update(self):
        # Move ground to the left
        self.rect[0] -= GAME_SPEED


def is_off_screen(sprite):
    # Check if sprite is off the screen
    return sprite.rect[0] < -(sprite.rect[2])


def get_random_pipes(xpos, PIPE_GAP=300):
    # Generate random pipes
    size = random.randint(260, 460)
    pipe = Pipe(False, xpos, size)
    pipe_inverted = Pipe(True, xpos, SCREEN_HEIGHT - size - PIPE_GAP)
    return pipe, pipe_inverted


pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Flappy Bird")

# Load background and beginning screen images
BACKGROUND = pygame.image.load("assets/sprites/background-day.png")
BACKGROUND = pygame.transform.scale(BACKGROUND, (SCREEN_WIDTH, SCREEN_HEIGHT))


# Added by Mansitha
# Load font for score display
pygame.font.init()
font = pygame.font.Font(None, 74)

# Electrotactile parameters
volume = 0
width = 50


def main():

    global volume, width
    PIPE_GAP = 220
    # Added by Mansitha
    score = 0  # Initialize score

    # Create bird group and add bird
    bird_group = pygame.sprite.Group()
    bird = Bird()
    bird_group.add(bird)

    # Create ground group and add ground sprites
    ground_group = pygame.sprite.Group()
    for i in range(2):
        ground = Ground(GROUND_WIDTH * i)
        ground_group.add(ground)

    # Create pipe group and add pipe sprites
    pipe_group = pygame.sprite.Group()
    for i in range(6):
        pipes = get_random_pipes(
            SCREEN_WIDTH * (i // 3) + 450 * (i % 3) + 900, PIPE_GAP
        )
        pipe_group.add(pipes[0])
        pipe_group.add(pipes[1])

    clock = pygame.time.Clock()

    begin = True
    
    #enable electrdoes for calibrations
    etactilekit.send_stim_pattern(on_pattern)

    # Beginning screen loop
    while begin:
        clock.tick(15)

        text = font.render("Calibrating...", True, (255, 255, 255))

        print('Volume', volume, 'Width', width, 'Force', fsr.get_force_reading())

        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
            if event.type == KEYDOWN:

                # Calibrate electrotactile with up, down, left, right keys and reset with escape key TODO: Give electrotactile feedback and adjust the change values
                if event.key == K_UP:
                    volume += 5
                elif event.key == K_DOWN:
                    volume -= 5
                if event.key == K_LEFT:
                    width -= 5
                elif event.key == K_RIGHT:
                    width += 5
                if event.key == K_ESCAPE:
                    volume, width = 0, 50

                # Start game with space key
                elif event.key == K_SPACE:
                    bird.bump()
                    pygame.mixer.music.load(wing)
                    pygame.mixer.music.play()
                    etactilekit.send_stim_pattern(off_pattern)
                    previous_force = fsr.get_force_reading()

                    begin = False

        volume = max(0, min(45, volume))  # TODO: Set max values
        width = max(0, min(100, width))  # TODO: Set max values

        #set et pulse parameters
        etactilekit.send_pulse_width(width)  #pulse width
        etactilekit.send_pulse_height(volume) #pulse height

        screen.blit(BACKGROUND, (0, 0))
        screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, 50))

        if is_off_screen(ground_group.sprites()[0]):
            ground_group.remove(ground_group.sprites()[0])
            new_ground = Ground(GROUND_WIDTH - 20)
            ground_group.add(new_ground)

        bird.begin()
        ground_group.update()

        bird_group.draw(screen)
        ground_group.draw(screen)

        pygame.display.update()

    count = 0
    # Main game loop
    while True:
        clock.tick(15)

        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
            if event.type == KEYDOWN:
                # if event.key == K_SPACE:
                #     bird.bump()
                #     pygame.mixer.music.load(wing)
                #     pygame.mixer.music.play()
                if event.key == K_q:
                    pygame.quit()
            
        current_force = fsr.get_force_reading()
        force_change = (current_force - previous_force) / 2500

        if force_change > 0.5:
            bird.bump(force_change - 0.5)
            pygame.mixer.music.load(wing)
            pygame.mixer.music.play()
            etactilekit.send_stim_pattern(on_pattern)
            time.sleep(0.015)
            etactilekit.send_stim_pattern(off_pattern)


        screen.blit(BACKGROUND, (0, 0))

        if is_off_screen(ground_group.sprites()[0]):
            ground_group.remove(ground_group.sprites()[0])
            new_ground = Ground(GROUND_WIDTH - 20)
            ground_group.add(new_ground)

        if is_off_screen(pipe_group.sprites()[0]):
            pipe_group.remove(pipe_group.sprites()[0])
            pipe_group.remove(pipe_group.sprites()[0])
            pipes = get_random_pipes(SCREEN_WIDTH * 2, PIPE_GAP)
            pipe_group.add(pipes[0])
            pipe_group.add(pipes[1])

        bird_group.update()
        ground_group.update()
        pipe_group.update()

        # Added by Mansitha
        # Score tracking logic
        for pipe in pipe_group.sprites():
            # Check if the bird has passed the pipe without scoring already
            if not pipe.scored and pipe.rect[0] + PIPE_WIDTH < (bird.rect[0]):
                score += 1
                pipe.scored = True
                # Give the electro-tactile pattern here to show the score
                etactilekit.send_stim_pattern(on_pattern)
                time.sleep(0.05)
                etactilekit.send_stim_pattern(off_pattern)

        bird_group.draw(screen)
        pipe_group.draw(screen)
        ground_group.draw(screen)

        # Render score
        score_text = font.render("Score:" + str(int(score / 2)), True, (255, 255, 255))
        screen.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, 50))

        pygame.display.update()

        # Check for collisions TODO: Add electrotactile feedback
        if pygame.sprite.groupcollide(
            bird_group, ground_group, False, False, pygame.sprite.collide_mask
        ) or pygame.sprite.groupcollide(
            bird_group, pipe_group, False, False, pygame.sprite.collide_mask
        ):
            pygame.mixer.music.load(hit)
            pygame.mixer.music.play()
            text = font.render("Game Over!", True, (255, 255, 255))
            screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2))
            '''GAME OVER
            Give the electro-tactile pattern here'''
            for i in range(5):
                etactilekit.send_stim_pattern(on_pattern)
                time.sleep(0.15)
                etactilekit.send_stim_pattern(off_pattern)
                time.sleep(0.15)
            
            time.sleep(3)
            break

        if count % 100 == 0:
            PIPE_GAP -= 10
        PIPE_GAP = max(80, PIPE_GAP)
        count += 1


if __name__ == "__main__":

    while True:
        main()
