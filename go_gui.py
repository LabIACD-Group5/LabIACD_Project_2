"""This module contains the GoGui class.
GoGui objects contain a representation of the
Chinese strategy board game Go.
"""
import os
import string
from collections import deque, namedtuple

import numpy as np
import pygame
from pygame import gfxdraw

BOARD_WIDTH = 612
WIDTH = 740
HEIGHT = int(WIDTH * 1.2)

Color = namedtuple("Color", ["r", "g", "b"])
WHITE = Color(255, 255, 255)
YELLOW = Color(220, 179, 92)
BLACK = Color(0, 0, 0)
GREY = Color(150, 150, 150)
BLUE = Color(160, 180, 220)


class GoGui:
    """Class representing the GUI of a Go board
    """

    board_width = BOARD_WIDTH
    width = WIDTH
    height = HEIGHT

    bot_pad = (width - board_width) // 2
    top_pad = height - board_width - bot_pad * 2
    hor_pad = bot_pad

    but_x = 15
    but0_y = 15
    but_width = 85
    but_height = 35
    but1_y = but0_y + but_height + 5

    def __init__(self, size):
        self.size = size
        self.spacing = self.board_width // (size - 1)
        self.buffer = self.spacing // 2
        self.stone_width = self.spacing // 2 - 1

        self.board = np.zeros((self.size, self.size), dtype=int)
        # keeps track of the parent of each group
        self.pointer = np.empty((self.size, self.size), dtype=int)
        self.pointer.fill(-1)
        self.white_groups = {}
        self.black_groups = {}
        self.newest_stone = None
        self.states = deque()

        self.running = False
        self.display = None
        self.black_stone_img = None
        self.white_stone_img = None
        self.clock = None
        self.time_elapsed = 0
        pygame.mixer.music.load(os.path.join(os.getcwd(), "assets", "sound", "tap.mp3"))

        # True for black, False for white
        self.color = True
        self.white_captured = 0
        self.black_captured = 0
        self.white_score = 0
        self.black_score = 0
        self.show_ter = False
        self.empty_groups = {}
        self.territory = None

    def check_liberty(self, row, col):
        """Checks the liberty of a stone

        Args:
            row (int): row of the stone
            col (int): column of the stone

        Returns:
            bool: True if stone has liberty, False otherwise
        """
        # checking row above
        if row != 0 and self.board[row - 1, col] == 0:
            return True
        # checking row below
        if row != self.size - 1 and self.board[row + 1, col] == 0:
            return True
        # checking col to the left
        if col != 0 and self.board[row, col - 1] == 0:
            return True
        # checking col to the right
        if col != self.size - 1 and self.board[row, col + 1] == 0:
            return True

        return False

    def check_board(self):
        """Checks the entire board for any stones that should be removed
        because they lack liberty
        """
        # checking white stones
        white_to_del = []
        check_again = None
        for key, group in self.white_groups.items():
            for pos in group:
                if pos == self.newest_stone:
                    # do not check newest placed stone yet
                    check_again = key
                    break
                if self.check_liberty(pos // self.size, pos % self.size):
                    break
            else:
                # if no stones in a group has liberty, remove entire group
                white_to_del.append(key)
                for pos in group:
                    self.white_captured += 1
                    row = pos // self.size
                    col = pos % self.size
                    self.board[row, col] = 0
                    self.pointer[row, col] = 0

        # remove group representation
        for to_del in white_to_del:
            del self.white_groups[to_del]

        # checking black stones
        black_to_del = []
        for key, group in self.black_groups.items():
            for pos in group:
                if pos == self.newest_stone:
                    # do not check newest placed stone yet
                    check_again = key
                    break
                if self.check_liberty(pos // self.size, pos % self.size):
                    break
            else:
                # if no stones in a group has liberty, remove entire group
                black_to_del.append(key)
                for pos in group:
                    self.black_captured += 1
                    row = pos // self.size
                    col = pos % self.size
                    self.board[row, col] = 0
                    self.pointer[row, col] = 0

        # remove group representation
        for to_del in black_to_del:
            del self.black_groups[to_del]

        if check_again is not None:
            # checking newest placed stone and removing it if necessary
            if self.color:
                for pos in self.black_groups[check_again]:
                    if self.check_liberty(pos // self.size, pos % self.size):
                        break
                else:
                    for pos in self.black_groups[check_again]:
                        self.black_captured += 1
                        row = pos // self.size
                        col = pos % self.size
                        self.board[row, col] = 0
                        self.pointer[row, col] = 0
                    del self.black_groups[check_again]
            else:
                for pos in self.white_groups[check_again]:
                    if self.check_liberty(pos // self.size, pos % self.size):
                        break
                else:
                    for pos in self.white_groups[check_again]:
                        self.white_captured += 1
                        row = pos // self.size
                        col = pos % self.size
                        self.board[row, col] = 0
                        self.pointer[row, col] = 0
                    del self.white_groups[check_again]

    def add_group(self, row, col, color_num):
        """Updating stones to form correct groups

        Args:
            row (int): row of the stone
            col (int): column of the stone
            color_num (int): 1 for black, -1 for white
        """
        group = self.black_groups if color_num == 1 else self.white_groups
        setted = False

        # checking whether stone above is of same color
        if row != 0 and self.board[row - 1, col] == color_num:
            parent = self.pointer[row - 1, col]
            self.pointer[row, col] = parent
            # adding stone to group of above stone
            group[parent] = group[parent].union({row * self.size + col})
            setted = True

        # checking whether stone below is of same color
        if row != self.size - 1 and self.board[row + 1, col] == color_num:
            if setted:
                # adding group of below stone to group newest stone belongs to
                prev_parent = self.pointer[row + 1, col]
                if prev_parent != parent:
                    for pos in group[prev_parent]:
                        self.pointer[pos // self.size, pos % self.size] = parent
                    group[parent] = group[parent].union(group[prev_parent])
                    del group[prev_parent]
            else:
                parent = self.pointer[row + 1, col]
                self.pointer[row, col] = parent
                # adding stone to group of below stone
                group[parent] = group[parent].union({row * self.size + col})
                setted = True

        # checking whether left stone is of same color
        if col != 0 and self.board[row, col - 1] == color_num:
            if setted:
                # adding left group to group newest stone belongs to
                prev_parent = self.pointer[row, col - 1]
                if prev_parent != parent:
                    for pos in group[prev_parent]:
                        self.pointer[pos // self.size, pos % self.size] = parent
                    group[parent] = group[parent].union(group[prev_parent])
                    del group[prev_parent]
            else:
                parent = self.pointer[row, col - 1]
                self.pointer[row, col] = parent
                # adding stone to left group
                group[parent] = group[parent].union({row * self.size + col})
                setted = True

        # checking whether right stone is of same color
        if col != self.size - 1 and self.board[row, col + 1] == color_num:
            if setted:
                # adding right group to group newest stone belongs to
                prev_parent = self.pointer[row, col + 1]
                if prev_parent != parent:
                    for pos in group[prev_parent]:
                        self.pointer[pos // self.size, pos % self.size] = parent
                    group[parent] = group[parent].union(group[prev_parent])
                    del group[prev_parent]
            else:
                parent = self.pointer[row, col + 1]
                self.pointer[row, col] = parent
                # adding stone to right group
                group[parent] = group[parent].union({row * self.size + col})
                setted = True

        # create new group of stone if there are no adjacent same color stones
        if not setted:
            parent = row * self.size + col
            self.pointer[row, col] = parent
            group[parent] = {parent}

    def check_ko(self):
        """Checking whether newest move violates Ko rule

        Returns:
            bool: True if violated, False otherwise
        """
        if len(self.states) > 2:
            _ = self.states.pop()
            board_2, pointer_2, white_2, black_2, w_cap_2, b_cap_2 = self.states.pop()

            self.states.append((board_2, pointer_2, white_2, black_2, w_cap_2, b_cap_2))
            self.states.append(_)

            return (board_2 == self.board).all()
        else:
            return False

    def fill_stone(self, pos):
        """Fill stone in position according to mouse click

        Args:
            pos (tuple): pos[0] is x position, pos[1] is y position
        """
        if (
            pos[0] > self.hor_pad - self.buffer
            and pos[0] < self.width - self.hor_pad + self.buffer
            and pos[1] > self.top_pad + self.bot_pad - self.buffer
            and pos[1] < self.height - self.bot_pad + self.buffer
        ):
            # getting row and col from x and y positino
            row = round((pos[1] - self.top_pad - self.bot_pad) / self.spacing)
            col = round((pos[0] - self.hor_pad) / self.spacing)
            if self.board[row, col] == 0:
                # if board position is unfilled
                # save state of game
                self.states.append(
                    (
                        self.board.copy(),
                        self.pointer.copy(),
                        self.white_groups.copy(),
                        self.black_groups.copy(),
                        self.white_captured,
                        self.black_captured,
                    )
                )

                # updating board
                color_num = 1 if self.color else -1
                if self.color:
                    self.board[row, col] = color_num
                else:
                    self.board[row, col] = color_num

                self.newest_stone = row * self.size + col

                # adding to group
                self.add_group(row, col, color_num)
                # remove captured stones
                self.check_board()

                # checking for Ko, prevent illegal move
                if self.check_ko() or self.board[row, col] == 0:
                    # violated Ko, move prevented
                    (
                        self.board,
                        self.pointer,
                        self.white_groups,
                        self.black_groups,
                        self.white_captured,
                        self.black_captured,
                    ) = self.states.pop()
                else:
                    pygame.mixer.music.play()
                    # did not violate Ko, move on
                    self.color = not self.color
        elif (
            pos[0] > self.but_x
            and pos[0] < self.but_x + self.but_width
            and pos[1] > self.but0_y
            and pos[1] < self.but0_y + self.but_height
        ):
            self.pass_turn()
        elif (
            pos[0] > self.but_x
            and pos[0] < self.but_x + self.but_width
            and pos[1] > self.but1_y
            and pos[1] < self.but1_y + self.but_height
        ):
            self.clear_board()

    def pass_turn(self):
        """Pass turn to opponent
        """
        # save state of game
        self.states.append(
            (
                self.board.copy(),
                self.pointer.copy(),
                self.white_groups.copy(),
                self.black_groups.copy(),
                self.white_captured,
                self.black_captured,
            )
        )
        self.color = not self.color

    def clear_board(self):
        """Clears the entire board
        """
        self.states.append(
            (
                self.board.copy(),
                self.pointer.copy(),
                self.white_groups.copy(),
                self.black_groups.copy(),
                self.white_captured,
                self.black_captured,
            )
        )
        self.board = np.zeros((self.size, self.size), dtype=int)
        # keeps track of the parent of each group
        self.pointer = np.empty((self.size, self.size), dtype=int)
        self.pointer.fill(-1)
        self.white_groups = {}
        self.black_groups = {}
        self.white_captured = 0
        self.black_captured = 0
        self.color = True

    def update_stones(self):
        """Update the stones on GUI
        """
        top_bot_padding = self.top_pad + self.bot_pad

        for row in range(self.size):
            for col in range(self.size):
                if self.board[row, col] == 1:
                    gfxdraw.aacircle(
                        self.display,
                        self.hor_pad + col * self.spacing,
                        top_bot_padding + row * self.spacing,
                        self.stone_width,
                        BLACK,
                    )
                    gfxdraw.filled_circle(
                        self.display,
                        self.hor_pad + col * self.spacing,
                        top_bot_padding + row * self.spacing,
                        self.stone_width,
                        BLACK,
                    )
                elif self.board[row, col] == -1:
                    gfxdraw.aacircle(
                        self.display,
                        self.hor_pad + col * self.spacing,
                        top_bot_padding + row * self.spacing,
                        self.stone_width,
                        WHITE,
                    )
                    gfxdraw.filled_circle(
                        self.display,
                        self.hor_pad + col * self.spacing,
                        top_bot_padding + row * self.spacing,
                        self.stone_width,
                        WHITE,
                    )

    def draw_lines(self):
        """Drawing the grid lines on GUI
        """
        thin_line = 1
        top_bot_padding = self.top_pad + self.bot_pad
        end_x = self.width - self.hor_pad
        end_y = self.height - self.bot_pad

        for i in range(self.size):
            # horizontal lines
            pygame.draw.line(
                self.display,
                BLACK,
                (self.hor_pad, i * self.spacing + top_bot_padding),
                (end_x, i * self.spacing + top_bot_padding),
                thin_line,
            )
            # vertical lines
            pygame.draw.line(
                self.display,
                BLACK,
                (self.hor_pad + i * self.spacing, top_bot_padding),
                (self.hor_pad + i * self.spacing, end_y),
                thin_line,
            )

    def draw_dots(self):
        """Drawing the small dots on GUI
        """
        top_bot_padding = self.top_pad + self.bot_pad

        for i in range(3, self.size, 6):
            for j in range(3, self.size, 6):
                gfxdraw.aacircle(
                    self.display,
                    self.hor_pad + j * self.spacing,
                    top_bot_padding + i * self.spacing,
                    3,
                    BLACK,
                )
                gfxdraw.filled_circle(
                    self.display,
                    self.hor_pad + j * self.spacing,
                    top_bot_padding + i * self.spacing,
                    3,
                    BLACK,
                )
        if self.size == 13:
            gfxdraw.aacircle(
                self.display,
                self.hor_pad + 6 * self.spacing,
                top_bot_padding + 6 * self.spacing,
                3,
                BLACK,
            )
            gfxdraw.filled_circle(
                self.display,
                self.hor_pad + 6 * self.spacing,
                top_bot_padding + 6 * self.spacing,
                3,
                BLACK,
            )

    def draw_nums(self):
        """Drawing the numbers on the side of the board
        """
        font = pygame.font.SysFont("calibri", 20)
        upper_case = string.ascii_uppercase

        for i in range(self.size):
            num = font.render(str(i + 1), True, BLACK)
            letter = font.render(upper_case[i], True, BLACK)
            increment = i * self.spacing
            letter_x = self.hor_pad + increment - letter.get_width() // 2
            height = self.height - self.bot_pad - num.get_height() // 2 - increment

            # drawing nums on left side
            self.display.blit(
                num, (self.hor_pad - self.buffer - num.get_width(), height),
            )
            # drawing nums on right side
            self.display.blit(
                num, (self.width - self.hor_pad + self.buffer, height),
            )
            # drawing letters on top
            self.display.blit(
                letter,
                (
                    letter_x,
                    self.top_pad + self.bot_pad - self.buffer - letter.get_height(),
                ),
            )
            # drawing letters on bottom
            self.display.blit(
                letter, (letter_x, self.height - self.bot_pad + self.buffer,),
            )

    def draw_captured(self, font):
        """Drawing the captured stone counts

        Args:
            font (pygame font): font to use to draw
        """
        hori_padding = self.board_width + self.spacing
        stone_width = 16

        # how many black stones have been captured
        text = font.render(str(self.black_captured), True, BLACK)
        gfxdraw.aacircle(
            self.display,
            hori_padding,
            self.top_pad - stone_width * 3 - 10,
            stone_width,
            BLACK,
        )
        gfxdraw.filled_circle(
            self.display,
            hori_padding,
            self.top_pad - stone_width * 3 - 10,
            stone_width,
            BLACK,
        )
        self.display.blit(
            text,
            (
                hori_padding + stone_width * 2,
                self.top_pad - stone_width * 3 - text.get_height() // 2 - 10,
            ),
        )
        # how many white stones have been captured
        text = font.render(str(self.white_captured), True, BLACK)
        gfxdraw.aacircle(
            self.display,
            hori_padding,
            self.top_pad - stone_width - 5,
            stone_width,
            WHITE,
        )
        gfxdraw.filled_circle(
            self.display,
            hori_padding,
            self.top_pad - stone_width - 5,
            stone_width,
            WHITE,
        )
        self.display.blit(
            text,
            (
                hori_padding + stone_width * 2,
                self.top_pad - stone_width - text.get_height() // 2 - 5,
            ),
        )

    def draw_turn(self, font):
        """Drawing which player's turn it is

        Args:
            font (pygame font): font to use to draw
        """
        color = "BLACK TURN" if self.color else "WHITE TURN"
        text = font.render(color, True, BLACK)
        self.display.blit(text, (self.width // 2 - text.get_width() // 2, 15))

    def draw_buttons(self):
        """Drawing the buttons
        """
        self.display.fill(
            BLUE, pygame.Rect(self.but_x, self.but0_y, self.but_width, self.but_height)
        )
        self.display.fill(
            BLUE, pygame.Rect(self.but_x, self.but1_y, self.but_width, self.but_height)
        )

        font = pygame.font.SysFont("timesnewroman", 22)
        text = font.render("PASS", True, BLACK)
        self.display.blit(
            text, (20, self.but0_y + (self.but_height - text.get_height()) // 2,),
        )
        text = font.render("CLEAR", True, BLACK)
        self.display.blit(
            text, (20, self.but1_y + (self.but_height - text.get_height()) // 2,),
        )

    def draw_territory(self):
        """Drawing the territory of both colors
        """
        top_bot_padding = self.top_pad + self.bot_pad

        for row in range(self.size):
            for col in range(self.size):
                if self.territory[row, col] == 1:
                    self.display.fill(
                        BLACK,
                        pygame.Rect(
                            self.hor_pad + col * self.spacing - 3,
                            top_bot_padding + row * self.spacing - 3,
                            6,
                            6,
                        ),
                    )
                elif self.territory[row, col] == -1:
                    self.display.fill(
                        WHITE,
                        pygame.Rect(
                            self.hor_pad + col * self.spacing - 3,
                            top_bot_padding + row * self.spacing - 3,
                            6,
                            6,
                        ),
                    )

    def update_gui(self):
        """Update Go board GUI
        """
        self.display.fill(GREY, pygame.Rect(0, 0, self.width, self.top_pad))
        self.display.fill(YELLOW, pygame.Rect(0, self.top_pad, self.width, self.width))

        # drawing grid
        self.draw_lines()

        # drawing dots
        self.draw_dots()

        font = pygame.font.SysFont("timesnewroman", 30)
        # drawing stones
        self.update_stones()

        # drawing nums on the sides of board
        self.draw_nums()

        # indicate the time elapsed since the game has started
        text = font.render(
            f"{(self.time_elapsed // 60):02}:{(self.time_elapsed % 60):02}",
            True,
            BLACK,
        )
        self.display.blit(text, (self.width - text.get_width() - 40, 15))

        # # fps counter
        # fps = str(int(self.clock.get_fps()))
        # fps_text = font.render(fps, True, BLACK)
        # self.display.blit(fps_text, (470, 15))

        # whose turn it is
        self.draw_turn(font)

        # drawing stones captured
        self.draw_captured(font)

        # drawing pass button
        self.draw_buttons()

        if self.show_ter:
            self.draw_territory()

        mouse_x = pygame.mouse.get_pos()[0] - self.stone_width
        mouse_y = pygame.mouse.get_pos()[1] - self.stone_width
        if pygame.mouse.get_focused():
            if self.color:
                self.display.blit(self.black_stone_img, (mouse_x, mouse_y))
            else:
                self.display.blit(self.white_stone_img, (mouse_x, mouse_y))

    def check_zero_liberty(self, row, col):
        """Checks the liberty of a stone

        Args:
            row (int): row of the stone
            col (int): column of the stone

        Returns:
            bool: True if stone has liberty, False otherwise
        """
        surrounded_by = set()
        # checking row above
        if row != 0 and self.board[row - 1, col] == 1:
            surrounded_by.add(1)
        elif row != 0 and self.board[row - 1, col] == -1:
            surrounded_by.add(-1)
        # checking row below
        if row != self.size - 1 and self.board[row + 1, col] == 1:
            surrounded_by.add(1)
        elif row != self.size - 1 and self.board[row + 1, col] == -1:
            surrounded_by.add(-1)
        # checking col to the left
        if col != 0 and self.board[row, col - 1] == 1:
            surrounded_by.add(1)
        elif col != 0 and self.board[row, col - 1] == -1:
            surrounded_by.add(-1)
        # checking col to the right
        if col != self.size - 1 and self.board[row, col + 1] == 1:
            surrounded_by.add(1)
        elif col != self.size - 1 and self.board[row, col + 1] == -1:
            surrounded_by.add(-1)

        return surrounded_by

    def check_territory(self):
        """Checking whether each group of empty intersections is part of
        a color's territory
        """
        for group in self.empty_groups.values():
            surrounded_by = set()
            for pos in group:
                new = self.check_zero_liberty(pos // self.size, pos % self.size)
                surrounded_by = surrounded_by.union(new)
                if len(surrounded_by) >= 2:
                    break
            else:
                try:
                    color = surrounded_by.pop()
                    for pos in group:
                        self.territory[pos // self.size, pos % self.size] = color
                    if color == 1:
                        self.black_score += len(group)
                    else:
                        self.white_score += len(group)
                except KeyError:
                    pass

    def group_empty(self, row, col):
        """Group all empty intersections

        Args:
            row (int): row of target intersection
            col (int): column of target intersection
        """
        group = self.empty_groups
        setted = False

        # checking whether stone above is of same color
        if row != 0 and self.board[row - 1, col] == 0:
            parent = self.pointer[row - 1, col]
            self.pointer[row, col] = parent
            # adding stone to group of above stone
            group[parent] = group[parent].union({row * self.size + col})
            setted = True

        # checking whether left stone is of same color
        if col != 0 and self.board[row, col - 1] == 0:
            if setted:
                # adding left group to group newest stone belongs to
                prev_parent = self.pointer[row, col - 1]
                if prev_parent != parent:
                    for pos in group[prev_parent]:
                        self.pointer[pos // self.size, pos % self.size] = parent
                    group[parent] = group[parent].union(group[prev_parent])
                    del group[prev_parent]
            else:
                parent = self.pointer[row, col - 1]
                self.pointer[row, col] = parent
                # adding stone to left group
                group[parent] = group[parent].union({row * self.size + col})
                setted = True

        # create new group of stone if there are no adjacent same color stones
        if not setted:
            parent = row * self.size + col
            self.pointer[row, col] = parent
            group[parent] = {parent}

    def score(self):
        """Score the game
        """
        self.empty_groups = {}
        self.territory = np.zeros((self.size, self.size), dtype=int)

        self.black_score = self.white_captured
        self.white_score = self.black_captured

        for row in range(self.size):
            for col in range(self.size):
                if self.board[row, col] == 0:
                    self.group_empty(row, col)

        self.check_territory()

        print(f"BLACK SCORE: {self.black_score}, WHITE SCORE: {self.white_score}")
        if self.black_score > self.white_score:
            print("BLACK WON")
        elif self.white_score > self.black_score:
            print("WHITE WON")
        else:
            print("TIE")

    def start_game(self):
        """Start game of Go
        """
        self.running = True
        self.display = pygame.display.set_mode((self.width, self.height))
        self.black_stone_img = pygame.image.load(
            os.path.join(os.getcwd(), "assets", "img", "black_stone.png")
        ).convert_alpha()
        self.white_stone_img = pygame.image.load(
            os.path.join(os.getcwd(), "assets", "img", "white_stone.png")
        ).convert_alpha()
        self.clock = pygame.time.Clock()
        pygame.mouse.set_visible(False)
        pygame.display.set_caption("GO")
        start_time = pygame.time.get_ticks()

        # main loop of Go
        while self.running:
            self.time_elapsed = int((pygame.time.get_ticks() - start_time) / 1000)

            for event in pygame.event.get():
                # enable closing of display
                if event.type == pygame.QUIT:
                    self.running = False
                    self.score()
                    return
                # getting position of mouse
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.show_ter = False
                    mouse_pos = pygame.mouse.get_pos()
                    self.fill_stone(mouse_pos)
                if event.type == pygame.KEYDOWN:
                    keys = pygame.key.get_pressed()
                    if keys[pygame.K_p]:
                        self.pass_turn()
                    if keys[pygame.K_LCTRL] and keys[pygame.K_z]:
                        self.show_ter = False
                        try:
                            (
                                self.board,
                                self.pointer,
                                self.white_groups,
                                self.black_groups,
                                self.white_captured,
                                self.black_captured,
                            ) = self.states.pop()
                            self.color = not self.color
                        except IndexError:
                            pass
                    if keys[pygame.K_LSHIFT] and keys[pygame.K_c]:
                        self.clear_board()
                    if keys[pygame.K_SPACE]:
                        self.show_ter = True
                        self.score()

            self.clock.tick(60)
            self.update_gui()
            pygame.display.update()


if __name__ == "__main__":
    pygame.mixer.init(2000, -16, 2, 32)
    pygame.init()
    go_gui = GoGui(7)
    go_gui.start_game()
    pygame.quit()
