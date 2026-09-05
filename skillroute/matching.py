"""Text normalization, technical match, context match, and career path calculations."""

import re
import unicodedata

from skillroute.graph import AdjacencyListGraph, dijkstra, reconstruct_path
from skillroute.models import (
    CandidateProfile,
    Job,
    ProficiencyLevel,
    RequirementMatchDetail,
    RoleDefinition,
    RoleTaxonomy,
    SkillDefinition,
)

# Context scoring point constants
CONTEXT_POINTS_SAME_AREA = 50.0
CONTEXT_POINTS_RELATED_AREA = 25.0
CONTEXT_POINTS_SAME_ROLE = 30.0
CONTEXT_POINTS_RELATED_ROLE = 15.0
CONTEXT_POINTS_SAME_SENIORITY = 20.0
CONTEXT_POINTS_ADJACENT_SENIORITY = 10.0

# Virtual profile graph vertex key
VIRTUAL_PROFILE_NODE = "PROFILE"

# Related area mappings
RELATED_AREAS_MAP: dict[str, set[str]] = {
    "software_development": {"qa_testing", "devops_platform"},
    "devops_platform": {"software_development", "data_engineering"},
    "data_engineering": {"data_analytics", "ai_machine_learning", "devops_platform"},
    "ai_machine_learning": {
        "data_engineering",
        "data_analytics",
        "software_development",
    },
    "data_analytics": {"data_engineering", "ai_machine_learning", "product"},
    "product": {"data_analytics", "qa_testing", "software_development"},
    "qa_testing": {"software_development", "devops_platform"},
}


