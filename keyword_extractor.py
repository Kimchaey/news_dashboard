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

    import csv
    import pandas as pd

    # 오늘 날짜
    today = datetime.today()
    year_str, month_str, day_str = str(today.year), str(today.month), str(today.day)
    today_ = year_str + month_str.zfill(2) + day_str.zfill(2)

    # 뉴스 크롤링
    def fetch_news_titles(today_, new_link):
        params = []
        for i in new_link:
            for page in tqdm(range(14), desc="Fetching URLs"):
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
                        if "분" not in date:
                            date_int=date[:-3]
                            date_int=int(date_int)
                        if "분"in date or date_int<=12:
                            for date_title_href in params:
                                if title_new_list[_] == date_title_href["title"]:
                                    a = False
                                    break
                            if a:
                                params.append({"date": date_new_list[_], "title": title_new_list[_], "href": href_new_list[_]})
                except Exception as e:
                    print(f"Error fetching page {page}: {e}")
            today_int=int(today_)
            today_int-=1
            today_=str(today_)
            for page in tqdm(range(4), desc="Fetching URLs"):
                
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
                        if "분" not in date:
                            date_int=date[:-3]
                            date_int=int(date_int)
                        if "분"in date or date_int<=12:
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
                if word_be_combined and len(word_be_combined)>1:# 한글자를 제거할 거면 이것도 사용하기
                    combined_words.append(word_be_combined)
            return combined_words

        keyword_extractor = KeywordSummarizer(tokenize=komoran_tokenize, window=-1, verbose=False)
        keywords = keyword_extractor.summarize(list_1st, topk=30)
        top_1_keyword = keywords[0][0]
        list_news_combined_1st=[]
        for i in list_1st:
            if top_1_keyword in i:
                list_news_combined_1st.append(i)
        return keywords, list_news_combined_1st,top_1_keyword#키워드들과 1st 뉴스 리스트를 가져온다.

    # 주요 키워드와 관련된 뉴스 추출
    def create_keyword_pair_and_today(keywords, list_1st,top_1_keyword):
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
                if word_be_combined: #and len(word_be_combined)>1:# 한글자를 제거할 거면 이것도 사용하기
                    combined_words.append(word_be_combined)
            return combined_words

        keyword_extractor = KeywordSummarizer(tokenize=komoran_tokenize, window=-1, verbose=False)
        keywords = keyword_extractor.summarize(list_1st, topk=30)
        #top_1_keyword = keywords[0][0]
        
        num=0
        best_num=0
        best_word=str()
        for i in keywords:
            num=0
            for j in list_1st:
                if i[0]!= top_1_keyword:
                    if i[0] in j:
                        num+=1
            if num>best_num:
                best_num=num
                best_word = i[0]
        top_2_keyword = best_word
        keyword_paired_news=[]
        for i in list_1st:
            if top_1_keyword in i and top_2_keyword in i:
                keyword_paired_news.append(i)
        keyword_pair =f"{top_1_keyword} {top_2_keyword}"

        
        df = pd.DataFrame([keyword_paired_news],columns=[f"title{i}"for i in range(len(keyword_paired_news))])
        
        
        return keyword_pair, keyword_paired_news

    def create_keyword_triple(keyword_pair,keyword_paired_news):
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
                if word_be_combined and len(word_be_combined)>1:# 한글자를 제거할 거면 이것도 사용하기
                    combined_words.append(word_be_combined)
            return combined_words

        keyword_extractor = KeywordSummarizer(tokenize=komoran_tokenize, window=-1, verbose=False)
        keywords = keyword_extractor.summarize(list_1st, topk=30)
        for i in keywords:
            if i[0] not in keyword_pair:
                keyword_pair+=f" {i[0]}"
                break
            else:
                continue

        
        return keyword_pair
    from urllib.parse import quote
    def find_news(keywords_of_today):
        a1,a2,a3= keywords_of_today.split(' ')
        encoded_a1 = quote(a1)
        encoded_a2 = quote(a2)
        encoded_a3 = quote(a3)
        #url2 = f'https://www.joongang.co.kr/search?keyword={keywords_of_today}'
        #https://www.joongang.co.kr/search?keyword=사도광산%20추도식%20정부
        url2 = f'https://www.joongang.co.kr/search?keyword={encoded_a1}%20{encoded_a2}%20{encoded_a3}'
        try:
            url = urllib.request.Request(url2)
            res = urllib.request.urlopen(url).read()
            encoding = chardet.detect(res)['encoding']
            decoded_res = res.decode(encoding)
            soup = BeautifulSoup(decoded_res, "html.parser")
            print("the volume of news articles")
            for link in soup.find_all(class_="btn btn_full"):
                # <span> 태그 안의 내용 추출
                span_content = link.find('span').text
                print(span_content)  # 결과: 13
                break
        except Exception as e:
            print(f"Error fetching page {e}")
        span_content_int=int(span_content)
        keyword = f"{a1} {a2} {a3}"
        print(keyword)
        if span_content_int >=120:
            #keyword = f"{a1} {a2} {a3}"
            #print(keyword)
            return keyword

        url2 = f'https://www.joongang.co.kr/search?keyword={encoded_a1}%20{encoded_a2}'
        #print(url2)
        try:
            url = urllib.request.Request(url2)
            #print(1)
            res = urllib.request.urlopen(url).read()
            #print(1)
            encoding = chardet.detect(res)['encoding']
            decoded_res = res.decode(encoding)
            soup = BeautifulSoup(decoded_res, "html.parser")
            print("the volume of news articles")
            for link in soup.find_all(class_="btn btn_full"):
                span_content = link.find('span').text
                print(span_content)  # 결과: 13
                break
        except Exception as e:
            print(f"Error fetching page {e}")
        span_content_int=int(span_content)
        keyword = f"{a1} {a2}"
        print(keyword)
        if span_content_int >=120:
            return keyword

        url2 = f'https://www.joongang.co.kr/search?keyword={encoded_a1}'
        #print(url2)
        try:
            url = urllib.request.Request(url2)
            res = urllib.request.urlopen(url).read()
            encoding = chardet.detect(res)['encoding']
            decoded_res = res.decode(encoding)
            soup = BeautifulSoup(decoded_res, "html.parser")
            print("the volume of news articles")
            for link in soup.find_all(class_="btn btn_full"):
                # <span> 태그 안의 내용 추출
                span_content = link.find('span').text
                print(span_content)  # 결과: 13
                break
        except Exception as e:
            print(f"Error fetching page {e}")
        span_content_int=int(span_content)
        keyword = f"{a1}"
        print(keyword)
        if span_content_int >=120:
            return keyword


    # 메인 로직
    new_link = ["032", "005", "020", "021", "081", "022", "023", "025", "028", "469"]
    params = fetch_news_titles(today_, new_link)
    #params = fetch_news_titles2(today_, new_link,params)
    keywords, list_1st,top_1_keyword = extract_keywords(params)
    keyword_pair, keyword_paired_news = create_keyword_pair_and_today(keywords, list_1st,top_1_keyword)
    keywords_of_today= create_keyword_triple(keyword_pair,keyword_paired_news)
    keywords_of_today= find_news(keywords_of_today)
    return keywords_of_today
