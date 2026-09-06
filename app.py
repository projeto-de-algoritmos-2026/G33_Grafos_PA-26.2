import json

import streamlit as st
from pyvis.network import Network

from skillroute.data_loader import DataLoader
from skillroute.matching import (
    calculate_career_path,
    get_context_breakdown,
    run_profile_dijkstra,
)
from skillroute.models import (
    CandidateProfile,
    CandidateSkill,
    Job,
    JobRecommendation,
    MatchClassification,
    ProficiencyLevel,
    RequirementKind,
    RoleTaxonomy,
    Seniority,
    SkillDefinition,
)
from skillroute.recommendation import recommend_jobs

# ============================================================================
# Custom CSS Theming
# ============================================================================

CUSTOM_CSS = """
<style>
/* --- Google Fonts --- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* --- Global --- */
.stApp {
    font-family: 'Inter', sans-serif;
}

/* --- Sidebar --- */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
}
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown li,
section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 {
    color: #e2e8f0 !important;
}
section[data-testid="stSidebar"] .stCaption p {
    color: #94a3b8 !important;
}

/* --- Metric cards --- */
[data-testid="stMetric"] {
    background: #ffffff;
    border: 1.5px solid #cbd5e1;
    border-radius: 12px;
    padding: 14px 18px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.04);
}
[data-testid="stMetric"] label {
    color: #334155 !important;
    font-weight: 700 !important;
    font-size: 0.82rem !important;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #0f172a !important;
    font-weight: 800 !important;
    font-size: 1.5rem !important;
}

/* --- Recommendation cards --- */
.rec-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03);
    transition: box-shadow 0.2s ease, transform 0.2s ease;
}
.rec-card:hover {
    box-shadow: 0 4px 16px rgba(0,0,0,0.08), 0 8px 24px rgba(0,0,0,0.05);
    transform: translateY(-1px);
}

/* --- Score badge --- */
.score-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 1.8rem;
    font-weight: 800;
    border-radius: 16px;
    padding: 8px 18px;
    line-height: 1;
}

/* --- Classification chips --- */
.classification-chip {
    display: inline-block;
    padding: 5px 14px;
    border-radius: 20px;
    font-weight: 600;
    font-size: 0.78rem;
    letter-spacing: 0.02em;
    color: #fff;
}

/* --- Status indicators --- */
.status-atendido { color: #16a34a; font-weight: 600; }
.status-parcial { color: #d97706; font-weight: 600; }
.status-ausente { color: #dc2626; font-weight: 600; }
.status-inalcancavel { color: #6b7280; font-weight: 600; }

/* --- Step cards --- */
.step-card {
    background: #f8fafc;
    border-left: 4px solid #3b82f6;
    border-radius: 0 12px 12px 0;
    padding: 16px 20px;
    margin-bottom: 12px;
}
.step-card.satisfied {
    border-left-color: #16a34a;
    background: #f0fdf4;
}
.step-card.unreachable {
    border-left-color: #9ca3af;
    background: #f9fafb;
}
.step-card.gap {
    border-left-color: #f59e0b;
    background: #fffbeb;
}

/* --- Path display --- */
.path-node {
    display: inline-block;
    background: #dbeafe;
    color: #1e40af;
    padding: 3px 10px;
    border-radius: 6px;
    font-size: 0.82rem;
    font-weight: 500;
    font-family: 'Inter', monospace;
    margin: 2px 3px;
}
.path-arrow {
    color: #94a3b8;
    font-weight: 700;
    margin: 0 2px;
}

/* --- Info box --- */
.info-box {
    background: #f0f7ff;
    border: 1px solid #bfdbfe;
    border-left: 5px solid #2563eb;
    border-radius: 8px;
    padding: 14px 18px;
    margin: 14px 0;
}
.info-box p {
    margin: 0;
    color: #1e3a8a;
    font-size: 0.9rem;
    line-height: 1.6;
}
.info-box strong {
    color: #0f172a;
    font-weight: 700;
}
.info-box em {
    color: #334155;
    font-style: italic;
}

/* --- Rank circle --- */
.rank-circle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: linear-gradient(135deg, #3b82f6, #1d4ed8);
    color: #fff;
    font-weight: 700;
    font-size: 0.9rem;
    margin-right: 10px;
    flex-shrink: 0;
}

/* --- Tab styling --- */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px 8px 0 0;
    padding: 10px 20px;
    font-weight: 600;
}

/* --- Expander polish --- */
.streamlit-expanderHeader {
    font-weight: 600 !important;
    font-size: 0.95rem !important;
}

/* --- Progress bar colors --- */
.stProgress > div > div > div {
    background: linear-gradient(90deg, #3b82f6, #06b6d4) !important;
}

/* --- Table styling --- */
.stTable table {
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid #cbd5e1;
}
.stTable thead th {
    background: #f1f5f9 !important;
    font-weight: 700 !important;
    font-size: 0.84rem !important;
    color: #0f172a !important;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    border-bottom: 2px solid #94a3b8 !important;
}
.stTable tbody td {
    font-size: 0.9rem;
    color: #1e293b;
}

/* --- Section header --- */
.section-header {
    font-size: 1.05rem;
    font-weight: 700;
    color: #0f172a;
    background: #f1f5f9;
    border-left: 5px solid #2563eb;
    border-radius: 0 8px 8px 0;
    padding: 8px 14px;
    margin: 18px 0 12px 0;
    letter-spacing: -0.01em;
    display: block;
}

/* --- Filter section --- */
.filter-section {
    background: #f8fafc;
    border-radius: 12px;
    padding: 8px;
    margin-bottom: 16px;
}

/* Legend items */
.legend-item {
    display: inline-flex;
    align-items: center;
    margin-right: 16px;
    font-size: 0.82rem;
    color: #475569;
}
.legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    display: inline-block;
    margin-right: 6px;
}
</style>
"""


# ============================================================================
# Visual Helper Components
# ============================================================================


def render_status_badge(status: str) -> str:
    """Render a text badge with status icon for accessibility."""
    mapping = {
        "atendido": "🟢 Atendido",
        "parcial": "🟡 Parcial",
        "ausente": "🔴 Ausente",
        "inalcancavel": "⚪ Inalcançável",
    }
    return mapping.get(status, status.capitalize())


def render_status_html(status: str) -> str:
    """Render an HTML-formatted status label."""
    mapping = {
        "atendido": ('<span class="status-atendido">✅ Atendido</span>', "satisfied"),
        "parcial": ('<span class="status-parcial">⚠️ Parcial</span>', "gap"),
        "ausente": ('<span class="status-ausente">❌ Ausente</span>', "gap"),
        "inalcancavel": (
            '<span class="status-inalcancavel">⛔ Inalcançável</span>',
            "unreachable",
        ),
    }
    html, _ = mapping.get(status, (f"<span>{status}</span>", ""))
    return html


def get_step_class(status: str) -> str:
    """Get CSS class for step card based on status."""
    mapping = {
        "atendido": "satisfied",
        "parcial": "gap",
        "ausente": "gap",
        "inalcancavel": "unreachable",
    }
    return mapping.get(status, "")


