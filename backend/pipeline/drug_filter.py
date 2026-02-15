"""
Drug Safety Filter - Filters out contraindicated medications
"""
import logging
from typing import List, Dict, Tuple, Set
import re

logger = logging.getLogger(__name__)


class DrugSafetyFilter:
    """
    Filters drug candidates based on contraindications for specific diseases.
    
    Uses a comprehensive database of known contraindications including:
    - Absolute contraindications (never use)
    - Relative contraindications (use with extreme caution)
    """
    
    def __init__(self):
        """Initialize the drug safety filter with contraindication data."""
        self.CRITICAL_CONTRAINDICATIONS = self._build_contraindication_database()
        logger.info(f"✅ Loaded contraindications for {len(self.CRITICAL_CONTRAINDICATIONS)} disease categories")
    
    def _build_contraindication_database(self) -> Dict[str, Dict[str, Dict]]:
        """
        Build comprehensive contraindication database.
        
        Structure:
        {
            "disease_pattern": {
                "drug_name": {
                    "severity": "absolute" or "relative",
                    "reason": "explanation",
                    "mechanism": "why it's dangerous"
                }
            }
        }
        """
        return {
            # ==================== DIABETES ====================
            "diabetes": {
                "olanzapine": {
                    "severity": "absolute",
                    "reason": "Causes significant weight gain and worsens glycemic control",
                    "mechanism": "Atypical antipsychotic that severely impairs glucose metabolism"
                },
                "clozapine": {
                    "severity": "absolute",
                    "reason": "High risk of hyperglycemia and diabetic ketoacidosis",
                    "mechanism": "Atypical antipsychotic with severe metabolic effects"
                },
                "quetiapine": {
                    "severity": "relative",
                    "reason": "Can worsen glycemic control",
                    "mechanism": "Atypical antipsychotic with metabolic side effects"
                },
                "risperidone": {
                    "severity": "relative",
                    "reason": "May impair glucose regulation",
                    "mechanism": "Atypical antipsychotic"
                },
                "prednisone": {
                    "severity": "relative",
                    "reason": "Increases blood glucose levels",
                    "mechanism": "Corticosteroid that promotes gluconeogenesis"
                },
                "dexamethasone": {
                    "severity": "relative",
                    "reason": "Severe hyperglycemia risk",
                    "mechanism": "Potent corticosteroid"
                },
                "methylprednisolone": {
                    "severity": "relative",
                    "reason": "Elevates blood sugar",
                    "mechanism": "Corticosteroid"
                },
                "hydrocortisone": {
                    "severity": "relative",
                    "reason": "Can destabilize glucose control",
                    "mechanism": "Corticosteroid"
                }
            },
            
            # ==================== PARKINSON'S DISEASE ====================
            "parkinson": {
                "haloperidol": {
                    "severity": "absolute",
                    "reason": "Blocks dopamine receptors, worsens motor symptoms",
                    "mechanism": "Typical antipsychotic - dopamine D2 antagonist"
                },
                "perphenazine": {
                    "severity": "absolute",
                    "reason": "Dopamine antagonist that exacerbates Parkinson's symptoms",
                    "mechanism": "Typical antipsychotic"
                },
                "chlorpromazine": {
                    "severity": "absolute",
                    "reason": "Severe dopamine blockade",
                    "mechanism": "Typical antipsychotic"
                },
                "fluphenazine": {
                    "severity": "absolute",
                    "reason": "Worsens motor symptoms",
                    "mechanism": "Typical antipsychotic"
                },
                "metoclopramide": {
                    "severity": "absolute",
                    "reason": "Dopamine antagonist causing parkinsonism",
                    "mechanism": "Antiemetic with dopamine-blocking effects"
                },
                "prochlorperazine": {
                    "severity": "absolute",
                    "reason": "Can precipitate severe motor dysfunction",
                    "mechanism": "Antiemetic dopamine antagonist"
                },
                "olanzapine": {
                    "severity": "relative",
                    "reason": "Some dopamine blockade, less severe than typical antipsychotics",
                    "mechanism": "Atypical antipsychotic"
                },
                "risperidone": {
                    "severity": "relative",
                    "reason": "May worsen motor symptoms at higher doses",
                    "mechanism": "Atypical antipsychotic"
                }
            },
            
            # ==================== ALZHEIMER'S DISEASE ====================
            "alzheimer": {
                "diphenhydramine": {
                    "severity": "absolute",
                    "reason": "Anticholinergic - worsens cognitive function",
                    "mechanism": "Blocks acetylcholine, critical for memory"
                },
                "benztropine": {
                    "severity": "absolute",
                    "reason": "Strong anticholinergic effects worsen dementia",
                    "mechanism": "Anticholinergic agent"
                },
                "oxybutynin": {
                    "severity": "absolute",
                    "reason": "Anticholinergic - severe cognitive impairment risk",
                    "mechanism": "Bladder medication with strong anticholinergic effects"
                },
                "tolterodine": {
                    "severity": "absolute",
                    "reason": "Anticholinergic for overactive bladder",
                    "mechanism": "Muscarinic antagonist"
                },
                "hydroxyzine": {
                    "severity": "relative",
                    "reason": "Anticholinergic antihistamine",
                    "mechanism": "Can impair cognition"
                },
                "scopolamine": {
                    "severity": "absolute",
                    "reason": "Potent anticholinergic",
                    "mechanism": "Causes confusion and memory impairment"
                },
                "cyclobenzaprine": {
                    "severity": "relative",
                    "reason": "Muscle relaxant with anticholinergic properties",
                    "mechanism": "Can worsen cognitive function"
                },
                "amitriptyline": {
                    "severity": "relative",
                    "reason": "Tricyclic antidepressant with strong anticholinergic effects",
                    "mechanism": "May impair memory"
                }
            },
            
            # ==================== ASTHMA ====================
            "asthma": {
                "propranolol": {
                    "severity": "absolute",
                    "reason": "Non-selective beta-blocker - causes bronchospasm",
                    "mechanism": "Blocks beta-2 receptors in airways"
                },
                "nadolol": {
                    "severity": "absolute",
                    "reason": "Non-selective beta-blocker",
                    "mechanism": "Life-threatening bronchospasm risk"
                },
                "timolol": {
                    "severity": "absolute",
                    "reason": "Non-selective beta-blocker",
                    "mechanism": "Even as eye drops can trigger asthma"
                },
                "atenolol": {
                    "severity": "relative",
                    "reason": "Beta-1 selective but still risky",
                    "mechanism": "Can cause bronchospasm at higher doses"
                },
                "metoprolol": {
                    "severity": "relative",
                    "reason": "Beta-1 selective blocker",
                    "mechanism": "Some beta-2 blockade possible"
                },
                "bisoprolol": {
                    "severity": "relative",
                    "reason": "Beta-1 selective but caution needed",
                    "mechanism": "Risk of bronchospasm"
                },
                "aspirin": {
                    "severity": "relative",
                    "reason": "Can trigger aspirin-exacerbated respiratory disease",
                    "mechanism": "NSAID-induced bronchospasm in susceptible patients"
                },
                "ibuprofen": {
                    "severity": "relative",
                    "reason": "NSAIDs can worsen asthma",
                    "mechanism": "Alternative arachidonic acid pathway"
                },
                "naproxen": {
                    "severity": "relative",
                    "reason": "NSAID with bronchospasm risk",
                    "mechanism": "Can trigger asthma attacks"
                }
            },
            
            # ==================== HEART FAILURE ====================
            "heart failure": {
                "ibuprofen": {
                    "severity": "relative",
                    "reason": "NSAIDs cause fluid retention",
                    "mechanism": "Worsens heart failure"
                },
                "naproxen": {
                    "severity": "relative",
                    "reason": "NSAID causing sodium retention",
                    "mechanism": "Exacerbates heart failure"
                },
                "rosiglitazone": {
                    "severity": "absolute",
                    "reason": "Causes severe fluid retention",
                    "mechanism": "Thiazolidinedione contraindicated in HF"
                },
                "pioglitazone": {
                    "severity": "absolute",
                    "reason": "Fluid retention and edema",
                    "mechanism": "Thiazolidinedione"
                }
            },
            
            # ==================== CHRONIC KIDNEY DISEASE ====================
            "kidney disease": {
                "metformin": {
                    "severity": "relative",
                    "reason": "Lactic acidosis risk in severe CKD",
                    "mechanism": "Contraindicated if eGFR < 30"
                },
                "ibuprofen": {
                    "severity": "relative",
                    "reason": "NSAIDs worsen kidney function",
                    "mechanism": "Reduces renal blood flow"
                },
                "naproxen": {
                    "severity": "relative",
                    "reason": "NSAID nephrotoxicity",
                    "mechanism": "Can precipitate acute kidney injury"
                }
            },
            
            # ==================== GLAUCOMA ====================
            "glaucoma": {
                "diphenhydramine": {
                    "severity": "absolute",
                    "reason": "Anticholinergic - increases intraocular pressure",
                    "mechanism": "Can precipitate acute angle-closure glaucoma"
                },
                "benztropine": {
                    "severity": "absolute",
                    "reason": "Strong anticholinergic",
                    "mechanism": "Contraindicated in angle-closure glaucoma"
                },
                "oxybutynin": {
                    "severity": "absolute",
                    "reason": "Anticholinergic effects on eye",
                    "mechanism": "Increases intraocular pressure"
                }
            },
            
            # ==================== EPILEPSY/SEIZURES ====================
            "epilepsy": {
                "bupropion": {
                    "severity": "absolute",
                    "reason": "Lowers seizure threshold",
                    "mechanism": "Can precipitate seizures"
                },
                "tramadol": {
                    "severity": "relative",
                    "reason": "Seizure risk",
                    "mechanism": "Lowers seizure threshold"
                },
                "clozapine": {
                    "severity": "relative",
                    "reason": "Dose-dependent seizure risk",
                    "mechanism": "Can cause seizures"
                }
            },
            
            # ==================== HYPERTENSION ====================
            "hypertension": {
                "pseudoephedrine": {
                    "severity": "relative",
                    "reason": "Increases blood pressure",
                    "mechanism": "Sympathomimetic decongestant"
                },
                "phenylephrine": {
                    "severity": "relative",
                    "reason": "Vasoconstrictor",
                    "mechanism": "Raises blood pressure"
                }
            }
        }
    
    def _normalize_name(self, name: str) -> str:
        """Normalize drug/disease names for matching."""
        if not name:
            return ""
        # Convert to lowercase and remove extra whitespace
        normalized = name.lower().strip()
        # Remove common suffixes
        normalized = re.sub(r'\s+(sodium|hydrochloride|hcl|sulfate|tartrate)$', '', normalized)
        return normalized
    
    def _find_disease_key(self, disease_name: str) -> List[str]:
        """
        Find matching disease keys in contraindication database.
        Uses partial matching to handle variations in disease names.
        """
        normalized_disease = self._normalize_name(disease_name)
        matching_keys = []
        
        for key in self.CRITICAL_CONTRAINDICATIONS.keys():
            # Check if the key is in the disease name or vice versa
            if key in normalized_disease or normalized_disease in key:
                matching_keys.append(key)
            # Also check for specific patterns
            elif key == "diabetes" and ("diabetes" in normalized_disease or "diabetic" in normalized_disease):
                matching_keys.append(key)
            elif key == "parkinson" and "parkinson" in normalized_disease:
                matching_keys.append(key)
            elif key == "alzheimer" and ("alzheimer" in normalized_disease or "dementia" in normalized_disease):
                matching_keys.append(key)
            elif key == "asthma" and "asthma" in normalized_disease:
                matching_keys.append(key)
            elif key == "heart failure" and ("heart failure" in normalized_disease or "cardiac failure" in normalized_disease):
                matching_keys.append(key)
            elif key == "kidney disease" and ("kidney" in normalized_disease or "renal" in normalized_disease or "ckd" in normalized_disease):
                matching_keys.append(key)
            elif key == "glaucoma" and "glaucoma" in normalized_disease:
                matching_keys.append(key)
            elif key == "epilepsy" and ("epilepsy" in normalized_disease or "seizure" in normalized_disease):
                matching_keys.append(key)
            elif key == "hypertension" and ("hypertension" in normalized_disease or "high blood pressure" in normalized_disease):
                matching_keys.append(key)
        
        return matching_keys
    
    async def filter_candidates(
        self,
        candidates: List[Dict],
        disease_name: str,
        remove_absolute: bool = True,
        remove_relative: bool = False
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Filter drug candidates based on contraindications.
        
        Args:
            candidates: List of drug candidates
            disease_name: Name of the disease being treated
            remove_absolute: Remove absolutely contraindicated drugs
            remove_relative: Remove relatively contraindicated drugs
        
        Returns:
            Tuple of (safe_candidates, filtered_out_candidates)
        """
        logger.info(f"🔍 FILTER STARTING")
        logger.info(f"   Disease: '{disease_name}'")
        logger.info(f"   Candidates to check: {len(candidates)}")
        logger.info(f"   remove_absolute: {remove_absolute}")
        logger.info(f"   remove_relative: {remove_relative}")
        
        # Find matching disease categories
        disease_keys = self._find_disease_key(disease_name)
        logger.info(f"   Matched disease categories: {disease_keys}")
        
        if not disease_keys:
            logger.warning(f"⚠️  No contraindication data for '{disease_name}'")
            return candidates, []
        
        # Collect all contraindications for this disease
        contraindications = {}
        for key in disease_keys:
            contraindications.update(self.CRITICAL_CONTRAINDICATIONS[key])
        
        logger.info(f"   Total contraindications loaded: {len(contraindications)}")
        logger.info(f"   Contraindicated drugs: {list(contraindications.keys())}")
        
        safe_candidates = []
        filtered_out = []
        
        for candidate in candidates:
            drug_name = candidate.get('drug_name', '')
            normalized_drug = self._normalize_name(drug_name)
            
            # Check if drug is contraindicated
            if normalized_drug in contraindications:
                contraindication = contraindications[normalized_drug]
                severity = contraindication['severity']
                
                # Decide whether to filter based on severity and settings
                should_filter = False
                if severity == 'absolute' and remove_absolute:
                    should_filter = True
                elif severity == 'relative' and remove_relative:
                    should_filter = True
                
                if should_filter:
                    # Add contraindication info to candidate
                    candidate['contraindication'] = contraindication
                    candidate['contraindication']['severity'] = severity
                    filtered_out.append(candidate)
                    logger.warning(
                        f"   ⛔ FILTERED: {drug_name} "
                        f"(severity: {severity}, reason: {contraindication['reason']})"
                    )
                else:
                    # Keep the drug but add warning
                    candidate['contraindication_warning'] = contraindication
                    safe_candidates.append(candidate)
                    logger.info(
                        f"   ⚠️  KEPT WITH WARNING: {drug_name} "
                        f"(severity: {severity})"
                    )
            else:
                # Drug is safe
                safe_candidates.append(candidate)
        
        logger.info(f"✅ FILTER COMPLETE")
        logger.info(f"   Safe candidates: {len(safe_candidates)}")
        logger.info(f"   Filtered out: {len(filtered_out)}")
        
        return safe_candidates, filtered_out
    
    def get_contraindications_for_disease(self, disease_name: str) -> Dict[str, Dict]:
        """
        Get all contraindications for a specific disease.
        
        Args:
            disease_name: Name of the disease
        
        Returns:
            Dictionary of contraindicated drugs with their info
        """
        disease_keys = self._find_disease_key(disease_name)
        
        if not disease_keys:
            return {}
        
        contraindications = {}
        for key in disease_keys:
            contraindications.update(self.CRITICAL_CONTRAINDICATIONS[key])
        
        return contraindications