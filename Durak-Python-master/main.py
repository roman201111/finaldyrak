import time
import pygame
from pygame.locals import *

# Local imports
from constants import *
from durak_game import NetworkDurak
from menu import Menu


class MainController:
    def __init__(self):
        # Create pygame instance, set screen, clock
        pygame.init()
        pygame.mixer.init()
        pygame.display.set_caption("Дурак онлайн")
        self.screen = pygame.display.set_mode(SCREENSIZE, 0, 32)
        self.clock = pygame.time.Clock()
        self.clock.tick(60)

        self.debugFont = pygame.font.SysFont("Arial", 18)

        # screen_state decides what the screen should be aspirationally displaying
        self.screen_state = MENU_SCREEN
        # animate_state decides what we are currently animating
        self.animate_state = MENU_SCREEN

        self.game_created = False

        self.background, self.game_background, self.game = None, None, None
        self.menu = Menu(self.clock)

        self.music_enabled = True

        self.set_background()
        self.set_game_background()
        self.load_background_music()

    def set_background(self):
        try:
            # Завантажуємо картинку для меню
            self.background = pygame.image.load('Res/background.jpg').convert()
            # Масштабуємо під розмір екрану
            self.background = pygame.transform.scale(self.background, SCREENSIZE)
        except pygame.error:
            # Якщо картинка не знайдена, залишаємо зелений фон
            print("Фонова картинка не знайдена, використовується зелений колір")
            self.background = pygame.surface.Surface(SCREENSIZE)
            self.background.fill(GREEN)

    def set_game_background(self):
        try:
            # Завантажуємо картинку для гри
            self.game_background = pygame.image.load('Res/background2.jpg').convert()
            # Масштабуємо під розмір екрану
            self.game_background = pygame.transform.scale(self.game_background, SCREENSIZE)
        except pygame.error:
            # Якщо картинка не знайдена, використовуємо темно-зелений фон
            print("Ігровий фон не знайдений, використовується темно-зелений колір")
            self.game_background = pygame.surface.Surface(SCREENSIZE)
            self.game_background.fill((5, 70, 25))  # Темно-зелений колір для гри

    def load_background_music(self):
        """Завантажує та запускає фонову музику"""
        try:
            pygame.mixer.music.load('Res/sounds/background_music.mp3')
            pygame.mixer.music.set_volume(0.5)
            if self.music_enabled:
                pygame.mixer.music.play(-1)
            print("Фонова музика успішно завантажена")
        except pygame.error as e:
            print(f"Помилка завантаження музики: {e}")
        except FileNotFoundError:
            print("Файл background_music.mp3 не знайдений")

    def toggle_music(self):
        """Перемикач музики вкл/викл"""
        self.music_enabled = not self.music_enabled
        if self.music_enabled:
            if not pygame.mixer.music.get_busy():
                try:
                    pygame.mixer.music.play(-1)
                except:
                    print("Не вдалося запустити музику")
        else:
            pygame.mixer.music.stop()

    # Start Game - тепер завжди мережева гра
    def start_game(self):
        self.game = NetworkDurak(self.clock, self)

    # Update
    def update(self):
        self.check_events()
        if self.screen_state == MENU_SCREEN:
            self.menu.set_music_state(self.music_enabled)  # Синхронізація стану
            self.menu.update()
        elif self.screen_state == GAME_SCREEN:
            if not self.game_created:
                self.start_game()
                self.game_created = True
            self.game.update()
        self.render()

    # Check Events
    def check_events(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                # Якщо є активна гра, від'єднуємось від сервера
                if self.game and hasattr(self.game, 'disconnect'):
                    self.game.disconnect()
                exit()

            if event.type == KEYDOWN:
                # ESC для повернення до меню з гри або скасування підключення
                if event.key == K_ESCAPE:
                    if self.screen_state == GAME_SCREEN and self.game:
                        self.game.handle_escape_key()
                        # Якщо гра перейшла в стан меню, повертаємось до меню
                        if self.game.game_state == "menu":
                            self.screen_state = MENU_SCREEN
                            self.animate_state = MENU_SCREEN
                            self.game_created = False
                            self.game = None
                            # Ресетуємо меню
                            self.menu = Menu(self.clock)

                # Передаємо обробку клавіш грі (для діалогу підключення)
                if self.screen_state == GAME_SCREEN and self.game:
                    self.game.handle_key_input(event)

            if event.type == MOUSEBUTTONDOWN:
                if self.animate_state == MENU_SCREEN:
                    self.menu.mouse_click()
                    click_result = self.menu.get_menu_click()
                    if click_result == "toggle_music":
                        self.toggle_music()
                    elif click_result == GAME_SCREEN:
                        self.animate_state = GAME_SCREEN
                    elif click_result == OPTION_SCREEN:
                        self.animate_state = OPTION_SCREEN
                elif self.animate_state == GAME_SCREEN:
                    if self.game:
                        self.game.mouse_click()
                elif self.animate_state == OPTION_SCREEN:
                    self.menu.mouse_click()
                    click_result = self.menu.get_options_click()
                    if click_result == "toggle_music":
                        self.toggle_music()
                    elif click_result == MENU_SCREEN:
                        self.animate_state = MENU_SCREEN

    # Render
    def render(self):
        # Вибираємо фон в залежності від стану
        if self.animate_state == GAME_SCREEN and self.screen_state == GAME_SCREEN:
            # Якщо ми в грі, використовуємо ігровий фон
            self.screen.blit(self.game_background, (0, 0))
        else:
            # Якщо в меню або налаштуваннях, використовуємо звичайний фон
            self.screen.blit(self.background, (0, 0))

        if self.animate_state == MENU_SCREEN:
            self.menu.render(self.screen)
        elif self.animate_state == OPTION_SCREEN:
            self.menu.render(self.screen)
        elif self.animate_state == GAME_SCREEN:
            # animate menu off screen while screen_state waits
            if self.screen_state == MENU_SCREEN:
                self.menu.render(self.screen)
                self.screen_state = self.menu.animate_off()
            else:
                if self.game:
                    self.game.render(self.screen)
                # "kill" our menu if we don't need it
                if self.menu is not None:
                    self.menu = None

        self.draw_FPS()
        pygame.display.update()

    def draw_FPS(self):
        fps_text = str(round(self.clock.get_fps()))
        self.screen.blit(self.debugFont.render(fps_text, False, (255, 255, 0)), (15, 0))


if __name__ == '__main__':
    main_window = MainController()
    while True:
        main_window.update()