"""
Drug Safety Filter — Fixed Implementation
==========================================
Two-layer safety system:
  Layer 1: CRITICAL_CONTRAINDICATIONS hardcoded lookup (always runs, no network)
           Contains medically critical drug-disease pairs backed by FDA evidence.
           This guarantees olanzapine is ALWAYS filtered for diabetes, etc.

  Layer 2: OpenFDA label API scan (runs after, adds more coverage)
           Fetches the actual FDA label and scans for disease keywords.

Exposes TWO public methods on DrugSafetyFilter:

  filter_drugs(candidate_drugs: List[str], disease_name: str)
      → (safe_names: List[str], filtered_info: List[Dict])

  filter_candidates(candidates: List[Dict], disease_name, ...)
      → (safe_candidates: List[Dict], filtered_candidates: List[Dict])
      THIS IS WHAT main.py CALLS.
"""

import asyncio
import re
import logging
from typing import List, Dict, Tuple, Optional, Set
from urllib.parse import quote

try:
    import aiohttp
    _AIOHTTP_AVAILABLE = True
except ImportError:
    _AIOHTTP_AVAILABLE = False

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  LAYER 1: CRITICAL CONTRAINDICATIONS (hardcoded, always enforced)
#  These are medically critical drug-disease pairs where the drug can
#  CAUSE or WORSEN the disease. Based on FDA black box warnings, prescribing
#  guidelines, and established clinical evidence.
# ─────────────────────────────────────────────────────────────────────────────

