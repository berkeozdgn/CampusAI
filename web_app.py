from typing import Any
import streamlit as st

from ai_client import create_ai_client
from chat_storage import (
    chat_to_json,
    chat_to_text,
    create_new_chat,
    delete_chat,
    generate_chat_title,
    load_all_chats,
    load_chat,
    rename_chat,
    save_chat,
)
from config import (
    DEFAULT_SOURCE_COUNT,
    MAX_SOURCE_COUNT,
    MIN_SOURCE_COUNT,
    OLLAMA_MODEL,
    SYSTEM_MESSAGE,
)
from pdf_utils import create_collection_name
from rag import RagService

st.set_page_config(
    page_title="LocalStudyAI",
    page_icon="🤖",
    layout="centered",
)

@st.cache_resource
def get_ai_client():
    return create_ai_client()

@st.cache_resource
def get_rag_service() -> RagService:
    return RagService()

def build_session_messages(chat_data: dict[str, Any]) -> list[dict[str, str]]:
    messages = [SYSTEM_MESSAGE]
    for message in chat_data.get("messages", []):
        if message.get("role") in {"user", "assistant"}:
            messages.append(message)
    return messages

def start_new_chat() -> None:
    new_chat = create_new_chat()
    st.session_state.current_chat = new_chat
    st.session_state.messages = [SYSTEM_MESSAGE]

def open_chat(chat_id: str) -> None:
    selected_chat = load_chat(chat_id)
    if selected_chat is None:
        st.error("Sohbet dosyası açılamadı.")
        return
    st.session_state.current_chat = selected_chat
    st.session_state.messages = build_session_messages(selected_chat)

def remove_chat(chat_id: str) -> None:
    delete_chat(chat_id)
    current_chat = st.session_state.get("current_chat")
    if current_chat and current_chat.get("id") == chat_id:
        remaining = load_all_chats()
        if remaining:
            st.session_state.current_chat = remaining[0]
            st.session_state.messages = build_session_messages(remaining[0])
        else:
            start_new_chat()

def save_user_message(question: str) -> None:
    user_message = {"role": "user", "content": question}
    st.session_state.messages.append(user_message)
    current_chat = st.session_state.current_chat
    current_chat["messages"].append(user_message)
    if current_chat["title"] == "Yeni Sohbet":
        current_chat["title"] = generate_chat_title(question)
    save_chat(current_chat)

def save_assistant_message(answer: str) -> None:
    assistant_message = {"role": "assistant", "content": answer}
    st.session_state.messages.append(assistant_message)
    current_chat = st.session_state.current_chat
    current_chat["messages"].append(assistant_message)
    save_chat(current_chat)

if "pdf_info" not in st.session_state:
    st.session_state.pdf_info = None

if "current_chat" not in st.session_state:
    saved_chats = load_all_chats()
    st.session_state.current_chat = (
        saved_chats[0] if saved_chats else create_new_chat()
    )

if "messages" not in st.session_state:
    st.session_state.messages = build_session_messages(
        st.session_state.current_chat
    )

client = get_ai_client()
rag_service = get_rag_service()

st.title("🤖 LocalStudyAI")
st.caption("Tamamen yerel çalışan Türkçe yapay zekâ asistanı")

