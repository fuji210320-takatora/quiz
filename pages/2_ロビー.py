import streamlit as st
import qrcode
import random
from streamlit_autorefresh import st_autorefresh
from utils import load_json, save_json, get_local_ip, QUIZ_FILE, STATE_FILE

st.title("🎪 ロビー画面")

quizzes = load_json(QUIZ_FILE, {})
if not quizzes:
    st.error("まずは「問題作成」でクイズを作ってください！")
    st.stop()

quiz_title = st.selectbox("遊ぶクイズを選ぶ", list(quizzes.keys()))

if st.button("ルームを作成（QR生成）"):
    pin = str(random.randint(1000, 9999))
    
    # URLの末尾にPINを仕込む（最強の工夫）
    local_ip = get_local_ip()
    join_url = f"http://{local_ip}:8501/?pin={pin}"
    
    # QR生成
    qr = qrcode.make(join_url)
    qr.save("join_qr.png")
    
    # 初期状態をセット
    state = {
        "pin": pin,
        "quiz_title": quiz_title,
        "status": "lobby",
        "current_q_index": 0,
        "players": {},
        "current_answers": {}
    }
    save_json(STATE_FILE, state)
    st.session_state.room_created = True

if st.session_state.get("room_created"):
    state = load_json(STATE_FILE, {})
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("スマホで読み込んで参加！")
        st.image("join_qr.png", width=300)
        st.write(f"PINコードで入る場合: **{state.get('pin')}**")
        
    with col2:
        st.subheader(f"参加者 ({len(state.get('players', {}))}人)")
        # 参加者をリアルタイム更新して表示
        st_autorefresh(interval=2000, key="lobby_refresh")
        for p in state.get("players", {}).keys():
            st.markdown(f"**🙋 {p}**")

    st.divider()
    if st.button("🚀 クイズをスタートする！", type="primary"):
        state["status"] = "question"
        save_json(STATE_FILE, state)
        st.switch_page("pages/3_クイズ開催.py")
