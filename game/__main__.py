import pygame

from .engine import GameState


def main():
    pygame.init()
    gamestate = GameState()
    while True:
        gamestate.step()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
