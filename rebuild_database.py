#!/usr/bin/env python3
"""
COMPLETE FIX SCRIPT - Rebuild drug database with working DGIdb
This will clear the cache and rebuild with proper gene targets
"""

import asyncio
import shutil
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

async def rebuild_database():
    print("\n" + "="*70)
    print("🔧 REBUILDING DRUG DATABASE WITH WORKING DGIDB")
    print("="*70)
    
    # Step 1: Clear cache
    print("\n📁 Step 1: Clearing old cache...")
    cache_dir = Path("/tmp/drug_repurposing_cache")
    if cache_dir.exists():
        try:
            shutil.rmtree(cache_dir)
            print("✅ Cache cleared")
        except Exception as e:
            print(f"⚠️  Could not clear cache: {e}")
    
    cache_dir.mkdir(exist_ok=True)
    print("✅ Fresh cache directory created")
    
    # Step 2: Import fixed fetcher
    print("\n📦 Step 2: Loading fixed data fetcher...")
    from pipeline.data_fetcher import ProductionDataFetcher
    
    fetcher = ProductionDataFetcher()
    print("✅ Data fetcher loaded")
    
    # Step 3: Fetch and test disease
    print("\n🔍 Step 3: Testing disease fetching...")
    disease = await fetcher.fetch_disease_data("Parkinson Disease")
    
    if not disease:
        print("❌ Failed to fetch disease!")
        await fetcher.close()
        return False
    
    print(f"✅ Disease: {disease['name']}")
    print(f"   Genes: {len(disease['genes'])}")
    print(f"   Pathways: {len(disease['pathways'])}")
    
    # Step 4: Fetch drugs with DGIdb enhancement
    print("\n💊 Step 4: Fetching drugs with DGIdb enhancement...")
    print("   (This may take 30-60 seconds on first run)")
    
    drugs = await fetcher.fetch_approved_drugs(limit=200)
    
    if not drugs:
        print("❌ No drugs fetched!")
        await fetcher.close()
        return False
    
    print(f"✅ Fetched {len(drugs)} drugs")
    
    # Step 5: Check enhancement
    print("\n🔍 Step 5: Checking DGIdb enhancement...")
    drugs_with_targets = [d for d in drugs if d.get('targets')]
    
    print(f"   Total drugs: {len(drugs)}")
    print(f"   Drugs with targets: {len(drugs_with_targets)}")
    print(f"   Enhancement rate: {len(drugs_with_targets)/len(drugs)*100:.1f}%")
    
    if len(drugs_with_targets) == 0:
        print("\n❌ STILL NO TARGETS FOUND!")
        print("\n🔍 Debugging: Let's check the DGIdb API directly...")
        
        # Try DGIdb API directly
        import aiohttp
        import ssl
        import certifi
        
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        timeout = aiohttp.ClientTimeout(total=30)
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            # Test with a known drug
            test_query = """
            query {
              drugs(names: ["Nilotinib", "Imatinib", "Aspirin"]) {
                name
                interactions {
                  gene {
                    name
                  }
                }
              }
            }
            """
            
            print("\n   Testing DGIdb API with known drugs...")
            try:
                async with session.post(
                    "https://dgidb.org/api/graphql",
                    json={"query": test_query},
                    headers={"Content-Type": "application/json"}
                ) as resp:
                    print(f"   DGIdb status: {resp.status}")
                    
                    if resp.status == 200:
                        result = await resp.json()
                        print(f"   Response: {json.dumps(result, indent=2)[:500]}")
                        
                        if 'data' in result and 'drugs' in result['data']:
                            test_drugs = result['data']['drugs']
                            test_drugs = [d for d in test_drugs if d is not None]
                            print(f"   ✅ DGIdb returned {len(test_drugs)} drugs")
                            
                            for td in test_drugs:
                                if td:
                                    interactions = td.get('interactions', [])
                                    print(f"   - {td['name']}: {len(interactions)} interactions")
                        else:
                            print("   ❌ DGIdb response structure unexpected")
                    else:
                        text = await resp.text()
                        print(f"   ❌ DGIdb error: {text[:300]}")
            
            except Exception as e:
                print(f"   ❌ DGIdb API call failed: {e}")
        
        print("\n💡 SOLUTION:")
        print("   DGIdb API might be down or blocking requests.")
        print("   The fetcher includes manual fallback for known drugs.")
        print("   Let's check if manual enhancement worked...")
        
        # Check manual enhancement
        manual_enhanced = []
        for drug in drugs:
            if drug.get('targets'):
                manual_enhanced.append(drug['name'])
        
        if manual_enhanced:
            print(f"\n   ✅ Manual enhancement worked for {len(manual_enhanced)} drugs:")
            for name in manual_enhanced[:10]:
                print(f"      - {name}")
        else:
            print("\n   ❌ Manual enhancement also failed")
            print("   This means drug names don't match known drugs list")
        
        await fetcher.close()
        return False
    
    # Step 6: Show sample drugs
    print("\n📋 Step 6: Sample drugs with targets:")
    for drug in drugs_with_targets[:10]:
        targets = drug.get('targets', [])
        pathways = drug.get('pathways', [])
        print(f"\n   {drug['name']}:")
        print(f"      Targets ({len(targets)}): {targets[:5]}")
        print(f"      Pathways ({len(pathways)}): {pathways[:3]}")
    
    # Step 7: Test scoring
    print("\n🎯 Step 7: Testing scoring system...")
    from pipeline.graph_builder import ProductionGraphBuilder
    from pipeline.scorer import ProductionScorer
    
    builder = ProductionGraphBuilder()
    graph = builder.build_graph(disease, drugs)
    
    print(f"   Graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    
    scorer = ProductionScorer(graph)
    
    candidates = []
    for drug in drugs_with_targets:
        score, evidence = scorer.score_drug_disease_match(
            drug['name'],
            disease['name'],
            disease,
            drug
        )
        
        if score >= 0.1:  # Very low threshold for testing
            candidates.append({
                'name': drug['name'],
                'score': score,
                'evidence': evidence
            })
    
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    print(f"\n   Candidates with score >= 0.1: {len(candidates)}")
    
    if len(candidates) == 0:
        print("\n   ❌ No candidates found even with threshold 0.1!")
        print("   This means drugs don't overlap with disease genes/pathways")
    else:
        print("\n   ✅ Top 10 candidates:")
        for i, cand in enumerate(candidates[:10], 1):
            ev = cand['evidence']
            print(f"\n   {i}. {cand['name']}: {cand['score']:.3f}")
            print(f"      Shared genes: {len(ev['shared_genes'])}")
            print(f"      Shared pathways: {len(ev['shared_pathways'])}")
            print(f"      Gene score: {ev['gene_score']:.3f}")
            print(f"      Pathway score: {ev['pathway_score']:.3f}")
    
    await fetcher.close()
    
    print("\n" + "="*70)
    if len(candidates) >= 5:
        print("✅ SUCCESS! Database rebuilt with working DGIdb")
        print(f"   Found {len(candidates)} candidates for Parkinson's")
        print("\n🚀 Next steps:")
        print("   1. Restart your backend: ./stop.sh && ./start.sh")
        print("   2. Try frontend search with min_score=0.1")
        print("   3. You should now see candidates!")
    else:
        print("⚠️  PARTIAL SUCCESS - Database rebuilt but few candidates")
        print("\n🔍 Possible issues:")
        print("   1. DGIdb API might be temporarily down")
        print("   2. Need to increase drug limit (try 500)")
        print("   3. Disease genes might not overlap with available drugs")
    print("="*70 + "\n")
    
    return len(candidates) >= 5


if __name__ == "__main__":
    success = asyncio.run(rebuild_database())
    sys.exit(0 if success else 1)