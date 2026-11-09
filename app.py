import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# Настройка страницы
st.set_page_config(page_title="Анализ интернет-магазина", layout="wide")

# 1. Загрузка данных с кэшированием
@st.cache_data
def load_data():
    orders = pd.read_csv("orders.csv")
    users = pd.read_csv("users.csv")
    items = pd.read_csv("items.csv")
    return orders, users, items

orders, users, items = load_data()

# 2. Объединение таблиц
# orders + users по user_id
df = orders.merge(users, on="user_id", how="left")
# + items по item_id
df = df.merge(items, on="item_id", how="left")

# 3. Очистка и подготовка данных
# Заполняем пропуски в категориальных колонках
categorical_cols = ["category", "supplier", "city", "user_segment"]
for col in categorical_cols:
    if col in df.columns:
        df[col] = df[col].fillna("Unknown")

# Удаляем строки, где нет ключевых числовых данных
df = df.dropna(subset=["quantity", "price_per_unit", "base_price"])

# Приведение типов
df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
df = df.dropna(subset=["order_date"])

df["quantity"] = df["quantity"].astype(int)
df["price_per_unit"] = df["price_per_unit"].astype(float)
df["base_price"] = df["base_price"].astype(float)

# Расчёт выручки по каждой позиции заказа
df["revenue"] = df["quantity"] * df["price_per_unit"]

# Дополнительные колонки для анализа
df["day_of_week"] = df["order_date"].dt.day_name()
df["date"] = df["order_date"].dt.date

# Приложение
st.title("Анализ эффективности работы интернет-магазина")
st.markdown("---")

# Боковая панель с фильтрами
st.sidebar.header("Фильтры")
# Фильтр по категории
categories = ["Все"] + sorted(df["category"].unique().tolist())
selected_category = st.sidebar.selectbox("Выберите категорию товара", categories)

