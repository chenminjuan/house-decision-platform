# -*- coding: utf-8 -*-
# 房地产数据可视化模块
# 跨平台中文字体 + 中文标题(红色20号) + 绿色虚线网格 + tight_layout
import os
import matplotlib.pyplot as plt
from matplotlib import rcParams, font_manager
import numpy as np
import pandas as pd


def _setup_chinese_font():
    """跨平台中文字体配置，兼容 Windows / macOS / Streamlit Cloud (Linux)"""
    _CANDIDATES = [
        'WenQuanYi Micro Hei',   # Linux (packages.txt 安装)
        'SimHei',                 # Windows
        'Microsoft YaHei',        # Windows
        'PingFang SC',            # macOS
        'Noto Sans CJK SC',       # Linux 备选
    ]
    _available = {f.name for f in font_manager.fontManager.ttflist}
    for _font in _CANDIDATES:
        if _font in _available:
            rcParams['font.family'] = _font
            rcParams['axes.unicode_minus'] = False
            return
    # 降级方案
    rcParams['font.family'] = 'sans-serif'
    rcParams['axes.unicode_minus'] = False


# 模块导入时自动配置字体
_setup_chinese_font()


def _empty_chart(title='数据不足', message='当前筛选条件下无足够数据生成图表'):
    """数据不足时的占位图表"""
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.text(0.5, 0.5, f'{title}\n\n{message}',
            transform=ax.transAxes, ha='center', va='center',
            fontsize=16, color='gray')
    ax.set_xticks([])
    ax.set_yticks([])
    plt.tight_layout()
    return fig


def plot_price_distribution(df):
    """
    价格分布直方图
    参考 matplotlib.ipynb cell1/cell5 的写法
    """
    # 创建图表
    plt.figure(figsize=(10, 5))
    # 绘制直方图
    data = df['price_num'].dropna()
    if len(data) == 0:
        return _empty_chart('房价分布直方图', '当前筛选条件下无价格数据')
    # 过滤掉极端值使图表更清晰
    q99 = data.quantile(0.99)
    data_filtered = data[data <= q99]
    plt.hist(data_filtered, bins=40, color='steelblue', edgecolor='white', alpha=0.8)
    # 添加均值线
    mean_price = data_filtered.mean()
    plt.axvline(mean_price, color='red', linestyle='--', linewidth=2,
                label=f'均价: {mean_price:.1f}万元')
    # 添加中位线
    median_price = data_filtered.median()
    plt.axvline(median_price, color='green', linestyle='--', linewidth=2,
                label=f'中位价: {median_price:.1f}万元')
    # 标题
    plt.title('房价分布直方图', color='red', fontsize=20)
    # 坐标轴
    plt.xlabel('价格（万元）')
    plt.ylabel('挂牌数量')
    # 添加图例
    plt.legend(loc='upper right')
    # 添加网格线
    plt.grid(True, alpha=0.5, color='green', linestyle='--')
    # 设置刻字大小
    plt.xticks(rotation=0, fontsize=10)
    plt.yticks(rotation=0, fontsize=10)
    # 自动排版优化
    plt.tight_layout()
    return plt.gcf()


def plot_price_trend(df):
    """
    年度价格趋势折线图
    参考 matplotlib.ipynb cell1 的写法
    """
    from data_processor import get_price_trend
    trend = get_price_trend(df)
    # 过滤掉极端年份
    trend = trend[(trend['year_num'] >= 1990) & (trend['year_num'] <= 2025)]
    # 空数据检查
    if len(trend) == 0 or trend['均价_万元'].isna().all():
        return _empty_chart('年度房价趋势', '当前筛选条件下年份数据不足，无法生成趋势图')
    # 创建图表
    plt.figure(figsize=(10, 5))
    plt.plot(trend['year_num'], trend['均价_万元'], label='均价',
             color='steelblue', marker='o', linewidth=2)
    # 添加置信区间（上下一个标准差范围的近似）
    # 添加价格带
    plt.fill_between(trend['year_num'],
                     trend['均价_万元'] * 0.9,
                     trend['均价_万元'] * 1.1,
                     alpha=0.2, color='steelblue')
    # 标题
    plt.title('年度房价趋势', color='red', fontsize=20)
    # 坐标轴
    plt.xlabel('年份')
    plt.ylabel('均价（万元）')
    # 添加图例
    plt.legend(loc='upper left')
    # 添加网格线
    plt.grid(True, alpha=0.5, color='green', linestyle='--')
    # 设置刻字大小
    plt.xticks(rotation=45, fontsize=10)
    plt.yticks(rotation=0, fontsize=10)
    # 设置y轴从0开始
    min_price = trend['均价_万元'].min()
    plt.ylim(max(0, min_price * 0.8), trend['均价_万元'].max() * 1.2)
    # 自动排版优化
    plt.tight_layout()
    return plt.gcf()


