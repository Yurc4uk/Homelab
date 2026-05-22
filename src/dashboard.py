import streamlit as st
import pandas as pd
import sqlite3

# Налаштування сторінки
st.set_page_config(page_title="IoT Control Room", layout="wide")
st.title("🎛️ Кімната контролю ESP32")

# Шлях до твоєї бази даних
DB_PATH = "/home/astarion/Projects/esp32_air_control/data/climate_data.db"

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

    st.subheader("Поточний стан")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Температура", f"{latest['temp']} °C")
    col2.metric("Вологість", f"{latest['hum']} %")
    col3.metric("Тиск", f"{latest['press']} hPa")
    col4.metric("Газ (Опір)", f"{latest['gas']} kOhm")

    st.markdown("---")
    
    chart_data = data.set_index('timestamp')
    tab1, tab2, tab3 = st.tabs(["Температура", "Вологість", "Вся інформація"])
    with tab1:
        # Побудова графіка
        st.subheader(f"Графік температури (останні {num_records} вимірів)")
        # Робимо час індексом, щоб він гарно відображався на осі X
        st.line_chart(chart_data['temp'])
    with tab2:
        st.subheader(f"Графік вологості (останні {num_records} вимірів)")
        st.line_chart(chart_data['hum'])
    with tab3:
        st.subheader(f"Всі остані {num_records} вимірів")
        st.dataframe(data)


    # Кнопка оновлення
    if st.button("🔄 Оновити дані"):
        st.rerun()

else:
    st.warning("База даних порожня або логер ще не записав дані.")
