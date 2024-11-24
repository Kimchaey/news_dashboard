import pandas as pd
from sklearn.cluster import KMeans
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import re
import json

def generate_timeline(file_path, num_clusters=20, min_cluster_size=4, similarity_threshold=0.5):
    # 1. 파일 이름에서 키워드 추출
    file_name = file_path.split("/")[-1]
    keywords = re.sub(r"\.csv$", "", file_name)

    # 2. 데이터 로드
    df = pd.read_csv(file_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(by='date').reset_index(drop=True)

    # 3. Sentence-BERT 로드 및 키워드 임베딩 생성
    model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    reference_embedding = model.encode(keywords)

    # 4. 요약문 임베딩
    summaries = df['Summary'].dropna().tolist()
    sentence_embeddings = model.encode(summaries)
    df['embedding'] = list(sentence_embeddings)

    # 5. K-Means 클러스터링
    kmeans = KMeans(n_clusters=num_clusters, random_state=42)
    kmeans.fit(sentence_embeddings)
    df['Cluster'] = kmeans.labels_

    # 6. 클러스터 대표 사건 추출
    cluster_representatives = []
    for cluster_num in range(num_clusters):
        cluster_df = df[df['Cluster'] == cluster_num]
        if len(cluster_df) == 0:
            continue

        cluster_embeddings = np.vstack(cluster_df['embedding'].to_numpy())
        cluster_center = kmeans.cluster_centers_[cluster_num]
        distances = np.linalg.norm(cluster_embeddings - cluster_center, axis=1)
        closest_idx = distances.argmin()

        representative_event = {
            "cluster": cluster_num,
            "date": cluster_df.iloc[closest_idx]['date'],
            "Summary": cluster_df.iloc[closest_idx]['Summary'],
            "link": cluster_df.iloc[closest_idx]['link'],  # 링크 필드 추가
            "size": len(cluster_df),
            "embedding": cluster_df.iloc[closest_idx]['embedding'],
        }
        cluster_representatives.append(representative_event)

    # 7. 클러스터 중심과 키워드 유사도 계산
    filtered_representatives = []
    while similarity_threshold >= 0.1:
        filtered_representatives = []
        for event in cluster_representatives:
            # 유사도 계산
            similarity_to_reference = cosine_similarity(
                [event['embedding']], [reference_embedding]
            )[0][0]

            # 유사도 및 클러스터 크기 조건 적용
            if similarity_to_reference >= similarity_threshold and event['size'] >= min_cluster_size:
                filtered_representatives.append(event)

        if len(filtered_representatives) >= 7:  # 최소 7개 클러스터가 남으면 종료
            break

        similarity_threshold -= 0.1

    # 8. 상위 7개 클러스터 선택 (클러스터 크기 기준)
    filtered_representatives = sorted(filtered_representatives, key=lambda x: x['size'], reverse=True)[:7]

    # 9. 시간 순으로 정렬하여 타임라인 구성
    timeline = sorted(filtered_representatives, key=lambda x: x['date'])

    # 10. 결과 JSON 생성
    timeline_json = [
        {
            "date": event['date'].strftime('%Y-%m-%d'),
            "Summary": event['Summary'],
            "link": event['link'],
        }
        for event in timeline
    ]

    return json.dumps(timeline_json, ensure_ascii=False, indent=4)
