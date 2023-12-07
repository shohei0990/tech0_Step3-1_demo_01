import os
from dotenv import load_dotenv
import re
import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import set_with_dataframe
from geopy.geocoders import Nominatim

# 環境変数の読み込み
load_dotenv()

# 環境変数から認証情報を取得
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
PRIVATE_KEY_PATH = os.getenv("PRIVATE_KEY_PATH")

# 物件検索URL
BASE_URL = "*********"

# Google スプレッドシートへの認証を行い、gspreadクライアントオブジェクトを返す関数。
def authenticate_spreadsheet():
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    credentials = Credentials.from_service_account_file(
        PRIVATE_KEY_PATH,
        scopes=scopes
    )
    return gspread.authorize(credentials)

# スプレッドシートにDataFrameを書き込む関数
def write_to_spreadsheet(client, sheet_key, sheet_name, dataframe):
    """
    client (gspread.Client): gspreadのクライアントオブジェクト
    sheet_key (str): スプレッドシートのキー
    sheet_name (str): 書き込み対象のシート名
    dataframe (pandas.DataFrame): 書き込むデータを含むDataFrame
    """
    spreadsheet = client.open_by_key(sheet_key)
    worksheet = spreadsheet.worksheet(sheet_name)
    set_with_dataframe(worksheet, dataframe)

# 指定されたURLから不動産データをスクレイピングする関数。
def scrape_real_estate_data(base_url, max_page):
    """
    base_url (str): スクレイピングの基本となるURL
    max_page (int): スクレイピングする最大ページ数
    """
    all_data  = []
    
    for page in range(1, max_page + 1):
        url = base_url.format(page)
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'lxml')
        items = soup.findAll("div", {"class": "cassetteitem"})

        print("page", page, "items", len(items))

        for item in items:
            base_data = {}
            base_data["名称"]     = item.find("div", {"class": "cassetteitem_content-title"}).get_text(strip=True) if item.find("div", {"class": "cassetteitem_content-title"}) else None
            base_data["カテゴリ"] = item.find("div", {"class": "cassetteitem_content-label"}).span.get_text(strip=True) if item.find("div", {"class": "cassetteitem_content-label"}) else None
            base_data["アドレス"] = item.find("li", {"class": "cassetteitem_detail-col1"}).get_text(strip=True) if item.find("li", {"class": "cassetteitem_detail-col1"}) else None
            
            # 駅のアクセス情報をまとめて取得
            base_data["アクセス"] = ", ".join([station.get_text(strip=True) for station in item.findAll("div", {"class": "cassetteitem_detail-text"})])

            construction_info = item.find("li", {"class": "cassetteitem_detail-col3"}).find_all("div") if item.find("li", {"class": "cassetteitem_detail-col3"}) else None
            base_data["築年数"] = construction_info[0].get_text(strip=True) if construction_info and len(construction_info) > 0 else None
            base_data["構造"] = construction_info[1].get_text(strip=True) if construction_info and len(construction_info) > 1 else None

            tbodys = item.find("table", {"class": "cassetteitem_other"}).findAll("tbody")

            

            for tbody in tbodys:
                data = base_data.copy()
                # 階数情報の正確な取得
                floor_info = tbody.find_all("td")[2].get_text(strip=True) if len(tbody.find_all("td")) > 2 else None
                data["階数"]   = floor_info
                data["家賃"]   = tbody.select_one(".cassetteitem_price--rent").get_text(strip=True) if tbody.select_one(".cassetteitem_price--rent") else None
                data["管理費"] = tbody.select_one(".cassetteitem_price--administration").get_text(strip=True) if tbody.select_one(".cassetteitem_price--administration") else None
                data["敷金"]   = tbody.select_one(".cassetteitem_price--deposit").get_text(strip=True) if tbody.select_one(".cassetteitem_price--deposit") else None
                data["礼金"]   = tbody.select_one(".cassetteitem_price--gratuity").get_text(strip=True) if tbody.select_one(".cassetteitem_price--gratuity") else None
                data["間取り"] = tbody.select_one(".cassetteitem_madori").get_text(strip=True) if tbody.select_one(".cassetteitem_madori") else None
                data["面積"]   = tbody.select_one(".cassetteitem_menseki").get_text(strip=True) if tbody.select_one(".cassetteitem_menseki") else None

                # 物件画像・間取り画像・詳細URLの取得を最後に行う
                property_image_element = item.find(class_="cassetteitem_object-item")
                data["物件画像URL"] = property_image_element.img["rel"] if property_image_element and property_image_element.img else None

                floor_plan_image_element = item.find(class_="casssetteitem_other-thumbnail")
                data["間取画像URL"] = floor_plan_image_element.img["rel"] if floor_plan_image_element and floor_plan_image_element.img else None

                property_link_element = item.select_one("a[href*='/chintai/jnc_']")
                data["物件詳細URL"] = "****" +property_link_element['href'] if property_link_element else None

                # ここで各物件のデータを取得し、all_dataに追加
                all_data.append(data)    

    return all_data