# Maps disease_key → list of (drug_names_lower, reason, severity)
# severity: "absolute" = never use, "relative" = use with extreme caution
CRITICAL_CONTRAINDICATIONS: Dict[str, List[Dict]] = {

    # ── DIABETES / METABOLIC SYNDROME ────────────────────────────────────────
    "diabetes": [
        # Atypical antipsychotics → hyperglycemia / new-onset diabetes (FDA Black Box)
        {"drugs": ["olanzapine", "clozapine", "quetiapine", "risperidone",
                   "ziprasidone", "aripiprazole", "asenapine", "iloperidone",
                   "lurasidone", "paliperidone"],
         "reason": "FDA Black Box Warning: Atypical antipsychotics cause hyperglycemia, "
                   "new-onset diabetes mellitus, and diabetic ketoacidosis. "
                   "Olanzapine and clozapine carry the highest risk.",
         "severity": "absolute"},
        # Corticosteroids → steroid-induced diabetes
        {"drugs": ["prednisone", "dexamethasone", "methylprednisolone",
                   "hydrocortisone", "betamethasone", "triamcinolone",
                   "fludrocortisone", "cortisone"],
         "reason": "Corticosteroids cause steroid-induced diabetes and worsen "
                   "glycemic control in existing diabetics via gluconeogenesis.",
         "severity": "absolute"},
        # Thiazide diuretics → hyperglycemia
        {"drugs": ["hydrochlorothiazide", "chlorothiazide", "chlorthalidone",
                   "indapamide", "metolazone"],
         "reason": "Thiazide diuretics impair insulin secretion and cause "
                   "hyperglycemia; worsen glucose control in T2DM.",
         "severity": "relative"},
        # Beta-blockers → mask hypoglycemia, worsen insulin resistance
        {"drugs": ["propranolol", "atenolol", "metoprolol", "nadolol",
                   "carvedilol", "bisoprolol", "labetalol"],
         "reason": "Non-selective beta-blockers mask hypoglycemia symptoms and "
                   "impair glycogenolysis; worsen insulin resistance.",
         "severity": "relative"},
        # Niacin → hyperglycemia
        {"drugs": ["niacin", "nicotinic acid", "niacinamide"],
         "reason": "High-dose niacin causes dose-dependent hyperglycemia and "
                   "worsens insulin resistance.",
         "severity": "relative"},
        # Fluoroquinolones → dysglycemia
        {"drugs": ["gatifloxacin", "levofloxacin", "moxifloxacin", "ciprofloxacin"],
         "reason": "Fluoroquinolones cause both hypoglycemia and hyperglycemia; "
                   "FDA warning for serious dysglycemia in diabetics.",
         "severity": "relative"},
    ],

    # ── PARKINSON'S DISEASE ───────────────────────────────────────────────────
    "parkinson": [
        # All dopamine antagonists → worsen Parkinson's directly
        {"drugs": ["haloperidol", "perphenazine", "fluphenazine", "thioridazine",
                   "trifluoperazine", "chlorpromazine", "droperidol",
                   "pimozide", "thiothixene"],
         "reason": "Typical antipsychotics (dopamine D2 antagonists) directly worsen "
                   "Parkinson's by blocking dopamine receptors — absolute contraindication.",
         "severity": "absolute"},
        {"drugs": ["olanzapine", "risperidone", "aripiprazole", "ziprasidone",
                   "asenapine", "iloperidone", "paliperidone"],
         "reason": "Atypical antipsychotics with significant D2 blockade worsen "
                   "parkinsonian motor symptoms. Only quetiapine/clozapine are tolerated.",
         "severity": "absolute"},
        # Antiemetics that are dopamine antagonists
        {"drugs": ["metoclopramide", "prochlorperazine", "promethazine",
                   "trimethobenzamide"],
         "reason": "Dopamine-blocking antiemetics cross the BBB and worsen "
                   "Parkinson's motor symptoms.",
         "severity": "absolute"},
        # Reserpine → depletes dopamine
        {"drugs": ["reserpine", "tetrabenazine"],
         "reason": "Dopamine-depleting agents worsen Parkinson's by reducing "
                   "presynaptic dopamine availability.",
         "severity": "absolute"},
        # Lithium → can worsen Parkinson's tremor
        {"drugs": ["lithium"],
         "reason": "Lithium can worsen parkinsonian tremor and cause drug-induced "
                   "parkinsonism.",
         "severity": "relative"},
    ],

    # ── ALZHEIMER'S DISEASE ──────────────────────────────────────────────────
    "alzheimer": [
        # Anticholinergics → worsen cognition dramatically
        {"drugs": ["diphenhydramine", "hydroxyzine", "promethazine",
                   "chlorpheniramine", "cyproheptadine", "meclizine",
                   "dimenhydrinate", "brompheniramine"],
         "reason": "First-generation antihistamines with strong anticholinergic "
                   "activity worsen cognitive function and memory in Alzheimer's.",
         "severity": "absolute"},
        {"drugs": ["benztropine", "trihexyphenidyl", "scopolamine",
                   "oxybutynin", "tolterodine", "solifenacin",
                   "fesoterodine", "darifenacin", "flavoxate"],
         "reason": "Anticholinergic drugs directly antagonize the cholinergic "
                   "system, the primary target of Alzheimer's treatment — "
                   "will negate benefit of cholinesterase inhibitors.",
         "severity": "absolute"},
        {"drugs": ["amitriptyline", "imipramine", "doxepin", "clomipramine",
                   "nortriptyline", "trimipramine"],
         "reason": "TCAs have strong anticholinergic activity that worsens "
                   "cognitive impairment in Alzheimer's.",
         "severity": "absolute"},
        # Benzodiazepines → cognitive decline, falls, increased dementia risk
        {"drugs": ["diazepam", "lorazepam", "alprazolam", "clonazepam",
                   "temazepam", "triazolam", "midazolam", "oxazepam"],
         "reason": "Benzodiazepines increase risk of cognitive decline and "
                   "dementia progression; associated with 50% increased dementia risk.",
         "severity": "absolute"},
        # Antipsychotics → increased mortality in dementia patients (FDA Black Box)
        {"drugs": ["haloperidol", "olanzapine", "quetiapine", "risperidone",
                   "aripiprazole", "clozapine"],
         "reason": "FDA Black Box Warning: Antipsychotics cause increased mortality "
                   "in elderly patients with dementia-related psychosis.",
         "severity": "absolute"},
    ],

    # ── ASTHMA ───────────────────────────────────────────────────────────────
    "asthma": [
        # Non-selective beta-blockers → life-threatening bronchospasm
        {"drugs": ["propranolol", "nadolol", "timolol", "sotalol",
                   "pindolol", "penbutolol", "carteolol"],
         "reason": "LIFE-THREATENING: Non-selective beta-blockers block β2 receptors "
                   "in bronchial smooth muscle, causing fatal bronchospasm in asthmatics.",
         "severity": "absolute"},
        # Even cardioselective beta-blockers are risky in severe asthma
        {"drugs": ["atenolol", "metoprolol", "bisoprolol", "acebutolol",
                   "betaxolol", "esmolol"],
         "reason": "Cardioselective beta-blockers lose selectivity at higher doses; "
                   "contraindicated in moderate-severe asthma.",
         "severity": "absolute"},
        # NSAIDs → aspirin-exacerbated respiratory disease (AERD) in ~10% of asthmatics
        {"drugs": ["aspirin", "ibuprofen", "naproxen", "indomethacin",
                   "ketorolac", "diclofenac", "celecoxib"],
         "reason": "NSAIDs trigger bronchospasm in aspirin-exacerbated respiratory "
                   "disease (AERD), affecting ~10% of adult asthmatics.",
         "severity": "relative"},
        # ACE inhibitors → cough can trigger bronchospasm
        {"drugs": ["lisinopril", "enalapril", "ramipril", "captopril",
                   "benazepril", "quinapril", "perindopril", "fosinopril"],
         "reason": "ACE inhibitors cause dry cough in 15-20% of patients via "
                   "bradykinin accumulation; can trigger asthma exacerbations.",
         "severity": "relative"},
    ],

    # ── COPD ─────────────────────────────────────────────────────────────────
    "copd": [
        {"drugs": ["propranolol", "nadolol", "timolol", "sotalol",
                   "atenolol", "metoprolol", "bisoprolol"],
         "reason": "Beta-blockers cause bronchospasm and worsen airflow "
                   "obstruction in COPD patients.",
         "severity": "absolute"},
        {"drugs": ["benzodiazepines", "diazepam", "lorazepam", "alprazolam",
                   "clonazepam", "temazepam"],
         "reason": "Benzodiazepines cause respiratory depression; dangerous "
                   "in COPD patients with hypercapnia.",
         "severity": "absolute"},
        {"drugs": ["opioids", "morphine", "oxycodone", "hydrocodone",
                   "codeine", "fentanyl"],
         "reason": "Opioids suppress respiratory drive; particularly dangerous "
                   "in COPD with CO2 retention.",
         "severity": "absolute"},
    ],

    # ── EPILEPSY / SEIZURES ───────────────────────────────────────────────────
    "epilepsy": [
        # Drugs that lower seizure threshold
        {"drugs": ["tramadol", "bupropion", "clozapine", "olanzapine",
                   "chlorpromazine", "thioridazine"],
         "reason": "Lower seizure threshold significantly; contraindicated in "
                   "epilepsy.",
         "severity": "absolute"},
        {"drugs": ["fluoroquinolones", "ciprofloxacin", "levofloxacin",
                   "moxifloxacin"],
         "reason": "Fluoroquinolones inhibit GABA-A receptors and lower seizure "
                   "threshold.",
         "severity": "relative"},
        {"drugs": ["meperidine", "pethidine"],
         "reason": "Normeperidine (active metabolite) lowers seizure threshold; "
                   "contraindicated in epilepsy.",
         "severity": "absolute"},
    ],

    # ── HEART FAILURE ────────────────────────────────────────────────────────
    "heart_failure": [
        # Negative inotropes
        {"drugs": ["verapamil", "diltiazem"],
         "reason": "Non-dihydropyridine calcium channel blockers have negative "
                   "inotropic effects; worsen systolic heart failure.",
         "severity": "absolute"},
        {"drugs": ["nifedipine", "amlodipine", "felodipine"],
         "reason": "Dihydropyridine CCBs cause reflex tachycardia and fluid "
                   "retention; worsen decompensated heart failure.",
         "severity": "relative"},
        {"drugs": ["rosiglitazone", "pioglitazone", "thiazolidinedione"],
         "reason": "Thiazolidinediones cause fluid retention and worsen or "
                   "precipitate heart failure.",
         "severity": "absolute"},
        {"drugs": ["nsaids", "ibuprofen", "naproxen", "celecoxib",
                   "indomethacin", "diclofenac"],
         "reason": "NSAIDs cause sodium/fluid retention, reduce diuretic "
                   "efficacy, and worsen heart failure.",
         "severity": "absolute"},
        {"drugs": ["dronedarone"],
         "reason": "Increases mortality in patients with permanent AF and "
                   "symptomatic heart failure.",
         "severity": "absolute"},
    ],

    # ── MYASTHENIA GRAVIS ─────────────────────────────────────────────────────
    "myasthenia_gravis": [
        {"drugs": ["fluoroquinolones", "ciprofloxacin", "levofloxacin",
                   "moxifloxacin", "aminoglycosides", "gentamicin",
                   "tobramycin", "amikacin"],
         "reason": "Antibiotics impair neuromuscular transmission and can "
                   "trigger myasthenic crisis.",
         "severity": "absolute"},
        {"drugs": ["beta-blockers", "propranolol", "atenolol", "metoprolol",
                   "timolol"],
         "reason": "Beta-blockers worsen myasthenia gravis and can precipitate "
                   "crisis.",
         "severity": "absolute"},
        {"drugs": ["chloroquine", "hydroxychloroquine", "quinine"],
         "reason": "Antimalarials can unmask or worsen myasthenia gravis.",
         "severity": "absolute"},
        {"drugs": ["d-penicillamine"],
         "reason": "D-penicillamine can induce an autoimmune myasthenia-like "
                   "syndrome.",
         "severity": "absolute"},
    ],

    # ── GLAUCOMA ─────────────────────────────────────────────────────────────
    "glaucoma": [
        {"drugs": ["anticholinergics", "atropine", "scopolamine", "benztropine",
                   "oxybutynin", "tolterodine", "ipratropium", "tiotropium"],
         "reason": "Anticholinergics cause pupillary dilation that can trigger "
                   "acute angle-closure glaucoma attack.",
         "severity": "absolute"},
        {"drugs": ["topiramate", "acetazolamide"],
         "reason": "Can cause acute angle-closure glaucoma as a rare but "
                   "serious adverse effect.",
         "severity": "relative"},
    ],

    # ── OSTEOPOROSIS ─────────────────────────────────────────────────────────
    "osteoporosis": [
        {"drugs": ["prednisone", "dexamethasone", "methylprednisolone",
                   "hydrocortisone", "cortisone", "betamethasone",
                   "triamcinolone", "fludrocortisone"],
         "reason": "Corticosteroids are the #1 cause of drug-induced osteoporosis; "
                   "reduce bone formation and increase bone resorption.",
         "severity": "absolute"},
        {"drugs": ["heparin"],
         "reason": "Long-term heparin use causes osteoporosis via osteoclast "
                   "activation.",
         "severity": "relative"},
        {"drugs": ["levothyroxine", "thyroxine"],
         "reason": "Supraphysiologic thyroid hormone suppression therapy "
                   "accelerates bone loss.",
         "severity": "relative"},
        {"drugs": ["anticonvulsants", "phenytoin", "carbamazepine",
                   "phenobarbital", "valproic acid"],
         "reason": "Enzyme-inducing anticonvulsants increase vitamin D "
                   "catabolism and worsen bone loss.",
         "severity": "relative"},
    ],

    # ── GOUT ─────────────────────────────────────────────────────────────────
    "gout": [
        {"drugs": ["hydrochlorothiazide", "chlorothiazide", "furosemide",
                   "bumetanide", "ethacrynic acid", "torsemide"],
         "reason": "Diuretics decrease renal uric acid excretion, causing "
                   "hyperuricemia and precipitating gout attacks.",
         "severity": "absolute"},
        {"drugs": ["aspirin", "salicylates"],
         "reason": "Low-dose aspirin blocks uric acid secretion and raises "
                   "serum uric acid levels.",
         "severity": "relative"},
        {"drugs": ["cyclosporine", "tacrolimus"],
         "reason": "Calcineurin inhibitors reduce renal urate clearance and "
                   "commonly cause gout.",
         "severity": "absolute"},
        {"drugs": ["niacin", "nicotinic acid"],
         "reason": "Niacin competes with uric acid for renal excretion, "
                   "raising serum urate levels.",
         "severity": "relative"},
        {"drugs": ["pyrazinamide", "ethambutol"],
         "reason": "Antituberculars inhibit renal uric acid excretion and "
                   "commonly trigger gout.",
         "severity": "absolute"},
    ],

    # ── KIDNEY DISEASE (CKD) ──────────────────────────────────────────────────
    "kidney_disease": [
        {"drugs": ["metformin"],
         "reason": "Metformin is contraindicated in severe CKD (eGFR<30) due to "
                   "risk of lactic acidosis.",
         "severity": "absolute"},
        {"drugs": ["nsaids", "ibuprofen", "naproxen", "celecoxib",
                   "indomethacin", "diclofenac", "ketorolac"],
         "reason": "NSAIDs reduce renal blood flow via prostaglandin inhibition; "
                   "worsen renal function and can cause acute kidney injury.",
         "severity": "absolute"},
        {"drugs": ["gadolinium"],
         "reason": "Gadolinium contrast causes nephrogenic systemic fibrosis "
                   "in severe CKD.",
         "severity": "absolute"},
        {"drugs": ["gentamicin", "tobramycin", "amikacin", "vancomycin"],
         "reason": "Nephrotoxic antibiotics require dose adjustment and cause "
                   "further renal damage.",
         "severity": "absolute"},
    ],

    # ── LIVER DISEASE ────────────────────────────────────────────────────────
    "liver_disease": [
        {"drugs": ["acetaminophen", "paracetamol"],
         "reason": "Hepatotoxic at standard doses in liver disease; maximum "
                   "dose must be reduced to 2g/day.",
         "severity": "absolute"},
        {"drugs": ["statins", "atorvastatin", "simvastatin", "rosuvastatin",
                   "lovastatin", "fluvastatin", "pravastatin"],
         "reason": "Statins are metabolized by the liver; contraindicated in "
                   "active liver disease or unexplained transaminase elevations.",
         "severity": "absolute"},
        {"drugs": ["isoniazid", "rifampin", "rifampicin"],
         "reason": "Antituberculars are hepatotoxic and contraindicated in "
                   "significant liver disease.",
         "severity": "absolute"},
        {"drugs": ["methotrexate"],
         "reason": "Methotrexate causes hepatic fibrosis/cirrhosis; "
                   "contraindicated in liver disease.",
         "severity": "absolute"},
        {"drugs": ["tetracycline", "doxycycline", "minocycline"],
         "reason": "Tetracyclines can cause fatty liver; use with caution "
                   "in liver disease.",
         "severity": "relative"},
    ],

    # ── INFLAMMATORY BOWEL DISEASE ────────────────────────────────────────────
    "inflammatory_bowel_disease": [
        {"drugs": ["nsaids", "ibuprofen", "naproxen", "aspirin",
                   "indomethacin", "diclofenac"],
         "reason": "NSAIDs trigger IBD flares by disrupting intestinal "
                   "mucosal barrier and increasing intestinal permeability.",
         "severity": "absolute"},
        {"drugs": ["infliximab", "adalimumab", "certolizumab"],
         "reason": "TNF inhibitors reactivate latent TB and other infections; "
                   "screen before use.",
         "severity": "relative"},
    ],

    # ── PSORIASIS ─────────────────────────────────────────────────────────────
    "psoriasis": [
        {"drugs": ["lithium"],
         "reason": "Lithium commonly triggers or worsens psoriasis flares.",
         "severity": "absolute"},
        {"drugs": ["propranolol", "atenolol", "metoprolol"],
         "reason": "Beta-blockers can trigger or worsen psoriasis.",
         "severity": "relative"},
        {"drugs": ["antimalarials", "chloroquine", "hydroxychloroquine"],
         "reason": "Antimalarials can trigger pustular psoriasis flares.",
         "severity": "relative"},
    ],

    # ── WILSON'S DISEASE ─────────────────────────────────────────────────────
    "wilson_disease": [
        {"drugs": ["zinc", "zinc sulfate", "zinc gluconate"],
         "reason": "High-dose zinc supplementation can interfere with Wilson's "
                   "disease treatment by competing with copper chelation.",
         "severity": "relative"},
        {"drugs": ["iron", "ferrous sulfate", "ferrous gluconate"],
         "reason": "Iron supplementation competes with copper chelation therapy "
                   "used in Wilson's disease.",
         "severity": "relative"},
    ],

    # ── PORPHYRIA ─────────────────────────────────────────────────────────────
    "porphyria": [
        {"drugs": ["sulfonamides", "sulfamethoxazole", "trimethoprim"],
         "reason": "Sulfonamides induce porphyrin synthesis; trigger acute "
                   "porphyria attacks.",
         "severity": "absolute"},
        {"drugs": ["barbiturates", "phenobarbital", "pentobarbital"],
         "reason": "Barbiturates are among the most dangerous drugs in "
                   "acute porphyria; can be fatal.",
         "severity": "absolute"},
        {"drugs": ["griseofulvin", "rifampin", "carbamazepine", "phenytoin"],
         "reason": "Enzyme-inducing drugs precipitate acute porphyria attacks.",
         "severity": "absolute"},
        {"drugs": ["alcohol", "ethanol"],
         "reason": "Alcohol is a potent precipitant of acute porphyria attacks.",
         "severity": "absolute"},
    ],

    # ── SICKLE CELL DISEASE ───────────────────────────────────────────────────
    "sickle_cell_disease": [
        {"drugs": ["estrogen", "oral contraceptives", "ethinyl estradiol"],
         "reason": "Estrogen increases thrombotic risk in sickle cell disease.",
         "severity": "relative"},
        {"drugs": ["desmopressin", "ddavp"],
         "reason": "DDAVP can cause severe hyponatremia in sickle cell disease.",
         "severity": "relative"},
    ],
}

