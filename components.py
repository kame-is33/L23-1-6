"""
このファイルは、画面表示に特化した関数定義のファイルです。
"""

############################################################
# ライブラリの読み込み
############################################################
import streamlit as st
import pandas as pd
import utils
import constants as ct


############################################################
# 関数定義
############################################################

def display_app_title():
    """
    タイトル表示
    """
    st.markdown(
        """
        <style>
        .app-title {
            color: #FFA500; /* オレンジ色 */
            font-size: 2em; /* フォントサイズ */
            font-weight: bold; /* 太字 */
        }
        </style>
        """, unsafe_allow_html=True
    )
    st.markdown(f"<div class='app-title'>{ct.BOT_ICON} {ct.APP_NAME}</div>", unsafe_allow_html=True)
    st.markdown("こんにちは。私は社内文書の情報をもとに回答する生成AIチャットボットです。サイドバーで利用目的を選択し、画面下部のチャット欄からメッセージを送信してください。")
    st.info(f"{ct.ADVICE_ICON} 具体的に入力したほうが期待通りの回答を得やすいです。")


def display_select_mode():
    """
    回答モードのラジオボタンを表示
    """
    # 回答モードを選択する用のラジオボタンを表示
    col1, col2 = st.columns([100, 1])
    with col1:
        # 「label_visibility="collapsed"」とすることで、ラジオボタンを非表示にする
        st.session_state.mode = st.radio(
            label="",
            options=[ct.ANSWER_MODE_1, ct.ANSWER_MODE_2],
            label_visibility="collapsed"
        )


def display_initial_ai_message():
    """
    AIメッセージの初期表示（右側メイン画面）
    """
    with st.chat_message("assistant"):
        # 「st.success()」とすると緑枠で表示される
        st.markdown("こんにちは。私は社内文書の情報をもとに回答する生成AIチャットボットです。上記で利用目的を選択し、画面下部のチャット欄からメッセージを送信してください。")
        st.markdown(f"{ct.ADVICE_ICON} 具体的に入力したほうが期待通りの回答を得やすいです。")


def display_conversation_log():
    """
    会話ログの一覧表示
    """
    # 会話ログのループ処理
    for message in st.session_state.messages:
        # 「message」辞書の中の「role」キーには「user」か「assistant」が入っている
        with st.chat_message(message["role"]):

            # ユーザー入力値の場合、そのままテキストを表示するだけ
            if message["role"] == "user":
                st.markdown(message["content"])
            
            # LLMからの回答の場合
            else:
                # 「社内文書検索」の場合、テキストの種類に応じて表示形式を分岐処理
                if message["content"]["mode"] == ct.ANSWER_MODE_1:
                    
                    # ファイルのありかの情報が取得できた場合（通常時）の表示処理
                    if not "no_file_path_flg" in message["content"]:
                        # ==========================================
                        # ユーザー入力値と最も関連性が高いメインドキュメントのありかを表示
                        # ==========================================
                        # 補足文の表示
                        st.markdown(message["content"]["main_message"])

                        # 参照元のありかに応じて、適したアイコンを取得
                        icon = utils.get_source_icon(message['content']['main_file_path'])
                        # PDFファイルの場合はページ番号を表示
                        if message['content']['main_file_path'].lower().endswith(".pdf"):
                            # ページ番号を取得（存在しない場合は1と仮定）
                            page_num = message['content'].get('main_page_number', 1)
                            st.success(f"{message['content']['main_file_path']} (ページ: {page_num})", icon=icon)
                        else:
                            # PDF以外の場合
                            st.success(f"{message['content']['main_file_path']}", icon=icon)
                        
                        # ==========================================
                        # ユーザー入力値と関連性が高いサブドキュメントのありかを表示
                        # ==========================================
                        if "sub_message" in message["content"]:
                            # 補足メッセージの表示
                            st.markdown(message["content"]["sub_message"])

                            # サブドキュメントのありかを一覧表示
                            for sub_choice in message["content"]["sub_choices"]:
                                # 参照元のありかに応じて、適したアイコンを取得
                                icon = utils.get_source_icon(sub_choice['source'])
                                # PDFファイルの場合はページ番号を表示
                                if sub_choice['source'].lower().endswith(".pdf"):
                                    # ページ番号を取得（存在しない場合は1と仮定）
                                    page_num = sub_choice.get('page_number', 1)
                                    st.info(f"{sub_choice['source']} (ページ: {page_num})", icon=icon)
                                else:
                                    # PDF以外の場合
                                    st.info(f"{sub_choice['source']}", icon=icon)
                    # ファイルのありかの情報が取得できなかった場合、LLMからの回答のみ表示
                    else:
                        st.markdown(message["content"]["answer"])
                
                # 「社内問い合わせ」の場合の表示処理
                else:
                    # LLMからの回答を表示
                    st.markdown(message["content"]["answer"])

                    # 参照元のありかを一覧表示
                    if "file_info_list" in message["content"]:
                        # 区切り線の表示
                        st.divider()
                        # 「情報源」の文字を太字で表示
                        st.markdown(f"##### {message['content']['message']}")
                        # ドキュメントのありかを一覧表示
                        for file_info in message["content"]["file_info_list"]:
                            # 参照元のありかに応じて、適したアイコンを取得
                            icon = utils.get_source_icon(file_info)
                            st.info(file_info, icon=icon)


