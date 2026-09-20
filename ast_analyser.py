from pathlib import Path
import json

from tree_sitter_language_pack import get_parser

AST_DIRECTORY = ".code_assistant"
AST_FILE = "repository_ast.json"

LANGUAGE_BY_EXTENSION = {
    ".py": "python",
    ".js": "javascript", ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".java": "java",
    ".kt": "kotlin", ".kts": "kotlin",
    ".scala": "scala",
    ".c": "c", ".h": "c",
    ".cpp": "cpp", ".hpp": "cpp", ".cc": "cpp", ".cxx": "cpp",
    ".cs": "c_sharp",
    ".go": "go",
    ".rs": "rust",
    ".php": "php",
    ".rb": "ruby",
    ".swift": "swift",
    ".dart": "dart", ".sh": "bash", ".bash": "bash", ".zsh": "bash",
    ".ps1": "powershell",
    ".html": "html",
    ".css": "css",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
}


# These are the kinds of structures that are useful to the LLM when understanding repository organization.
STRUCTURAL_NODE_TYPES = {"function_definition", "function_declaration", "function_item", "method_definition", "method_declaration", "class_definition", "class_declaration", "class_specifier", "interface_declaration", "interface_definition", "struct_definition", "struct_specifier", "enum_declaration", "enum_definition", "if_statement", "elif_clause", "else_clause", "for_statement", "for_in_statement", "while_statement", "switch_statement", "case_statement", "try_statement", "catch_clause", "finally_clause", "with_statement", "match_statement", "match_case", "decorated_definition",}

# get language by extension
def get_language(file_path):
    extension = Path(file_path).suffix.lower()
    return LANGUAGE_BY_EXTENSION.get(extension)

# define structure
def collect_structural_nodes(node):
    structures = []
    
    if node.type in STRUCTURAL_NODE_TYPES:
        structures.append({"type": node.type, "start_line": node.start_point[0] + 1, "end_line": node.end_point[0] + 1,})

    for child in node.children:
        structures.extend(collect_structural_nodes(child))

    return structures

# analyse current file path
def analyze_file(file_path):
    language = get_language(file_path)

    if language is None:
        return None

    try:
        source = Path(file_path).read_bytes()
        parser = get_parser(language)
        tree = parser.parse(source)
        structures = collect_structural_nodes(tree.root_node)
        return {"language": language, "structures": structures,}

    except Exception as error:
        print(f"Could not analyze {file_path}: {error}")
        return None

# genrate repo ast
def generate_repo_ast(repo_path):
    repo_path = Path(repo_path)
    ast_data = {}

    for file_path in repo_path.rglob("*"):

        if not file_path.is_file():
            continue

        if ".git" in file_path.parts:
            continue

        if AST_DIRECTORY in file_path.parts:
            continue

        relative_path = file_path.relative_to(repo_path)
        result = analyze_file(file_path)

        if result is not None:
            ast_data[str(relative_path)] = result

    return ast_data

# get the path for the ast
def get_ast_path(repo_path):
    repo_path = Path(repo_path)
    ast_directory = (repo_path / AST_DIRECTORY)
    ast_directory.mkdir(exist_ok=True)

    return ast_directory / AST_FILE

# saving AST
def save_repo_ast(repo_path, repo_ast, commit_hash):
    ast_path = get_ast_path(repo_path)
    data = {"commit_hash": commit_hash, "ast": repo_ast,}
    ast_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

# loading repo AST
def load_repo_ast(repo_path,commit_hash):
    ast_path = get_ast_path(repo_path)

    if not ast_path.exists():
        return None

    try:
        data = json.loads(ast_path.read_text(encoding="utf-8"))

    except json.JSONDecodeError:
        return None

    if data.get("commit_hash") != commit_hash:
        return None

    return data.get("ast")

# avoid reusing whole ast
def get_or_create_repo_ast(repo_path,commit_hash):
    existing_ast = load_repo_ast(repo_path,commit_hash)

    if existing_ast is not None:
        print("Using existing repository AST.")
        return existing_ast

    print("Generating repository AST...")
    repo_ast = generate_repo_ast(repo_path)
    
    save_repo_ast(repo_path, repo_ast, commit_hash)

    print("Repository AST saved.")
    return repo_ast