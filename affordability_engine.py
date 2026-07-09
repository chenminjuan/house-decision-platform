# -*- coding: utf-8 -*-
# 购买力评估引擎
# 功能：落地总成本计算 + 月供计算 + 购买力边界反算
#
# 参考政策（2025年）：
#   - 首套房首付比例: 20-30%（各城市不同，默认20%）
#   - 二套房首付比例: 30-40%
#   - 契税: 90㎡以下1%，90㎡以上1.5%（首套）；二套3%
#   - 个税: 总价×1%（满五唯一免征）
#   - 增值税及附加: 总价×5.6%（满二免征）
#   - 中介费: 总价×1-2%（默认1.5%）
#   - LPR 5年期以上: 3.95%（2025年基准，可调）

import math


# ======================== 落地成本计算 ========================

def calculate_down_payment(total_price, first_house=True, down_payment_ratio=None):
    """
    计算首付金额。

    Args:
        total_price: 房屋总价（万元）
        first_house: 是否首套房
        down_payment_ratio: 自定义首付比例，None=使用默认值

    Returns:
        dict: {首付比例, 首付金额(万元)}
    """
    if down_payment_ratio is not None:
        ratio = down_payment_ratio
    else:
        ratio = 0.20 if first_house else 0.30

    amount = total_price * ratio
    return {
        '首付比例': f'{ratio*100:.0f}%',
        '首付金额_万元': round(amount, 2),
        '首付金额_元': round(amount * 10000),
    }


def calculate_taxes(total_price, area, build_year=None, is_unique_5=False, is_exempt_2=False,
                    first_house=True):
    """
    计算购房税费（契税 + 个税 + 增值税）。

    Args:
        total_price: 总价（万元）
        area: 面积（㎡）
        build_year: 建成年份（用于判断是否满二/满五）
        is_unique_5: 是否满五唯一（免个税）
        is_exempt_2: 是否满二（免增值税）
        first_house: 是否首套房

    Returns:
        dict: 各项税费明细
    """
    # 契税
    if first_house:
        deed_tax_rate = 0.01 if area <= 90 else 0.015
    else:
        deed_tax_rate = 0.03
    deed_tax = total_price * deed_tax_rate

    # 个税（满五唯一免征）
    income_tax = 0 if is_unique_5 else total_price * 0.01

    # 增值税及附加（满二免征）
    vat = 0 if is_exempt_2 else total_price * 0.056

    total_tax = deed_tax + income_tax + vat

    return {
        '契税_万元': round(deed_tax, 2),
        '契税税率': f'{deed_tax_rate*100:.1f}%',
        '个税_万元': round(income_tax, 2),
        '个税说明': '满五唯一免征' if is_unique_5 else '总价×1%',
        '增值税_万元': round(vat, 2),
        '增值税说明': '满二免征' if is_exempt_2 else '总价×5.6%',
        '税费合计_万元': round(total_tax, 2),
    }


def calculate_landing_cost(total_price, area, build_year=None,
                           first_house=True, is_unique_5=False, is_exempt_2=False,
                           agent_fee_rate=0.015, decoration_budget_per_sqm=800):
    """
    计算「落地总成本」——真正需要准备的现金。

    落地总成本 = 首付 + 税费 + 中介费 + 装修预算

    Args:
        total_price: 总价（万元）
        area: 面积（㎡）
        build_year: 建成年份
        first_house: 是否首套房
        is_unique_5: 是否满五唯一
        is_exempt_2: 是否满二
        agent_fee_rate: 中介费率（默认1.5%）
        decoration_budget_per_sqm: 装修预算单价（元/㎡）（默认800）

    Returns:
        dict: 完整的落地成本明细
    """
    down = calculate_down_payment(total_price, first_house)
    taxes = calculate_taxes(total_price, area, build_year, is_unique_5, is_exempt_2, first_house)
    agent_fee = total_price * agent_fee_rate
    decoration = area * decoration_budget_per_sqm / 10000  # 转为万元

    landing_total = down['首付金额_万元'] + taxes['税费合计_万元'] + agent_fee + decoration

    return {
        '房屋总价_万元': total_price,
        '面积_㎡': area,
        '首付': down,
        '税费': taxes,
        '中介费_万元': round(agent_fee, 2),
        '装修预算_万元': round(decoration, 2),
        '落地总成本_万元': round(landing_total, 2),
        '落地总成本_元': round(landing_total * 10000),
        'vs挂牌价倍数': round(landing_total / total_price, 2) if total_price > 0 else 0,
    }


# ======================== 月供计算 ========================

