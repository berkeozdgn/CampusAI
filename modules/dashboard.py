from pathlib import Path
from typing import Any

import streamlit as st


def count_pdf_files(pdf_root: Path) -> int:
    """Tüm ders klasörlerinde kayıtlı PDF sayısını döndürür."""
    if not pdf_root.exists():
        return 0

    return sum(
        1
        for file_path in pdf_root.rglob("*")
        if file_path.is_file()
        and file_path.suffix.lower() == ".pdf"
    )


def count_subjects(pdf_root: Path) -> int:
    """Oluşturulan ders klasörlerinin sayısını döndürür."""
    if not pdf_root.exists():
        return 0

    return sum(
        1
        for item in pdf_root.iterdir()
        if item.is_dir()
    )


def count_user_questions(
    chats: list[dict[str, Any]],
) -> int:
    """Kullanıcının toplam soru sayısını hesaplar."""
    total = 0

    for chat in chats:
        for message in chat.get("messages", []):
            if message.get("role") == "user":
                total += 1

    return total


def get_recent_chats(
    chats: list[dict[str, Any]],
    limit: int = 5,
) -> list[dict[str, Any]]:
    """En güncel sohbetleri döndürür."""
    sorted_chats = sorted(
        chats,
        key=lambda chat: chat.get(
            "updated_at",
            chat.get("created_at", ""),
        ),
        reverse=True,
    )

    return sorted_chats[:limit]


def render_stat_card(
    icon: str,
    title: str,
    value: str | int,
    description: str,
) -> None:
    """HTML tabanlı istatistik kartı oluşturur."""
    st.markdown(
        f"""
        <div class="dashboard-stat-card">
            <div class="dashboard-stat-icon">{icon}</div>

            <div class="dashboard-stat-content">
                <p class="dashboard-stat-title">
                    {title}
                </p>

                <h3 class="dashboard-stat-value">
                    {value}
                </h3>

                <p class="dashboard-stat-description">
                    {description}
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_dashboard(
    active_subject: str,
    model_name: str,
    chats: list[dict[str, Any]],
    pdf_root: Path,
) -> str | None:
    """
    CampusAI Dashboard ekranını oluşturur.

    Döndürdüğü değerler:
    - new_chat
    - open_chat
    - summary
    - quiz
    - planner
    - None
    """

    subject_count = count_subjects(pdf_root)
    pdf_count = count_pdf_files(pdf_root)
    chat_count = len(chats)
    question_count = count_user_questions(chats)
    recent_chats = get_recent_chats(chats)

    st.markdown(
        """
        <div class="dashboard-hero">
            <div>
                <p class="dashboard-eyebrow">
                    YEREL YAPAY ZEKÂ ÇALIŞMA ALANI
                </p>

                <h2>
                    Tekrar hoş geldin 👋
                </h2>

                <p>
                    Ders belgelerini düzenle, CampusAI ile konuş
                    ve çalışma materyallerini tek yerden oluştur.
                </p>
            </div>

            <div class="dashboard-hero-badge">
                🔒 Tamamen Yerel
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 📊 Genel Bakış")

    first_row = st.columns(4, gap="medium")

    with first_row[0]:
        render_stat_card(
            icon="📚",
            title="Toplam Ders",
            value=subject_count,
            description="Oluşturulan çalışma alanı",
        )

    with first_row[1]:
        render_stat_card(
            icon="📄",
            title="Toplam PDF",
            value=pdf_count,
            description="Derslere eklenen belge",
        )

    with first_row[2]:
        render_stat_card(
            icon="💬",
            title="Sohbet",
            value=chat_count,
            description="Kaydedilmiş konuşma",
        )

    with first_row[3]:
        render_stat_card(
            icon="❓",
            title="Toplam Soru",
            value=question_count,
            description="CampusAI'a sorulan soru",
        )

    st.markdown("### 🎯 Aktif Çalışma Alanı")

    active_columns = st.columns(2, gap="medium")

    with active_columns[0]:
        st.markdown(
            f"""
            <div class="dashboard-info-card">
                <div class="dashboard-info-icon">📘</div>

                <div>
                    <p class="dashboard-info-label">
                        Aktif Ders
                    </p>

                    <h3>
                        {active_subject}
                    </h3>

                    <p>
                        Yüklenen belgeler bu derse kaydedilir.
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with active_columns[1]:
        st.markdown(
            f"""
            <div class="dashboard-info-card">
                <div class="dashboard-info-icon">🤖</div>

                <div>
                    <p class="dashboard-info-label">
                        Yerel Model
                    </p>

                    <h3>
                        {model_name}
                    </h3>

                    <p>
                        Verilerin cihazından dışarı gönderilmez.
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### ⚡ Hızlı İşlemler")

    action_columns = st.columns(4, gap="small")

    with action_columns[0]:
        if st.button(
            "💬 Yeni Sohbet",
            key="dashboard_new_chat",
            use_container_width=True,
        ):
            return "new_chat"

    with action_columns[1]:
        if st.button(
            "📖 Özet Oluştur",
            key="dashboard_summary",
            use_container_width=True,
        ):
            return "summary"

    with action_columns[2]:
        if st.button(
            "📝 Quiz Oluştur",
            key="dashboard_quiz",
            use_container_width=True,
        ):
            return "quiz"

    with action_columns[3]:
        if st.button(
            "📅 Çalışma Planı",
            key="dashboard_planner",
            use_container_width=True,
        ):
            return "planner"

    st.markdown("### 🕘 Son Sohbetler")

    if not recent_chats:
        st.info(
            "Henüz kayıtlı sohbet bulunmuyor. "
            "Yeni bir sohbet başlatarak CampusAI'ı kullanabilirsin."
        )

    else:
        for chat in recent_chats:
            title = chat.get("title", "Yeni Sohbet")
            message_count = len(
                [
                    message
                    for message in chat.get("messages", [])
                    if message.get("role")
                    in {"user", "assistant"}
                ]
            )

            columns = st.columns(
                [6, 2, 2],
                gap="small",
            )

            with columns[0]:
                st.markdown(
                    f"""
                    <div class="recent-chat-title">
                        💬 {title}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with columns[1]:
                st.caption(
                    f"{message_count} mesaj"
                )

            with columns[2]:
                if st.button(
                    "Aç",
                    key=(
                        "dashboard_open_"
                        f"{chat['id']}"
                    ),
                    use_container_width=True,
                ):
                    st.session_state.dashboard_chat_id = (
                        chat["id"]
                    )
                    return "open_chat"

    st.markdown("---")

    st.caption(
        "CampusAI • Yerel yapay zekâ • "
        "Gizlilik odaklı çalışma asistanı"
    )

    return None