"""
このファイルは、Webアプリのメイン処理が記述されたファイルです。
"""

############################################################
# 1. ライブラリの読み込み
############################################################
# 「.env」ファイルから環境変数を読み込むための関数
from dotenv import load_dotenv
# ログ出力を行うためのモジュール
import logging
# streamlitアプリの表示を担当するモジュール
import streamlit as st
# （自作）画面表示以外の様々な関数が定義されているモジュール
import utils
# （自作）アプリ起動時に実行される初期化処理が記述された関数
from initialize import initialize
# （自作）フォルダ構成やログファイルの初期セットアップ
from initialize import setup_environment
# （自作）画面表示系の関数が定義されているモジュール
import components as cn
# （自作）変数（定数）がまとめて定義・管理されているモジュール
import constants as ct
from constants import MAX_CONTEXT_LENGTH
import pandas as pd
import os

def format_row(df):
    if df.empty:
        return "該当するデータがありません。"

    headers = df.columns.tolist()
    header_row = "| " + " | ".join(headers) + " |\n"
    separator = "| " + " | ".join(["---"] * len(headers)) + " |\n"

    body = ""
    for _, row in df.iterrows():
        values = [str(v) if pd.notna(v) else "" for v in row.tolist()]
        body += "| " + " | ".join(values) + " |\n"

    return header_row + separator + body

############################################################
# 2. 設定関連
############################################################
# ブラウザタブの表示文言を設定
st.set_page_config(
    page_title=ct.APP_NAME
)

# ログ出力を行うためのロガーの設定
logger = logging.getLogger(ct.LOGGER_NAME)

############################################################
# 3. 初期化処理
############################################################
# ==========================================
# フォルダ構成やログファイルの初期セットアップ
# ==========================================
setup_environment()

try:
    # 初期化処理（「initialize.py」の「initialize」関数を実行）
    initialize()
except Exception as e:
    # エラーログの出力
    logger.error(f"{ct.INITIALIZE_ERROR_MESSAGE}\n{e}")
    # エラーメッセージの画面表示
    st.error(utils.build_error_message(ct.INITIALIZE_ERROR_MESSAGE), icon=ct.ERROR_ICON)
    # 後続の処理を中断
    st.stop()

# アプリ起動時のログファイルへの出力
if not "initialized" in st.session_state:
    st.session_state.initialized = True
    logger.info(ct.APP_BOOT_MESSAGE)

############################################################
# 4. 初期表示
############################################################
# タイトル表示
cn.display_app_title()

# モード表示
cn.display_select_mode()

# AIメッセージの初期表示
cn.display_initial_ai_message()

# 開発者メニュー切り替えボタンの表示
cn.render_dev_toggle_button()

############################################################
# 5. 会話ログの表示
############################################################
try:
    # 会話ログの表示
    cn.display_conversation_log()
except Exception as e:
    # エラーログの出力
    logger.error(f"{ct.CONVERSATION_LOG_ERROR_MESSAGE}\n{e}")
    # エラーメッセージの画面表示
    st.error(utils.build_error_message(ct.CONVERSATION_LOG_ERROR_MESSAGE), icon=ct.ERROR_ICON)
    # 後続の処理を中断
    st.stop()

############################################################
# 6. チャット入力の受け付け
############################################################
chat_message = st.chat_input(ct.CHAT_INPUT_HELPER_TEXT)

############################################################
# 7. チャット送信時の処理
############################################################
def build_employee_context(chat_message):
    employee_context = ""
    if any(keyword in chat_message for keyword in ["人事部", "営業部", "資格", "インターン", "マネージャー", "女性", "上智大学", "59歳", "SQL", "Python"]):
        try:
            df = pd.read_csv("data/社員について/社員名簿.csv")
            df = df[df["氏名（フルネーム）"] != "氏名（フルネーム）"]

            # 検索条件の定義
            keyword_filters = {
                "人事部": lambda df: df["所属部署"].str.contains("人事", na=False),
                "営業部": lambda df: df["所属部署"].str.contains("営業", na=False),
                "資格": lambda df: df["保有資格"].notna() & (df["保有資格"] != ""),
                "インターン": lambda df: df["従業員区分"].str.contains("インターン", na=False),
                "マネージャー": lambda df: df["役職"].str.contains("マネージャー", na=False),
                "女性": lambda df: df["性別"] == "女性",
                "上智大学": lambda df: df["大学名"].str.contains("上智", na=False),
                "59歳": lambda df: df["年齢"] == "59",
                "SQL": lambda df: df["スキルセット"].str.contains("SQL", na=False),
                "Python": lambda df: df["スキルセット"].str.contains("Python", na=False),
            }

            # AND条件でフィルタリングを適用
            filtered_df = df.copy()
            for keyword, condition in keyword_filters.items():
                if keyword in chat_message:
                    filtered_df = filtered_df[condition(filtered_df)]

            formatted = format_row(filtered_df)
            if len(formatted) <= MAX_CONTEXT_LENGTH:
                employee_context = formatted
            else:
                headers = filtered_df.columns.tolist()
                header_row = "| " + " | ".join(headers) + " |\n"
                separator = "| " + " | ".join(["---"] * len(headers)) + " |\n"
                truncated = header_row + separator
                current_length = len(truncated)

                for _, row in filtered_df.iterrows():
                    row_text = "| " + " | ".join(str(v) if pd.notna(v) else "" for v in row.tolist()) + " |\n"
                    if current_length + len(row_text) > MAX_CONTEXT_LENGTH:
                        break
                    truncated += row_text
                    current_length += len(row_text)

                employee_context = truncated
        except Exception as e:
            logger.warning(f"社員名簿の読み込みに失敗しました: {e}")
    return employee_context