# Фильтр по дате
min_date = df["order_date"].min().date()
max_date = df["order_date"].max().date()
date_range = st.sidebar.date_input(
    "Выберите период",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Применение фильтров
filtered_df = df.copy()
if selected_category != "Все":
    filtered_df = filtered_df[filtered_df["category"] == selected_category]

if len(date_range) == 2:
    start_date, end_date = date_range
    filtered_df = filtered_df[
        (filtered_df["order_date"].dt.date >= start_date) &
        (filtered_df["order_date"].dt.date <= end_date)
    ]

# Создание вкладок
tab1, tab2, tab3, tab4 = st.tabs(
    ["Сырые данные", "Ключевые показатели", "Визуализация", "Аналитические выводы"]
)

# ВКЛАДКА 1: СЫРЫЕ ДАННЫЕ
with tab1:
    st.header("Сырые данные")
    st.markdown("Объединённая таблица заказов, пользователей и товаров (с учётом фильтров):")
    st.dataframe(filtered_df, use_container_width=True)
    
    st.markdown(f"**Размер отфильтрованных данных:** {filtered_df.shape[0]} строк, {filtered_df.shape[1]} колонок")
    
    # Краткая статистика
    with st.expander("Показать описательную статистику"):
        st.write(filtered_df.describe())

# ВКЛАДКА 2: КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ
with tab2:
    st.header("Ключевые показатели")
    
    if filtered_df.empty:
        st.warning("Нет данных для отображения. Измените фильтры.")
    else:
        # Расчёт метрик
        total_orders = filtered_df["order_id"].nunique()
        total_revenue = filtered_df["revenue"].sum()
        unique_users = filtered_df["user_id"].nunique()
        avg_check = total_revenue / total_orders if total_orders > 0 else 0
        
        # Отображение метрик в колонках
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Общее количество заказов", f"{total_orders:,}")
        col2.metric("Общая выручка", f"{total_revenue:,.2f} ₽")
        col3.metric("Уникальные пользователи", f"{unique_users:,}")
        col4.metric("Средний чек", f"{avg_check:,.2f} ₽")
        
        st.markdown("---")
        
        st.subheader("Дополнительные показатели")
        col5, col6, col7 = st.columns(3)
        
        total_items_sold = filtered_df["quantity"].sum()
        avg_items_per_order = total_items_sold / total_orders if total_orders > 0 else 0
        
        col5.metric("Продано единиц товара", f"{total_items_sold:,}")
        col6.metric("Среднее кол-во товаров в заказе", f"{avg_items_per_order:.2f}")
        col7.metric("Уникальных товаров", f"{filtered_df['item_id'].nunique():,}")

#ВКЛАДКА 3: ВИЗУАЛИЗАЦИЯ
with tab3:
    st.header("Визуализация данных")
    
    if filtered_df.empty:
        st.warning("Нет данных для отображения. Измените фильтры.")
    else:
        # График 1: Топ-10 товаров по выручке
        st.subheader("Топ-10 товаров по выручке")
        
        top_items = (
            filtered_df.groupby("item_name")["revenue"]
            .sum()
            .sort_values(ascending=True)
            .tail(10)
        )
        
        fig1, ax1 = plt.subplots(figsize=(10, 6))
        ax1.barh(top_items.index, top_items.values, color="steelblue")
        ax1.set_xlabel("Выручка, ₽")
        ax1.set_title("Топ-10 товаров по выручке")
        ax1.grid(axis="x", linestyle="--", alpha=0.7)
        plt.tight_layout()
        st.pyplot(fig1)
        
        # График 2: Выручка по категориям ---
        st.subheader("Выручка по категориям товаров")
        
        category_revenue = (
            filtered_df.groupby("category")["revenue"]
            .sum()
            .sort_values(ascending=False)
        )
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            # Круговая диаграмма
            fig2, ax2 = plt.subplots(figsize=(8, 8))
            ax2.pie(
                category_revenue.values,
                labels=category_revenue.index,
                autopct="%1.1f%%",
                startangle=90,
                colors=plt.cm.Set3.colors[:len(category_revenue)]
            )
            ax2.set_title("Доля категорий в общей выручке")
            plt.tight_layout()
            st.pyplot(fig2)
        
        with col_b:
            # Столбчатая диаграмма
            fig3, ax3 = plt.subplots(figsize=(8, 8))
            ax3.bar(category_revenue.index, category_revenue.values, color="coral")
            ax3.set_xlabel("Категория")
            ax3.set_ylabel("Выручка, ₽")
            ax3.set_title("Выручка по категориям")
            ax3.tick_params(axis="x", rotation=45)
            ax3.grid(axis="y", linestyle="--", alpha=0.7)
            plt.tight_layout()
            st.pyplot(fig3)
        
        # График 3: Зависимость количества заказов от дня недели
        st.subheader("Зависимость количества заказов от дня недели")
        
        # Порядок дней недели
        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_names_ru = {
            "Monday": "Пн", "Tuesday": "Вт", "Wednesday": "Ср",
            "Thursday": "Чт", "Friday": "Пт", "Saturday": "Сб", "Sunday": "Вс"
        }
        
        orders_by_day = (
            filtered_df.groupby("day_of_week")["order_id"]
            .nunique()
            .reindex(day_order, fill_value=0)
        )
        orders_by_day.index = [day_names_ru[d] for d in orders_by_day.index]
        
        fig4, ax4 = plt.subplots(figsize=(10, 5))
        ax4.plot(orders_by_day.index, orders_by_day.values, marker="o", 
                 color="green", linewidth=2, markersize=8)
        ax4.fill_between(orders_by_day.index, orders_by_day.values, alpha=0.2, color="green")
        ax4.set_xlabel("День недели")
        ax4.set_ylabel("Количество заказов")
        ax4.set_title("Количество заказов по дням недели")
        ax4.grid(linestyle="--", alpha=0.7)
        plt.tight_layout()
        st.pyplot(fig4)
        
        # График 4: Выручка по дням
        st.subheader("Динамика выручки по дням")
        
        revenue_by_date = (
            filtered_df.groupby("date")["revenue"]
            .sum()
            .sort_index()
        )
        
        fig5, ax5 = plt.subplots(figsize=(12, 5))
        ax5.plot(revenue_by_date.index, revenue_by_date.values, 
                 marker="s", color="purple", linewidth=2)
        ax5.set_xlabel("Дата")
        ax5.set_ylabel("Выручка, ₽")
        ax5.set_title("Динамика выручки по дням")
        ax5.grid(linestyle="--", alpha=0.7)
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig5)

