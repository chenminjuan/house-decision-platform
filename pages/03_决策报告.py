# -*- coding: utf-8 -*-
# 模块3：决策报告
# 个性化报告 | 投资评估 | 风险提示 | 推荐方案
import streamlit as st
import pandas as pd
import numpy as np
import base64
import os

st.set_page_config(page_title='决策报告', page_icon='📝', layout='wide')

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

st.title('决策报告')
st.markdown('个性化推荐 | 投资评估 | 风险提示 | 推荐方案')

# ========== 数据检查 ==========
if 'cleaned_data' not in st.session_state or st.session_state.cleaned_data is None:
    st.warning('请先在首页加载数据')
    if st.button('🔄 加载数据'):
        from data_processor import load_and_clean_data
        with st.spinner('正在加载数据...'):
            df = load_and_clean_data('data/house_sales.csv')
            st.session_state.cleaned_data = df
        st.success(f'加载完成：{len(df):,} 条记录')
        st.rerun()
    st.stop()

df = st.session_state.cleaned_data

# ========== 初始化Session State ==========
if 'report_preferences' not in st.session_state:
    st.session_state.report_preferences = {}
if 'report_results' not in st.session_state:
    st.session_state.report_results = None
if 'report_generated' not in st.session_state:
    st.session_state.report_generated = False

# ========== Step 1: 偏好设置表单 ==========
st.markdown('---')
st.markdown('### Step 1: 填写购房偏好')

with st.form('preferences_form'):
    st.markdown('#### 预算与面积')

    col1, col2, col3 = st.columns(3)
    with col1:
        budget_min = st.number_input('最低预算（万元）', min_value=0, value=50, step=10)
    with col2:
        budget_max = st.number_input('最高预算（万元）', min_value=0, value=200, step=10)
    with col3:
        max_unit_price = st.number_input('最高单价（元/㎡）', min_value=1000, value=50000, step=1000)

    col_a1, col_a2 = st.columns(2)
    with col_a1:
        area_min = st.number_input('最小面积（㎡）', min_value=10, value=70, step=5)
    with col_a2:
        area_max = st.number_input('最大面积（㎡）', min_value=10, value=130, step=5)

    st.markdown('#### 户型与朝向')

    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        preferred_rooms = st.selectbox('室数', options=[1, 2, 3, 4, 5], index=2)
    with col_r2:
        preferred_halls = st.selectbox('厅数', options=[0, 1, 2], index=1)
    with col_r3:
        toward_options = df['toward'].dropna().unique().tolist()
        preferred_toward = st.multiselect('期望朝向', options=toward_options,
                                          default=['南向', '南北向'] if '南向' in toward_options else toward_options[:2])

    st.markdown('#### 房龄与年份')

    col_y1, col_y2 = st.columns(2)
    with col_y1:
        year_min = st.number_input('最早建成年份', min_value=1949, max_value=2025, value=2000, step=1)
    with col_y2:
        year_max = st.number_input('最晚建成年份', min_value=1949, max_value=2025, value=2025, step=1)

    st.markdown('#### 区域偏好')

    from data_processor import get_province_list, get_city_list

    col_loc1, col_loc2 = st.columns(2)
    with col_loc1:
        pref_province = st.selectbox('省份（可选）', options=get_province_list(df), key='report_province')
    with col_loc2:
        city_options = get_city_list(df, pref_province)
        preferred_locations = st.multiselect('期望城市（可多选，留空=全国）',
                                             options=city_options[1:],
                                             help='选择具体城市或留空搜索全国')

    st.markdown('#### 各维度重要性权重（0-100，总和不要求=100，将自动归一化）')

    col_w1, col_w2, col_w3, col_w4, col_w5 = st.columns(5)
    with col_w1:
        w_price = st.slider('价格因素', 0, 100, 70, help='价格越低越好的重视程度')
    with col_w2:
        w_area = st.slider('面积匹配', 0, 100, 40, help='面积接近理想的重视程度')
    with col_w3:
        w_age = st.slider('房龄新旧', 0, 100, 50, help='房龄越新越好的重视程度')
    with col_w4:
        w_unit = st.slider('单价合理性', 0, 100, 60, help='单价越低的重视程度')
    with col_w5:
        w_location = st.slider('地段热度', 0, 100, 30, help='市场活跃度的重视程度')

    submitted = st.form_submit_button('🔍 生成决策报告', type='primary', use_container_width=True)

    if submitted:
        if budget_min >= budget_max:
            st.error('最低预算不能大于等于最高预算！')
        elif area_min >= area_max:
            st.error('最小面积不能大于等于最大面积！')
        else:
            preferences = {
                'budget_min': budget_min,
                'budget_max': budget_max,
                'area_min': area_min,
                'area_max': area_max,
                'preferred_rooms': preferred_rooms,
                'preferred_halls': preferred_halls,
                'year_min': year_min,
                'year_max': year_max,
                'max_unit_price': max_unit_price,
                'preferred_toward': preferred_toward,
                'preferred_locations': preferred_locations,
                'preferred_province': pref_province if pref_province != '全部' else None,
            }
            weights = {
                'w_price': w_price,
                'w_area': w_area,
                'w_age': w_age,
                'w_unit': w_unit,
                'w_location': w_location,
            }

            st.session_state.report_preferences = preferences
            st.session_state.report_weights = weights

            with st.spinner('正在分析匹配房源，请稍候...'):
                from decision_engine import hard_filter, compute_matching_score, generate_report_data

                filtered = hard_filter(df, preferences)
                st.info(f'硬筛选通过：{len(filtered):,} 套房源')

                if len(filtered) > 0:
                    scored = compute_matching_score(filtered, df, weights)
                    report = generate_report_data(preferences, scored, df)
                    st.session_state.report_results = report
                    st.session_state.report_generated = True
                else:
                    st.session_state.report_results = {
                        'preferences': preferences,
                        'match_count': 0,
                        'message': '根据您的偏好未找到匹配房源，请放宽筛选条件后重试。'
                    }
                    st.session_state.report_generated = True

            st.rerun()

