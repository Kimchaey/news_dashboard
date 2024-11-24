// 새로운 검색 바의 기능 구현
const searchForm = document.getElementById("searchForm");
searchForm.addEventListener("submit", function (event) {
    event.preventDefault(); // 기본 동작 방지
    const keyword = document.getElementById("searchInput").value;
    if (keyword) {
        document.getElementById("statusMessage").innerHTML = "모델이 실행 중입니다. 잠시만 기다려주세요...";
        fetch("/custom-keyword", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ keyword: keyword }),
        }).then(() => checkStatus());
    } else {
        alert("키워드를 입력하세요.");
    }
});

// 자동 키워드 버튼 클릭 시 모델 실행
const startButton = document.getElementById("startButton");
startButton.addEventListener("click", function () {
    document.getElementById("statusMessage").innerHTML = "모델이 실행 중입니다. 잠시만 기다려주세요...";
    fetch("/start-crawling", {
        method: "POST",
    }).then(() => checkStatus());
});

// 상태 확인 및 대시보드 업데이트
function checkStatus() {
    fetch("/status")
        .then((response) => response.json())
        .then((data) => {
            const overlay = document.getElementById("loadingOverlay");
            if (data.loading) {
                overlay.classList.remove("hidden-overlay"); // 가리개 표시
                document.getElementById("statusMessage").innerHTML = "모델이 실행 중입니다. 잠시만 기다려주세요...";
                setTimeout(checkStatus, 1000); // 1초 후 재시도
            } else {
                overlay.classList.add("hidden-overlay"); // 가리개 숨김
                updateDashboard(data); // 대시보드 업데이트
                document.getElementById("statusMessage").innerHTML = "모델 실행이 완료되었습니다.";
            }
        })
        .catch((error) => {
            console.error("Error checking status:", error);
        });
}

// 대시보드 업데이트 함수
function updateDashboard(data) {
    const overlay = document.getElementById("loadingOverlay");
    overlay.classList.add("hidden-overlay"); // 모델 실행 완료 시 가리개 숨김
    // 동적 텍스트 업데이트
    const dynamicText = document.getElementById("dynamicText");
    const keyword = data.keyword || "키워드 없음";
    const increaseStartDate = data.increase_start_date || "정보 없음";

    if (data.user_action === "custom_keyword") {
        dynamicText.innerHTML = `
            관심 사건 키워드: <strong>${keyword}</strong><br>
            사건의 발생 시점: <strong>${increaseStartDate}</strong><br>
            아래에 사건의 발생 시점부터 사건의 타임라인을 생성했어요!
        `;
    } else if (data.user_action === "auto_keyword") {
        dynamicText.innerHTML = `
            오늘의 사건 키워드: <strong>${keyword}</strong><br>
            사건의 발생 시점: <strong>${increaseStartDate}</strong><br>
            아래에 사건의 발생 시점부터 사건의 타임라인을 생성했어요!
        `;
    }

    // 뉴스 임베드 업데이트
    if (data.latest_link) {
        document.querySelector(".news-frame-container").innerHTML = `
            <iframe src="${data.latest_link}" class="news-frame" title="Latest Article"></iframe>
        `;
    }

    // 뉴스 요약 업데이트
    if (data.latest_summary) {
        document.querySelector(".news-summary").innerHTML = `
            <div class="news-summary-header"><strong>위 기사를 요약해봤어요!</strong></div>
            <p>${data.latest_summary}</p>
        `;
    }

    // 시각화 이미지 업데이트
    if (data.combined_plot_exists) {
        document.querySelector(".content-top-left img").src = "/static/combined_plot.png";
        document.querySelector(".content-top-left img").classList.remove("hidden");
    }

    // 타임라인 업데이트
    if (data.timeline_json) {
        const timeline = document.querySelector(".timeline");
        timeline.innerHTML = ""; // 기존 타임라인 초기화

        JSON.parse(data.timeline_json).forEach((event) => {
            const timelineItem = document.createElement("div");
            timelineItem.className = "timeline-item";
            timelineItem.innerHTML = `
                <div class="timeline-date">${event.date}</div>
                <div class="timeline-summary">${event.Summary}</div>
            `;
            timeline.appendChild(timelineItem);
        });
    }

    // 대시보드 표시
    document.querySelector(".dashboard").classList.remove("hidden");
}

// 현재 날짜를 yyyy-MM-dd 형식으로 표시 (요일 포함)
function displayCurrentDate() {
    const currentDateElement = document.getElementById("currentDate");
    const today = new Date();
    const formattedDate = today.toLocaleDateString("ko-KR", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        weekday: "long", // 요일 추가
    });
    currentDateElement.textContent = formattedDate; // 날짜와 요일을 텍스트로 삽입
}

// 페이지 로드 시 날짜 표시
window.onload = displayCurrentDate;

// 검색 바 활성화 및 오버레이 제어
document.querySelector(".open-button").addEventListener("click", function () {
    document.querySelector(".search").classList.add("active");
    document.querySelector(".overlay").classList.remove("hidden");
    document.querySelector(".search input").focus();
});

document.querySelector(".overlay").addEventListener("click", function () {
    document.querySelector(".search").classList.remove("active");
    this.classList.add("hidden");
});