def display_search_llm_response(llm_response):
    """
    「社内文書検索」モードにおけるLLMレスポンスを表示

    Args:
        llm_response: LLMからの回答

    Returns:
        LLMからの回答を画面表示用に整形した辞書データ
    """
    # LLMからのレスポンスに参照元情報が入っており、かつ「該当資料なし」が回答として返された場合
    if llm_response["context"] and llm_response["answer"] != ct.NO_DOC_MATCH_ANSWER:

        # ==========================================
        # ユーザー入力値と最も関連性が高いメインドキュメントのありかを表示
        # ==========================================
        # LLMからのレスポンス（辞書）の「context」属性の中の「0」に、最も関連性が高いドキュメント情報が入っている
        main_file_path = llm_response["context"][0].metadata["source"]

        # 補足メッセージの表示
        main_message = "入力内容に関する情報は、以下のファイルに含まれている可能性があります。"
        st.markdown(main_message)
        
        # 参照元のありかに応じて、適したアイコンを取得
        icon = utils.get_source_icon(main_file_path)
        
        # PDFファイルの場合はページ番号を表示、それ以外はファイルパスのみ表示
        if main_file_path.lower().endswith(".pdf"):
            # ページ番号が取得できた場合はその値を使用、取得できない場合は1ページ目と仮定
            if "page" in llm_response["context"][0].metadata:
                main_page_number = llm_response["context"][0].metadata["page"]
            else:
                main_page_number = 1
            # 「メインドキュメントのファイルパス」と「ページ番号」を表示
            st.success(f"{main_file_path} (ページ: {main_page_number})", icon=icon)
        else:
            # PDF以外の場合は「メインドキュメントのファイルパス」のみを表示
            st.success(f"{main_file_path}", icon=icon)

        # ==========================================
        # ユーザー入力値と関連性が高いサブドキュメントのありかを表示
        # ==========================================
        # メインドキュメント以外で、関連性が高いサブドキュメントを格納する用のリストを用意
        sub_choices = []
        # 重複チェック用のリストを用意
        duplicate_check_list = []

        # ドキュメントが2件以上検索できた場合（サブドキュメントが存在する場合）のみ、サブドキュメントのありかを一覧表示
        # 「source_documents」内のリストの2番目以降をスライスで参照（2番目以降がなければfor文内の処理は実行されない）
        for document in llm_response["context"][1:ct.RETRIEVER_TOP_K]:
            # ドキュメントのファイルパスを取得
            sub_file_path = document.metadata["source"]

            # メインドキュメントのファイルパスと重複している場合、処理をスキップ（表示しない）
            if sub_file_path == main_file_path:
                continue
            
            # 同じファイル内の異なる箇所を参照した場合、2件目以降のファイルパスに重複が発生する可能性があるため、重複を除去
            if sub_file_path in duplicate_check_list:
                continue

            # 重複チェック用のリストにファイルパスを順次追加
            duplicate_check_list.append(sub_file_path)
            
            # ページ番号が取得できない場合のための分岐処理
            if "page" in document.metadata:
                # ページ番号を取得
                sub_page_number = document.metadata["page"]
                # 「サブドキュメントのファイルパス」と「ページ番号」の辞書を作成
                sub_choice = {"source": sub_file_path, "page_number": sub_page_number}
            else:
                # 「サブドキュメントのファイルパス」の辞書を作成
                sub_choice = {"source": sub_file_path}
            
            # 後ほど一覧表示するため、サブドキュメントに関する情報を順次リストに追加
            sub_choices.append(sub_choice)
        
        # サブドキュメントが存在する場合のみの処理
        if sub_choices:
            # 補足メッセージの表示
            sub_message = "その他、ファイルありかの候補を提示します。"
            st.markdown(sub_message)

            # サブドキュメントに対してのループ処理
            for sub_choice in sub_choices:
                # 参照元のありかに応じて、適したアイコンを取得
                icon = utils.get_source_icon(sub_choice['source'])
                # PDFファイルの場合はページ番号を表示
                if sub_choice['source'].lower().endswith(".pdf"):
                    # ページ番号が取得できた場合はその値を使用、取得できない場合は1ページ目と仮定
                    page_number = sub_choice.get('page_number', 1)
                    # 「サブドキュメントのファイルパス」と「ページ番号」を表示
                    st.info(f"{sub_choice['source']} (ページ: {page_number})", icon=icon)
                else:
                    # PDF以外の場合は「サブドキュメントのファイルパス」のみを表示
                    st.info(f"{sub_choice['source']}", icon=icon)
        
        # 表示用の会話ログに格納するためのデータを用意
        # - 「mode」: モード（「社内文書検索」or「社内問い合わせ」）
        # - 「main_message」: メインドキュメントの補足メッセージ
        # - 「main_file_path」: メインドキュメントのファイルパス
        # - 「main_page_number」: メインドキュメントのページ番号
        # - 「sub_message」: サブドキュメントの補足メッセージ
        # - 「sub_choices」: サブドキュメントの情報リスト
        content = {}
        content["mode"] = ct.ANSWER_MODE_1
        content["main_message"] = main_message
        content["main_file_path"] = main_file_path
        # メインドキュメントのページ番号は、取得できた場合にのみ追加
        if "page" in llm_response["context"][0].metadata:
            content["main_page_number"] = main_page_number
        # サブドキュメントの情報は、取得できた場合にのみ追加
        if sub_choices:
            content["sub_message"] = sub_message
            content["sub_choices"] = sub_choices
    
    # LLMからのレスポンスに、ユーザー入力値と関連性の高いドキュメント情報が入って「いない」場合
    else:
        # 関連ドキュメントが取得できなかった場合のメッセージ表示
        st.markdown(ct.NO_DOC_MATCH_MESSAGE)

        # 表示用の会話ログに格納するためのデータを用意
        # - 「mode」: モード（「社内文書検索」or「社内問い合わせ」）
        # - 「answer」: LLMからの回答
        # - 「no_file_path_flg」: ファイルパスが取得できなかったことを示すフラグ（画面を再描画時の分岐に使用）
        content = {}
        content["mode"] = ct.ANSWER_MODE_1
        content["answer"] = ct.NO_DOC_MATCH_MESSAGE
        content["no_file_path_flg"] = True
    
    return content


