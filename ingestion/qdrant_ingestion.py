import hashlib
from pathlib import Path
import re

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from langchain_qdrant import QdrantVectorStore, RetrievalMode, FastEmbedSparse

from langchain_core.documents import Document
from qdrant_client import QdrantClient

from core.config import settings
from core.logging import get_logger
from tools.vectorstore import VectorStore

logger = get_logger()


class DataIngestion:
    def __init__(self):
        self.vectorstore_manager = VectorStore()
        self.vectorstore = self.vectorstore_manager.get_vectorstore("document")
        self.processed_hashes = None
        self.BATCH_SIZE = 100

    def extract_metadata_from_filename(self, filename: str):
        """
        Extract metadata from filename.
        
        Expected format: CompanyName DocType [Quarter] Year.pdf
        Examples:
            - Amazon 10-Q Q1 2024.pdf
            - Microsoft 10-K 2023.pdf
        """

        filename = filename.replace('.pdf', '').replace('.md', '')
        parts = filename.split()

        return {
            'company_name': parts[0],
            'doc_type': parts[1],
            'fiscal_quarter': parts[2] if len(parts)==4 else None,
            'fiscal_year': parts[-1]
        }

    def compute_file_hash(self, file_path: Path):

        sha256_hash = hashlib.sha256()

        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        return sha256_hash.hexdigest()

    def get_processed_hashes(self):
        processed_hashes = set()
        offset = None

        while True:
            points, offset = self.vectorstore.client.scroll(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                limit=10_00,
                with_payload=True,
                offset=offset
            )

            if not points:
                break

            processed_hashes.update(point.payload["metadata"]["file_hash"] for point in points)

            if offset is None:
                break

        return processed_hashes

    def extract_page_number(self, file_path: Path):
        pattern = r'page_(\d+)'
        match = re.search(pattern=pattern, string=file_path.stem)
        return int(match.group(1)) if match else None

    def ingest_file_in_db(self, file_path, processed_hashes):
        documents = []

        file_hash = self.compute_file_hash(file_path)
        if file_hash in processed_hashes:
            return documents  # skip already processed

        path_str = str(file_path)
        if 'markdown' in path_str:
            content_type = 'text'
            doc_name = file_path.name
        elif 'tables' in path_str:
            content_type = 'tables'
            doc_name = file_path.parent.name
        elif 'images_desc' in path_str:
            content_type = 'image'
            doc_name = file_path.parent.name
        else:
            content_type = 'unknown'
            doc_name = file_path.name

        content = file_path.read_text(encoding='utf-8')

        base_metadata = extract_metadata_from_filename(doc_name)
        base_metadata.update({
            'content_type': content_type,
            'file_hash': file_hash,
            'source_file': doc_name
        })

        if content_type == 'text':
            pages = content.split('<!-- page break -->')
            for idx, page in enumerate(pages, start=1):
                metadata = base_metadata.copy()
                metadata.update({'page': idx})
                documents.append(Document(page_content=page, metadata=metadata))
        else:
            page_num = self.extract_page_number(file_path)
            metadata = base_metadata.copy()
            metadata.update({'page': page_num})
            documents.append(Document(page_content=content, metadata=metadata))

        processed_hashes.add(file_hash)
        return documents

    def run_pipeline(self):
        base_path = settings.BASE_RAG_DIR
        all_md_files = list(base_path.rglob("*.md"))

        document_batch = []
        self.processed_hashes = self.get_processed_hashes()

        for md_file in all_md_files:
            docs = self.ingest_file_in_db(md_file, self.processed_hashes)
            document_batch.extend(docs)

            if len(document_batch) >= self.BATCH_SIZE:
                self.vectorstore.add_documents(document_batch)
                document_batch.clear()

        if document_batch:
            self.vectorstore.add_documents(document_batch)
    