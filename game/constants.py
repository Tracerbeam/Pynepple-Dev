import pygame, os

from enum import Enum


ROOT_DIR = os.path.dirname(os.path.realpath(__file__))

FPS = 30

INTERACTION_CHAT = pygame.USEREVENT + 0


class GameModes(Enum):
    # Indicating the player is in control
    PLAYING = 0
    # Usually meaning a textbox is open
    CINEMATIC = 1


class Directions(Enum):
    NORTH = UP = 0
    SOUTH = DOWN = 1
    WEST = LEFT = 2
    EAST = RIGHT = 3
