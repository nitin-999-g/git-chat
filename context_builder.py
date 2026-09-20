import json

def build_context(question, ranked_documents, repo_ast, repo_metadata):
    
    context = ""
    context += "REPOSITORY INFORMATION:\n"
    context += f"Owner: {repo_metadata['owner']}\n"
    context += f"Repository: {repo_metadata['name']}\n"
    context += f"GitHub URL: {repo_metadata['url']}\n"
    context += f"Current Commit: {repo_metadata['commit']}\n\n"
    context += f"Total Files: {repo_metadata['stats']['total_files']}\n"
    context += "File Types:\n"

    for extension, count in repo_metadata["stats"]["file_types"].items():
        context += f"  {extension}: {count}\n"

    context += "\n"   
    context += f"USER QUESTION:\n{question}\n\n"
    context += "RELEVANT CODE:\n"

    # Keep track of which files were retrieved
    relevant_files = set()

    for i, (document, score) in enumerate(ranked_documents, start=1):

        source = document.metadata.get("source")
        relevant_files.add(source)

        context += f"\n--- CODE {i} ---\n"
        context += f"Source: {source}\n"
        context += document.page_content
        context += "\n"

    # Only include AST information for relevant files
    context += "\nRELEVANT REPOSITORY AST:\n"

    relevant_ast = {}

    for file in relevant_files:
        if file in repo_ast:
            relevant_ast[file] = repo_ast[file]

    context += json.dumps(relevant_ast,indent=2)
    return context