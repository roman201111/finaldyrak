#!/usr/bin/env python3
"""
Скрипт для запуску сервера гри Дурак
Використання: python run_server.py [host] [port]
"""
import sys
import os
import threading
import time

# Додаємо поточну директорію до шляху для імпортів
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import GameServer


def print_banner():
    """Виводить банер запуску сервера"""
    print("=" * 60)
    print("        🎮 СЕРВЕР ГРИ ДУРАК ОНЛАЙН 🎮")
    print("=" * 60)
    print()


def main():
    # Параметри за замовчуванням
    host = 'localhost'
    port = 12345

    # Парсимо аргументи командного рядка
    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            port = int(sys.argv[2])
        except ValueError:
            print("❌ Помилка: порт повинен бути числом")
            sys.exit(1)

    print_banner()
    print(f"🌐 Запуск сервера на {host}:{port}")
    print("🎯 Режим гри: 2 гравці")
    print("⌨️  Команди управління:")
    print("   'status' - показати статус сервера")
    print("   'help'   - показати довідку")
    print("   'quit'   - зупинити сервер")
    print("   Ctrl+C   - аварійна зупинка")
    print("-" * 60)

    # Створюємо та запускаємо сервер
    server = GameServer(host, port)

    try:
        # Запускаємо сервер в окремому потоці
        server_thread = threading.Thread(target=server.start)
        server_thread.daemon = True
        server_thread.start()

        # Даємо серверу час на ініціалізацію
        time.sleep(1)

        if server.running:
            print("✅ Сервер успішно запущено!")
            print("📱 Очікуємо підключення клієнтів...")
            print()

        # Головний цикл обробки команд
        while server.running and server_thread.is_alive():
            try:
                print("Сервер> ", end="", flush=True)
                command = input().strip().lower()

                if command == 'quit' or command == 'exit':
                    print("🛑 Зупинка сервера...")
                    break
                elif command == 'status':
                    server.print_status()
                elif command == 'help':
                    print("\n📖 ДОВІДКА ПО КОМАНДАХ:")
                    print("-" * 30)
                    print("status  - показати детальний статус сервера")
                    print("help    - показати цю довідку")
                    print("quit    - коректно зупинити сервер")
                    print("Ctrl+C  - аварійна зупинка")
                    print()
                elif command == '':
                    # Просто пропускаємо порожні рядки
                    continue
                else:
                    if command:
                        print(f"❓ Невідома команда: '{command}'")
                        print("💡 Введіть 'help' для списку команд")

            except (KeyboardInterrupt, EOFError):
                print("\n🛑 Отримано сигнал переривання...")
                break

    except Exception as e:
        print(f"💥 Критична помилка: {e}")
        print("📝 Перевірте логи для деталей")
        return 1
    finally:
        print("\n" + "=" * 40)
        print("🔄 Завершення роботи сервера...")
        server.stop()

        # Чекаємо завершення серверного потоку
        if server_thread.is_alive():
            print("⏳ Очікування завершення серверного потоку...")
            server_thread.join(timeout=5)

        print("✅ Сервер успішно зупинено")
        print("👋 До побачення!")

    return 0


if __name__ == '__main__':
    sys.exit(main())