def display_contact_llm_response(llm_response):
    """
    「社内問い合わせ」モードにおけるLLMレスポンスを表示

    Args:
        llm_response: LLMからの回答

    Returns:
        LLMからの回答を画面表示用に整形した辞書データ
    """
    # LLMからの回答を表示
    st.markdown(llm_response["answer"])

    # ユーザーの質問・要望に適切な回答を行うための情報が、社内文書のデータベースに存在しなかった場合
    if llm_response["answer"] != ct.INQUIRY_NO_MATCH_ANSWER:
        # 区切り線を表示
        st.divider()

        # 補足メッセージを表示
        message = "情報源"
        st.markdown(f"##### {message}")

        # 参照元のファイルパスの一覧を格納するためのリストを用意
        file_path_list = []
        file_info_list = []

        # LLMが回答生成の参照元として使ったドキュメントの一覧が「context」内のリストの中に入っているため、ループ処理
        for document in llm_response["context"]:
            # ファイルパスを取得
            file_path = document.metadata["source"]
            # ファイルパスの重複は除去
            if file_path in file_path_list:
                continue

            # PDFファイルの場合はページ番号を表示
            if file_path.lower().endswith(".pdf"):
                # ページ番号が取得できた場合はその値を使用、取得できない場合は1ページ目と仮定
                if "page" in document.metadata:
                    page_number = document.metadata["page"]
                else:
                    page_number = 1
                # 「ファイルパス」と「ページ番号」
                file_info = f"{file_path} (ページ: {page_number})"
            else:
                # PDF以外の場合は「ファイルパス」のみ
                file_info = f"{file_path}"

            # 参照元のありかに応じて、適したアイコンを取得
            icon = utils.get_source_icon(file_path)
            # ファイル情報を表示
            st.info(file_info, icon=icon)

            # 重複チェック用に、ファイルパスをリストに順次追加
            file_path_list.append(file_path)
            # ファイル情報をリストに順次追加
            file_info_list.append(file_info)

    # 表示用の会話ログに格納するためのデータを用意
    # - 「mode」: モード（「社内文書検索」or「社内問い合わせ」）
    # - 「answer」: LLMからの回答
    # - 「message」: 補足メッセージ
    # - 「file_path_list」: ファイルパスの一覧リスト
    content = {}
    content["mode"] = ct.ANSWER_MODE_2
    content["answer"] = llm_response["answer"]
    # 参照元のドキュメントが取得できた場合のみ
    if llm_response["answer"] != ct.INQUIRY_NO_MATCH_ANSWER:
        content["message"] = message
        content["file_info_list"] = file_info_list

    return content


