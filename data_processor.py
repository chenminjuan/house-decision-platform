# -*- coding: utf-8 -*-
# 房地产数据清洗与处理模块
# 参考 数据分析.ipynb 的编码风格：中文注释 + print检查 + 过程式风格
import pandas as pd
import numpy as np
import streamlit as st


# 尝试使用streamlit缓存（非streamlit环境下跳过缓存装饰器）
try:
    _st_cache = st.cache_data(ttl=3600)
except Exception:
    _st_cache = lambda f: f  # 非streamlit环境，原样返回函数


@_st_cache
def load_and_clean_data(filepath='data/house_sales.csv'):
    """
    完整数据清洗管线：加载原始CSV → 解析 → 清洗 → 派生列
    每步用 print() 输出检查，参考 数据分析.ipynb 风格
    """
    # ========== 第1步：加载数据 ==========
    print('========== 第1步：加载数据 ==========')
    df = pd.read_csv(filepath, encoding='utf-8-sig')  # 去除BOM头
    print(f'原始数据形状: {df.shape}')
    print(f'列名: {df.columns.tolist()}')
    print(df.head(3))
    print(df.dtypes)

    # ========== 第2步：数值列解析 ==========
    print('\n========== 第2步：数值列解析 ==========')
    # 解析价格：去除"万"后缀，转为float
    df['price_num'] = df['price'].str.extract(r'(\d+\.?\d*)', expand=False)
    df['price_num'] = pd.to_numeric(df['price_num'], errors='coerce')
    print(f'price解析后有效值: {df["price_num"].notna().sum()} / {len(df)}')

    # 解析面积：去除"㎡"后缀
    df['area_num'] = df['area'].str.extract(r'(\d+\.?\d*)', expand=False)
    df['area_num'] = pd.to_numeric(df['area_num'], errors='coerce')
    print(f'area解析后有效值: {df["area_num"].notna().sum()} / {len(df)}')

    # 解析单价：去除"元/㎡"后缀
    df['unit_num'] = df['unit'].str.extract(r'(\d+\.?\d*)', expand=False)
    df['unit_num'] = pd.to_numeric(df['unit_num'], errors='coerce')
    print(f'unit解析后有效值: {df["unit_num"].notna().sum()} / {len(df)}')

    # 解析建成年份：提取4位数字年份
    df['year_num'] = df['year'].str.extract(r'(\d{4})', expand=False)
    df['year_num'] = pd.to_numeric(df['year_num'], errors='coerce')
    # 标记异常年份（1949年前或2025年后）
    df.loc[df['year_num'] < 1949, 'year_num'] = np.nan
    df.loc[df['year_num'] > 2025, 'year_num'] = np.nan
    print(f'year解析后有效值: {df["year_num"].notna().sum()} / {len(df)}')

    # 解析户型：提取室数和厅数（参考notebook str.split分列写法）
    rooms_split = df['rooms'].str.split('室', expand=True)
    df['num_rooms'] = pd.to_numeric(rooms_split[0], errors='coerce')
    # 从"X厅"中提取厅数
    halls_extract = df['rooms'].str.extract(r'(\d+)厅', expand=False)
    df['num_halls'] = pd.to_numeric(halls_extract, errors='coerce')
    print(f'num_rooms有效值: {df["num_rooms"].notna().sum()}')
    print(f'num_halls有效值: {df["num_halls"].notna().sum()}')

    # 解析楼层级别（低/中/高）
    df['floor_level'] = df['floor'].str.extract(r'(低层|中层|高层)', expand=False)
    print(f'floor_level分布:')
    print(df['floor_level'].value_counts())

    # ========== 第3步：缺失值处理 ==========
    print('\n========== 第3步：缺失值处理 ==========')
    print('缺失值统计:')
    print(df[['price_num', 'area_num', 'unit_num', 'year_num', 'num_rooms', 'num_halls']].isna().sum())

    # 剔除价格、面积、单价中任一为空的行（核心分析字段不能缺）
    before_drop = len(df)
    df = df.dropna(subset=['price_num', 'area_num', 'unit_num'])
    print(f'剔除关键字段缺失后: {len(df)} 行 (删除 {before_drop - len(df)} 行)')

    # 朝向缺失值填充为"其他"
    df['toward'] = df['toward'].fillna('其他')
    print(f'朝向分布:')
    print(df['toward'].value_counts().head(10))

    # ========== 第4步：去重（按链接） ==========
    print('\n========== 第4步：去重处理 ==========')
    # 剔除origin_url为空的行
    df = df.dropna(subset=['origin_url'])
    before_dedup = len(df)
    df = df.drop_duplicates(subset=['origin_url'], keep='first')
    print(f'去重后: {len(df)} 行 (删除 {before_dedup - len(df)} 行)')

    # ========== 第5步：异常值过滤（IQR方法） ==========
    print('\n========== 第5步：异常值过滤 ==========')
    print(f'过滤前价格范围: {df["price_num"].min():.1f} - {df["price_num"].max():.1f} 万元')
    print(f'过滤前面积范围: {df["area_num"].min():.1f} - {df["area_num"].max():.1f} ㎡')
    print(f'过滤前单价范围: {df["unit_num"].min():.1f} - {df["unit_num"].max():.1f} 元/㎡')

    # 价格过滤：保留3-3000万之间的合理价格
    df = df[(df['price_num'] >= 3) & (df['price_num'] <= 3000)]
    # 面积过滤：保留20-500㎡之间的合理面积
    df = df[(df['area_num'] >= 20) & (df['area_num'] <= 500)]
    # 单价过滤：保留1000-150000元/㎡之间的合理单价
    df = df[(df['unit_num'] >= 1000) & (df['unit_num'] <= 150000)]

    print(f'异常值过滤后: {len(df)} 行')
    print(f'过滤后价格范围: {df["price_num"].min():.1f} - {df["price_num"].max():.1f} 万元')
    print(f'过滤后面积范围: {df["area_num"].min():.1f} - {df["area_num"].max():.1f} ㎡')
    print(f'过滤后单价范围: {df["unit_num"].min():.1f} - {df["unit_num"].max():.1f} 元/㎡')

    # ========== 第6步：数据类型转换 + 派生列 ==========
    print('\n========== 第6步：数据类型转换与派生列 ==========')
    # 类型转换（参考notebook astype写法）
    df['num_rooms'] = df['num_rooms'].astype('Int64')  # 可为空的整数类型
    df['num_halls'] = df['num_halls'].astype('Int64')
    df['toward'] = df['toward'].astype('category')
    df['province'] = df['province'].astype('category')
    df['city'] = df['city'].astype('category')
    df['floor_level'] = df['floor_level'].astype('category')
    print(f'转换后类型:')
    print(df.dtypes)

    # 派生列：房龄
    df['age'] = 2025 - df['year_num']
    df.loc[df['age'] < 0, 'age'] = np.nan

    # 派生列：面积段分类（参考notebook pd.cut写法）
    area_bins = [0, 50, 90, 120, 150, 200, 500]
    area_labels = ['<50㎡', '50-90㎡', '90-120㎡', '120-150㎡', '150-200㎡', '200㎡+']
    df['area_category'] = pd.cut(df['area_num'], bins=area_bins, labels=area_labels)
    print(f'面积段分布:')
    print(df['area_category'].value_counts())

    # 派生列：价格段分类
    price_bins = [0, 30, 50, 80, 120, 200, 500, 3000]
    price_labels = ['<30万', '30-50万', '50-80万', '80-120万', '120-200万', '200-500万', '500万+']
    df['price_category'] = pd.cut(df['price_num'], bins=price_bins, labels=price_labels)
    print(f'价格段分布:')
    print(df['price_category'].value_counts())

    # 派生列：户型分类
    def room_category(rooms):
        if pd.isna(rooms):
            return '未知'
        rooms = int(rooms)
        if rooms <= 1:
            return '1室'
        elif rooms == 2:
            return '2室'
        elif rooms == 3:
            return '3室'
        elif rooms == 4:
            return '4室'
        else:
            return '5室+'

    df['room_category'] = df['num_rooms'].apply(room_category)
    print(f'户型分类分布:')
    print(df['room_category'].value_counts())

    # 派生列：验证单价 = 总价*10000/面积 (交叉验证)
    df['unit_calculated'] = df['price_num'] * 10000 / df['area_num']
    df['unit_deviation'] = abs(df['unit_num'] - df['unit_calculated']) / df['unit_num']
    # 标记单价偏差超过20%的记录
    deviation_flag = df['unit_deviation'] > 0.2
    print(f'单价偏差>20%的记录数: {deviation_flag.sum()}')

    # ========== 第7步：最终确认 ==========
    print('\n========== 第7步：最终数据确认 ==========')
    print(f'最终数据形状: {df.shape}')
    print(f'覆盖城市数: {df["city"].nunique()}')
    print(f'覆盖省份数: {df["province"].nunique()}')
    print(f'最终列名: {df.columns.tolist()}')
    print(df[['price_num', 'area_num', 'unit_num', 'year_num', 'num_rooms', 'num_halls', 'age']].describe())

    return df


