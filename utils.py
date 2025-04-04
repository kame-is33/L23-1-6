"""
このファイルは、画面表示以外の様々な関数定義のファイルです。
"""

############################################################
# ライブラリの読み込み
############################################################
import os
from dotenv import load_dotenv
import streamlit as st
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage
from langchain_openai import ChatOpenAI
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
import constants as ct
import pandas as pd


############################################################
# 設定関連
############################################################
# 「.env」ファイルで定義した環境変数の読み込み
load_dotenv()


############################################################
# 関数定義
############################################################

def get_source_icon(source):
    """
    メッセージと一緒に表示するアイコンの種類を取得

    Args:
        source: 参照元のありか

    Returns:
        メッセージと一緒に表示するアイコンの種類
    """
    # 参照元がWebページの場合とファイルの場合で、取得するアイコンの種類を変える
    if source.startswith("http"):
        icon = ct.LINK_SOURCE_ICON
    else:
        icon = ct.DOC_SOURCE_ICON
    
    return icon


def build_error_message(message):
    """
    エラーメッセージと管理者問い合わせテンプレートの連結

    Args:
        message: 画面上に表示するエラーメッセージ

    Returns:
        エラーメッセージと管理者問い合わせテンプレートの連結テキスト
    """
    return "\n".join([message, ct.COMMON_ERROR_MESSAGE])


def add_employee_context(chat_message, employee_context):
    """
    チャットメッセージに社員情報を付加

    Args:
        chat_message: ユーザー入力値
        employee_context: 社員情報

    Returns:
        修正されたチャットメッセージ
    """
    if employee_context:
        return f"以下の社員情報を参照して質問に答えてください：\\n{employee_context}\\n\\n{chat_message}"
    return chat_message


def get_llm_response(chat_message, employee_context=""):
    """
    LLMからの回答取得

    Args:
        chat_message: ユーザー入力値

    Returns:
        LLMからの回答
    """
    # LLMのオブジェクトを用意
    llm = ChatOpenAI(model_name=ct.MODEL, temperature=ct.TEMPERATURE)

    # 会話履歴なしでもLLMに理解してもらえる、独立した入力テキストを取得するためのプロンプトテンプレートを作成
    question_generator_template = ct.SYSTEM_PROMPT_CREATE_INDEPENDENT_TEXT
    question_generator_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", question_generator_template),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}")
        ]
    )

    # モードによってLLMから回答を取得する用のプロンプトを変更
    if st.session_state.mode == ct.ANSWER_MODE_1:
        # モードが「社内文書検索」の場合のプロンプト
        question_answer_template = ct.SYSTEM_PROMPT_DOC_SEARCH
    else:
        # モードが「社内問い合わせ」の場合のプロンプト
        question_answer_template = ct.SYSTEM_PROMPT_INQUIRY

    # LLMから回答を取得する用のプロンプトテンプレートを作成
    question_answer_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", question_answer_template),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}")
        ]
    )

    # 会話履歴なしでもLLMに理解してもらえる、独立した入力テキストを取得するためのRetrieverを作成
    history_aware_retriever = create_history_aware_retriever(
        llm, st.session_state.retriever, question_generator_prompt
    )

    # LLMから回答を取得する用のChainを作成
    question_answer_chain = create_stuff_documents_chain(llm, question_answer_prompt)
    # 「RAG x 会話履歴の記憶機能」を実現するためのChainを作成
    chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

    # プロンプトの前処理として、社員データがある場合にチャット入力に先行して付与
    chat_message = add_employee_context(chat_message, employee_context)

    # LLMへのリクエストとレスポンス取得
    llm_response = chain.invoke({"input": chat_message, "chat_history": st.session_state.chat_history})
    # LLMレスポンスを会話履歴に追加
    st.session_state.chat_history.extend([HumanMessage(content=chat_message), llm_response["answer"]])

    return llm_response


def format_row(row):
    """
    従業員の情報をフォーマットして1人分の文字列を作成
    
    Args:
        row: 従業員データの1行（pandas.Series）
    
    Returns:
        整形された文字列
    """
    parts = []
    部署 = row.get("所属部署", "不明")
    
    def add(label, key):
        value = row.get(key, "不明")
        value = "不明" if pd.isna(value) or value == "" else str(value)
        parts.append(f"- **{label}**: {value}")

    parts.append(f"#### {row.get('氏名（フルネーム）', '不明')}")
    parts.append(f"- **所属部署**: {部署}")
    add("社員ID", "社員ID")
    add("性別", "性別")
    add("生年月日", "生年月日")
    add("年齢", "年齢")
    add("メールアドレス", "メールアドレス")
    add("従業員区分", "従業員区分")
    add("入社日", "入社日")
    add("役職", "役職")

    # スキルセットと保有資格はカンマ区切りでリスト表示
    skills = row.get("スキルセット", "")
    skills_list = [s.strip() for s in str(skills).split(",") if s.strip()]
    if skills_list:
        parts.append("- **スキルセット**: " + ", ".join(skills_list))

    qualifications = row.get("保有資格", "")
    qual_list = [q.strip() for q in str(qualifications).split(",") if q.strip()]
    if qual_list:
        parts.append("- **保有資格**: " + ", ".join(qual_list))

    add("大学名", "大学名")
    add("学部・学科", "学部・学科")
    add("卒業年月日", "卒業年月日")

    return "\n".join(parts)

def debug_log(message):
    """
    Streamlitアプリの開発時にのみログを表示するための関数

    Args:
        message: 表示したいログ内容
    """
    if "show_debug_logs" not in st.session_state:
        st.session_state.show_debug_logs = False

    if st.session_state.show_debug_logs:
        with st.sidebar:
            st.markdown("#### 開発者ログ")
            st.code(message, language="text")