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

from modules.pdf_utils import create_collection_name
from modules.rag import RagService

from modules.subject_manager import (
    create_subject,
    get_subject_path,
    get_subjects,
)


# ---------------------------------------------------------
# SAYFA AYARLARI
# ---------------------------------------------------------

st.set_page_config(
    page_title="CampusAI",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------
# CSS
# ---------------------------------------------------------

def load_css() -> None:
    css_path = Path("assets/styles.css")

    if css_path.exists():
        css_content = css_path.read_text(
            encoding="utf-8"
        )

        st.markdown(
            f"<style>{css_content}</style>",
            unsafe_allow_html=True,
        )


load_css()


# ---------------------------------------------------------
# SERVİSLER
# ---------------------------------------------------------

@st.cache_resource
def get_ai_client():
    return create_ai_client()


@st.cache_resource
def get_rag_service() -> RagService:
    return RagService()


client = get_ai_client()
rag_service = get_rag_service()


# ---------------------------------------------------------
# YARDIMCI FONKSİYONLAR
# ---------------------------------------------------------

def build_session_messages(
    chat_data: dict[str, Any],
) -> list[dict[str, str]]:
    messages = [SYSTEM_MESSAGE]

    for message in chat_data.get("messages", []):
        role = message.get("role")

        if role in {"user", "assistant"}:
            messages.append(
                {
                    "role": role,
                    "content": message.get(
                        "content",
                        "",
                    ),
                }
            )

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

    st.session_state.messages = (
        build_session_messages(selected_chat)
    )


def remove_chat(chat_id: str) -> None:
    delete_chat(chat_id)

    current_chat = st.session_state.get(
        "current_chat"
    )

    if (
        current_chat
        and current_chat.get("id") == chat_id
    ):
        remaining_chats = load_all_chats()

        if remaining_chats:
            first_chat = remaining_chats[0]

            st.session_state.current_chat = (
                first_chat
            )

            st.session_state.messages = (
                build_session_messages(
                    first_chat
                )
            )

        else:
            start_new_chat()


def save_user_message(question: str) -> None:
    user_message = {
        "role": "user",
        "content": question,
    }

    st.session_state.messages.append(
        user_message
    )

    current_chat = (
        st.session_state.current_chat
    )

    current_chat.setdefault(
        "messages",
        [],
    )

    current_chat["messages"].append(
        user_message
    )

    if (
        current_chat.get("title")
        == "Yeni Sohbet"
    ):
        current_chat["title"] = (
            generate_chat_title(question)
        )

    save_chat(current_chat)


def save_assistant_message(
    answer: str,
) -> None:
    assistant_message = {
        "role": "assistant",
        "content": answer,
    }

    st.session_state.messages.append(
        assistant_message
    )

    current_chat = (
        st.session_state.current_chat
    )

    current_chat.setdefault(
        "messages",
        [],
    )

    current_chat["messages"].append(
        assistant_message
    )

    save_chat(current_chat)


def clean_subject_name(
    subject_name: str,
) -> str:
    cleaned_name = " ".join(
        subject_name.strip().split()
    )

    cleaned_name = re.sub(
        r'[<>:"/\\|?*]',
        "",
        cleaned_name,
    )

    return cleaned_name[:60]


def save_uploaded_pdfs(
    uploaded_files: list[Any],
    subject_name: str,
) -> None:
    subject_path = Path(
        get_subject_path(subject_name)
    )

    subject_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    for uploaded_file in uploaded_files:
        safe_file_name = Path(
            uploaded_file.name
        ).name

        destination = (
            subject_path / safe_file_name
        )

        destination.write_bytes(
            uploaded_file.getvalue()
        )


def create_rag_messages(
    question: str,
    sources: list[dict[str, Any]],
    subject_name: str,
) -> dict[str, str]:
    context_parts = []

    for source in sources:
        context_parts.append(
            f"Ders: {subject_name}\n"
            f"Dosya: {source['file_name']}\n"
            f"Sayfa: {source['page']}\n"
            f"İçerik:\n{source['text']}"
        )

    context = "\n\n---\n\n".join(
        context_parts
    )

    return {
        "role": "system",
        "content": (
            f"Kullanıcının seçtiği ders: "
            f"{subject_name}\n\n"
            "Aşağıda yüklenen ders belgelerinden "
            "soruyla en alakalı bölümler bulunmaktadır. "
            "Cevabını yalnızca bu bölümlere dayanarak oluştur. "
            "Belgelerde yeterli bilgi yoksa bunu açıkça söyle. "
            "Bilgi uydurma. "
            "Cevabının sonunda kullandığın dosya ve "
            "sayfa numaralarını belirt.\n\n"
            f"Kullanıcının sorusu:\n{question}\n\n"
            f"Belge kaynakları:\n{context}"
        ),
    }


# ---------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------

if "pdf_info" not in st.session_state:
    st.session_state.pdf_info = None


if "active_subject" not in st.session_state:
    subjects = get_subjects()

    if subjects:
        st.session_state.active_subject = (
            subjects[0]
        )
    else:
        create_subject("Genel")
        st.session_state.active_subject = (
            "Genel"
        )


if "current_chat" not in st.session_state:
    saved_chats = load_all_chats()

    if saved_chats:
        st.session_state.current_chat = (
            saved_chats[0]
        )
    else:
        st.session_state.current_chat = (
            create_new_chat()
        )


if "messages" not in st.session_state:
    st.session_state.messages = (
        build_session_messages(
            st.session_state.current_chat
        )
    )


# ---------------------------------------------------------
# ANA BAŞLIK
# ---------------------------------------------------------

st.title("🎓 CampusAI")

st.caption(
    "Tamamen yerel çalışan akıllı "
    "üniversite ve ders çalışma asistanı"
)


# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------

with st.sidebar:
    st.header("🎓 CampusAI")

    st.caption(
        "Yerel ve gizlilik odaklı "
        "çalışma asistanı"
    )

    st.divider()

    # -----------------------------------------------------
    # DERS YÖNETİMİ
    # -----------------------------------------------------

    st.subheader("📚 Ders Yönetimi")

    subjects = get_subjects()

    if not subjects:
        create_subject("Genel")
        subjects = get_subjects()

    current_subject = (
        st.session_state.active_subject
    )

    if current_subject not in subjects:
        current_subject = subjects[0]

    selected_subject = st.selectbox(
        "Aktif ders",
        options=subjects,
        index=subjects.index(
            current_subject
        ),
        key="subject_selector",
    )

    if (
        selected_subject
        != st.session_state.active_subject
    ):
        st.session_state.active_subject = (
            selected_subject
        )

        st.session_state.pdf_info = None

        st.rerun()

    with st.expander("➕ Yeni ders oluştur"):
        new_subject_name = st.text_input(
            "Ders adı",
            placeholder=(
                "Örnek: Veri Yapıları"
            ),
            key="new_subject_name",
        )

        if st.button(
            "Dersi Oluştur",
            use_container_width=True,
        ):
            cleaned_subject_name = (
                clean_subject_name(
                    new_subject_name
                )
            )

            if not cleaned_subject_name:
                st.warning(
                    "Geçerli bir ders adı yaz."
                )

            elif (
                cleaned_subject_name
                in get_subjects()
            ):
                st.warning(
                    "Bu ders zaten mevcut."
                )

            else:
                create_subject(
                    cleaned_subject_name
                )

                st.session_state.active_subject = (
                    cleaned_subject_name
                )

                st.session_state.pdf_info = None

                st.success(
                    f"{cleaned_subject_name} "
                    "dersi oluşturuldu."
                )

                st.rerun()

    st.info(
        f"Aktif ders: "
        f"**{st.session_state.active_subject}**"
    )

    st.divider()

    # -----------------------------------------------------
    # MODEL VE MOD
    # -----------------------------------------------------

    st.subheader("⚙️ Ayarlar")

    st.write(
        f"**Model:** {OLLAMA_MODEL}"
    )

    st.write(
        "**Çalışma şekli:** Yerel"
    )

    calisma_modu = st.radio(
        "🧠 Çalışma modu",
        options=[
            "Genel Sohbet",
            "Belge Modu",
        ],
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

    # -----------------------------------------------------
    # SOHBET YÖNETİMİ
    # -----------------------------------------------------

    if st.button(
        "➕ Yeni Sohbet",
        use_container_width=True,
    ):
        start_new_chat()
        st.rerun()

    st.subheader("💬 Kayıtlı Sohbetler")

    all_chats = load_all_chats()

    if not all_chats:
        st.caption(
            "Henüz kayıtlı sohbet yok."
        )

    for chat in all_chats:
        columns = st.columns(
            [5, 1],
            gap="small",
        )

        with columns[0]:
            title = chat.get(
                "title",
                "Yeni Sohbet",
            )

            if (
                chat["id"]
                == st.session_state
                .current_chat["id"]
            ):
                title = f"🟢 {title}"

            if st.button(
                title,
                key=f"open_{chat['id']}",
                use_container_width=True,
            ):
                open_chat(chat["id"])
                st.rerun()

        with columns[1]:
            if st.button(
                "🗑️",
                key=f"delete_{chat['id']}",
                help="Sohbeti sil",
            ):
                remove_chat(chat["id"])
                st.rerun()

    st.divider()

    # -----------------------------------------------------
    # AKTİF SOHBET
    # -----------------------------------------------------

    st.subheader("✏️ Aktif Sohbet")

    current_chat = (
        st.session_state.current_chat
    )

    new_title = st.text_input(
        "Sohbet başlığı",
        value=current_chat.get(
            "title",
            "Yeni Sohbet",
        ),
        key=(
            f"rename_"
            f"{current_chat['id']}"
        ),
    )

    if st.button(
        "Başlığı Kaydet",
        use_container_width=True,
    ):
        success = rename_chat(
            current_chat["id"],
            new_title,
        )

        if success:
            updated_chat = load_chat(
                current_chat["id"]
            )

            if updated_chat:
                st.session_state.current_chat = (
                    updated_chat
                )

            st.rerun()

        else:
            st.warning(
                "Geçerli bir başlık yaz."
            )

    st.download_button(
        label="📄 TXT olarak indir",
        data=chat_to_text(
            st.session_state.current_chat
        ),
        file_name=(
            "campusai_sohbet.txt"
        ),
        mime="text/plain",
        use_container_width=True,
    )

    st.download_button(
        label="🧾 JSON olarak indir",
        data=chat_to_json(
            st.session_state.current_chat
        ),
        file_name=(
            "campusai_sohbet.json"
        ),
        mime="application/json",
        use_container_width=True,
    )

    st.divider()

    # -----------------------------------------------------
    # PDF YÜKLEME
    # -----------------------------------------------------

    st.subheader("📄 Ders Belgeleri")

    st.caption(
        "Yüklenen PDF dosyaları aktif "
        "dersin klasörüne kaydedilir."
    )

    uploaded_pdfs = st.file_uploader(
        "PDF dosyalarını yükle",
        type=["pdf"],
        accept_multiple_files=True,
        key=(
            "pdf_uploader_"
            f"{st.session_state.active_subject}"
        ),
    )

    if uploaded_pdfs:
        current_collection_name = (
            create_collection_name(
                uploaded_pdfs
            )
        )

        already_indexed = (
            st.session_state.pdf_info
            is not None
            and st.session_state.pdf_info[
                "collection_name"
            ]
            == current_collection_name
        )

        if not already_indexed:
            try:
                save_uploaded_pdfs(
                    uploaded_pdfs,
                    st.session_state
                    .active_subject,
                )

                with st.spinner(
                    "PDF dosyaları hazırlanıyor "
                    "ve indeksleniyor..."
                ):
                    pdf_info = (
                        rag_service.index_pdfs(
                            uploaded_pdfs
                        )
                    )

                pdf_info["subject"] = (
                    st.session_state
                    .active_subject
                )

                st.session_state.pdf_info = (
                    pdf_info
                )

                st.success(
                    "PDF dosyaları hazırlandı."
                )

            except Exception as error:
                st.session_state.pdf_info = (
                    None
                )

                st.error(
                    "PDF dosyaları hazırlanırken "
                    "hata oluştu."
                )

                st.code(str(error))

    if st.session_state.pdf_info:
        info = st.session_state.pdf_info

        st.success(
            "Ders belgeleri hazır"
        )

        st.write(
            f"**Ders:** "
            f"{info.get('subject', '-')}"
        )

        st.write(
            f"**Toplam PDF:** "
            f"{info['total_file_count']}"
        )

        st.write(
            f"**Toplam metin parçası:** "
            f"{info['total_chunk_count']}"
        )

        for file_info in info["files"]:
            st.markdown(
                f"**{file_info['file_name']}**  \n"
                f"Sayfa: "
                f"{file_info['page_count']}  \n"
                f"Metin parçası: "
                f"{file_info['chunk_count']}"
            )

        if st.button(
            "🧹 Belgeleri Temizle",
            use_container_width=True,
        ):
            rag_service.delete_collection(
                info["collection_name"]
            )

            st.session_state.pdf_info = (
                None
            )

            st.rerun()


# ---------------------------------------------------------
# ANA SOHBET EKRANI
# ---------------------------------------------------------

current_title = (
    st.session_state.current_chat.get(
        "title",
        "Yeni Sohbet",
    )
)

st.subheader(current_title)

st.caption(
    f"📚 Aktif ders: "
    f"{st.session_state.active_subject}"
)


for message in st.session_state.messages:
    if message.get("role") == "system":
        continue

    with st.chat_message(
        message["role"]
    ):
        st.markdown(
            message.get(
                "content",
                "",
            )
        )


question = st.chat_input(
    "Sorunu yaz..."
)


# ---------------------------------------------------------
# SORU CEVAPLAMA
# ---------------------------------------------------------

if question:
    if (
        calisma_modu == "Belge Modu"
        and not st.session_state.pdf_info
    ):
        st.warning(
            "Belge Modu için önce aktif "
            "derse en az bir PDF yüklemelisin."
        )

        st.stop()

    save_user_message(question)

    with st.chat_message("user"):
        st.markdown(question)

    api_messages = (
        st.session_state.messages.copy()
    )

    sources: list[
        dict[str, Any]
    ] = []

    if (
        calisma_modu == "Belge Modu"
        and st.session_state.pdf_info
    ):
        try:
            sources = rag_service.search(
                question=question,
                collection_name=(
                    st.session_state
                    .pdf_info[
                        "collection_name"
                    ]
                ),
                result_count=kaynak_sayisi,
            )

            rag_system_message = (
                create_rag_messages(
                    question=question,
                    sources=sources,
                    subject_name=(
                        st.session_state
                        .active_subject
                    ),
                )
            )

            api_messages.insert(
                1,
                rag_system_message,
            )

        except Exception as error:
            st.warning(
                "Ders belgelerinde arama "
                "yapılamadı."
            )

            st.code(str(error))

    with st.chat_message("assistant"):
        with st.spinner(
            "CampusAI düşünüyor..."
        ):
            try:
                response = (
                    client.chat
                    .completions
                    .create(
                        model=OLLAMA_MODEL,
                        messages=api_messages,
                    )
                )

                answer = (
                    response
                    .choices[0]
                    .message
                    .content
                )

                if not answer:
                    answer = (
                        "Model boş bir cevap "
                        "döndürdü."
                    )

                st.markdown(answer)

                if sources:
                    with st.expander(
                        "📚 Kullanılan belge "
                        "kaynakları"
                    ):
                        for (
                            index,
                            source,
                        ) in enumerate(
                            sources,
                            start=1,
                        ):
                            st.markdown(
                                f"### Kaynak "
                                f"{index}"
                            )

                            st.write(
                                f"**Dosya:** "
                                f"{source['file_name']}"
                            )

                            st.write(
                                f"**Sayfa:** "
                                f"{source['page']}"
                            )

                            st.write(
                                source["text"]
                            )

                            st.divider()

                save_assistant_message(
                    answer
                )

            except Exception as error:
                st.error(
                    "Yapay zekâya bağlanırken "
                    "hata oluştu. Ollama'nın "
                    "çalıştığından emin ol."
                )

                st.code(str(error))