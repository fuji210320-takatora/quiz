import streamlit as st
import json
import os
import time
import random
import qrcode
import pandas as pd
import io
import base64
from streamlit_autorefresh import st_autorefresh

# ==========================================
# 1. 裏方の設定とデザイン（CSS強制注入）
# ==========================================
st.set_page_config(page_title="自作Kahoot", layout="centered")

def apply_kahoot_theme():
    st.markdown("""
    <style>
    /* 全体の背景を紫のグラデーションに */
    [data-testid="stAppViewContainer"] {
        background-color: #46178f !important;
        background-image: linear-gradient(180deg, #46178f 0%, #321066 100%) !important;
    }
    
    h1, h2, h3, h4, h5, h6, p, span, div {
        color: white;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    
    /* 白い箱の中の文字を絶対に黒にするクラス */
    .force-black, .force-black p, .force-black span, .force-black div, .force-black h1, .force-black h2, .force-black h3 {
        color: black !important;
    }
    
    /* 入力カード内の文字 */
    [data-testid="stTextInput"] div, [data-testid="stTextInput"] p, [data-testid="stTextInput"] label {
        color: black !important;
        text-align: center !important;
        font-weight: bold !important;
    }

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

    /* ボタンの基本スタイル */
    .stButton > button {
        background-color: #333333 !important;
        color: white !important;
        font-size: 24px !important;
        font-weight: bold !important;
        height: 80px !important;
        border: none !important;
        border-bottom: 4px solid #000000 !important; 
        border-radius: 4px !important;
        width: 100% !important;
        transition: 0.1s !important;
    }
    .stButton > button:active {
        transform: translateY(4px) !important;
        border-bottom: 0px !important;
    }
    
    /* クイズ選択肢の色分け */
    [data-testid="column"]:nth-of-type(1) div[data-testid="stButton"]:nth-of-type(1) button { background-color: #e21b3c !important; border-bottom-color: #c01733 !important; }
    [data-testid="column"]:nth-of-type(1) div[data-testid="stButton"]:nth-of-type(2) button { background-color: #d89e00 !important; border-bottom-color: #b08200 !important; }
    [data-testid="column"]:nth-of-type(2) div[data-testid="stButton"]:nth-of-type(1) button { background-color: #1368ce !important; border-bottom-color: #1059b0 !important; }
    [data-testid="column"]:nth-of-type(2) div[data-testid="stButton"]:nth-of-type(2) button { background-color: #26890c !important; border-bottom-color: #20750a !important; }

    .stMarkdown { text-align: center !important; }
    [data-testid="stHeader"] { background-color: transparent !important; }
    
    [data-testid="stSidebar"] { background-color: #f0f0f0 !important; }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] div, [data-testid="stSidebar"] span { color: black !important; }
    </style>
    """, unsafe_allow_html=True)

apply_kahoot_theme()

QUIZ_FILE = "quizzes.json"
STATE_FILE = "game_state.json"

def load_json(filepath, default_data):
    if not os.path.exists(filepath): return default_data
    with open(filepath, "r", encoding="utf-8") as f:
        try: return json.load(f)
        except: return default_data

def save_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def submit_answer(nickname, choice_idx, state):
    time_taken = time.time() - state.get("start_time", time.time())
    if "current_answers" not in state:
        state["current_answers"] = {}
    state["current_answers"][nickname] = {"choice": choice_idx, "time": time_taken}
    save_json(STATE_FILE, state)
    st.rerun()

# ==========================================
# 2. 画面切り替えのルーティング
# ==========================================
room_id = st.query_params.get("room", "")

if "current_page" not in st.session_state:
    if room_id:
        st.session_state.room_id = room_id
        st.session_state.current_page = "player"
    else:
        st.session_state.current_page = "home" 

if st.session_state.current_page in ["lobby", "maker", "host"]:
    with st.sidebar:
        st.title("⚙ ホストメニュー")
        if st.button("🎪 ロビー（開催画面）", use_container_width=True):
            st.session_state.current_page = "lobby"
            st.rerun()
        if st.button("📝 問題セット作成", use_container_width=True):
            st.session_state.current_page = "maker"
            st.session_state.maker_mode = "menu" # 作成画面に戻る時はメニューへ
            st.rerun()
        if st.button("🚪 トップに戻る", use_container_width=True):
            st.session_state.current_page = "home"
            st.rerun()

