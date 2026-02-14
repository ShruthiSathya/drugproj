"""
LLMExplainer: uses Anthropic Claude API to generate explanations for drug repurposing candidates.
"""

import asyncio
from typing import Optional
import aiohttp
from models import DrugCandidate


class LLMExplainer:
    """Generate AI-powered explanations for repurposing candidates using Anthropic Claude."""

    def __init__(self):
        self.model = "claude-sonnet-4-20250514"
        self.api_url = "https://api.anthropic.com/v1/messages"

    async def explain_candidates(
        self,
        disease_name: str,
        candidates: list[DrugCandidate],
        api_key: Optional[str] = None
    ) -> list[DrugCandidate]:
        """
        Generate explanations for each candidate using Anthropic Claude API.
        If no API key provided, uses fallback heuristic explanations.
        """
        if not api_key:
            # Fallback to rule-based explanations
            return self._generate_fallback_explanations(disease_name, candidates)
        
        try:
            # Process in batches to avoid rate limits
            batch_size = 3
            explained_candidates = []
            
            for i in range(0, len(candidates), batch_size):
                batch = candidates[i:i + batch_size]
                tasks = [
                    self._explain_single_candidate(disease_name, candidate, api_key)
                    for candidate in batch
                ]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Handle any exceptions in the batch
                for result in batch_results:
                    if isinstance(result, Exception):
                        print(f"Error in batch explanation: {result}")
                    else:
                        explained_candidates.append(result)
                
                # Small delay between batches
                if i + batch_size < len(candidates):
                    await asyncio.sleep(0.5)
            
            return explained_candidates
            
        except Exception as e:
            print(f"LLM explanation failed: {e}, falling back to heuristic explanations")
            return self._generate_fallback_explanations(disease_name, candidates)

    async def _explain_single_candidate(
        self,
        disease_name: str,
        candidate: DrugCandidate,
        api_key: str
    ) -> DrugCandidate:
        """Generate explanation for a single candidate using Anthropic Claude."""
        
        prompt = f"""You are a drug repurposing expert. Generate a concise, scientifically accurate explanation (2-3 sentences) for why {candidate.drug_name} might be repurposed for {disease_name}.

Current indication: {candidate.original_indication}
Mechanism: {candidate.mechanism}
Shared genes: {', '.join(candidate.shared_genes[:5]) if candidate.shared_genes else 'None'}
Shared pathways: {', '.join(candidate.shared_pathways[:3]) if candidate.shared_pathways else 'None'}
Confidence: {candidate.confidence}

Focus on the biological rationale based on shared molecular targets and pathways. Be specific and scientific but accessible."""

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "max_tokens": 300,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ]
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        explanation = data['content'][0]['text'].strip()
                        candidate.explanation = explanation
                    else:
                        error_text = await response.text()
                        print(f"Anthropic API error ({response.status}): {error_text}")
                        candidate.explanation = self._generate_fallback_explanation(disease_name, candidate)
            
        except Exception as e:
            print(f"Failed to explain {candidate.drug_name}: {e}")
            candidate.explanation = self._generate_fallback_explanation(disease_name, candidate)
        
        return candidate

    def _generate_fallback_explanations(
        self,
        disease_name: str,
        candidates: list[DrugCandidate]
    ) -> list[DrugCandidate]:
        """Generate rule-based explanations when API is unavailable."""
        for candidate in candidates:
            candidate.explanation = self._generate_fallback_explanation(disease_name, candidate)
        return candidates

    def _generate_fallback_explanation(self, disease_name: str, candidate: DrugCandidate) -> str:
        """Generate a heuristic explanation based on available data."""
        
        parts = []
        
        if candidate.shared_genes:
            genes_str = ", ".join(candidate.shared_genes[:3])
            if len(candidate.shared_genes) > 3:
                genes_str += f" and {len(candidate.shared_genes) - 3} others"
            parts.append(f"{candidate.drug_name} targets key genes ({genes_str}) that are implicated in {disease_name}")
        
        if candidate.shared_pathways:
            pathways_str = ", ".join(candidate.shared_pathways[:2])
            if len(candidate.shared_pathways) > 2:
                pathways_str += f" and {len(candidate.shared_pathways) - 2} other pathways"
            parts.append(f"modulates critical pathways including {pathways_str}")
        
        if candidate.mechanism:
            parts.append(f"Its mechanism as a {candidate.mechanism.lower()} may address underlying disease mechanisms")
        
        if not parts:
            return f"{candidate.drug_name} shows therapeutic potential for {disease_name} based on computational analysis of shared molecular signatures and biological pathways."
        
        explanation = ". ".join(parts) + "."
        
        # Add confidence-based qualifier
        if candidate.confidence == "High":
            explanation = "Strong evidence suggests: " + explanation
        elif candidate.confidence == "Medium":
            explanation = "Moderate evidence indicates: " + explanation
        else:
            explanation = "Preliminary analysis suggests: " + explanation
        
        return explanation