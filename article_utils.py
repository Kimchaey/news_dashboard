import pandas as pd


# 최신 기사 링크 반환 함수
def get_latest_article_link(final_file):
    try:
        df = pd.read_csv(final_file, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(final_file, encoding="cp949")
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    latest_article = df.sort_values(by="date", ascending=False).iloc[0]
    latest_link = latest_article['link']
    return latest_link