def plot_area_price_scatter(df):
    """
    面积-房价散点图
    参考 matplotlib.ipynb cell5 的写法
    """
    # 采样以提高渲染性能（最多5000个点）
    sample_size = min(5000, len(df))
    data = df[['area_num', 'price_num']].dropna()
    if len(data) == 0:
        return _empty_chart('面积-房价关系', '当前筛选条件下无足够数据')
    data = data.sample(n=min(sample_size, len(data)), random_state=42)
    # 过滤合理范围
    data = data[(data['area_num'] <= 300) & (data['price_num'] <= 1000)]
    # 创建图表（与同行直方图统一高度）
    plt.figure(figsize=(10, 5))
    plt.scatter(data['area_num'], data['price_num'],
                color='steelblue',
                alpha=0.6,
                s=20)  # s是圆点大小
    # 添加趋势线
    z = np.polyfit(data['area_num'], data['price_num'], 1)
    p = np.poly1d(z)
    x_line = np.linspace(data['area_num'].min(), data['area_num'].max(), 100)
    plt.plot(x_line, p(x_line), color='red', linewidth=2, label='线性趋势线')
    # 标题
    plt.title('面积与房价关系', color='red', fontsize=20)
    # 坐标轴
    plt.xlabel('面积（㎡）')
    plt.ylabel('价格（万元）')
    # 添加图例
    plt.legend(loc='upper left')
    # 添加网格线
    plt.grid(True, alpha=0.5, color='green', linestyle='--')
    # 设置刻字大小
    plt.xticks(rotation=0, fontsize=10)
    plt.yticks(rotation=0, fontsize=10)
    # 自动排版优化
    plt.tight_layout()
    return plt.gcf()


def plot_room_pie(df):
    """
    户型分布饼图
    参考 matplotlib.ipynb cell4 的写法
    """
    room_counts = df['room_category'].dropna().value_counts()
    if len(room_counts) == 0:
        return _empty_chart('户型分布', '当前筛选条件下无户型数据')
    # 创建图表
    plt.figure(figsize=(10, 5))
    # 颜色列表
    colors = ['steelblue', 'coral', 'seagreen', 'gold', 'mediumpurple', 'lightcoral']
    explode = [0.05] * len(room_counts)  # 稍微分离每块
    plt.pie(room_counts.values,
            labels=room_counts.index,
            autopct='%1.1f%%',
            colors=colors[:len(room_counts)],
            explode=explode,
            shadow=True)
    # 标题
    plt.title('户型分布', color='red', fontsize=20)
    # 自动排版优化
    plt.tight_layout()
    return plt.gcf()


def plot_city_price_bar(df, top_n=10):
    """
    城市均价对比柱状图
    参考 matplotlib.ipynb cell2 的写法（竖柱）
    """
    from data_processor import get_city_stats
    city_stats = get_city_stats(df)
    # 取挂牌量Top N的城市（有代表性的城市）
    top_cities = city_stats[city_stats['挂牌量'] >= 30].head(top_n)
    # 创建图表
    plt.figure(figsize=(10, 5))
    bars = plt.bar(top_cities['city'], top_cities['均价_万元'],
                   color='steelblue', label='均价')
    # 在柱状图上显示数值
    for bar, val in zip(bars, top_cities['均价_万元']):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
                 f'{val:.0f}', ha='center', va='bottom', fontsize=9)
    # 标题
    plt.title('主要城市均价对比', color='red', fontsize=20)
    # 坐标轴
    plt.xlabel('城市')
    plt.ylabel('均价（万元）')
    # 添加网格线（只保留横线）
    plt.grid(axis='y', alpha=0.5, color='green', linestyle='--')
    # 设置刻字大小
    plt.xticks(rotation=45, fontsize=10)
    plt.yticks(rotation=0, fontsize=10)
    # 设置y轴范围
    plt.ylim(0, top_cities['均价_万元'].max() * 1.2)
    # 自动排版优化
    plt.tight_layout()
    return plt.gcf()


