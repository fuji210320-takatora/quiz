import streamlit as st
import time
from streamlit_autorefresh import st_autorefresh
from utils import load_json, save_json, STATE_FILE, QUIZ_FILE
import pandas as pd

st.set_page_config(layout="wide")
st_autorefresh(interval=1000, key="host_refresh")

state = load_json(STATE_FILE, {})
quizzes = load_json(QUIZ_FILE, {})
status = state.get("status")
quiz_title = state.get("quiz_title")
q_index = state.get("current_q_index", 0)

if not status or status == "lobby":
    st.error("ロビーからゲームを開始してください。")
    st.stop()

quiz_data = quizzes[quiz_title]
current_q = quiz_data[q_index]

# ----------------------------
# 出題中画面
# ----------------------------
if status == "question":
    st.title(f"Q{q_index + 1}. {current_q['q']}")
    
    # 選択肢の表示
    col1, col2 = st.columns(2)
    col1.info(f"🟥 {current_q['opts'][0]}")
    col2.info(f"🟦 {current_q['opts'][1]}")
    col1.warning(f"🟨 {current_q['opts'][2]}")
    col2.success(f"🟩 {current_q['opts'][3]}")
    
    # 開始時間を記録
    if "start_time" not in state:
        state["start_time"] = time.time()
        save_json(STATE_FILE, state)
    
    elapsed = time.time() - state["start_time"]
    remaining = max(0, current_q['time'] - int(elapsed))
    
    st.header(f"⏳ 残り時間: {remaining} 秒")
    
    # 全員答えたか、時間切れで締め切り
    answers_count = len(state.get("current_answers", {}))
    players_count = len(state.get("players", {}))
    
    st.progress(answers_count / max(1, players_count))
    st.write(f"{answers_count} / {players_count} 人 解答済み")

    if remaining == 0 or (answers_count == players_count and players_count > 0):
        if st.button("解答を締め切って正解発表！", type="primary"):
            state["status"] = "answer"
            save_json(STATE_FILE, state)
            st.rerun()

# ----------------------------
# 正解発表画面
# ----------------------------
elif status == "answer":
    st.title("正解発表！")
    correct_idx = current_q['ans']
    
    st.subheader(f"正解は... 「{current_q['opts'][correct_idx]}」でした！")
    st.balloons() # 正解のエフェクト
    
    # 投票結果の集計
    answers = state.get("current_answers", {})
    counts = [0, 0, 0, 0]
    for p, data in answers.items():
        counts[data["choice"]] += 1
        
    # 棒グラフで表示
    df = pd.DataFrame({
        "選択肢": current_q['opts'],
        "投票数": counts
    })
    st.bar_chart(df.set_index("選択肢"))
    
    if st.button("ランキングを見る 🏆"):
        # スコア計算（早く答えるほど高得点。基本1000点）
        players = state["players"]
        for p, data in answers.items():
            if data["choice"] == correct_idx:
                # タイムボーナスの計算ロジック
                time_ratio = data["time"] / current_q['time']
                points = int(1000 * (1 - (time_ratio / 2)))
                players[p]["score"] += max(500, points) # 最低500点
        
        state["players"] = players
        state["status"] = "leaderboard"
        save_json(STATE_FILE, state)
        st.rerun()

# ----------------------------
# ランキング画面
# ----------------------------
elif status == "leaderboard":
    st.title("🏆 中間ランキング")
    
    players = state.get("players", {})
    # スコア順にソート
    sorted_players = sorted(players.items(), key=lambda x: x[1]['score'], reverse=True)
    
    for rank, (p, data) in enumerate(sorted_players[:5]): # 上位5人
        st.header(f"{rank + 1}位: {p} ({data['score']} pt)")
        
    st.divider()
    
    # 次の問題があるかどうか
    if q_index + 1 < len(quiz_data):
        if st.button("次の問題へ"):
            state["current_q_index"] += 1
            state["status"] = "question"
            state.pop("start_time", None) # タイマーリセット
            state["current_answers"] = {} # 解答リセット
            save_json(STATE_FILE, state)
            st.rerun()
    else:
        st.success("🎉 全問終了！お疲れ様でした！")
        st.balloons()
