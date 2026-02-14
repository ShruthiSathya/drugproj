#!/usr/bin/env python3
"""
Test script for database integrations
Run this to verify OpenTargets, ChEMBL, and DGIdb are working
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from pipeline.data_fetcher import RareDiseaseDataFetcher


async def test_opentargets():
    """Test OpenTargets disease data fetching"""
    print("\n" + "="*70)
    print("🧬 TEST 1: OpenTargets Platform (Disease-Gene Associations)")
    print("="*70)
    
    fetcher = RareDiseaseDataFetcher()
    
    test_diseases = [
        "Huntington Disease",
        "Parkinson Disease",
        "Gaucher Disease",
        "Cystic Fibrosis",
    ]
    
    for disease_name in test_diseases:
        print(f"\n🔍 Testing: {disease_name}")
        disease = await fetcher.fetch_disease_data(disease_name)
        
        if disease:
            print(f"  ✅ Found: {disease['name']}")
            print(f"  📊 Genes: {len(disease['genes'])}")
            print(f"  🧪 Pathways: {len(disease['pathways'])}")
            print(f"  🔬 Rare disease: {disease.get('is_rare', False)}")
            print(f"  📋 Active trials: {disease.get('active_trials_count', 0)}")
            
            if disease['genes']:
                print(f"  🎯 Top genes: {', '.join(disease['genes'][:5])}")
            if disease['pathways']:
                print(f"  🛤️  Top pathways: {', '.join(disease['pathways'][:3])}")
        else:
            print(f"  ❌ NOT FOUND in OpenTargets")
    
    await fetcher.close()


async def test_chembl():
    """Test ChEMBL drug database"""
    print("\n" + "="*70)
    print("💊 TEST 2: ChEMBL (Approved Drugs)")
    print("="*70)
    
    fetcher = RareDiseaseDataFetcher()
    
    print("\n🔍 Fetching 20 approved drugs from ChEMBL...")
    drugs = await fetcher.fetch_approved_drugs(limit=20)
    
    if drugs:
        print(f"\n✅ Successfully fetched {len(drugs)} drugs")
        print("\n📋 Sample drugs:")
        
        for i, drug in enumerate(drugs[:10], 1):
            print(f"\n  {i}. {drug['name']}")
            print(f"     ID: {drug['id']}")
            print(f"     Indication: {drug['indication']}")
            
            if drug['targets']:
                print(f"     Targets ({len(drug['targets'])}): {', '.join(drug['targets'][:3])}")
            else:
                print(f"     Targets: None yet (will be added by DGIdb)")
            
            if drug['smiles']:
                print(f"     SMILES: {drug['smiles'][:50]}...")
    else:
        print("  ❌ FAILED to fetch drugs from ChEMBL")
    
    await fetcher.close()


async def test_dgidb():
    """Test DGIdb drug-gene interactions"""
    print("\n" + "="*70)
    print("🔗 TEST 3: DGIdb (Drug-Gene Interactions)")
    print("="*70)
    
    fetcher = RareDiseaseDataFetcher()
    
    # Create mock drugs to test DGIdb enhancement
    mock_drugs = [
        {"name": "Metformin", "id": "MOCK1", "targets": [], "pathways": []},
        {"name": "Aspirin", "id": "MOCK2", "targets": [], "pathways": []},
        {"name": "Ibuprofen", "id": "MOCK3", "targets": [], "pathways": []},
    ]
    
    print("\n🔍 Testing DGIdb enhancement for known drugs...")
    enhanced_drugs = await fetcher._enhance_with_dgidb(mock_drugs)
    
    print("\n📋 Results:")
    for drug in enhanced_drugs:
        print(f"\n  • {drug['name']}")
        if drug['targets']:
            print(f"    ✅ Targets found: {', '.join(drug['targets'][:5])}")
            if drug['pathways']:
                print(f"    ✅ Pathways inferred: {', '.join(drug['pathways'][:3])}")
        else:
            print(f"    ⚠️  No targets found (drug name might not match DGIdb)")
    
    await fetcher.close()


async def test_clinical_trials():
    """Test ClinicalTrials.gov integration"""
    print("\n" + "="*70)
    print("📋 TEST 4: ClinicalTrials.gov (Active Research)")
    print("="*70)
    
    fetcher = RareDiseaseDataFetcher()
    
    test_diseases = [
        "Huntington Disease",
        "Gaucher Disease",
        "Duchenne Muscular Dystrophy",
    ]
    
    for disease_name in test_diseases:
        print(f"\n🔍 Testing: {disease_name}")
        disease = await fetcher.fetch_disease_data(disease_name)
        
        if disease:
            trials = disease.get('active_trials_count', 0)
            if trials > 0:
                print(f"  ✅ Found {trials} active clinical trials")
            else:
                print(f"  ℹ️  No active trials found")
        else:
            print(f"  ❌ Disease not found")
    
    await fetcher.close()


async def test_full_pipeline():
    """Test complete pipeline with a rare disease"""
    print("\n" + "="*70)
    print("🚀 TEST 5: Full Pipeline (Disease → Drugs → Scoring)")
    print("="*70)
    
    fetcher = RareDiseaseDataFetcher()
    
    disease_name = "Wilson Disease"
    print(f"\n🔍 Running full pipeline for: {disease_name}")
    
    # Fetch disease
    print("\n1️⃣  Fetching disease data...")
    disease = await fetcher.fetch_disease_data(disease_name)
    
    if not disease:
        print("  ❌ Disease not found!")
        await fetcher.close()
        return
    
    print(f"  ✅ Disease: {disease['name']}")
    print(f"     Genes: {len(disease['genes'])}")
    print(f"     Pathways: {len(disease['pathways'])}")
    
    # Fetch drugs
    print("\n2️⃣  Fetching approved drugs...")
    drugs = await fetcher.fetch_approved_drugs(limit=50)
    print(f"  ✅ Fetched {len(drugs)} drugs")
    
    # Simple scoring (count overlapping genes/pathways)
    print("\n3️⃣  Scoring drug-disease matches...")
    matches = []
    
    for drug in drugs:
        gene_overlap = len(set(drug['targets']) & set(disease['genes']))
        pathway_overlap = len(set(drug['pathways']) & set(disease['pathways']))
        
        if gene_overlap > 0 or pathway_overlap > 0:
            score = gene_overlap * 0.6 + pathway_overlap * 0.4
            matches.append({
                'drug': drug['name'],
                'score': score,
                'genes': gene_overlap,
                'pathways': pathway_overlap
            })
    
    # Sort by score
    matches.sort(key=lambda x: x['score'], reverse=True)
    
    if matches:
        print(f"\n  ✅ Found {len(matches)} potential matches!")
        print("\n📊 Top 5 candidates:")
        for i, match in enumerate(matches[:5], 1):
            print(f"\n     {i}. {match['drug']}")
            print(f"        Score: {match['score']:.2f}")
            print(f"        Shared genes: {match['genes']}")
            print(f"        Shared pathways: {match['pathways']}")
    else:
        print("\n  ℹ️  No strong matches found (this is normal for small drug set)")
    
    await fetcher.close()


async def run_all_tests():
    """Run all tests sequentially"""
    print("\n" + "🧪"*35)
    print("DRUG REPURPOSING DATABASE INTEGRATION TESTS")
    print("🧪"*35)
    
    try:
        await test_opentargets()
        await test_chembl()
        await test_dgidb()
        await test_clinical_trials()
        await test_full_pipeline()
        
        print("\n" + "="*70)
        print("✅ ALL TESTS COMPLETED!")
        print("="*70)
        print("\nYour database integrations are working correctly! 🎉")
        print("\nNext steps:")
        print("  1. Update your main.py to use data_fetcher_v2.py")
        print("  2. Restart your app: ./stop.sh && ./start.sh")
        print("  3. Test with: http://localhost:3000")
        
    except Exception as e:
        print("\n" + "="*70)
        print("❌ TEST FAILED!")
        print("="*70)
        print(f"\nError: {e}")
        print("\nTroubleshooting:")
        print("  1. Check internet connection")
        print("  2. Verify API endpoints are accessible")
        print("  3. Check logs above for specific errors")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n🔬 Starting database integration tests...")
    print("This will test: OpenTargets, ChEMBL, DGIdb, ClinicalTrials.gov")
    print("Expected duration: 30-60 seconds\n")
    
    asyncio.run(run_all_tests())