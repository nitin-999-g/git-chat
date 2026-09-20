from github_loader import clone_repository, get_repository_stats, get_repository_commit, load_repository
from vector_store import load_vector_store, create_vector_store, vector_store_is_current, delete_vector_store, close_vector_store

from text_splitter import split_documents
from retriever import retrieve_code, load_reranker, rerank_documents
from ast_analyser import get_or_create_repo_ast
from context_builder import build_context
from langchain_core.prompts import PromptTemplate
from llm import load_llm


class CodeAssistant:

    # intitalise the object with repo data, vector store, ranker model, llm model, chat history
    def __init__(self, github_url):

        print("Setting up repository...")
        self.github_url = github_url

        parts = github_url.rstrip("/").split("/")
        self.repo_owner = parts[-2]
        self.repo_path = clone_repository(github_url)
        self.repo_name = self.repo_path.name
        self.repo_stats = get_repository_stats(self.repo_path)
        self.vector_store = (self._get_vector_store())

        print("Loading reranker...")
        self.reranker = load_reranker()

        print("Loading LLM...")
        self.llm = load_llm()

        # check for current commit in case there's a new change in repo
        current_commit = get_repository_commit(self.repo_path)
        self.repo_ast = get_or_create_repo_ast(self.repo_path, current_commit)

        self.chat_history = []
        print("Code assistant ready!")

    # vector store setup
    def _get_vector_store(self):
        current_commit = get_repository_commit(self.repo_path)
        vector_store = load_vector_store(self.repo_name)

        # if vector store already present in system
        if (vector_store is not None and vector_store_is_current(self.repo_name,current_commit)):
            print("Using existing vector store.")
            return vector_store

        print("Creating fresh vector store...")

        # IMPORTANT!! to delete older vector store
        if vector_store is not None:
            close_vector_store(vector_store)
            self.vector_store = None
            delete_vector_store(self.repo_name)

        documents = load_repository(self.repo_path)
        chunks = split_documents(documents)

        return create_vector_store(chunks, self.repo_name, current_commit)

    
    # main method to get query from user
    def ask(self, question):

        # Use recent conversation when formingthe retrieval query.
        recent_history = self.chat_history[-6:]

        retrieval_query = ""
        for message in recent_history:
            retrieval_query += (f"{message['role']}: {message['content']}\n")

        retrieval_query += (f"User: {question}")

        print("\nRetrieving relevant code...")
        retrieved_documents = retrieve_code(self.vector_store, retrieval_query, k=8)

        print(f"Retreved {len(retrieved_documents)} chunks.")
        
        print("Reranking...")
        ranked_documents = rerank_documents(self.reranker, retrieval_query, retrieved_documents)
        ranked_documents = ranked_documents[:4]

        print("Building context...")
        current_commit = get_repository_commit(self.repo_path)
        context = build_context(
            question,
            ranked_documents,
            self.repo_ast,
            {
                "owner": self.repo_owner,
                "name": self.repo_name,
                "url": self.github_url,
                "commit": current_commit,
                "stats": self.repo_stats,
            }
        )

        # Build conversation history for the LLM.
        recent_history = self.chat_history[-6:]
        
        conversation = ""
        for message in recent_history:
            conversation += (f"{message['role']}: {message['content']}\n\n")

        # prompt augumentation
        prompt_template = PromptTemplate(
            template="""
            You are a codebase assistant helping the user understand
            a GitHub repository.

            Your job is to explain the repository clearly using the
            provided repository context.

            Follow these rules:

            1. Answer the user's actual question directly.

            2. Use the relevant code from the repository context as
            the primary source of truth.

            3. Use the repository AST only to help understand the
            structure and relationships of the relevant code.

            4. Use conversation history only when it helps resolve
            references such as:
            - "this function"
            - "that file"
            - "the previous approach"
            - "why does it do that?"

            5. Do not assume that code exists in the repository if it
            is not present in the provided context.

            6. If the provided repository context does not contain
            enough information to answer confidently, clearly say so
            instead of inventing an answer.

            7. When explaining code:
            - mention the relevant file
            - mention the relevant function or class when possible
            - explain what happens step by step
            - use small code snippets only when they make the
                explanation clearer

            8. Prefer simple explanations over unnecessary technical
            terminology.

            9. If the user asks "how" something works, explain the
            flow from beginning to end.

            10. If the user asks "why" something happens, explain the
                reasoning based on the actual repository code.

            11. If multiple pieces of code are involved, explain how
                they connect to each other.

            12. Do not describe the RAG system itself unless the user
                asks about the assistant's architecture.


            CONVERSATION HISTORY:

            {conversation}


            REPOSITORY CONTEXT:

            {context}


            USER QUESTION:

            {question}


            Now answer the user's question clearly and concisely.
            """
        )

        prompt = prompt_template.format(
            conversation=conversation,
            context=context,
            question=question
        )

        print("Generating answer...")

        response = self.llm.invoke(prompt)

        answer = response.content

        answer = response.content
        self.chat_history.append({"role": "User","content": question,})
        self.chat_history.append({"role": "Assistant", "content": answer,})
        
        return answer

    # if you want to refresh repository
    def refresh_repository(self):
        print("\nChecking repository for updates...")
        self.repo_path = clone_repository(self.github_url)
        
        # Repository contents may have changed, so refresh the file statistics.
        self.repo_stats = get_repository_stats(self.repo_path)

        # Vector store will be reused if the repository commit is still current.
        self.vector_store = (self._get_vector_store())

        current_commit = get_repository_commit(self.repo_path)

        print("Updating repository AST...")
        self.repo_ast = get_or_create_repo_ast(self.repo_path,current_commit)
        print("Repository refresh complete!")