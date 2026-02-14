import networkx as nx
from pipeline.data_fetcher import DRUG_DATABASE
from pipeline.graph_builder import KnowledgeGraphBuilder
from models import DrugCandidate

KNOWN_REPURPOSING = {
    ("DB01235", "parkinson"): 1.0,  # Levodopa
    ("DB01367", "parkinson"): 1.0,  # Rasagiline
    ("DB01037", "parkinson"): 1.0,  # Selegiline
    ("DB00331", "parkinson"): 0.7,  # Metformin
    ("DB00331", "diabetes"): 1.0,
    ("DB00331", "cancer"): 0.7,
    ("DB00331", "aging"): 0.6,
    ("DB00877", "parkinson"): 0.6,  # Rapamycin
    ("DB00877", "cancer"): 0.8,
    ("DB00877", "aging"): 0.7,
    ("DB00619", "parkinson"): 0.5,  # Imatinib
    ("DB04868", "parkinson"): 0.6,  # Nilotinib
    ("DB01356", "parkinson"): 0.5,  # Lithium
    ("DB01356", "alzheimer"): 0.5,
    ("DB00313", "parkinson"): 0.4,  # Valproic acid
    ("DB01394", "parkinson"): 0.4,  # Colchicine
    ("DB06742", "parkinson"): 0.7,  # Ambroxol
    ("DB00201", "parkinson"): 0.6,  # Caffeine
    ("DB00549", "parkinson"): 0.6,  # UDCA
    ("DB01276", "parkinson"): 0.6,  # Exenatide
    ("DB01132", "parkinson"): 0.5,  # Pioglitazone
    ("DB08826", "parkinson"): 0.5,  # Deferiprone
}

WEIGHTS = {"gene_target": 0.40, "pathway_overlap": 0.35, "graph_centrality": 0.10, "literature": 0.15}


class RepurposingScorer:

    def __init__(self):
        self.graph_builder = KnowledgeGraphBuilder()

    def score_candidates(self, disease_data: dict, graph: nx.MultiDiGraph, top_k: int = 10, min_score: float = 0.3) -> list:
        disease_genes = set(disease_data.get("genes", []))
        disease_pathways = set(disease_data.get("pathways", []))
        disease_name = disease_data["name"].lower()
        candidates = []

        for drug_key, drug in DRUG_DATABASE.items():
            drug_id = drug["id"]
            drug_genes = set(drug.get("targets", []))
            drug_pathways = set(drug.get("pathways", []))

            shared_genes = disease_genes & drug_genes
            shared_pathways = disease_pathways & drug_pathways

            # Enhanced gene scoring
            if len(disease_genes) > 0:
                gene_target_score = len(shared_genes) / len(disease_genes)
                # Boost score for multiple gene hits
                if len(shared_genes) >= 3:
                    gene_target_score = min(gene_target_score * 1.5, 1.0)
                elif len(shared_genes) >= 2:
                    gene_target_score = min(gene_target_score * 1.2, 1.0)
            else:
                gene_target_score = 0.0

            # Enhanced pathway scoring
            union_pathways = disease_pathways | drug_pathways
            if union_pathways:
                pathway_overlap_score = len(shared_pathways) / len(union_pathways)
                # Boost for critical pathway matches
                if len(shared_pathways) >= 3:
                    pathway_overlap_score = min(pathway_overlap_score * 1.4, 1.0)
                elif len(shared_pathways) >= 2:
                    pathway_overlap_score = min(pathway_overlap_score * 1.2, 1.0)
                elif len(shared_pathways) >= 1:
                    pathway_overlap_score = max(pathway_overlap_score, 0.15)
            else:
                pathway_overlap_score = 0.0

            graph_centrality_score = self._compute_graph_score(graph, disease_data["name"], drug_id)
            literature_score = self._compute_literature_score(drug_id, disease_name)

            composite_score = (
                WEIGHTS["gene_target"] * gene_target_score +
                WEIGHTS["pathway_overlap"] * pathway_overlap_score +
                WEIGHTS["graph_centrality"] * graph_centrality_score +
                WEIGHTS["literature"] * literature_score
            )

            # Only include if there's some overlap or high literature score
            if composite_score < min_score and not shared_genes and not shared_pathways:
                continue

            confidence = "High" if composite_score >= 0.65 else "Medium" if composite_score >= 0.40 else "Low"

            candidates.append(DrugCandidate(
                drug_name=drug["name"],
                drug_id=drug_id,
                original_indication=drug["indication"],
                composite_score=round(composite_score, 4),
                pathway_overlap_score=round(pathway_overlap_score, 4),
                gene_target_score=round(gene_target_score, 4),
                literature_score=round(literature_score, 4),
                shared_genes=sorted(shared_genes),
                shared_pathways=sorted(shared_pathways),
                mechanism=drug["mechanism"],
                explanation="",
                confidence=confidence,
                smiles=drug.get("smiles", "")
            ))

        candidates.sort(key=lambda x: x.composite_score, reverse=True)
        candidates = [c for c in candidates if c.composite_score >= min_score]
        return candidates[:top_k]

    def _compute_graph_score(self, G: nx.MultiDiGraph, disease_name: str, drug_id: str) -> float:
        try:
            UG = G.to_undirected()
            if not UG.has_node(disease_name) or not UG.has_node(drug_id):
                return 0.0
            length = nx.shortest_path_length(UG, disease_name, drug_id)
            # Improved scoring: closer connections = higher score
            return round(max(0.0, 1.0 - (length - 1) * 0.2), 4)
        except:
            return 0.0

    def _compute_literature_score(self, drug_id: str, disease_name: str) -> float:
        best_score = 0.0
        for (did, disease_pattern), score in KNOWN_REPURPOSING.items():
            if did == drug_id and disease_pattern in disease_name:
                best_score = max(best_score, score)
        return best_score