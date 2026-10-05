import streamlit as st
import json
import os
import time
import random
import qrcode
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# ==========================================
# 1. 裏方の設定とデザイン（CSS強制注入）
# ==========================================
st.set_page_config(page_title="自作Kahoot", layout="centered")

# ★ここでKahoot風のCSSデザインを当てています！
def apply_kahoot_theme():
    st.markdown("""
    <style>
    /* 全体の背景をあの紫のグラデーションに！ */
    [data-testid="stAppViewContainer"] {
        background-color: #46178f !important;
        background-image: linear-gradient(180deg, #46178f 0%, #321066 100%) !important;
    }
    
    /* 基本の文字色を白、太字、中央揃えに */
    h1, h2, h3, h4, h5, h6, p, span, div {
        color: white ;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif ;
    }
    
    /* 入力カード内の文字だけは黒にする */
    [data-testid="stTextInput"] div, [data-testid="stTextInput"] p, [data-testid="stTextInput"] label {
        color: black !important;
        text-align: center !important;
        font-weight: bold !important;
    }

    /* PINや名前入力のエリアを「白いカード」風にする */
    [data-testid="stTextInput"] {
        background-color: white !important;
        padding: 20px 20px 0px 20px !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2) !important;
        margin-top: 20px !important;
    }

    [data-testid="stTextInput"] input {
        text-align: center !important;
        font-size: 24px !important;
        font-weight: bold !important;
        color: black !important;
        background-color: #ffffff !important;
        border: 2px solid #e0e0e0 !important;
        border-radius: 4px !important;
        margin-bottom: 20px !important;
    }

    /* 「参加」「OK、次へ！」などの黒いボタン */
    .stButton > button {
        background-color: #333333 !important;
        color: white !important;
        font-size: 20px !important;
        font-weight: bold !important;
        height: 60px !important;
        border: none !important;
        border-bottom: 4px solid #000000 !important; /* ボタンの立体感 */
        border-radius: 4px !important;
        width: 100% !important;
        transition: 0.1s !important;
    }
    /* ボタンを押したときのへこむ動き */
    .stButton > button:active {
        transform: translateY(4px) !important;
        border-bottom: 0px !important;
    }
    
    /* テキストを中央寄せ */
    .stMarkdown {
        text-align: center !important;
    }

    /* 邪魔な上のヘッダーを透明に */
    [data-testid="stHeader"] {
        background-color: transparent !important;
    }
    
    /* サイドバー（ホスト用）の背景は白にして見やすく */
    [data-testid="stSidebar"] {
        background-color: #f0f0f0 !important;
    }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] div, [data-testid="stSidebar"] span {
        color: black !important;
    }
    </style>
    """, unsafe_allow_html=True)

# CSSを適用
apply_kahoot_theme()

QUIZ_FILE = "quizzes.json"
STATE_FILE = "game_state.json"

def load_json(filepath, default_data):
    if not os.path.exists(filepath):
        return default_data
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return default_data

def save_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ==========================================
# 2. 画面切り替えのルーティング
# ==========================================
url_pin = st.query_params.get("pin", "")

if "current_page" not in st.session_state:
    if url_pin:
        st.session_state.entered_pin = url_pin
        st.session_state.current_page = "player"
    else:
        st.session_state.current_page = "home" 

if st.session_state.current_page in ["lobby", "maker", "host"]:
    with st.sidebar:
        st.title("⚙️ ホストメニュー")
        if st.button("🎪 ロビー（開催画面）", use_container_width=True):
            st.session_state.current_page = "lobby"
            st.rerun()
        if st.button("📝 問題セット作成", use_container_width=True):
            st.session_state.current_page = "maker"
            st.rerun()
        if st.button("🚪 トップに戻る", use_container_width=True):
            st.session_state.current_page = "home"
            st.rerun()

# ==========================================
# 3. 各画面ごとの処理
# ==========================================

# ------------------------------------------
# ⓪ 初期画面（PINコード入力）
# ------------------------------------------
if st.session_state.current_page == "home":
    st.markdown("<h1 style='font-size: 50px; font-weight: 900; margin-bottom: 40px;'>Kahoot!</h1>", unsafe_allow_html=True)
    
    pin_input = st.text_input("PIN", placeholder="PINを入力")
    if st.button("参加", type="primary", use_container_width=True):
        if pin_input:
            st.session_state.entered_pin = pin_input
            st.session_state.current_page = "player"
            st.rerun()
            
    st.divider()
    with st.expander("ホスト（主催者）用メニューはこちら"):
        if st.button("🎪 開催・問題作成を開く"):
            st.session_state.current_page = "lobby"
            st.rerun()