def get_score_color(pct: float, is_evaluated: bool = True) -> str:
    """Map a percentage to a gradient color."""
    if not is_evaluated:
        return "#64748b"
    if pct >= 80:
        return "#16a34a"
    if pct >= 65:
        return "#2563eb"
    if pct >= 50:
        return "#d97706"
    if pct >= 30:
        return "#ea580c"
    return "#dc2626"


def render_classification_badge(classification: MatchClassification) -> str:
    """Render HTML badge with classification color."""
    return (
        f'<span class="classification-chip" '
        f'style="background-color: {classification.color};">'
        f"{classification.value}</span>"
    )


def render_profile_form(
    current_profile: CandidateProfile | None,
    skills_catalog: list[SkillDefinition],
    taxonomy: RoleTaxonomy,
) -> CandidateProfile | None:
    """Render a clean and decluttered form to edit candidate profile attributes and dynamically add skills."""
    default_name = current_profile.name if current_profile else "Candidato"
    default_area = current_profile.area if current_profile else "data_engineering"
    default_role = current_profile.target_role if current_profile else "data_engineer"
    default_seniority = (
        current_profile.seniority if current_profile else Seniority.JUNIOR
    )

    # Initialize session state for user's declared skills dictionary: {skill_id: ProficiencyLevel}
    if "user_skills_dict" not in st.session_state:
        st.session_state.user_skills_dict = {}
        if current_profile and current_profile.skills:
            for sk in current_profile.skills:
                if sk.level != ProficiencyLevel.NENHUM:
                    st.session_state.user_skills_dict[sk.skill_id] = sk.level

    # ── 1. Dados Profissionais ──────────────────────────────────────────────
    st.markdown(
        '<div class="section-header">📋 Dados Profissionais</div>',
        unsafe_allow_html=True,
    )

    name = st.text_input(
        "👤 Nome do candidato:", value=default_name, key="prof_name_input"
    )

    col1, col2 = st.columns(2)

    area_keys = list(taxonomy.areas.keys())
    area_index = area_keys.index(default_area) if default_area in area_keys else 0

    with col1:
        selected_area_key = st.selectbox(
            "🏢 Área de atuação / interesse:",
            options=area_keys,
            index=area_index,
            format_func=lambda k: taxonomy.areas.get(k, k),
            key="profile_area",
        )

    with col2:
        seniority_options = list(Seniority)
        seniority_index = (
            seniority_options.index(default_seniority)
            if default_seniority in seniority_options
            else 1
        )
        selected_seniority = st.selectbox(
            "📊 Nível de Senioridade:",
            options=seniority_options,
            index=seniority_index,
            format_func=lambda s: s.label,
            key="profile_seniority",
        )

    # Filter roles matching selected area
    matching_roles = [r for r in taxonomy.roles if r.area == selected_area_key]
    if not matching_roles:
        matching_roles = taxonomy.roles

    role_ids = [r.id for r in matching_roles]
    role_index = (
        role_ids.index(default_role) if default_role and default_role in role_ids else 0
    )
    selected_role_id = st.selectbox(
        "🎯 Cargo desejado (Família Canônica):",
        options=role_ids,
        index=role_index,
        format_func=lambda rid: next(
            (r.name for r in matching_roles if r.id == rid), rid
        ),
        key="profile_role",
    )

    st.markdown("---")

    # ── 2. Adicionar Competência ────────────────────────────────────────────
    st.markdown(
        '<div class="section-header">🛠️ Adicionar Competência</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="info-box">
            <p>
                Selecione uma tecnologia e o seu nível de domínio para adicionar ao seu perfil.
                Adicione as competências que você domina para calcular a compatibilidade real com as vagas.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Prepare skills catalog lookup & sorted list
    skills_map = {s.id: s for s in skills_catalog}
    sorted_skills = sorted(
        skills_catalog,
        key=lambda s: (0 if s.area == selected_area_key else 1, s.name),
    )
    sorted_skill_ids = [s.id for s in sorted_skills]

    add_col1, add_col2, add_col3 = st.columns([5, 4, 3])

    with add_col1:
        chosen_skill_id = st.selectbox(
            "Tecnologia / Habilidade:",
            options=sorted_skill_ids,
            format_func=lambda sid: (
                f"{skills_map[sid].name} — {taxonomy.areas.get(skills_map[sid].area, skills_map[sid].area)}"
                if sid in skills_map
                else sid
            ),
            key="select_new_skill",
        )

    with add_col2:
        proficiency_choices = [
            ProficiencyLevel.BASICO,
            ProficiencyLevel.INTERMEDIARIO,
            ProficiencyLevel.AVANCADO,
            ProficiencyLevel.ESPECIALISTA,
        ]
        chosen_level = st.selectbox(
            "Nível de Domínio:",
            options=proficiency_choices,
            index=1,  # Default: Intermediário
            format_func=lambda lvl: f"{lvl.label} (Nível {lvl.score})",
            key="select_new_level",
        )

    with add_col3:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button(
            "➕ Adicionar",
            key="btn_add_skill",
            type="secondary",
        ):
            st.session_state.user_skills_dict[chosen_skill_id] = chosen_level
            st.rerun()

    # ── 3. Lista de Competências Declaradas ──────────────────────────────────
    user_skills_dict: dict[str, ProficiencyLevel] = st.session_state.user_skills_dict
    active_skills = [
        CandidateSkill(skill_id=sid, level=lvl)
        for sid, lvl in user_skills_dict.items()
        if lvl != ProficiencyLevel.NENHUM
    ]

    st.markdown("")
    st.markdown(
        f'<div class="section-header">📋 Competências no Perfil ({len(active_skills)})</div>',
        unsafe_allow_html=True,
    )

    if not active_skills:
        st.markdown(
            """
            <div style="background: #ffffff; border: 1.5px dashed #cbd5e1; border-radius: 12px; padding: 28px; text-align: center; color: #64748b; margin: 12px 0;">
                <span style="font-size: 2rem;">💡</span><br>
                <strong style="color: #1e293b; font-size: 1rem;">Nenhuma competência adicionada ainda.</strong><br>
                <span style="font-size: 0.88rem;">Selecione uma tecnologia acima e clique no botão <strong>➕ Adicionar</strong> para compor seu perfil profissional.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        # Table of declared skills with removal actions
        for sk in active_skills:
            s_def = skills_map.get(sk.skill_id)
            s_name = s_def.name if s_def else sk.skill_id.title()
            s_area_name = taxonomy.areas.get(s_def.area, s_def.area) if s_def else ""

            lvl_color = {
                ProficiencyLevel.BASICO: "#0284c7",
                ProficiencyLevel.INTERMEDIARIO: "#16a34a",
                ProficiencyLevel.AVANCADO: "#7c3aed",
                ProficiencyLevel.ESPECIALISTA: "#d97706",
            }.get(sk.level, "#64748b")

            col_s1, col_s2, col_s3 = st.columns([5, 4, 2])

            with col_s1:
                st.markdown(
                    f"**{s_name}** &nbsp; <span style='font-size: 0.78rem; color: #475569; background: #e2e8f0; padding: 2px 8px; border-radius: 4px;'>{s_area_name}</span>",
                    unsafe_allow_html=True,
                )

            with col_s2:
                st.markdown(
                    f"<span style='background: {lvl_color}18; color: {lvl_color}; border: 1px solid {lvl_color}55; padding: 3px 10px; border-radius: 10px; font-weight: 700; font-size: 0.82rem;'>{sk.level.label} (Nível {sk.level.score})</span>",
                    unsafe_allow_html=True,
                )

            with col_s3:
                if st.button(
                    "🗑️ Remover",
                    key=f"del_{sk.skill_id}",
                    help=f"Remover {s_name}",
                ):
                    del st.session_state.user_skills_dict[sk.skill_id]
                    st.rerun()

        st.markdown("")
        if st.button(
            "🗑️ Limpar todas as competências",
            key="btn_clear_all_skills",
        ):
            st.session_state.user_skills_dict.clear()
            st.rerun()

    st.markdown("---")

    # ── 4. Salvar Perfil ────────────────────────────────────────────────────
    if st.button(
        "💾  Salvar Perfil e Atualizar Recomendações",
        key="btn_save_full_profile",
        type="primary",
    ):
        return CandidateProfile(
            name=name.strip() or "Candidato",
            area=selected_area_key,
            target_role=selected_role_id,
            seniority=selected_seniority,
            skills=active_skills,
        )

    return None


def render_recommendation_card(
    rec: JobRecommendation,
    rank: int,
    taxonomy: RoleTaxonomy,
    profile: CandidateProfile | None = None,
) -> None:
    """Render a comprehensive recommendation card with progress, explanation, and breakdown table."""
    job = rec.job
    score_color = get_score_color(rec.final_percentage, is_evaluated=rec.is_evaluated)

    # Card container
    st.markdown('<div class="rec-card">', unsafe_allow_html=True)

    col_rank, col_title, col_score = st.columns([0.5, 4, 1.5])

    with col_rank:
        st.markdown(
            f'<div class="rank-circle">{rank}</div>',
            unsafe_allow_html=True,
        )

    with col_title:
        area_label = taxonomy.areas.get(job.area, job.area)
        st.markdown(f"#### {job.title}")
        st.markdown(
            f"🏢 **{job.company}** &nbsp;·&nbsp; 📍 {job.location} &nbsp;·&nbsp; "
            f"💼 {area_label} &nbsp;·&nbsp; 🏷️ **{job.seniority.label}**"
        )

    with col_score:
        st.markdown(
            f'<div style="text-align: center;">'
            f'<div class="score-badge" style="color: {score_color};">'
            f"{rec.final_percentage:.1f}%</div>"
            f"<br>{render_classification_badge(rec.classification)}"
            f"</div>",
            unsafe_allow_html=True,
        )

    # Progress bar
    if not rec.is_evaluated:
        st.progress(
            0.0,
            text="Perfil ainda não avaliado — 0,0%",
        )
        st.caption(
            "ℹ️ *Perfil ainda não avaliado. Preencha suas competências e informações "
            "profissionais para calcular a compatibilidade com esta vaga.*"
        )
    else:
        st.progress(
            min(max(rec.final_percentage / 100.0, 0.0), 1.0),
            text=f"Compatibilidade consolidada: {rec.final_percentage:.1f}%",
        )

    # Quick summary metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Match Técnico", f"{rec.technical_percentage:.1f}%")
    with m2:
        st.metric("Contexto", f"{rec.context_percentage:.1f}%")
    with m3:
        st.metric("Proximidade à Vaga", f"{rec.proximity_percentage:.1f}%")
    with m4:
        satisfied = sum(1 for d in rec.details if d.is_satisfied)
        st.metric(
            "Requisitos Atendidos",
            f"{satisfied}/{len(rec.details)}",
        )

    # Expandable detail section
    with st.expander("🔍 Detalhamento do Cálculo"):
        st.markdown(
            '<p class="section-header">📊 Composição da Nota Final</p>',
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="info-box">
                <p><strong>Fórmula Determinística:</strong><br>
                Nota Final = 60% × Match Técnico + 20% × Contexto + 20% × Proximidade à Vaga</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tech_contrib = 0.60 * rec.technical_percentage
        ctx_contrib = 0.20 * rec.context_percentage
        prox_contrib = 0.20 * rec.proximity_percentage

        comp_html = f"""
        <table style="width: 100%; border-collapse: separate; border-spacing: 0; margin: 14px 0; background: #ffffff; border: 1.5px solid #cbd5e1; border-radius: 10px; overflow: hidden; font-family: 'Inter', sans-serif;">
            <thead>
                <tr style="background: #f1f5f9; border-bottom: 2px solid #94a3b8;">
                    <th style="padding: 12px 16px; text-align: left; font-size: 0.85rem; font-weight: 700; color: #0f172a; text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 2px solid #94a3b8;">Critério</th>
                    <th style="padding: 12px 16px; text-align: center; font-size: 0.85rem; font-weight: 700; color: #0f172a; text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 2px solid #94a3b8;">Resultado</th>
                    <th style="padding: 12px 16px; text-align: center; font-size: 0.85rem; font-weight: 700; color: #0f172a; text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 2px solid #94a3b8;">Peso</th>
                    <th style="padding: 12px 16px; text-align: right; font-size: 0.85rem; font-weight: 700; color: #0f172a; text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 2px solid #94a3b8;">Contribuição</th>
                </tr>
            </thead>
            <tbody>
                <tr style="background: #ffffff; border-bottom: 1px solid #e2e8f0;">
                    <td style="padding: 12px 16px; font-weight: 600; color: #1e293b; border-bottom: 1px solid #e2e8f0;">🔧 Match Técnico</td>
                    <td style="padding: 12px 16px; text-align: center; font-weight: 700; color: #0284c7; font-size: 0.95rem; border-bottom: 1px solid #e2e8f0;">{rec.technical_percentage:.1f}%</td>
                    <td style="padding: 12px 16px; text-align: center; font-weight: 600; color: #475569; border-bottom: 1px solid #e2e8f0;">60%</td>
                    <td style="padding: 12px 16px; text-align: right; font-weight: 700; color: #0369a1; font-size: 0.95rem; border-bottom: 1px solid #e2e8f0;">{tech_contrib:.1f} pts</td>
                </tr>
                <tr style="background: #f8fafc; border-bottom: 1px solid #e2e8f0;">
                    <td style="padding: 12px 16px; font-weight: 600; color: #1e293b; border-bottom: 1px solid #e2e8f0;">🏢 Contexto</td>
                    <td style="padding: 12px 16px; text-align: center; font-weight: 700; color: #8b5cf6; font-size: 0.95rem; border-bottom: 1px solid #e2e8f0;">{rec.context_percentage:.1f}%</td>
                    <td style="padding: 12px 16px; text-align: center; font-weight: 600; color: #475569; border-bottom: 1px solid #e2e8f0;">20%</td>
                    <td style="padding: 12px 16px; text-align: right; font-weight: 700; color: #7c3aed; font-size: 0.95rem; border-bottom: 1px solid #e2e8f0;">{ctx_contrib:.1f} pts</td>
                </tr>
                <tr style="background: #ffffff; border-bottom: 2px solid #cbd5e1;">
                    <td style="padding: 12px 16px; font-weight: 600; color: #1e293b; border-bottom: 2px solid #cbd5e1;">🛤️ Proximidade à Vaga</td>
                    <td style="padding: 12px 16px; text-align: center; font-weight: 700; color: #d97706; font-size: 0.95rem; border-bottom: 2px solid #cbd5e1;">{rec.proximity_percentage:.1f}%</td>
                    <td style="padding: 12px 16px; text-align: center; font-weight: 600; color: #475569; border-bottom: 2px solid #cbd5e1;">20%</td>
                    <td style="padding: 12px 16px; text-align: right; font-weight: 700; color: #b45309; font-size: 0.95rem; border-bottom: 2px solid #cbd5e1;">{prox_contrib:.1f} pts</td>
                </tr>
                <tr style="background: #f1f5f9;">
                    <td style="padding: 14px 16px; color: #0f172a; font-size: 1rem; font-weight: 700;">📊 <strong>Nota Final</strong></td>
                    <td style="padding: 14px 16px; text-align: center; color: #64748b; font-weight: 600;">—</td>
                    <td style="padding: 14px 16px; text-align: center; color: #0f172a; font-size: 0.95rem; font-weight: 700;">100%</td>
                    <td style="padding: 14px 16px; text-align: right; color: #0f172a; font-size: 1.05rem; font-weight: 800;">{rec.final_percentage:.1f}%</td>
                </tr>
            </tbody>
        </table>
        """
        st.markdown(comp_html, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown(
            '<p class="section-header">📋 Detalhamento por Requisito</p>',
            unsafe_allow_html=True,
        )

        table_data = []
        for d in rec.details:
            kind_str = (
                "Obrigatório"
                if d.requirement.kind == RequirementKind.REQUIRED
                else "Desejável"
            )
            if not rec.is_evaluated:
                dist_str = "—"
            elif d.distance is not None:
                dist_str = f"{d.distance:.1f}"
            else:
                dist_str = "Inalcançável"

            path_str = " → ".join(d.shortest_path) if d.shortest_path else "—"
            sat_pct = min(d.satisfaction_ratio * 100.0, 100.0)

            table_data.append(
                {
                    "Competência": d.skill_name,
                    "Tipo": kind_str,
                    "Nível Atual": d.candidate_level.label,
                    "Nível Exigido": d.required_level.label,
                    "Atendimento": f"{render_status_badge(d.status)} ({sat_pct:.0f}%)",
                    "Peso": f"{d.max_weight:.1f}",
                    "Pontos": f"{d.requirement_score:.1f}",
                    "Dist. Dijkstra": dist_str,
                    "Proximidade": f"{d.proximity_score:.1f}%",
                    "Caminho": path_str,
                }
            )
        st.dataframe(
            table_data,
            use_container_width=True,
            hide_index=True,
            height=min(40 * len(table_data) + 60, 500),
        )

        # Context details computation
        ctx_details = (
            get_context_breakdown(profile, rec.job, taxonomy)
            if profile
            else {
                "area_pts": 0.0,
                "area_desc": "Perfil não avaliado",
                "role_pts": 0.0,
                "role_desc": "Perfil não avaliado",
                "seniority_pts": 0.0,
                "seniority_desc": "Perfil não avaliado",
                "total_pts": rec.context_percentage,
            }
        )

        total_req_points = sum(d.requirement_score for d in rec.details)
        total_req_max_points = sum(d.max_weight for d in rec.details)

        with st.expander(
            "📝 Justificativa Detalhada da Compatibilidade", expanded=True
        ):
            st.markdown(
                '<p class="section-header">Por que esta nota? Explicação por Dimensão</p>',
                unsafe_allow_html=True,
            )

            col_j1, col_j2, col_j3 = st.columns(3)
            satisfied_count = sum(1 for d in rec.details if d.is_satisfied)

            with col_j1:
                st.markdown(
                    f"""
                    <div style="background: #ffffff; border: 1.5px solid #0284c7; border-radius: 10px; padding: 16px; margin-bottom: 12px; height: 100%;">
                        <div style="color: #0369a1; font-weight: 700; font-size: 0.95rem; margin-bottom: 6px;">1. Match Técnico (60%)</div>
                        <div style="font-size: 1.15rem; color: #0284c7; font-weight: 800; margin-bottom: 8px;">{rec.technical_percentage:.1f}% &nbsp;·&nbsp; <span style="font-size: 0.9rem; font-weight: 600;">{tech_contrib:.1f} pts</span></div>
                        <p style="font-size: 0.85rem; color: #334155; margin-bottom: 6px;"><strong>Cálculo:</strong> {total_req_points:.1f} pts obtidos / {total_req_max_points:.1f} pts máximos = <strong>{rec.technical_percentage:.1f}%</strong></p>
                        <p style="font-size: 0.82rem; color: #64748b; margin: 0;">{satisfied_count} de {len(rec.details)} requisitos atendidos integralmente.</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col_j2:
                st.markdown(
                    f"""
                    <div style="background: #ffffff; border: 1.5px solid #8b5cf6; border-radius: 10px; padding: 16px; margin-bottom: 12px; height: 100%;">
                        <div style="color: #6d28d9; font-weight: 700; font-size: 0.95rem; margin-bottom: 6px;">2. Contexto (20%)</div>
                        <div style="font-size: 1.15rem; color: #7c3aed; font-weight: 800; margin-bottom: 8px;">{rec.context_percentage:.1f}% &nbsp;·&nbsp; <span style="font-size: 0.9rem; font-weight: 600;">{ctx_contrib:.1f} pts</span></div>
                        <p style="font-size: 0.85rem; color: #334155; margin-bottom: 4px;">• <strong>Área:</strong> {ctx_details["area_desc"]}</p>
                        <p style="font-size: 0.85rem; color: #334155; margin-bottom: 4px;">• <strong>Cargo:</strong> {ctx_details["role_desc"]}</p>
                        <p style="font-size: 0.85rem; color: #334155; margin-bottom: 6px;">• <strong>Senioridade:</strong> {ctx_details["seniority_desc"]}</p>
                        <p style="font-size: 0.82rem; color: #64748b; margin: 0;"><strong>Soma:</strong> {ctx_details["area_pts"]:.0f} + {ctx_details["role_pts"]:.0f} + {ctx_details["seniority_pts"]:.0f} = <strong>{rec.context_percentage:.1f}%</strong></p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col_j3:
                st.markdown(
                    f"""
                    <div style="background: #ffffff; border: 1.5px solid #d97706; border-radius: 10px; padding: 16px; margin-bottom: 12px; height: 100%;">
                        <div style="color: #b45309; font-weight: 700; font-size: 0.95rem; margin-bottom: 6px;">3. Proximidade à Vaga (20%)</div>
                        <div style="font-size: 1.15rem; color: #d97706; font-weight: 800; margin-bottom: 8px;">{rec.proximity_percentage:.1f}% &nbsp;·&nbsp; <span style="font-size: 0.9rem; font-weight: 600;">{prox_contrib:.1f} pts</span></div>
                        <p style="font-size: 0.85rem; color: #334155; margin-bottom: 6px;"><strong>Fórmula:</strong> max(0, 100 × (1 - Distância_Dijkstra / 10))</p>
                        <p style="font-size: 0.85rem; color: #334155; margin-bottom: 6px;">Média ponderada pelo peso dos requisitos que ainda faltam.</p>
                        <p style="font-size: 0.82rem; color: #64748b; margin: 0;">Custo total das distâncias no grafo: <strong>{rec.total_cost:.1f}</strong></p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.text_area(
                "Texto Consolidado da Justificativa:",
                value=rec.justification,
                height=220,
                disabled=True,
                key=f"justification_text_{rec.job.id}_{rank}",
            )

    st.markdown("</div>", unsafe_allow_html=True)


def format_skill_name(
    skill_id: str, skills_catalog: list[SkillDefinition] | None = None
) -> str:
    """Format a skill ID into a clean canonical display name without underscores."""
    if skills_catalog:
        for s in skills_catalog:
            if s.id == skill_id:
                return s.name
    return skill_id.replace("_", " ").title()


def get_node_style(
    node_key: str,
    profile: CandidateProfile,
    target_job: Job,
    skills_map: dict[str, SkillDefinition],
    distances_map: dict[str, float] | None = None,
) -> dict[str, object]:
    """Determine visual styling, semantic classification, and tooltip for a graph vertex."""
    if node_key == "PROFILE":
        return {
            "label": "PROFILE\n(Ponto de Partida)",
            "color": {
                "background": "#8B5CF6",
                "border": "#7C3AED",
                "highlight": {"background": "#A78BFA", "border": "#6D28D9"},
            },
            "size": 36,
            "shape": "diamond",
            "borderWidth": 3,
            "node_type": "Perfil: ponto de partida do candidato",
            "tooltip": (
                "Competência: PROFILE\n"
                "Tipo: Ponto de partida do candidato\n"
                "Distância acumulada: 0.0"
            ),
        }

    if ":" not in node_key:
        return {
            "label": node_key,
            "color": {
                "background": "#EF4444",
                "border": "#DC2626",
                "highlight": {"background": "#F87171", "border": "#991B1B"},
            },
            "size": 24,
            "shape": "box",
            "borderWidth": 2,
            "node_type": "Pendente: competência ou nível que ainda precisa ser alcançado",
            "tooltip": f"Vértice: {node_key}",
        }

    s_id, lvl_str = node_key.split(":", 1)
    s_def = skills_map.get(s_id)
    skill_name = s_def.name if s_def else s_id.replace("_", " ").title()
    lvl_enum = ProficiencyLevel(lvl_str)
    readable_level = f"Nível {lvl_enum.label.lower()}"

    cand_level = profile.get_skill_level(s_id)
    is_job_requirement = any(
        req.vertex_key == node_key for req in target_job.requirements
    )
    is_possessed = (cand_level.score >= lvl_enum.score) and (
        lvl_enum != ProficiencyLevel.NENHUM
    )

    if is_possessed and is_job_requirement:
        color = {
            "background": "#22C55E",
            "border": "#8B5CF6",
            "highlight": {"background": "#4ADE80", "border": "#7C3AED"},
        }
        border_width = 4
        node_type = "Atendido: competência e nível já dominados"
        size = 28
    elif is_possessed:
        color = {
            "background": "#22C55E",
            "border": "#15803D",
            "highlight": {"background": "#4ADE80", "border": "#166534"},
        }
        border_width = 2
        node_type = "Atendido: competência e nível já dominados"
        size = 26
    elif is_job_requirement:
        color = {
            "background": "#EF4444",
            "border": "#991B1B",
            "highlight": {"background": "#F87171", "border": "#7F1D1D"},
        }
        border_width = 5
        node_type = "Pendente: competência ou nível que ainda precisa ser alcançado"
        size = 30
    else:
        # Etapas pendentes / intermediárias de aprendizado (todas em vermelho)
        color = {
            "background": "#EF4444",
            "border": "#DC2626",
            "highlight": {"background": "#F87171", "border": "#991B1B"},
        }
        border_width = 2
        node_type = "Pendente: competência ou nível que ainda precisa ser alcançado"
        size = 26

    dist_val = distances_map.get(node_key) if distances_map else None
    dist_str = (
        f"{dist_val:.1f}"
        if dist_val is not None and dist_val != float("inf")
        else "N/A"
    )

    tooltip = (
        f"Competência: {skill_name}\n"
        f"Nível: {lvl_enum.label}\n"
        f"Status: {node_type}\n"
        f"É requisito da vaga: {'Sim' if is_job_requirement else 'Não'}\n"
        f"Distância acumulada desde o início: {dist_str}"
    )

    return {
        "label": f"{skill_name}\n{readable_level}",
        "color": color,
        "size": size,
        "shape": "box",
        "borderWidth": border_width,
        "node_type": node_type,
        "tooltip": tooltip,
    }


def build_path_graph(
    edges: list[tuple[str, str, float]],
    profile: CandidateProfile,
    target_job: Job,
    skills_catalog: list[SkillDefinition],
    distances_map: dict[str, float] | None = None,
) -> tuple[Network, set[str]]:
    """Construct hierarchical LR PyVis network with dark theme and return network and present node types."""
    net = Network(
        height="580px",
        width="100%",
        directed=True,
        bgcolor="#0E1117",
        font_color="#F8FAFC",
    )

    options = {
        "layout": {
            "hierarchical": {
                "enabled": True,
                "direction": "LR",
                "sortMethod": "directed",
                "levelSeparation": 220,
                "nodeSpacing": 140,
                "treeSpacing": 180,
                "parentCentralization": True,
                "blockShifting": True,
                "edgeMinimization": True,
            }
        },
        "interaction": {
            "dragNodes": True,
            "dragView": True,
            "zoomView": True,
            "hover": True,
        },
        "physics": {
            "enabled": False,
        },
        "edges": {
            "smooth": {
                "type": "cubicBezier",
                "forceDirection": "horizontal",
                "roundness": 0.25,
            },
            "arrows": {
                "to": {
                    "enabled": True,
                    "scaleFactor": 1.1,
                }
            },
        },
    }
    net.set_options(json.dumps(options))

    # Compute topological levels from PROFILE via BFS
    adj: dict[str, list[str]] = {}
    for u, v, _ in edges:
        adj.setdefault(u, []).append(v)

    node_levels: dict[str, int] = {"PROFILE": 0}
    bfs_queue = ["PROFILE"]
    while bfs_queue:
        curr = bfs_queue.pop(0)
        for neighbor in adj.get(curr, []):
            if neighbor not in node_levels:
                node_levels[neighbor] = node_levels[curr] + 1
                bfs_queue.append(neighbor)

    skills_map = {s.id: s for s in skills_catalog}
    added_nodes: set[str] = set()
    present_categories: set[str] = set()

    for u, v, weight in edges:
        for node in (u, v):
            if node not in added_nodes:
                style = get_node_style(
                    node_key=node,
                    profile=profile,
                    target_job=target_job,
                    skills_map=skills_map,
                    distances_map=distances_map,
                )
                b_width = int(style.get("borderWidth", 2))
                net.add_node(
                    node,
                    label=style["label"],
                    color=style["color"],
                    shape=style["shape"],
                    size=style["size"],
                    title=style["tooltip"],
                    level=node_levels.get(node, 1),
                    borderWidth=b_width,
                    borderWidthSelected=b_width + 2,
                    font={
                        "size": 12,
                        "face": "Inter, sans-serif",
                        "color": "#F8FAFC",
                    },
                )
                added_nodes.add(node)
                present_categories.add(str(style["node_type"]))

        w_val = int(weight) if weight.is_integer() else f"{weight:.1f}"
        w_str = f"Custo: {w_val}"

        src_desc = (
            "PROFILE"
            if u == "PROFILE"
            else f"{format_skill_name(u.split(':')[0], skills_catalog)} {ProficiencyLevel(u.split(':')[1]).label.lower()}"
        )
        tgt_desc = (
            "PROFILE"
            if v == "PROFILE"
            else f"{format_skill_name(v.split(':')[0], skills_catalog)} {ProficiencyLevel(v.split(':')[1]).label.lower()}"
        )
        edge_title = f"{src_desc} ── {w_str} ──→ {tgt_desc}"

        net.add_edge(
            u,
            v,
            label=w_str,
            width=3,
            color="#94A3B8",
            title=edge_title,
            font={
                "size": 11,
                "color": "#F8FAFC",
                "background": "#1E293B",
                "strokeWidth": 0,
                "align": "horizontal",
            },
            arrows={"to": {"enabled": True, "scaleFactor": 1.1}},
        )

    return net, present_categories


def render_graph_legend(present_categories: set[str]) -> None:
    """Render dynamic visual legend displaying ONLY categories present in the active graph."""
    legend_defs = [
        (
            "Perfil: ponto de partida do candidato",
            "#8B5CF6",
            "🟣 Perfil: ponto de partida do candidato",
        ),
        (
            "Atendido: competência e nível já dominados",
            "#22C55E",
            "🟢 Atendido: competência e nível já dominados",
        ),
        (
            "Pendente: competência ou nível que ainda precisa ser alcançado",
            "#EF4444",
            "🔴 Pendente: competência ou nível que ainda precisa ser alcançado",
        ),
    ]

    items_html = []
    for cat_name, color, desc in legend_defs:
        if cat_name in present_categories:
            items_html.append(
                f'<span class="legend-item" style="margin-right: 18px; margin-bottom: 6px; display: inline-flex; align-items: center;">'
                f'<span class="legend-dot" style="background: {color}; width: 12px; height: 12px; border-radius: 50%; display: inline-block; margin-right: 6px;"></span>'
                f'<span style="font-size: 0.85rem; color: #F8FAFC; font-weight: 500;">{desc}</span>'
                f"</span>"
            )

    if items_html:
        st.markdown(
            f'<div style="background: #1E293B; border: 1px solid #334155; border-radius: 10px; padding: 10px 16px; margin: 12px 0; display: flex; flex-wrap: wrap;">{"".join(items_html)}</div>',
            unsafe_allow_html=True,
        )


def render_path_summary(
    step: dict[str, object],
    profile: CandidateProfile,
    target_job: Job,
    skills_catalog: list[SkillDefinition],
) -> None:
    """Render structured contextualization card and clean narrative before graph rendering."""
    skill_name = str(step["skill_name"])
    req_lvl = str(step["required_level"])
    cand_lvl = str(step["candidate_level"])
    status = str(step["status"])
    dist = step["distance"]
    path = list(step["path"]) if isinstance(step["path"], list) else []

    st.markdown(f"#### Requisito: {skill_name} ({req_lvl})")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            "Vaga Alvo",
            target_job.title[:24] + "..."
            if len(target_job.title) > 24
            else target_job.title,
        )
    with c2:
        st.metric("Nível Atual vs Exigido", f"{cand_lvl} → {req_lvl}")
    with c3:
        cost_display = f"{float(dist):.1f}" if dist is not None else "—"
        st.metric("Custo Total do Menor Caminho", cost_display)
    with c4:
        num_transitions = max(0, len(path) - 1) if path else 0
        st.metric("Quantidade de Transições", str(num_transitions))

    if step.get("is_satisfied"):
        interpretation_html = (
            f"<strong>Requisito Atendido:</strong> O candidato já possui nível <strong>{cand_lvl}</strong> em <strong>{skill_name}</strong>, "
            f"o que atende ao nível exigido (<strong>{req_lvl}</strong>). O custo total de aprendizado é <strong>0.0</strong>."
        )
    elif status == "inalcancavel":
        interpretation_html = (
            f"<strong>Requisito Inalcançável:</strong> Não foi encontrada transição no grafo de competências "
            f"entre o perfil atual e <strong>{skill_name}</strong> no nível <strong>{req_lvl}</strong>."
        )
    else:
        clean_steps_desc = []
        for v in path:
            if ":" in v:
                s_id, l_str = v.split(":", 1)
                s_name = format_skill_name(s_id, skills_catalog)
                clean_steps_desc.append(f"{s_name} ({ProficiencyLevel(l_str).label})")
            else:
                clean_steps_desc.append(v)

        path_narrative = " &rarr; ".join(clean_steps_desc)
        dist_float = float(dist) if dist is not None else 0.0
        interpretation_html = (
            f"Para alcançar <strong>{skill_name}</strong> no nível <strong>{req_lvl.lower()}</strong>, o menor caminho parte da origem (<code>PROFILE</code>), "
            f"percorre a trilha <strong>{path_narrative}</strong> e totaliza um custo acumulado de <strong>{dist_float:.1f}</strong>.<br><br>"
            f"<em>Interpretação:</em> Quanto <strong>menor</strong> esse custo, <strong>maior a facilidade estimada</strong> de atingir o requisito a partir do perfil atual."
        )

    st.markdown(
        f"""
        <div class="info-box" style="margin: 12px 0;">
            <p>{interpretation_html}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_graph_network(
    edges: list[tuple[str, str, float]],
    profile: CandidateProfile,
    target_job: Job,
    skills_catalog: list[SkillDefinition],
    distances_map: dict[str, float] | None = None,
) -> None:
    """Build and display interactive hierarchical network with dynamic legend."""
    try:
        net, present_categories = build_path_graph(
            edges=edges,
            profile=profile,
            target_job=target_job,
            skills_catalog=skills_catalog,
            distances_map=distances_map,
        )
        render_graph_legend(present_categories)
        html_content = net.generate_html()

        # Inject automatic canvas fit script to ensure graph starts fully visible with margins
        fit_script = """
        <script type="text/javascript">
            window.addEventListener("load", function() {
                setTimeout(function() {
                    if (typeof network !== "undefined") {
                        network.fit({
                            animation: false,
                            padding: 40
                        });
                    }
                }, 150);
            });
        </script>
        """
        if "</body>" in html_content:
            html_content = html_content.replace("</body>", f"{fit_script}</body>")
        else:
            html_content += fit_script

        st.components.v1.html(html_content, height=600, scrolling=False)
    except Exception as exc:
        st.warning(
            f"Visualização interativa indisponível ({exc}). Exibindo lista de arestas:"
        )
        for u, v, w in edges:
            st.markdown(f"- `{u}` → `{v}` (custo **{w:.1f}**)")


# ============================================================================
# Application Entry Point
# ============================================================================


def main() -> None:
    """Main application orchestrator."""
    st.set_page_config(
        page_title="SkillRoute — Recomendador de Vagas e Trilhas de Carreira",
        page_icon="🗺️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    loader = DataLoader()
    taxonomy = loader.load_taxonomy()
    skills_catalog = loader.load_skills()
    jobs = loader.load_jobs()
    graph = loader.build_graph()

    # Default profile in session state
    if "candidate_profile" not in st.session_state:
        st.session_state.candidate_profile = CandidateProfile(
            name="Candidato",
            area="software_development",
            target_role=None,
            seniority=Seniority.JUNIOR,
            skills=[],
        )

    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(
            """
            <div style="text-align: center; padding: 10px 0 5px 0;">
                <span style="font-size: 2.5rem;">🧭</span><br>
                <span style="font-size: 1.4rem; font-weight: 800; color: #f8fafc; letter-spacing: -0.02em;">
                    SkillRoute
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(
            "Sistema determinístico de recomendação de vagas e análise de "
            "caminhos mínimos de capacitação baseado no Algoritmo de Dijkstra."
        )
        st.markdown("---")

        st.markdown("### 📊 Base de Dados")
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Vagas", len(jobs))
            st.metric("Vértices", graph.vertex_count)
        with c2:
            st.metric("Skills", len(skills_catalog))
            st.metric("Arestas", graph.edge_count)

        st.markdown(f"**Áreas Cobertas:** {len(taxonomy.areas)}")
        st.markdown("---")

        # Profile summary
        profile = st.session_state.candidate_profile
        st.markdown("### 👤 Perfil Ativo")
        st.markdown(f"**{profile.name}**")
        st.markdown(f"Área: {taxonomy.areas.get(profile.area, profile.area)}")
        st.markdown(f"Senioridade: {profile.seniority.label}")
        declared = [s for s in profile.skills if s.level != ProficiencyLevel.NENHUM]
        if declared:
            skills_str = ", ".join(
                f"{s.skill_id} ({s.level.label})" for s in declared[:6]
            )
            if len(declared) > 6:
                skills_str += f" +{len(declared) - 6}"
            st.caption(f"Skills: {skills_str}")

        st.markdown("---")
        st.caption("📚 Projeto de Algoritmos — Grafos & Dijkstra")

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab_profile, tab_recommendations, tab_path = st.tabs(
        [
            "👤 Perfil do Candidato",
            "💼 Vagas Recomendadas",
            "🛤️ Caminho até a Vaga",
        ]
    )

    current_profile: CandidateProfile = st.session_state.candidate_profile

    # ── Tab 1: Profile Editor ────────────────────────────────────────────────
    with tab_profile:
        st.markdown("## 👤 Perfil do Candidato")
        st.markdown(
            "Preencha as informações profissionais e declare as tecnologias que você domina. "
            "O sistema utilizará essas informações para calcular a compatibilidade com cada vaga."
        )
        st.markdown("")

        updated_profile = render_profile_form(
            current_profile=current_profile,
            skills_catalog=skills_catalog,
            taxonomy=taxonomy,
        )
        if updated_profile:
            st.session_state.candidate_profile = updated_profile
            st.session_state.user_skills_dict = {
                sk.skill_id: sk.level for sk in updated_profile.skills
            }
            st.success(
                "✅ Perfil atualizado com sucesso! Acesse a aba **Vagas Recomendadas** "
                "para ver o ranking atualizado."
            )
            st.rerun()

    # ── Compute recommendations ──────────────────────────────────────────────
    recommendations = recommend_jobs(
        profile=current_profile,
        jobs=jobs,
        graph=graph,
        taxonomy=taxonomy,
        skills_catalog=skills_catalog,
    )

    # ── Tab 2: Recommendations List ──────────────────────────────────────────
    with tab_recommendations:
        st.markdown("## 💼 Vagas Recomendadas")
        st.markdown(
            "Ranking de compatibilidade calculado com base em "
            "**Match Técnico (60%)**, **Contexto (20%)** e "
            "**Proximidade à Vaga por Dijkstra (20%)**."
        )

        if not current_profile.has_sufficient_data:
            st.info(
                "ℹ️ **Perfil ainda não avaliado:** Preencha suas competências e informações "
                "profissionais na aba **👤 Perfil do Candidato** para que o sistema calcule a "
                "compatibilidade real, o match técnico, contexto e a proximidade à vaga com cada oportunidade."
            )

        # Filters
        with st.expander("⚙️ Filtros e Ordenação", expanded=True):
            f_col1, f_col2, f_col3, f_col4 = st.columns(4)

            with f_col1:
                area_filter_options = ["Todas as áreas"] + list(taxonomy.areas.keys())
                selected_area_filter = st.selectbox(
                    "Filtrar por Área:",
                    options=area_filter_options,
                    format_func=lambda k: (
                        "🌐 Todas as áreas"
                        if k == "Todas as áreas"
                        else taxonomy.areas.get(k, k)
                    ),
                )

            with f_col2:
                seniority_filter_options = ["Todas as senioridades"] + [
                    s.value for s in Seniority
                ]
                selected_seniority_filter = st.selectbox(
                    "Filtrar por Senioridade:",
                    options=seniority_filter_options,
                    format_func=lambda s: (
                        "📊 Todas as senioridades"
                        if s == "Todas as senioridades"
                        else next((x.label for x in Seniority if x.value == s), s)
                    ),
                )

            with f_col3:
                min_score = st.slider(
                    "Nota Mínima (%):",
                    min_value=0,
                    max_value=100,
                    value=0,
                    step=5,
                )

            with f_col4:
                sort_order = st.selectbox(
                    "Ordenar por:",
                    options=[
                        "Maior compatibilidade",
                        "Maior match técnico",
                        "Menor custo de evolução",
                    ],
                )

        # Apply filters
        filtered_recs = list(recommendations)
        if selected_area_filter != "Todas as áreas":
            filtered_recs = [
                r for r in filtered_recs if r.job.area == selected_area_filter
            ]
        if selected_seniority_filter != "Todas as senioridades":
            filtered_recs = [
                r
                for r in filtered_recs
                if r.job.seniority.value == selected_seniority_filter
            ]
        if min_score > 0:
            filtered_recs = [
                r for r in filtered_recs if r.final_percentage >= min_score
            ]

        # Apply sorting
        if sort_order == "Maior match técnico":
            filtered_recs.sort(
                key=lambda r: (-r.technical_percentage, -r.final_percentage)
            )
        elif sort_order == "Menor custo de evolução":
            filtered_recs.sort(key=lambda r: (r.total_cost, -r.final_percentage))
        else:
            filtered_recs.sort(
                key=lambda r: (-r.final_percentage, -r.technical_percentage)
            )

        # Results summary
        st.markdown(f"Exibindo **{len(filtered_recs)}** de **{len(jobs)}** vagas")

        if not filtered_recs:
            st.warning(
                "Nenhuma vaga encontrada com os filtros selecionados. "
                "Tente ajustar os parâmetros."
            )
        else:
            for idx, rec in enumerate(filtered_recs, start=1):
                render_recommendation_card(
                    rec=rec,
                    rank=idx,
                    taxonomy=taxonomy,
                    profile=current_profile,
                )

    # ── Tab 3: Career Pathway & Graph ─────────────────────────────────────────
    with tab_path:
        st.markdown("## 🛤️ Caminho até a Vaga")
        st.markdown(
            "Explore passo a passo as lacunas de conhecimento e a "
            "**visualização hierárquica dos menores caminhos** calculados por Dijkstra para a vaga selecionada."
        )

        if not current_profile.has_sufficient_data:
            st.info(
                "Preencha seu perfil e selecione uma vaga para visualizar os caminhos."
            )
        else:
            job_choices = {
                j.id: f"{j.title} — {j.company} ({j.seniority.label})" for j in jobs
            }
            default_job_id = (
                recommendations[0].job.id
                if recommendations
                else list(job_choices.keys())[0]
            )

            selected_job_id = st.selectbox(
                "🎯 Selecione a vaga de destino:",
                options=list(job_choices.keys()),
                format_func=lambda jid: job_choices[jid],
                index=list(job_choices.keys()).index(default_job_id),
            )

            target_job = next((j for j in jobs if j.id == selected_job_id), None)
            target_rec = next(
                (r for r in recommendations if r.job.id == selected_job_id), None
            )

            if target_job and target_rec:
                st.markdown(
                    f"### {target_job.title} "
                    f"<span style='color: #64748b; font-weight: 400;'>— {target_job.company}</span>",
                    unsafe_allow_html=True,
                )

                # Metrics row
                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    st.metric(
                        "Compatibilidade",
                        f"{target_rec.final_percentage:.1f}%",
                    )
                with m2:
                    st.metric(
                        "Match Técnico",
                        f"{target_rec.technical_percentage:.1f}%",
                    )
                with m3:
                    st.metric("Custo Total", f"{target_rec.total_cost:.1f}")
                with m4:
                    satisfied_count = sum(
                        1 for d in target_rec.details if d.is_satisfied
                    )
                    st.metric(
                        "Requisitos Atendidos",
                        f"{satisfied_count} / {len(target_rec.details)}",
                    )

                st.divider()

                # Career path steps
                career_steps = calculate_career_path(
                    profile=current_profile,
                    job=target_job,
                    base_graph=graph,
                    skills_catalog=skills_catalog,
                )

                distances_map, _, _ = run_profile_dijkstra(
                    profile=current_profile,
                    base_graph=graph,
                    skills_catalog=skills_catalog,
                )

                st.markdown(
                    '<p class="section-header">📋 Passos Recomendados por Requisito</p>',
                    unsafe_allow_html=True,
                )

                for step in career_steps:
                    skill_title = step["skill_name"]
                    req_lvl = step["required_level"]
                    cand_lvl = step["candidate_level"]
                    status = step["status"]
                    dist = step["distance"]
                    path = step["path"]
                    step_class = get_step_class(status)

                    st.markdown(
                        f'<div class="step-card {step_class}">',
                        unsafe_allow_html=True,
                    )

                    col_s1, col_s2 = st.columns([4, 1])
                    with col_s1:
                        st.markdown(
                            f"**{skill_title}** &nbsp;·&nbsp; "
                            f"Exigido: `{req_lvl}` &nbsp;·&nbsp; Atual: `{cand_lvl}`"
                        )
                    with col_s2:
                        st.markdown(render_status_html(status), unsafe_allow_html=True)

                    if step["is_satisfied"]:
                        st.caption("✅ Requisito já atendido pelo perfil atual.")
                    elif status == "inalcancavel":
                        st.warning(
                            "⚠️ Não foi encontrada transição direta no grafo até este requisito."
                        )
                    else:
                        path_parts = []
                        for node in path:
                            if ":" in node:
                                s_id, l_str = node.split(":", 1)
                                s_name = format_skill_name(s_id, skills_catalog)
                                l_lbl = ProficiencyLevel(l_str).label
                                path_parts.append(
                                    f'<span class="path-node">{s_name} ({l_lbl})</span>'
                                )
                            else:
                                path_parts.append(
                                    f'<span class="path-node">{node}</span>'
                                )
                        path_html = '<span class="path-arrow"> &rarr; </span>'.join(
                            path_parts
                        )
                        st.markdown(
                            f"<strong>Caminho Mínimo:</strong> {path_html}",
                            unsafe_allow_html=True,
                        )
                        st.caption(f"Distância acumulada de aprendizado: {dist:.1f}")

                    st.markdown("</div>", unsafe_allow_html=True)

                # Graph Representation Section
                st.divider()
                st.markdown(
                    '<p class="section-header">🕸️ Visualização dos Menores Caminhos no Grafo</p>',
                    unsafe_allow_html=True,
                )

                view_mode = st.radio(
                    "Modo de visualização:",
                    options=[
                        "Caminhos separados por requisito",
                        "União dos menores caminhos",
                    ],
                    index=0,
                    horizontal=True,
                    help="Escolha entre inspecionar o menor caminho de um requisito individualmente ou visualizar a união de todos os menores caminhos.",
                )

                if view_mode == "Caminhos separados por requisito":
                    req_options = {
                        i: f"{s['skill_name']} {str(s['required_level']).lower()}"
                        for i, s in enumerate(career_steps)
                    }

                    selected_idx = st.selectbox(
                        "Selecione o requisito da vaga para inspecionar:",
                        options=list(req_options.keys()),
                        format_func=lambda i: req_options[i],
                    )

                    selected_step = career_steps[selected_idx]

                    # Contextualization card and narrative
                    render_path_summary(
                        step=selected_step,
                        profile=current_profile,
                        target_job=target_job,
                        skills_catalog=skills_catalog,
                    )

                    if selected_step.get("status") == "inalcancavel" or (
                        not selected_step.get("is_satisfied")
                        and not selected_step.get("path")
                    ):
                        st.warning(
                            "⚠️ Requisito inalcançável: não há caminho disponível no grafo para este requisito a partir do perfil atual."
                        )
                    else:
                        if selected_step.get("is_satisfied"):
                            single_edges = [
                                ("PROFILE", str(selected_step["target_vertex"]), 0.0)
                            ]
                        else:
                            p = list(selected_step["path"])
                            single_edges = [("PROFILE", p[0], 0.0)]
                            for i in range(len(p) - 1):
                                u, v = p[i], p[i + 1]
                                w = graph.get_edge_weight(u, v) or 1.0
                                single_edges.append((u, v, w))

                        render_graph_network(
                            edges=single_edges,
                            profile=current_profile,
                            target_job=target_job,
                            skills_catalog=skills_catalog,
                            distances_map=distances_map,
                        )

                else:
                    st.info(
                        "ℹ️ **União dos Menores Caminhos:** Esta visualização agrega todos os menores caminhos calculados "
                        "pelo algoritmo de Dijkstra para cada requisito da vaga. Os nós compartilhados são unificados visualmente. "
                        "Note que essa união não representa necessariamente um único caminho global ótimo percorrido em sequência."
                    )

                    union_edges_set: set[tuple[str, str, float]] = set()
                    for step in career_steps:
                        if step.get("is_satisfied"):
                            union_edges_set.add(
                                ("PROFILE", str(step["target_vertex"]), 0.0)
                            )
                        elif step.get("status") != "inalcancavel" and step.get("path"):
                            p = list(step["path"])
                            union_edges_set.add(("PROFILE", p[0], 0.0))
                            for i in range(len(p) - 1):
                                u, v = p[i], p[i + 1]
                                w = graph.get_edge_weight(u, v) or 1.0
                                union_edges_set.add((u, v, w))

                    if union_edges_set:
                        render_graph_network(
                            edges=sorted(union_edges_set),
                            profile=current_profile,
                            target_job=target_job,
                            skills_catalog=skills_catalog,
                            distances_map=distances_map,
                        )
                    else:
                        st.warning(
                            "⚠️ Nenhum caminho disponível no grafo para visualização na união."
                        )


if __name__ == "__main__":
    main()