# ВКЛАДКА 4: АНАЛИТИЧЕСКИЕ ВЫВОДЫ
with tab4:
    st.header("Аналитические выводы")
    
    if filtered_df.empty:
        st.warning("Нет данных для формирования выводов. Измените фильтры.")
    else:
        # Расчёт данных для выводов
        total_revenue = filtered_df["revenue"].sum()
        total_orders = filtered_df["order_id"].nunique()
        unique_users = filtered_df["user_id"].nunique()
        avg_check = total_revenue / total_orders if total_orders > 0 else 0
        
        # Топ-товар
        top_item = (
            filtered_df.groupby("item_name")["revenue"]
            .sum()
            .sort_values(ascending=False)
        )
        top_item_name = top_item.index[0] if len(top_item) > 0 else "Н/Д"
        top_item_revenue = top_item.values[0] if len(top_item) > 0 else 0
        
        # Топ-категория
        top_category = (
            filtered_df.groupby("category")["revenue"]
            .sum()
            .sort_values(ascending=False)
        )
        top_category_name = top_category.index[0] if len(top_category) > 0 else "Н/Д"
        top_category_revenue = top_category.values[0] if len(top_category) > 0 else 0
        top_category_share = (top_category_revenue / total_revenue * 100) if total_revenue > 0 else 0
        
        # Пик заказов по дням недели
        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_names_ru = {
            "Monday": "понедельник", "Tuesday": "вторник", "Wednesday": "среда",
            "Thursday": "четверг", "Friday": "пятница", "Saturday": "суббота", "Sunday": "воскресенье"
        }
        orders_by_day = (
            filtered_df.groupby("day_of_week")["order_id"]
            .nunique()
            .reindex(day_order, fill_value=0)
        )
        peak_day = orders_by_day.idxmax() if not orders_by_day.empty else "Н/Д"
        peak_day_ru = day_names_ru.get(peak_day, peak_day)
        peak_day_orders = orders_by_day.max() if not orders_by_day.empty else 0
        
        # Топ-город
        top_city = (
            filtered_df.groupby("city")["revenue"]
            .sum()
            .sort_values(ascending=False)
        )
        top_city_name = top_city.index[0] if len(top_city) > 0 else "Н/Д"
        
        # Топ-сегмент пользователей
        top_segment = (
            filtered_df.groupby("user_segment")["revenue"]
            .sum()
            .sort_values(ascending=False)
        )
        top_segment_name = top_segment.index[0] if len(top_segment) > 0 else "Н/Д"
        
        # Формирование выводов
        st.markdown(f"""
        ### Основные выводы по результатам анализа

        1. Общие показатели:
        - Общая выручка за период составила {total_revenue:,.2f} ₽
        - Всего оформлено {total_orders:,} заказов
        - Количество уникальных покупателей — {unique_users:,} человек
        - Средний чек — {avg_check:,.2f} ₽

        2. Лидеры продаж:
        - Товар-лидер по выручке: {top_item_name} ({top_item_revenue:,.2f} ₽)
        - Категория-лидер: {top_category_name} — {top_category_share:.1f}% от общей выручки
        - Наибольшая выручка приходится на город: {top_city_name}
        - Ведущий сегмент пользователей: {top_segment_name}

        3. Сезонность и активность:
        - Пик заказов наблюдается в {peak_day_ru} ({peak_day_orders} заказов)
        - Наблюдается неравномерность распределения заказов по дням недели

        4. Рекомендации:
        - Усилить маркетинговые активности в дни с низкой активностью
        - Обратить внимание на развитие категории «{top_category_name}» как основного драйвера выручки
        - Рассмотреть программы лояльности для сегмента «{top_segment_name}»
        - Проанализировать ассортимент товаров с низкими продажами для оптимизации складских запасов
        """)
        
        # Дополнительная информация
        with st.expander("Детальная статистика по категориям"):
            category_stats = filtered_df.groupby("category").agg(
                Выручка=("revenue", "sum"),
                Заказы=("order_id", "nunique"),
                Средний_чек=("revenue", lambda x: x.sum() / filtered_df.loc[x.index, "order_id"].nunique())
            ).sort_values("Выручка", ascending=False)
            st.dataframe(category_stats.style.format("{:,.2f}"))
        
        with st.expander("Статистика по сегментам пользователей"):
            segment_stats = filtered_df.groupby("user_segment").agg(
                Выручка=("revenue", "sum"),
                Заказы=("order_id", "nunique"),
                Пользователи=("user_id", "nunique")
            ).sort_values("Выручка", ascending=False)
            st.dataframe(segment_stats.style.format("{:,.2f}"))

# Футер
st.markdown("---")
st.markdown("*Дашборд создан в рамках итоговой работы по анализу эффективности интернет-магазина*")