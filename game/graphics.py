import pygame

from pygame import freetype
from xml.etree import ElementTree as ET
from collections import deque
from itertools import count


# TODO: add support for static and dynamic overlays, which are just sprites or
#       images to render on top of the current sprite
class Animator():
    """A class for providing the correct image with which to animate a sprite."""

    default_frame_timestep = 100
    default_sprite_size = (32, 32)

    def __init__(self, animations, spritesheets=[], frame_map=[]):
        if len(frame_map) > 0 and len(spritesheets) == 0:
            raise ValueError("Cannot provide a frame map without a spritesheet.")
        # Load and optimize spritesheets for fast blitting
        self.spritesheets = []
        for sheet in spritesheets:
            if type(sheet) == str:
                sheet = pygame.image.load(sheet)
            self.spritesheets.append(sheet.convert_alpha())
        frames = []
        for mapping in frame_map:
            # Create a rect representing the location of the sprite for the frame
            sprite_location = mapping[0:2]
            sprite_size = self.default_sprite_size
            if len(mapping) > 3:
                sprite_size = mapping[2:4]
            sprite_offset = pygame.Rect(sprite_location, sprite_size)

            # Select the spritesheet to cut the frame from
            sheet_index = 0
            if len(mapping) == 5:
                sheet_index = mapping[4] - 1
            elif len(mapping) == 3:
                sheet_index = mapping[2] - 1
            if sheet_index >= len(self.spritesheets):
                error_mesg = "Requested a sprite from sheet {}, " + \
                "but only {} sheets were found"
                error_mesg = error_mesg.format(sheet_index + 1, len(self.spritesheets))
                raise ValueError(error_mesg)

            # Cut the frame
            frame = self.spritesheets[sheet_index].subsurface(sprite_offset)
            frames.append(frame)

        self.animations = dict()
        for animation_name, encoded_frames in animations.items():
            decoded_frames = []
            for eframe in encoded_frames:
                decoded_frame = eframe
                if type(eframe) == int:
                    decoded_frame = frames[eframe - 1]
                decoded_frames.append(decoded_frame)
            self.animations[animation_name] = decoded_frames

        self.current_animation = None
        self.time_elapsed = 0

    def play(self, animation, reset=True):
        """Begin playing an animation."""
        if animation not in self.animations.keys():
            raise ValueError("'{}' is not an existing animation".format(animation))

        # unless the current animation was played with the reset flag set to False,
        # we should start playing the animation over from the beginning
        if not (self.current_animation == animation and not reset):
            self.time_elapsed = 0
        self.current_animation = animation
        return self.get_current_frame()

    def get_current_frame(self):
        frame_number = self.time_elapsed // self.default_frame_timestep
        return self.animations[self.current_animation][frame_number]

    def advance_animation(self, ms):
        total_animation_time = len(self.animations[self.current_animation]) * self.default_frame_timestep
        self.time_elapsed = (self.time_elapsed + ms) % total_animation_time
        return self.get_current_frame()


