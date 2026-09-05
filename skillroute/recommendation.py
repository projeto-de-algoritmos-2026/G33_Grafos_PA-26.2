"""Job recommendation ranking, score composition, and deterministic explanation."""

from skillroute.graph import AdjacencyListGraph, reconstruct_path
from skillroute.matching import (
    calculate_context_match,
    calculate_technical_match,
    get_context_breakdown,
    run_profile_dijkstra,
)
from skillroute.models import (
    CandidateProfile,
    Job,
    JobRecommendation,
    MatchClassification,
    ProficiencyLevel,
    RequirementMatchDetail,
    RoleTaxonomy,
    SkillDefinition,
)

# Scoring weights
TECHNICAL_MATCH_WEIGHT = 0.60
CONTEXT_MATCH_WEIGHT = 0.20
DIJKSTRA_PROXIMITY_WEIGHT = 0.20


def generate_justification(
    recommendation_data: dict[str, object],
    profile: CandidateProfile | None = None,
    taxonomy: RoleTaxonomy | None = None,
) -> str:
    """Generate a deterministic, fact-based textual explanation of the score separated by dimension."""
    if recommendation_data.get("status") == "not_evaluated":
        return (
            "Perfil ainda não avaliado. Preencha suas competências e "
            "informações profissionais para calcular a compatibilidade com esta vaga."
        )

    job = recommendation_data.get("job")
    final_pct = float(recommendation_data["final_percentage"])
    tech_pct = float(recommendation_data["technical_percentage"])
    ctx_pct = float(recommendation_data["context_percentage"])
    prox_pct = float(recommendation_data["proximity_percentage"])
    details = list(recommendation_data["details"])

    satisfied = [d for d in details if d.is_satisfied]
    partials = [d for d in details if d.status == "parcial"]
    missing = [d for d in details if d.status == "ausente"]

    total_req_points = sum(d.requirement_score for d in details)
    total_req_max_points = sum(d.max_weight for d in details)

    lines = [
        f"Compatibilidade Consolidada: {final_pct:.1f}% ({recommendation_data['classification'].value})",
        "Fórmula: (60% × Match Técnico) + (20% × Contexto) + (20% × Proximidade por Dijkstra)",
        f"Cálculo: (0.60 × {tech_pct:.1f}) + (0.20 × {ctx_pct:.1f}) + (0.20 × {prox_pct:.1f}) = {final_pct:.1f}%",
        "",
        "============================================================",
        f"1. MATCH TÉCNICO (Peso: 60%) — Nota: {tech_pct:.1f}% ({0.6 * tech_pct:.1f} pts)",
        "============================================================",
        f"• Como é calculado: Soma dos pontos obtidos ({total_req_points:.1f}) dividida pela soma dos pesos dos requisitos ({total_req_max_points:.1f}).",
        f"• Requisitos atendidos integralmente: {len(satisfied)} de {len(details)}.",
    ]

    if satisfied:
        top_satisfied = [
            f"{d.skill_name} ({d.candidate_level.label})" for d in satisfied[:4]
        ]
        lines.append(f"• Competências já dominadas: {', '.join(top_satisfied)}.")

    if partials:
        for p in partials[:3]:
            ratio_pct = p.satisfaction_ratio * 100.0
            lines.append(
                f"• Atendimento parcial em {p.skill_name}: nível atual {p.candidate_level.label} vs exigido {p.required_level.label} "
                f"({ratio_pct:.0f}% atendido → {p.requirement_score:.1f}/{p.max_weight:.1f} pts)."
            )

    if missing:
        lines.append(
            f"• Requisitos não declarados (0% atendimento): {', '.join(m.skill_name for m in missing[:4])}."
        )

    # 2. Context breakdown
    ctx_lines = [
        "",
        "============================================================",
        f"2. CONTEXTO PROFISSIONAL (Peso: 20%) — Nota: {ctx_pct:.1f}% ({0.2 * ctx_pct:.1f} pts)",
        "============================================================",
        "• Como é calculado: Pontuação por Área (até 50 pts) + Família de Cargo (até 30 pts) + Senioridade (até 20 pts).",
    ]
    if profile and isinstance(job, Job):
        ctx_details = get_context_breakdown(profile, job, taxonomy)
        ctx_lines.extend(
            [
                f"• Área: {ctx_details['area_desc']}",
                f"• Cargo: {ctx_details['role_desc']}",
                f"• Senioridade: {ctx_details['seniority_desc']}",
                f"• Total de Contexto: {ctx_details['area_pts']:.0f} + {ctx_details['role_pts']:.0f} + {ctx_details['seniority_pts']:.0f} = {ctx_pct:.1f}%",
            ]
        )
    else:
        ctx_lines.append(f"• Resultado de contexto calculado: {ctx_pct:.1f}%.")
    lines.extend(ctx_lines)

    # 3. Proximity breakdown
    prox_lines = [
        "",
        "============================================================",
        f"3. PROXIMIDADE À VAGA POR DIJKSTRA (Peso: 20%) — Nota: {prox_pct:.1f}% ({0.2 * prox_pct:.1f} pts)",
        "============================================================",
        "• Como é calculado: Média ponderada da proximidade dos requisitos que ainda faltam.",
        "• Fórmula por requisito: Proximidade = max(0, 100 × (1 - Distância_Dijkstra / 10)).",
    ]

    missing_and_partials = [d for d in details if not d.is_satisfied]
    if missing_and_partials:
        for m in missing_and_partials:
            if m.distance is not None and m.shortest_path:
                clean_path = []
                for v in m.shortest_path:
                    if ":" in v:
                        s_id, l_str = v.split(":", 1)
                        clean_path.append(
                            f"{s_id.replace('_', ' ').title()} ({l_str.title()})"
                        )
                    else:
                        clean_path.append(v)
                path_str = " → ".join(clean_path)
                prox_lines.append(
                    f"• {m.skill_name} (peso {m.max_weight:.1f}): menor caminho {path_str} (distância {m.distance:.1f}) → Proximidade = {m.proximity_score:.1f}%"
                )
            elif m.status == "inalcancavel":
                prox_lines.append(
                    f"• {m.skill_name} (peso {m.max_weight:.1f}): sem transição no grafo → Proximidade = 0.0%"
                )
    else:
        prox_lines.append(
            "• Todos os requisitos já atendidos plenamente → Proximidade = 100.0%"
        )

    lines.extend(prox_lines)
    return "\n".join(lines)