def plot_unit_price_ranking(df, top_n=15, highlight_cities=None):
    """
    单价排行横向柱状图
    参考 matplotlib.ipynb cell3 的写法（横柱 barh）
    """
    from data_processor import get_city_stats
    city_stats = get_city_stats(df)
    # 取挂牌量>=30的城市
    city_stats = city_stats[city_stats['挂牌量'] >= 30]
    # 按单价排序取top_n
    top_cities = city_stats.nlargest(top_n, '均单价_元每平')
    # 反转顺序使最高的在顶部
    top_cities = top_cities.iloc[::-1]
    # 创建图表
    plt.figure(figsize=(10, 5))
    # 颜色设置：高亮城市用红色，其他用蓝色
    colors = []
    for city in top_cities['city']:
        if highlight_cities and city in highlight_cities:
            colors.append('red')
        else:
            colors.append('steelblue')
    plt.barh(top_cities['city'], top_cities['均单价_元每平'],
             color=colors, label='均单价')
    # 标题
    plt.title('城市单价排行', color='red', fontsize=20)
    # 坐标轴
    plt.xlabel('均单价（元/㎡）')
    plt.ylabel('城市')
    # 添加图例
    if highlight_cities:
        from matplotlib.patches import Patch
        legend_elements = [Patch(facecolor='red', label='已选对比城市'),
                           Patch(facecolor='steelblue', label='其他城市')]
        plt.legend(handles=legend_elements, loc='lower right')
    # 添加网格线（只保留竖线）
    plt.grid(axis='x', alpha=0.5, color='green', linestyle='--')
    # 设置刻字大小
    plt.xticks(rotation=0, fontsize=10)
    plt.yticks(rotation=0, fontsize=10)
    # 自动排版优化
    plt.tight_layout()
    return plt.gcf()


def plot_city_comparison_bars(df, cities, metric='均价_万元'):
    """
    多城市分组柱状图
    参考 matplotlib.ipynb cell2 的写法
    """
    from data_processor import get_city_stats
    city_stats = get_city_stats(df)
    compare_data = city_stats[city_stats['city'].isin(cities)]
    # 如果城市不在城市统计中，跳过
    if len(compare_data) == 0:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.text(0.5, 0.5, '所选城市数据不足，无法对比', ha='center', va='center',
                fontsize=15, transform=ax.transAxes)
        ax.set_title('城市对比', color='red', fontsize=20)
        plt.tight_layout()
        return plt.gcf()
    # 创建图表
    plt.figure(figsize=(10, 5))
    metric_labels = {
        '均价_万元': '均价（万元）',
        '中位价_万元': '中位价（万元）',
        '均单价_元每平': '均单价（元/㎡）',
        '挂牌量': '挂牌量',
        '平均面积': '平均面积（㎡）',
        '平均房龄': '平均房龄（年）'
    }
    label = metric_labels.get(metric, metric)
    bars = plt.bar(compare_data['city'], compare_data[metric],
                   color=['steelblue', 'coral', 'seagreen', 'gold', 'mediumpurple'][:len(cities)])
    # 数值标签
    for bar, val in zip(bars, compare_data[metric]):
        if metric == '均单价_元每平':
            plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
                     f'{val:.0f}', ha='center', va='bottom', fontsize=9)
        else:
            plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
                     f'{val:.1f}', ha='center', va='bottom', fontsize=9)
    # 标题
    plt.title(f'城市{label}对比', color='red', fontsize=20)
    # 坐标轴
    plt.xlabel('城市')
    plt.ylabel(label)
    # 网格
    plt.grid(axis='y', alpha=0.5, color='green', linestyle='--')
    # 刻度
    plt.xticks(rotation=30, fontsize=10)
    plt.yticks(rotation=0, fontsize=10)
    # Y轴范围
    if metric in ['均单价_元每平', '均价_万元', '中位价_万元']:
        plt.ylim(0, compare_data[metric].max() * 1.2)
    # 排版
    plt.tight_layout()
    return plt.gcf()


def plot_score_breakdown(scores_dict):
    """
    推荐得分分解条形图
    参考 matplotlib.ipynb cell3 的写法（横柱 barh）
    """
    labels = list(scores_dict.keys())
    values = list(scores_dict.values())
    # 创建图表
    plt.figure(figsize=(10, 5))
    colors = ['steelblue', 'coral', 'seagreen', 'gold', 'mediumpurple']
    plt.barh(labels, values, color=colors[:len(labels)])
    # 数值标签
    for bar, val in zip(plt.gca().patches, values):
        plt.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                 f'{val:.1f}分', ha='left', va='center', fontsize=10)
    # 标题
    plt.title('各维度得分分解', color='red', fontsize=20)
    # 坐标轴
    plt.xlabel('得分')
    # 网格
    plt.grid(axis='x', alpha=0.5, color='green', linestyle='--')
    # 刻度
    plt.xticks(rotation=0, fontsize=10)
    plt.yticks(rotation=0, fontsize=10)
    # X轴范围
    plt.xlim(0, 110)
    # 排版
    plt.tight_layout()
    return plt.gcf()


