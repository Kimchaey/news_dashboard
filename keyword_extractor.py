def extract_keywords_of_today():
    from datetime import datetime
    from collections import Counter, defaultdict
    from scipy.sparse import csr_matrix
    import math
    import numpy as np
    import pandas as pd
    from konlpy.tag import Komoran
    from textrank import KeywordSummarizer
    import urllib.request
    from bs4 import BeautifulSoup
    import chardet
    from tqdm import tqdm

    # 오늘 날짜
    today = datetime.today()
    year_str, month_str, day_str = str(today.year), str(today.month), str(today.day)
    today_ = year_str + month_str.zfill(2) + day_str.zfill(2)

    # 뉴스 크롤링
    def fetch_news_titles(today_, new_link):
        params = []
        for i in new_link:
            for page in tqdm(range(18), desc="Fetching URLs"):
                url2 = f'https://news.naver.com/main/list.naver?mode=LPOD&mid=sec&oid={i}&listType=title&date={today_}&page={page}'
                try:
                    url = urllib.request.Request(url2)
                    res = urllib.request.urlopen(url).read()
                    encoding = chardet.detect(res)['encoding']
                    decoded_res = res.decode(encoding)
                    soup = BeautifulSoup(decoded_res, "html.parser")

                    title_new_list, href_new_list, date_new_list = [], [], []
                    for link in soup.find_all(class_="nclicks(cnt_flashart)"):
                        if link.get("href"):
                            href_new_list.append(link.get("href"))
                            title_new_list.append(link.get_text())

                    for link in soup.find_all(class_="date is_new"):
                        date_new_list.append(link.get_text())
                    for link in soup.find_all(class_="date is_outdated"):
                        date_new_list.append(link.get_text())

                    for _ in range(len(date_new_list)):
                        a = True
                        date = date_new_list[_]
                        if "분" in date or date.startswith("1") or date.startswith("2"):
                            for date_title_href in params:
                                if title_new_list[_] == date_title_href["title"]:
                                    a = False
                                    break
                            if a:
                                params.append({"date": date_new_list[_], "title": title_new_list[_], "href": href_new_list[_]})
                except Exception as e:
                    print(f"Error fetching page {page}: {e}")
        return params

    # 텍스트 정제 및 키워드 추출
    def extract_keywords(params):
        df = pd.DataFrame(params)
        list_1st = df['title'].dropna().tolist()
        for j in range(len(list_1st)):
            if "[" in list_1st[j] and "]" in list_1st[j]:
                a = list_1st[j].find("[")
                b = list_1st[j].find("]")
                list_1st[j] = list_1st[j].replace(list_1st[j][a:b + 1], "")

        komoran = Komoran()
        def komoran_tokenize(sent):
            if not sent:
                return []
            combined_words = []
            words = sent.split()
            for word_real_sub in words:
                try:
                    word1 = komoran.pos(word_real_sub, join=True)
                    if word1 is None:
                        continue
                except Exception as e:
                    continue
                word_be_combined = ""
                for j in word1:
                    count_slash = j.count('/')
                    if count_slash > 1:
                        continue
                    else:
                        try:
                            word, pos = j.split('/')
                        except ValueError:
                            continue
                        if pos not in ["NNP", "NNG"]:
                            continue
                        else:
                            word_be_combined += word
                if word_be_combined:
                    combined_words.append(word_be_combined)
            return combined_words

        keyword_extractor = KeywordSummarizer(tokenize=komoran_tokenize, window=-1, verbose=False)
        keywords = keyword_extractor.summarize(list_1st, topk=30)
        return keywords, list_1st

    # 주요 키워드와 관련된 뉴스 추출
    def create_keyword_pair_and_today(keywords, list_1st):
        top_1_keyword = keywords[0][0]
        top_other_keywords = [kw[0] for kw in keywords[1:]]
        keyword_paired_news = []

        for keyword1 in top_other_keywords:
            temp_news = [title for title in list_1st if top_1_keyword in title and keyword1 in title]
            if len(keyword_paired_news) < len(temp_news):
                keyword_paired_news = temp_news
                keyword_pair = f"{top_1_keyword} {keyword1}"

        return keyword_pair, keyword_paired_news

    # 메인 로직
    new_link = ["032", "005", "020", "021", "081", "022", "023", "025", "028", "469"]
    params = fetch_news_titles(today_, new_link)
    keywords, list_1st = extract_keywords(params)
    keyword_pair, keyword_paired_news = create_keyword_pair_and_today(keywords, list_1st)

    # 오늘의 키워드
    keywords_of_today = keyword_pair
    for keyword in keywords:
        if keyword[0] not in keyword_pair:
            keywords_of_today += f" {keyword[0]}"
            break

    return keywords_of_today
