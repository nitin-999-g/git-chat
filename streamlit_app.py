import streamlit as st
from answer import CodeAssistant

# Page configuration
st.set_page_config(
    page_title="GitHub Code Assistant",
    page_icon="💻",
    layout="wide"
)

# Simple custom styling
st.markdown(
    """
<style>

.stApp {background-color: #0f1117;}

.block-container {max-width: 1150px; padding-top: 2rem;}

h1 {letter-spacing: -0.5px;}

section[data-testid="stSidebar"] {background-color: #151821;}

.stButton > button {border-radius: 8px; font-weight: 600;}

.repo-info {
    padding: 12px 16px;
    border-left: 3px solid #6366f1;
    background-color: #171a23;
    border-radius: 6px;
    margin-bottom: 20px;
}

.repo-name {
    font-size: 18px;
    font-weight: 600;
}

.repo-url {
    color: #8b92a5;
    font-size: 13px;
}

</style>
""",
    unsafe_allow_html=True
)

# Session state
if "assistant" not in st.session_state:
    st.session_state.assistant = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "repo_url" not in st.session_state:
    st.session_state.repo_url = None


# Sidebar
with st.sidebar:
    st.title("💻 Code Assistant")
    st.caption("Ask questions about any GitHub repository.")
    st.divider()
    st.subheader("Repository")
    github_url = st.text_input("GitHub Repository URL", placeholder="https://github.com/user/repository")

    if st.button("Initialize Repository",use_container_width=True):
        if not github_url:
            st.warning("Please enter a GitHub repository URL.")
            
        elif st.session_state.repo_url != github_url:
            with st.spinner("Setting up repository..."):
                st.session_state.assistant = (CodeAssistant(github_url))

            st.session_state.repo_url = github_url
            st.session_state.messages = []
            st.success("Repository is ready!")

        else:
            st.info("Repository is already initialized.")


    # Repository information
    if st.session_state.assistant is not None:
        assistant = st.session_state.assistant
        st.divider()
        st.subheader("Repository Info")

        stats = assistant.repo_stats

        st.write(f"**Repository:** {assistant.repo_name}" )
        st.write( f"**Owner:** {assistant.repo_owner}")
        st.write( f"**Files:** {stats['total_files']}")

        if st.button( "🔄 Refresh Repository",  use_container_width=True):
            with st.spinner("Checking for repository updates..."):
                assistant.refresh_repository()

            st.success("Repository refreshed!")

# Main area
st.title("💬 Chat With Your Repository")
st.caption("Understand your codebase using semantic retrieval, reranking and repository-aware context.")


# Repository header
if st.session_state.assistant is not None:
    assistant = st.session_state.assistant
    st.markdown(
        f"""
        <div class="repo-info">
            <div class="repo-name">
                📦 {assistant.repo_name}
            </div>
            <div class="repo-url">
                {assistant.github_url}
            </div>
        </div>
        """,
                unsafe_allow_html=True
    )

# Empty state
if (st.session_state.assistant is None and not st.session_state.messages):
    st.info("Enter a GitHub repository URL in the sidebar to get started.")

# Chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if st.session_state.assistant is not None:
    question = st.chat_input( "Ask a question about the repository...")
    
    if question:
        st.session_state.messages.append({"role": "user", "content": question})

        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Searching the codebase..."):
                answer = st.session_state.assistant.ask(question)

            st.markdown(answer)

        st.session_state.messages.append({ "role": "assistant",   "content": answer})