# ========== Step 2: 报告展示 ==========
if st.session_state.report_generated and st.session_state.report_results:
    report = st.session_state.report_results

    if report.get('match_count', 0) == 0:
        st.error(report.get('message', '无匹配结果'))
        st.markdown('### 建议调整方向')
        st.markdown('- 扩大预算范围')
        st.markdown('- 减少面积限制')
        st.markdown('- 放宽房龄要求')
        st.markdown('- 增加更多可选城市')
        st.stop()

    st.markdown('---')
    st.markdown('### Step 2: 决策报告结果')

    # ===== 匹配概览 =====
    st.markdown('#### 匹配房源概览')
    overview_cols = st.columns(4)
    overview_cols[0].metric('匹配房源数', f'{report["match_count"]:,}套')
    overview_cols[1].metric('覆盖城市', f'{report["match_cities"]}个')
    overview_cols[2].metric('匹配均价', f'{report["avg_price"]}万')
    overview_cols[3].metric('匹配均单价', f'{report["avg_unit"]:.0f}元/㎡')

    ov2 = st.columns(3)
    ov2[0].metric('匹配均面积', f'{report["avg_area"]}㎡')
    prefs = st.session_state.report_preferences
    budget_mid = (prefs['budget_min'] + prefs['budget_max']) / 2
    price_diff = report['avg_price'] - budget_mid
    ov2[1].metric('vs 预算中位', f'{budget_mid:.0f}万', delta=f'{price_diff:+.1f}万', delta_color='inverse')
    ov2[2].metric('vs 面积中位', f'{(prefs["area_min"] + prefs["area_max"]) / 2:.0f}㎡',
                   delta=f'{report["avg_area"] - (prefs["area_min"] + prefs["area_max"]) / 2:+.1f}㎡',
                   delta_color='off')

    # ===== 得分分解 =====
    st.markdown('---')
    st.markdown('#### 各维度得分分解（Top5平均）')
    from visualizer import plot_score_breakdown
    score_breakdown = report.get('score_breakdown', {})
    if score_breakdown:
        fig = plot_score_breakdown(score_breakdown)
        st.pyplot(fig)
        import matplotlib.pyplot as plt
        plt.close('all')

    # ===== Top推荐列表 =====
    st.markdown('---')
    st.markdown('#### Top 20 推荐房源')
    top_listings = report.get('top_listings', pd.DataFrame())
    if len(top_listings) > 0:
        display_df = top_listings.copy()
        st.dataframe(
            display_df.style.background_gradient(subset=['综合得分'], cmap='RdYlGn'),
            use_container_width=True,
            hide_index=True
        )

        st.markdown('**得分Top3房源卡片：**')
        top3_cols = st.columns(3)
        medals = ['🥇', '🥈', '🥉']
        for i in range(min(3, len(display_df))):
            row = display_df.iloc[i]
            with top3_cols[i]:
                st.markdown(f'''
                <div style="background: #f8f9fa; border-radius: 10px; padding: 15px;
                            border-left: 4px solid {'#FFD700' if i==0 else '#C0C0C0' if i==1 else '#CD7F32'};">
                    <h3>{medals[i]} {row.get("小区名称", "--")}</h3>
                    <p><b>城市：</b>{row.get("城市", "--")} | <b>得分：</b>{row.get("综合得分", "--")}</p>
                    <p><b>总价：</b>{row.get("总价(万)", "--")}万 | <b>面积：</b>{row.get("面积(㎡)", "--")}㎡</p>
                    <p><b>户型：</b>{row.get("户型", "--")} | <b>朝向：</b>{row.get("朝向", "--")}</p>
                    <p><b>单价：</b>{row.get("单价(元/㎡)", "--")}元/㎡ | <b>年份：</b>{row.get("建成年份", "--")}</p>
                </div>
                ''', unsafe_allow_html=True)

    # ===== 投资评估 =====
    st.markdown('---')
    st.markdown('#### 投资评估')
    investment = report.get('investment', {})
    st.markdown(investment.get('summary', '--'))

    city_trends = investment.get('city_trends', {})
    if city_trends:
        st.markdown('**主要城市价格趋势：**')
        trend_data = []
        for city, trend in city_trends.items():
            trend_data.append({
                '城市': city,
                '年均涨幅(%)': trend.get('年均涨幅(%)', 0),
                '年均涨幅(万/年)': trend.get('年均涨幅(万元/年)', 0),
                '最新均价(万元)': trend.get('最新均价(万元)', 0),
                '数据年份': trend.get('数据年份数', 0)
            })
        trend_df = pd.DataFrame(trend_data)
        st.dataframe(trend_df.set_index('城市').round(2), use_container_width=True)

    unit_analysis = investment.get('unit_analysis', {})
    if unit_analysis:
        st.markdown('**单价分析：**')
        ua_cols = st.columns(3)
        ua_cols[0].metric('匹配中位单价', f'{unit_analysis.get("匹配房源中位单价", "--")}', '元/㎡')
        ua_cols[1].metric('全国中位单价', f'{unit_analysis.get("全国中位单价", "--")}', '元/㎡')
        ua_cols[2].metric('性价比评估', unit_analysis.get('性价比评估', '--'))

    city_liquidity = investment.get('city_liquidity', {})
    if city_liquidity:
        st.markdown('**城市流动性：**')
        liq_data = []
        for city, info in city_liquidity.items():
            liq_data.append({'城市': city, '挂牌量': info['挂牌量'], '流动性': info['流动性']})
        liq_df = pd.DataFrame(liq_data)
        st.dataframe(liq_df.set_index('城市'), use_container_width=True)

    # ===== 风险评估 =====
    st.markdown('---')
    st.markdown('#### 风险评估')
    risk_overview = report.get('risk_overview', {})
    if risk_overview:
        safety_score = risk_overview.get('安全评分', 0)
        safety_color = 'green' if safety_score >= 80 else ('orange' if safety_score >= 60 else 'red')
        st.markdown(f'**综合安全评分：<span style="color:{safety_color};font-size:24px;">{safety_score}分</span>**',
                    unsafe_allow_html=True)
        st.markdown(f'**评估结论：** {risk_overview.get("评估结论", "--")}')

        risk_counts = risk_overview.get('风险分布', {})
        if risk_counts:
            st.markdown('**风险类型分布：**')
            risk_cols = st.columns(len(risk_counts))
            for i, (risk_type, count) in enumerate(risk_counts.items()):
                with risk_cols[i]:
                    st.metric(risk_type, f'{count}次', delta=f'Top{risk_overview.get("检查房源数", "--")}套中')

    # ===== 导出 =====
    st.markdown('---')
    st.markdown('#### 导出报告')
    col_export, col_reset = st.columns([1, 3])
    with col_export:
        if st.button('📄 导出PDF报告', use_container_width=True):
            from decision_engine import export_to_pdf
            pdf_bytes = export_to_pdf(report)
            if pdf_bytes:
                st.download_button(
                    label='⬇️ 下载PDF文件',
                    data=pdf_bytes,
                    file_name='购房决策报告.pdf',
                    mime='application/pdf',
                    use_container_width=True
                )
                st.success('PDF报告生成成功！请点击上方按钮下载')
            else:
                st.warning('PDF生成需要系统支持中文字体（SimHei/微软雅黑），当前环境不支持。'
                           '您可以截图保存报告内容。')

    with col_reset:
        if st.button('🔄 重新生成报告'):
            st.session_state.report_generated = False
            st.session_state.report_results = None
            st.rerun()

elif not st.session_state.report_generated:
    st.info('👆 请在上方填写购房偏好后，点击"生成决策报告"按钮')
    st.markdown('### 功能说明')
    st.markdown('''
    - **个性化匹配**：基于您的预算、面积、户型、朝向、房龄等偏好，从10万+房源中智能匹配
    - **多维度评分**：价格合理性、面积匹配度、房龄评分、单价合理性、地段热度，权重可自定义
    - **投资评估**：分析目标城市的价格趋势、单价水平、市场流动性
    - **风险提示**：自动识别高价位、老旧房源、低流动性等风险因素
    - **导出报告**：支持PDF格式导出，方便分享和打印
    ''')

st.markdown('---')
st.caption('💡 提示：调整各维度权重可影响推荐排序。权重越高，该维度对综合得分的影响越大。')