# Canonical disease name aliases
DISEASE_NAME_MAP: Dict[str, str] = {
    "parkinson": "parkinson", "parkinsonian": "parkinson",
    "parkinson's disease": "parkinson", "parkinson disease": "parkinson",
    "alzheimer": "alzheimer", "alzheimer's disease": "alzheimer",
    "dementia": "alzheimer",
    "diabetes": "diabetes", "diabetic": "diabetes",
    "type 2 diabetes": "diabetes", "type 1 diabetes": "diabetes",
    "diabetes mellitus": "diabetes", "t2dm": "diabetes",
    "type 2 diabetes mellitus": "diabetes", "t1dm": "diabetes",
    "dm2": "diabetes", "dm1": "diabetes",
    "asthma": "asthma", "bronchial asthma": "asthma",
    "copd": "copd", "chronic obstructive pulmonary disease": "copd",
    "emphysema": "copd",
    "epilepsy": "epilepsy", "seizure disorder": "epilepsy",
    "seizures": "epilepsy",
    "heart failure": "heart_failure", "cardiac failure": "heart_failure",
    "congestive heart failure": "heart_failure", "chf": "heart_failure",
    "hypertension": "hypertension", "high blood pressure": "hypertension",
    "glaucoma": "glaucoma",
    "myasthenia gravis": "myasthenia_gravis", "myasthenia": "myasthenia_gravis",
    "kidney disease": "kidney_disease", "renal disease": "kidney_disease",
    "chronic kidney disease": "kidney_disease", "ckd": "kidney_disease",
    "renal failure": "kidney_disease",
    "liver disease": "liver_disease", "hepatic disease": "liver_disease",
    "cirrhosis": "liver_disease", "hepatitis": "liver_disease",
    "osteoporosis": "osteoporosis", "bone loss": "osteoporosis",
    "gout": "gout", "hyperuricemia": "gout",
    "psoriasis": "psoriasis",
    "crohn's disease": "inflammatory_bowel_disease",
    "ulcerative colitis": "inflammatory_bowel_disease",
    "inflammatory bowel disease": "inflammatory_bowel_disease",
    "ibd": "inflammatory_bowel_disease",
    "gaucher disease": "gaucher_disease",
    "porphyria": "porphyria",
    "huntington's disease": "huntington_disease",
    "huntington disease": "huntington_disease",
    "cystic fibrosis": "cystic_fibrosis",
    "duchenne muscular dystrophy": "duchenne_muscular_dystrophy",
    "duchenne": "duchenne_muscular_dystrophy", "dmd": "duchenne_muscular_dystrophy",
    "fabry disease": "fabry_disease",
    "pompe disease": "pompe_disease",
    "amyotrophic lateral sclerosis": "amyotrophic_lateral_sclerosis",
    "als": "amyotrophic_lateral_sclerosis",
    "motor neuron disease": "amyotrophic_lateral_sclerosis",
    "hemophilia": "hemophilia", "haemophilia": "hemophilia",
    "sickle cell disease": "sickle_cell_disease",
    "sickle cell anemia": "sickle_cell_disease",
    "myotonic dystrophy": "myotonic_dystrophy",
    "phenylketonuria": "phenylketonuria", "pku": "phenylketonuria",
    "wilson disease": "wilson_disease", "wilson's disease": "wilson_disease",
}

