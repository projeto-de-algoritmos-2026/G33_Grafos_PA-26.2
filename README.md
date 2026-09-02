# SkillRoute

Número da Lista: 33<br>
Conteúdo da Disciplina: Algoritmo de Dijkstra e Caminhos Mínimos em Grafos<br>

## Alunos

| Matrícula | Aluno |
| :-- | :-- |
| 22/1022266 | Eric Silveira Gomes |

---

## Sobre

O **SkillRoute** é um sistema acadêmico de recomendação de vagas e planejamento de capacitação técnica em tecnologia, utilizando modelagem de competências em grafos direcionados e o **Algoritmo de Dijkstra**.

O objetivo principal do projeto é superar limitações de casamentos textuais simplistas por meio da representação explícita de relações de dependência, transição e progressão de proficiência entre tecnologias, calculando o menor esforço de aprendizado entre o perfil atual de um candidato e os requisitos exigidos pelo mercado.

---

## Tecnologias Planejadas

* **Linguagem:** Python 3.12+
* **Framework Web:** Streamlit
* **Validação e Tipagem:** Pydantic v2
* **Visualização de Grafos:** PyVis (Network)
* **Qualidade de Código:** Ruff e Make

---

## Funcionalidades Planejadas

* Cadastro interativo de perfil técnico de candidatos;
* Modelagem de competências em múltiplos estados ordinais de proficiência;
* Algoritmo de Dijkstra determinístico para cálculo de menores caminhos de capacitação;
* Recomendação ranqueada com pontuação transparente e justificativas explicáveis;
* Visualização interativa e hierárquica das rotas de aprendizado no grafo.

---

## Instalação e Execução

### 1. Criar e Ativar Ambiente Virtual

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 2. Instalar Dependências

```bash
make install
```

### 3. Executar Aplicação

```bash
make run
```
