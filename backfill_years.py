# -*- coding: utf-8 -*-
# 建成年份渐进式回填脚本
# 功能：对现有数据中缺少年份的房源，逐条访问详情页补充建成年份
#
# 使用方式：
#   python backfill_years.py                       # 默认回填200条（优先级排序）
#   python backfill_years.py --limit 500           # 回填500条
#   python backfill_years.py --city 浏阳           # 只回填指定城市
#   python backfill_years.py --resume              # 从上次中断处继续
#   python backfill_years.py --dry-run             # 预览将要回填的记录数

import pandas as pd
import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# 确保可以导入同目录的 data_fetcher
sys.path.insert(0, str(Path(__file__).parent))

from data_fetcher import fetch_listing_detail

# ======================== 配置 ========================

BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / 'data' / 'house_sales.csv'
PROGRESS_FILE = BASE_DIR / 'data' / 'backfill_progress.json'
QUERY_LOG_FILE = BASE_DIR / 'data' / 'queried_cities.json'
REQUEST_DELAY = 0.8  # 每条请求间隔（秒），比 data_fetcher 稍快

# 默认优先级城市（用户画像 + 兜底）
DEFAULT_PRIORITY_CITIES = ['浏阳', '湛江', '昌邑', '巢湖', '太仓', '北海', '清镇', '简阳']


def _load_query_priority():
    """
    从 queried_cities.json 读取用户实际查询过的城市，按查询频次排序。
    返回: list[city] — 排在前面的优先回填
    """
    if not QUERY_LOG_FILE.exists():
        return []

    try:
        with open(QUERY_LOG_FILE, 'r', encoding='utf-8') as f:
            log = json.load(f)
    except Exception:
        return []

    # 按查询次数降序
    sorted_cities = sorted(log.items(), key=lambda x: x[1].get('count', 0), reverse=True)
    return [city for city, _ in sorted_cities]


def _get_priority_cities(auto_mode=False):
    """
    获取回填优先城市列表。
    auto_mode=True: 用户实际查询的城市排在前面，默认列表兜底
    auto_mode=False: 使用默认列表
    """
    if auto_mode:
        queried = _load_query_priority()
        if queried:
            print(f'[AUTO] 从查询日志读取到 {len(queried)} 个城市')
            for c in queried[:10]:
                print(f'       {c}')
            # 用户查询过的排前面 + 默认列表去重兜底
            merged = queried + [c for c in DEFAULT_PRIORITY_CITIES if c not in queried]
            return merged
        else:
            print('[AUTO] 查询日志为空，使用默认优先级列表')
            return list(DEFAULT_PRIORITY_CITIES)
    else:
        return list(DEFAULT_PRIORITY_CITIES)


# ======================== 核心逻辑 ========================

def load_data():
    """加载现有数据"""
    if not DATA_FILE.exists():
        print(f'[ERROR] 数据文件不存在: {DATA_FILE}')
        sys.exit(1)
    return pd.read_csv(DATA_FILE, encoding='utf-8-sig')


