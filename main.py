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
import pandas as pd

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

# DEBUGログ表示スイッチの表示
cn.render_debug_toggle()

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
    # 社員名簿データの追加処理
    employee_context = ""
    if "人事" in chat_message or "従業員" in chat_message or "部署" in chat_message:
        try:
            df = pd.read_csv("data/社員について/社員名簿.csv")
            def format_row(row):
                def get_value(col):
                    value = str(row.get(col, "")).strip()
                    return value if value else "不明"

                skills = get_value("スキルセット").replace(",", "、")
                certs = get_value("保有資格").replace(",", "、")

                return (
                    f"- **氏名**: {get_value('氏名（フルネーム）')}\n"
                    f"- **社員ID**: {get_value('社員ID')}\n"
                    f"- **性別**: {get_value('性別')}\n"
                    f"- **生年月日**: {get_value('生年月日')}\n"
                    f"- **年齢**: {get_value('年齢')}\n"
                    f"- **メールアドレス**: {get_value('メールアドレス')}\n"
                    f"- **従業員区分**: {get_value('従業員区分')}\n"
                    f"- **入社日**: {get_value('入社日')}\n"
                    f"- **役職**: {get_value('役職')}\n"
                    f"- **スキルセット**: {skills}\n"
                    f"- **保有資格**: {certs}\n"
                    f"- **大学名**: {get_value('大学名')}\n"
                    f"- **学部・学科**: {get_value('学部・学科')}\n"
                    f"- **卒業年月日**: {get_value('卒業年月日')}\n"
                )
            rows = [format_row(row) for _, row in df.iterrows()]
            employee_context = "\\n".join(rows)
        except Exception as e:
            logger.warning(f"社員名簿の読み込みに失敗しました: {e}")

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