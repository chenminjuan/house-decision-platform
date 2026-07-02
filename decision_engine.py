# -*- coding: utf-8 -*-
# 房地产购房决策引擎
# 评分算法 + 投资评估 + 风险评估 + PDF导出
import pandas as pd
import numpy as np

# ========== Phase 1: 硬筛选 ==========

def hard_filter(df, preferences):
    """
    硬筛选：基于用户偏好过滤房源列表
    preferences字段：
        - budget_min / budget_max: 预算范围（万元）
        - area_min / area_max: 面积范围（㎡）
        - preferred_rooms: 期望室数
        - preferred_halls: 期望厅数
        - year_min / year_max: 房龄范围
        - max_unit_price: 最高单价
        - preferred_toward: 期望朝向列表
        - preferred_locations: 期望城市列表
    """
    filtered = df.copy()

    # 预算
    if 'budget_min' in preferences and 'budget_max' in preferences:
        filtered = filtered[
            (filtered['price_num'] >= preferences['budget_min']) &
            (filtered['price_num'] <= preferences['budget_max'])
            ]

    # 面积
    if 'area_min' in preferences and 'area_max' in preferences:
        filtered = filtered[
            (filtered['area_num'] >= preferences['area_min']) &
            (filtered['area_num'] <= preferences['area_max'])
            ]

    # 室数
    if 'preferred_rooms' in preferences and preferences['preferred_rooms'] is not None:
        filtered = filtered[filtered['num_rooms'] == preferences['preferred_rooms']]

    # 厅数（至少不少于指定数量）
    if 'preferred_halls' in preferences and preferences['preferred_halls'] is not None:
        filtered = filtered[filtered['num_halls'] >= preferences['preferred_halls']]

    # 年份（保留年份缺失的记录）
    if 'year_min' in preferences and 'year_max' in preferences:
        year_mask = (
                filtered['year_num'].isna() |
                ((filtered['year_num'] >= preferences['year_min']) &
                 (filtered['year_num'] <= preferences['year_max']))
        )
        filtered = filtered[year_mask]

    # 单价上限
    if 'max_unit_price' in preferences and preferences['max_unit_price'] is not None:
        filtered = filtered[filtered['unit_num'] <= preferences['max_unit_price']]

    # 朝向
    if 'preferred_toward' in preferences and preferences['preferred_toward']:
        filtered = filtered[filtered['toward'].isin(preferences['preferred_toward'])]

    # 城市
    if 'preferred_locations' in preferences and preferences['preferred_locations']:
        filtered = filtered[filtered['city'].isin(preferences['preferred_locations'])]

    # 省份（当用户选择了省份但未指定具体城市时，限定在该省份范围内）
    if 'preferred_province' in preferences and preferences['preferred_province'] is not None:
        filtered = filtered[filtered['province'] == preferences['preferred_province']]

    return filtered


# ========== Phase 2: 加权评分 ==========

