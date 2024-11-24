import matplotlib
matplotlib.use('Agg')

import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import time

# uploads 폴더가 없으면 생성
if not os.path.exists("static"):
    os.makedirs("static")

# 1. 1차 크롤링 함수 (날짜, 제목, 링크 수집)
def crawl_joongang_news(keyword, max_pages=209):
    base_url = f"https://www.joongang.co.kr/search/news?keyword={keyword}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36"
    }
    articles = []
    page = 1

    while page <= max_pages:
        print(f"Scraping page {page}: {base_url}")
        response = requests.get(base_url, headers=headers)
        if response.status_code != 200:
            print("Failed to retrieve page.")
            break

        soup = BeautifulSoup(response.text, 'html.parser')
        news_items = soup.select('ul.story_list > li')
        if not news_items:
            print("No more articles found.")
            break

        for item in news_items:
            title_tag = item.select_one('h2.headline a')
            if title_tag:
                title = title_tag.get_text(strip=True)
                link = title_tag['href']
                if not link.startswith("http"):
                    link = "https://www.joongang.co.kr" + link

                # 날짜 추출
                date_tag = item.select_one('p.date')
                if date_tag:
                    raw_date = date_tag.get_text(strip=True)
                    try:
                        date = datetime.strptime(raw_date, '%Y.%m.%d %H:%M').strftime('%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        date = "N/A"
                else:
                    date = "N/A"

                articles.append({"date": date, "title": title, "link": link})

        # 다음 페이지로 이동
        next_button = soup.select_one('a.page_link[aria-label="다음 페이지"]')
        if next_button and 'href' in next_button.attrs:
            next_link = next_button['href']
            if not next_link.startswith("http"):
                next_link = "https://www.joongang.co.kr" + next_link
            base_url = next_link
            page += 1
            time.sleep(1)
        else:
            print("No more pages to scrape.")
            break

    # 데이터 저장
    initial_file = f"static/{keyword}_joongang_articles.csv"
    df = pd.DataFrame(articles)
    df.to_csv(initial_file, index=False, encoding='utf-8-sig')
    print(f"Saved {len(articles)} articles to {initial_file}")
    return initial_file

# 2. 증가 시점 찾기 함수
def find_increase_start_point(file_name, window_size=4, gradient_threshold=1.0, acceleration_threshold=1.0):
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd

    # CSV 파일에서 데이터 로드
    df = pd.read_csv(file_name, encoding='utf-8-sig')

    # 날짜 컬럼을 datetime 형식으로 변환
    df['date'] = pd.to_datetime(df['date'], errors='coerce')

    # 날짜 데이터 중 유효한 값만 필터링
    valid_dates = df['date'].dropna()

    # 날짜별 기사 수 집계
    daily_counts = valid_dates.dt.date.value_counts().sort_index()

    # 날짜 집계 데이터를 다시 인덱스를 DatetimeIndex로 변환
    daily_counts.index = pd.to_datetime(daily_counts.index)

    # 최신 기사와 가장 오래된 기사 간의 기간 계산
    max_date = daily_counts.index.max()
    min_date = daily_counts.index.min()
    total_days = (max_date - min_date).days  # 전체 기간 (일 단위)
    interval_days = max(total_days // 30, 1)  # 최소 1일 이상의 간격을 보장
    interval = f"{interval_days}D"  # 동적으로 계산된 interval 설정

    print(f"Dynamic Interval: {interval}")

    # 리샘플링 (동적 interval 적용)
    resampled_counts = daily_counts.resample(interval).sum()  # 리샘플링하여 interval 데이터로 변환

    # 변화량 계산 (리샘플링된 데이터)
    difference = resampled_counts.diff()  # 변화량 계산

    # 감소(음수 변화량)만 필터링
    negative_difference = difference[difference < 0]  # 감소 변화량만 추출

    # IQR을 사용한 이상치 탐지
    Q1 = np.percentile(negative_difference.dropna(), 25)
    Q3 = np.percentile(negative_difference.dropna(), 75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR  # 하한선 (급격한 감소)

    # 급격히 감소하는 지점 탐지
    decrease_indices = np.where(negative_difference < lower_bound)[0]  # 감소 지점 탐지

    # 감소 지점 필터링
    filtered_counts = resampled_counts.copy()
    if decrease_indices.size > 0:
        for idx in decrease_indices:
            filtered_counts.iloc[:idx + 1] = np.nan  # 감소 지점 이전 데이터 제거

    # 이후 데이터로 이동 평균 계산
    filtered_counts = filtered_counts.dropna()
    rolling_mean = filtered_counts.rolling(window=window_size).mean()

    # 데이터 크기 조건 추가 (np.gradient 계산 전에 확인)
    if len(rolling_mean.dropna()) > 2:  # 최소 세 점 필요
        # 이동 평균의 기울기(gradient) 계산
        gradient = np.gradient(rolling_mean.dropna())
        
        # 기울기의 변화율(가속도) 계산
        acceleration = np.gradient(gradient)

        # 기울기와 가속도 모두 임계값을 초과하는 지점 탐지
        increase_indices = np.where((gradient > gradient_threshold) & (acceleration > acceleration_threshold))[0]
        increase_start_date = rolling_mean.dropna().index[increase_indices[0]] if increase_indices.size > 0 else None
    else:
        increase_start_date = None

    # increase_start_date를 datetime.date 형식으로 변환
    if increase_start_date:
        increase_start_date = increase_start_date.date()

    # 통합 시각화 생성
    fig, ax1 = plt.subplots(figsize=(12, 6))

    # 첫 번째 그래프: 리샘플링 데이터와 이동 평균
    ax1.bar(resampled_counts.index, resampled_counts.values, color='skyblue', alpha=0.6, label="Resampled Article Count")
    ax1.plot(filtered_counts.index, rolling_mean, label=f"{window_size}-Interval Moving Average", color='orange', linewidth=2)
    if increase_start_date:
        ax1.axvline(x=increase_start_date, color='red', linestyle='--', label="Increase Start Point")
    ax1.set_ylabel("Number of Articles")
    ax1.set_xlabel("Date")
    ax1.legend(loc="upper left")
    ax1.grid(visible=True, alpha=0.5)

    # 두 번째 그래프: 날짜 히스토그램 (보조축)
    ax2 = ax1.twinx()
    ax2.hist(valid_dates, bins=30, color='red', alpha=0.3, edgecolor='black', label="Date Distribution Histogram")
    ax2.set_ylabel("Frequency of Dates")
    ax2.legend(loc="upper right")

    # 그래프 제목 및 저장
    plt.title("Combined Visualization: Article Frequency and Date Distribution")
    plt.tight_layout()

    # 그래프를 static 폴더에 저장
    output_path = "static/combined_plot.png"
    plt.savefig(output_path)
    plt.close()

    print(f"Combined graph saved to {output_path}")

    if increase_start_date:
        print(f"The article publication frequency started to increase around {increase_start_date}.")
    else:
        print("No significant increase start point found.")

    return increase_start_date



# 3. 증가 시점 이후 본문 크롤링 함수
def crawl_articles_since(keyword, start_date, max_pages=209):
    base_url = f"https://www.joongang.co.kr/search/news?keyword={keyword}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36"
    }
    articles = []
    page = 1

    while page <= max_pages:
        print(f"Scraping page {page}: {base_url}")
        response = requests.get(base_url, headers=headers)
        if response.status_code != 200:
            print("Failed to retrieve page.")
            break

        soup = BeautifulSoup(response.text, 'html.parser')
        news_items = soup.select('ul.story_list > li')
        if not news_items:
            print("No more articles found.")
            break

        for item in news_items:
            title_tag = item.select_one('h2.headline a')
            if title_tag:
                title = title_tag.get_text(strip=True)
                link = title_tag['href']
                if not link.startswith("http"):
                    link = "https://www.joongang.co.kr" + link

                # 날짜 가져오기
                date_tag = item.select_one('p.date')
                if date_tag:
                    raw_date = date_tag.get_text(strip=True)
                    try:
                        article_date = datetime.strptime(raw_date, '%Y.%m.%d %H:%M')
                    except ValueError:
                        continue
                    if article_date.date() < start_date:
                        continue

                # 본문 가져오기
                news_response = requests.get(link, headers=headers)
                if news_response.status_code != 200:
                    continue
                news_soup = BeautifulSoup(news_response.text, 'html.parser')
                content = " ".join([p.get_text(strip=True) for p in news_soup.select('div#article_body p')])

                articles.append({
                    "date": article_date.strftime('%Y-%m-%d %H:%M:%S'),
                    "title": title,
                    "link": link,
                    "content": content
                })

        # 다음 페이지로 이동
        next_button = soup.select_one('a.page_link[aria-label="다음 페이지"]')
        if next_button and 'href' in next_button.attrs:
            next_link = next_button['href']
            if not next_link.startswith("http"):
                next_link = "https://www.joongang.co.kr" + next_link
            base_url = next_link
            page += 1
            time.sleep(1)
        else:
            print("No more pages to scrape.")
            break

    # 최종 데이터 저장
    final_file = f"static/{keyword}_joongang_articles_since_{start_date}.csv"
    final_df = pd.DataFrame(articles)
    final_df.to_csv(final_file, index=False, encoding='utf-8-sig')
    print(f"Final save: {len(articles)} articles saved to {final_file}")
    
    return final_file  # 생성된 파일 경로 반환
