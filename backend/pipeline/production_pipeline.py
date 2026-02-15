"""
PRODUCTION PIPELINE ORCHESTRATOR
Coordinates the complete drug repurposing workflow
Uses real public databases (OpenTargets, ChEMBL, DGIdb)
"""

import asyncio
import logging
from typing import Dict, List, Optional
import time

from .data_fetcher import ProductionDataFetcher
from .graph_builder import ProductionGraphBuilder
from .scorer import ProductionScorer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProductionPipeline:
    """
    Main pipeline for drug repurposing analysis.
    Integrates multiple public databases and scoring algorithms.
    """
    
    def __init__(self):
        self.data_fetcher = ProductionDataFetcher()
        self.graph_builder = ProductionGraphBuilder()
        self.scorer = None
        
        # Cache for repeated queries
        self.disease_cache = {}
        self.drugs_cache = None
    
    async def analyze_disease(
        self,
        disease_name: str,
        min_score: float = 0.2,
        max_results: int = 20
    ) -> Dict:
        """
        Main entry point: Analyze a disease and find drug candidates.
        
        Args:
            disease_name: Name of the disease to analyze
            min_score: Minimum score threshold (0-1)
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary with candidates and analysis metadata
        """
        start_time = time.time()
        
        logger.info("="*70)
        logger.info(f"🔬 STARTING ANALYSIS: {disease_name}")
        logger.info("="*70)
        
        # STEP 1: Fetch disease data from OpenTargets
        logger.info("\n📊 Step 1/5: Fetching disease data from OpenTargets...")
        disease_data = await self.data_fetcher.fetch_disease_data(disease_name)
        
        if not disease_data:
            logger.error(f"❌ Disease not found: {disease_name}")
            return {
                'success': False,
                'error': f"Disease '{disease_name}' not found in OpenTargets database",
                'suggestion': "Try searching with full disease name (e.g., 'Parkinson Disease' not 'Parkinsons')"
            }
        
        logger.info(f"✅ Found: {disease_data['name']}")
        logger.info(f"   Genes: {len(disease_data['genes'])}")
        logger.info(f"   Pathways: {len(disease_data['pathways'])}")
        logger.info(f"   Rare disease: {disease_data.get('is_rare', False)}")
        
        # STEP 2: Fetch approved drugs from ChEMBL
        logger.info("\n💊 Step 2/5: Fetching approved drugs from ChEMBL...")
        
        if self.drugs_cache is None:
            drugs_data = await self.data_fetcher.fetch_approved_drugs(limit=500)  # Increased from 500 for better coverage
            self.drugs_cache = drugs_data
            logger.info(f"✅ Fetched {len(drugs_data)} approved drugs (cached for future queries)")
        else:
            drugs_data = self.drugs_cache
            logger.info(f"✅ Using cached drug data ({len(drugs_data)} drugs)")
        
        # STEP 3: Build knowledge graph
        logger.info("\n🕸️  Step 3/5: Building knowledge graph...")
        graph = self.graph_builder.build_graph(disease_data, drugs_data)
        
        graph_stats = self.graph_builder.get_graph_stats()
        logger.info(f"✅ Graph built: {graph_stats['total_nodes']} nodes, {graph_stats['total_edges']} edges")
        
        # STEP 4: Score all drugs
        logger.info("\n🎯 Step 4/5: Scoring drug-disease matches...")
        self.scorer = ProductionScorer(graph)
        
        candidates = []
        for drug in drugs_data:
            score, evidence = self.scorer.score_drug_disease_match(
                drug['name'],
                disease_data['name'],
                disease_data,
                drug
            )
            
            if score >= min_score:
                candidates.append({
                    'drug_name': drug['name'],
                    'drug_id': drug.get('id', ''),
                    'score': score,
                    'confidence': evidence['confidence'],
                    'shared_genes': evidence['shared_genes'],
                    'shared_pathways': evidence['shared_pathways'],
                    'explanation': evidence['explanation'],
                    'indication': drug.get('indication', ''),
                    'mechanism': drug.get('mechanism', ''),
                    'gene_score': evidence['gene_score'],
                    'pathway_score': evidence['pathway_score'],
                    'mechanism_score': evidence['mechanism_score'],
                    'literature_score': evidence['literature_score']
                })
        
        # Sort by score
        candidates.sort(key=lambda x: x['score'], reverse=True)
        
        # Limit results
        candidates = candidates[:max_results]
        
        logger.info(f"✅ Found {len(candidates)} candidates above threshold {min_score}")
        
        # STEP 5: Generate summary
        logger.info("\n📝 Step 5/5: Generating analysis summary...")
        
        elapsed_time = time.time() - start_time
        
        result = {
            'success': True,
            'disease': {
                'name': disease_data['name'],
                'id': disease_data.get('id', ''),
                'description': disease_data.get('description', ''),
                'genes_count': len(disease_data['genes']),
                'pathways_count': len(disease_data['pathways']),
                'is_rare': disease_data.get('is_rare', False),
                'active_trials': disease_data.get('active_trials_count', 0),
                'top_genes': disease_data['genes'][:10]
            },
            'candidates': candidates,
            'metadata': {
                'total_drugs_analyzed': len(drugs_data),
                'candidates_found': len(candidates),
                'min_score_threshold': min_score,
                'graph_stats': graph_stats,
                'analysis_time_seconds': round(elapsed_time, 2),
                'data_sources': [
                    'OpenTargets Platform (disease-gene associations)',
                    'ChEMBL (approved drugs)',
                    'DGIdb (drug-gene interactions)',
                    'ClinicalTrials.gov (active trials)'
                ]
            }
        }
        
        # Print summary
        logger.info("="*70)
        logger.info("✅ ANALYSIS COMPLETE!")
        logger.info("="*70)
        logger.info(f"Disease: {disease_data['name']}")
        logger.info(f"Candidates found: {len(candidates)}")
        logger.info(f"Analysis time: {elapsed_time:.2f}s")
        
        if candidates:
            logger.info("\n🏆 Top 5 candidates:")
            for i, candidate in enumerate(candidates[:5], 1):
                logger.info(f"  {i}. {candidate['drug_name']}")
                logger.info(f"     Score: {candidate['score']:.3f} ({candidate['confidence']} confidence)")
                logger.info(f"     Shared genes: {len(candidate['shared_genes'])}")
                logger.info(f"     Shared pathways: {len(candidate['shared_pathways'])}")
        
        return result
    
    async def close(self):
        """Cleanup resources"""
        await self.data_fetcher.close()
        logger.info("🔒 Pipeline closed")


# Convenience function for quick analysis
async def analyze(disease_name: str, min_score: float = 0.2, max_results: int = 20) -> Dict:
    """
    Quick analysis function.
    
    Example:
        result = await analyze("Parkinson Disease", min_score=0.3)
    """
    pipeline = ProductionPipeline()
    try:
        result = await pipeline.analyze_disease(disease_name, min_score, max_results)
        return result
    finally:
        await pipeline.close()