# Always filtered regardless of disease
WITHDRAWN_DRUGS: Set[str] = {
    "troglitazone", "rofecoxib", "cerivastatin", "fenfluramine",
    "dexfenfluramine", "terfenadine", "astemizole", "cisapride",
    "valdecoxib", "lumiracoxib", "pemoline", "propoxyphene",
    "sibutramine", "tegaserod", "aprotinin", "ximelagatran",
    "trovafloxacin", "levomethadyl",
}

# FDA API disease keywords (secondary layer)
DISEASE_KEYWORDS: Dict[str, List[str]] = {
    "parkinson": ["parkinson", "parkinsonism", "extrapyramidal",
                  "dopamine antagonist", "levodopa"],
    "alzheimer": ["alzheimer", "dementia", "cognitive impairment",
                  "anticholinergic"],
    "diabetes": ["diabetes", "diabetic", "hyperglycemia",
                 "blood glucose", "insulin", "glycemic", "hypoglycemia",
                 "glucose intolerance", "diabetic ketoacidosis"],
    "asthma": ["asthma", "asthmatic", "bronchospasm",
               "bronchial", "bronchoconstriction", "bronchial hyperreactivity"],
    "copd": ["copd", "chronic obstructive", "emphysema", "bronchospasm"],
    "epilepsy": ["epilepsy", "seizure", "convulsion", "seizure threshold"],
    "heart_failure": ["heart failure", "cardiac failure", "congestive heart failure"],
    "hypertension": ["hypertension", "high blood pressure"],
    "glaucoma": ["glaucoma", "intraocular pressure", "angle-closure"],
    "myasthenia_gravis": ["myasthenia gravis", "myasthenic"],
    "kidney_disease": ["renal impairment", "renal failure", "chronic kidney", "ckd"],
    "liver_disease": ["hepatic impairment", "hepatotoxic", "cirrhosis", "liver disease"],
    "osteoporosis": ["osteoporosis", "bone density", "bone loss"],
    "gout": ["gout", "uric acid", "hyperuricemia"],
    "psoriasis": ["psoriasis", "psoriatic"],
    "inflammatory_bowel_disease": ["crohn", "ulcerative colitis", "inflammatory bowel"],
}


