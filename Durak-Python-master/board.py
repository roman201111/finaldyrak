import pygame
from constants import *

from math import log


class Board:
    def __init__(self, pygame_clock, deck):
        # Get clock so we can do dt animation math
        self.pygame_clock = pygame_clock

        # mouse position
        self.mx, self.my = 0, 0
        self.dt = 0
        self.click = False
        self.deck = deck
        self.attack_list = []
        self.defense_list = []
        self.index_list = []
        self.card_pos = {0: []}

        # Ігрове поле починається порожнім
        # attack_list та defense_list будуть заповнюватися під час гри
        # USED IF WE DON'T KNOW WHERE TO GO
        self.found_size = False

        self.back_image = self.deck.cards_list[-1].current_image.copy()

        # Розміщуємо колоду праворуч від центру (синхронізовано з durak_game.py)
        self.deck_x = (SCREENWIDTH // 2) + 150
        self.deck_y = (SCREENHEIGHT // 2) - (self.back_image.get_rect().size[1] // 2)

        # Позиція козирної карти: під колодою на 35% та трохи зміщена праворуч
        card_height = self.back_image.get_rect().size[1]
        card_width = self.back_image.get_rect().size[0]
        self.trump_x = self.deck_x + (card_width * 0.3)
        self.trump_y = self.deck_y + (card_height * 0.35)

    def get_card_indexes(self, card_count_x, card_count_y):
        card_width, card_height = self.back_image.get_rect().size
        card_gap = 110

        # Спростимо логіку для 2 гравців - карти розміщуються горизонтально
        bottom_row_y = (self.deck_y + card_height) + (
                (SCREENHEIGHT - card_height // 2) - (self.deck_y + card_height) - card_height) // 2

        for c_index in range(1, card_count_x + 1):
            if c_index == 1:
                bottom_row_x = self.deck_x - card_width // 2
                temp_pos = (bottom_row_x, bottom_row_y, 0)
                self.card_pos.update({c_index: [temp_pos]})
            elif c_index % 2 == 0:
                bottom_row_x = self.deck_x - card_width - card_gap // 4
                position_list = self.card_pos.get(c_index - 2).copy()
                for i in range(len(position_list), c_index):
                    if i == 0:
                        temp_x = bottom_row_x
                    elif i % 2 == 0:
                        temp_x = bottom_row_x - ((card_width + card_gap // 2) * (i - i // 2))
                    else:
                        temp_x = bottom_row_x + ((card_width + card_gap // 2) * (i - i // 2))
                    temp_pos = (temp_x, bottom_row_y, 0)
                    position_list.append(temp_pos)
                self.card_pos.update({c_index: position_list})
            elif c_index % 2 == 1:
                bottom_row_x = self.deck_x - card_width // 2
                position_list = self.card_pos.get(c_index - 2).copy()
                for i in range(len(position_list), c_index):
                    if i % 2 == 1:
                        # to the right of our first attack
                        temp_x = bottom_row_x + ((card_width + card_gap // 2) * (i - i // 2))
                    else:
                        if i != 0:
                            temp_x = bottom_row_x - ((card_width + card_gap // 2) * (i - i // 2))
                        else:
                            temp_x = bottom_row_x
                    temp_pos = (temp_x, bottom_row_y, 0)
                    position_list.append(temp_pos)
                self.card_pos.update({c_index: position_list})
        print(self.card_pos)

    def update(self):
        self.dt = self.pygame_clock.tick(60) / 1000.0
        self.mx, self.my = pygame.mouse.get_pos()

    def render(self, screen):
        # GOAL->Draw for each space for each row given the size
        card_width, card_height = self.back_image.get_rect().size
        card_gap = 110

        # GET THE WIDTH POSSIBLE - зменшені розрахунки для 2 гравців
        build_size_width, build_size_height = card_width, card_width
        card_count_x = 1
        card_count_y = 1
        while not self.found_size:
            found_x_card_count = build_size_width + card_gap + card_width >= SCREENWIDTH - (2 * card_height // 3)
            # Для 2 гравців не потрібно багато рядів
            found_y_card_count = True  # Завжди використовуємо один ряд
            if found_x_card_count:
                self.found_size = True
                print("SCREENWIDTH", SCREENWIDTH - (2 * card_height // 3))
                print("build_size_width", build_size_width)
                print(card_count_x, "cards can be played horizontally")
                print(card_width + card_gap)
                self.get_card_indexes(card_count_x, card_count_y)
            if not found_x_card_count:
                build_size_width = build_size_width + card_gap // 2 + card_width
                card_count_x += 1

        attack_card_points = self.card_pos[len(self.attack_list)]

        # Positions to draw
        for i, c in enumerate(self.attack_list):
            temp_screen = pygame.transform.rotate(c.front_image, attack_card_points[i][2])
            screen.blit(temp_screen, (attack_card_points[i][0], attack_card_points[i][1]))

        for i, c in enumerate(self.defense_list):
            if i < len(attack_card_points):
                temp_screen = pygame.transform.rotate(c.front_image, attack_card_points[i][2])
                screen.blit(temp_screen, (attack_card_points[i][0] + 13, attack_card_points[i][1] + 13))

    def mouse_click(self):
        self.click = True

    def get_menu_click(self):
        # do something like move card if clicked?
        return 0