class TextBoxPage():
    def only_with_choices(func):
        def wrapper(self, *args, **kwargs):
            if len(self.choices):
                return func(self, *args, **kwargs)
        return wrapper

    def __init__(
        self, raw_text=None, characters_per_second=30, text_color=(255,255,255),
        line_separation=0, text_size=14, choices=dict()
    ):
        self.text = ''
        if raw_text != None:
            self.text = raw_text
        self.cps = characters_per_second
        self.font = freetype.SysFont('', text_size)
        self.text_color = text_color
        self.line_separation = line_separation
        self.choices = choices
        self.choice_keys = list(self.choices.keys())
        self.current_choice = 0 if len(self.choices) else None

    @only_with_choices
    def make_choice(self):
        return self.choices[self.choice_keys[self.current_choice]]

    @only_with_choices
    def next_choice(self):
        self.current_choice = (self.current_choice + 1) % len(self.choices)

    @only_with_choices
    def prev_choice(self):
        self.current_choice = (self.current_choice - 1) % len(self.choices)

    def draw_choices(self, surface):
        separation = surface.get_width() // (len(self.choice_keys) + 1)
        iterator = count(separation, separation)
        for choice_text, x, i in zip(self.choice_keys, iterator, count()):
            style = 0
            if i == self.current_choice:
                style = (freetype.STYLE_STRONG | freetype.STYLE_UNDERLINE)
            text_rect = self.font.get_rect(choice_text, style=style)
            self.font.render_to(
                surface, (x - (text_rect.width // 2), 0), None,
                fgcolor=(self.text_color), style=style
            )


class TextBox():
    SIZE = (480, 80)
    BACKGROUND_COLOR = (0, 0, 110)
    LOCATION = (16, 192)
    RESTING_PERIOD = 200
    DEFAULT_MARGIN = (8, 8)

    def skip_if_resting(func):
        def wrapper(self, *args, **kwargs):
            if self.is_resting():
                return False
            return func(self, *args, **kwargs)
        return wrapper

    def __init__(self, pages=[], pagefile=None, text_margin=None):
        self.pages = pages
        if pagefile:
            self.pages = self.parse_pagefile(pagefile)
        self.current_page = 0
        self.time_displaying_page = 0
        self.text = ""
        if text_margin == None:
            self.text_margin = self.DEFAULT_MARGIN
        else:
            self.text_margin = text_margin
        self.background = pygame.Surface(self.SIZE)
        self.choice_stack = deque()
        # if we enter a question branch without totally exploring the dialog
        # at the current depth, we record that depth here, for rebounding to
        self.rebound_depth = None

    def parse_pagefile(self, pagefile):
        # TODO: add support for adding attributes to each page
        root = ET.parse(pagefile).getroot()
        assert root.tag == "DialogBox"
        return self._enumerate_pages(root.findall("Page"))

    def _enumerate_pages(self, page_nodes):
        pages = []
        for page_node in page_nodes:
            choices = { }
            terminal_choice_pages = page_node.findall("Page")
            choice_nodes = page_node.findall("Choice")
            for choice_node in choice_nodes:
                if len(terminal_choice_pages) == 0:
                    choice_pages = self._enumerate_pages(choice_node.findall("Page"))
                else:
                    choice_pages = self._enumerate_pages(terminal_choice_pages)
                choices[choice_node.text.strip()] = choice_pages
            page = TextBoxPage(
                raw_text = page_node.text.strip(),
                choices = choices
            )
            pages.append(page)
        return pages

    def update(self, gamestate):
        self.time_displaying_page += gamestate.step_delta
        page_text = self.get_page_text()
        cps = self.get_current_cps()
        render_end = (cps * self.time_displaying_page) // 1000
        render_end = min(len(page_text), render_end)
        self.text = page_text[0:render_end]

    def draw(self, display):
        self.background.fill(self.BACKGROUND_COLOR)
        self.draw_choices_to_background()
        self.draw_text_to_background()
        display.blit(self.background, self.LOCATION)

    def draw_text_to_background(self):
        # TODO: if the page has choices, make sure to stop early to leave space
        page = self.pages[self.current_page]
        x, y = self.text_margin
        leftmost, rightmost = x, self.background.get_width() - x
        bottommost = self.background.get_height() - y
        space = page.font.get_rect(' ')
        font_height = page.font.get_sized_height()
        carriage_return = page.line_separation + font_height
        for word in self.text.split(' '):
            bounds = page.font.get_rect(word)
            if bounds.width + bounds.x + x > rightmost:
                x, y = leftmost, y + carriage_return
            # TODO: cut off the text if it's too long
            # TODO: based on the height of the text vs the font's actual height,
            #       calculate how far down you should render it to align all the
            #       words to a baseline, rather than having them top-aligned.
            page.font.render_to(
                self.background, (x, y + (font_height - bounds.y)), None,
                fgcolor=(page.text_color)
            )
            x += bounds.width + space.width

    def draw_choices_to_background(self):
        page = self.pages[self.current_page]
        if len(page.choices):
            width = self.background.get_width() - (2 * self.text_margin[0])
            height = page.font.get_sized_height()
            choice_box = pygame.Surface((width, height), flags=pygame.SRCALPHA)
            choice_box.fill((0, 0, 0, 0))
            page.draw_choices(choice_box)
            offset = (
                self.text_margin[0],
                self.background.get_height() - (self.text_margin[1] + height)
            )
            self.background.blit(choice_box, offset)

    def get_page_text(self):
        return self.pages[self.current_page].text

    def get_current_cps(self):
        page = self.pages[self.current_page]
        return page.cps

    def get_minimum_time_to_show_full_page(self):
        return len(self.pages[self.current_page].text) * self.get_current_cps() * 1000

    # TODO: if the page had hooks to run based on the decision, return them
    def make_choice(self):
        page = self.pages[self.current_page]
        if not self.showing_last_page():
            self.rebound_depth = len(self.choice_stack)
        self.choice_stack.append((
            self.current_page,
            self.pages,
            self.rebound_depth
        ))
        self.time_displaying_page = 0
        self.current_page = 0
        self.pages = page.make_choice()

    def unmake_choice(self):
        previous = self.choice_stack.pop()
        self.current_page, self.pages, self.rebound_depth = previous

    def rebound(self):
        """
        Percolate up the choice stack until we reach a dialogue branch that
        hasn't been fully explored, yet.
        """
        while self.rebound_depth is not None and len(self.choice_stack) != self.rebound_depth:
            self.unmake_choice()

    def goto_page(self, page_num):
        if page_num != self.current_page:
            self.pages[self.current_page] # throw error if nonexistent page
            self.current_page = page_num
            self.time_displaying_page = 0

    @skip_if_resting
    def next_page(self):
        if self.showing_last_page() and len(self.choice_stack):
            self.rebound()

        if not self.showing_last_page():
            self.goto_page(self.current_page + 1)

    @skip_if_resting
    def prev_page(self):
        if self.current_page > 0:
            self.goto_page(self.current_page - 1)

    @skip_if_resting
    def next_choice(self):
        self.pages[self.current_page].next_choice()

    @skip_if_resting
    def prev_choice(self):
        self.pages[self.current_page].prev_choice()

    def show_full_page(self):
        cps = self.get_current_cps()
        time_to_full = self.get_minimum_time_to_show_full_page()
        self.time_displaying_page = max(time_to_full, self.time_displaying_page)

    def showing_full_page(self):
        return len(self.text) == len(self.pages[self.current_page].text)

    def showing_last_page(self):
        return self.current_page == len(self.pages) - 1

    @skip_if_resting
    def finished(self):
        decision_tree_expended = self.rebound_depth == None or len(self.choice_stack) == 0
        return self.showing_last_page() and self.showing_full_page() and decision_tree_expended

    def is_resting(self):
        """Return whether the page finished displaying within the resting period."""
        progress = self.time_displaying_page - self.get_minimum_time_to_show_full_page()
        return progress > 0 and progress <= self.RESTING_PERIOD

    def is_choosing(self):
        page = self.pages[self.current_page]
        return len(page.choices) > 0
