import os
from pathlib import Path
import pandas as pd
import streamlit as st
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent
CSV_DIR = BASE_DIR / "out_csv"
IMG_DIR = BASE_DIR / "out_img"

st.set_page_config(page_title="전기기사 CBT", layout="wide")

st.title("전기기사 CBT (CSV + 이미지 하이브리드)")

# --- CSV 선택 ---
csv_files = sorted(CSV_DIR.glob("*.csv"))
if not csv_files:
    st.error("out_csv 폴더에 CSV가 없습니다.")
    st.stop()

file_names = [f.name for f in csv_files]
selected_name = st.sidebar.selectbox("회차/파일 선택", file_names)
csv_path = CSV_DIR / selected_name

df = pd.read_csv(csv_path, encoding="utf-8-sig")

# 방어: 컬럼 없으면 중단
required_cols = {"번호","문제","보기1","보기2","보기3","보기4","정답","타입","이미지"}
missing = required_cols - set(df.columns)
if missing:
    st.error(f"CSV 컬럼이 부족합니다: {missing}")
    st.stop()

# --- 모드/옵션 ---
mode = st.sidebar.radio("모드", ["연습(바로 채점)", "시험(마지막 채점)"])
show_answer = st.sidebar.checkbox("정답/해설 표시(연습모드용)", value=False)

qnums = df["번호"].astype(int).tolist()
qnum = st.sidebar.select_slider("문제 번호", options=qnums, value=qnums[0])

row = df.loc[df["번호"] == qnum].iloc[0]

# --- 문제 표시 ---
st.subheader(f"{selected_name} / {qnum}번")

if str(row["타입"]).lower() == "image" and isinstance(row["이미지"], str) and row["이미지"].strip():
    # CSV에 저장된 경로가 절대경로일 수도 있으니 파일명만 뽑아 로컬(out_img)에서 찾기
    img_name = Path(row["이미지"]).name
    img_path = IMG_DIR / img_name
    if img_path.exists():
        st.image(Image.open(img_path), use_container_width=True)
    else:
        st.warning(f"이미지 파일을 찾지 못했습니다: {img_path}")
        # 그래도 텍스트 있으면 보여주기
        if isinstance(row["문제"], str) and row["문제"].strip():
            st.write(row["문제"])
else:
    st.write(row["문제"])
    choices = [row["보기1"], row["보기2"], row["보기3"], row["보기4"]]
    labels = ["1", "2", "3", "4"]
    for lab, ch in zip(labels, choices):
        if isinstance(ch, str) and ch.strip():
            st.write(f"**{lab})** {ch}")
        else:
            st.write(f"**{lab})** (빈 보기)")

# --- 답 선택 ---
correct = int(row["정답"]) if str(row["정답"]).strip() else None
pick = st.radio("답을 선택하세요", [1,2,3,4], horizontal=True)

if mode.startswith("연습"):
    if st.button("채점"):
        if correct is None:
            st.info("정답 정보가 없습니다.")
        elif pick == correct:
            st.success("정답!")
        else:
            st.error(f"오답! 정답은 {correct}번")
    if show_answer and correct is not None:
        st.caption(f"정답: {correct}번")
else:
    st.info("시험 모드는 MVP에서는 저장/마지막 채점 기능을 추가해야 합니다. (원하면 붙여줄게요)")
