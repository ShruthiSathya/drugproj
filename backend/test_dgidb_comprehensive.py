import asyncio
import aiohttp
import ssl
import certifi
import json


async def test_correct_format():
    print("\n" + "="*80)
    print("🎯 TESTING CORRECT DGIDB FORMAT (Connection/Edges Pattern)")
    print("="*80)
    
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    timeout = aiohttp.ClientTimeout(total=30)
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        
        # The CORRECT format using edges/node pattern
        query = """
        query GetDrugs($names: [String!]!) {
          drugs(names: $names, first: 10) {
            edges {
              node {
                name
                conceptId
                approved
                interactions {
                  edges {
                    node {
                      gene {
                        name
                      }
                      interactionTypes {
                        type
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """
        
        test_drugs = ["NILOTINIB", "IMATINIB", "ASPIRIN", "METFORMIN"]
        
        print(f"\n📋 Testing with drugs: {test_drugs}")
        print("-" * 80)
        
        try:
            async with session.post(
                "https://dgidb.org/api/graphql",
                json={
                    "query": query,
                    "variables": {"names": test_drugs}
                },
                headers={"Content-Type": "application/json"}
            ) as resp:
                print(f"Status: {resp.status}")
                
                if resp.status != 200:
                    text = await resp.text()
                    print(f"❌ Error: {text[:500]}")
                    return
                
                data = await resp.json()
                
                if 'errors' in data:
                    print(f"❌ GraphQL Errors:")
                    for error in data['errors']:
                        print(f"   - {error.get('message')}")
                    return
                
                if 'data' not in data or 'drugs' not in data['data']:
                    print(f"❌ Unexpected response structure")
                    print(f"Response: {json.dumps(data, indent=2)[:500]}")
                    return
                
                edges = data['data']['drugs'].get('edges', [])
                
                print(f"\n✅ SUCCESS! Found {len(edges)} drugs")
                print("=" * 80)
                
                for edge in edges:
                    node = edge.get('node', {})
                    drug_name = node.get('name', 'Unknown')
                    concept_id = node.get('conceptId', 'N/A')
                    approved = node.get('approved', False)
                    
                    interaction_edges = node.get('interactions', {}).get('edges', [])
                    
                    genes = []
                    for int_edge in interaction_edges:
                        int_node = int_edge.get('node', {})
                        gene = int_node.get('gene', {}).get('name')
                        if gene:
                            genes.append(gene)
                    
                    print(f"\n🔬 {drug_name}")
                    print(f"   Concept ID: {concept_id}")
                    print(f"   Approved: {approved}")
                    print(f"   Targets: {len(genes)} genes")
                    print(f"   Sample targets: {genes[:10]}")
                
                print("\n" + "=" * 80)
                print("✅ DGIdb API IS WORKING WITH CORRECT FORMAT!")
                print("=" * 80)
                
                return data
        
        except Exception as e:
            print(f"❌ Request failed: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_correct_format())
