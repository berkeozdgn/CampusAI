from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

OLLAMA_BASE_URL = "http://localhost:11434/v1"
OLLAMA_API_KEY = "ollama"
OLLAMA_MODEL = "qwen2.5:3b"

EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

CHROMA_PATH = BASE_DIR / "chroma_db"
SAVED_CHATS_PATH = BASE_DIR / "saved_chats"

DEFAULT_SOURCE_COUNT = 5
MIN_SOURCE_COUNT = 2
MAX_SOURCE_COUNT = 10

SYSTEM_MESSAGE = {
    "role": "system",
    "content": (
        "Sen LocalStudyAI adlı Türkçe konuşan yardımcı bir yapay zekâ asistanısın. "
        "Her zaman yalnızca Türkçe cevap ver. "
        "Yanıtlarını açık, anlaşılır ve düzenli yaz. "
        "Kod sorularında açıklama ve örnek kod kullan. "
        "Belge kaynakları verildiğinde yalnızca sağlanan kaynaklardan yararlan. "
        "Cevap kaynaklarda yoksa bunu açıkça belirt."
    ),
}