def load_progress():
    """加载回填进度"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'completed_urls': [], 'total_filled': 0, 'last_update': None}


def save_progress(progress):
    """保存回填进度"""
    progress['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def get_backfill_queue(df, city_filter=None, limit=200, auto_mode=False):
    """
    获取待回填的房源列表，按优先级排序。

    优先级（auto_mode=True）：
      1. 用户实际查询过的城市（queried_cities.json）
      2. 默认偏好城市（用户画像）
      3. 其余城市按挂牌量降序

    优先级（auto_mode=False）：
      1. 默认偏好城市
      2. 其余城市按挂牌量降序
    """
    # 筛选缺年份的记录
    missing = df[df['year'].isna() | (df['year'] == '')].copy()
    missing = missing.drop_duplicates(subset=['origin_url'])

    if len(missing) == 0:
        print('[OK] 没有缺少年份的记录，无需回填。')
        return pd.DataFrame()

    # 按城市筛选
    if city_filter:
        missing = missing[missing['city'] == city_filter]
        if len(missing) == 0:
            print(f'[OK] 城市 "{city_filter}" 没有缺年份的记录。')
            return pd.DataFrame()

    # 获取优先级城市列表
    priority_cities = _get_priority_cities(auto_mode)

    # 优先级映射：排名越靠前，分数越高
    city_priority_score = {}
    for i, c in enumerate(priority_cities):
        city_priority_score[c] = len(priority_cities) - i  # 越靠前分越高

    # 挂牌量排名
    city_counts = df['city'].value_counts()
    missing['city_rank'] = missing['city'].map(lambda c: city_counts.get(c, 0))
    missing['priority_score'] = missing['city'].apply(lambda c: city_priority_score.get(c, 0))

    # 排序：优先级分数 > 挂牌量
    missing = missing.sort_values(['priority_score', 'city_rank'], ascending=[False, False])

    return missing.head(limit)


def run_backfill(df, queue, progress, dry_run=False):
    """
    执行回填

    Args:
        df: 完整 DataFrame
        queue: 待回填的房源 DataFrame
        progress: 进度 dict
        dry_run: True=仅预览，不实际抓取

    Returns:
        int: 成功回填的记录数
    """
    completed = set(progress.get('completed_urls', []))
    filled = 0

    for idx, row in queue.iterrows():
        url = row.get('origin_url', '')
        if not url or url in completed:
            continue

        if dry_run:
            print(f'  [DRY-RUN] {row.get("city", "")} | {row.get("name", "")} | {url[:60]}...')
            filled += 1
            continue

        # 实际抓取
        detail = fetch_listing_detail(url)
        year = detail.get('year', '')

        if year:
            df.at[idx, 'year'] = year
            filled += 1
            completed.add(url)
            progress['completed_urls'] = list(completed)
            progress['total_filled'] = progress.get('total_filled', 0) + 1

        # 进度提示
        if (filled) % 20 == 0 and filled > 0:
            print(f'    进度: {filled} 条已填充')
            save_progress(progress)

        # 请求间隔
        time.sleep(REQUEST_DELAY)

    return filled


def backfill_on_demand(listings_df, data_file=None, request_delay=0.8):
    """
    按需回填：只针对用户当前筛选结果中缺少年份的房源。
    适用场景：用户在决策报告中发现年份覆盖率低，主动触发回填。

    Args:
        listings_df: 用户筛选后的房源 DataFrame（需含 origin_url, year, year_num 列）
        data_file: CSV 数据文件路径，None=使用默认
        request_delay: 请求间隔（秒）

    Returns:
        dict: {
            'total_missing': 待回填数量,
            'filled': 成功回填数量,
            'after_coverage': 回填后覆盖率(%),
            'still_missing': 回填后仍缺失数量（房源本身未标明年份）,
        }
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from data_fetcher import fetch_listing_detail

    if data_file is None:
        data_file = DATA_FILE

    df = listings_df.drop_duplicates(subset=['origin_url'])

    # 找出缺少年份的
    missing = df[df['year'].isna() | (df['year'] == '')]
    total_missing = len(missing)

    if total_missing == 0:
        return {'total_missing': 0, 'filled': 0, 'after_coverage': 100.0, 'still_missing': 0}

    print(f'[按需回填] 待补全: {total_missing} 条')

    filled = 0
    for idx in missing.index:
        url = df.at[idx, 'origin_url'] if pd.notna(df.at[idx, 'origin_url']) else ''
        if not url:
            continue

        try:
            detail = fetch_listing_detail(url)
            year = detail.get('year', '')
            if year:
                df.at[idx, 'year'] = str(year)
                df.at[idx, 'year_num'] = pd.to_numeric(year, errors='coerce')
                filled += 1
        except Exception as e:
            print(f'  [WARN] {url[:60]}... 回填失败: {e}')

        time.sleep(request_delay)

    # 同步到 CSV 文件
    if filled > 0 and data_file.exists():
        full_df = pd.read_csv(data_file, encoding='utf-8-sig')
        # 按 origin_url 更新年份
        updated_urls = set(df.loc[df['year'].notna() & (df['year'] != ''), 'origin_url'])
        for i, row in full_df.iterrows():
            url = row.get('origin_url', '')
            if url in updated_urls and url in df.index:
                continue
            if url in updated_urls:
                matching = df[df['origin_url'] == url]
                if len(matching) > 0 and pd.notna(matching.iloc[0]['year']) and matching.iloc[0]['year'] != '':
                    full_df.at[i, 'year'] = matching.iloc[0]['year']
        full_df.to_csv(data_file, index=False, encoding='utf-8-sig')
        print(f'[按需回填] CSV 已同步更新')

    # 统计回填后覆盖率
    still_missing = df['year'].isna().sum() + (df['year'] == '').sum()
    after_cov = (len(df) - still_missing) / len(df) * 100 if len(df) > 0 else 0

    print(f'[按需回填] 成功 {filled}/{total_missing}, 覆盖率 {after_cov:.0f}%, 仍缺失 {still_missing}')

    return {
        'total_missing': total_missing,
        'filled': filled,
        'after_coverage': round(after_cov, 1),
        'still_missing': still_missing,
        'updated_df': df,
    }


