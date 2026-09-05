"""Directed weighted graph representation and manual Dijkstra shortest path algorithm."""

import heapq


class AdjacencyListGraph:
    """Directed graph using an adjacency list representation with non-negative edge weights."""

    def __init__(self) -> None:
        self._adj: dict[str, dict[str, float]] = {}

    def add_vertex(self, vertex: str) -> None:
        if vertex not in self._adj:
            self._adj[vertex] = {}

    def add_edge(
        self, source: str, target: str, weight: float, directed: bool = True
    ) -> None:
        if weight < 0:
            raise ValueError(
                f"Negative edge weights not supported ({weight}) from '{source}' to '{target}'."
            )
        self.add_vertex(source)
        self.add_vertex(target)
        self._adj[source][target] = weight

        if not directed:
            self._adj[target][source] = weight

    def get_neighbors(self, vertex: str) -> list[tuple[str, float]]:
        if vertex not in self._adj:
            return []
        return list(self._adj[vertex].items())

    def get_edge_weight(self, source: str, target: str) -> float | None:
        return self._adj.get(source, {}).get(target)

    def has_vertex(self, vertex: str) -> bool:
        return vertex in self._adj

    def has_edge(self, source: str, target: str) -> bool:
        return source in self._adj and target in self._adj[source]

    @property
    def vertices(self) -> list[str]:
        return list(self._adj.keys())

    @property
    def vertex_count(self) -> int:
        return len(self._adj)

    @property
    def edge_count(self) -> int:
        return sum(len(neighbors) for neighbors in self._adj.values())

    def get_all_edges(self) -> list[tuple[str, str, float]]:
        edges: list[tuple[str, str, float]] = []
        for src, neighbors in self._adj.items():
            for tgt, weight in neighbors.items():
                edges.append((src, tgt, weight))
        return edges

    def __repr__(self) -> str:
        return (
            f"AdjacencyListGraph(vertices={self.vertex_count}, edges={self.edge_count})"
        )


def dijkstra(
    graph: AdjacencyListGraph, sources: list[str]
) -> tuple[dict[str, float], dict[str, str | None]]:
    """Compute shortest paths on a weighted graph using manual min-heap Dijkstra with heapq.

    Args:
        graph: AdjacencyListGraph with non-negative edge weights.
        sources: Source vertex identifiers from which distances start at 0.

    Returns:
        tuple (distances, previous):
            - distances: Dict mapping vertex key to shortest distance.
            - previous: Dict mapping vertex key to predecessor vertex.
    """
    if not sources:
        return {}, {}

    all_vertices = graph.vertices
    distances: dict[str, float] = {v: float("inf") for v in all_vertices}
    previous: dict[str, str | None] = dict.fromkeys(all_vertices)

    queue: list[tuple[float, str]] = []

    for source in sources:
        distances[source] = 0.0
        previous[source] = None
        heapq.heappush(queue, (0.0, source))

    while queue:
        current_distance, current_vertex = heapq.heappop(queue)

        # Lazy deletion of outdated queue entries
        if current_distance > distances.get(current_vertex, float("inf")):
            continue

        for neighbor, weight in graph.get_neighbors(current_vertex):
            if weight < 0:
                raise ValueError(
                    f"Negative edge weight encountered ({weight}) "
                    f"from '{current_vertex}' to '{neighbor}'."
                )

            new_distance = current_distance + weight

            if new_distance < distances.get(neighbor, float("inf")):
                distances[neighbor] = new_distance
                previous[neighbor] = current_vertex
                heapq.heappush(queue, (new_distance, neighbor))

    return distances, previous


def reconstruct_path(
    previous: dict[str, str | None],
    target: str,
    source: str | None = None,
) -> list[str]:
    """Reconstruct shortest path from predecessor map.

    Args:
        previous: Map of vertex -> predecessor.
        target: Target destination vertex.
        source: Optional source vertex.

    Returns:
        List of vertex keys from source to target.
    """
    if target not in previous:
        return []

    path: list[str] = []
    current: str | None = target
    visited: set[str] = set()

    while current is not None:
        if current in visited:
            break  # Cycle protection
        visited.add(current)
        path.append(current)

        if source is not None and current == source:
            break
        current = previous.get(current)

    path.reverse()

    if source is not None and (not path or path[0] != source):
        return []

    return path
