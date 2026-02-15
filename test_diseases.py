#!/usr/bin/env python3
"""
Drug Repurposing App - Multi-Disease Tester
Tests your app with multiple diseases and formats output for validation
"""

import requests
import json
import time
from typing import Dict, List

# Configuration
API_URL = "http://localhost:8000/analyze"
MAX_RESULTS = 10

# Disease test cases with expected results for validation
DISEASE_TESTS = [
    {
        "name": "Parkinson Disease",
        "expected_filtered": ["perphenazine", "olanzapine", "haloperidol", "metoclopramide"],
        "expected_candidates": ["apomorphine", "amantadine", "pramipexole"],
        "critical": ["dopamine antagonists must be filtered"]
    },
    {
        "name": "Alzheimer Disease",
        "expected_filtered": ["diphenhydramine", "benztropine", "oxybutynin"],
        "expected_candidates": ["donepezil", "rivastigmine", "galantamine", "memantine"],
        "critical": ["anticholinergics must be filtered"]
    },
    {
        "name": "Type 2 Diabetes",
        "expected_filtered": ["olanzapine", "clozapine", "prednisone", "dexamethasone"],
        "expected_candidates": ["metformin", "glipizide", "pioglitazone"],
        "critical": ["CRITICAL: olanzapine MUST be filtered (causes diabetes)"]
    },
    {
        "name": "Asthma",
        "expected_filtered": ["propranolol", "atenolol", "metoprolol", "nadolol"],
        "expected_candidates": ["albuterol", "montelukast", "fluticasone"],
        "critical": ["LIFE-THREATENING: beta-blockers must be filtered"]
    },
]


def print_header():
    """Print test header"""
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "Drug Repurposing App - Multi-Disease Tester" + " " * 15 + "║")
    print("╚" + "═" * 78 + "╝")
    print()


def print_section_header(title: str):
    """Print section header"""
    print("━" * 80)
    print(f"TESTING: {title}")
    print("━" * 80)
    print()


