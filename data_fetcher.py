# -*- coding: utf-8 -*-
# 房天下二手房数据获取模块
# 功能：从 fang.com 抓取最新二手房源数据，与现有数据合并，版本化管理
#
# 使用方式：
#   python data_fetcher.py                    # 更新全部城市（增量）
#   python data_fetcher.py --city 合肥        # 只更新指定城市
#   python data_fetcher.py --max-pages 5      # 每个城市最多抓5页
#   python data_fetcher.py --full             # 全量抓取（覆盖模式）

import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import os
import re
import time
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path


# ======================== 配置 ========================

# 项目根目录
BASE_DIR = Path(__file__).parent

# 数据目录
DATA_DIR = BASE_DIR / 'data'

# 现有数据文件
EXISTING_DATA_FILE = DATA_DIR / 'house_sales.csv'

# 城市-房天下子域名 映射表（已知的城市拼音码）
# 子域名规则：通常是城市名的拼音首字母缩写
CITY_CODE_MAP = {
    '合肥': 'hf', '南京': 'nj', '杭州': 'hz', '苏州': 'su', '无锡': 'wx',
    '常州': 'cz', '扬州': 'yz', '南通': 'nt', '徐州': 'xz', '盐城': 'yc',
    '泰州': 'tz', '镇江': 'zj', '淮安': 'ha', '连云港': 'lyg', '宿迁': 'sq',
    '济南': 'jn', '青岛': 'qd', '烟台': 'yt', '威海': 'wh', '潍坊': 'wf',
    '淄博': 'zb', '临沂': 'ly', '济宁': 'jining', '泰安': 'ta', '聊城': 'lc',
    '德州': 'dz', '滨州': 'bz', '荷泽': 'heze', '东营': 'dy', '日照': 'rz',
    '枣庄': 'zz', '莱芜': 'lw',
    '郑州': 'zz', '洛阳': 'luoyang', '新乡': 'xinxiang', '南阳': 'ny',
    '许昌': 'xc', '开封': 'kaifeng', '焦作': 'jiaozuo', '平顶山': 'pds',
    '石家庄': 'sjz', '唐山': 'ts', '保定': 'bd', '邯郸': 'hd', '廊坊': 'lf',
    '秦皇岛': 'qhd', '沧州': 'cangzhou', '邢台': 'xt', '衡水': 'hs',
    '张家口': 'zjk', '承德': 'chengde',
    '广州': 'gz', '深圳': 'sz', '东莞': 'dg', '佛山': 'fs', '惠州': 'huizhou',
    '珠海': 'zh', '中山': 'zs', '汕头': 'st', '湛江': 'zhanjiang',
    '江门': 'jiangmen', '肇庆': 'zhaoqing', '清远': 'qy', '茂名': 'maoming',
    '武汉': 'wh', '宜昌': 'yichang', '襄阳': 'xiangyang', '荆州': 'jingzhou',
    '黄石': 'huangshi', '十堰': 'shiyan', '孝感': 'xiaogan', '鄂州': 'ezhou',
    '长沙': 'cs', '株洲': 'zhuzhou', '湘潭': 'xiangtan', '衡阳': 'hengyang',
    '岳阳': 'yueyang', '常德': 'changde', '郴州': 'chenzhou',
    '成都': 'cd', '绵阳': 'mianyang', '德阳': 'deyang', '宜宾': 'yibin',
    '南充': 'nanchong', '泸州': 'luzhou', '乐山': 'leshan', '达州': 'dazhou',
    '杭州': 'hz', '宁波': 'nb', '温州': 'wz', '嘉兴': 'jx', '绍兴': 'sx',
    '金华': 'jh', '台州': 'tz', '湖州': 'huzhou', '丽水': 'lishui', '衢州': 'quzhou',
    '福州': 'fz', '厦门': 'xm', '泉州': 'qz', '漳州': 'zhangzhou',
    '莆田': 'putian', '龙岩': 'longyan', '三明': 'sanming',
    '西安': 'xa', '咸阳': 'xianyang', '宝鸡': 'baoji', '榆林': 'yulin',
    '昆明': 'km', '曲靖': 'qujing', '玉溪': 'yuxi', '大理': 'dali',
    '南宁': 'nn', '桂林': 'gl', '柳州': 'liuzhou', '北海': 'bh',
    '贵阳': 'gy', '遵义': 'zunyi', '六盘水': 'lps',
    '南昌': 'nc', '九江': 'jiujiang', '赣州': 'ganzhou', '上饶': 'shangrao',
    '沈阳': 'sy', '大连': 'dl', '鞍山': 'anshan', '抚顺': 'fushun',
    '锦州': 'jinzhou', '营口': 'yingkou', '丹东': 'dandong',
    '长春': 'cc', '吉林': 'jl', '延边': 'yanbian',
    '哈尔滨': 'hrb', '大庆': 'dq', '齐齐哈尔': 'qqhe', '牡丹江': 'mdj',
    '太原': 'ty', '大同': 'datong', '临汾': 'linfen', '运城': 'yuncheng',
    '长治': 'changzhi', '晋中': 'jinzhong',
    '兰州': 'lz', '天水': 'tianshui', '庆阳': 'qingyang',
    '海口': 'haikou', '三亚': 'sanya', '万宁': 'wanning',
    '乌鲁木齐': 'wlmq', '昌吉': 'changji',
    '呼和浩特': 'hu', '包头': 'bt', '赤峰': 'chifeng',
    '银川': 'yinchuan', '吴忠': 'wuzhong',
    '西宁': 'xn', '海东': 'haidong',
    '拉萨': 'lasa',
    '北京': 'bj', '上海': 'sh', '天津': 'tj', '重庆': 'cq',
    # 县级市和部分数据量大的小城市
    '安丘': 'anqiu', '迁安': 'qianan', '新郑': 'xinzheng', '招远': 'zhaoyuan',
    '丰县': 'fengxian', '溧阳': 'liyang', '莱州': 'laizhou', '浏阳': 'liuyang',
    '简阳': 'jianyang', '清镇': 'qingzhen', '青州': 'qingzhou', '荥阳': 'xingyang',
    '章丘': 'zhangqiu', '睢宁': 'suining', '辛集': 'xinji', '新沂': 'xinyi',
    '莱阳': 'laiyang', '昌乐': 'changle', '巢湖': 'chaohu',
    '东方': 'dongfang', '文昌': 'wenchang', '新密': 'xinmi', '昌邑': 'changyi',
    '宝应': 'baoying', '仪征': 'yizheng', '西双版纳': 'xsbn', '太仓': 'taicang',
}

