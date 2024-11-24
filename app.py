from flask import Flask, render_template, request, jsonify
from threading import Thread
from crawling_functions import crawl_joongang_news, find_increase_start_point, crawl_articles_since
from article_utils import get_latest_article_link
from summary import summarize_and_save
from timeline import generate_timeline
from keyword_extractor import extract_keywords_of_today
import os


app = Flask(__name__)

# 상태를 저장하는 전역 변수
status = {
    "loading": False,  # 모델 실행 중인지 여부
    "keyword": None,  # 사용자가 입력한 키워드 또는 자동 생성된 키워드
    "latest_link": None,  # 최신 뉴스 기사 링크
    "summary_file": None,  # 요약 파일 경로
    "timeline_json": None,  # 생성된 타임라인 JSON
    "latest_summary": None,  # 최신 뉴스 기사의 요약문
    "increase_start_date": None,  # 사건 발생 시점
    "combined_plot_exists": False,  # 그래프 파일 존재 여부
    "user_action": None,  # 사용자의 동작 (custom_keyword 또는 auto_keyword)
}

def run_full_pipeline(keyword=None):
    """
    키워드를 기반으로 크롤링, 요약, 타임라인 생성.
    """
    try:
        # 상태 초기화
        status.update({
            "loading": True,
            "keyword": keyword,
            "increase_start_date": None,
            "latest_link": None,
            "latest_summary": None,
            "summary_file": None,
            "timeline_json": None,
            "combined_plot_exists": False,
            "user_action": None,
        })

        # 키워드 처리
        if not keyword:
            keyword = extract_keywords_of_today()
            status["user_action"] = "auto_keyword"
        else:
            status["user_action"] = "custom_keyword"

        status["keyword"] = keyword

        # 1차 크롤링 및 발생 시점 탐지
        initial_file = crawl_joongang_news(keyword)
        increase_start_date = find_increase_start_point(initial_file)
        status["increase_start_date"] = str(increase_start_date)

        if increase_start_date:
            # 2차 크롤링
            final_file = crawl_articles_since(keyword, increase_start_date)

            # 최신 링크 저장
            latest_link = get_latest_article_link(final_file)
            status["latest_link"] = latest_link

            # 요약 수행
            summary_file, latest_summary = summarize_and_save(final_file)
            status.update({
                "summary_file": summary_file,
                "latest_summary": latest_summary,
            })

            # 그래프 상태 업데이트
            if os.path.exists("static/combined_plot.png"):
                status["combined_plot_exists"] = True

            # 타임라인 생성
            timeline_json = generate_timeline(summary_file)
            status["timeline_json"] = timeline_json  # 타임라인 JSON 저장
        else:
            print("No significant increase start point found.")
    except Exception as e:
        print(f"Error during pipeline execution: {e}")
    finally:
        # 모델 실행 완료 상태로 설정
        status["loading"] = False


@app.route("/")
def index():
    return render_template("index.html", status=status)

@app.route("/start-crawling", methods=["POST"])
def start_crawling():
    """
    버튼을 눌러 실행되는 크롤링, 요약, 타임라인 생성.
    """
    thread = Thread(target=run_full_pipeline)
    thread.start()
    return jsonify({"message": "Crawling, summarization, and timeline generation started"})

@app.route("/custom-keyword", methods=["POST"])
def custom_keyword():
    """
    사용자가 키워드를 입력한 경우 해당 키워드로 파이프라인 실행.
    """
    user_keyword = request.json.get("keyword")
    if user_keyword:
        thread = Thread(target=run_full_pipeline, args=(user_keyword,))
        thread.start()
        return jsonify({"message": f"Crawling started with keyword: {user_keyword}"})
    return jsonify({"error": "Keyword is required"}), 400

@app.route("/status", methods=["GET"])
def check_status():
    """
    현재 상태를 반환.
    """
    return jsonify({
        "loading": status.get("loading", False),
        "keyword": status.get("keyword"),
        "increase_start_date": status.get("increase_start_date"),
        "user_action": status.get("user_action"),
        "latest_link": status.get("latest_link"),
        "latest_summary": status.get("latest_summary"),
        "combined_plot_exists": status.get("combined_plot_exists", False),
        "timeline_json": status.get("timeline_json"),  # 타임라인 JSON 반환
    })

if __name__ == "__main__":
    # static 폴더 생성
    os.makedirs("static", exist_ok=True)
    app.run(debug=True)
