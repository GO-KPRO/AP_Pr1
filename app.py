import matplotlib.pyplot as plt
from datetime import datetime
import pandas as pd
import requests
import streamlit as st

seasonal_temperatures = {
    "New York": {"winter": 0, "spring": 10, "summer": 25, "autumn": 15},
    "London": {"winter": 5, "spring": 11, "summer": 18, "autumn": 12},
    "Paris": {"winter": 4, "spring": 12, "summer": 20, "autumn": 13},
    "Tokyo": {"winter": 6, "spring": 15, "summer": 27, "autumn": 18},
    "Moscow": {"winter": -10, "spring": 5, "summer": 18, "autumn": 8},
    "Sydney": {"winter": 12, "spring": 18, "summer": 25, "autumn": 20},
    "Berlin": {"winter": 0, "spring": 10, "summer": 20, "autumn": 11},
    "Beijing": {"winter": -2, "spring": 13, "summer": 27, "autumn": 16},
    "Rio de Janeiro": {"winter": 20, "spring": 25, "summer": 30, "autumn": 25},
    "Dubai": {"winter": 20, "spring": 30, "summer": 40, "autumn": 30},
    "Los Angeles": {"winter": 15, "spring": 18, "summer": 25, "autumn": 20},
    "Singapore": {"winter": 27, "spring": 28, "summer": 28, "autumn": 27},
    "Mumbai": {"winter": 25, "spring": 30, "summer": 35, "autumn": 30},
    "Cairo": {"winter": 15, "spring": 25, "summer": 35, "autumn": 25},
    "Mexico City": {"winter": 12, "spring": 18, "summer": 20, "autumn": 15},
}

month_to_season = {12: "winter", 1: "winter", 2: "winter",
                   3: "spring", 4: "spring", 5: "spring",
                   6: "summer", 7: "summer", 8: "summer",
                   9: "autumn", 10: "autumn", 11: "autumn"}

def sliding_window(data, size):
  sw = data['temperature'].rolling(window=size, center=True).mean()
  return data.drop(['temperature'], axis=1).join(sw).dropna()


def weather_now(city, api_key):
  url = "http://api.openweathermap.org/data/2.5/weather"
  params = {
      'q': city,
      'appid': api_key,
      'units': 'metric',
  }
  response = requests.get(url, params=params)
  if response.status_code != 200:
    return
  else:
    data = response.json()
    city = data['name']
    date = datetime.fromtimestamp(data['dt']).date()
    temperature = data['main']['temp']
    season = month_to_season[date.month]
    return pd.DataFrame({'city' : [city], 'timestamp' : [date], 'temperature' : [temperature], 'season' : [season]})

def api_check(api_key):
  url = "http://api.openweathermap.org/data/2.5/weather"
  params = {
      'q': 'Moscow',
      'appid': api_key,
      'units': 'metric',
  }
  response = requests.get(url, params=params)
  return response


def streamlit_outliers_plot(data, outliers):

    fig, ax = plt.subplots(figsize=(12, 4))
    time = map(lambda x: datetime.strptime(x, '%Y-%m-%d'), data['timestamp'])

    ax.plot(list(time),
            data['temperature'],
            alpha=0.3,
            linewidth=0.5,
            color='gray',
            label='Исходные данные')

    slidind_data = sliding_window(data, 30)
    time = map(lambda x: datetime.strptime(x, '%Y-%m-%d'), slidind_data['timestamp'])
    ax.plot(list(time),
            slidind_data['temperature'],
            linewidth=2,
            color='blue',
            label='Скользящее среднее (30 дней)')

    ax.scatter(outliers['timestamp'],
               outliers['temperature'],
               color='red', s=15, alpha=0.7, label='Выбросы')

    plt.gcf().autofmt_xdate()
    ax.set_xlabel("Дата")
    ax.set_ylabel("Температура (°C)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    st.pyplot(fig)


def streamlit_app():
    st.title('Прикладной Питон Проект №1')

    if 'valid_api_key' not in st.session_state:
        st.session_state['valid_api_key'] = None

    with st.form(key="api_form"):
        api_key = st.text_input(
            "Для работы с текущей погодой введите API ключ OpenWeatherMap:",
        )
        submit_api = st.form_submit_button("Проверить")
        if submit_api:
            check = api_check(api_key)
            if check.status_code == 200:
                st.success("API ключ корректен!")
                st.session_state['valid_api_key'] = api_key
            else:
                st.error(f"API ключ некорректен, сообщение: {check.json()}")

    if not st.session_state['valid_api_key']:
        st.write(f'Ожидание корректного api ключа')
    else:
        st.write(f'Используемый api ключ: {st.session_state['valid_api_key']}')
    uploaded_file = st.file_uploader("Загрузите файл с историческими данными о температуре", type=['csv'])

    if uploaded_file is not None:
        his_temp_data = pd.read_csv(uploaded_file)
        st.success("Файл успешно загружен!")

        st.subheader("Предпросмотр данных")
        st.write(pd.concat([his_temp_data.head(), his_temp_data.tail(5)]))

        cities_stats = his_temp_data.groupby(['city', 'season'])['temperature'].agg(['mean', 'std'])

        city_dict = {}
        if his_temp_data is not None:
            for name, data in his_temp_data.sort_values('timestamp').groupby('city'):
                city_dict[name] = data

            selected_city = st.selectbox(
                "Выберите город для анализа:",
                options=list(city_dict.keys()),
            )

            if selected_city:
                city_data = city_dict[selected_city]
                st.write(f"Количество записей: {len(city_data)}")

                #st.write(cities_stats.loc[selected_city])

                st.write('Средняя температура по сезонам')
                st.bar_chart(cities_stats.loc[selected_city]['mean'], )
                st.write('Стандартное отклонение температуры по сезонам')
                st.bar_chart(cities_stats.loc[selected_city]['std'])

                data_merged = his_temp_data.merge(cities_stats, on=['city', 'season'])
                outliers = data_merged[(data_merged['temperature'] - data_merged['mean']).abs() > 2 * data_merged['std']]
                outliers = outliers[outliers['city'] == selected_city]
                st.subheader(f"Исторический график температур для {selected_city}")
                streamlit_outliers_plot(city_data, outliers)

                if not st.session_state['valid_api_key']:
                    st.write('Для анализа текущей температуры предоставьте действующий ключ OpenWeatherMap API')
                else:
                    weather = weather_now(selected_city, api_key=st.session_state['valid_api_key'])
                    st.subheader(f"Текущая температура в {weather.loc[0]['city']}: {weather.loc[0]['temperature']}")
                    weather_merged = weather.merge(cities_stats, on=['city', 'season'])
                    current_outliers = weather_merged[(weather_merged['temperature'] - weather_merged['mean']).abs() > 2 * weather_merged['std']]

                    if len(current_outliers) == 0:
                        st.success(f'Эта температура нормальна для сезона {weather.loc[0]['season']}')
                    else:
                        st.warning(f'Температура выходит за рамки нормы для сезона {weather.loc[0]['season']}')
    else:
        st.info("Пожалуйста, загрузите CSV файл с данными для анализа")

if __name__ == '__main__':
    streamlit_app()

