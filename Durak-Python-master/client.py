import socket
import threading
import json
import queue
import time


class GameClient:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False

        # Черга для повідомлень від сервера
        self.message_queue = queue.Queue()

        # Дані гравця
        self.player_id = None
        self.player_name = None
        self.game_id = None
        self.position = None
        self.opponent_name = None

        # Ігрові дані
        self.hand = []
        self.trump_suit = None
        self.trump_card = None
        self.deck_size = 0
        self.is_attacker = False
        self.attacker_name = None

        # Потік для отримання повідомлень
        self.receive_thread = None
        self.running = False

        # Статистика підключення
        self.connection_attempts = 0
        self.max_connection_attempts = 3
        self.last_error = None

    def connect(self, player_name="Player", host=None, port=None):
        """Підключення до сервера з коротшим таймаутом"""
        if host:
            self.host = host
        if port:
            self.port = port

        self.connection_attempts = 0

        while self.connection_attempts < self.max_connection_attempts:
            try:
                self.connection_attempts += 1
                print(
                    f"Спроба підключення {self.connection_attempts}/{self.max_connection_attempts} до {self.host}:{self.port}")

                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(5)  # Коротший таймаут - 5 секунд
                self.socket.connect((self.host, self.port))
                self.connected = True
                self.player_name = player_name

                # Запускаємо потік для отримання повідомлень
                self.running = True
                self.receive_thread = threading.Thread(target=self.receive_messages)
                self.receive_thread.daemon = True
                self.receive_thread.start()

                # Відправляємо запит на підключення
                join_message = {
                    'type': 'join',
                    'name': player_name
                }
                self.send_message(join_message)

                print(f"Успішно підключено до сервера як {player_name}")
                self.last_error = None
                return True

            except socket.timeout:
                self.last_error = "Таймаут підключення"
                print(f"Таймаут підключення до {self.host}:{self.port}")
            except ConnectionRefusedError:
                self.last_error = "Сервер відхилив підключення"
                print(f"Сервер {self.host}:{self.port} відхилив підключення")
            except socket.gaierror:
                self.last_error = "Невірна адреса сервера"
                print(f"Не вдалося знайти сервер {self.host}")
            except Exception as e:
                self.last_error = str(e)
                print(f"Помилка підключення: {e}")

            # Закриваємо сокет при невдалому підключенні
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                self.socket = None

            self.connected = False

            if self.connection_attempts < self.max_connection_attempts:
                print("Очікування перед наступною спробою...")
                time.sleep(1)  # Коротша затримка - 1 секунда

        print("Вичерпано всі спроби підключення")
        return False

    def disconnect(self):
        """Від'єднання від сервера"""
        print("Від'єднання від сервера...")
        self.running = False
        self.connected = False

        if self.socket:
            try:
                # Відправляємо повідомлення про від'єднання
                disconnect_message = {
                    'type': 'disconnect'
                }
                self.send_message(disconnect_message)
            except:
                pass

            try:
                self.socket.close()
            except:
                pass
            finally:
                self.socket = None

        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=2)

        # Очищуємо дані
        self.reset_game_data()
        print("Від'єднано від сервера")

    def reset_game_data(self):
        """Скидає ігрові дані"""
        self.player_id = None
        self.game_id = None
        self.position = None
        self.opponent_name = None
        self.hand = []
        self.trump_suit = None
        self.trump_card = None
        self.deck_size = 0
        self.is_attacker = False
        self.attacker_name = None

    def send_message(self, message):
        """Відправка повідомлення серверу"""
        if not self.connected or not self.socket:
            print("Немає з'єднання з сервером")
            return False

        try:
            json_message = json.dumps(message, ensure_ascii=False)
            self.socket.send(json_message.encode('utf-8'))
            return True
        except BrokenPipeError:
            print("З'єднання розірвано сервером")
            self.connected = False
            return False
        except Exception as e:
            print(f"Помилка відправки: {e}")
            self.connected = False
            return False

    def receive_messages(self):
        """Отримання повідомлень від сервера"""
        buffer = ""

        while self.running and self.connected:
            try:
                self.socket.settimeout(1)  # Таймаут для перевірки self.running
                data = self.socket.recv(1024).decode('utf-8')
                if not data:
                    print("Сервер закрив з'єднання")
                    break

                buffer += data

                # Обробляємо всі повні повідомлення в буфері
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            message = json.loads(line.strip())
                            self.message_queue.put(message)
                        except json.JSONDecodeError as e:
                            print(f"Некоректне повідомлення: {line} - {e}")

            except socket.timeout:
                # Нормальний таймаут для перевірки self.running
                continue
            except ConnectionResetError:
                print("З'єднання скинуто сервером")
                break
            except Exception as e:
                if self.running:
                    print(f"Помилка отримання даних: {e}")
                break

        self.connected = False
        print("Потік отримання повідомлень завершено")

    def get_messages(self):
        """Отримання всіх накопичених повідомлень"""
        messages = []
        while not self.message_queue.empty():
            try:
                messages.append(self.message_queue.get_nowait())
            except queue.Empty:
                break
        return messages

    def process_message(self, message):
        """Обробка повідомлення від сервера"""
        msg_type = message.get('type')

        if msg_type == 'join_success':
            self.player_id = message.get('player_id')
            self.player_name = message.get('name')
            print(f"Успішно підключено! ID: {self.player_id}, Ім'я: {self.player_name}")

        elif msg_type == 'game_created':
            self.game_id = message.get('game_id')
            self.position = message.get('position')
            self.opponent_name = message.get('opponent_name')
            print(f"Гра створена! ID: {self.game_id}, Суперник: {self.opponent_name}")

        elif msg_type == 'card_dealt':
            card_data = message.get('card')
            self.hand.append(card_data)
            print(f"Отримано карту: {card_data['rank']} {card_data['suit']}")

        elif msg_type == 'trump_card':
            self.trump_card = message.get('card')
            self.trump_suit = message.get('trump_suit')
            self.deck_size = message.get('deck_size')
            print(f"Козир: {self.trump_suit}, Карт в колоді: {self.deck_size}")

        elif msg_type == 'game_started':
            self.is_attacker = message.get('is_attacker')
            self.attacker_name = message.get('attacker_name')
            print(f"Гра почалася! Нападник: {self.attacker_name}")
            if self.is_attacker:
                print("Ви нападаєте!")
            else:
                print("Ви захищаєтесь!")

        elif msg_type == 'opponent_disconnected':
            print("Суперник від'єднався")

        elif msg_type == 'error':
            error_msg = message.get('message', 'Невідома помилка')
            print(f"Помилка від сервера: {error_msg}")

        else:
            print(f"Невідомий тип повідомлення: {msg_type}")

    def send_ready(self):
        """Повідомлення про готовність"""
        message = {
            'type': 'ready'
        }
        return self.send_message(message)

    def send_game_action(self, action_type, data=None):
        """Відправка ігрової дії"""
        message = {
            'type': 'game_action',
            'action': action_type,
            'data': data or {}
        }
        return self.send_message(message)

    def is_connected(self):
        """Перевірка з'єднання"""
        return self.connected and self.socket is not None

    def get_connection_status(self):
        """Отримання статусу підключення"""
        if self.connected:
            return "connected"
        elif self.last_error:
            return f"disconnected: {self.last_error}"
        else:
            return "disconnected"

    def get_hand(self):
        """Отримання карт в руці"""
        return self.hand.copy()

    def get_trump_info(self):
        """Отримання інформації про козир"""
        return {
            'suit': self.trump_suit,
            'card': self.trump_card,
            'deck_size': self.deck_size
        }

    def get_game_info(self):
        """Отримання інформації про гру"""
        return {
            'game_id': self.game_id,
            'position': self.position,
            'opponent_name': self.opponent_name,
            'is_attacker': self.is_attacker,
            'attacker_name': self.attacker_name
        }

    def ping_server(self):
        """Перевірка зв'язку з сервером"""
        if not self.is_connected():
            return False

        ping_message = {
            'type': 'ping'
        }
        return self.send_message(ping_message)