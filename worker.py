import os
from datetime import datetime
import io

from app.main import process_payment_files

import telegram
import asyncio


# Для простоты примера, будем считать, что файлы лежат в папке /data
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
RENT_FILE_PATH = os.path.join(DATA_DIR, 'arenda.xlsx')
BANK_STATEMENT_PATH = os.path.join(DATA_DIR, 'print 2.xlsx')

# Путь для сохранения отчета
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')

# Настройки Telegram (ЗАМЕНИТЕ НА ВАШИ ДАННЫЕ)
# ВАЖНО: В реальном проекте эти данные нужно хранить в переменных окружения, а не в коде
TELEGRAM_BOT_TOKEN = "ВАШ_БОТ_ТОКЕН"
TELEGRAM_CHAT_ID = "ВАШ_ЧАТ_ID"


async def send_report_to_telegram(report_path: str, caption: str):
    """Асинхронно отправляет файл отчета в Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Переменные Telegram не настроены. Отчет не будет отправлен.")
        return

    try:
        bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        async with bot:
            await bot.send_document(
                chat_id=TELEGRAM_CHAT_ID,
                document=open(report_path, 'rb'),
                caption=caption,
                disable_notification=True
            )
        print(f"Отчет успешно отправлен в Telegram в чат {TELEGRAM_CHAT_ID}")
    except Exception as e:
        print(f"Ошибка при отправке отчета в Telegram: {e}")


async def main():
    """Главная функция-воркер."""
    print(f"[{datetime.now()}] Запуск воркера для генерации отчета...")

    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)

    if not os.path.exists(RENT_FILE_PATH) or not os.path.exists(BANK_STATEMENT_PATH):
        print("Ошибка: Файлы 'arenda.xlsx' или 'print 2.xlsx' не найдены в папке /data.")
        return

    try:
        with open(RENT_FILE_PATH, 'rb') as rent_f, open(BANK_STATEMENT_PATH, 'rb') as bank_f:
            rent_data = io.BytesIO(rent_f.read())
            bank_data = io.BytesIO(bank_f.read())

            # Вызываем нашу основную логику
            report_df = process_payment_files(rent_data, bank_data)

        # Сохраняем отчет в файл
        report_filename = f"payment_report_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
        report_filepath = os.path.join(REPORTS_DIR, report_filename)
        report_df.to_excel(report_filepath, index=False)

        print(f"Отчет успешно сгенерирован и сохранен: {report_filepath}")

        # Отправка в Telegram
        caption_text = f"Отчет по аренде на {datetime.now().strftime('%d.%m.%Y')}"
        await send_report_to_telegram(report_filepath, caption_text)

    except Exception as e:
        print(f"Произошла критическая ошибка при генерации отчета: {e}")


if __name__ == "__main__":
    asyncio.run(main())
