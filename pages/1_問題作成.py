import streamlit as st
from utils import load_json, save_json, QUIZ_FILE

st.title("📝 問題作成")

quizzes = load_json(QUIZ_FILE, {})

quiz_title = st.text_input("クイズのタイトル", "俺たちの身内クイズ大会")
question = st.text_input("問題文")
col1, col2 = st.columns(2)
ans0 = col1.text_input("選択肢1 (🟥)")
ans1 = col2.text_input("選択肢2 (🟦)")
ans2 = col1.text_input("選択肢3 (🟨)")
ans3 = col2.text_input("選択肢4 (🟩)")

correct_ans = st.radio("正解はどれ？", [0, 1, 2, 3], format_func=lambda x: f"選択肢{x+1}")
time_limit = st.number_input("制限時間（秒）", min_value=5, value=20)

if st.button("この問題を保存する"):
    if quiz_title not in quizzes:
        quizzes[quiz_title] = []
        
    quizzes[quiz_title].append({
        "q": question,
        "opts": [ans0, ans1, ans2, ans3],
        "ans": correct_ans,
        "time": time_limit
    })
    save_json(QUIZ_FILE, quizzes)
    st.success("保存しました！")

st.divider()
st.write("【保存済みのクイズ】")
st.json(quizzes)
