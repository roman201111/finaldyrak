import pygame
from constants import *

from math import log


class Menu:
    def __init__(self, pygame_clock):
        # Get clock so we can do dt animation math
        self.pygame_clock = pygame_clock

        # load fonts, for now assume same fonts, different variables
        self.titleFont = pygame.font.Font('Res/Font/CozetteVector.ttf', 128)
        self.buttonFont = pygame.font.Font('Res/Font/CozetteVector.ttf', 64)

        # create all text objects we'll need to draw
        self.titleText = self.titleFont.render("Дурак онлайн", False, (0, 0, 0)).convert()
        self.startText = self.buttonFont.render("Грати онлайн", False, (0, 0, 0)).convert()
        self.optionsText = self.buttonFont.render("Налаштування", False, (0, 0, 0)).convert()

        self.startTextSize = self.buttonFont.size("Грати онлайн")
        self.optionsTextSize = self.buttonFont.size("Налаштування")

        # aspirational button_width, button_x location defined by ScreenWidth
        button_width = SCREENWIDTH - (SCREENWIDTH // 2)
        self.button_x = button_width - button_width // 2

        self.titleX = SCREENWIDTH // 2 - (self.titleFont.size("Дурак онлайн")[0] // 2)
        self.titleY = -260

        # create buttons for our menu
        self.startButton = pygame.Rect(SCREENWIDTH + 200, 200, button_width, 75)
        self.optionsButton = pygame.Rect(SCREENWIDTH + 200, 350, button_width, 75)

        self.button_frame_count = 0
        self.title_frame_count = 0

        # mouse position
        self.mx = 0
        self.my = 0

        self.dt = 0

        self.state = MENU_SCREEN
        self.click = False

        # Кнопки для меню налаштувань
        self.music_button = pygame.Rect(SCREENWIDTH + 200, 200, button_width, 75)
        self.back_button = pygame.Rect(SCREENWIDTH + 200, 350, button_width, 75)

        # Текст для кнопок налаштувань
        self.music_on_text = self.buttonFont.render("Музика: УВІМК", False, (0, 0, 0)).convert()
        self.music_off_text = self.buttonFont.render("Музика: ВИМК", False, (0, 0, 0)).convert()
        self.back_text = self.buttonFont.render("Назад", False, (0, 0, 0)).convert()

        self.music_on_size = self.buttonFont.size("Музика: УВІМК")
        self.music_off_size = self.buttonFont.size("Музика: ВИМК")
        self.back_text_size = self.buttonFont.size("Назад")

        # Стан музики (буде оновлюватись з MainController)
        self.music_enabled = True

    def set_music_state(self, music_enabled):
        """Метод для синхронізації стану музики з MainController"""
        self.music_enabled = music_enabled

    def update(self):
        self.dt = self.pygame_clock.tick(60) / 1000.0
        if self.state == MENU_SCREEN:
            self.animate_buttons_on_screen()
            self.animate_title_on_screen()
        elif self.state == OPTION_SCREEN:
            self.animate_options_on_screen()
            self.animate_title_on_screen()  # Заголовок також показується в налаштуваннях
        self.mx, self.my = pygame.mouse.get_pos()

    def animate_buttons_on_screen(self):
        """Анімація появи кнопок головного меню"""
        self.button_frame_count += 1
        target_x = self.button_x

        # Анімація кнопки "Грати онлайн"
        if self.startButton.x > target_x:
            move_distance = max(5, (self.startButton.x - target_x) // 8)
            self.startButton.x -= move_distance

        # Анімація кнопки "Налаштування" з затримкою
        if self.button_frame_count > 10 and self.optionsButton.x > target_x:
            move_distance = max(5, (self.optionsButton.x - target_x) // 8)
            self.optionsButton.x -= move_distance

    def animate_options_on_screen(self):
        """Анімація появи кнопок меню налаштувань"""
        target_x = self.button_x

        # Анімація кнопки музики
        if self.music_button.x > target_x:
            move_distance = max(5, (self.music_button.x - target_x) // 8)
            self.music_button.x -= move_distance

        # Анімація кнопки "Назад"
        if self.back_button.x > target_x:
            move_distance = max(5, (self.back_button.x - target_x) // 8)
            self.back_button.x -= move_distance

    def animate_title_on_screen(self):
        """Анімація появи заголовка"""
        self.title_frame_count += 1
        target_y = 50

        if self.titleY < target_y:
            move_distance = max(2, (target_y - self.titleY) // 10)
            self.titleY += move_distance

    def animate_off(self):
        """Анімація зникнення меню"""
        # Переміщуємо всі елементи за межі екрану
        self.titleY -= 15
        self.startButton.x += 20
        self.optionsButton.x += 20
        self.music_button.x += 20
        self.back_button.x += 20

        # Повертаємо новий стан коли анімація завершена
        if self.startButton.x > SCREENWIDTH:
            return GAME_SCREEN
        return MENU_SCREEN

    def render(self, screen):
        if self.state == MENU_SCREEN:
            # Рендер головного меню
            screen.blit(self.titleText, (self.titleX, self.titleY))
            pygame.draw.rect(screen, (255, 255, 255), self.startButton)
            pygame.draw.rect(screen, (0, 0, 0), self.startButton, 2)  # Рамка
            screen.blit(self.startText,
                        (self.startButton.centerx - self.startTextSize[0] // 2, self.startButton.y + 15))

            pygame.draw.rect(screen, (255, 255, 255), self.optionsButton)
            pygame.draw.rect(screen, (0, 0, 0), self.optionsButton, 2)  # Рамка
            screen.blit(self.optionsText,
                        (self.optionsButton.centerx - self.optionsTextSize[0] // 2, self.optionsButton.y + 15))

            # Додаємо підказку про онлайн-режим
            info_font = pygame.font.Font('Res/Font/CozetteVector.ttf', 32)
            info_text = info_font.render("Мережева гра для 2 гравців", False, (100, 100, 100))
            info_rect = info_text.get_rect(center=(SCREENWIDTH // 2, SCREENHEIGHT - 100))
            screen.blit(info_text, info_rect)

        elif self.state == OPTION_SCREEN:
            # Рендер меню налаштувань
            screen.blit(self.titleText, (self.titleX, self.titleY))

            # Кнопка музики
            pygame.draw.rect(screen, (255, 255, 255), self.music_button)
            pygame.draw.rect(screen, (0, 0, 0), self.music_button, 2)  # Рамка
            if self.music_enabled:
                screen.blit(self.music_on_text,
                            (self.music_button.centerx - self.music_on_size[0] // 2, self.music_button.y + 15))
            else:
                screen.blit(self.music_off_text,
                            (self.music_button.centerx - self.music_off_size[0] // 2, self.music_button.y + 15))

            # Кнопка "Назад"
            pygame.draw.rect(screen, (255, 255, 255), self.back_button)
            pygame.draw.rect(screen, (0, 0, 0), self.back_button, 2)  # Рамка
            screen.blit(self.back_text,
                        (self.back_button.centerx - self.back_text_size[0] // 2, self.back_button.y + 15))

    def mouse_click(self):
        """Обробка кліку миші"""
        self.click = True

    def get_menu_click(self):
        """Перевіряє клік по кнопках головного меню"""
        if not self.click:
            return None

        self.click = False

        if self.startButton.collidepoint(self.mx, self.my):
            return GAME_SCREEN
        elif self.optionsButton.collidepoint(self.mx, self.my):
            self.state = OPTION_SCREEN
            return OPTION_SCREEN

        return None

    def get_options_click(self):
        """Перевіряє клік по кнопках меню налаштувань"""
        if not self.click:
            return None

        self.click = False

        if self.music_button.collidepoint(self.mx, self.my):
            return "toggle_music"
        elif self.back_button.collidepoint(self.mx, self.my):
            self.state = MENU_SCREEN
            # Скидаємо позиції кнопок для повторної анімації
            self.reset_button_positions()
            return MENU_SCREEN

        return None

    def reset_button_positions(self):
        """Скидає позиції кнопок для повторної анімації"""
        button_width = SCREENWIDTH - (SCREENWIDTH // 2)

        self.startButton.x = SCREENWIDTH + 200
        self.optionsButton.x = SCREENWIDTH + 200
        self.music_button.x = SCREENWIDTH + 200
        self.back_button.x = SCREENWIDTH + 200

        self.button_frame_count = 0
        self.title_frame_count = 0
        self.titleY = -260