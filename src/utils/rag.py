import os
import json
import logging
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

class RAG:
    def __init__(self, embed_model="all-MiniLM-L6-v2", index_path="./data/rag_index", doc_dir="./data/documents"):
        self.embed_model = SentenceTransformer(embed_model)
        self.index_path = index_path
        self.doc_dir = doc_dir
        self.dimension = self.embed_model.get_sentence_embedding_dimension()
        self.index = None
        self.documents = []
        self._initialize_index()
        self._load_documents()

    def _initialize_index(self):
        try:
            if os.path.exists(f"{self.index_path}/faiss_index.bin"):
                self.index = faiss.read_index(f"{self.index_path}/faiss_index.bin")
                with open(f"{self.index_path}/documents.json", "r", encoding="utf-8") as f:
                    self.documents = json.load(f)
            else:
                os.makedirs(self.index_path, exist_ok=True)
                self.index = faiss.IndexFlatL2(self.dimension)
        except Exception as e:
            logging.error(f"Error initializing FAISS index: {str(e)}")
            self.index = faiss.IndexFlatL2(self.dimension)

    def _load_documents(self):
        if not os.path.exists(self.doc_dir):
            os.makedirs(self.doc_dir, exist_ok=True)
            return

        for filename in os.listdir(self.doc_dir):
            filepath = os.path.join(self.doc_dir, filename)
            try:
                if filename.endswith(".pdf"):
                    self._process_pdf(filepath)
                elif filename.endswith(".json"):
                    self._process_json(filepath)
                elif filename.endswith(".jsonl"):
                    self._process_jsonl(filepath)
            except Exception as e:
                logging.error(f"Error processing {filename}: {str(e)}")

        if self.documents:
            self._index_documents()

    def _process_pdf(self, filepath):
        with open(filepath, "rb") as f:
            pdf = PdfReader(f)
            text = "".join(page.extract_text() or "" for page in pdf.pages)
            chunks = [text[i:i+512] for i in range(0, len(text), 512)]  # Chunk text to 512 chars
            self.documents.extend(chunks)

    def _process_json(self, filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                texts = [json.dumps(item, ensure_ascii=False) for item in data]
            elif isinstance(data, dict):
                texts = [json.dumps(data, ensure_ascii=False)]
            else:
                texts = [str(data)]
            self.documents.extend(texts[:512])

    def _process_jsonl(self, filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            texts = [json.loads(line.strip()) for line in f if line.strip()]
            texts = [json.dumps(item, ensure_ascii=False) for item in texts]
            self.documents.extend(texts[:512])

    def _index_documents(self):
        if not self.documents:
            return
        embeddings = self.embed_model.encode(self.documents, show_progress_bar=False)
        embeddings = np.array(embeddings).astype("float32")
        self.index.add(embeddings)
        faiss.write_index(self.index, f"{self.index_path}/faiss_index.bin")
        with open(f"{self.index_path}/documents.json", "w", encoding="utf-8") as f:
            json.dump(self.documents, f, ensure_ascii=False)

    def retrieve(self, query, top_k=3):
        try:
            query_embedding = self.embed_model.encode([query], show_progress_bar=False)[0]
            query_embedding = np.array([query_embedding]).astype("float32")
            distances, indices = self.index.search(query_embedding, top_k)
            return [self.documents[idx] for idx in indices[0] if idx < len(self.documents)]
        except Exception as e:
            logging.error(f"Error retrieving documents: {str(e)}")
            return []