def render_debug_toggle():
    """
    開発者モードを切り替えるトグルスイッチ（ON/OFF）を画面左下に表示。
    トグルを切り替えるとDEBUGログの表示/非表示が切り替わる。
    """
    with st.sidebar:
        st.markdown("---")
        st.markdown("#### 開発者モード")
        debug_toggle = st.checkbox("DEBUGログを表示する", key="debug_checkbox")
        if debug_toggle:
            st.session_state["debug_mode"] = True
        else:
            st.session_state["debug_mode"] = False


def get_dataframe_display_options(df: pd.DataFrame, max_chars: int = 3000) -> pd.DataFrame:
    """
    表示可能な文字数の範囲でDataFrameをカットする関数（Streamlit表示制限対応）
    
    Args:
        df (pd.DataFrame): 表示対象のDataFrame
        max_chars (int): 表示可能な最大文字数
    
    Returns:
        pd.DataFrame: カット後のDataFrame
    """
    output_lines = []
    current_length = 0

    for i, row in df.iterrows():
        line = row.to_string()
        if current_length + len(line) > max_chars:
            break
        output_lines.append(i)
        current_length += len(line)

    return df.loc[output_lines]

def display_sample_prompts():
    """
    左サイドバーに表示される入力例のセクション。
    """
    st.subheader("『社内文書検索』を選択した場合")
    st.info("入力内容と関連性が高い社内文書のありかを検索できます。")
    st.subheader("【入力例】")
    st.write("社員の育成方針に関するMTGの議事録")

    st.subheader("『社内問い合わせ』を選択した場合")
    st.info("質問・要望に対して、社内文書の情報をもとに回答を得られます。")
    st.subheader("【入力例】")
    st.write("人事部に所属している従業員情報を一覧化して")

    st.subheader("【社員情報を含む質問】")
    st.info("人事・従業員・部署に関する質問をすると、社員名簿のデータを参照して回答します。")
    st.subheader("【入力例】")
    st.write("人事部に所属する全従業員のスキルセットを一覧にしてください")

def render_dataframe(df: pd.DataFrame, title: str = "検索結果（社内問い合わせ）") -> None:
    """
    社内問い合わせの回答としてDataFrameを表示するための関数
    
    Args:
        df (pd.DataFrame): 表示するDataFrame
        title (str): 表示タイトル
    """
    if df.empty:
        st.warning("該当するデータが見つかりませんでした。")
        return

    st.markdown(f"### {title}")
    st.dataframe(df, use_container_width=True)