# ------------------------------------------
# ① プレイヤー画面（スマホ用）
# ------------------------------------------
elif st.session_state.current_page == "player":
    st.markdown("<h1 style='font-size: 40px; font-weight: 900; margin-bottom: 20px;'>Kahoot!</h1>", unsafe_allow_html=True)
    state = load_json(STATE_FILE, {})
    
    current_pin = state.get("pin", "")
    entered_pin = st.session_state.get("entered_pin", "")
    
    if not current_pin or current_pin != entered_pin:
        st.error("PINコードが間違っています。")
        if st.button("戻る"):
            st.session_state.current_page = "home"
            st.rerun()
    else:
        if "nickname" not in st.session_state:
            nickname = st.text_input("ニックネーム", placeholder="ニックネームを入力")
            if st.button("OK、次へ！", type="primary"):
                if nickname:
                    if "players" not in state:
                        state["players"] = {}
                    state["players"][nickname] = {"score": 0}
                    save_json(STATE_FILE, state)
                    st.session_state.nickname = nickname
                    st.rerun()
            st.markdown("<p style='font-size:12px; margin-top:20px;'>本名を使用しないでください</p>", unsafe_allow_html=True)
        else:
            st_autorefresh(interval=1000, key="player_refresh")
            state = load_json(STATE_FILE, {})
            status = state.get("status", "lobby")
            nickname = st.session_state.nickname

            if status == "lobby":
                st.markdown("<h2 style='font-size:60px;'>🌞</h2>", unsafe_allow_html=True)
                st.markdown(f"<h2>{nickname}</h2>", unsafe_allow_html=True)
                st.markdown("<p style='font-size:20px;'>参加しました！画面にニックネームが表示されていますか？</p>", unsafe_allow_html=True)

            elif status == "question":
                st.markdown("<h2 style='font-size:40px;'>準備はいい？</h2>", unsafe_allow_html=True)
                st.markdown("<p>読み込み中です...</p>", unsafe_allow_html=True)
                
                # 選択肢をスクショのように文字付きで表示
                q_index = state.get("current_q_index", 0)
                quizzes = load_json(QUIZ_FILE, {})
                quiz_title = state.get("quiz_title")
                current_q = quizzes.get(quiz_title, [])[q_index]
                
                col1, col2 = st.columns(2)
                # スクショのように色と選択肢の文字を表示
                choices = [
                    f"🟥 {current_q['opts'][0]}", 
                    f"🟦 {current_q['opts'][1]}", 
                    f"🟨 {current_q['opts'][2]}", 
                    f"🟩 {current_q['opts'][3]}"
                ]
                
                answered = state.get("current_answers", {}).get(nickname)
                if answered:
                    st.markdown("<h2>回答を送信しました！</h2>", unsafe_allow_html=True)
                else:
                    for i, choice in enumerate(choices):
                        target_col = col1 if i % 2 == 0 else col2
                        if target_col.button(choice, use_container_width=True, key=f"btn_{i}"):
                            time_taken = time.time() - state.get("start_time", time.time())
                            if "current_answers" not in state:
                                state["current_answers"] = {}
                            state["current_answers"][nickname] = {"choice": i, "time": time_taken}
                            save_json(STATE_FILE, state)
                            st.rerun()
                
                st.markdown(f"<div style='margin-top: 30px; text-align:left;'>🌞 {nickname}</div>", unsafe_allow_html=True)

            elif status == "answer":
                st.markdown("<h1 style='font-size:50px;'>正解</h1>", unsafe_allow_html=True)
                st.markdown("<h2 style='font-size:80px;'>🙌</h2>", unsafe_allow_html=True)
                
                # 自分の獲得ポイントを計算して表示
                my_ans = state.get("current_answers", {}).get(nickname, {})
                correct_idx = state.get("correct_idx", -1)
                
                if my_ans.get("choice") == correct_idx:
                    st.markdown("<h2 style='background-color:#333; padding:10px; border-radius:5px;'>+ 獲得ポイント</h2>", unsafe_allow_html=True)
                    st.markdown("<p>あなたは表彰台に乗っています！</p>", unsafe_allow_html=True)
                else:
                    st.markdown("<h1 style='font-size:50px; color:#e21b3c !important;'>不正解...</h1>", unsafe_allow_html=True)
                    st.markdown("<p>次は頑張ろう！</p>", unsafe_allow_html=True)
                
            elif status == "leaderboard":
                st.markdown("<h1 style='font-size:40px;'>発表の時間です...</h1>", unsafe_allow_html=True)
                st.snow()

