# -*- coding: utf-8 -*-
# 模块1：数据看板
# 房价分布 | 趋势走势 | 热力地图 | 市场概览
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import base64
import os


def plt_close_safe():
    """安全关闭matplotlib图表以释放内存"""
    plt.close('all')


st.set_page_config(page_title='数据看板', page_icon='📊', layout='wide')

# 全局背景
BG_IMAGE_PATH = os.path.join(os.path.dirname(__file__), '..', 'bg.jpg')
if os.path.exists(BG_IMAGE_PATH):
    with open(BG_IMAGE_PATH, 'rb') as f:
        _bg_b64 = base64.b64encode(f.read()).decode()
    st.markdown(f'''
    <style>
    [data-testid="stAppViewContainer"] {{
        background: linear-gradient(rgba(255,255,255,0.92), rgba(255,255,255,0.92)),
                    url('data:image/jpeg;base64,{_bg_b64}');
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    </style>
    ''', unsafe_allow_html=True)

st.title('数据看板')
st.markdown('房价分布 | 趋势走势 | 热力地图 | 市场概览')

# CSS: 同行 border 容器强制等高
st.markdown('''
<style>
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    display: flex !important;
    flex-direction: column !important;
}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"] > [data-testid="stVerticalBlock"] {
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
}
[data-testid="stHorizontalBlock"] [data-testid="stVerticalBlockBorderWrapper"] {
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
}
[data-testid="stHorizontalBlock"] [data-testid="stVerticalBlockBorderWrapper"] > [data-testid="stVerticalBlock"] {
    flex: 1 !important;
}
</style>
''', unsafe_allow_html=True)

# ========== 侧边栏筛选 ==========
with st.sidebar:
    st.header('🔍 数据筛选')

    if 'cleaned_data' not in st.session_state or st.session_state.cleaned_data is None:
        st.warning('请先在首页加载数据')
        if st.button('🔄 在此加载数据'):
            from data_processor import load_and_clean_data
            with st.spinner('正在加载数据...'):
                df = load_and_clean_data('data/house_sales.csv')
                st.session_state.cleaned_data = df
            st.success(f'加载完成：{len(df):,} 条记录')
            st.rerun()
        st.stop()

    df = st.session_state.cleaned_data

    from data_processor import get_province_list, get_city_list, get_room_options

    # 省份筛选
    provinces = get_province_list(df)
    selected_province = st.selectbox('省份', options=provinces, key='dashboard_province')

    # 城市筛选（联动省份）
    cities = get_city_list(df, selected_province)
    selected_cities = st.multiselect('城市（可多选，留空=全部）', options=cities[1:], key='dashboard_cities')

    # 价格范围
    price_min = float(df['price_num'].min())
    price_max = float(df['price_num'].max())
    price_range = st.slider('价格范围（万元）',
                            min_value=price_min, max_value=price_max,
                            value=(price_min, min(500.0, price_max)),
                            step=10.0, key='dashboard_price')

    # 面积范围
    area_min = float(df['area_num'].min())
    area_max = float(df['area_num'].max())
    area_range = st.slider('面积范围（㎡）',
                           min_value=area_min, max_value=min(300.0, area_max),
                           value=(area_min, min(200.0, area_max)),
                           step=5.0, key='dashboard_area')

    # 户型筛选
    room_options = get_room_options(df)
    selected_rooms = st.multiselect('户型（留空=全部）', options=room_options, key='dashboard_rooms')

    # 年份范围
    year_min = int(df['year_num'].dropna().min())
    year_max = int(df['year_num'].dropna().max())
    year_range = st.slider('建成年份',
                           min_value=year_min, max_value=year_max,
                           value=(2000, year_max),
                           step=1, key='dashboard_year')

# ========== 应用筛选 ==========
filtered_df = df.copy()
if selected_province != '全部':
    filtered_df = filtered_df[filtered_df['province'] == selected_province]
if selected_cities:
    filtered_df = filtered_df[filtered_df['city'].isin(selected_cities)]
if selected_rooms:
    filtered_df = filtered_df[filtered_df['room_category'].isin(selected_rooms)]

filtered_df = filtered_df[
    (filtered_df['price_num'] >= price_range[0]) &
    (filtered_df['price_num'] <= price_range[1]) &
    (filtered_df['area_num'] >= area_range[0]) &
    (filtered_df['area_num'] <= area_range[1])
    ]

