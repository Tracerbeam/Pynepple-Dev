import pygame

from . import constants
from .constants import Directions
from .graphics import Animator
from .utilities import get_asset_path


# TODO: create a group that can have a scroll state
class GameGroup(pygame.sprite.Group):
    def __init__(self, *args):
        super().__init__(*args)

    def select_rect(self, rectname):
        for sprite in self.sprites():
            if isinstance(sprite, GameObject) and rectname in sprite.rect_options:
                sprite.select_rect(rectname)


class Vector():
    def __init__(self, x, y):
        self.x = x
        self.y = y


# TODO: it really would be better if you did the select_rect stuff in a 
#       context manager...
class GameObject(pygame.sprite.Sprite):
    image = None
    rect_options = dict()
    spritesheet = spritesheet_frame_map = animations = None
    available_interactions = set()

    def __init__(self, startx, starty):
        super().__init__()

        if self.spritesheet:
            self.animator = Animator(
                self.animations,
                frame_map = self.spritesheet_frame_map,
                spritesheets = [self.spritesheet]
            )
            initial_animation = list(self.animations.keys())[0]
            self.animator.play(initial_animation)
            self.image = self.animator.get_current_frame()

        if not self.image:
            self.image = self.get_fallback_image()

        if len(self.rect_options) == 0 or 'renderer' not in self.rect_options:
            default_rect = pygame.Rect((0, 0), self.image.get_size())
            self.rect_options = { 'renderer': default_rect }
        initial_rect = list(self.rect_options.keys())[0]
        self.current_rect = initial_rect
        rect_size = self.rect_options[self.current_rect].size
        self.rect = pygame.Rect((startx, starty), rect_size)

    def get_fallback_image(self):
        fallback_image = pygame.Surface((128, 128))
        fallback_image.fill((255, 255, 255))
        return fallback_image

    def select_rect(self, target):
        """Chooses which rectangle to assign the sprite."""
        new_offset = self.rect_options[target]
        current_offset = self.rect_options[self.current_rect]
        # undo current offset
        self.rect.x -= current_offset.x
        self.rect.y -= current_offset.y
        # add the target offset
        self.rect.x += new_offset.x
        self.rect.y += new_offset.y
        self.rect.size = new_offset.size
        self.current_rect = target