def test_disease(disease_config: Dict) -> Dict:
    """Test a single disease and return results"""
    disease_name = disease_config["name"]
    
    try:
        # Make API request
        response = requests.post(
            API_URL,
            json={
                "disease_name": disease_name, 
                "max_results": MAX_RESULTS,
                "min_score": 0.2
            },
            timeout=60
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text[:200]}"
            }
        
        data = response.json()
        return {"success": True, "data": data, "config": disease_config}
        
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": "Failed to connect to API. Is the backend running on port 8000?"
        }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Request timed out (>60 seconds)"
        }
    except json.JSONDecodeError:
        return {
            "success": False,
            "error": "Invalid JSON response from API"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


def print_results(result: Dict):
    """Print formatted test results"""
    if not result["success"]:
        print(f"❌ ERROR: {result['error']}")
        print()
        return
    
    data = result["data"]
    config = result["config"]
    
    # Check if API request succeeded
    if not data.get("success", False):
        print(f"❌ API ERROR: {data.get('error', 'Unknown error')}")
        if 'suggestion' in data:
            print(f"   Suggestion: {data['suggestion']}")
        print()
        return
    
    # Print disease info
    disease_info = data.get('disease', {})
    print("DISEASE ANALYSIS:")
    print(f"  Disease: {disease_info.get('name', 'Unknown')}")
    print(f"  Genes Identified: {disease_info.get('genes_count', 0)}")
    print(f"  Pathways Mapped: {disease_info.get('pathways_count', 0)}")
    print(f"  Candidates Found: {len(data.get('candidates', []))}")
    print(f"  Drugs Filtered: {data.get('filtered_count', 0)}")
    
    # Print contraindicated drugs
    filtered_drugs = data.get('filtered_drugs', [])
    print(f"\n⛔ CONTRAINDICATED DRUGS ({len(filtered_drugs)} filtered):")
    
    if filtered_drugs:
        for drug in filtered_drugs:
            name = drug.get('drug_name', 'Unknown').upper()
            reason = drug.get('reason', 'No reason provided')
            severity = drug.get('severity', 'unknown').upper()
            print(f"  ❌ {name}")
            print(f"     Severity: {severity}")
            print(f"     Reason: {reason[:100]}{'...' if len(reason) > 100 else ''}")
    else:
        print("  ✅ None (no drugs filtered)")
    
    # Validation check for expected filtered drugs
    if config["expected_filtered"]:
        filtered_names = [d.get('drug_name', '').lower() for d in filtered_drugs]
        missing_filters = []
        for expected in config["expected_filtered"]:
            if expected.lower() not in filtered_names:
                missing_filters.append(expected)
        
        if missing_filters:
            print(f"\n  ⚠️  VALIDATION WARNING: Expected these to be filtered but they weren't:")
            for drug in missing_filters:
                print(f"     - {drug}")
    
    # Print critical warnings
    if config["critical"]:
        print(f"\n  🚨 CRITICAL SAFETY CHECKS:")
        for warning in config["critical"]:
            print(f"     {warning}")
    
    # Print top candidates
    candidates = data.get('candidates', [])
    num_to_show = min(5, len(candidates))
    
    print(f"\n🔬 TOP {num_to_show} CANDIDATES:")
    
    if candidates:
        for i, candidate in enumerate(candidates[:5], 1):
            name = candidate.get('drug_name', 'Unknown').upper()
            score = candidate.get('score', 0)
            confidence = candidate.get('confidence', 'unknown')
            gene_score = candidate.get('gene_score', 0)
            pathway_score = candidate.get('pathway_score', 0)
            shared_genes = candidate.get('shared_genes', [])
            
            print(f"\n  #{i} {name}")
            print(f"     Match Score: {score*100:.1f}%")
            print(f"     Confidence: {confidence}")
            print(f"     Gene Score: {gene_score*100:.1f}% ({len(shared_genes)} shared genes)")
            print(f"     Pathway Score: {pathway_score*100:.1f}%")
            
            # Show first few shared genes
            if shared_genes and len(shared_genes) > 0:
                genes_str = ", ".join(shared_genes[:5])
                if len(shared_genes) > 5:
                    genes_str += f" (+ {len(shared_genes) - 5} more)"
                print(f"     Shared Genes: {genes_str}")
        
        # Validation check for expected candidates
        if config["expected_candidates"]:
            candidate_names = [c.get('drug_name', '').lower() for c in candidates[:10]]
            found_expected = []
            for expected in config["expected_candidates"]:
                if expected.lower() in candidate_names:
                    found_expected.append(expected)
            
            if found_expected:
                print(f"\n  ✅ VALIDATION: Found expected drug(s): {', '.join(found_expected)}")
            else:
                print(f"\n  ⚠️  VALIDATION WARNING: None of the expected drugs found in top 10:")
                print(f"     Expected: {', '.join(config['expected_candidates'])}")
    else:
        print("  ⚠️ No candidates found")
    
    print()


def print_summary(results: List[Dict]):
    """Print summary of all tests"""
    print("\n" + "╔" + "═" * 78 + "╗")
    print("║" + " " * 30 + "TEST SUMMARY" + " " * 36 + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    
    successful = sum(1 for r in results if r["success"] and r["data"].get("success"))
    total = len(results)
    
    print(f"Tests Run: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")
    print()
    
    # Critical issues
    critical_issues = []
    
    for result in results:
        if not result["success"] or not result["data"].get("success"):
            continue
        
        data = result["data"]
        config = result["config"]
        disease_name = config["name"]
        
        # Check for critical issues
        if "diabetes" in disease_name.lower():
            filtered_names = [d.get('drug_name', '').lower() 
                            for d in data.get('filtered_drugs', [])]
            if "olanzapine" not in filtered_names:
                critical_issues.append(
                    f"🚨 CRITICAL: Olanzapine NOT filtered for {disease_name} (causes diabetes!)"
                )
        
        if "asthma" in disease_name.lower():
            filtered_names = [d.get('drug_name', '').lower() 
                            for d in data.get('filtered_drugs', [])]
            beta_blockers = ["propranolol", "atenolol", "metoprolol"]
            if not any(bb in filtered_names for bb in beta_blockers):
                critical_issues.append(
                    f"🚨 CRITICAL: Beta-blockers NOT filtered for {disease_name} (life-threatening!)"
                )
    
    if critical_issues:
        print("🚨 CRITICAL SAFETY ISSUES DETECTED:")
        for issue in critical_issues:
            print(f"   {issue}")
        print()
    else:
        print("✅ No critical safety issues detected!")
        print()


def main():
    """Main test execution"""
    print_header()
    print(f"Testing {len(DISEASE_TESTS)} diseases...")
    print(f"API: {API_URL}")
    print()
    print()
    
    results = []
    
    for disease_config in DISEASE_TESTS:
        print_section_header(disease_config["name"])
        result = test_disease(disease_config)
        print_results(result)
        results.append(result)
        time.sleep(2)  # Small delay between requests
    
    print_summary(results)


if __name__ == "__main__":
    main()