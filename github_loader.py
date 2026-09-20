import os
import subprocess
from pathlib import Path

from langchain_core.documents import Document

# new folder for storing repo
REPOS_DIR = Path("repos")

SUPPORTED_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".kts", ".scala", ".c", ".h", ".cpp", ".hpp", ".cc", ".cxx", ".cs", ".go",".rs", ".php", ".rb", ".swift", ".dart",".sh", ".bash", ".zsh", ".ps1",".html", ".css", ".scss", ".sass", ".json", ".yaml", ".yml", ".toml", ".xml", ".md", ".txt", ".ipynb",}
IGNORED_DIRECTORIES = {".git", "venv", ".venv", "__pycache__", "node_modules", ".next", "dist", "build",}

# parse repository name from URL
def parse_github_url(github_url):
    github_url = github_url.rstrip("/")
    repo_name = github_url.split("/")[-1]

    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]

    return repo_name


# clone repository into the system
def clone_repository(github_url):
    repo_name = parse_github_url(github_url)

    # directory to store repository
    REPOS_DIR.mkdir(exist_ok=True)
    repo_path = REPOS_DIR / repo_name

    # if repository already exist, so we dont overstore files
    if repo_path.exists():
        print("Repository already exists.")
        print("Checking for new changes...")

        subprocess.run(["git", "pull", "--ff-only"], cwd=repo_path, check=True)
        return repo_path

    # if repository is new in the system
    print(f"Cloning {repo_name}...")
    subprocess.run(["git", "clone", github_url, str(repo_path)], check=True)
    print("Repository cloned successfully.")
    return repo_path


def load_repository(repo_path):
    documents = []

    for root, dirs, files in os.walk(repo_path):
        # ignoring the irrelevant paths
        dirs[:] = [directory for directory in dirs if directory not in IGNORED_DIRECTORIES]

        for filename in files:
            file_path = Path(root) / filename
            
            # ignoring file path with unavailable extensions
            if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                # finding relative path for better directory representation
                relative_path = file_path.relative_to(repo_path)
                
                document = Document(
                    page_content=content,
                    metadata={
                        "source": str(relative_path),
                        "file_type": file_path.suffix.lower(),
                    }
                )
                # getting each file's content along with some meta data into document object
                documents.append(document)

            except Exception as error:
                print(f"Could not read {file_path}: {error}")

    print(f"Loaded {len(documents)} files.")
    return documents


# fetching some repoistory statistics
def get_repository_stats(repo_path):
    stats = {"total_files": 0, "file_types": {}}

    for root, dirs, files in os.walk(repo_path):
        # ignore irrelevant directories
        dirs[:] = [directory for directory in dirs if directory not in IGNORED_DIRECTORIES]
        for filename in files:
            file_path = Path(root) / filename
            
            # ignoring unavailable extensions
            if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            stats["total_files"] += 1
            extension = file_path.suffix.lower()

            if extension == "":
                extension = "no_extension"

            stats["file_types"][extension] = (stats["file_types"].get(extension, 0) + 1)
    return stats


# get the latest commit of repo
def get_repository_commit(repo_path):
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_path, capture_output=True, text=True,check=True)
    return result.stdout.strip()