import streamlit as st
import json
import os
import time
import random
import qrcode
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# ==========================================
# 1. 裏方の設定と関数
# ==========================================
st.set_page_config(page_title="自作Kahoot", layout="centered")

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
# QRコードのURL（?pin=XXXX）から来た場合の処理
url_pin = st.query_params.get("pin", "")

if "current_page" not in st.session_state:
    if url_pin:
        st.session_state.entered_pin = url_pin
        st.session_state.current_page = "player"
    else:
        st.session_state.current_page = "home" # 初期画面をPIN入力に

# ホスト用のサイドバーメニュー（ホスト関連画面の時だけ表示）
if st.session_state.current_page in ["lobby", "maker", "host"]:
    with st.sidebar:
        st.title("⚙️ ホストメニュー")
        if st.button("🎪 ロビー（開催画面）", use_container_width=True):
            st.session_state.current_page = "lobby"
            st.rerun()
        if st.button("📝 問題セット作成", use_container_width=True):
            st.session_state.current_page = "maker"
            st.rerun()
        if st.button("🚪 トップ（PIN入力）に戻る", use_container_width=True):
            st.session_state.current_page = "home"
            st.rerun()

# ==========================================
# 3. 各画面ごとの処理
# ==========================================

# ------------------------------------------
# ⓪ 初期画面（PINコード入力）
# ------------------------------------------
if st.session_state.current_page == "home":
    st.title("⚡ 自作Kahootへようこそ！")
    st.write("ホストが画面に表示しているPINコードを入力してください。")
    
    pin_input = st.text_input("PINコード", placeholder="例: 1234")
    if st.button("参加する！", type="primary", use_container_width=True):
        if pin_input:
            st.session_state.entered_pin = pin_input
            st.session_state.current_page = "player"
            st.rerun()
            
    st.divider()
    with st.expander("ホスト（主催者）用メニューはこちら"):
        if st.button("🎪 開催・問題作成メニューを開く"):
            st.session_state.current_page = "lobby"
            st.rerun()

# ------------------------------------------
# ① プレイヤー画面（スマホ用）
# ------------------------------------------
elif st.session_state.current_page == "player":
    st.title("📱 プレイヤー画面")
    state = load_json(STATE_FILE, {})
    
    current_pin = state.get("pin", "")
    entered_pin = st.session_state.get("entered_pin", "")
    
    # PINコードの正誤チェック
    if not current_pin or current_pin != entered_pin:
        st.error("PINコードが間違っているか、現在ゲームが開催されていません。")
        if st.button("戻る"):
            st.session_state.current_page = "home"
            st.rerun()
    else:
        # ニックネーム入力
        if "nickname" not in st.session_state:
            nickname = st.text_input("ニックネームを入力してね！")
            if st.button("入室する", type="primary"):
                if nickname:
                    if "players" not in state:
                        state["players"] = {}
                    state["players"][nickname] = {"score": 0}
                    save_json(STATE_FILE, state)
                    st.session_state.nickname = nickname
                    st.rerun()
        # コントローラー画面
        else:
            st_autorefresh(interval=1000, key="player_refresh")
            state = load_json(STATE_FILE, {})
            status = state.get("status", "lobby")
            nickname = st.session_state.nickname

            st.write(f"👤 **{nickname}** さん")

            if status == "lobby":
                st.info("ホストが開始するのを待っています...")
                st.snow()

            elif status == "question":
                st.warning("問題が出題されています！画面を見て答えてね！")
                col1, col2 = st.columns(2)
                choices = ["🟥", "🟦", "🟨", "🟩"]
                
                answered = state.get("current_answers", {}).get(nickname)
                if answered:
                    st.success("解答を受け付けました！他の人を待ってね。")
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

            elif status == "answer":
                st.info("ホスト画面で正解発表中！")
                
            elif status == "leaderboard":
                score = state.get("players", {}).get(nickname, {}).get("score", 0)
                st.success(f"現在のあなたのスコア: {score} pt")

# ------------------------------------------
# ② 問題作成画面（複数追加対応）
# ------------------------------------------
elif st.session_state.current_page == "maker":
    st.title("📝 問題セット作成")
    quizzes = load_json(QUIZ_FILE, {})

    # セッションに作成中の問題リストを保持
    if "draft_questions" not in st.session_state:
        st.session_state.draft_questions = [{"q": "", "opts": ["", "", "", ""], "ans": 0, "time": 20}]

    quiz_title = st.text_input("クイズセットのタイトル", "新しいクイズ大会")
    st.divider()

    # 複数問題の入力フォームをループで生成
    for i, q in enumerate(st.session_state.draft_questions):
        st.subheader(f"第 {i + 1} 問")
        q["q"] = st.text_input("問題文", value=q["q"], key=f"q_{i}")
        
        col1, col2 = st.columns(2)
        q["opts"][0] = col1.text_input("選択肢1 (🟥)", value=q["opts"][0], key=f"opt0_{i}")
        q["opts"][1] = col2.text_input("選択肢2 (🟦)", value=q["opts"][1], key=f"opt1_{i}")
        q["opts"][2] = col1.text_input("選択肢3 (🟨)", value=q["opts"][2], key=f"opt2_{i}")
        q["opts"][3] = col2.text_input("選択肢4 (🟩)", value=q["opts"][3], key=f"opt3_{i}")
        
        q["ans"] = st.radio("正解はどれ？", [0, 1, 2, 3], format_func=lambda x: f"選択肢{x+1}", horizontal=True, key=f"ans_{i}", index=q["ans"])
        q["time"] = st.number_input("制限時間（秒）", min_value=5, value=q["time"], key=f"time_{i}")
        st.divider()

    # コントロールボタン
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("＋ 問題をさらに追加する"):
            st.session_state.draft_questions.append({"q": "", "opts": ["", "", "", ""], "ans": 0, "time": 20})
            st.rerun()
            
    with col_b:
        if st.button("💾 このセットを保存する", type="primary"):
            quizzes[quiz_title] = st.session_state.draft_questions
            save_json(QUIZ_FILE, quizzes)
            st.success(f"「{quiz_title}」（全{len(st.session_state.draft_questions)}問）を保存しました！")
            # リセット
            st.session_state.draft_questions = [{"q": "", "opts": ["", "", "", ""], "ans": 0, "time": 20}]

