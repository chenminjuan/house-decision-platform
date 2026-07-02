# -*- coding: utf-8 -*-
# 模块2：区域对比
# 多区域对比 | 维度筛选 | 指标排名 | 对比图表
import streamlit as st
import pandas as pd
import numpy as np
import base64
import os

st.set_page_config(page_title='区域对比', page_icon='🔍', layout='wide')

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

st.title('区域对比')
st.markdown('多区域对比 | 维度筛选 | 指标排名 | 对比图表')

# ========== 侧边栏：添加对比区域 ==========
with st.sidebar:
    st.header('添加对比区域')

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

    # 初始化对比列表
    if 'compare_regions' not in st.session_state:
        st.session_state.compare_regions = []

    from data_processor import get_province_list, get_city_list

    # 选择要添加的城市
    st.markdown('**选择城市添加到对比列表**')
    filter_province = st.selectbox('先选省份（可选）', options=['全部'] + get_province_list(df)[1:], key='comp_province')
    city_options = get_city_list(df, filter_province)
    selected_city = st.selectbox('选择城市', options=city_options[1:], key='comp_city_select')

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button('➕ 添加对比', use_container_width=True):
            if selected_city and selected_city not in st.session_state.compare_regions:
                if len(st.session_state.compare_regions) >= 5:
                    st.warning('最多对比5个城市！请先删除已有城市')
                else:
                    st.session_state.compare_regions.append(selected_city)
                    st.rerun()
            elif selected_city in st.session_state.compare_regions:
                st.info(f'{selected_city} 已在对比列表中')

    with col_btn2:
        if st.button('🗑️ 清空列表', use_container_width=True):
            st.session_state.compare_regions = []
            st.rerun()

    # 显示当前对比列表
    if st.session_state.compare_regions:
        st.markdown('**当前对比城市（最多5个）：**')
        for i, city in enumerate(st.session_state.compare_regions):
            col_name, col_del = st.columns([4, 1])
            with col_name:
                st.markdown(f'{i + 1}. **{city}**')
            with col_del:
                if st.button('✕', key=f'del_{i}'):
                    st.session_state.compare_regions.pop(i)
                    st.rerun()

    # 对比维度选择
    if st.session_state.compare_regions:
        st.markdown('---')
        st.markdown('**选择对比指标**')
        available_metrics = ['均价(万元)', '中位价(万元)', '均单价(元/㎡)', '挂牌量', '平均面积(㎡)', '平均房龄(年)', '价格标准差']
        selected_metrics = st.multiselect(
            '对比指标',
            options=available_metrics,
            default=['均价(万元)', '均单价(元/㎡)', '挂牌量', '平均面积(㎡)'],
            key='comp_metrics'
        )

# ========== 主区域 ==========
if not st.session_state.compare_regions:
    st.info('👈 请在左侧侧边栏添加要对比的城市（最多5个），选择城市后点击"添加对比"按钮')
    st.markdown('### 功能说明')
    st.markdown('''
    - **多区域并行对比**：同时比较最多5个城市的房价、单价、面积等关键指标
    - **雷达图**：从多维度直观展示各城市优劣势
    - **差异高亮**：在对比表中标注各城市与平均值的差异
    - **动态排序**：支持按不同指标排序查看排名
    ''')
    st.stop()

# ========== 获取对比数据 ==========
from data_processor import get_city_stats
city_stats = get_city_stats(df)
compare_data = city_stats[city_stats['city'].isin(st.session_state.compare_regions)]

# 如果某些城市数据不足
if len(compare_data) < len(st.session_state.compare_regions):
    missing = set(st.session_state.compare_regions) - set(compare_data['city'].tolist())
    st.warning(f'以下城市数据不足（挂牌量<30），无法完整对比：{", ".join(missing)}')

# ========== 对比KPI表格 ==========
st.markdown('---')
st.markdown('### 城市指标对比表')

# 准备对比表
comp_table = compare_data[['city', '均价_万元', '中位价_万元', '均单价_元每平', '挂牌量', '平均面积', '平均房龄', '价格标准差']].copy()
comp_table.columns = ['城市', '均价(万元)', '中位价(万元)', '均单价(元/㎡)', '挂牌量', '平均面积(㎡)', '平均房龄(年)', '价格标准差']

# 设置城市为索引
comp_table = comp_table.set_index('城市')

# 添加"与均值差异"行
avg_row = comp_table.mean()
comp_table.loc['【平均值】'] = avg_row

# 使用st.dataframe展示
st.dataframe(comp_table.round(1), use_container_width=True)

