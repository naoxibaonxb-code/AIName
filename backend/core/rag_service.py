import asyncio
import logging
from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.database import AsyncSessionFactory
from models.knowledge import KnowledgeFile

logger = logging.getLogger(__name__)
embedding_model = OllamaEmbeddings(model="nomic-embed-text")
DB_PATH = "./chroma_rag_db"
PUBLIC_COLLECTION = "public_docs"


def _collection_name(user_id: int, scope: str) -> str:
    return PUBLIC_COLLECTION if scope == "public" else f"user_{user_id}_docs"


def _vector_store(user_id: int, scope: str) -> Chroma:
    return Chroma(
        collection_name=_collection_name(user_id, scope),
        embedding_function=embedding_model,
        persist_directory=DB_PATH,
    )


def delete_knowledge_vectors(record_id: int, user_id: int, scope: str) -> None:
    try:
        _vector_store(user_id, scope).delete(where={"file_id": str(record_id)})
    except Exception:
        logger.warning("知识库向量清理失败: record_id=%s scope=%s", record_id, scope, exc_info=True)


def process_and_store_file(file_path: str, user_id: int, record_id: int, scope: str) -> int:
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf":
        loader = PyPDFLoader(file_path)
    elif suffix == ".txt":
        loader = TextLoader(file_path, encoding="utf-8")
    else:
        raise ValueError("仅支持 PDF 和 TXT 文件")

    documents = loader.load()
    if not documents:
        raise ValueError("文件中没有可解析的文本")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50,
        add_start_index=True,
    )
    chunks = splitter.split_documents(documents)
    if not chunks:
        raise ValueError("文件中没有可索引的文本")

    for chunk in chunks:
        chunk.metadata.update({
            "file_id": str(record_id),
            "scope": scope,
            "owner_user_id": str(user_id),
        })

    vector_store = _vector_store(user_id, scope)
    delete_knowledge_vectors(record_id, user_id, scope)
    vector_store.add_documents(chunks)
    return len(chunks)


async def index_knowledge_file(
        record_id: int, file_path: str, user_id: int, scope: str = "private") -> None:
    async with AsyncSessionFactory() as session:
        record = await session.get(KnowledgeFile, record_id)
        if not record:
            return
        record.status = "processing"
        await session.commit()

        try:
            chunk_count = await asyncio.to_thread(
                process_and_store_file, file_path, user_id, record_id, scope
            )
        except Exception:
            logger.exception("知识库文件解析失败: %s", file_path)
            record.status = "failed"
            record.error_message = "文件解析失败，请检查文件内容或稍后重试"
            record.chunk_count = 0
        else:
            record.status = "ready"
            record.error_message = None
            record.chunk_count = chunk_count
        await session.commit()


def _search_collection(query: str, user_id: int, scope: str, top_k: int) -> list:
    try:
        return _vector_store(user_id, scope).similarity_search(query, k=top_k)
    except Exception:
        logger.warning("知识库检索失败: user_id=%s scope=%s", user_id, scope, exc_info=True)
        return []


def retrieve_user_knowledge(query: str, user_id: int, top_k: int = 2) -> str:
    private_documents = _search_collection(query, user_id, "private", top_k)
    public_documents = _search_collection(query, user_id, "public", top_k)
    documents = private_documents + public_documents
    if not documents:
        return "暂无可用的知识库资料。"

    blocks = []
    for document in documents[:top_k * 2]:
        scope = document.metadata.get("scope", "private")
        label = "平台公共参考资料" if scope == "public" else "用户专属参考资料"
        blocks.append(f"【{label}】\n{document.page_content}")
    return "\n\n".join(blocks)
