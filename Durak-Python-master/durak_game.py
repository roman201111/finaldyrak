import time
import pygame
from math import ceil
import threading

# local imports
from cards import Deck, Card
from board import Board
from constants import *
from player import Player
from client import GameClient


class NetworkDurak:
    def __init__(self, pygame_clock, game_controller):
        self.dt = 0
        self.pygame_clock = pygame_clock
        self.game_controller = game_controller

        # Мережевий клієнт
        self.client = GameClient()
        self.connection_state = "disconnected"  # disconnected, connecting, connected, in_game

        # Локальні дані гри
        self.board = None
        self.back_image = None
        self.deck_x = 0
        self.deck_y = 0
        self.trump_x = 0
        self.trump_y = 0

        # mouse + position
        self.click = False
        self.mx, self.my = 0, 0

        # Дані гравців
        self.local_player = None  # Локальний гравець
        self.opponent_player = None  # Суперник
        self.players = []

        # Ігрові стани
        self.game_state = "menu"  # menu, connecting, waiting, dealing, playing
        self.show_connection_dialog = False
        self.connection_message = ""
        self.connection_input = ""  # Для введення IP
        self.input_active = False
        self.server_host = "localhost"
        self.server_port = 12345

        # Дані для відображення
        self.trump_suit = None
        self.trump_card = None
        self.deck_size = 0
        self.is_attacker = False

        # Потік для підключення
        self.connection_thread = None

        # Завантажуємо базові ресурси
        self.load_basic_assets()

        # Шрифт для інтерфейсу
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)

    def load_basic_assets(self):
        """Завантаження базових ресурсів для відображення"""
        # Створюємо тимчасову колоду для завантаження ресурсів
        temp_deck = Deck()
        for card in temp_deck.cards_list:
            card.load_image_assets()

        self.back_image = temp_deck.cards_list[-1].current_image.copy()

        # Встановлюємо позиції для відображення
        self.setup_display_positions()

    def setup_display_positions(self):
        """Налаштування позицій для відображення елементів"""
        if self.back_image:
            # Розміщуємо колоду праворуч від центру
            self.deck_x = (SCREENWIDTH // 2) + 350
            self.deck_y = (SCREENHEIGHT // 2) - (self.back_image.get_rect().size[1] // 2)

            # Позиція козирної карти
            card_height = self.back_image.get_rect().size[1]
            self.trump_x = self.deck_x
            self.trump_y = self.deck_y + (card_height * 0.35)

    def show_connection_interface(self):
        """Показати інтерфейс підключення"""
        self.game_state = "connection_dialog"
        self.show_connection_dialog = True
        self.connection_input = self.server_host

    def connect_to_server_async(self, player_name="Player", host=None, port=None):
        """Асинхронне підключення до сервера"""
        if host:
            self.server_host = host
        if port:
            self.server_port = port

        self.connection_state = "connecting"
        self.connection_message = f"Підключення до {self.server_host}:{self.server_port}..."
        self.game_state = "connecting"

        # Запускаємо підключення в окремому потоці
        if self.connection_thread and self.connection_thread.is_alive():
            return  # Підключення вже йде

        self.connection_thread = threading.Thread(
            target=self._connect_worker,
            args=(player_name,),
            daemon=True
        )
        self.connection_thread.start()

    def _connect_worker(self, player_name):
        """Робочий потік для підключення"""
        try:
            if self.client.connect(player_name, self.server_host, self.server_port):
                self.connection_state = "connected"
                self.connection_message = "Очікування суперника..."
                self.game_state = "waiting"
            else:
                self.connection_state = "disconnected"
                self.connection_message = f"Помилка підключення: {self.client.get_connection_status()}"
                # Через 3 секунди повертаємося в меню
                time.sleep(3)
                if self.game_state == "connecting":
                    self.game_state = "menu"
        except Exception as e:
            print(f"Помилка в потоці підключення: {e}")
            self.connection_state = "disconnected"
            self.connection_message = f"Помилка підключення: {str(e)}"
            self.game_state = "menu"

    def connect_to_server(self, player_name="Player", host=None, port=None):
        """Підключення до сервера (публічний метод для зворотної сумісності)"""
        self.connect_to_server_async(player_name, host, port)

    def update(self):
        """Оновлення стану гри"""
        self.mx, self.my = pygame.mouse.get_pos()

        # Обробляємо повідомлення від сервера
        if self.client.is_connected():
            messages = self.client.get_messages()
            for message in messages:
                self.process_server_message(message)

        # Оновлюємо стан підключення
        if not self.client.is_connected() and self.connection_state in ["connected", "connecting"]:
            self.connection_state = "disconnected"
            if self.game_state not in ["menu", "connection_dialog"]:
                self.game_state = "menu"
                self.connection_message = "З'єднання втрачено"

        # Обробка кліку
        if self.click:
            self.handle_click()
            self.click = False

        # Оновлюємо board якщо він існує
        if self.board:
            self.board.update()

    def handle_click(self):
        """Обробка кліків в різних станах гри"""
        if self.game_state == "connection_dialog":
            self.handle_connection_dialog_click()
        elif self.game_state == "playing":
            self.handle_game_click()

    def handle_connection_dialog_click(self):
        """Обробка кліків в діалозі підключення"""
        # Перевіряємо клік по полю введення IP
        input_rect = pygame.Rect(SCREENWIDTH // 2 - 150, SCREENHEIGHT // 2 - 50, 300, 40)
        if input_rect.collidepoint(self.mx, self.my):
            self.input_active = True
        else:
            self.input_active = False

        # Перевіряємо клік по кнопці підключення
        connect_rect = pygame.Rect(SCREENWIDTH // 2 - 75, SCREENHEIGHT // 2 + 20, 150, 40)
        if connect_rect.collidepoint(self.mx, self.my):
            self.connect_to_server_async("Player", self.connection_input, self.server_port)

        # Перевіряємо клік по кнопці скасування
        cancel_rect = pygame.Rect(SCREENWIDTH // 2 - 75, SCREENHEIGHT // 2 + 70, 150, 40)
        if cancel_rect.collidepoint(self.mx, self.my):
            self.game_state = "menu"
            self.show_connection_dialog = False

    def handle_game_click(self):
        """Обробка кліків в грі"""
        if self.local_player and self.local_player.hand:
            card_width = self.back_image.get_rect().size[0] if self.back_image else 80
            card_height = self.back_image.get_rect().size[1] if self.back_image else 120

            user_cards_x = SCREENWIDTH // 4
            user_cards_x_end = SCREENWIDTH - SCREENWIDTH // 4
            user_cards_gap = (user_cards_x_end - user_cards_x) / len(self.local_player.hand) if len(
                self.local_player.hand) > 1 else 0

            for i, card in enumerate(self.local_player.hand):
                card_x = user_cards_x + i * user_cards_gap
                card_y = SCREENHEIGHT - card_height // 2
                card_rect = pygame.Rect(card_x, card_y, card_width, card_height)

                if card_rect.collidepoint(self.mx, self.my):
                    print(f"Клік по карті: {card.rank} {card.suit}")
                    # Тут буде логіка гри

    def handle_key_input(self, event):
        """Обробка введення з клавіатури"""
        if self.game_state == "connection_dialog" and self.input_active:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    self.connect_to_server_async("Player", self.connection_input, self.server_port)
                elif event.key == pygame.K_BACKSPACE:
                    self.connection_input = self.connection_input[:-1]
                elif event.key == pygame.K_ESCAPE:
                    self.game_state = "menu"
                    self.show_connection_dialog = False
                else:
                    # Додаємо символи до введення
                    if len(self.connection_input) < 20:  # Обмеження довжини
                        self.connection_input += event.unicode

    def process_server_message(self, message):
        """Обробка повідомлень від сервера"""
        self.client.process_message(message)
        msg_type = message.get('type')

        if msg_type == 'game_created':
            self.connection_message = "Гра створена! Роздаю карти..."
            self.setup_players()

        elif msg_type == 'card_dealt':
            # Додаємо карту до руки локального гравця
            if self.local_player:
                card_data = message.get('card')
                card = self.create_card_from_data(card_data)
                self.local_player.hand.append(card)

        elif msg_type == 'trump_card':
            self.trump_card = message.get('card')
            self.trump_suit = message.get('trump_suit')
            self.deck_size = message.get('deck_size')

        elif msg_type == 'game_started':
            self.is_attacker = message.get('is_attacker')
            self.game_state = "playing"
            self.connection_message = ""

            # Сортуємо руку гравця
            if self.local_player:
                self.local_player.sort_hand()

        elif msg_type == 'opponent_disconnected':
            self.connection_message = "Суперник від'єднався"
            self.game_state = "menu"

    def setup_players(self):
        """Налаштування гравців"""
        game_info = self.client.get_game_info()

        # Створюємо локального гравця
        self.local_player = Player(self.client.player_name, True, self.client.player_id)

        # Створюємо гравця-суперника
        self.opponent_player = Player(game_info['opponent_name'], False, 1 - self.client.player_id)

        self.players = [self.local_player, self.opponent_player]

        # Створюємо дошку для гри
        if not self.board:
            # Створюємо тимчасову колоду для board
            temp_deck = Deck()
            self.board = Board(self.pygame_clock, temp_deck)

    def create_card_from_data(self, card_data):
        """Створення об'єкта карти з даних сервера"""
        card = Card(card_data['rank'], card_data['suit'])
        card.load_image_assets()
        if card_data.get('is_trump', False):
            card.uber = card.suit
        elif self.trump_suit:
            card.uber = self.trump_suit
        return card

    def mouse_click(self):
        """Обробка кліків миші"""
        self.click = True

    def render(self, screen):
        """Відображення гри"""
        self.dt = self.pygame_clock.tick(60) / 1000.0

        if self.game_state == "menu":
            self.draw_menu(screen)
        elif self.game_state == "connection_dialog":
            self.draw_connection_dialog(screen)
        elif self.game_state == "connecting":
            self.draw_connecting_screen(screen)
        elif self.game_state == "waiting":
            self.draw_waiting_screen(screen)
        elif self.game_state == "playing":
            self.draw_game(screen)

    def draw_menu(self, screen):
        """Відображення меню підключення"""
        font = pygame.font.Font(None, 48)
        small_font = pygame.font.Font(None, 32)

        # Заголовок
        title = font.render("Мережева гра Дурак", True, (255, 255, 255))
        title_rect = title.get_rect(center=(SCREENWIDTH // 2, SCREENHEIGHT // 2 - 150))
        screen.blit(title, title_rect)

        # Кнопка підключення
        connect_text = small_font.render("Натисніть SPACE для підключення", True, (255, 255, 255))
        connect_rect = connect_text.get_rect(center=(SCREENWIDTH // 2, SCREENHEIGHT // 2 - 50))
        screen.blit(connect_text, connect_rect)

        # Кнопка налаштувань підключення
        settings_text = small_font.render("Натисніть C для налаштувань підключення", True, (200, 200, 200))
        settings_rect = settings_text.get_rect(center=(SCREENWIDTH // 2, SCREENHEIGHT // 2))
        screen.blit(settings_text, settings_rect)

        # Повідомлення про помилку (якщо є)
        if self.connection_message:
            error_text = small_font.render(self.connection_message, True, (255, 100, 100))
            error_rect = error_text.get_rect(center=(SCREENWIDTH // 2, SCREENHEIGHT // 2 + 50))
            screen.blit(error_text, error_rect)

        # Перевіряємо натискання клавіш
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE]:
            self.connect_to_server_async("Player")
        elif keys[pygame.K_c]:
            self.show_connection_interface()

    def draw_connection_dialog(self, screen):
        """Відображення діалогу підключення"""
        # Напівпрозорий фон
        overlay = pygame.Surface((SCREENWIDTH, SCREENHEIGHT))
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        # Головне вікно діалогу
        dialog_rect = pygame.Rect(SCREENWIDTH // 2 - 200, SCREENHEIGHT // 2 - 120, 400, 240)
        pygame.draw.rect(screen, (50, 50, 50), dialog_rect)
        pygame.draw.rect(screen, (255, 255, 255), dialog_rect, 2)

        # Заголовок
        title_text = self.font.render("Налаштування підключення", True, (255, 255, 255))
        title_rect = title_text.get_rect(center=(SCREENWIDTH // 2, SCREENHEIGHT // 2 - 90))
        screen.blit(title_text, title_rect)

        # Поле введення IP
        label_text = self.small_font.render("IP сервера:", True, (255, 255, 255))
        screen.blit(label_text, (SCREENWIDTH // 2 - 150, SCREENHEIGHT // 2 - 70))

        input_rect = pygame.Rect(SCREENWIDTH // 2 - 150, SCREENHEIGHT // 2 - 50, 300, 40)
        color = (255, 255, 255) if self.input_active else (200, 200, 200)
        pygame.draw.rect(screen, (30, 30, 30), input_rect)
        pygame.draw.rect(screen, color, input_rect, 2)

        input_text = self.small_font.render(self.connection_input, True, (255, 255, 255))
        screen.blit(input_text, (input_rect.x + 10, input_rect.y + 10))

        # Кнопки
        connect_rect = pygame.Rect(SCREENWIDTH // 2 - 75, SCREENHEIGHT // 2 + 20, 150, 40)
        pygame.draw.rect(screen, (0, 150, 0), connect_rect)
        pygame.draw.rect(screen, (255, 255, 255), connect_rect, 2)
        connect_text = self.small_font.render("Підключитись", True, (255, 255, 255))
        connect_text_rect = connect_text.get_rect(center=connect_rect.center)
        screen.blit(connect_text, connect_text_rect)

        cancel_rect = pygame.Rect(SCREENWIDTH // 2 - 75, SCREENHEIGHT // 2 + 70, 150, 40)
        pygame.draw.rect(screen, (150, 0, 0), cancel_rect)
        pygame.draw.rect(screen, (255, 255, 255), cancel_rect, 2)
        cancel_text = self.small_font.render("Скасувати", True, (255, 255, 255))
        cancel_text_rect = cancel_text.get_rect(center=cancel_rect.center)
        screen.blit(cancel_text, cancel_text_rect)

    def draw_connecting_screen(self, screen):
        """Екран підключення"""
        font = pygame.font.Font(None, 48)
        message = font.render(self.connection_message, True, (255, 255, 255))
        message_rect = message.get_rect(center=(SCREENWIDTH // 2, SCREENHEIGHT // 2))
        screen.blit(message, message_rect)

        # Анімація завантаження
        dots_count = int(time.time() * 2) % 4
        dots = "." * dots_count
        dots_text = font.render(dots, True, (255, 255, 255))
        dots_rect = dots_text.get_rect(center=(SCREENWIDTH // 2 + 200, SCREENHEIGHT // 2))
        screen.blit(dots_text, dots_rect)

        # Інструкція для скасування
        cancel_text = pygame.font.Font(None, 24).render("Натисніть ESC для скасування", True, (200, 200, 200))
        cancel_rect = cancel_text.get_rect(center=(SCREENWIDTH // 2, SCREENHEIGHT // 2 + 100))
        screen.blit(cancel_text, cancel_rect)

    def draw_waiting_screen(self, screen):
        """Екран очікування"""
        font = pygame.font.Font(None, 48)
        message = font.render(self.connection_message, True, (255, 255, 255))
        message_rect = message.get_rect(center=(SCREENWIDTH // 2, SCREENHEIGHT // 2))
        screen.blit(message, message_rect)

        # Анімація очікування
        dots_count = int(time.time() * 2) % 4
        dots = "." * dots_count
        dots_text = font.render(dots, True, (255, 255, 255))
        dots_rect = dots_text.get_rect(center=(SCREENWIDTH // 2 + 200, SCREENHEIGHT // 2))
        screen.blit(dots_text, dots_rect)

        # Інструкція для скасування
        cancel_text = pygame.font.Font(None, 24).render("Натисніть ESC для повернення до меню", True, (200, 200, 200))
        cancel_rect = cancel_text.get_rect(center=(SCREENWIDTH // 2, SCREENHEIGHT // 2 + 100))
        screen.blit(cancel_text, cancel_rect)

    def draw_game(self, screen):
        """Відображення ігрового процесу"""
        # Відображаємо колоду і козир
        self.draw_deck_and_trump(screen)

        # Відображаємо гравців
        self.draw_players(screen)

        # Відображаємо дошку (якщо є)
        if self.board:
            self.board.render(screen)

        # Відображаємо інформацію про хід
        self.draw_turn_info(screen)

    def draw_deck_and_trump(self, screen):
        """Відображення колоди та козирної карти"""
        if not self.back_image:
            return

        # Малюємо колоду
        for i in range(min(6, ceil(self.deck_size / 4.5))):
            screen.blit(self.back_image, (self.deck_x + i * 2, self.deck_y + i * 2))

        # Малюємо козирну карту
        if self.trump_card:
            trump_card_obj = self.create_card_from_data(self.trump_card)
            screen.blit(trump_card_obj.front_image, (self.trump_x, self.trump_y))

    def draw_players(self, screen):
        """Відображення карт гравців"""
        if not self.local_player or not self.back_image:
            return

        card_width = self.back_image.get_rect().size[0]
        card_height = self.back_image.get_rect().size[1]

        # Відображення карт локального гравця (внизу, лицьовою стороною)
        if self.local_player.hand:
            user_cards_x = SCREENWIDTH // 4
            user_cards_x_end = SCREENWIDTH - SCREENWIDTH // 4
            user_cards_gap = (user_cards_x_end - user_cards_x) / len(self.local_player.hand) if len(
                self.local_player.hand) > 1 else 0

            for i, card in enumerate(self.local_player.hand):
                card_x = user_cards_x + i * user_cards_gap
                card_y = SCREENHEIGHT - card_height // 2 - 20
                screen.blit(card.front_image, (card_x, card_y))

                # Підсвічуємо карту при наведенні миші
                card_rect = pygame.Rect(card_x, card_y, card_width, card_height)
                if card_rect.collidepoint(self.mx, self.my):
                    pygame.draw.rect(screen, (255, 255, 0), card_rect, 3)

        # Відображення карт суперника (вгорі, тильною стороною)
        if self.opponent_player:
            opponent_hand_size = len(getattr(self.opponent_player, 'hand', [])) or 6
            if opponent_hand_size > 0:
                opponent_cards_x = SCREENWIDTH // 4
                opponent_cards_x_end = SCREENWIDTH - SCREENWIDTH // 4
                opponent_cards_gap = (
                                             opponent_cards_x_end - opponent_cards_x) / opponent_hand_size if opponent_hand_size > 1 else 0

                for i in range(opponent_hand_size):
                    screen.blit(self.back_image,
                                (opponent_cards_x + i * opponent_cards_gap, card_height // 4))

    def draw_turn_info(self, screen):
        """Відображення інформації про поточний хід"""
        font = pygame.font.Font(None, 36)

        # Інформація про нападника/захисника
        if self.is_attacker:
            turn_text = "Ваш хід - НАПАД"
            color = (255, 100, 100)
        else:
            turn_text = "Ваш хід - ЗАХИСТ"
            color = (100, 100, 255)

        turn_surface = font.render(turn_text, True, color)
        screen.blit(turn_surface, (10, SCREENHEIGHT - 50))

        # Інформація про козир
        if self.trump_suit:
            trump_text = f"Козир: {self.trump_suit}"
            trump_surface = font.render(trump_text, True, (255, 255, 255))
            screen.blit(trump_surface, (10, SCREENHEIGHT - 90))

        # Кількість карт в колоді
        deck_text = f"Карт в колоді: {self.deck_size}"
        deck_surface = font.render(deck_text, True, (255, 255, 255))
        screen.blit(deck_surface, (10, SCREENHEIGHT - 130))

        # Імена гравців
        if self.local_player:
            player_text = f"Ви: {self.local_player.name} ({len(self.local_player.hand)} карт)"
            player_surface = font.render(player_text, True, (255, 255, 255))
            screen.blit(player_surface, (10, 10))

        if self.opponent_player:
            opponent_hand_size = len(getattr(self.opponent_player, 'hand', [])) or 6
            opponent_text = f"Суперник: {self.opponent_player.name} ({opponent_hand_size} карт)"
            opponent_surface = font.render(opponent_text, True, (255, 255, 255))
            screen.blit(opponent_surface, (10, 50))

    def handle_escape_key(self):
        """Обробка натискання ESC"""
        if self.game_state == "waiting" or self.game_state == "connecting":
            self.disconnect()
        elif self.game_state == "connection_dialog":
            self.game_state = "menu"
            self.show_connection_dialog = False

    def disconnect(self):
        """Від'єднання від сервера"""
        if self.client:
            self.client.disconnect()

        # Скасовуємо потік підключення якщо він активний
        if self.connection_thread and self.connection_thread.is_alive():
            # Потік daemon, тому він завершиться автоматично
            pass

        self.connection_state = "disconnected"
        self.game_state = "menu"
        self.local_player = None
        self.opponent_player = None
        self.players = []
        self.board = None
        self.connection_message = ""