def normalize_disease_name(disease_name: str) -> Optional[str]:
    """Map raw disease name to canonical key."""
    lower = disease_name.lower().strip()
    if lower in CRITICAL_CONTRAINDICATIONS:
        return lower
    if lower in DISEASE_KEYWORDS:
        return lower
    best_key, best_len = None, 0
    for fragment, key in DISEASE_NAME_MAP.items():
        if fragment in lower and len(fragment) > best_len:
            best_key, best_len = key, len(fragment)
    return best_key


def _check_hardcoded_contraindications(
    drug_name: str,
    disease_key: str,
) -> Optional[Dict]:
    """
    Layer 1: Check hardcoded critical contraindications.
    Returns contraindication info dict or None if safe.
    """
    if not disease_key or disease_key not in CRITICAL_CONTRAINDICATIONS:
        return None

    drug_lower = drug_name.lower().strip()
    contraindication_list = CRITICAL_CONTRAINDICATIONS[disease_key]

    for contra in contraindication_list:
        for known_drug in contra["drugs"]:
            known_lower = known_drug.lower()
            # Exact match or drug name contains the known drug name
            if known_lower == drug_lower or drug_lower.startswith(known_lower) or known_lower in drug_lower:
                return {
                    "drug": drug_name,
                    "reason": contra["reason"],
                    "severity": contra["severity"],
                    "source": "clinical_contraindications_db",
                    "fda_section": "contraindications"
                    if contra["severity"] == "absolute"
                    else "warnings_and_precautions",
                }
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  LAYER 2: FDA LABEL API
# ─────────────────────────────────────────────────────────────────────────────

