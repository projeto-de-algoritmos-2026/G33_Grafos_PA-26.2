from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ============================================================================
# Enumerations
# ============================================================================


class ProficiencyLevel(StrEnum):
    """Ordinal proficiency levels for skills."""

    NENHUM = "nenhum"
    BASICO = "basico"
    INTERMEDIARIO = "intermediario"
    AVANCADO = "avancado"
    ESPECIALISTA = "especialista"

    @property
    def score(self) -> int:
        """Numeric score from 0 to 4."""
        mapping = {
            ProficiencyLevel.NENHUM: 0,
            ProficiencyLevel.BASICO: 1,
            ProficiencyLevel.INTERMEDIARIO: 2,
            ProficiencyLevel.AVANCADO: 3,
            ProficiencyLevel.ESPECIALISTA: 4,
        }
        return mapping[self]

    @property
    def label(self) -> str:
        """Portuguese display label."""
        mapping = {
            ProficiencyLevel.NENHUM: "Nenhum",
            ProficiencyLevel.BASICO: "Básico",
            ProficiencyLevel.INTERMEDIARIO: "Intermediário",
            ProficiencyLevel.AVANCADO: "Avançado",
            ProficiencyLevel.ESPECIALISTA: "Especialista",
        }
        return mapping[self]

    @classmethod
    def from_score(cls, score: int) -> "ProficiencyLevel":
        """Convert integer score to ProficiencyLevel."""
        mapping = {
            0: cls.NENHUM,
            1: cls.BASICO,
            2: cls.INTERMEDIARIO,
            3: cls.AVANCADO,
            4: cls.ESPECIALISTA,
        }
        if score not in mapping:
            raise ValueError(f"Score {score} is not a valid proficiency level (0-4).")
        return mapping[score]


class RequirementKind(StrEnum):
    """Importance classification for job requirements."""

    REQUIRED = "required"
    DESIRABLE = "desirable"

    @property
    def label(self) -> str:
        return "Obrigatório" if self == RequirementKind.REQUIRED else "Desejável"


class Seniority(StrEnum):
    """Seniority levels for candidates and job vacancies."""

    ESTAGIO = "estagio"
    JUNIOR = "junior"
    PLENO = "pleno"
    SENIOR = "senior"
    ESPECIALISTA = "especialista"

    @property
    def order(self) -> int:
        """Ordinal scale for context distance calculation."""
        mapping = {
            Seniority.ESTAGIO: 0,
            Seniority.JUNIOR: 1,
            Seniority.PLENO: 2,
            Seniority.SENIOR: 3,
            Seniority.ESPECIALISTA: 4,
        }
        return mapping[self]

    @property
    def label(self) -> str:
        mapping = {
            Seniority.ESTAGIO: "Estágio",
            Seniority.JUNIOR: "Júnior",
            Seniority.PLENO: "Pleno",
            Seniority.SENIOR: "Sênior",
            Seniority.ESPECIALISTA: "Especialista",
        }
        return mapping[self]


class MatchClassification(StrEnum):
    """Visual classification bands for recommendations."""

    NAO_AVALIADO = "Perfil ainda não avaliado"
    EXCELENTE = "Excelente compatibilidade"
    BOA = "Boa compatibilidade"
    MODERADA = "Compatibilidade moderada"
    BAIXA = "Baixa compatibilidade"
    MUITO_BAIXA = "Compatibilidade muito baixa"

    @classmethod
    def from_percentage(
        cls, pct: float, is_evaluated: bool = True
    ) -> "MatchClassification":
        if not is_evaluated:
            return cls.NAO_AVALIADO
        if pct >= 80.0:
            return cls.EXCELENTE
        elif pct >= 65.0:
            return cls.BOA
        elif pct >= 50.0:
            return cls.MODERADA
        elif pct >= 30.0:
            return cls.BAIXA
        return cls.MUITO_BAIXA

    @property
    def color(self) -> str:
        mapping = {
            MatchClassification.NAO_AVALIADO: "#64748B",
            MatchClassification.EXCELENTE: "#2E7D32",
            MatchClassification.BOA: "#1976D2",
            MatchClassification.MODERADA: "#F57C00",
            MatchClassification.BAIXA: "#E65100",
            MatchClassification.MUITO_BAIXA: "#C62828",
        }
        return mapping[self]


# ============================================================================
# Domain Models
# ============================================================================


class CandidateSkill(BaseModel):
    """Individual skill and declared level in a candidate profile."""

    model_config = ConfigDict(frozen=True)

    skill_id: str = Field(..., min_length=1, description="Canonical skill identifier")
    level: ProficiencyLevel = Field(
        default=ProficiencyLevel.NENHUM, description="Current proficiency level"
    )

    @model_validator(mode="before")
    @classmethod
    def handle_legacy_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "skill" in data and "skill_id" not in data:
                data["skill_id"] = data["skill"]
        return data

    @property
    def vertex_key(self) -> str:
        """Corresponding vertex key in the graph, e.g., 'python:intermediario'."""
        return f"{self.skill_id}:{self.level.value}"


