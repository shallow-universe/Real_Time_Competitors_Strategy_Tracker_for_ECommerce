import os
from pathlib import Path
from utils import (
    find_files, load_documents, split_documents,
    build_or_load_faiss, make_retriever, make_rag_chain,
    extract_product_info, format_sources
)

# ------------------------------
# CONFIG
# ------------------------------
DATA_DIR = Path("My_docs")      # Amazon + Flipkart CSVs
INDEX_DIR = Path("faiss_index") # FAISS index

CHUNKER_CFG = {"chunk_size": 500, "chunk_overlap": 50}
RETRIEVER_CFG = {"search_type": "similarity", "top_k": 5}

REBUILD_INDEX = True   # True = always rebuild
CHAT_MODEL = "llama-3.3-70b-versatile"  # Groq LLM

# ------------------------------
# STEP 1: Load Documents
# ------------------------------
print("📂 Looking for dataset files...")
files = find_files(DATA_DIR)
if not files:
    print("⚠ No dataset files found in My_docs/. Run the scrapers first!")
    exit(1)

print(f"✅ Found {len(files)} dataset files")
docs = load_documents(files)
print(f"📄 Loaded {len(docs)} raw documents")

# ------------------------------
# STEP 2: Split into Chunks
# ------------------------------
print("✂️ Splitting into chunks...")
chunks = split_documents(docs, CHUNKER_CFG)
print(f"✅ Created {len(chunks)} chunks")

# ------------------------------
# STEP 3: Build / Load FAISS
# ------------------------------
print("🧠 Building / Loading FAISS index...")
faiss_index = build_or_load_faiss(chunks, rebuild=REBUILD_INDEX, index_path=INDEX_DIR)
print("✅ FAISS index ready")

# ------------------------------
# STEP 4: Create Retriever + RAG
# ------------------------------
retriever = make_retriever(faiss_index, RETRIEVER_CFG)
rag_chain = make_rag_chain(retriever, chat_model=CHAT_MODEL)
print("🤖 RAG pipeline ready!")

# ------------------------------
# STEP 5: Interactive Modes
# ------------------------------
def summarize_reviews(product_name: str):
    """
    Retrieves all reviews for a given product and summarizes them.
    """
    query = f"Summarize the reviews for {product_name}"
    response = rag_chain.invoke({"input": query})
    print("\n📝 Review Summary for", product_name)
    print(response["answer"])
    if "context" in response:
        print("\n📚 Sources:", format_sources(response["context"]))
    print("\n" + "-"*50 + "\n")

def compare_products(product_name: str):
    """
    Compare Amazon vs Flipkart product details (price, discount, rating).
    """
    query = f"Fetch product details for {product_name} from Amazon and Flipkart"
    response = rag_chain.invoke({"input": query})
    ctx = response.get("context", [])

    product_info = extract_product_info(ctx)

    if not product_info:
        print(f"⚠ No structured info found for {product_name}")
        return

    print(f"\n📊 Comparison for: {product_name}\n")
    for product, entries in product_info.items():
        print(f"🔹 {product}")
        for e in entries:
            print(f"   - Source: {e['source']}")
            print(f"   - Category: {e['category']}")
            print(f"   - Price: ₹{e['price']}")
            print(f"   - Discount: {e['discount']}")
            print(f"   - Discounted Price: ₹{e['discounted_price']}")
            print()
    print("-"*50)

def main():
    print("\n💬 Ask me anything about Amazon/Flipkart products!")
    print("   Examples:")
    print("   - 'Which mobiles have the best discounts?'")
    print("   - 'Summarize reviews for iPhone 16'")
    print("   - 'Compare iPhone 16 between Amazon and Flipkart'")
    print("Type 'exit' to quit.\n")

    while True:
        query = input("❓ Your question: ").strip()
        if query.lower() in ["exit", "quit"]:
            print("👋 Goodbye!")
            break

        # Special case: summarization
        if query.lower().startswith("summarize reviews for"):
            product = query.replace("summarize reviews for", "").strip()
            summarize_reviews(product)
            continue

        # Special case: comparison
        if query.lower().startswith("compare"):
            product = query.replace("compare", "").replace("between amazon and flipkart", "").strip()
            compare_products(product)
            continue

        # Normal Q&A
        try:
            response = rag_chain.invoke({"input": query})
            print("\n📖 Answer:\n", response["answer"])
            if "context" in response:
                print("\n📚 Sources:", format_sources(response["context"]))
            print("\n" + "-"*50 + "\n")
        except Exception as e:
            print(f"⚠ Error: {e}")

if __name__ == "__main__":
    main()

