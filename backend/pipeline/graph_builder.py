"""
KnowledgeGraphBuilder: constructs a multi-layer heterogeneous graph
connecting diseases, genes, pathways, and drugs.
"""

import networkx as nx
from typing import Optional


class KnowledgeGraphBuilder:
    """Builds a knowledge graph from disease and drug data."""

    def build(self, disease_data: dict) -> nx.MultiDiGraph:
        """
        Construct a heterogeneous multi-graph:
        - Nodes: disease, genes, pathways, drugs
        - Edges: disease→gene, gene→pathway, drug→gene, drug→pathway
        """
        from pipeline.data_fetcher import DRUG_DATABASE
        
        G = nx.MultiDiGraph()
        
        disease_name = disease_data["name"]
        disease_genes = disease_data.get("genes", [])
        disease_pathways = disease_data.get("pathways", [])
        
        # Add disease node
        G.add_node(disease_name, node_type="disease", description=disease_data.get("description", ""))
        
        # Add gene nodes and edges
        for gene in disease_genes:
            G.add_node(gene, node_type="gene")
            score = disease_data.get("gene_scores", {}).get(gene, 0.5)
            G.add_edge(disease_name, gene, relation="associated_with", weight=score)
        
        # Add pathway nodes and edges
        for pathway in disease_pathways:
            G.add_node(pathway, node_type="pathway")
            G.add_edge(disease_name, pathway, relation="involves_pathway", weight=0.7)
        
        # Add drug nodes and their connections
        for drug_key, drug_info in DRUG_DATABASE.items():
            drug_id = drug_info["id"]
            drug_name = drug_info["name"]
            
            G.add_node(
                drug_id,
                node_type="drug",
                name=drug_name,
                indication=drug_info["indication"],
                mechanism=drug_info["mechanism"],
                smiles=drug_info.get("smiles", "")
            )
            
            # Connect drugs to their target genes
            for target in drug_info.get("targets", []):
                if target in disease_genes:  # Only connect if gene is relevant to disease
                    G.add_node(target, node_type="gene")
                    G.add_edge(drug_id, target, relation="targets", weight=0.8)
            
            # Connect drugs to pathways
            for pathway in drug_info.get("pathways", []):
                if pathway in disease_pathways:  # Only connect if pathway is relevant
                    G.add_node(pathway, node_type="pathway")
                    G.add_edge(drug_id, pathway, relation="modulates_pathway", weight=0.6)
        
        return G

    def get_stats(self, G: nx.MultiDiGraph) -> dict:
        """Return graph statistics."""
        node_types = {}
        for node, data in G.nodes(data=True):
            node_type = data.get("node_type", "unknown")
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        return {
            "total_nodes": G.number_of_nodes(),
            "total_edges": G.number_of_edges(),
            "node_types": node_types,
            "density": round(nx.density(G), 4) if G.number_of_nodes() > 0 else 0
        }