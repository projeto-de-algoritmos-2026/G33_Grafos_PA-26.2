"""Data loader and graph builder using importlib.resources."""

import importlib.resources
import json
from pathlib import Path
from typing import Any

from skillroute.graph import AdjacencyListGraph
from skillroute.models import (
    Job,
    RoleTaxonomy,
    SkillDefinition,
    SkillRelation,
)

# Cost of progressing between sequential levels within the same skill
INTERNAL_PROGRESSION_COSTS: dict[tuple[str, str], float] = {
    ("nenhum", "basico"): 2.0,
    ("basico", "intermediario"): 3.0,
    ("intermediario", "avancado"): 4.0,
    ("avancado", "especialista"): 5.0,
}


def _read_json(filename: str) -> Any:
    """Read a JSON file from skillroute.data package."""
    try:
        content = (
            importlib.resources.files("skillroute.data")
            .joinpath(filename)
            .read_text(encoding="utf-8")
        )
    except Exception:
        fallback = Path(__file__).resolve().parent / "data" / filename
        content = fallback.read_text(encoding="utf-8")
    return json.loads(content)


class DataLoader:
    """Loads JSON datasets and builds the domain skill graph."""

    def load_taxonomy(self) -> RoleTaxonomy:
        data = _read_json("role_taxonomy.json")
        return RoleTaxonomy.model_validate(data)

    def load_skills(self) -> list[SkillDefinition]:
        raw_list = _read_json("skills.json")
        return [SkillDefinition.model_validate(item) for item in raw_list]

    def load_jobs(self) -> list[Job]:
        raw_list = _read_json("jobs.json")
        return [Job.model_validate(item) for item in raw_list]

    def load_skill_relations(self) -> list[SkillRelation]:
        raw_list = _read_json("skill_relations.json")
        return [SkillRelation.model_validate(item) for item in raw_list]

    def build_graph(self) -> AdjacencyListGraph:
        """Construct graph with expanded proficiency states and cross-technology relations."""
        graph = AdjacencyListGraph()
        skills = self.load_skills()
        levels = ["nenhum", "basico", "intermediario", "avancado", "especialista"]

        # 1. Expand each canonical skill into 5 vertices and connect internal progressions
        for skill in skills:
            s_id = skill.id
            for lvl in levels:
                graph.add_vertex(f"{s_id}:{lvl}")

            for (from_lvl, to_lvl), cost in INTERNAL_PROGRESSION_COSTS.items():
                graph.add_edge(
                    f"{s_id}:{from_lvl}", f"{s_id}:{to_lvl}", cost, directed=True
                )

        # 2. Add cross-technology relations
        relations = self.load_skill_relations()
        for rel in relations:
            graph.add_edge(rel.source, rel.target, rel.cost, directed=True)

        return graph