def plot_multi_city_trend(df, cities):
    """
    多城市价格趋势对比折线图
    参考 matplotlib.ipynb cell1 的写法
    """
    # 创建图表
    plt.figure(figsize=(10, 5))
    colors = ['steelblue', 'coral', 'seagreen', 'gold', 'mediumpurple']
    for i, city in enumerate(cities):
        city_data = df[df['city'] == city].dropna(subset=['year_num'])
        city_data = city_data[(city_data['year_num'] >= 2000) & (city_data['year_num'] <= 2025)]
        if len(city_data) < 10:
            continue
        yearly = city_data.groupby('year_num')['price_num'].mean().reset_index()
        yearly = yearly.sort_values('year_num')
        color = colors[i % len(colors)]
        plt.plot(yearly['year_num'], yearly['price_num'],
                 label=f'{city}均价', marker='o', color=color, linewidth=2)
    # 标题
    plt.title('多城市价格趋势对比', color='red', fontsize=20)
    # 坐标轴
    plt.xlabel('年份')
    plt.ylabel('均价（万元）')
    # 图例
    plt.legend(loc='upper left')
    # 网格
    plt.grid(True, alpha=0.5, color='green', linestyle='--')
    # 刻度
    plt.xticks(rotation=45, fontsize=10)
    plt.yticks(rotation=0, fontsize=10)
    # 排版
    plt.tight_layout()
    return plt.gcf()


# ========== plotly 图表（用于交互式复杂图表） ==========
try:
    import plotly.graph_objects as go
    import plotly.express as px

    def plot_radar_chart(regions_data):
        """
        多维度雷达图（plotly - matplotlib不支持雷达图）
        regions_data: {城市名: {'维度1': 值, '维度2': 值, ...}}
        """
        categories = list(list(regions_data.values())[0].keys())
        fig = go.Figure()
        colors = ['steelblue', 'coral', 'seagreen', 'gold', 'mediumpurple']
        for i, (region, values) in enumerate(regions_data.items()):
            vals = list(values.values())
            # 闭合雷达图
            vals_closed = vals + [vals[0]]
            cats_closed = categories + [categories[0]]
            fig.add_trace(go.Scatterpolar(
                r=vals_closed,
                theta=cats_closed,
                name=region,
                fill='toself',
                fillcolor=colors[i % len(colors)],
                opacity=0.3,
                line=dict(color=colors[i % len(colors)], width=2)
            ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100]),
            ),
            title=dict(text='区域多维度对比雷达图', font=dict(size=20, color='red')),
            showlegend=True
        )
        return fig

    def plot_unit_heatmap(df, top_n_cities=10):
        """
        户型×城市 单价热力图（plotly）
        """
        # 获取挂牌量Top N城市
        top_cities = df.groupby('city')['price_num'].count().nlargest(top_n_cities).index.tolist()
        # 获取户型分类
        room_cats = ['1室', '2室', '3室', '4室', '5室+']
        heatmap_data = df[df['city'].isin(top_cities)].groupby(
            ['room_category', 'city'])['unit_num'].mean().reset_index()
        # 创建透视表
        pivot = heatmap_data.pivot(index='room_category', columns='city', values='unit_num')
        # 按户型排序
        pivot = pivot.reindex([r for r in room_cats if r in pivot.index])
        # 按均价排序城市
        pivot = pivot[top_cities]
        fig = go.Figure(data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale='RdYlGn_r',
            text=[[f'{v:.0f}' if not pd.isna(v) else 'N/A' for v in row] for row in pivot.values],
            texttemplate='%{text}',
            textfont=dict(size=10),
            colorbar_title='元/㎡'
        ))
        fig.update_layout(
            title=dict(text='户型×城市 单价热力图', font=dict(size=20, color='red')),
            xaxis_title='城市',
            yaxis_title='户型'
        )
        return fig

except ImportError:
    # plotly未安装时的降级处理
    def plot_radar_chart(regions_data):
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.text(0.5, 0.5, '雷达图需要安装plotly库\n请运行: pip install plotly',
                ha='center', va='center', fontsize=15, transform=ax.transAxes)
        ax.set_title('雷达图（需plotly支持）', color='red', fontsize=20)
        plt.tight_layout()
        return plt.gcf()

    def plot_unit_heatmap(df, top_n_cities=10):
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.text(0.5, 0.5, '热力图需要安装plotly库\n请运行: pip install plotly',
                ha='center', va='center', fontsize=15, transform=ax.transAxes)
        ax.set_title('热力图（需plotly支持）', color='red', fontsize=20)
        plt.tight_layout()
        return plt.gcf()