def compute_matching_score(filtered_df, full_df, weights):
    """
    加权评分算法（0-100分）
    weights: dict with keys:
        w_price, w_area, w_age, w_unit, w_location
        各维度权重(0-100)，会被归一化为总和=1
    """
    df = filtered_df.copy()
    if len(df) == 0:
        return df

    # 归一化权重
    total_w = sum(weights.values())
    if total_w == 0:
        # 默认等权重
        weights = {k: 20 for k in weights}
        total_w = 100
    norm_weights = {k: v / total_w for k, v in weights.items()}

    # ----- 维度1: 价格合理性 -----
    # 价格越低越好（相对预算范围内）—— 价格在预算下限时得100分
    budget_min = df['price_num'].min()
    budget_max = df['price_num'].max()
    if budget_max > budget_min:
        df['S_price'] = ((budget_max - df['price_num']) / (budget_max - budget_min) * 100).clip(0, 100)
    else:
        df['S_price'] = 50

    # ----- 维度2: 面积匹配度 -----
    # 使用高斯距离到理想面积（面积中位数作为理想值）
    ideal_area = df['area_num'].median()
    if ideal_area > 0:
        sigma = ideal_area * 0.3  # 30%宽度的高斯核
        df['S_area'] = 100 * np.exp(-((df['area_num'] - ideal_area) ** 2) / (2 * sigma ** 2))
    else:
        df['S_area'] = 50

    # ----- 维度3: 房龄评分 -----
    # 越新越高分，40年以上为0
    df['S_age'] = 100 * np.maximum(0, 1 - df['age'].fillna(20) / 40)

    # ----- 维度4: 单价合理性 -----
    # 单价越低越好
    unit_max = df['unit_num'].max()
    unit_min = df['unit_num'].min()
    if unit_max > unit_min:
        df['S_unit'] = ((unit_max - df['unit_num']) / (unit_max - unit_min) * 100).clip(0, 100)
    else:
        df['S_unit'] = 50

    # ----- 维度5: 地段热度 -----
    # 城市挂牌密度百分位（流通性代理）
    city_counts = full_df['city'].value_counts()
    total_cities = len(city_counts)
    city_percentile = {}
    for i, (city, count) in enumerate(city_counts.items()):
        city_percentile[str(city)] = (1 - i / total_cities) * 100  # 排名越靠前分越高
    # 将city转为字符串后映射（处理category类型）
    df['S_location'] = df['city'].astype(str).map(city_percentile).fillna(50).astype(float)

    # ----- 加权总分 -----
    df['score'] = (
            norm_weights.get('w_price', 0.2) * df['S_price'] +
            norm_weights.get('w_area', 0.2) * df['S_area'] +
            norm_weights.get('w_age', 0.2) * df['S_age'] +
            norm_weights.get('w_unit', 0.2) * df['S_unit'] +
            norm_weights.get('w_location', 0.2) * df['S_location']
    )

    # 排序
    df = df.sort_values('score', ascending=False)
    return df


def get_top_recommendations(scored_df, top_n=20):
    """获取Top N推荐房源，返回展示用DataFrame"""
    if len(scored_df) == 0:
        return pd.DataFrame()
    display_cols = ['city', 'address', 'name', 'price_num', 'area_num', 'unit_num',
                    'year_num', 'rooms', 'toward', 'floor_level', 'score']
    available_cols = [c for c in display_cols if c in scored_df.columns]
    result = scored_df[available_cols].head(top_n).copy()
    # 格式化显示
    result['排名'] = range(1, len(result) + 1)
    result = result.rename(columns={
        'city': '城市', 'address': '地址', 'name': '小区名称',
        'price_num': '总价(万)', 'area_num': '面积(㎡)', 'unit_num': '单价(元/㎡)',
        'year_num': '建成年份', 'rooms': '户型', 'toward': '朝向',
        'floor_level': '楼层', 'score': '综合得分'
    })
    # 调整列顺序
    col_order = ['排名', '城市', '小区名称', '地址', '总价(万)', '面积(㎡)', '单价(元/㎡)',
                 '户型', '朝向', '楼层', '建成年份', '综合得分']
    result = result[[c for c in col_order if c in result.columns]]
    return result


# ========== 投资评估 ==========