# HTTP 请求配置
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
}

# 请求间隔（秒），反爬虫礼貌等待
REQUEST_DELAY = 2.0

# 默认每个城市最大抓取页数（每页约60条）
DEFAULT_MAX_PAGES = 10


# ======================== 工具函数 ========================

def _load_existing_data():
    """加载现有数据，返回 DataFrame 和已有的 origin_url 集合"""
    if not EXISTING_DATA_FILE.exists():
        print(f'⚠️ 未找到现有数据文件: {EXISTING_DATA_FILE}')
        return None, set()

    df = pd.read_csv(EXISTING_DATA_FILE, encoding='utf-8-sig')
    existing_urls = set(df['origin_url'].dropna().unique())
    print(f'✅ 已加载现有数据: {len(df):,} 条记录, {len(existing_urls):,} 个唯一URL')
    return df, existing_urls


def _get_city_subdomain(city_name):
    """获取城市对应的房天下子域名"""
    if city_name in CITY_CODE_MAP:
        return CITY_CODE_MAP[city_name]
    # 尝试用拼音首字母
    return None


def _province_for_city(city_name, existing_df=None):
    """从现有数据中查找城市所属省份"""
    if existing_df is not None:
        match = existing_df[existing_df['city'] == city_name]
        if len(match) > 0:
            return match.iloc[0]['province']
    return '未知'