# 年份筛选（保留无年份数据的记录）
year_mask = (
        filtered_df['year_num'].isna() |
        ((filtered_df['year_num'] >= year_range[0]) & (filtered_df['year_num'] <= year_range[1]))
)
filtered_df = filtered_df[year_mask]

st.markdown(f'**当前筛选结果：{len(filtered_df):,} 条房源**')

# ========== KPI卡片行 ==========
st.markdown('---')
st.markdown('### 关键指标')
cols = st.columns(4)
cols[0].metric('筛选房源数', f'{len(filtered_df):,}套')
cols[1].metric('均价', f'{filtered_df["price_num"].mean():.1f}万元')
cols[2].metric('中位价', f'{filtered_df["price_num"].median():.1f}万元')
cols[3].metric('均单价', f'{filtered_df["unit_num"].mean():.0f}元/㎡')

cols2 = st.columns(4)
cols2[0].metric('平均面积', f'{filtered_df["area_num"].mean():.1f}㎡')
cols2[1].metric('平均房龄', f'{filtered_df["age"].dropna().mean():.1f}年'
                if filtered_df['age'].notna().sum() > 0 else '数据不足')
cols2[2].metric('覆盖城市', f'{filtered_df["city"].nunique()}个')
price_std = filtered_df['price_num'].std()
cols2[3].metric('价格标准差', f'{price_std:.1f}万元')

# ========== 图表区域 ==========
st.markdown('---')

# 第一行：价格分布 + 面积-房价散点图
col_left, col_right = st.columns(2, gap='medium')

with col_left:
    with st.container(border=True):
        st.markdown('#### 房价分布直方图')
        from visualizer import plot_price_distribution
        fig = plot_price_distribution(filtered_df)
        st.pyplot(fig)
        plt_close_safe()

with col_right:
    with st.container(border=True):
        st.markdown('#### 面积-房价关系')
        from visualizer import plot_area_price_scatter
        fig = plot_area_price_scatter(filtered_df)
        st.pyplot(fig)
        plt_close_safe()

# 第二行：年度趋势 + 户型分布
col_left2, col_right2 = st.columns(2, gap='medium')

with col_left2:
    with st.container(border=True):
        st.markdown('#### 年度房价趋势')
        from visualizer import plot_price_trend
        fig = plot_price_trend(filtered_df)
        st.pyplot(fig)
        plt_close_safe()

with col_right2:
    with st.container(border=True):
        st.markdown('#### 户型分布')
        from visualizer import plot_room_pie
        fig = plot_room_pie(filtered_df)
        st.pyplot(fig)
        plt_close_safe()

# 第三行：热力图
st.markdown('---')
st.markdown('### 户型×城市 单价热力图')
from visualizer import plot_unit_heatmap
try:
    fig = plot_unit_heatmap(filtered_df, top_n_cities=10)
    st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.warning(f'热力图渲染失败（可能plotly未安装）: {e}')

# 第四行：市场概览表
st.markdown('---')
st.markdown('### 市场概览')

# TOP城市表格
from data_processor import get_city_stats
city_stats = get_city_stats(filtered_df)

tab1, tab2 = st.tabs(['均价最高城市', '均价最低城市'])

with tab1:
    top_expensive = city_stats.nlargest(10, '均价_万元')[
        ['city', '均价_万元', '中位价_万元', '均单价_元每平', '挂牌量', '平均面积', '平均房龄']
    ]
    top_expensive.columns = ['城市', '均价(万元)', '中位价(万元)', '均单价(元/㎡)', '挂牌量', '平均面积(㎡)', '平均房龄(年)']
    top_expensive.index = range(1, len(top_expensive) + 1)
    st.dataframe(top_expensive.round(1), use_container_width=True)

with tab2:
    top_cheap = city_stats.nsmallest(10, '均价_万元')[
        ['city', '均价_万元', '中位价_万元', '均单价_元每平', '挂牌量', '平均面积', '平均房龄']
    ]
    top_cheap.columns = ['城市', '均价(万元)', '中位价(万元)', '均单价(元/㎡)', '挂牌量', '平均面积(㎡)', '平均房龄(年)']
    top_cheap.index = range(1, len(top_cheap) + 1)
    st.dataframe(top_cheap.round(1), use_container_width=True)

st.markdown('---')
st.caption('💡 提示：使用左侧筛选器可按省份、城市、价格、面积、户型、年份进行数据过滤，图表将实时更新。')