def handle_chat(chat_message):
    if chat_message:
        # ==========================================
        # 7-1. ユーザーメッセージの表示
        # ==========================================
        # ユーザーメッセージのログ出力
        logger.info({"message": chat_message, "application_mode": st.session_state.mode})

        # ユーザーメッセージを表示
        with st.chat_message("user"):
            st.markdown(chat_message)

        # ==========================================
        # 7-2. LLMからの回答取得
        # ==========================================
        employee_context = build_employee_context(chat_message)
        # 「st.spinner」でグルグル回っている間、表示の不具合が発生しないよう空のエリアを表示
        res_box = st.empty()
        # LLMによる回答生成（回答生成が完了するまでグルグル回す）
        with st.spinner(ct.SPINNER_TEXT):
            try:
                # 画面読み込み時に作成したRetrieverを使い、Chainを実行
                llm_response = utils.get_llm_response(chat_message, employee_context=employee_context)
            except Exception as e:
                # エラーログの出力
                logger.error(f"{ct.GET_LLM_RESPONSE_ERROR_MESSAGE}\n{e}")
                # エラーメッセージの画面表示
                st.error(utils.build_error_message(ct.GET_LLM_RESPONSE_ERROR_MESSAGE), icon=ct.ERROR_ICON)
                # 後続の処理を中断
                st.stop()

        # ==========================================
        # 7-3. LLMからの回答表示
        # ==========================================
        with st.chat_message("assistant"):
            try:
                # ==========================================
                # モードが「社内文書検索」の場合
                # ==========================================
                if st.session_state.mode == ct.ANSWER_MODE_1:
                    # 入力内容と関連性が高い社内文書のありかを表示
                    content = cn.display_search_llm_response(llm_response)

                # ==========================================
                # モードが「社内問い合わせ」の場合
                # ==========================================
                elif st.session_state.mode == ct.ANSWER_MODE_2:
                    # 入力に対しての回答と、参照した文書のありかを表示
                    content = cn.display_contact_llm_response(llm_response)

                # AIメッセージのログ出力
                logger.info({"message": content, "application_mode": st.session_state.mode})
                # 出典情報の表示
                if "file_info_list" in llm_response:
                    sources_markdown = "\n".join(
                        f"- [{os.path.basename(path)}]({path})" for path in llm_response["file_info_list"]
                    )
                    st.markdown("---")
                    st.markdown("**情報源**")
                    st.markdown(sources_markdown)
            except Exception as e:
                # エラーログの出力
                logger.error(f"{ct.DISP_ANSWER_ERROR_MESSAGE}\n{e}")
                # エラーメッセージの画面表示
                st.error(utils.build_error_message(ct.DISP_ANSWER_ERROR_MESSAGE), icon=ct.ERROR_ICON)
                # 後続の処理を中断
                st.stop()

        # ==========================================
        # DEBUGログの表示（チェックON時）
        # ==========================================
        if st.session_state.get("show_debug_logs", False):
            st.subheader("🪵 DEBUGログ")
            try:
                with open("logs/application.log", "r", encoding="utf-8") as f:
                    st.code(f.read(), language="text")
            except FileNotFoundError:
                st.warning("ログファイルが見つかりませんでした。")

        # ==========================================
        # 7-4. 会話ログへの追加
        # ==========================================
        # 表示用の会話ログにユーザーメッセージを追加
        st.session_state.messages.append({"role": "user", "content": chat_message})
        # 表示用の会話ログにAIメッセージを追加
        st.session_state.messages.append({"role": "assistant", "content": content})

if chat_message:
    handle_chat(chat_message)