def _clean_text(text):
    """清理文本中的空白字符"""
    if not text:
        return ''
    return re.sub(r'\s+', ' ', str(text)).strip()


# ======================== 核心爬取逻辑 ========================

def fetch_city_listings(city_name, max_pages=DEFAULT_MAX_PAGES, existing_urls=None):
    """
    抓取指定城市的最新二手房源列表

    Args:
        city_name: 城市中文名（如'合肥'）
        max_pages: 最大抓取页数（每页约60条）
        existing_urls: 已有URL集合，用于跳过已存在的房源

    Returns:
        list[dict]: 新增房源数据列表
    """
    subdomain = _get_city_subdomain(city_name)
    if not subdomain:
        print(f'  ⚠️ 城市 "{city_name}" 未找到子域名映射，跳过')
        return []

    base_url = f'https://{subdomain}.esf.fang.com'
    if existing_urls is None:
        existing_urls = set()

    new_listings = []
    session = requests.Session()
    session.headers.update(HEADERS)

    # 第一步：获取首页，同时获取总页数
    print(f'  📡 正在获取 {city_name} ({subdomain}.esf.fang.com) 第1页...')
    try:
        r = session.get(base_url + '/', timeout=20)
        r.raise_for_status()
    except Exception as e:
        print(f'  ❌ 访问首页失败: {e}')
        return []

    soup = BeautifulSoup(r.text, 'html.parser')
    total_pages = _parse_total_pages(soup)
    pages_to_fetch = min(max_pages, total_pages)
    print(f'  📊 {city_name} 共 {total_pages} 页，计划抓取 {pages_to_fetch} 页')

    # 解析第一页
    page1_listings = _parse_listing_page(soup, city_name, base_url, existing_urls)
    new_listings.extend(page1_listings)
    print(f'  📄 第1页: 抓取 {len(page1_listings)} 条新房源')

    # 抓取后续页面
    for page_num in range(2, pages_to_fetch + 1):
        time.sleep(REQUEST_DELAY)

        page_url = f'{base_url}/house/i3{page_num}/'
        print(f'  📡 正在获取第{page_num}页...', end=' ')
        try:
            r = session.get(page_url, timeout=20)
            if r.status_code != 200:
                print(f'状态码 {r.status_code}, 跳过剩余页面')
                break
            soup = BeautifulSoup(r.text, 'html.parser')
            page_listings = _parse_listing_page(soup, city_name, base_url, existing_urls)
            new_listings.extend(page_listings)
            # 同时更新已有URL集合避免重复
            for item in page_listings:
                existing_urls.add(item['origin_url'])
            print(f'{len(page_listings)} 条新房源')
        except Exception as e:
            print(f'失败: {e}')
            break

    session.close()
    print(f'  ✅ {city_name} 完成: 共抓取 {len(new_listings)} 条新房源')
    return new_listings


def _parse_total_pages(soup):
    """从页面解析总页数"""
    # 查找分页区域的末页链接
    last_page_link = soup.find('a', href=re.compile(r'/house/i3\d+/'), string=re.compile(r'末页|尾页'))
    if last_page_link:
        href = last_page_link.get('href', '')
        match = re.search(r'i3(\d+)', href)
        if match:
            return int(match.group(1))

    # 备选：查找最大页码数字
    all_links = soup.find_all('a', href=re.compile(r'/house/i3\d+/'))
    max_page = 1
    for link in all_links:
        href = link.get('href', '')
        match = re.search(r'i3(\d+)', href)
        if match:
            max_page = max(max_page, int(match.group(1)))
        try:
            page_num = int(link.get_text(strip=True))
            max_page = max(max_page, page_num)
        except ValueError:
            pass

    # 查找"共X页"文本
    page_text = soup.find(string=re.compile(r'共\s*\d+\s*页'))
    if page_text:
        match = re.search(r'(\d+)', str(page_text))
        if match:
            max_page = max(max_page, int(match.group(1)))

    return max(1, max_page)


