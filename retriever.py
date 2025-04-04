# ==========================================
# ベクトル化処理・検索機能定義ファイル
# - ドキュメントの再帰的読み込みと更新チェック
# - Chromaベースのベクトルストア生成と保存
# - クエリによる類似検索を提供
# ==========================================

import hashlib
import json
import os
from langchain_core.documents import Document
from langchain_community.document_loaders import UnstructuredPDFLoader, TextLoader, CSVLoader, UnstructuredWordDocumentLoader
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings

METADATA_FILE = ".chroma/metadata.json"

def load_metadata():
    # ベクトルストアのメタデータ読み込み
    if not os.path.exists(METADATA_FILE):
        return {}
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_metadata(meta):
    # ベクトルストアのメタデータ保存
    os.makedirs(os.path.dirname(METADATA_FILE), exist_ok=True)
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

def calculate_hash(file_path):
    # 指定ファイルのMD5ハッシュを生成
    with open(file_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

def get_loader(file_path):
    ext = os.path.splitext(file_path)[-1].lower()
    if ext == ".pdf":
        return UnstructuredPDFLoader(file_path)
    elif ext == ".txt":
        return TextLoader(file_path)
    elif ext == ".csv":
        return CSVLoader(file_path)
    elif ext == ".docx":
        return UnstructuredWordDocumentLoader(file_path)
    else:
        return None

def get_all_documents(data_path: str):
    documents = []
    metadata = load_metadata()
    updated_metadata = {}

    for root, _, files in os.walk(data_path):
        for file in files:
            file_path = os.path.join(root, file)
            if not file_path.lower().endswith((".pdf", ".txt", ".csv", ".docx")):
                continue

            file_hash = calculate_hash(file_path)
            if metadata.get(file_path) == file_hash:
                continue  # 変更なし

            loader = get_loader(file_path)
            if not loader:
                continue

            try:
                docs = loader.load()
                for doc in docs:
                    doc.metadata["source"] = file_path
                documents.extend(docs)
                updated_metadata[file_path] = file_hash
            except Exception as e:
                print(f"Error loading {file_path}: {e}")

    # 更新されたファイルのメタデータのみ保存
    metadata.update(updated_metadata)
    save_metadata(metadata)
    return documents

def create_vector_store(data_path: str):
    documents = get_all_documents(data_path)
    embeddings = OpenAIEmbeddings()
    text_splitter = RecursiveCharacterTextSplitter()
    
    for doc in documents:
        chunks = text_splitter.split_text(doc.page_content)
        for chunk in chunks:
            Chroma.add_texts([chunk], embeddings.embed_documents([chunk]), metadatas=[doc.metadata])

def search_query(query: str, k: int):
    embeddings = OpenAIEmbeddings()
    vector_store = Chroma()
    results = vector_store.similarity_search(query, k=k)
    return results