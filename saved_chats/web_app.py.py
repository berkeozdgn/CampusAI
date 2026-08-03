from pathlib import Path
from typing import Any
import re

import streamlit as st

from config import (
    DEFAULT_SOURCE_COUNT,
    MAX_SOURCE_COUNT,
    MIN_SOURCE_COUNT,
    OLLAMA_MODEL,
    SYSTEM_MESSAGE,
)
from modules.ai_client import create_ai_client
from modules.chat_storage import (
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
from modules.dashboard import render_dashboard
from modules.pdf_utils import create_collection_name
from modules.rag import RagService
from modules.subject_manager import (
    create_subject,
    get_subject_path,
    get_subjects,
)


st.set_page_config(
    page_title="CampusAI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_css() -> None:
    css_path = Path("assets/styles.css")
    if css_path.exists():
        st.markdown(
            f"<style>{css_path.read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True,
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
            messages.append(
                {
                    "role": message["role"],
                    "content": message.get("content", ""),
                }
            )
    return messages


def start_new_chat() -> None:
    chat = create_new_chat()
    st.session_state.current_chat = chat
    st.session_state.messages = [SYSTEM_MESSAGE]


def open_chat(chat_id: str) -> None:
    chat = load_chat(chat_id)
    if chat is None:
        st.error("Sohbet açılamadı.")
        return
    st.session_state.current_chat = chat
    st.session_state.messages = build_session_messages(chat)


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
    message = {"role": "user", "content": question}
    st.session_state.messages.append(message)

    chat = st.session_state.current_chat
    chat.setdefault("messages", []).append(message)

    if chat.get("title") == "Yeni Sohbet":
        chat["title"] = generate_chat_title(question)

    save_chat(chat)


def save_assistant_message(answer: str) -> None:
    message = {"role": "assistant", "content": answer}
    st.session_state.messages.append(message)

    chat = st.session_state.current_chat
    chat.setdefault("messages", []).append(message)
    save_chat(chat)


def clean_subject_name(subject_name: str) -> str:
    cleaned = " ".join(subject_name.strip().split())
    cleaned = re.sub(r'[<>:"/\\|?*]', "", cleaned)
    return cleaned[:60]


def save_uploaded_pdfs(uploaded_files: list[Any], subject_name: str) -> None:
    subject_path = Path(get_subject_path(subject_name))
    subject_path.mkdir(parents=True, exist_ok=True)

    for uploaded_file in uploaded_files:
        destination = subject_path / Path(uploaded_file.name).name
        destination.write_bytes(uploaded_file.getvalue())


def create_rag_message(
    question: str,
    sources: list[dict[str, Any]],
    subject_name: str,
) -> dict[str, str]:
    context = "\n\n---\n\n".join(
        (
            f"Ders: {subject_name}\n"
            f"Dosya: {source['file_name']}\n"
            f"Sayfa: {source['page']}\n"
            f"İçerik:\n{source['text']}"
        )
        for source in sources
    )

    return {
        "role": "system",
        "content": (
            f"Seçilen ders: {subject_name}\n\n"
            "Aşağıdaki belge parçalarını kullanarak cevap ver. "
            "Yeterli bilgi yoksa açıkça belirt ve bilgi uydurma. "
            "Cevabın sonunda dosya ve sayfa numarasını yaz.\n\n"
            f"Kullanıcı sorusu:\n{question}\n\n"
            f"Kaynaklar:\n{context}"
        ),
    }


load_css()
client = get_ai_client()
rag_service = get_rag_service()


if "pdf_info" not in st.session_state:
    st.session_state.pdf_info = None

if "active_subject" not in st.session_state:
    subjects = get_subjects()
    if not subjects:
        create_subject("Genel")
        subjects = get_subjects()
    st.session_state.active_subject = subjects[0]

if "current_chat" not in st.session_state:
    chats = load_all_chats()
    st.session_state.current_chat = chats[0] if chats else create_new_chat()

if "messages" not in st.session_state:
    st.session_state.messages = build_session_messages(
        st.session_state.current_chat
    )

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"


with st.sidebar:
    st.title("🎓 CampusAI")
    st.caption("Yerel ve gizlilik odaklı çalışma asistanı")

    st.radio(
        "Sayfa",
        options=["Dashboard", "Sohbet"],
        key="page",
    )

    st.divider()
    st.subheader("📚 Ders Yönetimi")

    subjects = get_subjects()
    if not subjects:
        create_subject("Genel")
        subjects = get_subjects()

    current_subject = st.session_state.active_subject
    if current_subject not in subjects:
        current_subject = subjects[0]

    selected_subject = st.selectbox(
        "Aktif ders",
        options=subjects,
        index=subjects.index(current_subject),
        key="subject_selector",
    )

    if selected_subject != st.session_state.active_subject:
        st.session_state.active_subject = selected_subject
        st.session_state.pdf_info = None
        st.rerun()

    with st.expander("➕ Yeni ders oluştur"):
        new_subject = st.text_input(
            "Ders adı",
            placeholder="Örnek: Veri Yapıları",
            key="new_subject_name",
        )

        if st.button("Dersi Oluştur", use_container_width=True):
            cleaned = clean_subject_name(new_subject)

            if not cleaned:
                st.warning("Geçerli bir ders adı yaz.")
            elif cleaned in get_subjects():
                st.warning("Bu ders zaten mevcut.")
            else:
                create_subject(cleaned)
                st.session_state.active_subject = cleaned
                st.session_state.pdf_info = None
                st.rerun()

    st.info(f"Aktif ders: **{st.session_state.active_subject}**")

    st.divider()
    st.subheader("⚙️ Ayarlar")

    st.write(f"**Model:** {OLLAMA_MODEL}")
    st.write("**Çalışma şekli:** Yerel")

    calisma_modu = st.radio(
        "🧠 Çalışma modu",
        options=["Genel Sohbet", "Belge Modu"],
        key="calisma_modu",
    )

    kaynak_sayisi = st.slider(
        "Kullanılacak kaynak parçası",
        min_value=MIN_SOURCE_COUNT,
        max_value=MAX_SOURCE_COUNT,
        value=DEFAULT_SOURCE_COUNT,
        key="kaynak_sayisi",
    )

    st.divider()

    if st.button("➕ Yeni Sohbet", use_container_width=True):
        start_new_chat()
        st.session_state.page = "Sohbet"
        st.rerun()

    st.subheader("💬 Kayıtlı Sohbetler")

    for chat in load_all_chats():
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
                st.session_state.page = "Sohbet"
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
    st.subheader("✏️ Aktif Sohbet")

    current_chat = st.session_state.current_chat

    new_title = st.text_input(
        "Sohbet başlığı",
        value=current_chat.get("title", "Yeni Sohbet"),
        key=f"rename_{current_chat['id']}",
    )

    if st.button("Başlığı Kaydet", use_container_width=True):
        if rename_chat(current_chat["id"], new_title):
            updated = load_chat(current_chat["id"])
            if updated:
                st.session_state.current_chat = updated
            st.rerun()
        else:
            st.warning("Geçerli bir başlık yaz.")

    st.download_button(
        "📄 TXT olarak indir",
        data=chat_to_text(st.session_state.current_chat),
        file_name="campusai_sohbet.txt",
        mime="text/plain",
        use_container_width=True,
    )

    st.download_button(
        "🧾 JSON olarak indir",
        data=chat_to_json(st.session_state.current_chat),
        file_name="campusai_sohbet.json",
        mime="application/json",
        use_container_width=True,
    )

    st.divider()
    st.subheader("📄 Ders Belgeleri")

    uploaded_pdfs = st.file_uploader(
        "PDF dosyalarını yükle",
        type=["pdf"],
        accept_multiple_files=True,
        key=f"pdf_uploader_{st.session_state.active_subject}",
    )

    if uploaded_pdfs:
        collection_name = create_collection_name(uploaded_pdfs)

        already_indexed = (
            st.session_state.pdf_info is not None
            and st.session_state.pdf_info["collection_name"] == collection_name
        )

        if not already_indexed:
            try:
                save_uploaded_pdfs(
                    uploaded_pdfs,
                    st.session_state.active_subject,
                )

                with st.spinner(
                    "PDF dosyaları hazırlanıyor ve indeksleniyor..."
                ):
                    info = rag_service.index_pdfs(uploaded_pdfs)

                info["subject"] = st.session_state.active_subject
                st.session_state.pdf_info = info
                st.success("PDF dosyaları hazırlandı.")

            except Exception as error:
                st.session_state.pdf_info = None
                st.error("PDF dosyaları hazırlanırken hata oluştu.")
                st.code(str(error))

    if st.session_state.pdf_info:
        info = st.session_state.pdf_info

        st.success("Ders belgeleri hazır")
        st.write(f"**Ders:** {info.get('subject', '-')}")
        st.write(f"**Toplam PDF:** {info['total_file_count']}")
        st.write(
            f"**Toplam metin parçası:** {info['total_chunk_count']}"
        )

        if st.button("🧹 Belgeleri Temizle", use_container_width=True):
            rag_service.delete_collection(info["collection_name"])
            st.session_state.pdf_info = None
            st.rerun()


st.title("🎓 CampusAI")
st.caption("Tamamen yerel çalışan akıllı üniversite asistanı")


if st.session_state.page == "Dashboard":
    render_dashboard(
        active_subject=st.session_state.active_subject,
        model_name=OLLAMA_MODEL,
        chats=load_all_chats(),
        pdf_root=Path("data/pdfs"),
    )

    st.markdown("---")
    st.markdown("### 💡 Başlamak için")
    st.write(
        "Sol menüden ders seçebilir, PDF yükleyebilir ve "
        "Sohbet sayfasına geçebilirsin."
    )

    if st.button("💬 Sohbete Git", use_container_width=True):
        st.session_state.page = "Sohbet"
        st.rerun()

else:
    current_title = st.session_state.current_chat.get(
        "title",
        "Yeni Sohbet",
    )

    st.subheader(current_title)
    st.caption(f"📚 Aktif ders: {st.session_state.active_subject}")

    for message in st.session_state.messages:
        if message.get("role") == "system":
            continue

        with st.chat_message(message["role"]):
            st.markdown(message.get("content", ""))

    question = st.chat_input("Sorunu yaz...")

    if question:
        if calisma_modu == "Belge Modu" and not st.session_state.pdf_info:
            st.warning(
                "Belge Modu için önce aktif derse en az bir PDF yüklemelisin."
            )
            st.stop()

        save_user_message(question)

        with st.chat_message("user"):
            st.markdown(question)

        api_messages = st.session_state.messages.copy()
        sources: list[dict[str, Any]] = []

        if calisma_modu == "Belge Modu":
            try:
                sources = rag_service.search(
                    question=question,
                    collection_name=st.session_state.pdf_info["collection_name"],
                    result_count=kaynak_sayisi,
                )

                api_messages.insert(
                    1,
                    create_rag_message(
                        question=question,
                        sources=sources,
                        subject_name=st.session_state.active_subject,
                    ),
                )

            except Exception as error:
                st.warning("Ders belgelerinde arama yapılamadı.")
                st.code(str(error))

        with st.chat_message("assistant"):
            with st.spinner("CampusAI düşünüyor..."):
                try:
                    response = client.chat.completions.create(
                        model=OLLAMA_MODEL,
                        messages=api_messages,
                    )

                    answer = (
                        response.choices[0].message.content
                        or "Model boş bir cevap döndürdü."
                    )

                    st.markdown(answer)

                    if sources:
                        with st.expander("📚 Kullanılan belge kaynakları"):
                            for index, source in enumerate(sources, start=1):
                                st.markdown(f"### Kaynak {index}")
                                st.write(f"**Dosya:** {source['file_name']}")
                                st.write(f"**Sayfa:** {source['page']}")
                                st.write(source["text"])
                                st.divider()

                    save_assistant_message(answer)

                except Exception as error:
                    st.error(
                        "Yapay zekâya bağlanırken hata oluştu. "
                        "Ollama'nın çalıştığından emin ol."
                    )
                    st.code(str(error))