LABEL_BASE = "https://api.fda.gov/drug/label.json"
LABEL_SECTIONS = [
    "contraindications",
    "boxed_warning",
    "warnings_and_precautions",
    "warnings",
]


async def _fetch_label(
    session: "aiohttp.ClientSession",
    drug_name: str,
    cache: Dict[str, Optional[Dict]],
    api_key: Optional[str] = None,
) -> Optional[Dict]:
    """Fetch the FDA label for a drug. Tries exact match then full-text."""
    key = drug_name.lower()
    if key in cache:
        return cache[key]

    params_base = f"&api_key={api_key}" if api_key else ""
    urls = [
        f'{LABEL_BASE}?search=openfda.generic_name:"{quote(key)}"&limit=1{params_base}',
        f'{LABEL_BASE}?search="{quote(key)}"&limit=1{params_base}',
    ]

    for url in urls:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    results = data.get("results", [])
                    if results:
                        cache[key] = results[0]
                        return results[0]
                elif resp.status not in (404, 400):
                    logger.debug(f"FDA API {resp.status} for {drug_name}")
        except Exception as e:
            logger.debug(f"FDA fetch error for {drug_name}: {e}")
            break

    cache[key] = None
    return None


def _extract_label_text(label: Dict, section: str) -> str:
    val = label.get(section)
    if not val:
        return ""
    if isinstance(val, list):
        return " ".join(val).lower()
    return str(val).lower()


def _find_disease_mention(
    label: Dict, keywords: List[str]
) -> Optional[Tuple[str, str, str]]:
    """Search label for disease keywords. Returns (section, severity, excerpt)."""
    for section in LABEL_SECTIONS:
        text = _extract_label_text(label, section)
        if not text:
            continue
        for kw in keywords:
            if kw.lower() in text:
                idx = text.find(kw.lower())
                start = max(0, idx - 80)
                end = min(len(text), idx + 180)
                excerpt = re.sub(r"\s+", " ", text[start:end].strip())
                # FIXED: both contraindications AND warnings are now treated as absolute
                # when they mention the disease we're treating
                severity = (
                    "absolute"
                    if section in ("contraindications", "boxed_warning",
                                   "warnings_and_precautions", "warnings")
                    else "relative"
                )
                return section, severity, f"...{excerpt}..."
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN FILTER CLASS
# ─────────────────────────────────────────────────────────────────────────────

