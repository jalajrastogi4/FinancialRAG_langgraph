from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore, RetrievalMode, FastEmbedSparse
from core.config import settings
from core.logging import get_logger

logger = get_logger()


class VectorStore:
    def __init__(self):
        self.sparse_embeddings = FastEmbedSparse(model_name=settings.QDRANT_SPARSE_MODEL)
        try:
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model=settings.EMBEDDINGS_MODEL,
                api_key=settings.GOOGLE_API_KEY
            )
            logger.info("Initialized embeddings")
        except Exception as e:
            logger.exception("Failed to initialize embeddings")
            raise

    def get_vectorstore(self, choice: str = "normal"):
        try:
            logger.info("Initializing vector store...")

            if choice == "document":
                vector_store = QdrantVectorStore.from_documents(
                    documents=[],
                    embedding=self.embeddings,
                    sparse_embedding=self.sparse_embeddings,
                    url=settings.QDRANT_URL, 
                    api_key=settings.QDRANT_API_KEY,
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    retrieval_mode=RetrievalMode.HYBRID,
                    force_recreate=False,
                    timeout=3600
                )
                logger.info("Initialized vector store successfully")

                return vector_store
            else:
                vector_store = QdrantVectorStore.from_existing_collection(
                    embedding=self.embeddings,
                    sparse_embedding=self.sparse_embeddings,
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    url=settings.QDRANT_URL, 
                    api_key=settings.QDRANT_API_KEY,
                    retrieval_mode=RetrievalMode.HYBRID,
                )
                logger.info("Initialized vector store successfully")

                return vector_store

        except Exception as e:
            logger.exception("Failed to initialize vector store")
            raise
        