def compute_investment_assessment(scored_df, full_df):
    """
    投资评估分析
    返回dict包含：价格趋势、单价分析、流动性分析
    """
    assessment = {}

    if len(scored_df) == 0:
        assessment['summary'] = '无匹配房源，无法生成投资评估'
        return assessment

    # 匹配房源的Top5城市
    top_cities = scored_df['city'].value_counts().head(5).index.tolist()

    # 1) 价格趋势：对每个Top城市计算年均涨幅
    city_trends = {}
    for city in top_cities:
        city_data = full_df[full_df['city'] == city].dropna(subset=['year_num'])
        city_data = city_data[(city_data['year_num'] >= 2000) & (city_data['year_num'] <= 2025)]
        if len(city_data) >= 30:
            yearly = city_data.groupby('year_num')['price_num'].mean().reset_index()
            if len(yearly) >= 3:
                # 线性回归
                z = np.polyfit(yearly['year_num'], yearly['均价'] if '均价' in yearly.columns else yearly['price_num'], 1)
                annual_change = z[0]  # 斜率（万元/年）
                latest_price = yearly.iloc[-1]['price_num'] if 'price_num' in yearly.columns else yearly.iloc[-1]['均价']
                annual_pct = (annual_change / latest_price * 100) if latest_price > 0 else 0
                city_trends[city] = {
                    '年均涨幅(万元/年)': round(annual_change, 2),
                    '年均涨幅(%)': round(annual_pct, 2),
                    '最新均价(万元)': round(latest_price, 1),
                    '数据年份数': len(yearly)
                }

    assessment['city_trends'] = city_trends

    # 2) 单价分析
    city_median_unit = full_df.groupby('city')['unit_num'].median()
    global_median = full_df['unit_num'].median()

    match_median_unit = scored_df['unit_num'].median()
    assessment['unit_analysis'] = {
        '匹配房源中位单价': round(match_median_unit, 0),
        '全国中位单价': round(global_median, 0),
        '单价水平': '低于全国中位' if match_median_unit < global_median else '高于全国中位',
        '性价比评估': '较好' if match_median_unit < global_median * 0.8
        else ('一般' if match_median_unit < global_median * 1.2 else '偏低')
    }

    # 3) 流动性分析
    city_listing_counts = full_df.groupby('city')['price_num'].count()
    match_cities = scored_df['city'].unique()
    city_liquidity = {}
    for city in match_cities:
        count = city_listing_counts.get(city, 0)
        city_liquidity[city] = {
            '挂牌量': int(count),
            '流动性': '高' if count >= 200 else ('中' if count >= 50 else '低')
        }
    assessment['city_liquidity'] = city_liquidity

    # 汇总
    assessment['summary'] = (
        f'共匹配 {len(scored_df)} 套房源，覆盖 {len(match_cities)} 个城市。'
        f'匹配房源中位单价{match_median_unit:.0f}元/㎡，'
        f'{"低于" if match_median_unit < global_median else "高于"}全国中位({global_median:.0f}元/㎡)。'
    )

    return assessment


# ========== 风险评估 ==========

def compute_risk_flags(listing, city_stats, full_df):
    """
    单个房源的风险标记
    返回风险标签列表
    """
    risks = []

    # 获取城市中位价
    city_median = city_stats[city_stats['city'] == listing['city']]
    if len(city_median) > 0:
        city_median_price = city_median.iloc[0]['中位价_万元']
        city_median_unit = city_median.iloc[0]['均单价_元每平']
        city_listing_count = city_median.iloc[0]['挂牌量']

        # 高价位风险：价格 > 城市90分位
        city_p90 = full_df[full_df['city'] == listing['city']]['price_num'].quantile(0.9)
        if listing['price_num'] > city_p90:
            risks.append('⚠️ 高价位风险：总价高于同城90%房源')

        # 单价异常风险
        if listing['unit_num'] > city_median_unit * 1.5:
            risks.append('⚠️ 单价异常：单价显著高于同城中位水平')

        # 低流动性风险
        if city_listing_count < 50:
            risks.append('⚠️ 低流动性：该城市挂牌量较少，转手可能困难')

    # 老旧房源风险
    if not pd.isna(listing.get('age', np.nan)) and listing['age'] > 20:
        risks.append('⚠️ 老旧房源：房龄超过20年')

    # 数据缺失风险
    if pd.isna(listing.get('year_num', np.nan)):
        risks.append('⚠️ 建成年份不详：无法评估房龄')

    return risks