def calculate_monthly_payment(loan_amount, loan_years=30, annual_rate=3.95,
                               method='equal_installment'):
    """
    计算月供。

    Args:
        loan_amount: 贷款金额（万元）
        loan_years: 贷款年限（1-30）
        annual_rate: 年利率（%），默认3.95%（2025年LPR 5年期）
        method: 'equal_installment'(等额本息) 或 'equal_principal'(等额本金)

    Returns:
        dict: 月供明细
    """
    total_months = loan_years * 12
    monthly_rate = annual_rate / 100 / 12

    if method == 'equal_installment':
        # 等额本息: M = P × r × (1+r)^n / ((1+r)^n - 1)
        P = loan_amount * 10000  # 转为元
        if monthly_rate > 0:
            monthly = P * monthly_rate * (1 + monthly_rate) ** total_months / \
                      ((1 + monthly_rate) ** total_months - 1)
        else:
            monthly = P / total_months
        monthly = monthly / 10000  # 转回万元

        total_payment = monthly * total_months
        total_interest = total_payment - loan_amount

        schedule = []  # 等额本息不需要详细的还款表

    elif method == 'equal_principal':
        # 等额本金: 每月还本金 = P/n，利息 = 剩余本金 × r
        P = loan_amount * 10000
        monthly_principal = P / total_months / 10000  # 万元

        payments = []
        total_payment = 0
        remaining = loan_amount

        for m in range(1, total_months + 1):
            interest = remaining * monthly_rate
            month_payment = monthly_principal + interest
            total_payment += month_payment
            remaining -= monthly_principal

            # 记录首月和末月
            if m == 1:
                first_month = month_payment
            if m == total_months:
                last_month = month_payment

        monthly = first_month  # 第一期月供（最高）
        total_interest = total_payment - loan_amount

        schedule = {
            '首月月供_万元': round(first_month, 4),
            '末月月供_万元': round(last_month, 4),
            '月递减_元': round(monthly_principal * 10000 * monthly_rate, 2),
        }

    else:
        raise ValueError(f"不支持的还款方式: {method}")

    return {
        '贷款金额_万元': loan_amount,
        '贷款年限': loan_years,
        '年利率': f'{annual_rate}%',
        '还款方式': '等额本息' if method == 'equal_installment' else '等额本金',
        '月供_万元': round(monthly, 4),
        '月供_元': round(monthly * 10000),
        '总还款_万元': round(total_payment, 2),
        '总利息_万元': round(total_interest, 2),
        '利息占比': f'{total_interest/total_payment*100:.1f}%' if total_payment > 0 else '0%',
        '还款明细': schedule,
    }


def monthly_payment_simple(loan_amount_wan, loan_years=30, annual_rate=3.95):
    """
    快速计算月供（等额本息），只返回数字。

    Args:
        loan_amount_wan: 贷款金额（万元）
        loan_years: 贷款年限
        annual_rate: 年利率（%）

    Returns:
        float: 月供（元）
    """
    result = calculate_monthly_payment(loan_amount_wan, loan_years, annual_rate, 'equal_installment')
    return result['月供_元']


# ======================== 购买力边界分析 ========================