# ------------------------------------------
# ③ ロビー画面（ホスト待機）
# ------------------------------------------
elif st.session_state.current_page == "lobby":
    st.title("🎪 ロビー画面")
    quizzes = load_json(QUIZ_FILE, {})
    
    if not quizzes:
        st.error("左のメニューから「問題セット作成」へ行き、クイズを作ってください。")
        st.stop()

    quiz_title = st.selectbox("遊ぶクイズセットを選ぶ", list(quizzes.keys()))

    if st.button("ルームを作成（PIN・QR生成）", type="primary"):
        pin = str(random.randint(1000, 9999))
        
        # ★ GitHub公開後は、ここを自分のStreamlitアプリのURLに変更してください
        base_url = "https://quizhistory.streamlit.app/" 
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
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("参加方法")
            st.write(f"PINコード: **{state.get('pin')}**")
            st.image("join_qr.png", width=300)
            
        with col2:
            st.subheader(f"参加者 ({len(state.get('players', {}))}人)")
            st_autorefresh(interval=2000, key="lobby_refresh")
            for p in state.get("players", {}).keys():
                st.markdown(f"**🙋 {p}**")

        st.divider()
        if st.button("🚀 クイズをスタートする！", type="primary", use_container_width=True):
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
    
    if not quiz_data or status == "lobby":
        st.error("ロビーに戻ってゲームを開始してください。")
        st.stop()

    current_q = quiz_data[q_index]

    # --- 出題中 ---
    if status == "question":
        st.title(f"Q{q_index + 1}. {current_q['q']}")
        col1, col2 = st.columns(2)
        col1.info(f"🟥 {current_q['opts'][0]}")
        col2.info(f"🟦 {current_q['opts'][1]}")
        col1.warning(f"🟨 {current_q['opts'][2]}")
        col2.success(f"🟩 {current_q['opts'][3]}")
        
        if "start_time" not in state:
            state["start_time"] = time.time()
            save_json(STATE_FILE, state)
        
        elapsed = time.time() - state["start_time"]
        remaining = max(0, current_q['time'] - int(elapsed))
        
        st.header(f"⏳ 残り時間: {remaining} 秒")
        
        answers_count = len(state.get("current_answers", {}))
        players_count = len(state.get("players", {}))
        st.progress(answers_count / max(1, players_count))
        st.write(f"{answers_count} / {players_count} 人 解答済み")

        if remaining == 0 or (answers_count == players_count and players_count > 0):
            if st.button("解答を締め切って正解発表！", type="primary"):
                state["status"] = "answer"
                save_json(STATE_FILE, state)
                st.rerun()

    # --- 正解発表 ---
    elif status == "answer":
        st.title("正解発表！")
        correct_idx = current_q['ans']
        st.subheader(f"正解は... 「{current_q['opts'][correct_idx]}」でした！")
        st.balloons()
        
        answers = state.get("current_answers", {})
        counts = [0, 0, 0, 0]
        for p, data in answers.items():
            counts[data["choice"]] += 1
            
        df = pd.DataFrame({"選択肢": current_q['opts'], "投票数": counts})
        st.bar_chart(df.set_index("選択肢"))
        
        if st.button("ランキングを見る 🏆", type="primary"):
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

    # --- ランキング ---
    elif status == "leaderboard":
        st.title("🏆 中間ランキング")
        players = state.get("players", {})
        sorted_players = sorted(players.items(), key=lambda x: x[1]['score'], reverse=True)
        
        for rank, (p, data) in enumerate(sorted_players[:5]):
            st.header(f"{rank + 1}位: {p} ({data['score']} pt)")
            
        st.divider()
        if q_index + 1 < len(quiz_data):
            if st.button("次の問題へ", type="primary"):
                state["current_q_index"] += 1
                state["status"] = "question"
                state.pop("start_time", None)
                state["current_answers"] = {}
                save_json(STATE_FILE, state)
                st.rerun()
        else:
            st.success("🎉 全問終了！お疲れ様でした！")
            st.balloons()
            if st.button("ロビーに戻る"):
                st.session_state.current_page = "lobby"
                st.rerun()
