from pathlib import Path
import zipfile
import random

import pandas as pd
import streamlit as st
from PIL import Image

# =========================================================
# 경로 설정
# =========================================================
BASE_DIR = Path(__file__).resolve().parent
CSV_DIR = BASE_DIR / "out_csv"
IMG_DIR = BASE_DIR / "out_img"
ZIP_PATH = BASE_DIR / "out_img.zip"

# =========================================================
# 이미지 zip 자동 해제 (최초 1회)
# =========================================================
def ensure_images_ready():
    if not IMG_DIR.exists() and ZIP_PATH.exists():
        IMG_DIR.mkdir(exist_ok=True)
        with zipfile.ZipFile(ZIP_PATH, "r") as z:
            z.extractall(IMG_DIR)

ensure_images_ready()

# =========================================================
# Streamlit 기본 설정
# =========================================================
st.set_page_config(page_title="전기기사 CBT", layout="wide")
st.title("전기기사 CBT")

# =========================================================
# CSV 로드
# =========================================================
csv_files = sorted(CSV_DIR.glob("*.csv"))
if not csv_files:
    st.error("out_csv 폴더에 CSV 파일이 없습니다.")
    st.stop()

selected_csv = st.sidebar.selectbox(
    "회차 / 파일 선택",
    [f.name for f in csv_files]
)
df = pd.read_csv(CSV_DIR / selected_csv, encoding="utf-8-sig")

required_cols = {"번호", "문제", "보기1", "보기2", "보기3", "보기4", "정답", "타입", "이미지"}
missing = required_cols - set(df.columns)
if missing:
    st.error(f"CSV 컬럼 누락: {missing}")
    st.stop()

df["번호"] = df["번호"].astype(int)
df = df.sort_values("번호").reset_index(drop=True)

# =========================================================
# 모드 선택
# =========================================================
mode = st.sidebar.radio("모드", ["연습(바로 채점)", "시험(랜덤 80문항)"])
show_answer = st.sidebar.checkbox("정답 표시", value=mode.startswith("연습"))

# =========================================================
# 세션 상태 (시험모드용)
# =========================================================
if "exam_qnums" not in st.session_state:
    st.session_state.exam_qnums = []
if "exam_answers" not in st.session_state:
    st.session_state.exam_answers = {}
if "exam_done" not in st.session_state:
    st.session_state.exam_done = False

# =========================================================
# 문제 렌더 함수
# =========================================================
def render_question(row):
    qnum = int(row["번호"])
    st.subheader(f"{selected_csv} / {qnum}번")

    qtype = str(row["타입"]).lower().strip()
    img_val = "" if pd.isna(row["이미지"]) else str(row["이미지"])

    # 이미지형 문제
    if qtype == "image" and img_val:
        img_name = Path(img_val).name
        img_path = IMG_DIR / img_name
        if img_path.exists():
            st.image(Image.open(img_path), use_container_width=True)
        else:
            st.warning("이미지 문제이지만 out_img에 이미지가 없습니다.")
            if isinstance(row["문제"], str) and row["문제"].strip():
                st.write(row["문제"])
    else:
        st.write(row["문제"])
        for i in range(1, 5):
            txt = row.get(f"보기{i}", "")
            txt = "" if pd.isna(txt) else str(txt)
            st.write(f"**{i})** {txt if txt.strip() else '(빈 보기)'}")

    try:
        correct = int(row["정답"])
    except Exception:
        correct = None

    return correct

# =========================================================
# 연습 모드
# =========================================================
if mode.startswith("연습"):
    qnums = df["번호"].tolist()
    qnum = st.sidebar.slider(
        "문제 번호",
        min_value=min(qnums),
        max_value=max(qnums),
        value=min(qnums),
        step=1
    )

    row = df.loc[df["번호"] == qnum].iloc[0]
    correct = render_question(row)

    pick = st.radio(
        "답을 선택하세요",
        [1, 2, 3, 4],
        horizontal=True,
        key=f"practice_{qnum}"
    )

    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("채점"):
            if correct is None:
                st.info("정답 정보가 없습니다.")
            elif pick == correct:
                st.success("정답!")
            else:
                st.error(f"오답! 정답은 {correct}번")

    with col2:
        if show_answer and correct is not None:
            st.caption(f"정답: {correct}번")

# =========================================================
# 시험 모드
# =========================================================
else:
    st.sidebar.caption("시험모드는 새로고침 시 초기화될 수 있습니다.")

    if st.sidebar.button("시험 시작 (랜덤 80문항)"):
        all_qnums = df["번호"].tolist()
        st.session_state.exam_qnums = (
            all_qnums if len(all_qnums) <= 80 else random.sample(all_qnums, 80)
        )
        st.session_state.exam_answers = {}
        st.session_state.exam_done = False

    if not st.session_state.exam_qnums:
        st.info("좌측에서 시험 시작 버튼을 눌러주세요.")
        st.stop()

    idx = st.sidebar.slider(
        "진행 문제",
        1,
        len(st.session_state.exam_qnums),
        1,
        1
    )

    qnum = st.session_state.exam_qnums[idx - 1]
    row = df.loc[df["번호"] == qnum].iloc[0]
    correct = render_question(row)

    default_pick = st.session_state.exam_answers.get(qnum, 1)
    pick = st.radio(
        "답을 선택하세요",
        [1, 2, 3, 4],
        index=default_pick - 1,
        horizontal=True,
        key=f"exam_{qnum}"
    )
    st.session_state.exam_answers[qnum] = pick

    if st.button("시험 종료 & 채점"):
        st.session_state.exam_done = True

    if st.session_state.exam_done:
        total = len(st.session_state.exam_qnums)
        wrong = []

        for q in st.session_state.exam_qnums:
            r = df.loc[df["번호"] == q].iloc[0]
            try:
                ans = int(r["정답"])
            except Exception:
                continue
            if st.session_state.exam_answers.get(q) != ans:
                wrong.append((q, st.session_state.exam_answers.get(q), ans))

        score = total - len(wrong)
        st.success(f"결과: {score} / {total}")

        if wrong:
            st.write("오답 목록 (문제번호 / 선택 / 정답)")
            st.dataframe(
                pd.DataFrame(wrong, columns=["번호", "선택", "정답"]),
                use_container_width=True
            )