# ------------------------------------------
# ② 問題作成画面
# ------------------------------------------
elif st.session_state.current_page == "maker":
    st.markdown("<h2>📝 問題セット作成</h2>", unsafe_allow_html=True)
    quizzes = load_json(QUIZ_FILE, {})

    if "draft_questions" not in st.session_state:
        st.session_state.draft_questions = [{"q": "", "opts": ["", "", "", ""], "ans": 0, "time": 20}]

    quiz_title = st.text_input("タイトル", "新しいクイズ大会")
    
    for i, q in enumerate(st.session_state.draft_questions):
        st.markdown(f"<h3>第 {i + 1} 問</h3>", unsafe_allow_html=True)
        q["q"] = st.text_input("問題文", value=q["q"], key=f"q_{i}")
        
        col1, col2 = st.columns(2)
        q["opts"][0] = col1.text_input("選択肢1 (🟥)", value=q["opts"][0], key=f"opt0_{i}")
        q["opts"][1] = col2.text_input("選択肢2 (🟦)", value=q["opts"][1], key=f"opt1_{i}")
        q["opts"][2] = col1.text_input("選択肢3 (🟨)", value=q["opts"][2], key=f"opt2_{i}")
        q["opts"][3] = col2.text_input("選択肢4 (🟩)", value=q["opts"][3], key=f"opt3_{i}")
        
        q["ans"] = st.radio("正解", [0, 1, 2, 3], format_func=lambda x: f"選択肢{x+1}", horizontal=True, key=f"ans_{i}", index=q["ans"])
        q["time"] = st.number_input("制限時間（秒）", min_value=5, value=q["time"], key=f"time_{i}")
        st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("＋ 問題追加"):
            st.session_state.draft_questions.append({"q": "", "opts": ["", "", "", ""], "ans": 0, "time": 20})
            st.rerun()
    with col_b:
        if st.button("💾 保存する", type="primary"):
            quizzes[quiz_title] = st.session_state.draft_questions
            save_json(QUIZ_FILE, quizzes)
            st.success("保存しました！")
            st.session_state.draft_questions = [{"q": "", "opts": ["", "", "", ""], "ans": 0, "time": 20}]

# ------------------------------------------
# ③ ロビー画面（ホスト待機）
# ------------------------------------------
elif st.session_state.current_page == "lobby":
    st.markdown("<h1>Kahoot! ロビー</h1>", unsafe_allow_html=True)
    quizzes = load_json(QUIZ_FILE, {})
    
    if not quizzes:
        st.error("「問題セット作成」からクイズを作ってください。")
        st.stop()

    quiz_title = st.selectbox("遊ぶクイズを選ぶ", list(quizzes.keys()))

    if st.button("ルームを作成", type="primary"):
        pin = str(random.randint(100, 999)) + " " + str(random.randint(100, 999)) # 本家風に空白を入れる
        
        # ★ ここはあなたの公開URLに書き換えてください！ ★
        base_url = "https://あなたのアプリのURL.streamlit.app" 
        join_url = f"{base_url}/?pin={pin}"
        
        qr = qrcode.make(join_url)
        qr.save("join_qr.png")
        
        state = {
            "pin": pin, "quiz_title": quiz_title, "status": "lobby",
            "current_q_index": 0, "players": {}, "current_answers": {}
        }
        save_json(STATE_FILE, state)
        st.session_state.room_created = True

    if st.session_state.get("room_created"):
        state = load_json(STATE_FILE, {})
        
        st.markdown(f"<h2 style='font-size:50px; background:white; color:black !important; padding:10px; border-radius:10px;'>ゲームのPIN: <br> {state.get('pin')}</h2>", unsafe_allow_html=True)
        st.image("join_qr.png", width=200)
        
        st.markdown(f"<h3>参加者を待っています... ({len(state.get('players', {}))}人)</h3>", unsafe_allow_html=True)
        st_autorefresh(interval=2000, key="lobby_refresh")
        
        # 参加者の名前を横並びで表示
        players = list(state.get("players", {}).keys())
        st.markdown("<p style='font-size:24px; font-weight:bold;'>" + " ".join(players) + "</p>", unsafe_allow_html=True)

        if st.button("🚀 開始", type="primary", use_container_width=True):
            state["status"] = "question"
            save_json(STATE_FILE, state)
            st.session_state.current_page = "host"
            st.rerun()