def calculate_affordable_range(monthly_income, savings,
                                area_min=70, area_max=130,
                                loan_years=30, annual_rate=3.95,
                                first_house=True, city_unit_price=None,
                                decoration_budget_per_sqm=800,
                                monthly_expense=None):
    """
    反向计算用户的真实购买力边界。

    逻辑：
      1. 根据可支配收入（月收入-月支出）计算最大可承受月供
         - 有月支出数据：安全线=可支配×50%，舒适线=可支配×30%
         - 无月支出数据：安全线=收入×50%，舒适线=收入×30%（银行通用标准）
      2. 根据月供反算最大贷款金额
      3. 根据储蓄反算最大总价
      4. 综合考虑税费和装修后，给出「真正买得起」的价格范围

    Args:
        monthly_income: 家庭月收入（元）
        savings: 可用于购房的储蓄（万元）
        area_min/max: 意向面积范围
        loan_years: 贷款年限
        annual_rate: 年利率（%）
        first_house: 是否首套房
        city_unit_price: 目标城市参考单价（元/㎡），用于估算可买面积
        decoration_budget_per_sqm: 装修预算（元/㎡）
        monthly_expense: 家庭月支出（元），可选。提供后可更精准计算可支配收入

    Returns:
        dict: 购买力分析结果
    """
    monthly_rate = annual_rate / 100 / 12
    total_months = loan_years * 12

    # 计算可用于月供的基准收入
    if monthly_expense is not None and monthly_expense > 0:
        disposable_income = max(0, monthly_income - monthly_expense)
        expense_note = f'月收入{monthly_income} - 月支出{monthly_expense} = 可支配{disposable_income}元'
    else:
        disposable_income = monthly_income
        expense_note = f'月收入{monthly_income}（未填写月支出，使用全部收入估算）'

    # 1. 月供上限（基于可支配收入）
    max_monthly_payment_safe = disposable_income * 0.50  # 月供不超过可支配收入50%
    max_monthly_payment_comfort = disposable_income * 0.30  # 舒适线：可支配收入30%

    # 2. 反算最大贷款金额（等额本息公式反解）
    # M = P × r × (1+r)^n / ((1+r)^n - 1)
    # P = M × ((1+r)^n - 1) / (r × (1+r)^n)
    def max_loan_for_monthly(monthly_payment):
        if monthly_rate > 0:
            return monthly_payment * ((1 + monthly_rate) ** total_months - 1) / \
                   (monthly_rate * (1 + monthly_rate) ** total_months) / 10000
        else:
            return monthly_payment * total_months / 10000

    max_loan_safe = max_loan_for_monthly(max_monthly_payment_safe)
    max_loan_comfort = max_loan_for_monthly(max_monthly_payment_comfort)

    # 3. 根据储蓄反算最大总价
    # 必须现金 = 首付 + 税费 + 中介费（装修可以后做，不占用首付现金）
    # 首付 ≈ 总价 × 20%（首套）
    # 税费+中介费 ≈ 总价 × 3%
    # 总价上限 ≈ 储蓄 / (首付比例 + 税费中介比例)

    down_ratio = 0.20 if first_house else 0.30
    extra_ratio = 0.03  # 税费+中介费约占3%

    max_price_by_savings = savings / (down_ratio + extra_ratio) if (down_ratio + extra_ratio) > 0 else 0

    # 4. 综合考虑：取储蓄约束和贷款约束的较小值
    max_price_by_loan_safe = max_loan_safe / (1 - down_ratio)  # 贷款占80%
    max_price_by_loan_comfort = max_loan_comfort / (1 - down_ratio)

    affordable_price_safe = min(max_price_by_savings, max_price_by_loan_safe)
    affordable_price_comfort = min(max_price_by_savings, max_price_by_loan_comfort)

    # 5. 计算实际月供
    if affordable_price_comfort > 0:
        loan_comfort = affordable_price_comfort * (1 - down_ratio)
        monthly_comfort = calculate_monthly_payment(loan_comfort, loan_years, annual_rate)
    else:
        monthly_comfort = None

    if affordable_price_safe > 0:
        loan_safe = affordable_price_safe * (1 - down_ratio)
        monthly_safe = calculate_monthly_payment(loan_safe, loan_years, annual_rate)
    else:
        monthly_safe = None

    # 6. 估算装修预算（额外，不占首付）
    avg_area = (area_min + area_max) / 2
    decoration_total = avg_area * decoration_budget_per_sqm / 10000

    # 7. 如果知道城市单价，估算可买面积
    affordable_area = None
    if city_unit_price and city_unit_price > 0 and affordable_price_comfort > 0:
        affordable_area = affordable_price_comfort * 10000 / city_unit_price

    return {
        '家庭月收入_元': monthly_income,
        '家庭月支出_元': monthly_expense,
        '可用于月供_元': disposable_income,
        '计算说明': expense_note,
        '可用于购房储蓄_万元': savings,
        '首付比例': f'{down_ratio*100:.0f}%',
        '月供安全线_元': round(max_monthly_payment_safe),
        '月供舒适线_元': round(max_monthly_payment_comfort),
        '安全线说明': f'月供≤可支配收入50%（{disposable_income}×50%）',
        '舒适线说明': f'月供≤可支配收入30%（{disposable_income}×30%）',
        '最大贷款额_安全线_万元': round(max_loan_safe, 1),
        '最大贷款额_舒适线_万元': round(max_loan_comfort, 1),
        '买得起总价_安全线_万元': round(affordable_price_safe, 1),
        '买得起总价_舒适线_万元': round(affordable_price_comfort, 1),
        '装修预留_万元(额外)': round(decoration_total, 2),
        '首付所需现金_万元': round(affordable_price_comfort * (down_ratio + extra_ratio), 2),
        '实际月供_舒适线': monthly_comfort,
        '实际月供_安全线': monthly_safe,
        '可买面积_估算_㎡': round(affordable_area, 1) if affordable_area else None,
    }


