from langchain_ollama import ChatOllama

def load_llm():
    llm = ChatOllama(
        model="qwen2.5-coder:3b",
        temperature=0
    )

    return llm