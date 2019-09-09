#!/usr/bin/env python3

import pygame

from . import constants
from .constants import GameModes
from .gameobjects import Player, GameObject, GameGroup
from .graphics import TextBox, TextBoxPage
from .utilities import get_asset_path


def get_old_man():
    old_man = pygame.Surface((48,64))
    old_man.fill((0,255,0))
    return old_man

class OldMan(GameObject):
    image = get_old_man()
    available_interactions = { constants.INTERACTION_CHAT }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def chat(self, gamestate):
        return TextBox(pagefile=get_asset_path('example_dialog.xml'))


class GameState():
    """General purpose manager for the game state."""

    SCREEN_SIZE = (512, 288)
    CONTROLS = {
        'chat_next': pygame.K_e
    }

    def __init__(self):
        self.display = pygame.display.set_mode(self.SCREEN_SIZE)
        self.clock = pygame.time.Clock()
        self.step_delta = 0
        self.player = Player(100, 100)
        old_man = OldMan(400, 10)
        self.interactable_objects = GameGroup(old_man)
        self.dynamic_objects = GameGroup(self.player)
        self.static_objects = GameGroup(GameObject(300, 130), old_man)
        self.all_objects = GameGroup(
            self.dynamic_objects,
            self.static_objects,
            self.interactable_objects
        )
        self.mode = GameModes.PLAYING
        self.textbox = None
        self.chat_cooldown = 180
        self.last_chatted = 0

    # TODO: this 'can_chat' business needs to be moved to the player model in the
    #       more general form of a 'can_interact' check that runs in 'update'
    def can_chat(self):
        return pygame.time.get_ticks() - self.last_chatted > self.chat_cooldown

    def process_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit()
            if event.type == pygame.KEYDOWN:
                ctrl_mod = (event.mod & pygame.KMOD_CTRL) > 0
                if event.key == pygame.K_q and ctrl_mod:
                    pygame.event.post(pygame.event.Event(pygame.QUIT))

                if self.mode == GameModes.CINEMATIC:
                    if event.key == self.CONTROLS['chat_next'] and self.textbox:
                        if self.textbox.finished():
                            self.textbox = None
                            self.last_chatted = pygame.time.get_ticks()
                            self.mode = GameModes.PLAYING
                        elif not self.textbox.showing_full_page():
                            self.textbox.show_full_page()
                        else:
                            self.textbox.next_page()
            if self.mode == GameModes.PLAYING:
                if event.type == constants.INTERACTION_CHAT and self.can_chat():
                    self.mode = GameModes.CINEMATIC
                    self.textbox = event.gameobject.chat(self)

    def step(self):
        self.step_delta = self.clock.tick(constants.FPS)
        self.process_events()
        # TODO: create a CutScene class that can be used to animate objects in
        #       the level, artificially move objects in the level, or call
        #       arbitrary callback methods on objects in the level, all while
        #       also managing the textboxes on screen
        # TODO: Two classes of cutscene: one that just manages the textbox and
        #       callbacks, and one that does that and also takes control of
        #       animation and movement of specific objects
        if self.mode == GameModes.PLAYING:
            self.dynamic_objects.update(self)
        elif self.textbox:
            self.textbox.update(self)
        self.draw()
        return self.step_delta

    def draw(self):
        self.display.fill((128, 128, 155))
        self.all_objects.draw(self.display)
        if self.textbox:
            self.textbox.draw(self.display)
        pygame.display.flip()
