import os
import pandas as pd
from transformers import BartForConditionalGeneration, PreTrainedTokenizerFast
import nltk
from nltk.tokenize import sent_tokenize
from datetime import datetime, timedelta

# NLTK punkt tokenizer 다운로드
nltk.download('punkt')

# 모델 경로
model_path = "fine_tuned_model"

# 모델 및 토크나이저 로드
model = BartForConditionalGeneration.from_pretrained(model_path)
tokenizer = PreTrainedTokenizerFast.from_pretrained(model_path)

# 요약 함수 정의 (길이 초과 시 분할 요약)
def summarize_text_with_chunks(text, max_chunk_length=1024, summary_max_length=512, max_time=120):
    if not isinstance(text, str) or len(text.strip()) == 0:
        return None  # 요약할 내용이 없으면 Null 값 반환
    
    start_time = datetime.now()
    
    try:
        input_ids = tokenizer.encode(text, return_tensors="pt")
        if len(input_ids[0]) <= max_chunk_length:
            summary_ids = model.generate(
                input_ids, max_length=summary_max_length, num_beams=5, early_stopping=True
            )
            return tokenizer.decode(summary_ids[0], skip_special_tokens=True)

        sentences = sent_tokenize(text)
        current_chunk = ""
        chunk_summaries = []

        for sentence in sentences:
            # 시간 초과 체크
            if (datetime.now() - start_time).total_seconds() > max_time:
                return None  # 시간 초과로 Null 값 반환

            tentative_chunk = current_chunk + " " + sentence
            input_ids = tokenizer.encode(tentative_chunk, return_tensors="pt")
            
            if len(input_ids[0]) > max_chunk_length:
                summary_ids = model.generate(
                    tokenizer.encode(current_chunk, return_tensors="pt"),
                    max_length=summary_max_length,
                    num_beams=5,
                    early_stopping=True
                )
                chunk_summaries.append(tokenizer.decode(summary_ids[0], skip_special_tokens=True))
                current_chunk = sentence
            else:
                current_chunk = tentative_chunk

        if current_chunk.strip():
            summary_ids = model.generate(
                tokenizer.encode(current_chunk, return_tensors="pt"),
                max_length=summary_max_length,
                num_beams=5,
                early_stopping=True
            )
            chunk_summaries.append(tokenizer.decode(summary_ids[0], skip_special_tokens=True))

        combined_summary = " ".join(chunk_summaries)
        final_input_ids = tokenizer.encode(combined_summary, return_tensors="pt")
        final_summary_ids = model.generate(
            final_input_ids, max_length=summary_max_length, num_beams=5, early_stopping=True
        )
        return tokenizer.decode(final_summary_ids[0], skip_special_tokens=True)

    except Exception as e:
        return None  # 에러 발생 시 Null 값 반환

# 요약 작업 수행 함수
def summarize_and_save(input_csv_path):
    try:
        # 입력 파일 이름에서 `_` 앞의 텍스트 추출
        base_name = os.path.basename(input_csv_path)
        output_name = base_name.split('_')[0] + ".csv"
        static_dir = "static"  # static 폴더 경로
        os.makedirs(static_dir, exist_ok=True)  # static 폴더가 없으면 생성
        output_csv_path = os.path.join(static_dir, output_name)

        # 데이터 읽기
        print(f"입력 데이터를 로드 중입니다: {input_csv_path}")
        data = pd.read_csv(input_csv_path)

        # NaN 값을 빈 문자열로 대체
        data['content'] = data['content'].fillna("")

        total_articles = len(data)
        print(f"전체 {total_articles}개의 기사를 요약합니다.")

        # 요약 열 생성
        summaries = []
        for idx, content in enumerate(data['content']):
            print(f"기사 {idx + 1}/{total_articles} 요약 중...")
            summary = summarize_text_with_chunks(content)
            if summary is None:
                print(f"기사 {idx + 1} 요약 시간 초과 또는 오류로 건너뜀.")
            else:
                print(f"기사 {idx + 1}/{total_articles} 요약 완료.")
            summaries.append(summary)

        # 요약 결과를 데이터프레임에 추가
        data['Summary'] = summaries

        # Null 값(요약 실패) 행 삭제
        data = data.dropna(subset=['Summary'])

        # 결과를 CSV 파일로 저장
        print(f"\n요약된 데이터를 저장 중입니다: {output_csv_path}")
        data.to_csv(output_csv_path, index=False, encoding='utf-8-sig')

        print(f"요약된 데이터가 {output_csv_path} 파일로 저장되었습니다.")

        # 최신 기사의 요약 추출
        if not data.empty:
            data['date'] = pd.to_datetime(data['date'])
            latest_article = data.sort_values(by='date', ascending=False).iloc[0]
            latest_summary = latest_article['Summary']
        else:
            latest_summary = None

        return output_csv_path, latest_summary  # 요약 파일 경로와 최신 기사의 요약 반환

    except Exception as e:
        print(f"Error during summarization: {e}")
        return None, None