def get_summary_stats(df):
    """获取数据概览统计指标，返回dict"""
    stats = {
        '总挂牌量': len(df),
        '均价(万元)': round(df['price_num'].mean(), 1),
        '中位价(万元)': round(df['price_num'].median(), 1),
        '均单价(元/㎡)': round(df['unit_num'].mean(), 0),
        '平均面积(㎡)': round(df['area_num'].mean(), 1),
        '覆盖城市数': df['city'].nunique(),
        '覆盖省份数': df['province'].nunique(),
        '平均房龄(年)': round(df['age'].dropna().mean(), 1),
    }
    return stats


def get_province_list(df):
    """获取排序后的省份列表"""
    provinces = ['全部'] + sorted(df['province'].dropna().unique().tolist())
    return provinces


def get_city_list(df, province=None):
    """获取排序后的城市列表，可按省份筛选"""
    if province and province != '全部':
        cities = ['全部'] + sorted(df[df['province'] == province]['city'].dropna().unique().tolist())
    else:
        cities = ['全部'] + sorted(df['city'].dropna().unique().tolist())
    return cities


def get_room_options(df):
    """获取户型选项"""
    rooms = sorted(df['room_category'].dropna().unique().tolist())
    return rooms


def get_price_trend(df):
    """按年份统计价格趋势，返回聚合DataFrame"""
    trend = df.dropna(subset=['year_num']).groupby('year_num').agg(
        均价_万元=('price_num', 'mean'),
        中位价_万元=('price_num', 'median'),
        挂牌量=('price_num', 'count'),
        均单价_元每平=('unit_num', 'mean')
    ).reset_index()
    trend['year_num'] = trend['year_num'].astype(int)
    trend = trend.sort_values('year_num')
    return trend