def _parse_listing_page(soup, city_name, base_url, existing_urls):
    """
    解析房源列表页，提取房源信息

    房天下列表页结构 (2025.07):
    每个房源是一个 <dl> 标签，内部 <dd> 标签包含各字段
    字段顺序大致为：
      [0] 标题/描述  [1] 户型  [4] 面积  [7] 楼层  [8] 总层数
      [11] 朝向  [14] 税费状态  [15] 小区名称  [16] 地址
    价格和单价在独立的 <span> 中
    """
    listings = []
    dls = soup.find_all('dl')

    for dl in dls:
        try:
            listing = _parse_single_listing(dl, city_name, base_url)
            if listing and listing['origin_url'] not in existing_urls:
                listings.append(listing)
        except Exception as e:
            continue

    return listings


def _parse_single_listing(dl, city_name, base_url):
    """
    解析单个房源卡片。

    基于房天下 dd[0] 的实际结构 (2025.07):
      part[0]  → 标题描述
      part[1]  → 户型 (如 "3室2厅")
      part[4]  → 面积 (如 "141.94㎡")
      part[7]  → 楼层级别 (如 "低层"/"中层"/"高层"/"顶层")
      part[8]  → 总层数 (如 "（共18层）")
      part[11] → 朝向 (如 "南北向")
      part[14] → 经纪人姓名
      part[15] → 小区名称  ← 核心字段
      part[16] → 地址      ← 核心字段
      part[17+]→ 标签 (如 "满两年", "3km公园" 等)
    price/unit 在 dd[1].price_right 中
    """
    # ---- 1. 标题与URL ----
    h4 = dl.find('h4')
    if not h4:
        return None
    a_tag = h4.find('a')
    if not a_tag:
        return None

    title = _clean_text(a_tag.get_text())
    href = a_tag.get('href', '')
    if href.startswith('//'):
        origin_url = f'https:{href}'
    elif href.startswith('/'):
        origin_url = base_url + href
    else:
        origin_url = href

    # ---- 2. 提取 dd[0] 信息字段 ----
    dds = dl.find_all('dd')
    if len(dds) < 2:
        return None

    # get_text('|', strip=True) 将嵌套元素的文本用 | 连接
    info_text = dds[0].get_text('|', strip=True)
    parts = [p.strip() for p in info_text.split('|')]

    # 安全检查：至少需要 17 个字段（到地址位置）
    if len(parts) < 17:
        return None

    # ---- 3. 直接按固定位置提取字段 ----
    rooms = parts[1] if re.match(r'\d+室\d+厅', parts[1]) else ''
    area = parts[4] if re.match(r'^\d+\.?\d*㎡$', parts[4]) else ''

    # 楼层：part[7]=级别，part[8]=总层数
    floor_level = parts[7] if parts[7] in ('低层', '中层', '高层', '顶层', '底层') else ''
    floor_total = parts[8] if re.match(r'（共\d+层）', parts[8]) else ''
    floor = f'{floor_level}{floor_total}' if floor_level else (floor_total or '')

    # 朝向: part[11]
    toward = parts[11] if parts[11] in ('南北向', '南向', '东南向', '东西向', '东向',
                                         '北向', '西南向', '西向', '东北向', '西北向') else ''

    # 小区名称: part[15]
    name = parts[15]

    # 地址: part[16]
    address = parts[16]

    # ---- 4. 提取价格和单价 (dd[1].price_right) ----
    price_text = dds[1].get_text(strip=True)
    price_match = re.search(r'(\d+\.?\d*)万', price_text)
    unit_match = re.search(r'(\d+\.?\d*)元/㎡', price_text)

    if not price_match:
        return None

    price_raw = price_match.group(1) + '万'
    unit_raw = unit_match.group(1) + '元/㎡' if unit_match else ''

    # ---- 5. 构建记录 ----
    listing = {
        'city': city_name,
        'province': '',
        'address': address,
        'area': area,
        'floor': floor,
        'name': name,
        'price': price_raw,
        'rooms': rooms,
        'toward': toward,
        'unit': unit_raw,
        'year': '',
        'house_type': '二手房',  # 数据来源为房天下二手房频道，统一标注
        'origin_url': origin_url,
    }

    return listing


