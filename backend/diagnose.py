#!/usr/bin/env python3
"""
Diagnostic Script - Find out why no candidates are appearing
Run this to debug your drug repurposing platform
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

async def diagnose():
    print("\n" + "="*70)
    print("🔍 DRUG REPURPOSING PLATFORM - DIAGNOSTIC TOOL")
    print("="*70)
    
    from pipeline.data_fetcher import ProductionDataFetcher
    from pipeline.graph_builder import ProductionGraphBuilder
    from pipeline.scorer import ProductionScorer
    
    fetcher = ProductionDataFetcher()
    
    # Test 1: Fetch disease
    print("\n📊 TEST 1: Fetching Parkinson Disease...")
    disease = await fetcher.fetch_disease_data("Parkinson Disease")
    
    if not disease:
        print("❌ PROBLEM: Disease not found!")
        print("   Solution: Check internet connection and OpenTargets API")
        await fetcher.close()
        return
    
    print(f"✅ Disease found: {disease['name']}")
    print(f"   Genes: {len(disease['genes'])}")
    print(f"   Top genes: {disease['genes'][:10]}")
    print(f"   Pathways: {len(disease['pathways'])}")
    print(f"   Top pathways: {disease['pathways'][:5]}")
    
    # Test 2: Fetch drugs
    print("\n💊 TEST 2: Fetching approved drugs...")
    drugs = await fetcher.fetch_approved_drugs(limit=100)
    
    if not drugs:
        print("❌ PROBLEM: No drugs fetched!")
        await fetcher.close()
        return
    
    print(f"✅ Fetched {len(drugs)} drugs")
    
    # Check if drugs have targets
    drugs_with_targets = [d for d in drugs if d.get('targets')]
    print(f"   Drugs with gene targets: {len(drugs_with_targets)}")
    
    if len(drugs_with_targets) == 0:
        print("❌ PROBLEM: No drugs have gene targets!")
        print("   This means DGIdb enhancement failed")
        print("   Solution: Check DGIdb API connection")
        await fetcher.close()
        return
    
    # Show sample drugs with targets
    print("\n   Sample drugs with targets:")
    for drug in drugs_with_targets[:5]:
        print(f"   - {drug['name']}: {len(drug['targets'])} targets")
        print(f"     Targets: {drug['targets'][:5]}")
    
    # Test 3: Build graph
    print("\n🕸️  TEST 3: Building knowledge graph...")
    builder = ProductionGraphBuilder()
    graph = builder.build_graph(disease, drugs)
    
    print(f"✅ Graph built:")
    print(f"   Nodes: {graph.number_of_nodes()}")
    print(f"   Edges: {graph.number_of_edges()}")
    
    # Test 4: Check for overlaps
    print("\n🎯 TEST 4: Finding drug-disease overlaps...")
    scorer = ProductionScorer(graph)
    
    overlaps_found = 0
    high_scoring_drugs = []
    
    for drug in drugs[:100]:  # Check first 100 drugs
        drug_name = drug['name']
        
        # Get shared genes
        shared_genes = builder.get_shared_genes(drug_name, disease['name'])
        shared_pathways = builder.get_shared_pathways(drug_name, disease['name'])
        
        if shared_genes or shared_pathways:
            overlaps_found += 1
            
            # Score this drug
            score, evidence = scorer.score_drug_disease_match(
                drug_name,
                disease['name'],
                disease,
                drug
            )
            
            if score >= 0.2:
                high_scoring_drugs.append({
                    'name': drug_name,
                    'score': score,
                    'genes': len(shared_genes),
                    'pathways': len(shared_pathways),
                    'evidence': evidence
                })
    
    print(f"   Drugs with ANY overlap: {overlaps_found}")
    print(f"   Drugs scoring >= 0.2: {len(high_scoring_drugs)}")
    
    if len(high_scoring_drugs) == 0:
        print("\n❌ PROBLEM: No drugs score above 0.2!")
        print("\n🔍 Debugging the scoring system...")
        
        # Let's manually check a few known drugs
        test_drugs = ['Nilotinib', 'Ambroxol', 'Metformin', 'Imatinib', 'Aspirin']
        
        print("\n   Testing known drugs manually:")
        for test_drug_name in test_drugs:
            # Find if this drug exists in our dataset
            test_drug = next((d for d in drugs if test_drug_name.lower() in d['name'].lower()), None)
            
            if test_drug:
                shared_genes = builder.get_shared_genes(test_drug['name'], disease['name'])
                shared_pathways = builder.get_shared_pathways(test_drug['name'], disease['name'])
                
                score, evidence = scorer.score_drug_disease_match(
                    test_drug['name'],
                    disease['name'],
                    disease,
                    test_drug
                )
                
                print(f"\n   {test_drug['name']}:")
                print(f"      Targets: {len(test_drug.get('targets', []))}")
                print(f"      Shared genes: {len(shared_genes)} - {list(shared_genes)[:5]}")
                print(f"      Shared pathways: {len(shared_pathways)} - {list(shared_pathways)[:3]}")
                print(f"      Gene score: {evidence['gene_score']:.3f}")
                print(f"      Pathway score: {evidence['pathway_score']:.3f}")
                print(f"      TOTAL SCORE: {score:.3f}")
                
                if score < 0.2:
                    print(f"      ⚠️  Score too low! Needs to be >= 0.2")
            else:
                print(f"\n   {test_drug_name}: NOT FOUND in database")
        
        print("\n💡 LIKELY ISSUES:")
        print("   1. DGIdb not returning enough drug-gene interactions")
        print("   2. Gene/pathway matching is too strict")
        print("   3. Scoring weights need adjustment")
        print("   4. Need to fetch more drugs (try limit=500)")
        
    else:
        print(f"\n✅ SUCCESS! Found {len(high_scoring_drugs)} drugs scoring >= 0.2")
        print("\n🏆 Top 10 candidates:")
        
        high_scoring_drugs.sort(key=lambda x: x['score'], reverse=True)
        
        for i, drug in enumerate(high_scoring_drugs[:10], 1):
            print(f"\n   {i}. {drug['name']}")
            print(f"      Score: {drug['score']:.3f}")
            print(f"      Shared genes: {drug['genes']}")
            print(f"      Shared pathways: {drug['pathways']}")
            print(f"      Gene score: {drug['evidence']['gene_score']:.3f}")
            print(f"      Pathway score: {drug['evidence']['pathway_score']:.3f}")
    
    await fetcher.close()
    
    print("\n" + "="*70)
    print("DIAGNOSIS COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(diagnose())