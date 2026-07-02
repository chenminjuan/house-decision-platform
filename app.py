# -*- coding: utf-8 -*-
# 房地产购房决策辅助平台 - 主入口
# Streamlit 原生多页面机制：pages/ 目录下的文件自动发现

import streamlit as st
import base64
import os

# ========== 页面配置 ==========
st.set_page_config(
    page_title='房地产购房决策辅助平台',
    layout='wide',
    initial_sidebar_state='expanded',
)

# ========== 全局背景 ==========
BG_IMAGE_PATH = os.path.join(os.path.dirname(__file__), 'bg.jpg')
if os.path.exists(BG_IMAGE_PATH):
    with open(BG_IMAGE_PATH, 'rb') as f:
        bg_base64 = base64.b64encode(f.read()).decode()
    st.markdown(f'''
    <style>
    [data-testid="stAppViewContainer"] {{
        background: linear-gradient(rgba(255,255,255,0.92), rgba(255,255,255,0.92)),
                    url('data:image/jpeg;base64,{bg_base64}');
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    /* 侧边栏保持纯白 */
    [data-testid="stSidebar"] > div:first-child {{
        background: rgba(255,255,255,0.92);
    }}
    </style>
    ''', unsafe_allow_html=True)

# ========== 首页内容 ==========
st.markdown('<h1 style="font-size: 2.5rem;">房地产购房决策辅助平台</h1>', unsafe_allow_html=True)
st.markdown('---')

# 欢迎区域：三列功能入口
st.markdown('<h3>选择功能模块开始分析</h3>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3, gap='medium')

with col1:
    st.markdown('''
    <div style="background: #FFFFFF; border-radius: 12px; padding: 22px 24px;
                box-shadow: 0 2px 12px rgba(0,0,0,0.06); border-left: 4px solid #165DFF;">
        <div style="font-weight: 700; font-size: 17px; color: #1D2129; margin-bottom: 4px;">数据看板</div>
        <div style="color: #86909C; font-size: 12px;">房价分布・趋势走势・热力地图・市场概览</div>
    </div>
    ''', unsafe_allow_html=True)
    st.page_link('pages/01_数据看板.py', label='进入数据看板 →', use_container_width=True)

with col2:
    st.markdown('''
    <div style="background: #FFFFFF; border-radius: 12px; padding: 22px 24px;
                box-shadow: 0 2px 12px rgba(0,0,0,0.06); border-left: 4px solid #7B61FF;">
        <div style="font-weight: 700; font-size: 17px; color: #1D2129; margin-bottom: 4px;">区域对比</div>
        <div style="color: #86909C; font-size: 12px;">多区域对比・维度筛选・指标排名・对比图表</div>
    </div>
    ''', unsafe_allow_html=True)
    st.page_link('pages/02_区域对比.py', label='进入区域对比 →', use_container_width=True)

with col3:
    st.markdown('''
    <div style="background: #FFFFFF; border-radius: 12px; padding: 22px 24px;
                box-shadow: 0 2px 12px rgba(0,0,0,0.06); border-left: 4px solid #00B4D8;">
        <div style="font-weight: 700; font-size: 17px; color: #1D2129; margin-bottom: 4px;">决策报告</div>
        <div style="color: #86909C; font-size: 12px;">个性化报告・投资评估・风险提示・推荐方案</div>
    </div>
    ''', unsafe_allow_html=True)
    st.page_link('pages/03_决策报告.py', label='进入决策报告 →', use_container_width=True)

st.markdown('---')

# 平台介绍
st.markdown('''
### 平台功能说明

本平台基于 **10.6万+** 二手房源数据，为购房者提供数据驱动的决策支持：

| 模块 | 功能亮点 | 适合场景 |
|------|----------|----------|
| **数据看板** | 房价KPI仪表盘、价格分布、趋势分析、市场热力图 | 快速了解整体市场行情 |
| **区域对比** | 多城市并行对比、雷达图、差异高亮、动态排序 | 在多区域间做选择比较 |
| **决策报告** | 个性化偏好匹配、智能评分推荐、投资评估、风险提示 | 明确购房需求后精准决策 |
''')

st.markdown('---')

# 数据加载区域
st.markdown('### 数据加载')

if st.button('🔄 加载/刷新数据', help='加载并清洗房源数据（首次加载可能需要几十秒）'):
    with st.spinner('正在加载和清洗数据...'):
        from data_processor import load_and_clean_data
        df = load_and_clean_data('data/house_sales.csv')
        st.session_state.cleaned_data = df
    st.success(f'✅ 数据加载完成！共 {len(df):,} 条有效房源记录，覆盖 {df["city"].nunique()} 个城市')

# 如果有数据，显示概览
if 'cleaned_data' in st.session_state and st.session_state.cleaned_data is not None:
    df = st.session_state.cleaned_data
    from data_processor import get_summary_stats
    stats = get_summary_stats(df)
    st.markdown('### 全国房产市场概览')
    cols = st.columns(4)
    cols[0].metric('总挂牌量', f'{stats["总挂牌量"]:,}套')
    cols[1].metric('全国均价', f'{stats["均价(万元)"]}万')
    cols[2].metric('均单价', f'{stats["均单价(元/㎡)"]:.0f}元/㎡')
    cols[3].metric('覆盖城市', f'{stats["覆盖城市数"]}个')
    cols2 = st.columns(4)
    cols2[0].metric('中位价', f'{stats["中位价(万元)"]}万')
    cols2[1].metric('平均面积', f'{stats["平均面积(㎡)"]}㎡')
    cols2[2].metric('平均房龄', f'{stats["平均房龄(年)"]}年')
    cols2[3].metric('覆盖省份', f'{stats["覆盖省份数"]}个')
else:
    st.info('👆 请点击上方按钮加载数据，或使用左侧导航进入各功能模块（页面内也可加载数据）')
