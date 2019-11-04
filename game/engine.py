#!/usr/bin/env python3

import pygame

from . import constants
from .constants import GameModes
from .cutscenes import CutScene
from .gameobjects import Player, GameObject, GameGroup, Pointer
from .graphics import TextBox, TextBoxPage
from .utilities import get_asset_path


# TODO: add save files
class GameState():
    """General purpose manager for the game state."""

    SCREEN_SIZE = (512, 288)
    SCROLL_MARGIN = 80

    def __init__(self):
        self.display = pygame.display.set_mode(self.SCREEN_SIZE)
        self.clock = pygame.time.Clock()
        self.step_delta = 0
        test_pointer = Pointer(16,-50)
        self.player = Player(100, 100)
        self.player.children.add(test_pointer)
        # TODO: create Levels, and use them to initialize the gamestate
        self.interactable_objects = GameGroup()
        self.dynamic_objects = GameGroup(self.player)
        self.static_objects = GameGroup()
        self.all_objects = GameGroup(
            self.dynamic_objects,
            self.static_objects,
            self.interactable_objects
        )
        self.mode = GameModes.PLAYING
        self.cutscene = None
        self.keydowns = set()

    def process_events(self):
        self.keydowns.clear()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit()
            if event.type == pygame.KEYDOWN:
                self.keydowns.add(event.key)
                ctrl_mod = (event.mod & pygame.KMOD_CTRL) > 0
                if event.key == pygame.K_q and ctrl_mod:
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
            if self.mode == GameModes.PLAYING:
                if event.type == constants.INTERACTION_CHAT:
                    self.mode = GameModes.CINEMATIC
                    self.cutscene = CutScene(cue_list=['chat'])
                    self.cutscene.edit_cue('chat', 0, textbox=event.gameobject.chat(self))
                    self.cutscene.start()

    def adjust_camera_for_player(self):
        screen_left, screen_top = self.all_objects.offset
        margin_left = screen_left + self.SCROLL_MARGIN
        margin_right = screen_left + self.SCREEN_SIZE[0] - self.SCROLL_MARGIN
        margin_top = screen_top + self.SCROLL_MARGIN
        margin_bottom = screen_top + self.SCREEN_SIZE[1] - self.SCROLL_MARGIN

        scroll_x = 0
        if self.player.rect.right > margin_right:
            scroll_x = self.player.rect.right - margin_right
        elif self.player.rect.left < margin_left:
            scroll_x = self.player.rect.left - margin_left

        scroll_y = 0
        if self.player.rect.top < margin_top:
            scroll_y = self.player.rect.top - margin_top
        elif self.player.rect.bottom > margin_bottom:
            scroll_y = self.player.rect.bottom - margin_bottom

        self.scroll_camera(scroll_x, scroll_y)

    def scroll_camera(self, x, y):
        self.all_objects.scroll(x, y)

    def step(self):
        self.step_delta = self.clock.tick(constants.FPS)
        self.process_events()
        if self.mode == GameModes.PLAYING:
            self.dynamic_objects.update(self)
            self.adjust_camera_for_player()
        elif self.mode == GameModes.CINEMATIC:
            self.cutscene.update(self)
            if self.cutscene.finished:
                self.cutscene = None
                self.mode = GameModes.PLAYING
                self.player.last_chatted = pygame.time.get_ticks()
        self.draw()
        return self.step_delta

    def draw(self):
        self.display.fill((128, 128, 155))
        self.all_objects.draw(self.display)
        if self.cutscene:
            self.cutscene.draw(self.display)
        pygame.display.flip()