def fetch_listing_detail(origin_url):
    """
    抓取房源详情页，获取建成年份、装修情况等补充信息。

    详情页中有两类年份信息：
    1. 小区级别的「建筑年代」：在 <span class=\"lab\">建筑年代</span> 的父级 div 中
    2. 房源标题中可能包含年份

    Args:
        origin_url: 房源详情页 URL

    Returns:
        dict: {'year': '2014年建', ...} 或 {}
    """
    time.sleep(REQUEST_DELAY * 0.3)  # 详情页请求间隔适当缩短
    try:
        r = requests.get(origin_url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return {}

        soup = BeautifulSoup(r.text, 'html.parser')
        detail = {}

        # ---- 方式1: 通过「建筑年代」标签获取 ----
        lab_span = soup.find('span', class_='lab', string=re.compile(r'建筑年代'))
        if lab_span and lab_span.parent:
            parent_text = lab_span.parent.get_text(strip=True)
            # "建筑年代2014年" → 提取年份
            year_match = re.search(r'建筑年代(\d{4})年', parent_text)
            if year_match:
                detail['year'] = year_match.group(1) + '年建'

        # ---- 方式2: 从页面文本中找最近的合理年份 ----
        if 'year' not in detail:
            text = soup.get_text()
            # 找所有合理建成年份
            years = re.findall(r'(?<!\d)(19[5-9]\d|20[0-2]\d)年(?!\d)', text)
            if years:
                # 取第一个出现的（通常是最相关的）
                detail['year'] = years[0] + '年建'

        # ---- 方式3: 尝试从 meta 标签获取 ----
        if 'year' not in detail:
            for meta in soup.find_all('meta'):
                content = meta.get('content', '')
                year_match = re.search(r'(19[5-9]\d|20[0-2]\d)年建', content)
                if year_match:
                    detail['year'] = year_match.group(0)
                    break

        return detail
    except Exception:
        return {}


def enrich_with_details(listings, max_detail_fetch=100):
    """
    为房源列表补充详情页信息（主要是建成年份）。

    由于详情页抓取耗时较长（每次约0.6秒），建议：
    - 对新抓取的房源，优先为缺少 year 的条目抓取
    - 使用 max_detail_fetch 限制单次最大抓取数

    Args:
        listings: 房源列表
        max_detail_fetch: 最多抓取多少个详情页（0=不抓取）

    Returns:
        int: 成功补充年份的房源数
    """
    if max_detail_fetch <= 0 or not listings:
        return 0

    # 优先为没有年份的房源抓取
    need_fetch = [item for item in listings if not item.get('year')]
    fetch_count = min(max_detail_fetch, len(need_fetch))

    if fetch_count == 0:
        return 0

    print(f'  🔍 正在为 {fetch_count} 套房源抓取详情页补充年份...')

    enriched = 0
    for i, item in enumerate(need_fetch[:fetch_count]):
        url = item.get('origin_url', '')
        if not url:
            continue

        detail = fetch_listing_detail(url)
        if detail.get('year'):
            item['year'] = detail['year']
            enriched += 1

        # 进度提示
        if (i + 1) % 20 == 0:
            print(f'    进度: {i+1}/{fetch_count}, 已获取年份: {enriched}')

    print(f'  ✅ 年份补充完成: {enriched}/{fetch_count} 成功')
    return enriched


# ======================== 数据合并与保存 ========================

def enrich_with_province(listings, existing_df):
    """用现有数据中的省份信息填充新数据"""
    if existing_df is None:
        return listings

    city_province_map = existing_df.groupby('city')['province'].first().to_dict()
    for item in listings:
        if not item['province'] and item['city'] in city_province_map:
            item['province'] = city_province_map[item['city']]

    return listings


def merge_and_save(new_listings, existing_df, output_path=None):
    """
    合并新旧数据并保存为版本化文件

    Args:
        new_listings: 新抓取的房源列表
        existing_df: 现有数据DataFrame
        output_path: 输出路径，默认自动生成带日期的文件名

    Returns:
        DataFrame: 合并后的数据
        str: 保存的文件路径
    """
    if not new_listings:
        print('⚠️ 无新数据，不执行合并')
        if existing_df is not None:
            return existing_df, str(EXISTING_DATA_FILE)
        return None, None

    new_df = pd.DataFrame(new_listings)

    # 合并
    if existing_df is not None and len(existing_df) > 0:
        # 为现有数据补充缺失的 house_type 列（旧数据没有此字段）
        if 'house_type' not in existing_df.columns:
            existing_df['house_type'] = '二手房'

        # 确保列对齐
        common_cols = [c for c in existing_df.columns if c in new_df.columns]
        aligned_new = new_df[common_cols]
        aligned_old = existing_df[common_cols]

        merged = pd.concat([aligned_old, aligned_new], ignore_index=True)
        # 按 origin_url 去重，保留最新的
        merged = merged.drop_duplicates(subset=['origin_url'], keep='last')
        print(f'📊 合并后总记录: {len(merged):,} (原有 {len(existing_df):,} + 新增 {len(new_df):,} - 去重)')
    else:
        merged = new_df
        print(f'📊 新建数据集: {len(merged):,} 条记录')

    # 生成版本化文件名
    if output_path is None:
        date_str = datetime.now().strftime('%Y%m%d')
        output_path = DATA_DIR / f'house_sales_{date_str}.csv'

    # 保存
    merged.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f'💾 数据已保存至: {output_path}')

    # 同时更新主数据文件（如果输出路径不是主文件）
    if str(output_path) != str(EXISTING_DATA_FILE):
        merged.to_csv(EXISTING_DATA_FILE, index=False, encoding='utf-8-sig')
        print(f'💾 主数据文件已更新: {EXISTING_DATA_FILE}')

    return merged, str(output_path)


