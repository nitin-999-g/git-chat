from pathlib import Path
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from ast_analyser import get_language

MAX_CHUNK_SIZE = 1500
MIN_CHUNK_SIZE = 300


def split_documents(documents):
    all_chunks = []

    fallback_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""]
    )

    for document in documents:
        file_path = Path(document.metadata["source"])
        language = get_language(file_path)

        # If Tree-sitter does not support this file, use normal text splitting.
        if language is None:
            chunks = fallback_splitter.split_documents([document])
            all_chunks.extend(chunks)
            continue

        try:
            from tree_sitter_language_pack import get_parser

            parser = get_parser(language)

            source_bytes = document.page_content.encode("utf-8")
            tree = parser.parse(source_bytes)

            # Get the top-level pieces of the source code.
            nodes = [node for node in tree.root_node.children if node.type not in {"comment", "newline"}]

            current_parts = []
            current_start = None
            current_end = None
            current_size = 0

            for node in nodes:
                start = node.start_byte
                end = node.end_byte

                content = source_bytes[start:end].decode("utf-8", errors="ignore")

                if not content.strip():
                    continue

                node_size = len(content)

                # If one individual code block is already too large, split that block normally.
                if node_size > MAX_CHUNK_SIZE:
                    if current_parts:
                        all_chunks.append(
                            Document(
                                page_content="\n\n".join(
                                    current_parts
                                ),
                                metadata={
                                    **document.metadata,
                                    "language": language,
                                    "chunk_type": "combined",
                                    "start_line": current_start,
                                    "end_line": current_end,
                                }
                            )
                        )

                        current_parts = []
                        current_start = None
                        current_end = None
                        current_size = 0

                    temp_document = Document(
                        page_content=content,
                        metadata={
                            **document.metadata,
                            "language": language,
                            "chunk_type": node.type,
                        }
                    )

                    all_chunks.extend(
                        fallback_splitter.split_documents(
                            [temp_document]
                        )
                    )

                    continue

                # If adding this node would make the chunk too large, finish the current chunk first.
                if (current_parts and current_size + node_size > MAX_CHUNK_SIZE):
                    all_chunks.append(
                        Document(
                            page_content="\n\n".join(
                                current_parts
                            ),
                            metadata={
                                **document.metadata,
                                "language": language,
                                "chunk_type": "combined",
                                "start_line": current_start,
                                "end_line": current_end,
                            }
                        )
                    )

                    current_parts = []
                    current_start = None
                    current_end = None
                    current_size = 0

                # Start a new chunk if necessary.
                if not current_parts:
                    current_start = node.start_point[0] + 1

                current_parts.append(content)
                current_end = node.end_point[0] + 1
                current_size += node_size

                # Once the chunk is reasonably sized, finish it.
                if current_size >= MIN_CHUNK_SIZE:
                    all_chunks.append(
                        Document(
                            page_content="\n\n".join(
                                current_parts
                            ),
                            metadata={
                                **document.metadata,
                                "language": language,
                                "chunk_type": "combined",
                                "start_line": current_start,
                                "end_line": current_end,
                            }
                        )
                    )

                    current_parts = []
                    current_start = None
                    current_end = None
                    current_size = 0

            # Don't lose the final small chunk.
            if current_parts:
                all_chunks.append(
                    Document(
                        page_content="\n\n".join(current_parts),
                        metadata={
                            **document.metadata,
                            "language": language,
                            "chunk_type": "combined",
                            "start_line": current_start,
                            "end_line": current_end,
                        }
                    )
                )

        except Exception as error:
            print(f"Could not structurally split {file_path}: {error}")
            # If structural splitting fails, fall back to normal text splitting.
            all_chunks.extend(fallback_splitter.split_documents([document]))

    print(f"Created {len(all_chunks)} code-aware chunks.")
    return all_chunks