class Player(GameObject):
    SPEED = 32 * 6 # pixels per second per axis
    INTERACTION_REACH = 30
    CONTROLS = {
        'left': pygame.K_a,
        'right': pygame.K_d,
        'up': pygame.K_w,
        'down': pygame.K_s,
        'interact': pygame.K_e
    }
    spritesheet = get_asset_path("mr_pynepple_64.png")
    spritesheet_frame_map = (
        (0, 0, 64, 64),
        (64, 0, 64, 64),
        (128, 0, 64, 64),
        (192, 0, 64, 64),
        (0, 64, 64, 64),
        (64, 64, 64, 64),
        (128, 64, 64, 64),
        (192, 64, 64, 64),
        (0, 128, 64, 64),
        (64, 128, 64, 64),
        (128, 128, 64, 64),
        (192, 128, 64, 64),
        (0, 192, 64, 64),
        (64, 192, 64, 64),
        (128, 192, 64, 64),
        (192, 192, 64, 64),
        (0, 256, 64, 64),
        (64, 256, 64, 64)
    )
    animations = {
        'idling_down': [1, 5, 6, 5],
        'idling_up': [3],
        'idling_left': [4, 9, 10, 9],
        'idling_right': [2, 7, 8, 7],
        'walking_down': [11, 1, 12, 1],
        'walking_up': [15, 3, 16, 3],
        'walking_left': [17, 4, 18, 4],
        'walking_right': [13, 2, 14, 2]
    }
    # A set of offsets by which to adjust the sprite's rect in
    # various situations. For example, collisions for various circumstances
    # might be calculated at different locations on the sprite.
    rect_options = {
        # Used for drawing the sprite to the screen
        'renderer': pygame.Rect(0, 0, 64, 64),
        # Used when walking into objects
        'foot_collider': pygame.Rect(18, 59, 28, 5)
    }

    def __init__(self, startx, starty):
        super().__init__(startx, starty)

        self.orientation = Directions.SOUTH
        self.velocity = Vector(0, 0)

    def update(self, gamestate):
        self.calculate_velocity(gamestate.step_delta)
        self.rect = self.rect.move(self.velocity.x, self.velocity.y)
        self.set_orientation(self.velocity.x, self.velocity.y)
        gamestate.static_objects.select_rect('collider')
        self.collide_with(gamestate.static_objects)
        gamestate.static_objects.select_rect('renderer')
        if pygame.key.get_pressed()[self.CONTROLS['interact']]:
            self.check_for_interactions(gamestate.interactable_objects)
        self.select_animation()
        self.image = self.animator.advance_animation(gamestate.step_delta)

    def calculate_velocity(self, ms_delta):
        pressed_keys = pygame.key.get_pressed()
        x_velocity, y_velocity = 0, 0
        if pressed_keys[self.CONTROLS['left']]:
            x_velocity -= self.SPEED
        if pressed_keys[self.CONTROLS['right']]:
            x_velocity += self.SPEED
        if pressed_keys[self.CONTROLS['up']]:
            y_velocity -= self.SPEED
        if pressed_keys[self.CONTROLS['down']]:
            y_velocity += self.SPEED

        self.velocity.x = (x_velocity * ms_delta) / 1000
        self.velocity.y = (y_velocity * ms_delta) / 1000

    def check_for_interactions(self, interactable):
        interaction_rect = self.get_interaction_rect()
        old_rect = self.rect
        self.rect = interaction_rect
        for gameobj in pygame.sprite.spritecollide(self, interactable, False):
            if constants.INTERACTION_CHAT in gameobj.available_interactions:
                interaction_event = pygame.event.Event(
                    constants.INTERACTION_CHAT,
                    { 'gameobject': gameobj }
                )
                pygame.event.post(interaction_event)
                break
        self.rect = old_rect

    def collide_with(self, obstacles):
        """Change position and velocity based on a group of sprites with which
        to collide. Note that the object colliding may be included in the group."""
        self.select_rect('foot_collider')
        # Generate collisions
        for bumped_obj in pygame.sprite.spritecollide(self, obstacles, False):
            if self == bumped_obj:
                pass
            brect = bumped_obj.rect
            # Determine which side to consider collided
            bumped_side = None
            if self.rect.centerx < brect.centerx:
                hor_depth = self.rect.right - brect.left
                if self.rect.centery < brect.centery:
                    vert_depth = self.rect.bottom - brect.top
                    if vert_depth > hor_depth:
                        bumped_side = Directions.RIGHT
                    else:
                        bumped_side = Directions.DOWN
                else: # if self.rect.centery >= brect.centery
                    vert_depth = brect.bottom - self.rect.top
                    if vert_depth > hor_depth:
                        bumped_side = Directions.RIGHT
                    else:
                        bumped_side = Directions.UP
            elif self.rect.centerx > brect.centerx:
                hor_depth = brect.right - self.rect.left
                if self.rect.centery < brect.centery:
                    vert_depth = self.rect.bottom - brect.top
                    if vert_depth > hor_depth:
                        bumped_side = Directions.LEFT
                    else:
                        bumped_side = Directions.DOWN
                else: # if self.rect.centery >= brect.centery
                    vert_depth = brect.bottom - self.rect.top
                    if vert_depth > hor_depth:
                        bumped_side = Directions.LEFT
                    else:
                        bumped_side = Directions.UP
            else: # self.rect.centerx == brect.centerx
                if self.rect.centery < brect.centery:
                    bumped_side = Directions.DOWN
                else:
                    bumped_side = Directions.UP

            # Adjust our location and velocity for the collision
            if bumped_side == Directions.UP or bumped_side == Directions.DOWN:
                self.velocity.y = 0
                if bumped_side == Directions.UP:
                    self.rect.top = brect.bottom
                else: 
                    self.rect.bottom = brect.top
            else: # if bumped_side in [Directions.LEFT, Directions.RIGHT]
                self.velocity.x = 0
                if bumped_side == Directions.LEFT:
                    self.rect.left = brect.right
                else: 
                    self.rect.right = brect.left
        self.select_rect('renderer')

    def get_interaction_rect(self):
        """
        Returns a rect that acts like a ray pointing out from the player's center
        towards what they're facing.
        """
        interaction_rect = pygame.Rect(0,0,3,3)
        if self.orientation == Directions.NORTH:
            interaction_rect.height = (self.INTERACTION_REACH * 2) // 3
            interaction_rect.midbottom = self.rect.center
        elif self.orientation == Directions.SOUTH:
            # vertical reach is a little shorter, for illusion of 3D
            interaction_rect.height = (self.INTERACTION_REACH * 3) // 4
            interaction_rect.midtop = self.rect.center
        elif self.orientation == Directions.EAST or self.orientation == Directions.WEST:
            interaction_rect.width = self.INTERACTION_REACH
            if self.orientation == Directions.WEST:
                interaction_rect.midright = self.rect.center
            else:
                interaction_rect.midleft = self.rect.center
        return interaction_rect

    def set_orientation(self, x_velocity, y_velocity):
        """Chooses the character's orientation based on its velocity.
        Horizontal orientations take precedence over vertical ones."""
        if x_velocity > 0:
            self.orientation = Directions.EAST
        elif x_velocity < 0:
            self.orientation = Directions.WEST
        elif y_velocity > 0:
            self.orientation = Directions.SOUTH
        elif y_velocity < 0:
            self.orientation = Directions.NORTH

    def select_animation(self):
        """Based on internal information on our state, tell the animator what
        it should be playing."""
        animation = None
        x_velocity, y_velocity = self.velocity.x, self.velocity.y
        if x_velocity == 0 and y_velocity == 0:
            if self.orientation == Directions.SOUTH:
                animation = 'idling_down'
            elif self.orientation == Directions.NORTH:
                animation = 'idling_up'
            elif self.orientation == Directions.WEST:
                animation = 'idling_left'
            elif self.orientation == Directions.EAST:
                animation = 'idling_right'
        elif x_velocity > 0:
            animation = 'walking_right'
        elif x_velocity < 0:
            animation = 'walking_left'
        elif y_velocity > 0:
            animation = 'walking_down'
        elif y_velocity < 0:
            animation = 'walking_up'
        self.animator.play(animation, reset=False)