# ======================== 数据更新摘要 ========================

def generate_update_summary(old_df, new_df):
    """生成数据更新摘要报告"""
    if old_df is None:
        old_count = 0
    else:
        old_count = len(old_df)

    new_count = len(new_df) if new_df is not None else old_count

    summary = {
        '更新时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        '原有记录': old_count,
        '更新后记录': new_count,
        '新增记录': new_count - old_count,
        '数据文件': str(EXISTING_DATA_FILE),
    }

    if new_df is not None:
        summary['覆盖城市数'] = new_df['city'].nunique() if 'city' in new_df.columns else 0
        summary['覆盖省份数'] = new_df['province'].nunique() if 'province' in new_df.columns else 0

    return summary


# ======================== 主入口 ========================

def update_data(cities=None, max_pages=DEFAULT_MAX_PAGES, full_refresh=False, fetch_details=0):
    """
    主函数：更新房源数据

    Args:
        cities: 要更新的城市列表，None=从现有数据中取Top城市
        max_pages: 每个城市最大抓取页数
        full_refresh: True=全量覆盖，False=增量更新
        fetch_details: 抓取详情页补充年份的数量（0=不抓取）

    Returns:
        dict: 更新摘要
    """
    print('=' * 60)
    print('🏠 房天下二手房数据获取器')
    print(f'⏰ 开始时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 60)

    # 加载现有数据
    existing_df, existing_urls = _load_existing_data()

    # 确定要更新的城市
    if cities is None:
        if existing_df is not None and not full_refresh:
            # 默认：取现有数据中挂牌量Top 20城市
            top_cities = existing_df['city'].value_counts().head(20).index.tolist()
            cities = [c for c in top_cities if c in CITY_CODE_MAP]
            print(f'🎯 自动选择 Top {len(cities)} 城市进行更新')
        else:
            cities = list(CITY_CODE_MAP.keys())[:20]

    # 如果是全量刷新，清空已有URL集合
    if full_refresh:
        existing_urls = set()
        print('🔄 全量刷新模式：将忽略已有数据')

    # 逐城市抓取
    all_new_listings = []
    for i, city in enumerate(cities):
        print(f'\n[{i+1}/{len(cities)}] 正在处理: {city}')
        try:
            city_listings = fetch_city_listings(city, max_pages=max_pages, existing_urls=existing_urls)
            all_new_listings.extend(city_listings)
            # 更新URL集合
            for item in city_listings:
                existing_urls.add(item['origin_url'])
        except Exception as e:
            print(f'  ❌ {city} 处理失败: {e}')
            continue

        # 城市间礼貌等待
        if i < len(cities) - 1:
            time.sleep(REQUEST_DELAY * 1.5)

    # 填充省份信息
    all_new_listings = enrich_with_province(all_new_listings, existing_df)

    # 抓取详情页补充建成年份（对新房源）
    if fetch_details > 0:
        print(f'\n📅 开始补充建成年份信息...')
        enriched = enrich_with_details(all_new_listings, max_detail_fetch=fetch_details)
        summary_extra = {'年份补充数': enriched}
    else:
        summary_extra = {}

    # 合并保存
    merged_df, saved_path = merge_and_save(all_new_listings, existing_df)

    # 生成摘要
    summary = generate_update_summary(existing_df, merged_df)
    print('\n' + '=' * 60)
    print('📊 更新摘要')
    print('=' * 60)
    for k, v in summary.items():
        print(f'  {k}: {v}')

    # 保存摘要到JSON
    summary_path = DATA_DIR / 'update_log.json'
    summary['新抓取记录'] = len(all_new_listings)
    summary['更新城市列表'] = cities[:30]

    existing_logs = []
    if summary_path.exists():
        try:
            with open(summary_path, 'r', encoding='utf-8') as f:
                existing_logs = json.load(f)
        except Exception:
            pass

    existing_logs.append(summary)
    # 只保留最近20条日志
    existing_logs = existing_logs[-20:]

    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(existing_logs, f, ensure_ascii=False, indent=2)

    return summary


# ======================== CLI ========================

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='房天下二手房数据获取器')
    parser.add_argument('--city', type=str, default=None, help='指定城市名（多个用逗号分隔）')
    parser.add_argument('--max-pages', type=int, default=DEFAULT_MAX_PAGES, help='每个城市最大抓取页数')
    parser.add_argument('--full', action='store_true', help='全量刷新（覆盖模式）')
    parser.add_argument('--top', type=int, default=10, help='自动选择Top N城市更新')
    parser.add_argument('--fetch-details', type=int, default=0, help='抓取详情页补充年份的房源数（0=不抓取, 建议50-200）')

    args = parser.parse_args()

    cities = None
    if args.city:
        cities = [c.strip() for c in args.city.split(',') if c.strip() in CITY_CODE_MAP]
        if not cities:
            print(f'❌ 未找到匹配的城市。已知城市: {list(CITY_CODE_MAP.keys())[:30]}...')
            exit(1)

    update_data(cities=cities, max_pages=args.max_pages, full_refresh=args.full, fetch_details=args.fetch_details)
