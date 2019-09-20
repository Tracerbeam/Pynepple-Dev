import pygame

from xml.etree import ElementTree as ET

from .constants import GameModes

class CutSceneCue():
    def __init__(self):
        self.period = 0
        self.textbox = None
        self.autocontinue = False
        self.hooks = dict()

    def update(self, period=None, textbox=None, autocontinue=None, hooks=None):
        if textbox is not None:
            self.textbox = textbox
        if period is not None:
            self.period = period
        if autocontinue is not None:
            self.autocontinue = autocontinue
        if hooks is not None:
            self.hooks = hooks

class CutScene():
    CONTROLS = {
        'chat_next': pygame.K_e,
        'chat_choose': pygame.K_q,
        'chat_choice_left': pygame.K_a,
        'chat_choice_right': pygame.K_d,
        'cutscene_next': pygame.K_e
    }

    def __init__(self, cue_list=[], actors=dict(), cutscene_file=None):
        self.actors = actors
        self.cues = dict()
        self.cue_list = cue_list
        self.current_cue = None
        self.time_playing_cue = None
        self.finished = None
        if cutscene_file is not None:
            self._load_from_file(cutscene_file)

    def _load_from_file(self, cutscene_file):
        root = ET.parse(cutscene_file).getroot()
        # TODO

    def add_actor(self, actor_name, *gameobjects):
        gameobjects = set(gameobjects)
        if actor_name not in self.actors:
            self.actors[actor_name] = gameobjects
        else:
            self.actors[actor_name] = self.actors[actor_name].union(gameobjects)

    def remove_actor(self, actor_name):
        if actor_name in self.actors:
            del self.actors[actor_name]

    def edit_cue(self, cue_name, cue_period, **kwargs):
        if cue_name not in self.cues:
            self.cues[cue_name] = CutSceneCue()
        self.cues[cue_name].update(period=cue_period, **kwargs)

    def get_cue(self):
        cue = None
        if self.current_cue is not None:
            print(self.current_cue, self.time_playing_cue)
            cue = self.cues[self.cue_list[self.current_cue]]
        return cue

    def start(self):
        """Begin playing the cutscene."""
        if len(self.cue_list) == 0:
            raise Exception("Cannot play a cutscene without any cues.")

        self.current_cue = 0
        self.time_playing_cue = 0
        self.finished = False

    def update(self, gamestate):
        # TODO: add the ability to add programmatic hooks to cues, that
        #       have access to the gamestate
        cue = self.get_cue()
        self.time_playing_cue += gamestate.step_delta

        should_advance = (
            (cue.autocontinue or
            self.CONTROLS['cutscene_next'] in gamestate.keydowns) and
            (not cue.textbox or cue.textbox.finished())
        )
        if self.time_playing_cue >= cue.period and should_advance:
            if self.current_cue == len(self.cue_list) - 1: # we're on the last cue
                self.finished = True
            else:
                # update to the next cue with rollover
                self.current_cue += 1
                if cue.textbox:
                    self.time_playing_cue = 0
                else:
                    self.time_playing_cue -= cue.period
                cue = self.get_cue()

        if cue.textbox:
            cue.textbox.update(gamestate)
            if cue.textbox.is_choosing():
                if self.CONTROLS['chat_choose'] in gamestate.keydowns:
                    cue.textbox.make_choice()
                elif self.CONTROLS['chat_choice_left'] in gamestate.keydowns:
                    cue.textbox.prev_choice()
                elif self.CONTROLS['chat_choice_right'] in gamestate.keydowns:
                    cue.textbox.next_choice()
            elif self.CONTROLS['chat_next'] in gamestate.keydowns:
                if not cue.textbox.showing_full_page():
                    cue.textbox.show_full_page()
                elif not cue.textbox.is_choosing() and not cue.textbox.finished():
                    cue.textbox.next_page()

        for actor_name, hooks in cue.hooks.items():
            for actor in self.actors[actor_name]:
                for hook_method, args, kwargs in hooks:
                    actor.__getattribute__('hook_' + hook_method)(*args, **kwargs)

    def draw(self, display):
        cue = self.get_cue()
        if cue.textbox:
            cue.textbox.draw(display)