def get_city_stats(df):
    """按城市聚合统计信息"""
    city_stats = df.groupby('city').agg(
        均价_万元=('price_num', 'mean'),
        中位价_万元=('price_num', 'median'),
        均单价_元每平=('unit_num', 'mean'),
        挂牌量=('price_num', 'count'),
        平均面积=('area_num', 'mean'),
        平均房龄=('age', 'mean'),
        最高价=('price_num', 'max'),
        最低价=('price_num', 'min')
    ).reset_index()
    # 计算价格标准差（离散度）
    price_std = df.groupby('city')['price_num'].std().reset_index()
    price_std.columns = ['city', '价格标准差']
    city_stats = city_stats.merge(price_std, on='city', how='left')
    # 计算百分位排名
    city_stats['均价排名'] = city_stats['均价_万元'].rank(ascending=False)
    city_stats['流动性排名'] = city_stats['挂牌量'].rank(ascending=False)
    return city_stats.sort_values('挂牌量', ascending=False)


def get_province_stats(df):
    """按省份聚合统计信息"""
    province_stats = df.groupby('province').agg(
        均价_万元=('price_num', 'mean'),
        均单价_元每平=('unit_num', 'mean'),
        挂牌量=('price_num', 'count'),
        城市数=('city', 'nunique')
    ).reset_index()
    return province_stats.sort_values('挂牌量', ascending=False)


def get_room_price_stats(df):
    """按户型分类统计价格"""
    room_stats = df.groupby('room_category').agg(
        均价_万元=('price_num', 'mean'),
        中位价_万元=('price_num', 'median'),
        均单价_元每平=('unit_num', 'mean'),
        挂牌量=('price_num', 'count'),
        平均面积=('area_num', 'mean')
    ).reset_index()
    return room_stats
