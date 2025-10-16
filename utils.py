import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import CSVLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain

# ------------------------------ Load Keys ------------------------------
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY not set in environment variables (.env)")

# ------------------------------ Helpers ------------------------------

def find_files(path: Path) -> list[Path]:
    exts = [".csv", ".txt"]
    return [p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in exts]

def load_documents(paths: list[Path]) -> list[Document]:
    docs = []
    for p in paths:
        try:
            if p.suffix.lower() == ".csv":
                docs.extend(CSVLoader(str(p)).load())
            elif p.suffix.lower() == ".txt":
                docs.extend(TextLoader(str(p), encoding="utf-8").load())
        except Exception as e:
            print(f"[WARN] Failed to load {p}: {e}")
    return docs

def split_documents(docs: list[Document], splitter_cfg: dict) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=splitter_cfg["chunk_size"], 
        chunk_overlap=splitter_cfg["chunk_overlap"]
    )
    return splitter.split_documents(docs)

# ------------------------------ FAISS Build ------------------------------

def build_or_load_faiss(chunks, rebuild, index_path):
    """
    Use HuggingFace sentence-transformers for embeddings (free, local).
    """
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    if rebuild:
        vs = FAISS.from_documents(chunks, embeddings)
        index_path.mkdir(parents=True, exist_ok=True)
        vs.save_local(str(index_path))
    return FAISS.load_local(str(index_path), embeddings, allow_dangerous_deserialization=True)

# ------------------------------ Retriever & RAG ------------------------------

def make_retriever(vectorstore: FAISS, retriever_cfg: dict):
    return vectorstore.as_retriever(
        search_type=retriever_cfg["search_type"], 
        search_kwargs={"k": retriever_cfg["top_k"]}
    )

def make_rag_chain(retriever, chat_model: str):
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a concise assistant. Answer only from the dataset context and cite sources."),
        ("human", "Question:\n{input}\n\nContext:\n{context}")
    ])
    llm = ChatGroq(model=chat_model, temperature=0.2, groq_api_key=GROQ_API_KEY)
    doc_chain = create_stuff_documents_chain(llm, prompt)
    return create_retrieval_chain(retriever, doc_chain)

# ------------------------------ Utility ------------------------------

def calculate_discounted_price(price: float, discount: str) -> float:
    try:
        discount_value = float(discount.strip('%')) / 100
        return round(price - (price * discount_value), 2)
    except:
        return price

def extract_product_info(ctx: list[Document]) -> dict:
    results = {}
    for d in ctx:
        text = d.page_content.strip()
        parts = text.split(",")
        if len(parts) >= 5:
            product, category, price, discount, source = parts
            try:
                price = float(price)
            except:
                continue
            discounted_price = calculate_discounted_price(price, discount)
            results.setdefault(product, []).append({
                "category": category,
                "price": price,
                "discount": discount,
                "discounted_price": discounted_price,
                "source": source
            })
    return results

def format_sources(ctx: list[Document]) -> str:
    sources = [d.metadata.get("source") or d.metadata.get("file_path") or "unknown" for d in ctx]
    return ", ".join(set(sources))
