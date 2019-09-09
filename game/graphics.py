import pygame

from pygame import freetype
from xml.etree import ElementTree as ET


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
    def __init__(
        self, raw_text=None, characters_per_second=30, text_color=(255,255,255),
        line_separation=0, text_size=14
    ):
        self.text = ''
        if raw_text != None:
            self.text = raw_text
        self.cps = characters_per_second
        self.font = freetype.SysFont('', text_size)
        self.text_color = text_color
        self.line_separation = line_separation


class TextBox():
    SIZE = (480, 80)
    BACKGROUND_COLOR = (0, 0, 110)
    LOCATION = (16, 192)
    RESTING_PERIOD = 200

    def skip_if_resting(func):
        def wrapper(self, *args, **kwargs):
            if self.is_resting():
                return False
            return func(self, *args, **kwargs)
        return wrapper

    def __init__(self, pages=[], pagefile=None, text_margin=(0,0)):
        self.pages = pages
        if pagefile:
            self.pages.extend(self.parse_pagefile(pagefile))
        self.current_page = 0
        self.time_displaying_page = 0
        self.text = ""
        self.text_margin = text_margin
        self.background = pygame.Surface(self.SIZE)

    # TODO: add support for multiple choice 
    def parse_pagefile(self, pagefile):
        # TODO: add support for adding attributes to each page
        root = ET.parse(pagefile).getroot()
        assert root.tag == "DialogBox"

        pages = []
        for page_node in root.getchildren():
            page = TextBoxPage(raw_text = page_node.text.strip())
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
        page = self.pages[self.current_page]
        x, y = self.text_margin
        leftmost, rightmost = x, self.background.get_width() - x
        bottommost = self.background.get_height() - y
        space = page.font.get_rect(' ')
        carriage_return = page.line_separation + page.font.get_sized_height()
        for word in self.text.split(' '):
            bounds = page.font.get_rect(word)
            if bounds.width + bounds.x + x > rightmost:
                x, y = leftmost, y + carriage_return
            # TODO: cut off the word if it's too wide
            # TODO: cut off the text if it's too long
            # TODO: based on the height of the text vs the font's actual height,
            #       calculate how far down you should render it to align all the
            #       words to a baseline, rather than having them top-aligned.
            page.font.render_to(self.background, (x,y), None, fgcolor=(page.text_color))
            x += bounds.width + space.width
        display.blit(self.background, self.LOCATION)

    def get_page_text(self):
        return self.pages[self.current_page].text

    def get_current_cps(self):
        page = self.pages[self.current_page]
        return page.cps

    def get_minimum_time_to_show_full_page(self):
        return len(self.pages[self.current_page].text) * self.get_current_cps() * 1000

    def goto_page(self, page_num):
        if page_num != self.current_page:
            self.pages[page_num] # throw error if nonexistent page
            self.current_page = page_num
            self.time_displaying_page = 0

    @skip_if_resting
    def next_page(self):
        if self.current_page < len(self.pages):
            self.goto_page(self.current_page + 1)

    @skip_if_resting
    def prev_page(self):
        if self.current_page > 0:
            self.goto_page(self.current_page - 1)

    def show_full_page(self):
        cps = self.get_current_cps()
        time_to_full = self.get_minimum_time_to_show_full_page()
        self.time_displaying_page = max(time_to_full, self.time_displaying_page)

    def showing_full_page(self):
        return len(self.text) == len(self.pages[self.current_page].text)

    @skip_if_resting
    def finished(self):
        showing_last_page = self.current_page == len(self.pages) - 1
        return showing_last_page and self.showing_full_page()

    def is_resting(self):
        """Return whether the page finished displaying within the resting period."""
        progress = self.time_displaying_page - self.get_minimum_time_to_show_full_page()
        return progress > 0 and progress <= self.RESTING_PERIOD