# 用st.metric展示关键差异
st.markdown('#### 与全国均值对比')
metric_cols = st.columns(len(st.session_state.compare_regions))
for i, (_, row) in enumerate(compare_data.iterrows()):
    with metric_cols[i]:
        delta_price = row['均价_万元'] - city_stats['均价_万元'].mean()
        st.metric(
            label=f'{row["city"]}均价',
            value=f'{row["均价_万元"]:.1f}万',
            delta=f'{delta_price:+.1f}万 vs 全国均值',
            delta_color='inverse'
        )

# ========== 图表区域 ==========
st.markdown('---')

# 雷达图
st.markdown('### 多维度雷达图对比')
from visualizer import plot_radar_chart

# 准备雷达图数据（归一化0-100）
radar_data = {}
for _, row in compare_data.iterrows():
    city_metrics = {}
    max_price = compare_data['均价_万元'].max()
    max_unit = compare_data['均单价_元每平'].max()
    max_count = compare_data['挂牌量'].max()
    max_std = compare_data['价格标准差'].max()

    city_metrics['均价水平'] = round(row['均价_万元'] / max_price * 100, 1) if max_price > 0 else 0
    city_metrics['单价水平'] = round(row['均单价_元每平'] / max_unit * 100, 1) if max_unit > 0 else 0
    city_metrics['市场供应'] = round(row['挂牌量'] / max_count * 100, 1) if max_count > 0 else 0
    # 性价比：单价越低越好
    city_metrics['性价比'] = round((1 - row['均单价_元每平'] / max_unit) * 100, 1) if max_unit > 0 else 0
    city_metrics['面积多样性'] = round(row['价格标准差'] / max_std * 100, 1) if max_std > 0 else 0

    radar_data[row['city']] = city_metrics

try:
    fig = plot_radar_chart(radar_data)
    st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.warning(f'雷达图需要plotly支持: {e}')

# 柱状图对比（多指标）
st.markdown('---')
st.markdown('### 关键指标柱状图对比')

# 用户选择的指标
metric_map = {
    '均价(万元)': '均价_万元',
    '中位价(万元)': '中位价_万元',
    '均单价(元/㎡)': '均单价_元每平',
    '挂牌量': '挂牌量',
    '平均面积(㎡)': '平均面积',
    '平均房龄(年)': '平均房龄',
    '价格标准差': '价格标准差',
}

if 'selected_metrics' in locals() and selected_metrics:
    chart_cols = st.columns(2)
    for idx, metric_label in enumerate(selected_metrics[:4]):
        metric_col = metric_map.get(metric_label, '均价_万元')
        with chart_cols[idx % 2]:
            from visualizer import plot_city_comparison_bars
            fig = plot_city_comparison_bars(df, st.session_state.compare_regions, metric=metric_col)
            st.pyplot(fig)
            import matplotlib.pyplot as plt
            plt.close('all')

# 单价排行（高亮已选城市）
st.markdown('---')
st.markdown('### 城市单价排行（高亮已选城市）')
from visualizer import plot_unit_price_ranking
fig = plot_unit_price_ranking(df, top_n=15, highlight_cities=st.session_state.compare_regions)
st.pyplot(fig)
import matplotlib.pyplot as plt
plt.close('all')

# 价格趋势对比
st.markdown('---')
st.markdown('### 价格趋势对比')
from visualizer import plot_multi_city_trend
fig = plot_multi_city_trend(df, st.session_state.compare_regions)
st.pyplot(fig)
plt.close('all')

# ========== 按户型的区域对比 ==========
st.markdown('---')
st.markdown('### 各户型价格对比')
room_cats = df['room_category'].dropna().unique().tolist()
selected_room = st.selectbox('选择户型查看', options=sorted(room_cats), key='comp_room')

if selected_room:
    room_df = df[df['room_category'] == selected_room]
    room_city_data = room_df[room_df['city'].isin(st.session_state.compare_regions)]
    if len(room_city_data) > 0:
        room_stats = room_city_data.groupby('city').agg(
            均价=('price_num', 'mean'),
            挂牌量=('price_num', 'count')
        ).reset_index()
        room_stats.columns = ['城市', '均价(万元)', '挂牌量']
        st.dataframe(room_stats.round(1).set_index('城市'), use_container_width=True)

st.markdown('---')
st.caption('💡 提示：在左侧侧边栏动态添加/删除对比城市（最多5个），图表会即时更新。雷达图展示各城市在多个维度的相对优劣势。')
