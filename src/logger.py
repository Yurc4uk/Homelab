import serial
import time
import sqlite3
import os
import logging # Додаємо бібліотеку для логування

# --- НАЛАШТУВАННЯ ЛОГУВАННЯ ---
LOG_FILE = "/home/astarion/Projects/esp32_air_control/logs/server.log"

# Гарантуємо, що папка для логів існує, якщо раптом її немає
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
# ------------------------------

PORT = "/dev/ttyUSB0"
BAUD_RATE = 115200
DB_PATH = "/app/data/climate_data.db"

def init_db():
    """Ініціалізація бази даних та створення таблиці"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            year INTEGER,
            month INTEGER,
            day INTEGER,
            hour INTEGER,
            minute INTEGER,
            second INTEGER,
            temp REAL,
            hum REAL,
            press REAL,
            gas REAL,
            alt REAL
        )
    ''')
    conn.commit()
    return conn

try:
    ser = serial.Serial(PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    # Замінюємо print на logging.info
    logging.info(f"З'єднано з {PORT}. Починаю збір даних з BME680...")

    db_conn = init_db()
    cursor = db_conn.cursor()

    while True:
        if ser.in_waiting > 0:
            try:
                line = ser.readline().decode('utf-8').strip()

                if line.startswith("DATA,"):
                    parts = line.split(",")

                    temp, hum, press, gas, alt = map(float, parts[1:])

                    now = time.localtime()
                    iso_time = time.strftime("%Y-%m-%d %H:%M:%S", now)

                    year = int(time.strftime("%Y", now))
                    month = int(time.strftime("%m", now))
                    day = int(time.strftime("%d", now))
                    hour = int(time.strftime("%H", now))
                    minute = int(time.strftime("%M", now))
                    second = int(time.strftime("%S", now))

                    cursor.execute('''
                        INSERT INTO sensor_logs (
                            timestamp, year, month, day, hour, minute, second, 
                            temp, hum, press, gas, alt
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (iso_time, year, month, day, hour, minute, second, temp, hum, press, gas, alt))

                    db_conn.commit()

                    # Замінюємо print на logging.info
                    logging.info(f"Збережено в БД: Час={iso_time}, T={temp}°C, G={gas}kOhm")

            except Exception as e:
                # Помилки записуємо як logging.error
                logging.error(f"Помилка обробки рядка: {e}")

        time.sleep(0.1)

except KeyboardInterrupt:
    logging.info("Зупинка запису користувачем.")

finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()
        logging.info("Порт закритий.")
    if 'db_conn' in locals():
        db_conn.close()
        logging.info("З'єднання з базою даних закрито.")