class DrugSafetyFilter:
    """
    Two-layer drug safety filter.

    Layer 1: Hardcoded critical contraindications (always runs, no network needed)
    Layer 2: FDA label API (additional coverage, requires network)

    Public methods:
      filter_drugs()       — accepts List[str] of drug names
      filter_candidates()  — accepts List[Dict] from the pipeline (main.py)
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self._cache: Dict[str, Optional[Dict]] = {}

    def filter_drugs(
        self,
        candidate_drugs: List[str],
        disease_name: str,
    ) -> Tuple[List[str], List[Dict]]:
        """Filter a plain list of drug name strings.
        
        Layer 1 (hardcoded critical contraindications) always runs.
        Layer 2 (FDA label API) requires aiohttp; if unavailable, a warning is logged.
        """
        if not _AIOHTTP_AVAILABLE:
            logger.warning("aiohttp not available — FDA label API (Layer 2) disabled. "
                           "Critical contraindications (Layer 1) still enforced.")
        return asyncio.run(self._async_filter(candidate_drugs, disease_name))

    def filter_candidates(
        self,
        candidates: List[Dict],
        disease_name: str,
        remove_absolute: bool = True,
        remove_relative: bool = True,  # FIXED: default True to catch all dangerous drugs
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Filter pipeline candidate dicts (each must have a 'drug_name' key).
        Returns (safe_candidates, filtered_candidates).
        
        FIXED: remove_relative now defaults to True so drugs like olanzapine
        that have 'warnings_and_precautions' entries are properly filtered.
        """
        if not _AIOHTTP_AVAILABLE:
            logger.warning("aiohttp not available — FDA label API (Layer 2) disabled. "
                           "Critical contraindications (Layer 1) still enforced.")
        if not candidates:
            return [], []

        drug_names = [
            c.get("drug_name") or c.get("name") or ""
            for c in candidates
        ]
        name_to_candidate = {
            (c.get("drug_name") or c.get("name") or "").lower(): c
            for c in candidates
        }

        safe_names, filtered_info = asyncio.run(
            self._async_filter(drug_names, disease_name)
        )
        filtered_name_map = {f["drug"].lower(): f for f in filtered_info}

        safe_candidates: List[Dict] = []
        filtered_candidates: List[Dict] = []

        for drug_name in drug_names:
            key = drug_name.lower()
            candidate = dict(name_to_candidate.get(key, {"drug_name": drug_name}))

            if key in filtered_name_map:
                hit = filtered_name_map[key]
                severity = hit["severity"]
                candidate["contraindication"] = {
                    "reason": hit["reason"],
                    "severity": severity,
                    "source": hit.get("source", ""),
                    "fda_section": hit.get("fda_section", ""),
                }
                if severity == "withdrawn":
                    filtered_candidates.append(candidate)
                elif severity == "absolute" and remove_absolute:
                    filtered_candidates.append(candidate)
                elif severity == "relative" and remove_relative:
                    filtered_candidates.append(candidate)
                else:
                    candidate["safety_warning"] = hit["reason"]
                    safe_candidates.append(candidate)
            else:
                safe_candidates.append(candidate)

        logger.info(
            f"filter_candidates: {len(filtered_candidates)}/{len(candidates)} "
            f"removed for '{disease_name}'"
        )
        return safe_candidates, filtered_candidates

    async def _async_filter(
        self,
        candidate_drugs: List[str],
        disease_name: str,
    ) -> Tuple[List[str], List[Dict]]:
        """Two-layer async filter: hardcoded first, FDA API second."""

        disease_key = normalize_disease_name(disease_name)
        fda_keywords = DISEASE_KEYWORDS.get(disease_key, []) if disease_key else []

        if not disease_key:
            logger.warning(
                f"No disease key found for '{disease_name}'. "
                "Only withdrawn drugs and hardcoded contraindications will be filtered."
            )

        # --- Layer 2: FDA label fetch (run in parallel) ---
        labels: Dict[str, Optional[Dict]] = {}
        if _AIOHTTP_AVAILABLE and fda_keywords:
            try:
                async with aiohttp.ClientSession() as session:
                    tasks = {
                        drug: asyncio.create_task(
                            _fetch_label(session, drug.lower(), self._cache, self.api_key)
                        )
                        for drug in candidate_drugs
                    }
                    for drug, task in tasks.items():
                        try:
                            labels[drug] = await task
                        except Exception as e:
                            logger.error(f"Label fetch task failed for {drug}: {e}")
                            labels[drug] = None
            except Exception as e:
                logger.warning(f"FDA label fetch failed: {e}. Relying on hardcoded DB.")

        safe_drugs: List[str] = []
        filtered_drugs: List[Dict] = []

        for drug in candidate_drugs:
            drug_lower = drug.lower()

            # 0. Check withdrawn
            if drug_lower in WITHDRAWN_DRUGS:
                filtered_drugs.append({
                    "drug": drug,
                    "reason": "Market-withdrawn drug (FDA safety recall).",
                    "severity": "withdrawn",
                    "source": "withdrawn_db",
                    "fda_section": "market_withdrawal",
                })
                logger.info(f"FILTERED (withdrawn): {drug}")
                continue

            # 1. Layer 1: hardcoded critical contraindications
            hardcoded_hit = _check_hardcoded_contraindications(drug, disease_key)
            if hardcoded_hit:
                filtered_drugs.append(hardcoded_hit)
                logger.info(
                    f"FILTERED (hardcoded/{hardcoded_hit['severity']}): "
                    f"{drug} for '{disease_name}'"
                )
                continue

            # 2. Layer 2: FDA label API
            label = labels.get(drug)
            if label is None:
                # No label found — pass through (benefit of doubt)
                safe_drugs.append(drug)
                continue

            if fda_keywords:
                hit = _find_disease_mention(label, fda_keywords)
                if hit:
                    section, severity, excerpt = hit
                    filtered_drugs.append({
                        "drug": drug,
                        "reason": f"FDA label ({section.replace('_', ' ')}): {excerpt}",
                        "severity": severity,
                        "source": "fda_label",
                        "fda_section": section,
                    })
                    logger.info(
                        f"FILTERED (fda_label/{section}): {drug} for '{disease_name}'"
                    )
                    continue

            safe_drugs.append(drug)

        logger.info(
            f"Safety filter: {len(filtered_drugs)}/{len(candidate_drugs)} "
            f"drugs removed for '{disease_name}'"
        )
        return safe_drugs, filtered_drugs