def recommend_jobs(
    profile: CandidateProfile,
    jobs: list[Job],
    graph: AdjacencyListGraph,
    taxonomy: RoleTaxonomy | None = None,
    skills_catalog: list[SkillDefinition] | None = None,
) -> list[JobRecommendation]:
    """Rank job vacancies for a candidate profile based on technical, context, and Dijkstra proximity."""
    if not profile.has_sufficient_data:
        recommendations = []
        for job in jobs:
            enriched_details = []
            for req in job.requirements:
                skill_name = req.skill_id.replace("_", " ").title()
                if skills_catalog:
                    for s in skills_catalog:
                        if s.id == req.skill_id:
                            skill_name = s.name
                            break
                enriched_details.append(
                    RequirementMatchDetail(
                        requirement=req,
                        skill_name=skill_name,
                        candidate_level=ProficiencyLevel.NENHUM,
                        required_level=req.minimum_level,
                        satisfaction_ratio=0.0,
                        distance=None,
                        shortest_path=[],
                        is_satisfied=False,
                        status="ausente",
                        requirement_score=0.0,
                        max_weight=req.weight,
                        proximity_score=0.0,
                    )
                )

            rec_data = {
                "job": job,
                "final_percentage": 0.0,
                "classification": MatchClassification.NAO_AVALIADO,
                "technical_percentage": 0.0,
                "context_percentage": 0.0,
                "proximity_percentage": 0.0,
                "status": "not_evaluated",
                "total_cost": 0.0,
                "weighted_gap_cost": 0.0,
                "details": enriched_details,
                "union_path_edges": [],
            }
            rec_data["justification"] = generate_justification(
                rec_data, profile=profile, taxonomy=taxonomy
            )
            recommendations.append(JobRecommendation.model_validate(rec_data))
        return recommendations

    # Run single Dijkstra from candidate profile virtual origin node
    distances, previous, virtual_node = run_profile_dijkstra(
        profile, graph, skills_catalog
    )

    recommendations: list[JobRecommendation] = []

    for job in jobs:
        # Technical match calculation
        tech_pct, tech_details = calculate_technical_match(profile, job, skills_catalog)

        # Process shortest paths and proximity for each requirement
        enriched_details: list[RequirementMatchDetail] = []
        total_gap_distance = 0.0
        missing_gap_weight_sum = 0.0
        missing_gap_distance_weighted = 0.0
        missing_weighted_prox = 0.0
        missing_req_weights = 0.0
        union_edges_set: set[tuple[str, str, float]] = set()

        for d in tech_details:
            target_vertex = d.requirement.vertex_key
            req_weight = d.max_weight
            cand_score = d.candidate_level.score

            if d.is_satisfied:
                dist = 0.0
                prox = 100.0
                status = "atendido"
                path = [target_vertex]
            else:
                raw_dist = distances.get(target_vertex, float("inf"))
                if raw_dist == float("inf"):
                    dist = None
                    path = []
                    prox = 0.0
                    status = "inalcancavel"
                else:
                    dist = raw_dist
                    total_gap_distance += dist
                    missing_gap_weight_sum += req_weight
                    missing_gap_distance_weighted += dist * req_weight
                    prox = max(0.0, 100.0 * (1.0 - (dist / 10.0)))
                    status = "parcial" if cand_score > 0 else "ausente"

                    raw_path = reconstruct_path(
                        previous, target_vertex, source=virtual_node
                    )
                    path = [v for v in raw_path if v != virtual_node]

                    for i in range(len(path) - 1):
                        u, v = path[i], path[i + 1]
                        w = graph.get_edge_weight(u, v) or 0.0
                        union_edges_set.add((u, v, w))

                missing_req_weights += req_weight
                missing_weighted_prox += prox * req_weight

            enriched_detail = d.model_copy(
                update={
                    "distance": dist,
                    "shortest_path": path,
                    "proximity_score": prox,
                    "status": status,
                }
            )
            enriched_details.append(enriched_detail)

        # Proximity percentage
        if missing_req_weights > 0:
            proximity_pct = missing_weighted_prox / missing_req_weights
        else:
            proximity_pct = 100.0
        proximity_pct = min(max(proximity_pct, 0.0), 100.0)

        # Context match calculation
        context_pct = calculate_context_match(profile, job, taxonomy)

        # Composite Final Percentage
        final_pct = (
            TECHNICAL_MATCH_WEIGHT * tech_pct
            + CONTEXT_MATCH_WEIGHT * context_pct
            + DIJKSTRA_PROXIMITY_WEIGHT * proximity_pct
        )
        final_pct = min(max(final_pct, 0.0), 100.0)

        classification = MatchClassification.from_percentage(
            final_pct, is_evaluated=True
        )

        weighted_gap_cost = (
            (missing_gap_distance_weighted / missing_gap_weight_sum)
            if missing_gap_weight_sum > 0
            else 0.0
        )

        rec_data = {
            "job": job,
            "final_percentage": final_pct,
            "classification": classification,
            "technical_percentage": tech_pct,
            "context_percentage": context_pct,
            "proximity_percentage": proximity_pct,
            "status": "evaluated",
            "total_cost": total_gap_distance,
            "weighted_gap_cost": weighted_gap_cost,
            "details": enriched_details,
            "union_path_edges": sorted(union_edges_set),
        }
        rec_data["justification"] = generate_justification(
            rec_data, profile=profile, taxonomy=taxonomy
        )

        recommendations.append(JobRecommendation.model_validate(rec_data))

    # Deterministic sorting
    recommendations.sort(
        key=lambda r: (
            -r.final_percentage,
            -r.technical_percentage,
            r.total_cost,
            r.job.id,
        )
    )

    return recommendations
