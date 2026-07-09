# -*- coding: utf-8 -*-
# 模块3：决策报告
# 个性化报告 | 投资评估 | 风险提示 | 推荐方案
import streamlit as st
import pandas as pd
import numpy as np
import base64
import os
import json
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title='决策报告', page_icon='📝', layout='wide')

# ========== 城市查询日志（驱动回填优先级） ==========
_QUERY_LOG_PATH = Path(__file__).parent.parent / 'data' / 'queried_cities.json'


def _log_queried_cities(filtered_df):
    """记录用户查询的城市及频次，供 backfill_years.py --auto 使用"""
    cities = filtered_df['city'].unique().tolist()
    log = {}
    if _QUERY_LOG_PATH.exists():
        try:
            with open(_QUERY_LOG_PATH, 'r', encoding='utf-8') as f:
                log = json.load(f)
        except Exception:
            pass

    for city in cities:
        if city in log:
            log[city]['count'] = log[city].get('count', 0) + 1
            log[city]['last_query'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        else:
            log[city] = {'count': 1, 'last_query': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

    with open(_QUERY_LOG_PATH, 'w', encoding='utf-8') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


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

# === 区域偏好（表单外：选省份实时联动城市列表） ===
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

with st.form('preferences_form'):
    st.markdown('#### 你的购房能力')
    col_income, col_expense, col_savings = st.columns(3)
    with col_income:
        monthly_income = st.number_input('家庭月收入（元）', min_value=1000, value=10000, step=500,
                                         help='夫妻双方的税后月收入总和')
    with col_expense:
        monthly_expense = st.number_input('家庭月支出（元）', min_value=0, value=0, step=500,
                                          help='每月固定开支（房租/生活费/车贷等），填0=使用收入估算')
    with col_savings:
        savings = st.number_input('可用于购房的储蓄（万元）', min_value=1, value=20, step=1,
                                  help='包括存款、理财、父母资助等可用于首付的现金')
    col_loan_years, col_first = st.columns(2)
    with col_loan_years:
        loan_years = st.selectbox('期望贷款年限', options=[10, 15, 20, 25, 30], index=4,
                                  help='年限越长月供越低，但总利息越多')
    with col_first:
        is_first_house = st.selectbox('购房类型', options=['首套房', '二套房'], index=0,
                                       help='首套首付20%，二套首付30%；契税税率也不同')
        first_house = (is_first_house == '首套房')

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

    st.markdown('#### 各维度重要性权重（0-100，总和不要求=100，将自动归一化）')

    col_w1, col_w2, col_w3, col_w4, col_w5, col_w6 = st.columns(6)
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
    with col_w6:
        w_afford = st.slider('买得起指数', 0, 100, 60, help='月供占收入比越低越好的重视程度')

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
                'w_afford': w_afford,
            }

            st.session_state.report_preferences = preferences
            st.session_state.report_weights = weights
            st.session_state.monthly_income = monthly_income
            st.session_state.monthly_expense = monthly_expense
            st.session_state.savings = savings
            st.session_state.loan_years_input = loan_years
            st.session_state.first_house = first_house

            with st.spinner('正在分析匹配房源，请稍候...'):
                from decision_engine import hard_filter, compute_matching_score, generate_report_data

                filtered = hard_filter(df, preferences)
                st.info(f'硬筛选通过：{len(filtered):,} 套房源')

                if len(filtered) > 0:
                    # 保存筛选结果，供后续按需回填使用
                    st.session_state.filtered_for_backfill = filtered

                    scored, weight_info = compute_matching_score(
                        filtered, df, weights,
                        monthly_income=monthly_income,
                        savings=savings,
                        first_house=first_house,
                        loan_years=loan_years,
                        monthly_expense=monthly_expense if monthly_expense > 0 else None
                    )

                    # 购买力标记：为推荐列表增加月供和适配等级
                    from affordability_engine import enrich_with_affordability
                    scored = enrich_with_affordability(scored, monthly_income, savings,
                                                       first_house=first_house, loan_years=loan_years,
                                                       monthly_expense=monthly_expense if monthly_expense > 0 else None)
                    st.session_state.scored_data = scored

                    # 记录用户查询的城市（驱动回填优先级）
                    _log_queried_cities(filtered)

                    report = generate_report_data(preferences, scored, df, weight_info)
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

    # ===== 数据质量提示 + 按需回填 =====
    weight_info = report.get('weight_info', {})
    if weight_info and weight_info.get('adapted'):
        cov = weight_info.get('coverage', 0)
        level = weight_info.get('level', '?')
        orig_w = weight_info.get('original_weights', {})
        adj_w = weight_info.get('adjusted_weights', {})
        orig_age = orig_w.get('w_age', 0)
        adj_age = adj_w.get('w_age', 0)

        level_color = {'A': 'green', 'B': 'green', 'C': 'orange', 'D': 'red'}.get(level, 'gray')

        if level == 'D':
            # D级：展示选项——跳过 or 补全
            filtered_for_bf = st.session_state.get('filtered_for_backfill')
            missing_count = filtered_for_bf['year_num'].isna().sum() if filtered_for_bf is not None else 0

            st.markdown(f'''
            <div style="background: #FFF3E0; border-radius: 10px; padding: 14px 18px;
                        border-left: 4px solid #E65100; margin-bottom: 8px;">
                <b>年份数据覆盖不足</b><br>
                当前筛选结果年份覆盖率仅 <b style="color:#E65100">{cov}%</b>，
                房龄评分权重已暂时关闭，当前推荐基于
                价格、面积、月供、单价、地段 5个维度。
            </div>
            ''', unsafe_allow_html=True)

            if missing_count > 0:
                est_time = max(2, int(missing_count * 0.8))
                st.caption(f'该城市有 {missing_count} 套房源缺少年份，补全预计需 {est_time} 秒。')

                col_skip, col_fill = st.columns([1, 1])
                with col_skip:
                    st.markdown('*当前展示的是不含房龄评估的结果。*')
                with col_fill:
                    if st.button('🔍 补全年份数据，获得更精准推荐', type='primary', use_container_width=True,
                                 key='backfill_btn', help=f'自动访问房源详情页补全约{missing_count}条年份数据'):
                        with st.spinner(f'正在补全年份数据（约{est_time}秒）...'):
                            from backfill_years import backfill_on_demand
                            from decision_engine import hard_filter, compute_matching_score, generate_report_data
                            from affordability_engine import enrich_with_affordability
                            from data_processor import load_and_clean_data

                            bf_result = backfill_on_demand(filtered_for_bf)

                            if bf_result['filled'] > 0:
                                # 重新加载数据
                                st.session_state.cleaned_data = load_and_clean_data('data/house_sales.csv')
                                new_df = st.session_state.cleaned_data

                                # 重新筛选
                                new_filtered = hard_filter(new_df, st.session_state.report_preferences)

                                # 用完整权重重新评分（age不会被降级了）
                                new_scored, new_wi = compute_matching_score(
                                    new_filtered, new_df, st.session_state.report_weights,
                                    monthly_income=st.session_state.get('monthly_income', 10000),
                                    savings=st.session_state.get('savings', 20),
                                    first_house=st.session_state.get('first_house', True),
                                    loan_years=st.session_state.get('loan_years_input', 30),
                                    monthly_expense=st.session_state.get('monthly_expense', 0) or None
                                )
                                new_scored = enrich_with_affordability(
                                    new_scored,
                                    st.session_state.get('monthly_income', 10000),
                                    st.session_state.get('savings', 20),
                                    first_house=st.session_state.get('first_house', True),
                                    loan_years=st.session_state.get('loan_years_input', 30),
                                    monthly_expense=st.session_state.get('monthly_expense', 0) or None
                                )
                                st.session_state.scored_data = new_scored
                                _log_queried_cities(new_filtered)

                                new_report = generate_report_data(
                                    st.session_state.report_preferences, new_scored, new_df, new_wi
                                )
                                st.session_state.report_results = new_report

                                # 存储回填后信息
                                st.session_state.backfill_done = True
                                st.session_state.backfill_result = bf_result

                                st.success(f'已补全 {bf_result["filled"]} 条年份数据，'
                                          f'覆盖率提升至 {bf_result["after_coverage"]}%')
                                st.rerun()
                            else:
                                st.warning('未能补全任何数据，房源页面可能已失效。')
                st.markdown('---')
        else:
            # C级：显示提示但不需要操作
            st.markdown(f'''
            <div style="background: #FFF8E1; border-radius: 10px; padding: 14px 18px;
                        border-left: 4px solid {level_color}; margin-bottom: 12px;">
                <b>数据质量提示</b><br>
                当前筛选条件年份覆盖率: <b style="color:{level_color}">{cov}% ({level}级)</b><br>
                房龄评分权重已自动从 <b>{orig_age}</b> 降低至 <b>{adj_age}</b>，
                差额已分配至其他维度，以保证推荐结果可靠性。
            </div>
            ''', unsafe_allow_html=True)

    # ===== 回填后仍低覆盖说明 =====
    bf_done = st.session_state.get('backfill_done', False)
    bf_result = st.session_state.get('backfill_result', {})
    if bf_done and bf_result.get('after_coverage', 100) < 50:
        still = bf_result.get('still_missing', 0)
        total = bf_result.get('total_missing', 0) + bf_result.get('filled', 0)
        st.markdown(f'''
        <div style="background: #F5F5F5; border-radius: 10px; padding: 12px 16px;
                    border-left: 4px solid #999; margin-bottom: 12px; font-size: 14px; color: #666;">
            <b>说明</b><br>
            补全后仍有 {still} 套（{bf_result["after_coverage"]}%）房源本身未标明年份。
            当前剔除房龄权重的评估结果合理可靠——这些房源在市场上本就缺乏年份信息，
            任何基于房龄的排序都不可信。
        </div>
        ''', unsafe_allow_html=True)

    # ===== 购买力评估 =====
    st.markdown('---')
    st.markdown('#### 购买力评估')

    from affordability_engine import calculate_affordable_range
    mi = st.session_state.get('monthly_income', 10000)
    me = st.session_state.get('monthly_expense', 0)
    sv = st.session_state.get('savings', 20)
    ly = st.session_state.get('loan_years_input', 30)
    fh = st.session_state.get('first_house', True)

    afford = calculate_affordable_range(mi, sv, area_min=prefs.get('area_min', 70),
                                         area_max=prefs.get('area_max', 130),
                                         loan_years=ly, first_house=fh,
                                         monthly_expense=me if me > 0 else None)

    aff_cols = st.columns(4)
    aff_cols[0].metric('买得起总价（舒适线）', f'{afford["买得起总价_舒适线_万元"]}万',
                       delta=f'月供≤{afford["月供舒适线_元"]}元/月',
                       help=afford.get('舒适线说明', '月供不超过收入30%，还款无压力'))
    aff_cols[1].metric('买得起总价（安全线）', f'{afford["买得起总价_安全线_万元"]}万',
                       delta=f'月供≤{afford["月供安全线_元"]}元/月',
                       help=afford.get('安全线说明', '月供不超过收入50%，银行审批上限'))
    aff_cols[2].metric('首付需准备现金', f'{afford["首付所需现金_万元"]}万',
                       delta=f'{afford["首付比例"]} | 储蓄{sv}万',
                       help='首付+税费+中介费，不含装修')
    aff_cols[3].metric('装修预算（额外）', f'{afford["装修预留_万元(额外)"]}万',
                       delta='可后期分批投入',
                       help=f'按{prefs.get("area_min", 70)}-{prefs.get("area_max", 130)}㎡ × 800元/㎡估算')

    # 计算依据提示
    if afford.get('家庭月支出_元') and afford['家庭月支出_元'] > 0:
        st.caption(f"💡 {afford.get('计算说明', '')} —— 填写月支出后评估更精准")
    else:
        st.caption(f"💡 {afford.get('计算说明', '')} —— 建议填写月支出以获得更精准的评估")

    # 适配等级分布
    scored_for_display = st.session_state.get('scored_data')
    if scored_for_display is not None and len(scored_for_display) > 0:
        level_counts = scored_for_display['适配等级'].value_counts()
        level_summary = ' | '.join([f'{k}: {v}套' for k, v in level_counts.items()])
        st.caption(f'Top20推荐适配分布: {level_summary}')

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

    if scored_for_display is not None and len(scored_for_display) > 0:
        # 用增强后的数据展示（含月供和适配等级）
        top20 = scored_for_display.head(20)
        show_cols_map = {
            'city': '城市', 'name': '小区名称', 'price_num': '总价(万)',
            'area_num': '面积(㎡)', 'rooms': '户型', 'toward': '朝向',
            'score': '综合得分', '月供_元': '月供(元)', '月供占比': '月供占比(%)',
            '落地成本_万元': '落地成本(万)', '适配等级': '适配等级'
        }
        display_cols = {k: v for k, v in show_cols_map.items() if k in top20.columns}
        display_df = top20[list(display_cols.keys())].copy()
        display_df.rename(columns=display_cols, inplace=True)
        display_df['综合得分'] = display_df['综合得分'].round(1)

        styled = display_df.style \
            .background_gradient(subset=['综合得分'], cmap='RdYlGn') \
            .map(lambda x: 'color: green; font-weight: bold' if '轻松' in str(x) else
                           ('color: orange; font-weight: bold' if any(w in str(x) for w in ['适中', '紧张', '勉强']) else
                            ('color: red; font-weight: bold' if '超预算' in str(x) else '')),
                 subset=['适配等级'] if '适配等级' in display_df.columns else [])
        st.dataframe(styled, use_container_width=True, hide_index=True)
    elif len(top_listings) > 0:
        st.dataframe(
            top_listings.style.background_gradient(subset=['综合得分'], cmap='RdYlGn'),
            use_container_width=True,
            hide_index=True
        )

    if len(top_listings) > 0:
        st.markdown('**得分Top3房源卡片：**')
        top3_cols = st.columns(3)
        medals = ['🥇', '🥈', '🥉']

        # 从 scored 数据取各维度得分，用于优劣势分析
        scored_src = scored_for_display if scored_for_display is not None else top_listings
        dim_labels = {
            'S_price': '价格优', 'S_area': '面积匹配', 'S_age': '房龄新',
            'S_unit': '单价低', 'S_location': '地段热', 'S_afford': '月供轻'
        }

        for i in range(min(3, len(display_df))):
            row = display_df.iloc[i]

            # -- 计算该房源的优劣势 --
            src_row = None
            if scored_src is not None and i < len(scored_src):
                src_row = scored_src.iloc[i]
            # 如果 scored_src 是按 score 排好序的（head 20），取对应位置
            elif scored_src is not None and 'score' in scored_src.columns:
                top_scored = scored_src.head(20)
                if i < len(top_scored):
                    src_row = top_scored.iloc[i]

            strength_text = ''
            weakness_text = ''
            if src_row is not None:
                dim_scores = {}
                for col, label in dim_labels.items():
                    if col in src_row.index:
                        dim_scores[label] = float(src_row[col])
                if dim_scores:
                    sorted_dims = sorted(dim_scores.items(), key=lambda x: x[1], reverse=True)
                    # 优势: 取最高2个（分数>60才算真正优势）
                    strengths = [(k, v) for k, v in sorted_dims[:3] if v >= 60][:2]
                    if strengths:
                        strength_text = '优势：' + '  '.join([f'{k}({v:.0f})' for k, v in strengths])
                    # 短板: 取最低1个
                    weakest = sorted_dims[-1]
                    if weakest[1] < 70:
                        weakness_text = '短板：' + f'{weakest[0]}({weakest[1]:.0f})'

            with top3_cols[i]:
                analysis_html = ''
                if strength_text or weakness_text:
                    analysis_html = '<div style="margin-top:8px; font-family:KaiTi,STKaiti,楷体,serif; font-size:13px; color:#666; line-height:1.6;">'
                    if strength_text:
                        analysis_html += f'<span>{strength_text}</span>'
                    if weakness_text:
                        if strength_text:
                            analysis_html += '<br>'
                        analysis_html += f'<span>{weakness_text}</span>'
                    analysis_html += '</div>'

                st.markdown(f'''
                <div style="background: #f8f9fa; border-radius: 10px; padding: 15px;
                            border-left: 4px solid {'#FFD700' if i==0 else '#C0C0C0' if i==1 else '#CD7F32'};">
                    <h3>{medals[i]} {row.get("小区名称", "--")}</h3>
                    <p><b>城市：</b>{row.get("城市", "--")} | <b>得分：</b>{row.get("综合得分", "--")}</p>
                    <p><b>总价：</b>{row.get("总价(万)", "--")}万 | <b>面积：</b>{row.get("面积(㎡)", "--")}㎡</p>
                    <p><b>户型：</b>{row.get("户型", "--")} | <b>朝向：</b>{row.get("朝向", "--")}</p>
                    <p><b>单价：</b>{row.get("单价(元/㎡)", "--")}元/㎡ | <b>年份：</b>{row.get("建成年份", "--")}</p>
                    {analysis_html}
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