with st.sidebar:
    st.header("⚙️ Ayarlar")
    st.write(f"**Model:** {OLLAMA_MODEL}")
    st.write("**Çalışma şekli:** Yerel")

    calisma_modu = st.radio(
        "🧠 Çalışma modu",
        ["Genel Sohbet", "Belge Modu"],
        key="calisma_modu",
    )

    kaynak_sayisi = st.slider(
        "Kullanılacak kaynak parçası",
        min_value=MIN_SOURCE_COUNT,
        max_value=MAX_SOURCE_COUNT,
        value=DEFAULT_SOURCE_COUNT,
        key="kaynak_sayisi",
    )

    if st.button("➕ Yeni Sohbet", use_container_width=True):
        start_new_chat()
        st.rerun()

    st.markdown("### 💬 Kayıtlı Sohbetler")
    all_chats = load_all_chats()

    if not all_chats:
        st.caption("Henüz kayıtlı sohbet yok.")

    for chat in all_chats:
        cols = st.columns([5, 1], gap="small")
        with cols[0]:
            title = chat.get("title", "Yeni Sohbet")
            if chat["id"] == st.session_state.current_chat["id"]:
                title = f"🟢 {title}"
            if st.button(
                title,
                key=f"open_{chat['id']}",
                use_container_width=True,
            ):
                open_chat(chat["id"])
                st.rerun()

        with cols[1]:
            if st.button(
                "🗑️",
                key=f"delete_{chat['id']}",
                help="Sohbeti sil",
            ):
                remove_chat(chat["id"])
                st.rerun()

    st.divider()
    st.markdown("### ✏️ Aktif Sohbet")
    current_chat = st.session_state.current_chat

    new_title = st.text_input(
        "Sohbet başlığı",
        value=current_chat.get("title", "Yeni Sohbet"),
        key=f"rename_{current_chat['id']}",
    )

    if st.button("Başlığı Kaydet", use_container_width=True):
        if rename_chat(current_chat["id"], new_title):
            updated_chat = load_chat(current_chat["id"])
            if updated_chat:
                st.session_state.current_chat = updated_chat
            st.rerun()
        else:
            st.warning("Geçerli bir başlık yaz.")

    st.download_button(
        "📄 TXT olarak indir",
        data=chat_to_text(st.session_state.current_chat),
        file_name="localstudyai_sohbet.txt",
        mime="text/plain",
        use_container_width=True,
    )

    st.download_button(
        "🧾 JSON olarak indir",
        data=chat_to_json(st.session_state.current_chat),
        file_name="localstudyai_sohbet.json",
        mime="application/json",
        use_container_width=True,
    )

    st.divider()

    uploaded_pdfs = st.file_uploader(
        "📚 PDF dosyalarını yükle",
        type=["pdf"],
        accept_multiple_files=True,
        key="pdf_uploader",
    )

    if uploaded_pdfs:
        current_collection_name = create_collection_name(uploaded_pdfs)
        already_indexed = (
            st.session_state.pdf_info is not None
            and st.session_state.pdf_info["collection_name"]
            == current_collection_name
        )

        if not already_indexed:
            try:
                with st.spinner("PDF dosyaları hazırlanıyor ve indeksleniyor..."):
                    st.session_state.pdf_info = rag_service.index_pdfs(
                        uploaded_pdfs
                    )
                st.success("PDF dosyaları RAG sistemine eklendi.")
            except Exception as error:
                st.session_state.pdf_info = None
                st.error("PDF dosyaları hazırlanırken hata oluştu.")
                st.code(str(error))

    if st.session_state.pdf_info:
        info = st.session_state.pdf_info
        st.success("PDF dosyaları hazır")
        st.write(f"**Toplam PDF:** {info['total_file_count']}")
        st.write(f"**Toplam metin parçası:** {info['total_chunk_count']}")

        for file_info in info["files"]:
            st.markdown(
                f"**{file_info['file_name']}**  \n"
                f"Sayfa: {file_info['page_count']}  \n"
                f"Metin parçası: {file_info['chunk_count']}"
            )

        if st.button("🧹 Belgeleri Temizle", use_container_width=True):
            rag_service.delete_collection(info["collection_name"])
            st.session_state.pdf_info = None
            st.rerun()

current_title = st.session_state.current_chat.get("title", "Yeni Sohbet")
st.subheader(current_title)

for message in st.session_state.messages:
    if message["role"] == "system":
        continue
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

question = st.chat_input("Sorunu yaz...")

if question:
    if calisma_modu == "Belge Modu" and not st.session_state.pdf_info:
        st.warning("Belge Modu için önce en az bir PDF yüklemelisin.")
        st.stop()

    save_user_message(question)

    with st.chat_message("user"):
        st.markdown(question)

    api_messages = st.session_state.messages.copy()
    sources: list[dict[str, Any]] = []

    if calisma_modu == "Belge Modu" and st.session_state.pdf_info:
        try:
            sources = rag_service.search(
                question=question,
                collection_name=st.session_state.pdf_info["collection_name"],
                result_count=kaynak_sayisi,
            )

            context = "\n\n---\n\n".join(
                f"Dosya: {source['file_name']}\n"
                f"Sayfa: {source['page']}\n"
                f"İçerik:\n{source['text']}"
                for source in sources
            )

            api_messages.insert(
                1,
                {
                    "role": "system",
                    "content": (
                        "Aşağıda yüklenen PDF dosyalarından soruyla en alakalı "
                        "bölümler vardır. Cevabını yalnızca bu bölümlere dayanarak "
                        "oluştur. Bilgi yoksa PDF dosyalarında bulunamadığını söyle. "
                        "Cevabının sonunda dosya ve sayfa numaralarını yaz.\n\n"
                        f"{context}"
                    ),
                },
            )
        except Exception as error:
            st.warning("PDF dosyalarında arama yapılamadı.")
            st.code(str(error))

    with st.chat_message("assistant"):
        with st.spinner("Yapay zekâ düşünüyor..."):
            try:
                response = client.chat.completions.create(
                    model=OLLAMA_MODEL,
                    messages=api_messages,
                )
                answer = response.choices[0].message.content
                st.markdown(answer)

                if sources:
                    with st.expander("📚 Kullanılan PDF kaynakları"):
                        for index, source in enumerate(sources, start=1):
                            st.markdown(f"**Kaynak {index}**")
                            st.write(f"Dosya: {source['file_name']}")
                            st.write(f"Sayfa: {source['page']}")
                            st.write(source["text"])
                            st.divider()

                save_assistant_message(answer)

            except Exception as error:
                st.error(
                    "Yapay zekâya bağlanırken hata oluştu. "
                    "Ollama'nın çalıştığından emin ol."
                )
                st.code(str(error))