def compute_risk_assessment(scored_df, full_df):
    """
    对Top推荐房源做风险评估
    返回带风险标签的DataFrame
    """
    if len(scored_df) == 0:
        return pd.DataFrame(), {}

    from data_processor import get_city_stats
    city_stats = get_city_stats(full_df)

    # 安全评分
    risk_summary = {}
    risk_counts = {
        '高价位风险': 0,
        '单价异常': 0,
        '低流动性': 0,
        '老旧房源': 0,
        '数据缺失': 0
    }

    # 计算安全评分
    top_n = min(20, len(scored_df))
    for idx in range(top_n):
        listing = scored_df.iloc[idx]
        risks = compute_risk_flags(listing, city_stats, full_df)
        risk_summary[idx] = risks
        for r in risks:
            for key in risk_counts:
                if key in r:
                    risk_counts[key] += 1

    # 总体安全评分
    total_checks = top_n * 5  # 5个维度
    total_risks = sum(risk_counts.values())
    safety_score = max(0, 100 - (total_risks / max(total_checks, 1) * 100))

    risk_overview = {
        '安全评分': round(safety_score, 1),
        '检查房源数': top_n,
        '总风险标记数': total_risks,
        '风险分布': risk_counts,
        '评估结论': '整体风险较低，推荐可信度高' if safety_score >= 80
        else ('存在一定风险，建议进一步核实' if safety_score >= 60
              else '风险较高，建议谨慎决策')
    }

    return risk_summary, risk_overview


# ========== 报告聚合 ==========

def generate_report_data(preferences, scored_df, full_df):
    """
    聚合所有报告数据
    返回结构化dict供展示和PDF导出
    """
    if len(scored_df) == 0:
        return {
            'preferences': preferences,
            'match_count': 0,
            'message': '根据您的偏好未找到匹配房源，请放宽筛选条件后重试。'
        }

    # Top推荐
    top_listings = get_top_recommendations(scored_df, top_n=20)

    # 投资评估
    investment = compute_investment_assessment(scored_df, full_df)

    # 风险评估
    risk_detail, risk_overview = compute_risk_assessment(scored_df, full_df)

    # 得分分解（Top5平均）
    top5 = scored_df.head(5)
    score_breakdown = {}
    score_cols = ['S_price', 'S_area', 'S_age', 'S_unit', 'S_location']
    score_labels = ['价格合理性', '面积匹配度', '房龄评分', '单价合理性', '地段热度']
    for col, label in zip(score_cols, score_labels):
        if col in top5.columns:
            score_breakdown[label] = round(top5[col].mean(), 1)

    # 匹配概览
    match_cities = scored_df['city'].nunique()
    avg_price = scored_df['price_num'].mean()
    avg_area = scored_df['area_num'].mean()
    avg_unit = scored_df['unit_num'].mean()

    report = {
        'preferences': preferences,
        'match_count': len(scored_df),
        'match_cities': match_cities,
        'avg_price': round(avg_price, 1),
        'avg_area': round(avg_area, 1),
        'avg_unit': round(avg_unit, 0),
        'top_listings': top_listings,
        'score_breakdown': score_breakdown,
        'investment': investment,
        'risk_overview': risk_overview,
        'risk_detail': risk_detail,
    }

    return report


# ========== PDF导出 ==========