# ------------------------------------------
# ④ クイズ開催画面（ホスト進行）
# ------------------------------------------
elif st.session_state.current_page == "host":
    st_autorefresh(interval=1000, key="host_refresh")
    state = load_json(STATE_FILE, {})
    quizzes = load_json(QUIZ_FILE, {})
    
    status = state.get("status")
    quiz_title = state.get("quiz_title")
    q_index = state.get("current_q_index", 0)
    quiz_data = quizzes.get(quiz_title, [])

    current_q = quiz_data[q_index]

    if status == "question":
        st.markdown(f"<h1>{current_q['q']}</h1>", unsafe_allow_html=True)
        
        if "start_time" not in state:
            state["start_time"] = time.time()
            save_json(STATE_FILE, state)
        
        elapsed = time.time() - state["start_time"]
        remaining = max(0, current_q['time'] - int(elapsed))
        
        st.markdown(f"<h1 style='font-size:80px; background-color:#864cbf; border-radius:50%; width:120px; height:120px; line-height:120px; margin:0 auto;'>{remaining}</h1>", unsafe_allow_html=True)
        
        answers_count = len(state.get("current_answers", {}))
        players_count = len(state.get("players", {}))
        st.markdown(f"<h3 style='text-align:right;'>回答数: {answers_count}</h3>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        col1.error(f"🟥 {current_q['opts'][0]}")
        col2.info(f"🟦 {current_q['opts'][1]}")
        col1.warning(f"🟨 {current_q['opts'][2]}")
        col2.success(f"🟩 {current_q['opts'][3]}")

        if remaining == 0 or (answers_count == players_count and players_count > 0):
            if st.button("次へ（正解発表）", type="primary"):
                state["status"] = "answer"
                state["correct_idx"] = current_q['ans']
                save_json(STATE_FILE, state)
                st.rerun()

    elif status == "answer":
        st.markdown("<h1>正解発表！</h1>", unsafe_allow_html=True)
        correct_idx = current_q['ans']
        
        answers = state.get("current_answers", {})
        counts = [0, 0, 0, 0]
        for p, data in answers.items():
            counts[data["choice"]] += 1
            
        df = pd.DataFrame({"選択肢": current_q['opts'], "投票数": counts})
        st.bar_chart(df.set_index("選択肢"))
        
        if st.button("次へ（ランキング）", type="primary"):
            players = state["players"]
            for p, data in answers.items():
                if data["choice"] == correct_idx:
                    time_ratio = data["time"] / current_q['time']
                    points = int(1000 * (1 - (time_ratio / 2)))
                    players[p]["score"] += max(500, points)
            
            state["players"] = players
            state["status"] = "leaderboard"
            save_json(STATE_FILE, state)
            st.rerun()

    elif status == "leaderboard":
        st.markdown("<h1>🏆 表彰台</h1>", unsafe_allow_html=True)
        players = state.get("players", {})
        sorted_players = sorted(players.items(), key=lambda x: x[1]['score'], reverse=True)
        
        for rank, (p, data) in enumerate(sorted_players[:5]):
            st.markdown(f"<h2>{rank + 1}位: {p} - {data['score']} pt</h2>", unsafe_allow_html=True)
            
        if q_index + 1 < len(quiz_data):
            if st.button("次の問題へ", type="primary"):
                state["current_q_index"] += 1
                state["status"] = "question"
                state.pop("start_time", None)
                state["current_answers"] = {}
                save_json(STATE_FILE, state)
                st.rerun()
        else:
            st.markdown("<h1>🎉 全問終了！</h1>", unsafe_allow_html=True)
            if st.button("ロビーに戻る"):
                st.session_state.current_page = "lobby"
                st.rerun()
