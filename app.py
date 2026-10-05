import streamlit as st
import time
from streamlit_autorefresh import st_autorefresh
from utils import load_json, save_json, STATE_FILE

st.set_page_config(page_title="自作Kahoot", layout="centered")

# URLからPINコードを取得（QRコードから飛んできた場合）
query_params = st.query_params
url_pin = query_params.get("pin", "")

state = load_json(STATE_FILE, {})

if url_pin:
    st.title("📱 プレイヤー画面")
    
    # 参加前（名前入力）
    if "nickname" not in st.session_state:
        nickname = st.text_input("ニックネームを入力してね！")
        if st.button("参加する！"):
            if nickname:
                # プレイヤーを登録
                state = load_json(STATE_FILE, {})
                if "players" not in state:
                    state["players"] = {}
                state["players"][nickname] = {"score": 0}
                save_json(STATE_FILE, state)
                
                st.session_state.nickname = nickname
                st.rerun()
    
    # 参加後（コントローラー画面）
    else:
        # 1秒ごとに状態を自動更新
        st_autorefresh(interval=1000, key="player_refresh")
        state = load_json(STATE_FILE, {})
        status = state.get("status", "lobby")
        nickname = st.session_state.nickname

        st.write(f"👤 {nickname} さん")

        if status == "lobby":
            st.info("ホストが開始するのを待っています...")
            st.snow() # 待機中のエフェクト

        elif status == "question":
            st.warning("問題が出題されています！画面を見て答えてね！")
            
            # スマホ側は色付きの絵文字ボタンだけを表示（Kahoot風）
            col1, col2 = st.columns(2)
            choices = ["🟥", "🟦", "🟨", "🟩"]
            
            # すでに答えたかチェック
            answered = state.get("current_answers", {}).get(nickname)
            if answered:
                st.success("解答を受け付けました！他の人を待ってね。")
            else:
                for i, choice in enumerate(choices):
                    target_col = col1 if i % 2 == 0 else col2
                    if target_col.button(choice, use_container_width=True, key=f"btn_{i}"):
                        # 答えた時間を記録
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
            
else:
    st.title("⚡ 自作Kahoot システム")
    st.write("左のメニューから画面を選んでね！")
    st.write("※スマホから参加する人は、ホストが映すQRコードを読み込んでください。")
