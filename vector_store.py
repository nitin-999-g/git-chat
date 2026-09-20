from pathlib import Path
import json
import shutil

from langchain_chroma import Chroma
from embeddings import load_embedding_model


VECTOR_STORES_DIR = Path("vector_stores")
INDEX_VERSION = "1"

# fetch vector store path
def get_vector_store_path(repo_name):
    return VECTOR_STORES_DIR / repo_name

# fetch meta data about vector store
def get_metadata_path(repo_name):
    return get_vector_store_path(repo_name) / "metadata.json"

# storing vector store meta data
def save_vector_store_metadata(repo_name,commit_hash):
    metadata_path = get_metadata_path(repo_name)
    metadata = {"commit_hash": commit_hash, "index_version": INDEX_VERSION}

    metadata_path.write_text(
        json.dumps(
            metadata,
            indent=2
        ),
        encoding="utf-8"
    )

# get stored meta data
def get_stored_metadata(repo_name):  
    metadata_path = get_metadata_path(repo_name)
    
    if not metadata_path.exists():
        return None

    try:
        return json.loads(metadata_path.read_text(encoding="utf-8"))

    except json.JSONDecodeError:
        return None

# create vector store for first time
def create_vector_store(chunks, repo_name, commit_hash):    
    print("Loading embedding model...")
    embeddings = load_embedding_model()

    vector_store_path = get_vector_store_path(repo_name)
    vector_store_path.mkdir(parents=True, exist_ok=True)

    print("Creating vector store...")
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name="code_chunks",
        persist_directory=str(
            vector_store_path
        )
    )

    # save vector store meta data with latest commit
    save_vector_store_metadata(repo_name, commit_hash)
    print("Vector store created.")
    return vector_store

# fetch vector store
def load_vector_store(repo_name):
    vector_store_path = get_vector_store_path(repo_name)

    if not vector_store_path.exists():
        return None

    metadata = get_stored_metadata(repo_name)

    if metadata is None:
        return None

    embeddings = load_embedding_model()
    vector_store = Chroma(
        collection_name="code_chunks",
        embedding_function=embeddings,
        persist_directory=str(
            vector_store_path
        )
    )

    return vector_store

# IMPORTANT!! if not closed, can give error at the time of deleting older vector store
def close_vector_store(vector_store):
    if vector_store is None:
        return

    client = getattr(vector_store, "_client", None)

    if client is not None:
        client.close()

    print("Vector store closed.")

# check for latest commit
def vector_store_is_current(repo_name, current_commit):   
    metadata = get_stored_metadata(repo_name)

    if metadata is None:
        return False

    stored_commit = metadata.get("commit_hash")
    stored_index_version = metadata.get("index_version")

    if stored_commit != current_commit or stored_index_version != INDEX_VERSION:
        return False

    return True

# delete older vector store
def delete_vector_store(repo_name):
    vector_store_path = get_vector_store_path(repo_name)
    if vector_store_path.exists():
        shutil.rmtree(vector_store_path)
        print("Old vector store deleted.")