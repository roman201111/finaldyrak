import socket
import threading
import json
import time
from cards import Deck
from player import Player


class GameServer:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Ігрові дані
        self.clients = {}  # {socket: player_data}
        self.games = {}  # {game_id: game_data}
        self.waiting_players = []

        self.running = True
        self.client_counter = 0

        # Статистика
        self.total_connections = 0
        self.active_games = 0

    def start(self):
        """Запуск сервера"""
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            print(f"🎮 Сервер Дурак запущено на {self.host}:{self.port}")
            print("Очікуємо підключення гравців...")
            print("-" * 50)

            while self.running:
                try:
                    client_socket, addr = self.socket.accept()
                    self.total_connections += 1
                    print(f"📱 Новий клієнт підключився: {addr} (Загалом: {self.total_connections})")

                    # Створюємо окремий потік для кожного клієнта
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, addr)
                    )
                    client_thread.daemon = True
                    client_thread.start()

                except socket.error as e:
                    if self.running:
                        print(f"Помилка прийняття підключення: {e}")

        except Exception as e:
            print(f"Критична помилка сервера: {e}")
        finally:
            self.cleanup()

    def handle_client(self, client_socket, addr):
        """Обробка підключення клієнта"""
        client_id = self.client_counter
        self.client_counter += 1

        print(f"🔄 Запуск обробника для клієнта {addr} (ID: {client_id})")

        try:
            # Встановлюємо таймаут для сокета
            client_socket.settimeout(300)  # 5 хвилин таймауту

            while self.running:
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        print(f"📤 Клієнт {addr} закрив з'єднання")
                        break

                    try:
                        decoded_data = data.decode('utf-8')
                        message = json.loads(decoded_data)
                        self.process_message(client_socket, message, addr)
                    except json.JSONDecodeError as e:
                        print(f"❌ Некоректні дані від {addr}: {e}")
                        error_response = {
                            'type': 'error',
                            'message': 'Некоректний формат повідомлення'
                        }
                        self.send_message(client_socket, error_response)
                    except UnicodeDecodeError as e:
                        print(f"❌ Помилка кодування від {addr}: {e}")

                except socket.timeout:
                    # Перевіряємо пінг
                    if client_socket in self.clients:
                        ping_message = {'type': 'ping'}
                        if not self.send_message(client_socket, ping_message):
                            print(f"⏰ Таймаут з'єднання з {addr}")
                            break
                except socket.error as e:
                    print(f"🔌 Помилка сокета з клієнтом {addr}: {e}")
                    break

        except Exception as e:
            print(f"💥 Необроблена помилка з клієнтом {addr}: {e}")
        finally:
            self.disconnect_client(client_socket, addr)

    def process_message(self, client_socket, message, addr):
        """Обробка повідомлень від клієнтів"""
        msg_type = message.get('type')

        if msg_type == 'join':
            self.handle_join(client_socket, message, addr)
        elif msg_type == 'ready':
            self.handle_ready(client_socket, message)
        elif msg_type == 'game_action':
            self.handle_game_action(client_socket, message)
        elif msg_type == 'disconnect':
            print(f"📤 Клієнт {addr} відправив сигнал від'єднання")
        elif msg_type == 'ping':
            # Відповідаємо на пінг
            pong_message = {'type': 'pong'}
            self.send_message(client_socket, pong_message)
        else:
            print(f"❓ Невідомий тип повідомлення від {addr}: {msg_type}")

    def handle_join(self, client_socket, message, addr):
        """Обробка підключення гравця"""
        player_name = message.get('name', f'Player_{len(self.clients)}')

        # Перевіряємо, чи не підключений вже цей клієнт
        if client_socket in self.clients:
            print(f"⚠️ Клієнт {addr} вже підключений")
            return

        # Створюємо дані гравця
        player_data = {
            'socket': client_socket,
            'name': player_name,
            'id': len(self.clients),
            'address': addr,
            'game_id': None,
            'ready': False,
            'join_time': time.time()
        }

        self.clients[client_socket] = player_data
        self.waiting_players.append(client_socket)

        print(f"👤 Гравець '{player_name}' приєднався (адреса: {addr})")
        print(f"📊 Гравців в черзі: {len(self.waiting_players)}, Активних ігор: {len(self.games)}")

        # Відправляємо підтвердження
        response = {
            'type': 'join_success',
            'player_id': player_data['id'],
            'name': player_name
        }
        self.send_message(client_socket, response)

        # Перевіряємо, чи можна створити гру
        self.check_for_game_creation()

    def check_for_game_creation(self):
        """Перевіряє, чи можна створити нову гру"""
        if len(self.waiting_players) >= 2:
            # Беремо двох гравців з черги
            player1_socket = self.waiting_players.pop(0)
            player2_socket = self.waiting_players.pop(0)

            # Перевіряємо, що обидва гравці ще підключені
            if player1_socket in self.clients and player2_socket in self.clients:
                # Створюємо гру
                game_id = f"game_{int(time.time())}"
                self.create_game(game_id, [player1_socket, player2_socket])
            else:
                # Якщо хтось від'єднався, повертаємо інших в чергу
                if player1_socket in self.clients:
                    self.waiting_players.insert(0, player1_socket)
                if player2_socket in self.clients:
                    self.waiting_players.insert(0, player2_socket)

    def create_game(self, game_id, player_sockets):
        """Створення нової гри"""
        print(f"🎲 Створення нової гри: {game_id}")

        try:
            # Створюємо колоду
            deck = Deck()

            # Створюємо гру
            game_data = {
                'id': game_id,
                'players': player_sockets,
                'deck': deck,
                'state': 'dealing',  # waiting, dealing, playing, finished
                'current_attacker': 0,
                'attack_cards': [],
                'defense_cards': [],
                'created_time': time.time()
            }

            self.games[game_id] = game_data
            self.active_games += 1

            # Оновлюємо дані гравців
            player_names = []
            for i, socket in enumerate(player_sockets):
                if socket in self.clients:
                    self.clients[socket]['game_id'] = game_id
                    self.clients[socket]['position'] = i
                    player_names.append(self.clients[socket]['name'])

            print(f"👥 Гравці в грі {game_id}: {' vs '.join(player_names)}")

            # Повідомляємо гравців про створення гри
            for i, socket in enumerate(player_sockets):
                if socket in self.clients:
                    opponent_socket = player_sockets[1 - i]
                    opponent_name = self.clients[opponent_socket][
                        'name'] if opponent_socket in self.clients else "Невідомий"

                    response = {
                        'type': 'game_created',
                        'game_id': game_id,
                        'position': i,
                        'opponent_name': opponent_name
                    }
                    self.send_message(socket, response)

            # Починаємо роздавання карт
            self.deal_initial_cards(game_id)

        except Exception as e:
            print(f"❌ Помилка створення гри: {e}")
            # Повертаємо гравців в чергу
            for socket in player_sockets:
                if socket in self.clients:
                    self.waiting_players.append(socket)

    def deal_initial_cards(self, game_id):
        """Роздавання початкових карт"""
        if game_id not in self.games:
            print(f"❌ Гра {game_id} не знайдена для роздавання карт")
            return

        game = self.games[game_id]
        deck = game['deck']

        print(f"🃏 Роздавання карт для гри {game_id}")

        try:
            # Роздаємо по 6 карт кожному гравцеві
            for round_num in range(6):
                for player_socket in game['players']:
                    if player_socket in self.clients and len(deck) > 0:
                        card = deck.pop()

                        # Відправляємо карту гравцеві
                        response = {
                            'type': 'card_dealt',
                            'card': {
                                'rank': card.rank,
                                'suit': card.suit,
                                'is_trump': card.uber == card.suit
                            },
                            'round': round_num + 1
                        }
                        if not self.send_message(player_socket, response):
                            print(f"❌ Не вдалося надіслати карту гравцеві")
                            return

            # Відправляємо інформацію про козирну карту
            trump_card = deck.top_card
            trump_info = {
                'type': 'trump_card',
                'card': {
                    'rank': trump_card.rank,
                    'suit': trump_card.suit
                },
                'trump_suit': deck.uber,
                'deck_size': len(deck)
            }

            for player_socket in game['players']:
                if player_socket in self.clients:
                    self.send_message(player_socket, trump_info)

            # Визначаємо першого нападника
            self.determine_first_attacker(game_id)

            # Змінюємо стан гри
            game['state'] = 'playing'

            # Повідомляємо про початок гри
            for i, player_socket in enumerate(game['players']):
                if player_socket in self.clients:
                    attacker_name = self.clients[game['players'][game['current_attacker']]]['name']
                    response = {
                        'type': 'game_started',
                        'is_attacker': i == game['current_attacker'],
                        'attacker_name': attacker_name
                    }
                    self.send_message(player_socket, response)

            print(f"✅ Гра {game_id} успішно запущена")

        except Exception as e:
            print(f"❌ Помилка при роздаванні карт: {e}")
            self.end_game(game_id, "Помилка при роздаванні карт")

    def determine_first_attacker(self, game_id):
        """Визначає першого нападника"""
        import random
        game = self.games.get(game_id)
        if game:
            game['current_attacker'] = random.randint(0, 1)
            print(f"🎯 Перший нападник в грі {game_id}: гравець {game['current_attacker']}")

    def handle_ready(self, client_socket, message):
        """Обробка готовності гравця"""
        if client_socket in self.clients:
            self.clients[client_socket]['ready'] = True
            player_name = self.clients[client_socket]['name']
            print(f"✅ Гравець {player_name} готовий")

    def handle_game_action(self, client_socket, message):
        """Обробка ігрових дій"""
        if client_socket not in self.clients:
            return

        player_data = self.clients[client_socket]
        game_id = player_data.get('game_id')

        if not game_id or game_id not in self.games:
            error_response = {
                'type': 'error',
                'message': 'Ви не в грі'
            }
            self.send_message(client_socket, error_response)
            return

        action = message.get('action')
        print(f"🎮 Ігрова дія від {player_data['name']}: {action}")

        # Тут буде логіка обробки ігрових ходів
        # Поки що просто логуємо

    def send_message(self, client_socket, message):
        """Відправка повідомлення клієнту"""
        try:
            json_message = json.dumps(message, ensure_ascii=False) + '\n'
            client_socket.send(json_message.encode('utf-8'))
            return True
        except BrokenPipeError:
            print(f"🔌 З'єднання розірвано при відправці повідомлення")
            return False
        except Exception as e:
            print(f"❌ Помилка відправки повідомлення: {e}")
            return False

    def disconnect_client(self, client_socket, addr):
        """Від'єднання клієнта"""
        if client_socket not in self.clients:
            return

        player_data = self.clients[client_socket]
        player_name = player_data['name']
        print(f"📤 Гравець '{player_name}' від'єднався ({addr})")

        # Видаляємо з черги очікування
        if client_socket in self.waiting_players:
            self.waiting_players.remove(client_socket)
            print(f"🚫 Видалено з черги очікування: {player_name}")

        # Обробляємо від'єднання в грі
        game_id = player_data.get('game_id')
        if game_id and game_id in self.games:
            self.handle_player_disconnect_in_game(game_id, client_socket)

        # Видаляємо клієнта
        del self.clients[client_socket]

        # Закриваємо сокет
        try:
            client_socket.close()
        except:
            pass

        print(f"📊 Активних клієнтів: {len(self.clients)}, Гравців в черзі: {len(self.waiting_players)}")

    def handle_player_disconnect_in_game(self, game_id, disconnected_socket):
        """Обробка від'єднання гравця під час гри"""
        game = self.games.get(game_id)
        if not game:
            return

        disconnected_player = self.clients.get(disconnected_socket, {}).get('name', 'Невідомий')
        print(f"🎲 Гравець {disconnected_player} від'єднався від гри {game_id}")

        # Повідомляємо іншого гравця
        for player_socket in game['players']:
            if player_socket != disconnected_socket and player_socket in self.clients:
                response = {
                    'type': 'opponent_disconnected',
                    'message': f'Гравець {disconnected_player} від\'єднався'
                }
                self.send_message(player_socket, response)

                # Повертаємо гравця в чергу очікування
                if player_socket not in self.waiting_players:
                    self.waiting_players.append(player_socket)
                    self.clients[player_socket]['game_id'] = None
                    self.clients[player_socket]['ready'] = False

        # Видаляємо гру
        self.end_game(game_id, f"Гравець {disconnected_player} від'єднався")

    def end_game(self, game_id, reason=""):
        """Завершення гри"""
        if game_id in self.games:
            del self.games[game_id]
            self.active_games = max(0, self.active_games - 1)
            print(f"🏁 Гру {game_id} завершено. Причина: {reason}")
            print(f"📊 Активних ігор: {self.active_games}")

    def cleanup(self):
        """Очищення ресурсів сервера"""
        print("\n🧹 Очищення ресурсів сервера...")

        # Повідомляємо всіх клієнтів про зупинку сервера
        shutdown_message = {
            'type': 'server_shutdown',
            'message': 'Сервер зупиняється'
        }

        for client_socket in list(self.clients.keys()):
            self.send_message(client_socket, shutdown_message)
            try:
                client_socket.close()
            except:
                pass

        # Очищуємо дані
        self.clients.clear()
        self.waiting_players.clear()
        self.games.clear()

        # Закриваємо основний сокет
        try:
            self.socket.close()
        except:
            pass

        print("✅ Ресурси сервера очищено")

    def stop(self):
        """Зупинка сервера"""
        print("\n🛑 Отримано сигнал зупинки сервера...")
        self.running = False
        self.cleanup()

    def get_server_stats(self):
        """Отримання статистики сервера"""
        return {
            'total_connections': self.total_connections,
            'active_clients': len(self.clients),
            'waiting_players': len(self.waiting_players),
            'active_games': len(self.games),
            'running': self.running
        }

    def print_status(self):
        """Виведення статусу сервера"""
        stats = self.get_server_stats()
        print("\n" + "=" * 50)
        print("📊 СТАТУС СЕРВЕРА")
        print("=" * 50)
        print(f"🌐 Адреса сервера: {self.host}:{self.port}")
        print(f"📈 Загальних підключень: {stats['total_connections']}")
        print(f"👥 Активних клієнтів: {stats['active_clients']}")
        print(f"⏳ Гравців в черзі: {stats['waiting_players']}")
        print(f"🎮 Активних ігор: {stats['active_games']}")
        print(f"🔄 Статус: {'Працює' if stats['running'] else 'Зупинено'}")
        print("=" * 50)

        # Виводимо список активних гравців
        if self.clients:
            print("\n👥 АКТИВНІ ГРАВЦІ:")
            for i, (socket, player_data) in enumerate(self.clients.items(), 1):
                status = "В грі" if player_data.get('game_id') else "В черзі"
                print(f"  {i}. {player_data['name']} ({player_data['address']}) - {status}")

        # Виводимо список активних ігор
        if self.games:
            print("\n🎮 АКТИВНІ ІГРИ:")
            for game_id, game_data in self.games.items():
                players = []
                for socket in game_data['players']:
                    if socket in self.clients:
                        players.append(self.clients[socket]['name'])
                print(f"  {game_id}: {' vs '.join(players)} ({game_data['state']})")

        print()


if __name__ == '__main__':
    server = GameServer()
    try:
        # Запускаємо сервер
        server_thread = threading.Thread(target=server.start)
        server_thread.daemon = True
        server_thread.start()

        # Основний цикл для команд адміністратора
        print("Команди: 'status' - статус сервера, 'quit' - вихід")
        while server.running:
            try:
                command = input().strip().lower()
                if command == 'quit':
                    break
                elif command == 'status':
                    server.print_status()
                elif command == 'help':
                    print("Доступні команди:")
                    print("  status - показати статус сервера")
                    print("  help - показати цю довідку")
                    print("  quit - зупинити сервер")
                elif command:
                    print("Невідома команда. Введіть 'help' для довідки.")
            except (KeyboardInterrupt, EOFError):
                break

    except KeyboardInterrupt:
        print("\n🛑 Отримано сигнал переривання...")
    finally:
        server.stop()