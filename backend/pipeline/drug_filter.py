"""
Drug Safety Filter
Filters out contraindicated drugs that would harm patients with specific diseases
"""

import logging
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


class DrugSafetyFilter:
    """
    Filters out drugs that are contraindicated for specific diseases.
    This prevents the system from recommending harmful drugs.
    """
    
    def __init__(self):
        self.contraindications = self._build_contraindication_database()
    
    def _build_contraindication_database(self) -> Dict[str, List[Dict]]:
        """
        Build comprehensive database of contraindications.
        
        Structure:
        {
            'disease_keyword': [
                {
                    'drug_classes': [...],
                    'drug_names': [...],
                    'mechanisms': [...],
                    'reason': '...',
                    'severity': 'absolute' | 'relative'
                }
            ]
        }
        """
        return {
            # PARKINSON'S DISEASE CONTRAINDICATIONS
            'parkinson': [
                {
                    'drug_classes': [
                        'antipsychotic', 'neuroleptic', 'typical antipsychotic',
                        'atypical antipsychotic', 'antiemetic'
                    ],
                    'drug_names': [
                        'haloperidol', 'chlorpromazine', 'perphenazine', 'fluphenazine',
                        'olanzapine', 'risperidone', 'quetiapine', 'aripiprazole',
                        'ziprasidone', 'paliperidone', 'asenapine', 'lurasidone',
                        'metoclopramide', 'prochlorperazine', 'promethazine'
                    ],
                    'mechanisms': [
                        'dopamine antagonist', 'd2 antagonist', 'dopamine receptor antagonist',
                        'blocks dopamine', 'antidopaminergic'
                    ],
                    'reason': 'Blocks dopamine receptors - directly worsens Parkinson\'s motor symptoms',
                    'severity': 'absolute'
                },
                {
                    'drug_classes': ['anticholinesterase', 'cholinesterase inhibitor'],
                    'drug_names': ['donepezil', 'rivastigmine', 'galantamine'],
                    'mechanisms': ['acetylcholinesterase inhibitor', 'increases acetylcholine'],
                    'reason': 'May worsen tremor and motor symptoms',
                    'severity': 'relative'
                },
                {
                    'drug_classes': ['calcium channel blocker'],
                    'drug_names': ['cinnarizine', 'flunarizine'],
                    'mechanisms': ['calcium channel antagonist'],
                    'reason': 'Can cause or worsen parkinsonism',
                    'severity': 'absolute'
                }
            ],
            
            # ALZHEIMER'S DISEASE CONTRAINDICATIONS
            'alzheimer': [
                {
                    'drug_classes': [
                        'anticholinergic', 'antimuscarinic', 'tricyclic antidepressant'
                    ],
                    'drug_names': [
                        'diphenhydramine', 'atropine', 'scopolamine', 'benztropine',
                        'oxybutynin', 'tolterodine', 'amitriptyline', 'doxepin',
                        'hydroxyzine', 'meclizine', 'promethazine'
                    ],
                    'mechanisms': [
                        'anticholinergic', 'blocks acetylcholine', 'antimuscarinic',
                        'muscarinic antagonist'
                    ],
                    'reason': 'Worsens cognitive impairment and memory',
                    'severity': 'absolute'
                },
                {
                    'drug_classes': ['benzodiazepine'],
                    'drug_names': [
                        'diazepam', 'lorazepam', 'alprazolam', 'clonazepam', 'temazepam'
                    ],
                    'mechanisms': ['gaba agonist', 'benzodiazepine receptor agonist'],
                    'reason': 'Increases confusion, falls, and cognitive decline',
                    'severity': 'relative'
                }
            ],
            
            # DEMENTIA (GENERAL) CONTRAINDICATIONS
            'dementia': [
                {
                    'drug_classes': ['anticholinergic', 'antimuscarinic'],
                    'drug_names': [
                        'diphenhydramine', 'hydroxyzine', 'oxybutynin', 'tolterodine',
                        'benztropine', 'trihexyphenidyl'
                    ],
                    'mechanisms': ['anticholinergic', 'antimuscarinic'],
                    'reason': 'Worsens cognitive impairment',
                    'severity': 'absolute'
                }
            ],
            
            # TYPE 1 DIABETES CONTRAINDICATIONS
            'diabetes type 1': [
                {
                    'drug_classes': ['corticosteroid', 'glucocorticoid'],
                    'drug_names': [
                        'prednisone', 'dexamethasone', 'methylprednisolone', 'hydrocortisone'
                    ],
                    'mechanisms': ['glucocorticoid', 'corticosteroid'],
                    'reason': 'Causes severe hyperglycemia and ketoacidosis risk',
                    'severity': 'absolute'
                }
            ],
            
            # TYPE 2 DIABETES CONTRAINDICATIONS
            'diabetes type 2': [
                {
                    'drug_classes': ['corticosteroid', 'glucocorticoid'],
                    'drug_names': [
                        'prednisone', 'dexamethasone', 'methylprednisolone'
                    ],
                    'mechanisms': ['glucocorticoid', 'increases blood glucose'],
                    'reason': 'Significantly worsens glycemic control',
                    'severity': 'relative'
                },
                {
                    'drug_classes': ['thiazide diuretic'],
                    'drug_names': ['hydrochlorothiazide', 'chlorthalidone'],
                    'mechanisms': ['thiazide diuretic'],
                    'reason': 'Can worsen glucose control',
                    'severity': 'relative'
                }
            ],
            
            # ASTHMA CONTRAINDICATIONS
            'asthma': [
                {
                    'drug_classes': ['beta blocker', 'beta-blocker', 'non-selective beta blocker'],
                    'drug_names': [
                        'propranolol', 'nadolol', 'timolol', 'carvedilol', 'labetalol'
                    ],
                    'mechanisms': [
                        'beta blocker', 'beta-adrenergic antagonist', 'blocks beta receptors'
                    ],
                    'reason': 'Can cause life-threatening bronchospasm',
                    'severity': 'absolute'
                },
                {
                    'drug_classes': ['nsaid'],
                    'drug_names': ['aspirin', 'ibuprofen', 'naproxen', 'ketorolac'],
                    'mechanisms': ['cox inhibitor', 'cyclooxygenase inhibitor'],
                    'reason': 'Can trigger asthma attacks in aspirin-sensitive patients',
                    'severity': 'relative'
                }
            ],
            
            # HEART FAILURE CONTRAINDICATIONS
            'heart failure': [
                {
                    'drug_classes': ['nsaid', 'cox-2 inhibitor'],
                    'drug_names': [
                        'ibuprofen', 'naproxen', 'celecoxib', 'diclofenac', 'indomethacin'
                    ],
                    'mechanisms': ['cox inhibitor', 'prostaglandin inhibitor'],
                    'reason': 'Causes fluid retention and worsens heart failure',
                    'severity': 'absolute'
                },
                {
                    'drug_classes': ['thiazolidinedione', 'glitazone'],
                    'drug_names': ['pioglitazone', 'rosiglitazone'],
                    'mechanisms': ['ppar gamma agonist'],
                    'reason': 'Causes significant fluid retention',
                    'severity': 'absolute'
                }
            ],
            
            # GLAUCOMA CONTRAINDICATIONS
            'glaucoma': [
                {
                    'drug_classes': ['anticholinergic', 'antimuscarinic'],
                    'drug_names': [
                        'atropine', 'scopolamine', 'ipratropium', 'tiotropium'
                    ],
                    'mechanisms': ['anticholinergic', 'antimuscarinic'],
                    'reason': 'Increases intraocular pressure - can cause acute angle-closure glaucoma',
                    'severity': 'absolute'
                }
            ],
            
            # EPILEPSY/SEIZURE CONTRAINDICATIONS
            'epilepsy': [
                {
                    'drug_classes': ['antipsychotic'],
                    'drug_names': ['clozapine', 'chlorpromazine'],
                    'mechanisms': ['lowers seizure threshold'],
                    'reason': 'Significantly lowers seizure threshold',
                    'severity': 'absolute'
                }
            ],
            
            'seizure': [
                {
                    'drug_classes': ['antipsychotic', 'tricyclic antidepressant'],
                    'drug_names': ['clozapine', 'chlorpromazine', 'bupropion'],
                    'mechanisms': ['lowers seizure threshold'],
                    'reason': 'Increases seizure risk',
                    'severity': 'absolute'
                }
            ],
            
            # MYASTHENIA GRAVIS CONTRAINDICATIONS
            'myasthenia gravis': [
                {
                    'drug_classes': [
                        'aminoglycoside', 'fluoroquinolone', 'neuromuscular blocker'
                    ],
                    'drug_names': [
                        'gentamicin', 'tobramycin', 'ciprofloxacin', 'levofloxacin',
                        'vecuronium', 'rocuronium'
                    ],
                    'mechanisms': ['neuromuscular blockade', 'impairs neuromuscular transmission'],
                    'reason': 'Can cause myasthenic crisis - life-threatening',
                    'severity': 'absolute'
                }
            ],
            
            # DEPRESSION CONTRAINDICATIONS (with certain conditions)
            'depression': [
                {
                    'drug_classes': ['corticosteroid'],
                    'drug_names': ['prednisone', 'dexamethasone'],
                    'mechanisms': ['glucocorticoid'],
                    'reason': 'Can worsen depression and cause mood changes',
                    'severity': 'relative'
                }
            ],
            
            # GOUT CONTRAINDICATIONS
            'gout': [
                {
                    'drug_classes': ['thiazide diuretic', 'loop diuretic'],
                    'drug_names': ['hydrochlorothiazide', 'furosemide'],
                    'mechanisms': ['increases uric acid'],
                    'reason': 'Increases uric acid levels and triggers gout attacks',
                    'severity': 'relative'
                }
            ],
            
            # HYPERTENSION WITH CERTAIN CONDITIONS
            'hypertension': [
                {
                    'drug_classes': ['nsaid'],
                    'drug_names': ['ibuprofen', 'naproxen', 'celecoxib'],
                    'mechanisms': ['cox inhibitor'],
                    'reason': 'Increases blood pressure and reduces antihypertensive efficacy',
                    'severity': 'relative'
                }
            ],
            
            # LIVER DISEASE CONTRAINDICATIONS
            'cirrhosis': [
                {
                    'drug_classes': ['nsaid'],
                    'drug_names': ['ibuprofen', 'naproxen', 'aspirin'],
                    'mechanisms': ['cox inhibitor'],
                    'reason': 'Increases bleeding risk with portal hypertension',
                    'severity': 'absolute'
                }
            ],
            
            'liver disease': [
                {
                    'drug_classes': ['nsaid'],
                    'drug_names': ['ibuprofen', 'naproxen'],
                    'mechanisms': ['cox inhibitor'],
                    'reason': 'Hepatotoxic and increases bleeding risk',
                    'severity': 'relative'
                }
            ],
            
            # KIDNEY DISEASE CONTRAINDICATIONS
            'kidney disease': [
                {
                    'drug_classes': ['nsaid'],
                    'drug_names': ['ibuprofen', 'naproxen', 'ketorolac'],
                    'mechanisms': ['cox inhibitor', 'prostaglandin inhibitor'],
                    'reason': 'Nephrotoxic - can cause acute kidney injury',
                    'severity': 'absolute'
                }
            ],
            
            'chronic kidney disease': [
                {
                    'drug_classes': ['nsaid'],
                    'drug_names': ['ibuprofen', 'naproxen'],
                    'mechanisms': ['cox inhibitor'],
                    'reason': 'Accelerates kidney function decline',
                    'severity': 'absolute'
                }
            ]
        }
    
    def is_contraindicated(
        self,
        drug_name: str,
        disease_name: str,
        drug_mechanism: str = '',
        drug_indication: str = ''
    ) -> Dict:
        """
        Check if a drug is contraindicated for a disease.
        
        Returns:
            {
                'contraindicated': bool,
                'severity': 'absolute' | 'relative' | None,
                'reason': str,
                'matched_on': 'name' | 'mechanism' | 'class'
            }
        """
        drug_name_lower = drug_name.lower().strip()
        disease_name_lower = disease_name.lower().strip()
        mechanism_lower = drug_mechanism.lower() if drug_mechanism else ''
        indication_lower = drug_indication.lower() if drug_indication else ''
        
        # Check each disease keyword
        for disease_keyword, contraindication_list in self.contraindications.items():
            if disease_keyword not in disease_name_lower:
                continue
            
            # Found matching disease, now check contraindications
            for contraindication in contraindication_list:
                # Check drug name match
                for contraindicated_drug in contraindication.get('drug_names', []):
                    if contraindicated_drug in drug_name_lower:
                        logger.warning(
                            f"⛔ CONTRAINDICATED: {drug_name} for {disease_name} "
                            f"(Reason: {contraindication['reason']})"
                        )
                        return {
                            'contraindicated': True,
                            'severity': contraindication['severity'],
                            'reason': contraindication['reason'],
                            'matched_on': 'name'
                        }
                
                # Check mechanism match
                for contraindicated_mechanism in contraindication.get('mechanisms', []):
                    if contraindicated_mechanism in mechanism_lower:
                        logger.warning(
                            f"⛔ CONTRAINDICATED: {drug_name} for {disease_name} "
                            f"(Mechanism: {contraindicated_mechanism})"
                        )
                        return {
                            'contraindicated': True,
                            'severity': contraindication['severity'],
                            'reason': contraindication['reason'],
                            'matched_on': 'mechanism'
                        }
                
                # Check drug class match in indication
                for drug_class in contraindication.get('drug_classes', []):
                    if drug_class in indication_lower or drug_class in mechanism_lower:
                        logger.warning(
                            f"⛔ CONTRAINDICATED: {drug_name} for {disease_name} "
                            f"(Class: {drug_class})"
                        )
                        return {
                            'contraindicated': True,
                            'severity': contraindication['severity'],
                            'reason': contraindication['reason'],
                            'matched_on': 'class'
                        }
        
        # Not contraindicated
        return {
            'contraindicated': False,
            'severity': None,
            'reason': None,
            'matched_on': None
        }
    
    def filter_candidates(
        self,
        candidates: List[Dict],
        disease_name: str,
        remove_absolute: bool = True,
        remove_relative: bool = False
    ) -> tuple[List[Dict], List[Dict]]:
        """
        Filter out contraindicated drugs from candidate list.
        
        Args:
            candidates: List of drug candidates
            disease_name: Disease being treated
            remove_absolute: Remove absolutely contraindicated drugs
            remove_relative: Remove relatively contraindicated drugs
        
        Returns:
            (safe_candidates, filtered_out_candidates)
        """
        safe_candidates = []
        filtered_out = []
        
        for candidate in candidates:
            drug_name = candidate.get('drug_name', '')
            mechanism = candidate.get('mechanism', '')
            indication = candidate.get('indication', candidate.get('original_indication', ''))
            
            check_result = self.is_contraindicated(
                drug_name=drug_name,
                disease_name=disease_name,
                drug_mechanism=mechanism,
                drug_indication=indication
            )
            
            should_filter = False
            
            if check_result['contraindicated']:
                if check_result['severity'] == 'absolute' and remove_absolute:
                    should_filter = True
                elif check_result['severity'] == 'relative' and remove_relative:
                    should_filter = True
                
                # Add contraindication info to candidate
                candidate['contraindication'] = check_result
            
            if should_filter:
                filtered_out.append(candidate)
                logger.info(
                    f"❌ Filtered out {drug_name}: {check_result['reason']}"
                )
            else:
                safe_candidates.append(candidate)
        
        logger.info(
            f"✅ Filter results: {len(safe_candidates)} safe, "
            f"{len(filtered_out)} contraindicated"
        )
        
        return safe_candidates, filtered_out