def normalize_text(text: str) -> str:
    """Normalize text by converting to lowercase, removing accents and punctuation."""
    if not text:
        return ""
    nfkd_form = unicodedata.normalize("NFKD", text)
    clean = "".join(c for c in nfkd_form if not unicodedata.combining(c))
    clean = clean.lower()
    clean = clean.replace("-", " ")
    clean = re.sub(r"[^\w\s]", "", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def normalize_skill_name(
    raw_name: str, skills: list[SkillDefinition] | None = None
) -> str:
    """Resolve a raw skill input string to its canonical skill_id."""
    cleaned = normalize_text(raw_name)
    if not cleaned:
        return ""

    if skills:
        for skill in skills:
            if (
                normalize_text(skill.id) == cleaned
                or normalize_text(skill.name) == cleaned
            ):
                return skill.id
            for alias in skill.aliases:
                if normalize_text(alias) == cleaned:
                    return skill.id
    return raw_name.strip()


def resolve_role_family(title: str, taxonomy: RoleTaxonomy) -> RoleDefinition | None:
    """Resolve a job title to its canonical RoleDefinition in the taxonomy."""
    if not title or not taxonomy.roles:
        return None

    clean_title = normalize_text(title)

    # 1. Exact match on ID, Name or Aliases
    for role in taxonomy.roles:
        if (
            normalize_text(role.id) == clean_title
            or normalize_text(role.name) == clean_title
        ):
            return role
        for alias in role.aliases:
            if normalize_text(alias) == clean_title:
                return role

    # 2. Substring match on aliases
    for role in taxonomy.roles:
        for alias in role.aliases:
            clean_alias = normalize_text(alias)
            if clean_alias and (
                clean_alias in clean_title or clean_title in clean_alias
            ):
                return role

    # 3. Context keyword matching
    best_role = None
    max_keyword_matches = 0
    title_words = set(clean_title.split())

    for role in taxonomy.roles:
        matches = sum(
            1 for kw in role.context_keywords if normalize_text(kw) in title_words
        )
        if matches > max_keyword_matches:
            max_keyword_matches = matches
            best_role = role

    return best_role if max_keyword_matches > 0 else None


def calculate_technical_match(
    profile: CandidateProfile,
    job: Job,
    skills_catalog: list[SkillDefinition] | None = None,
) -> tuple[float, list[RequirementMatchDetail]]:
    """Calculate technical match score between candidate skills and job requirements.

    Formula:
        level_ratio = min(candidate_level / required_level, 1.0)
        requirement_score = level_ratio * weight
        technical_percentage = (sum(requirement_score) / sum(weight)) * 100
    """
    if not job.requirements:
        return 100.0, []

    skills_name_map = {}
    if skills_catalog:
        skills_name_map = {s.id: s.name for s in skills_catalog}

    details: list[RequirementMatchDetail] = []
    total_earned = 0.0
    total_max_weight = 0.0

    for req in job.requirements:
        cand_level = profile.get_skill_level(req.skill_id)
        cand_score = cand_level.score
        req_score = req.minimum_level.score

        if req_score <= 0:
            req_score = 1

        level_ratio = min(cand_score / req_score, 1.0)
        pts = level_ratio * req.weight
        total_earned += pts
        total_max_weight += req.weight

        is_satisfied = cand_score >= req_score
        if is_satisfied:
            status = "atendido"
        elif cand_score > 0:
            status = "parcial"
        else:
            status = "ausente"

        display_name = skills_name_map.get(
            req.skill_id, req.skill_id.replace("_", " ").title()
        )

        detail = RequirementMatchDetail(
            requirement=req,
            skill_name=display_name,
            candidate_level=cand_level,
            required_level=req.minimum_level,
            satisfaction_ratio=level_ratio,
            distance=0.0 if is_satisfied else None,
            shortest_path=[],
            is_satisfied=is_satisfied,
            status=status,
            requirement_score=pts,
            max_weight=req.weight,
            proximity_score=100.0 if is_satisfied else 0.0,
        )
        details.append(detail)

    if total_max_weight <= 0:
        return 100.0, details

    technical_percentage = (total_earned / total_max_weight) * 100.0
    return min(max(technical_percentage, 0.0), 100.0), details


def get_context_breakdown(
    profile: CandidateProfile,
    job: Job,
    taxonomy: RoleTaxonomy | None = None,
) -> dict[str, object]:
    """Calculate detailed contextual match sub-scores (Area: 50 pts, Role: 30 pts, Seniority: 20 pts)."""
    if not profile.has_sufficient_data:
        return {
            "area_pts": 0.0,
            "area_desc": "Perfil não avaliado (0.0 pts)",
            "role_pts": 0.0,
            "role_desc": "Perfil não avaliado (0.0 pts)",
            "seniority_pts": 0.0,
            "seniority_desc": "Perfil não avaliado (0.0 pts)",
            "total_pts": 0.0,
        }

    clean_p_area = normalize_text(profile.area)
    clean_j_area = normalize_text(job.area)

    p_area_label = (
        taxonomy.areas.get(profile.area, profile.area) if taxonomy else profile.area
    )
    j_area_label = taxonomy.areas.get(job.area, job.area) if taxonomy else job.area

    # 1. Area match (max 50 pts)
    area_pts = 0.0
    if (
        clean_p_area == clean_j_area
        or clean_p_area in clean_j_area
        or clean_j_area in clean_p_area
    ):
        area_pts = CONTEXT_POINTS_SAME_AREA
        area_desc = f"Mesma área ({j_area_label}): +{area_pts:.0f} pts (máx: 50)"
    else:
        p_related = RELATED_AREAS_MAP.get(job.area, set())
        if profile.area in p_related or any(r in clean_p_area for r in p_related):
            area_pts = CONTEXT_POINTS_RELATED_AREA
            area_desc = f"Área correlata ({p_area_label} ↔ {j_area_label}): +{area_pts:.0f} pts (máx: 50)"
        else:
            area_pts = 0.0
            area_desc = (
                f"Áreas distintas ({p_area_label} vs {j_area_label}): 0 pts (máx: 50)"
            )

    # 2. Role family match (max 30 pts)
    role_pts = 0.0
    role_desc = "Cargos distintos: 0 pts (máx: 30)"
    if profile.target_role and taxonomy:
        p_role = resolve_role_family(profile.target_role, taxonomy)
        j_role = resolve_role_family(job.canonical_role or job.title, taxonomy)

        if p_role and j_role:
            if p_role.id == j_role.id:
                role_pts = CONTEXT_POINTS_SAME_ROLE
                role_desc = f"Mesma família de cargo ({p_role.name}): +{role_pts:.0f} pts (máx: 30)"
            elif p_role.area == j_role.area:
                role_pts = CONTEXT_POINTS_RELATED_ROLE
                role_desc = f"Cargo na mesma área ({p_role.name} ↔ {j_role.name}): +{role_pts:.0f} pts (máx: 30)"
            else:
                role_pts = 0.0
                role_desc = f"Famílias distintas ({p_role.name} vs {j_role.name}): 0 pts (máx: 30)"
        elif clean_p_area == clean_j_area:
            role_pts = CONTEXT_POINTS_SAME_ROLE
            role_desc = (
                f"Cargo alinhado à área ({j_area_label}): +{role_pts:.0f} pts (máx: 30)"
            )
    elif clean_p_area == clean_j_area:
        role_pts = CONTEXT_POINTS_SAME_ROLE
        role_desc = (
            f"Cargo alinhado à área ({j_area_label}): +{role_pts:.0f} pts (máx: 30)"
        )
    elif area_pts > 0:
        role_pts = CONTEXT_POINTS_RELATED_ROLE
        role_desc = "Cargo em área correlata: +15 pts (máx: 30)"

    # 3. Seniority match (max 20 pts)
    diff = abs(profile.seniority.order - job.seniority.order)
    if diff == 0:
        seniority_pts = CONTEXT_POINTS_SAME_SENIORITY
        seniority_desc = f"Mesma senioridade ({job.seniority.label}): +{seniority_pts:.0f} pts (máx: 20)"
    elif diff == 1:
        seniority_pts = CONTEXT_POINTS_ADJACENT_SENIORITY
        seniority_desc = f"Senioridade adjacente ({profile.seniority.label} vs {job.seniority.label}): +{seniority_pts:.0f} pts (máx: 20)"
    else:
        seniority_pts = 0.0
        seniority_desc = f"Diferença > 1 nível ({profile.seniority.label} vs {job.seniority.label}): 0 pts (máx: 20)"

    total_context = min(max(area_pts + role_pts + seniority_pts, 0.0), 100.0)
    return {
        "area_pts": area_pts,
        "area_desc": area_desc,
        "role_pts": role_pts,
        "role_desc": role_desc,
        "seniority_pts": seniority_pts,
        "seniority_desc": seniority_desc,
        "total_pts": total_context,
    }


def calculate_context_match(
    profile: CandidateProfile,
    job: Job,
    taxonomy: RoleTaxonomy | None = None,
) -> float:
    """Calculate contextual match score (Area: 50 pts, Role: 30 pts, Seniority: 20 pts)."""
    return float(get_context_breakdown(profile, job, taxonomy)["total_pts"])


def build_profile_augmented_graph(
    profile: CandidateProfile,
    base_graph: AdjacencyListGraph,
    skills_catalog: list[SkillDefinition] | None = None,
) -> tuple[AdjacencyListGraph, str]:
    """Create graph with virtual PROFILE node connected with weight 0 to candidate skills."""
    augmented = AdjacencyListGraph()

    for src, tgt, weight in base_graph.get_all_edges():
        augmented.add_edge(src, tgt, weight, directed=True)

    virtual_node = VIRTUAL_PROFILE_NODE
    augmented.add_vertex(virtual_node)

    all_skill_ids: set[str] = set()
    if skills_catalog:
        all_skill_ids = {s.id for s in skills_catalog}
    else:
        for v in base_graph.vertices:
            if ":" in v:
                all_skill_ids.add(v.split(":", 1)[0])

    levels_order = ["nenhum", "basico", "intermediario", "avancado", "especialista"]

    for skill_id in all_skill_ids:
        declared_level = profile.get_skill_level(skill_id)
        declared_idx = declared_level.score

        # Connect PROFILE to declared level and all lower levels with cost 0
        for idx in range(declared_idx + 1):
            lvl_name = levels_order[idx]
            target_vertex = f"{skill_id}:{lvl_name}"
            augmented.add_edge(virtual_node, target_vertex, 0.0, directed=True)

    return augmented, virtual_node


def run_profile_dijkstra(
    profile: CandidateProfile,
    base_graph: AdjacencyListGraph,
    skills_catalog: list[SkillDefinition] | None = None,
) -> tuple[dict[str, float], dict[str, str | None], str]:
    """Execute Dijkstra from candidate PROFILE node."""
    augmented_graph, virtual_node = build_profile_augmented_graph(
        profile, base_graph, skills_catalog
    )
    distances, previous = dijkstra(augmented_graph, [virtual_node])
    return distances, previous, virtual_node


def calculate_career_path(
    profile: CandidateProfile,
    job: Job,
    base_graph: AdjacencyListGraph,
    skills_catalog: list[SkillDefinition] | None = None,
) -> list[dict[str, object]]:
    """Compute individual shortest paths and steps from candidate profile to job requirements."""
    skills_name_map = {}
    if skills_catalog:
        skills_name_map = {s.id: s.name for s in skills_catalog}

    if not profile.has_sufficient_data:
        results: list[dict[str, object]] = []
        for req in job.requirements:
            display_name = skills_name_map.get(
                req.skill_id, req.skill_id.replace("_", " ").title()
            )
            results.append(
                {
                    "skill_id": req.skill_id,
                    "skill_name": display_name,
                    "target_vertex": req.vertex_key,
                    "required_level": req.minimum_level.label,
                    "candidate_level": ProficiencyLevel.NENHUM.label,
                    "status": "ausente",
                    "distance": None,
                    "path": [],
                    "is_satisfied": False,
                }
            )
        return results

    distances, previous, virtual_node = run_profile_dijkstra(
        profile, base_graph, skills_catalog
    )

    results: list[dict[str, object]] = []

    for req in job.requirements:
        cand_level = profile.get_skill_level(req.skill_id)
        target_vertex = req.vertex_key
        display_name = skills_name_map.get(
            req.skill_id, req.skill_id.replace("_", " ").title()
        )

        if cand_level.score >= req.minimum_level.score:
            results.append(
                {
                    "skill_id": req.skill_id,
                    "skill_name": display_name,
                    "target_vertex": target_vertex,
                    "required_level": req.minimum_level.label,
                    "candidate_level": cand_level.label,
                    "status": "atendido",
                    "distance": 0.0,
                    "path": [f"{req.skill_id}:{cand_level.value}", target_vertex]
                    if cand_level != req.minimum_level
                    else [target_vertex],
                    "is_satisfied": True,
                }
            )
        else:
            dist = distances.get(target_vertex, float("inf"))
            if dist == float("inf"):
                results.append(
                    {
                        "skill_id": req.skill_id,
                        "skill_name": display_name,
                        "target_vertex": target_vertex,
                        "required_level": req.minimum_level.label,
                        "candidate_level": cand_level.label,
                        "status": "inalcancavel",
                        "distance": None,
                        "path": [],
                        "is_satisfied": False,
                    }
                )
            else:
                raw_path = reconstruct_path(
                    previous, target_vertex, source=virtual_node
                )
                clean_path = [v for v in raw_path if v != virtual_node]

                results.append(
                    {
                        "skill_id": req.skill_id,
                        "skill_name": display_name,
                        "target_vertex": target_vertex,
                        "required_level": req.minimum_level.label,
                        "candidate_level": cand_level.label,
                        "status": "parcial"
                        if cand_level != ProficiencyLevel.NENHUM
                        else "ausente",
                        "distance": dist,
                        "path": clean_path,
                        "is_satisfied": False,
                    }
                )

    return results
