import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from openai import vector_stores

embedding_model = OllamaEmbeddings(model="nomic-embed-text")
DB_PATH = "./chroma_rag_db"


def process_and_store_file(file_path: str, user_id: int):
    """
    后台任务：解析文件并存入该用户的专属向量库
    """
    print(f"[后台任务启动] 正在处理用户 {user_id} 的文件: {file_path}")
    if file_path.endswith(".pdf"):
        loader = PyPDFLoader(file_path)
    elif file_path.endswith(".txt"):
        loader = TextLoader(file_path, encoding="utf-8")
    else:
        print("不支持的文件格式")
        return

    docs = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50,
        add_start_index=True,
    )
    all_splits = text_splitter.split_documents(docs)
    collection_name = f"user_{user_id}_docs"
    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=embedding_model,
        persist_directory=DB_PATH,
    )
    vector_store.add_documents(documents=all_splits)


def retrieve_user_knowledge(query: str, user_id: int, top_k: int = 2) -> str:
    """
    供智能体调用的检索工具：只查当前用户的专属知识库
    """
    collection_name = f"user_{user_id}_docs"
    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=embedding_model,
        persist_directory=DB_PATH,
    )
    retrieved_docs = vector_store.similarity_search(query, k=top_k)
    if not retrieved_docs:
        return "未在您的知识库中检索到相关信息。"
    context = "\n\n".join(
        f"【您的专属参考资料】:\n{doc.page_content}" for doc in retrieved_docs
    )
    return context