class CandidateProfile(BaseModel):
    """Profile of a candidate seeking job recommendations."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(default="Candidato", min_length=1)
    area: str = Field(default="software_development", min_length=1)
    target_role: str | None = Field(default=None)
    seniority: Seniority = Field(default=Seniority.JUNIOR)
    skills: list[CandidateSkill] = Field(default_factory=list)

    @property
    def has_sufficient_data(self) -> bool:
        """Check if candidate has provided sufficient information (at least one declared skill)."""
        return any(sk.level != ProficiencyLevel.NENHUM for sk in self.skills)

    def get_skill_level(self, skill_id: str) -> ProficiencyLevel:
        for sk in self.skills:
            if sk.skill_id == skill_id:
                return sk.level
        return ProficiencyLevel.NENHUM

    def get_skill_score(self, skill_id: str) -> int:
        return self.get_skill_level(skill_id).score

    def has_skill(self, skill_id: str) -> bool:
        return self.get_skill_level(skill_id) != ProficiencyLevel.NENHUM


class SkillDefinition(BaseModel):
    """Canonical technology or skill definition."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    aliases: list[str] = Field(default_factory=list)
    area: str = Field(default="software_development")
    related_areas: list[str] = Field(default_factory=list)
    description: str = Field(default="")


class JobRequirement(BaseModel):
    """Skill requirement for a job vacancy."""

    model_config = ConfigDict(frozen=True)

    skill_id: str = Field(..., min_length=1)
    minimum_level: ProficiencyLevel = Field(default=ProficiencyLevel.BASICO)
    kind: RequirementKind = Field(default=RequirementKind.REQUIRED)
    weight: float = Field(default=1.0, gt=0.0)

    @model_validator(mode="before")
    @classmethod
    def handle_legacy_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "skill" in data and "skill_id" not in data:
                data["skill_id"] = data["skill"]
            if "level" in data and "minimum_level" not in data:
                data["minimum_level"] = data["level"]
            if "kind" in data and str(data["kind"]).lower() in (
                "desired",
                "desejavel",
                "opcional",
            ):
                data["kind"] = "desirable"
            elif "kind" in data and str(data["kind"]).lower() in (
                "obrigatorio",
                "required",
            ):
                data["kind"] = "required"
        return data

    @property
    def vertex_key(self) -> str:
        """Target graph vertex, e.g., 'fastapi:basico'."""
        return f"{self.skill_id}:{self.minimum_level.value}"


class Job(BaseModel):
    """Job vacancy definition."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    canonical_role: str | None = Field(default=None)
    area: str = Field(..., min_length=1)
    seniority: Seniority = Field(default=Seniority.JUNIOR)
    company: str = Field(default="Empresa Confidencial")
    location: str = Field(default="Remoto")
    employment_type: str = Field(default="Tempo integral")
    description: str = Field(default="")
    responsibilities: list[str] = Field(default_factory=list)
    requirements: list[JobRequirement] = Field(default_factory=list)
    source: str = Field(default="synthetic")


class RoleDefinition(BaseModel):
    """Canonical role family definition in the taxonomy."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    area: str = Field(..., min_length=1)
    aliases: list[str] = Field(default_factory=list)
    allowed_seniorities: list[str] = Field(default_factory=list)
    context_keywords: list[str] = Field(default_factory=list)


class RoleTaxonomy(BaseModel):
    """Taxonomy catalog for canonical roles and synonyms."""

    model_config = ConfigDict(frozen=True)

    areas: dict[str, str] = Field(default_factory=dict)
    roles: list[RoleDefinition] = Field(default_factory=list)


class SkillRelation(BaseModel):
    """Directed edge representing transition/learning between skill states."""

    model_config = ConfigDict(frozen=True)

    source: str = Field(..., min_length=1)
    target: str = Field(..., min_length=1)
    cost: float = Field(..., ge=0.0)


class RequirementMatchDetail(BaseModel):
    """Detailed breakdown for an individual job requirement."""

    model_config = ConfigDict(frozen=True)

    requirement: JobRequirement
    skill_name: str
    candidate_level: ProficiencyLevel
    required_level: ProficiencyLevel
    satisfaction_ratio: float
    distance: float | None = None
    shortest_path: list[str] = Field(default_factory=list)
    is_satisfied: bool
    status: str
    requirement_score: float
    max_weight: float
    proximity_score: float = 0.0


class JobRecommendation(BaseModel):
    """Complete recommendation score and explanation for a job."""

    model_config = ConfigDict(frozen=True)

    job: Job
    final_percentage: float
    classification: MatchClassification
    technical_percentage: float
    context_percentage: float
    proximity_percentage: float
    status: str = Field(
        default="evaluated", description="'evaluated' or 'not_evaluated'"
    )
    total_cost: float = 0.0
    weighted_gap_cost: float = 0.0
    details: list[RequirementMatchDetail] = Field(default_factory=list)
    justification: str = ""
    union_path_edges: list[tuple[str, str, float]] = Field(default_factory=list)

    @property
    def is_evaluated(self) -> bool:
        return self.status == "evaluated"

    @property
    def satisfied_count(self) -> int:
        return sum(1 for d in self.details if d.is_satisfied)

    @property
    def gap_count(self) -> int:
        return sum(1 for d in self.details if not d.is_satisfied)

    @property
    def unreachable_count(self) -> int:
        return sum(1 for d in self.details if d.status == "inalcancavel")