def assess_listing_affordability(listing_price, listing_area,
                                  monthly_income, savings,
                                  first_house=True, loan_years=30, annual_rate=3.95):
    """
    评估单套房源的「购买适配度」。

    评估逻辑：
      - 月供占收入比 ≤ 30% → 轻松
      - 月供占收入比 ≤ 40% → 适中
      - 月供占收入比 ≤ 50% → 紧张
      - 月供占收入比 > 50% → 超预算
      - 同时检查储蓄是否覆盖「必须现金」（首付+税费+中介费，不含装修）

    Returns:
        dict: 适配度评估
    """
    cost = calculate_landing_cost(listing_price, listing_area, first_house=first_house)

    down_ratio = 0.20 if first_house else 0.30
    loan = listing_price * (1 - down_ratio)
    monthly = calculate_monthly_payment(loan, loan_years, annual_rate)
    monthly_yuan = monthly['月供_元']

    # 月供占收入比
    income_ratio = monthly_yuan / monthly_income if monthly_income > 0 else 999

    # 「必须现金」= 首付 + 税费 + 中介费（装修可以后做）
    must_have_cash = (cost['首付']['首付金额_万元'] +
                      cost['税费']['税费合计_万元'] +
                      cost['中介费_万元'])
    landing = cost['落地总成本_万元']
    must_have_gap = savings - must_have_cash  # 正的=够，负的=不够
    landing_gap = savings - landing  # 含装修的缺口

    # 评级
    if income_ratio <= 0.30 and must_have_gap >= 0:
        level = '轻松'
        color = 'green'
    elif income_ratio <= 0.40 and must_have_gap >= 0:
        level = '适中'
        color = 'green'
    elif income_ratio <= 0.50 and must_have_gap >= 0:
        level = '紧张'
        color = 'orange'
    elif income_ratio <= 0.50 and must_have_gap >= -3:
        level = '勉强（储蓄稍不足）'
        color = 'orange'
    else:
        level = '超预算'
        color = 'red'

    return {
        '房源总价_万元': listing_price,
        '必须现金_万元': round(must_have_cash, 2),
        '落地成本_万元': landing,
        '月供_元': monthly_yuan,
        '月供占收入比': f'{income_ratio*100:.1f}%',
        '首付缺口_万元': round(-must_have_gap, 2) if must_have_gap < 0 else 0,
        '落地缺口_万元': round(-landing_gap, 2) if landing_gap < 0 else 0,
        '适配等级': level,
        '适配颜色': color,
        '明细': {
            '首付_万元': cost['首付']['首付金额_万元'],
            '税费_万元': cost['税费']['税费合计_万元'],
            '中介费_万元': cost['中介费_万元'],
            '装修_万元': cost['装修预算_万元'],
            '贷款_万元': round(loan, 2),
            '总利息_万元': monthly['总利息_万元'],
        }
    }


# ======================== 辅助：批量标记 ========================

def enrich_with_affordability(listings_df, monthly_income, savings,
                               first_house=True, loan_years=30,
                               monthly_expense=None):
    """
    为房源列表批量添加购买力适配标记。

    Args:
        listings_df: 房源 DataFrame（需含 price_num, area_num）
        monthly_income: 家庭月收入（元）
        savings: 储蓄（万元）
        first_house: 是否首套
        loan_years: 贷款年限
        monthly_expense: 家庭月支出（元），可选。提供后使用可支配收入计算月供占比

    Returns:
        DataFrame: 新增列: 月供_元, 月供占比, 落地成本_万元, 适配等级
    """
    df = listings_df.copy()
    if len(df) == 0:
        return df

    # 可支配收入
    if monthly_expense is not None and monthly_expense > 0:
        effective_income = max(1, monthly_income - monthly_expense)
    else:
        effective_income = monthly_income

    down_ratio = 0.20 if first_house else 0.30

    monthly_payments = []
    income_ratios = []
    landing_costs = []
    levels = []

    for _, row in df.iterrows():
        price = row['price_num']
        area = row['area_num']

        cost = calculate_landing_cost(price, area, first_house=first_house)
        landing = cost['落地总成本_万元']

        loan = price * (1 - down_ratio)
        mp = calculate_monthly_payment(loan, loan_years)
        mp_yuan = mp['月供_元']

        ratio = mp_yuan / effective_income if effective_income > 0 else 999

        if ratio <= 0.30:
            level = '轻松'
        elif ratio <= 0.40:
            level = '适中'
        elif ratio <= 0.50:
            level = '紧张'
        else:
            level = '超预算'

        monthly_payments.append(round(mp_yuan))
        income_ratios.append(round(ratio * 100, 1))
        landing_costs.append(round(landing, 2))
        levels.append(level)

    df['月供_元'] = monthly_payments
    df['月供占比'] = income_ratios
    df['落地成本_万元'] = landing_costs
    df['适配等级'] = levels

    return df
