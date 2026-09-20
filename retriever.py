from sentence_transformers import CrossEncoder

MODEL_NAME = "BAAI/bge-reranker-base"

# retrieve relevant chunks
def retrieve_code(vector_store, question, k=8):
    documents = vector_store.similarity_search(question,k=k)
    return documents

# reranker cross encoder model object
def load_reranker():
    reranker = CrossEncoder(MODEL_NAME, device="cpu")
    return reranker

# ranking and calculating similarity scores
def rerank_documents(reranker, question, documents):
    if not documents:
        return []

    pairs = [(question, document.page_content)for document in documents]
    scores = reranker.predict(pairs)
    
    ranked_documents = sorted(zip(documents, scores), key=lambda item: item[1],reverse=True)
    return ranked_documents