def export_to_pdf(report_data):
    """
    使用fpdf2生成PDF报告
    返回bytes供streamlit下载按钮
    """
    try:
        from fpdf import FPDF
    except ImportError:
        return None

    pdf = FPDF()
    pdf.add_page()

    # 设置中文字体
    # 尝试使用系统自带的中文字体
    import os
    font_paths = [
        'C:/Windows/Fonts/simhei.ttf',
        'C:/Windows/Fonts/msyh.ttc',
        'C:/Windows/Fonts/simsun.ttc',
        '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
        '/System/Library/Fonts/PingFang.ttc',
    ]
    font_loaded = False
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdf.add_font('CJK', '', font_path, uni=True)
                pdf.add_font('CJK', 'B', font_path, uni=True)
                font_loaded = True
                break
            except Exception:
                continue

    if not font_loaded:
        # 无中文字体时返回None，由调用方处理
        return None

    # 封面标题
    pdf.set_font('CJK', 'B', 20)
    pdf.cell(0, 15, '房地产购房决策报告', new_x='LMARGIN', new_y='NEXT', align='C')
    pdf.ln(5)
    pdf.set_font('CJK', '', 12)
    pdf.cell(0, 10, '购房决策辅助平台', new_x='LMARGIN', new_y='NEXT', align='C')
    pdf.ln(10)

    # 分割线
    pdf.set_line_width(0.5)
    x = pdf.get_x()
    y = pdf.get_y()
    pdf.line(x, y, x + 190, y)
    pdf.ln(5)

    # 1. 需求概览
    pdf.set_font('CJK', 'B', 14)
    pdf.cell(0, 10, '一、购房需求概览', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('CJK', '', 11)
    prefs = report_data.get('preferences', {})
    pref_text = f"预算：{prefs.get('budget_min', '--')}-{prefs.get('budget_max', '--')}万元  |  "
    pref_text += f"面积：{prefs.get('area_min', '--')}-{prefs.get('area_max', '--')}㎡  |  "
    pref_text += f"户型：{prefs.get('preferred_rooms', '--')}室{prefs.get('preferred_halls', '--')}厅"
    pdf.cell(0, 8, pref_text, new_x='LMARGIN', new_y='NEXT')
    pdf.ln(3)

    # 2. 匹配概览
    pdf.set_font('CJK', 'B', 14)
    pdf.cell(0, 10, '二、匹配概览', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('CJK', '', 11)
    pdf.cell(0, 8, f"匹配房源数：{report_data.get('match_count', 0)}套", new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 8, f"覆盖城市数：{report_data.get('match_cities', 0)}个", new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 8, f"匹配均价：{report_data.get('avg_price', '--')}万元", new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 8, f"匹配均单价：{report_data.get('avg_unit', '--')}元/㎡", new_x='LMARGIN', new_y='NEXT')
    pdf.ln(3)

    # 3. 得分分解
    pdf.set_font('CJK', 'B', 14)
    pdf.cell(0, 10, '三、评分维度分解（Top5平均）', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('CJK', '', 11)
    breakdown = report_data.get('score_breakdown', {})
    for k, v in breakdown.items():
        pdf.cell(0, 7, f"  {k}：{v}分", new_x='LMARGIN', new_y='NEXT')
    pdf.ln(3)

    # 4. 投资评估
    pdf.set_font('CJK', 'B', 14)
    pdf.cell(0, 10, '四、投资评估', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('CJK', '', 11)
    investment = report_data.get('investment', {})
    pdf.cell(0, 8, investment.get('summary', '--'), new_x='LMARGIN', new_y='NEXT')
    # 城市趋势
    city_trends = investment.get('city_trends', {})
    for city, trend in city_trends.items():
        pdf.cell(0, 7,
                 f"  {city}：年均涨幅{trend.get('年均涨幅(%)', '--')}%，最新均价{trend.get('最新均价(万元)', '--')}万元",
                 new_x='LMARGIN', new_y='NEXT')
    pdf.ln(3)

    # 5. 风险评估
    pdf.set_font('CJK', 'B', 14)
    pdf.cell(0, 10, '五、风险评估', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('CJK', '', 11)
    risk = report_data.get('risk_overview', {})
    pdf.cell(0, 8, f"综合安全评分：{risk.get('安全评分', '--')}分", new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 8, f"评估结论：{risk.get('评估结论', '--')}", new_x='LMARGIN', new_y='NEXT')
    pdf.ln(3)

    # 6. Top推荐列表
    pdf.set_font('CJK', 'B', 14)
    pdf.cell(0, 10, '六、Top 10推荐房源', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('CJK', '', 9)
    listings = report_data.get('top_listings', pd.DataFrame())
    if len(listings) > 0:
        for i, (_, row) in enumerate(listings.head(10).iterrows()):
            text = (f"  #{i + 1} {row.get('城市', '--')} | {row.get('小区名称', '--')} | "
                    f"{row.get('总价(万)', '--')}万 | {row.get('面积(㎡)', '--')}㎡ | "
                    f"{row.get('单价(元/㎡)', '--')}元/㎡ | 得分:{row.get('综合得分', '--')}")
            pdf.cell(0, 6, text[:90], new_x='LMARGIN', new_y='NEXT')

    # 页脚
    pdf.ln(10)
    pdf.set_font('CJK', '', 9)
    pdf.cell(0, 8, '本报告由"房地产购房决策辅助平台"自动生成，仅供参考。', new_x='LMARGIN', new_y='NEXT', align='C')

    return bytes(pdf.output())