# 築年数の加工
def process_construction_year(x):
    return 0 if x == '新築' else int(re.split('[築年]', x)[1])

# 構造：階建情報の取得
def get_most_floor(x):
    if '階建' not in x:
        return np.nan
    elif 'B' not in x:
        floor_list = list(map(int, re.findall(r'(\d+)階建', str(x))))
        return min(floor_list)
    else:
        return np.nan

# 階数の取得
def get_floor(x):
    if '階' not in x:
        return np.nan
    elif 'B' not in x:
        floor_list = list(map(int, re.findall(r'(\d+)階', str(x))))
        return min(floor_list)
    else:
        floor_list = list(map(int, re.findall(r'(\d+)階', str(x))))
        return -1 * min(floor_list)

# 費用の変換
def change_fee(x, unit):
    if unit not in x:
        return np.nan
    else:
        return float(x.split(unit)[0])

# 面積の変換
def process_area(x):
    return float(x[:-2])

# 住所の分割
def split_address(x, start, end):
    return x[x.find(start)+1:x.find(end)+1]

# アクセス情報の分割
def split_access(row):
    accesses = row['アクセス'].split(', ')
    results = {}

    for i, access in enumerate(accesses, start=1):
        if i > 3:
            break  # 最大3つのアクセス情報のみを考慮

        parts = access.split('/')
        if len(parts) == 2:
            line_station, walk = parts
            # ' 歩'で分割できるか確認
            if ' 歩' in walk:
                station, walk_min = walk.split(' 歩')
                # 歩数の分の数値だけを抽出
                walk_min = int(re.search(r'\d+', walk_min).group())
            else:
                station = None
                walk_min = None
        else:
            line_station = access
            station = walk_min = None

        results[f'アクセス①{i}線路名'] = line_station
        results[f'アクセス①{i}駅名'] = station
        results[f'アクセス①{i}徒歩(分)'] = walk_min

    return pd.Series(results)


# データ加工のメイン関数
def process_real_estate_data(dataframe):
    """
    不動産データを加工する関数。
    Args:
    dataframe (pandas.DataFrame): 加工する不動産データが含まれるDataFrame
    Returns:
    pandas.DataFrame: 加工後のDataFrame
    """
    dataframe['築年数'] = dataframe['築年数'].apply(process_construction_year)
    dataframe['構造'] = dataframe['構造'].apply(get_most_floor)
    dataframe['階数'] = dataframe['階数'].apply(get_floor)
    dataframe['家賃'] = dataframe['家賃'].apply(lambda x: change_fee(x, '万円'))
    dataframe['敷金'] = dataframe['敷金'].apply(lambda x: change_fee(x, '万円'))
    dataframe['礼金'] = dataframe['礼金'].apply(lambda x: change_fee(x, '万円'))
    dataframe['管理費'] = dataframe['管理費'].apply(lambda x: change_fee(x, '円'))
    dataframe['面積'] = dataframe['面積'].apply(process_area)
    dataframe['区'] = dataframe['アドレス'].apply(lambda x: split_address(x, "都", "区"))
    dataframe['市町'] = dataframe['アドレス'].apply(lambda x: split_address(x, "区", ""))
    dataframe = dataframe.join(dataframe.apply(split_access, axis=1))
    return dataframe

# メイン処理部分
def main():
    # スプレッドシートの認証
    print("1.スプレッドシートアクセス認証")
    gc = authenticate_spreadsheet()

    # スクレイピング
    base_url = BASE_URL
    max_page = 6
    print("2.スクレイピング開始", " : ページ数", max_page)
    scraped_data = scrape_real_estate_data(base_url, max_page)
    print("2.スクレイピング完了")

    # データフレームに変換
    df = pd.DataFrame(scraped_data)

    # 重複データの削除
    df = df.drop_duplicates() 

    # スプレッドシートに書き込み
    tab_w0 = "tech0_90"
    print("3.不動産データの生データを書き込み", " : タブ名", tab_w0)
    write_to_spreadsheet(gc, SPREADSHEET_ID, tab_w0, df)

    # データ加工
    print("4.不動産データの加工開始")
    processed_df = process_real_estate_data(df)
    print("4.不動産データの加工完了")

    # スプレッドシートに書き込み
    tab_w1 = "tech0_91"
    print("5.不動産データの加工データを書き込み", " : タブ名", tab_w1)
    write_to_spreadsheet(gc, SPREADSHEET_ID, tab_w1, processed_df)

if __name__ == "__main__":
    main()