def print_status(df):
    """打印当前年份覆盖率状态"""
    total = len(df)
    has_year = df['year'].notna().sum() & (df['year'] != '').sum()
    coverage = has_year / total * 100 if total > 0 else 0

    unique_urls = df['origin_url'].nunique()
    unique_has_year = df[df['year'].notna() & (df['year'] != '')]['origin_url'].nunique()
    unique_coverage = unique_has_year / unique_urls * 100 if unique_urls > 0 else 0

    print(f'总记录: {total:,}  有年份: {has_year:,} ({coverage:.1f}%)')
    print(f'唯一URL: {unique_urls:,}  有年份: {unique_has_year:,} ({unique_coverage:.1f}%)')

    # 按城市
    city_stats = df.groupby('city').agg(
        total=('year', 'count'),
        has_year=('year', lambda x: x.notna().sum()),
    )
    city_stats['coverage'] = (city_stats['has_year'] / city_stats['total'] * 100)
    low = city_stats[city_stats['total'] >= 30].nsmallest(5, 'coverage')
    if len(low) > 0:
        print('覆盖率最低的5个城市:')
        for city, row in low.iterrows():
            print(f'  {city}: {row["coverage"]:.0f}% ({int(row["has_year"])}/{int(row["total"])})')


# ======================== CLI ========================

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='建成年份渐进式回填脚本')
    parser.add_argument('--limit', type=int, default=200, help='最大回填数量（默认200）')
    parser.add_argument('--city', type=str, default=None, help='只回填指定城市')
    parser.add_argument('--resume', action='store_true', help='从上次中断处继续（跳过已完成的URL）')
    parser.add_argument('--dry-run', action='store_true', help='仅预览，不实际抓取')
    parser.add_argument('--auto', action='store_true', dest='auto_mode', help='根据用户实际查询记录驱动回填优先级')
    parser.add_argument('--status', action='store_true', help='仅显示当前数据覆盖率状态')

    args = parser.parse_args()

    print('=' * 60)
    print('建成年份渐进式回填脚本')
    print(f'时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 60)

    if args.status:
        df = load_data()
        print_status(df)
        sys.exit(0)

    # 加载数据
    df = load_data()
    print()
    print('[当前状态]')
    print_status(df)

    # 加载进度
    progress = load_progress() if args.resume else {'completed_urls': [], 'total_filled': 0, 'last_update': None}
    if progress.get('completed_urls'):
        print(f'\n[RESUME] 已跳过 {len(progress["completed_urls"])} 条已完成的URL')

    # 构建队列
    queue = get_backfill_queue(df, city_filter=args.city, limit=args.limit, auto_mode=args.auto_mode)
    if len(queue) == 0:
        print('\n没有需要回填的记录。')
        sys.exit(0)

    print(f'\n[计划回填] {len(queue)} 条记录')
    if args.city:
        print(f'  城市: {args.city}')
    print(f'  预计耗时: {len(queue) * REQUEST_DELAY:.0f} 秒 (~{len(queue) * REQUEST_DELAY / 60:.1f} 分钟)')

    if args.dry_run:
        print('\n[预览模式 - 不实际抓取]')
        run_backfill(df, queue, progress, dry_run=True)
        print(f'\n预览完成: {len(queue)} 条待回填')
        sys.exit(0)

    # 确认
    print()
    confirm = input('确认开始回填？(y/n): ')
    if confirm.lower() != 'y':
        print('取消回填。')
        sys.exit(0)

    # 执行回填
    print('\n[开始回填]')
    filled = run_backfill(df, queue, progress)

    # 保存数据
    df.to_csv(DATA_FILE, index=False, encoding='utf-8-sig')
    save_progress(progress)

    print('\n' + '=' * 60)
    print(f'[完成] 成功回填 {filled} 条记录')
    print(f'数据已保存至: {DATA_FILE}')
    print(f'进度已保存至: {PROGRESS_FILE}')
    print('=' * 60)
