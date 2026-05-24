import streamlit as st
import pandas as pd
import sqlite3

# Налаштування сторінки
st.set_page_config(page_title="IoT Control Room", layout="wide")
st.title("🎛️ Кімната контролю ESP32")

# Шлях до твоєї бази даних
DB_PATH = "/app/data/climate_data.db"
# DB_PATH = "/home/spike/PycharmProjects/Projects/esp32_air_control/data/climate_data.db"

@st.cache_data(ttl=20)
def load_data():
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Помилка підключення до бази: {e}")
        return pd.DataFrame()


# Створення sidebar
with st.sidebar:
    st.sidebar.header("Налаштування")
    # Добавляємо вибір кількості вимірів
    num_records = st.sidebar.selectbox("Кількість:", (48, 144, 336))

# Створюємо запит до бази даних з кількістю вимірів
query = f"SELECT * FROM sensor_logs ORDER BY id DESC LIMIT {num_records}"

data = load_data()

with st.sidebar:
    # Button for download data like csv in sidebar
    csv = data.to_csv(index=False).encode('utf-8')
    st.download_button(label='⏬Завантажити дані як CSV', data=csv, file_name='filtered_sensor_data.csv', mime='text/csv')


if not data.empty:
    # Беремо найсвіжіший запис (перший у списку, бо ми сортували DESC)
    latest = data.iloc[0]

    # Ініціалізуємо змінні для дельти як None (якщо немає попереднього запису)
    d_temp = d_hum = d_press = d_gas = None

    # Перевіряємо, чи є в таблиці хоча б два записи, щоб порахувати різницю
    if len(data) >= 2:
        pre_latest = data.iloc[1]

        # Обчислюємо чисту різницю (поточне мінус попереднє)
        diff_temp = float(latest['temp']) - float(pre_latest['temp'])
        diff_hum = float(latest['hum']) - float(pre_latest['hum'])
        diff_press = float(latest['press']) - float(pre_latest['press'])
        diff_gas = float(latest['gas']) - float(pre_latest['gas'])

        # Форматуємо відображення дельти.
        # Специфікатор :+.1f автоматично додасть "+" для позитивних чисел і "-" для негативних
        d_temp = f"{diff_temp:+.1f} °C"
        d_hum = f"{diff_hum:+.1f} %"
        d_press = f"{diff_press:+.1f} hPa"
        d_gas = f"{diff_gas:+.1f} kOhm"

    # Відображення на сайті
    st.subheader(f"Останній вимір о: {latest['hour']}:{latest['minute']}")

    col1, col2, col3, col4 = st.columns(4)

    # Передаємо пораховані рядки в параметр delta
    col1.metric("Температура", f"{latest['temp']} °C", delta=d_temp)
    col2.metric("Вологість", f"{latest['hum']} %", delta=d_hum)
    col3.metric("Тиск", f"{latest['press']} hPa", delta=d_press)
    col4.metric("Газ (Опір)", f"{latest['gas']} kOhm", delta=d_gas)

    st.markdown("---")

    chart_data = data.set_index('timestamp')
    tab1, tab2, tab3, tab4 = st.tabs(["Температура", "Вологість", "Опір повітря", "Вся інформація"])
    with tab1:
        # Побудова графіка
        st.subheader(f"Графік температури (останні {num_records} вимірів)")
        # Робимо час індексом, щоб він гарно відображався на осі X
        st.line_chart(chart_data['temp'])
    with tab2:
        st.subheader(f"Графік вологості (останні {num_records} вимірів)")
        st.line_chart(chart_data['hum'])
    with tab3:
        st.subheader(f"Графік опіру (останні {num_records} вимірів)")
        st.line_chart(chart_data['gas'])
    with tab4:
        st.subheader(f"Всі остані {num_records} вимірів")
        st.dataframe(data)


    # Кнопка оновлення
    if st.button("🔄 Оновити дані"):
        st.rerun()

else:
    st.warning("База даних порожня або логер ще не записав дані.")