# ─────────────────────────────────────────────────────────────────────────────
#  CONVENIENCE FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def filter_unsafe_drugs(
    candidate_drugs: List[str],
    disease_name: str,
    api_key: Optional[str] = None,
) -> Tuple[List[str], List[Dict]]:
    """Convenience wrapper around DrugSafetyFilter.filter_drugs()."""
    return DrugSafetyFilter(api_key=api_key).filter_drugs(candidate_drugs, disease_name)


# ─────────────────────────────────────────────────────────────────────────────
#  SELF-TEST
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if not _AIOHTTP_AVAILABLE:
        print("ERROR: aiohttp not installed. Run: pip install aiohttp")
        sys.exit(1)

    test_cases = [
        {
            "disease": "Type 2 Diabetes Mellitus",
            "candidates": [
                {"drug_name": "olanzapine"},
                {"drug_name": "clozapine"},
                {"drug_name": "prednisone"},
                {"drug_name": "metformin"},
                {"drug_name": "sitagliptin"},
                {"drug_name": "hydrochlorothiazide"},
            ],
            "must_filter": {"olanzapine", "clozapine", "prednisone"},
        },
        {
            "disease": "Parkinson Disease",
            "candidates": [
                {"drug_name": "haloperidol"},
                {"drug_name": "olanzapine"},
                {"drug_name": "metoclopramide"},
                {"drug_name": "levodopa"},
                {"drug_name": "carbidopa"},
            ],
            "must_filter": {"haloperidol", "olanzapine", "metoclopramide"},
        },
        {
            "disease": "Alzheimer Disease",
            "candidates": [
                {"drug_name": "diphenhydramine"},
                {"drug_name": "amitriptyline"},
                {"drug_name": "donepezil"},
                {"drug_name": "memantine"},
                {"drug_name": "diazepam"},
            ],
            "must_filter": {"diphenhydramine", "amitriptyline", "diazepam"},
        },
        {
            "disease": "Asthma",
            "candidates": [
                {"drug_name": "propranolol"},
                {"drug_name": "atenolol"},
                {"drug_name": "metoprolol"},
                {"drug_name": "montelukast"},
                {"drug_name": "fluticasone"},
            ],
            "must_filter": {"propranolol", "atenolol", "metoprolol"},
        },
    ]

    f = DrugSafetyFilter()
    all_passed = True

    for tc in test_cases:
        print(f"\n{'─'*60}")
        print(f"DISEASE: {tc['disease']}")
        print(f"{'─'*60}")
        safe, filtered = f.filter_candidates(tc["candidates"], tc["disease"])
        filtered_names = {c["drug_name"].lower() for c in filtered}
        missing = tc["must_filter"] - filtered_names

        print(f"✅ SAFE ({len(safe)}): {[c['drug_name'] for c in safe]}")
        print(f"❌ FILTERED ({len(filtered)}):")
        for c in filtered:
            info = c.get("contraindication", {})
            src = info.get("source", "?")
            sev = info.get("severity", "?")
            reason = info.get("reason", "")[:80]
            print(f"   [{sev.upper()}] {c['drug_name']} ({src})")
            print(f"   → {reason}...")

        if missing:
            all_passed = False
            print(f"\n  ⚠️  MISSED (CRITICAL!): {sorted(missing)}")
            status = "FAIL ❌"
        else:
            status = "PASS ✅"

        print(f"\n  RESULT: {status}")

    print(f"\n{'═'*60}")
    print("ALL TESTS PASSED ✅" if all_passed else "SOME TESTS FAILED ❌")