# ==========================================
# 3. 各画面ごとの処理
# ==========================================

# ------------------------------------------
# ⓪ 初期画面
# ------------------------------------------
if st.session_state.current_page == "home":
    st.markdown("<h1 style='font-size: 50px; font-weight: 900; margin-bottom: 20px;'>Kahoot!</h1>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 18px;'>ホストが映しているQRコードをスマホで読み込んで参加してください！</p>", unsafe_allow_html=True)
    
    st.divider()
    with st.expander("ホスト（主催者）用メニューはこちら"):
        if st.button("🎪 開催・問題作成を開く"):
            st.session_state.current_page = "lobby"
            st.rerun()

# ------------------------------------------
# ① プレイヤー画面（スマホ用）
# ------------------------------------------
elif st.session_state.current_page == "player":
    state = load_json(STATE_FILE, {})
    current_room = state.get("room_id", "")
    entered_room = st.session_state.get("room_id", "")
    
    if not current_room or current_room != entered_room:
        st.error("現在開催されているゲームルームが見つからないか、終了しました。")
    else:
        if "nickname" not in st.session_state:
            st.markdown("<h1 style='font-size: 40px; font-weight: 900; margin-bottom: 20px;'>Kahoot!</h1>", unsafe_allow_html=True)
            nickname = st.text_input("ニックネーム", placeholder="ニックネームを入力")
            if st.button("OK、次へ！", type="primary"):
                if nickname:
                    if "players" not in state: state["players"] = {}
                    state["players"][nickname] = {"score": 0}
                    save_json(STATE_FILE, state)
                    st.session_state.nickname = nickname
                    st.rerun()
            st.markdown("<p style='font-size:12px; margin-top:20px;'>本名を使用しないでください</p>", unsafe_allow_html=True)
        else:
            st_autorefresh(interval=500, key="player_refresh")
            state = load_json(STATE_FILE, {})
            status = state.get("status", "lobby")
            nickname = st.session_state.nickname

            if status == "lobby":
                st.markdown("<h2 style='font-size:60px;'>🌞</h2>", unsafe_allow_html=True)
                st.markdown(f"<h2>{nickname}</h2>", unsafe_allow_html=True)
                st.markdown("<p style='font-size:20px;'>参加しました！画面にニックネームが表示されていますか？</p>", unsafe_allow_html=True)

            elif status == "question":
                q_index = state.get("current_q_index", 0)
                quizzes = load_json(QUIZ_FILE, {})
                quiz_title = state.get("quiz_title")
                current_q = quizzes.get(quiz_title, [])[q_index]
                
                elapsed = time.time() - state.get("start_time", time.time())
                remaining = max(0, current_q['time'] - int(elapsed))
                
                st.markdown(f"""
                <div class="force-black" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <div style="background-color: white; border-radius: 50%; width: 40px; height: 40px; line-height: 40px; text-align: center; font-weight: bold; font-size: 20px;">{q_index + 1}</div>
                    <div style="background-color: white; padding: 5px 20px; border-radius: 20px; font-weight: bold;">🔠 クイズ</div>
                    <div style="width: 40px;"></div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"<div class='force-black' style='background-color:white; padding:20px; border-radius:8px; text-align:center; font-size:24px; font-weight:bold; margin-bottom: 20px;'>{current_q['q']}</div>", unsafe_allow_html=True)
                
                answered = state.get("current_answers", {}).get(nickname)
                if answered:
                    st.markdown("<h2 style='margin-top: 50px;'>回答を送信しました！</h2>", unsafe_allow_html=True)
                else:
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(current_q['opts'][0], key="btn_0", use_container_width=True): submit_answer(nickname, 0, state)
                        if st.button(current_q['opts'][2], key="btn_2", use_container_width=True): submit_answer(nickname, 2, state)
                    with col2:
                        if st.button(current_q['opts'][1], key="btn_1", use_container_width=True): submit_answer(nickname, 1, state)
                        if st.button(current_q['opts'][3], key="btn_3", use_container_width=True): submit_answer(nickname, 3, state)

                score = state.get('players', {}).get(nickname, {}).get('score', 0)
                st.markdown(f"""
                <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-top: 40px;">
                    <div style="display: flex; align-items: center;">
                        <span style="font-size: 40px; margin-right: 10px;">🌞</span>
                        <div>
                            <div style="font-weight: bold; font-size: 18px; text-align:left;">{nickname}</div>
                            <div style="font-size: 14px; opacity: 0.8; text-align:left;">{score}</div>
                        </div>
                    </div>
                    <div style="font-size: 30px; font-weight: bold; line-height: 1;">{remaining}</div>
                </div>
                """, unsafe_allow_html=True)

            elif status == "answer":
                correct_idx = state.get("correct_idx", -1)
                my_ans = state.get("current_answers", {}).get(nickname, {})
                if my_ans.get("choice") == correct_idx:
                    st.markdown("<h1 style='font-size:50px;'>正解</h1>", unsafe_allow_html=True)
                    st.markdown("<h2 style='font-size:80px;'>🙌</h2>", unsafe_allow_html=True)
                    st.markdown("<p>あなたは表彰台に乗っています！</p>", unsafe_allow_html=True)
                else:
                    st.markdown("<h1 style='font-size:50px; color:#e21b3c !important;'>不正解...</h1>", unsafe_allow_html=True)
                    st.markdown("<p>次は頑張ろう！</p>", unsafe_allow_html=True)
                
            elif status == "leaderboard":
                st.markdown("<h1 style='font-size:40px;'>発表の時間です...</h1>", unsafe_allow_html=True)
                st.snow()

# ------------------------------------------
# ② 問題作成画面（メニュー・インポート・編集機能追加）
# ------------------------------------------
elif st.session_state.current_page == "maker":
    if "maker_mode" not in st.session_state:
        st.session_state.maker_mode = "menu"

    # --- 1. メニュー画面 ---
    if st.session_state.maker_mode == "menu":
        st.markdown("<h2>📝 問題セット作成メニュー</h2>", unsafe_allow_html=True)
        st.write("")
        
        if st.button("✨ 新しく作成", use_container_width=True):
            st.session_state.maker_mode = "new"
            st.session_state.draft_questions = [{"q": "", "opts": ["", "", "", ""], "ans": 0, "time": 20}]
            st.session_state.draft_title = "新しいクイズ大会"
            st.rerun()
            
        st.write("")
        if st.button("📄 txtファイルから作成", use_container_width=True):
            st.session_state.maker_mode = "import"
            st.rerun()
            
        st.write("")
        if st.button("✏️ 作った問題の編集", use_container_width=True):
            st.session_state.maker_mode = "edit"
            st.session_state.editing_target = None
            st.rerun()

    # --- 2. txtファイルから作成（インポート画面） ---
    elif st.session_state.maker_mode == "import":
        if st.button("🔙 メニューに戻る", use_container_width=True):
            st.session_state.maker_mode = "menu"
            st.rerun()
            
        st.markdown("<h2>📄 txtファイルから作成</h2>", unsafe_allow_html=True)
        st.markdown("""
        <div class="force-black" style="background: white; padding: 20px; border-radius: 8px; text-align: left; font-size: 14px; margin-bottom: 20px;">
            <b>【書き方のルール】</b><br>
            以下の形式で書かれたテキストファイル(.txt)をアップロードしてください。<br><br>
            <span style="color:#1368ce; font-weight:bold;">【タイトル】俺たちのクイズ大会</span><br><br>
            <span style="color:#e21b3c; font-weight:bold;">【問題】日本の首都は？</span><br>
            【1】大阪<br>
            【2】東京<br>
            【3】京都<br>
            【4】福岡<br>
            <span style="color:#26890c; font-weight:bold;">【正解】2</span><br>
            <span style="color:#d89e00; font-weight:bold;">【時間】20</span><br><br>
            <span style="color:#e21b3c; font-weight:bold;">【問題】次の問題の文...</span>
        </div>
        """, unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader("txtファイルを選択", type=["txt"])
        
        if uploaded_file is not None:
            text = uploaded_file.read().decode("utf-8")
            lines = text.split('\n')
            
            quiz_title = "インポートされたクイズ"
            questions = []
            current_q = None
            
            for line in lines:
                line = line.strip()
                if line.startswith("【タイトル】"):
                    quiz_title = line.replace("【タイトル】", "").strip()
                elif line.startswith("【問題】"):
                    if current_q: questions.append(current_q)
                    current_q = {"q": line.replace("【問題】", "").strip(), "opts": ["", "", "", ""], "ans": 0, "time": 20}
                elif line.startswith("【1】") and current_q: current_q["opts"][0] = line.replace("【1】", "").strip()
                elif line.startswith("【2】") and current_q: current_q["opts"][1] = line.replace("【2】", "").strip()
                elif line.startswith("【3】") and current_q: current_q["opts"][2] = line.replace("【3】", "").strip()
                elif line.startswith("【4】") and current_q: current_q["opts"][3] = line.replace("【4】", "").strip()
                elif line.startswith("【正解】") and current_q:
                    ans_str = line.replace("【正解】", "").strip()
                    current_q["ans"] = (int(ans_str) - 1) if ans_str.isdigit() and 1 <= int(ans_str) <= 4 else 0
                elif line.startswith("【時間】") and current_q:
                    time_str = line.replace("【時間】", "").strip()
                    current_q["time"] = int(time_str) if time_str.isdigit() else 20
            
            if current_q:
                questions.append(current_q)
                
            if len(questions) > 0:
                st.success(f"✅ {len(questions)}問のクイズを読み込みました！")
                st.write(f"タイトル: {quiz_title}")
                if st.button("💾 この内容で保存する", type="primary", use_container_width=True):
                    quizzes = load_json(QUIZ_FILE, {})
                    quizzes[quiz_title] = questions
                    save_json(QUIZ_FILE, quizzes)
                    st.success("保存が完了しました！")
            else:
                st.error("問題が見つかりませんでした。書き方のルールを確認してください。")

    # --- 3. 新しく作成 ＆ 編集画面 ---
    elif st.session_state.maker_mode in ["new", "edit"]:
        if st.button("🔙 メニューに戻る", use_container_width=True):
            st.session_state.maker_mode = "menu"
            st.rerun()

        quizzes = load_json(QUIZ_FILE, {})
        
        # 編集モードの場合、プルダウンでクイズを選択させる
        if st.session_state.maker_mode == "edit":
            st.markdown("<h2>✏️ 作った問題の編集</h2>", unsafe_allow_html=True)
            if not quizzes:
                st.warning("保存されたクイズがありません。")
                st.stop()
            else:
                edit_target = st.selectbox("編集するクイズを選択", ["-- 選択してください --"] + list(quizzes.keys()))
                if edit_target != "-- 選択してください --":
                    if st.session_state.get("editing_target") != edit_target:
                        st.session_state.draft_title = edit_target
                        st.session_state.draft_questions = quizzes[edit_target]
                        st.session_state.editing_target = edit_target
                        st.rerun()
                else:
                    st.stop()
        else:
            st.markdown("<h2>✨ 新しく作成</h2>", unsafe_allow_html=True)

        # ここからは「新規」も「編集」も同じUI
        quiz_title = st.text_input("タイトル", st.session_state.get("draft_title", "新しいクイズ大会"))
        
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
            if st.button("＋ 問題追加", use_container_width=True):
                st.session_state.draft_questions.append({"q": "", "opts": ["", "", "", ""], "ans": 0, "time": 20})
                st.rerun()
        with col_b:
            if st.button("💾 保存する", type="primary", use_container_width=True):
                quizzes[quiz_title] = st.session_state.draft_questions
                save_json(QUIZ_FILE, quizzes)
                st.success(f"「{quiz_title}」を保存しました！")

# ------------------------------------------
# ③ ロビー画面（ホスト待機）
# ------------------------------------------
elif st.session_state.current_page == "lobby":
    quizzes = load_json(QUIZ_FILE, {})
    if not quizzes:
        st.error("「問題セット作成」からクイズを作ってください。")
        st.stop()

    quiz_title = st.selectbox("遊ぶクイズを選ぶ", list(quizzes.keys()))

    if st.button("ルームを作成", type="primary"):
        room_id = str(random.randint(100000, 999999))
        
        base_url = "https://quizhistory.streamlit.app" 
        join_url = f"{base_url}/?room={room_id}"
        
        qr_obj = qrcode.QRCode(border=1)
        qr_obj.add_data(join_url)
        qr_obj.make(fit=True)
        img = qr_obj.make_image(fill_color="black", back_color="white")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        state = {
            "room_id": room_id, "quiz_title": quiz_title, "status": "lobby",
            "current_q_index": 0, "players": {}, "current_answers": {},
            "qr_base64": qr_base64
        }
        save_json(STATE_FILE, state)
        st.session_state.room_created = True

    if st.session_state.get("room_created"):
        state = load_json(STATE_FILE, {})
        qr_base64 = state.get("qr_base64", "")
        
        st.markdown("""
        <div class="force-black" style="background-color: white; border-radius: 12px; padding: 30px; text-align: center; margin-bottom: 40px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); max-width: 500px; margin-left: auto; margin-right: auto;">
            <div style="font-weight: bold; font-size: 26px; margin-bottom: 20px;">
                スマホでQRコードを読み込んで参加！
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown(f'<div style="text-align: center;"><img src="data:image/png;base64,{qr_base64}" width="280" style="display:block; margin: 0 auto;"></div>', unsafe_allow_html=True)
            
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<h1 style='font-size: 80px; font-weight: 900; text-align: center; margin-top: 20px; margin-bottom: 30px; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);'>Kahoot!</h1>", unsafe_allow_html=True)
        
        st.markdown("""
        <div style="text-align: center; margin-bottom: 30px;">
            <span style="background-color: rgba(0,0,0,0.4); padding: 10px 30px; font-size: 24px; font-weight: bold; border-radius: 5px;">
                参加者を待っています
            </span>
        </div>
        """, unsafe_allow_html=True)
        
        st_autorefresh(interval=500, key="lobby_refresh")
        
        players = list(state.get("players", {}).keys())
        st.markdown("<p style='font-size:28px; font-weight:bold; text-align: center;'>" + "  ".join(players) + "</p>", unsafe_allow_html=True)

        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("🚀 開始", type="primary", use_container_width=True):
            state["status"] = "question"
            save_json(STATE_FILE, state)
            st.session_state.current_page = "host"
            st.rerun()

# ------------------------------------------
# ④ クイズ開催画面（ホスト進行）
# ------------------------------------------
elif st.session_state.current_page == "host":
    st_autorefresh(interval=500, key="host_refresh")
    state = load_json(STATE_FILE, {})
    quizzes = load_json(QUIZ_FILE, {})
    
    status = state.get("status")
    quiz_title = state.get("quiz_title")
    q_index = state.get("current_q_index", 0)
    quiz_data = quizzes.get(quiz_title, [])
    current_q = quiz_data[q_index]

    if status == "question":
        st.markdown(f"<div class='force-black' style='background-color:white; padding:20px; border-radius:8px; text-align:center; font-size:40px; font-weight:bold; margin-bottom: 20px;'>{current_q['q']}</div>", unsafe_allow_html=True)
        
        if "start_time" not in state:
            state["start_time"] = time.time()
            save_json(STATE_FILE, state)
        
        elapsed = time.time() - state["start_time"]
        remaining = max(0, current_q['time'] - int(elapsed))
        
        st.markdown(f"<h1 style='font-size:80px; background-color:#864cbf; border-radius:50%; width:120px; height:120px; line-height:120px; text-align:center; margin:20px auto;'>{remaining}</h1>", unsafe_allow_html=True)
        
        answers_count = len(state.get("current_answers", {}))
        players_count = len(state.get("players", {}))
        st.markdown(f"<h3 style='text-align:right;'>回答数: {answers_count} / {players_count}</h3>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.button(current_q['opts'][0], key="host_btn0", use_container_width=True)
            st.button(current_q['opts'][2], key="host_btn2", use_container_width=True)
        with col2:
            st.button(current_q['opts'][1], key="host_btn1", use_container_width=True)
            st.button(current_q['opts'][3], key="host_btn3", use_container_width=True)

        if remaining <= 0 or (players_count > 0 and answers_count >= players_count):
            state["status"] = "answer"
            state["correct_idx"] = current_q['ans']
            save_json(STATE_FILE, state)
            st.rerun()

    elif status == "answer":
        st.markdown("<h1>正解発表！</h1>", unsafe_allow_html=True)
        correct_idx = current_q['ans']
        
        answers = state.get("current_answers", {})
        counts = [0, 0, 0, 0]
        for p, data in answers.items(): counts[data["choice"]] += 1
            
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
