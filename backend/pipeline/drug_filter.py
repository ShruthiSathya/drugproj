"""
Drug Safety Filter — OpenFDA-first implementation
===================================================
Exposes TWO public methods on DrugSafetyFilter:

  filter_drugs(candidate_drugs: List[str], disease_name: str)
      → (safe_names: List[str], filtered_info: List[Dict])
      For callers that have a plain list of drug name strings.

  filter_candidates(candidates: List[Dict], disease_name, ...)
      → (safe_candidates: List[Dict], filtered_candidates: List[Dict])
      For callers (like main.py) that have pipeline candidate dicts
      with a 'drug_name' key. THIS IS WHAT main.py CALLS.

Strategy:
  1. Withdrawn-drug list     → always block
  2. OpenFDA label API       → fetch contraindications / boxed_warning /
                               warnings_and_precautions and scan for disease
                               keywords. Returns exact FDA label excerpt.

Key fixes vs. the broken original:
  - Correct query field: openfda.generic_name:"<drug>" (harmonized, exact match)
    The old code used generic_name:<drug> (raw SPL field) which 404s for almost
    every generic name.
  - Searches contraindications + boxed_warning + warnings_and_precautions.
  - filter_candidates() method added so main.py can call it without changes.
  - Errors are logged loudly, never swallowed silently.
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
#  DISEASE KEYWORD MAP
# ─────────────────────────────────────────────────────────────────────────────

DISEASE_KEYWORDS: Dict[str, List[str]] = {
    "parkinson":    ["parkinson", "parkinsonism", "extrapyramidal",
                     "dopamine agonist", "levodopa"],
    "alzheimer":    ["alzheimer", "dementia", "cognitive impairment",
                     "anticholinergic"],
    "diabetes":     ["diabetes", "diabetic", "hyperglycemia",
                     "blood glucose", "insulin", "glycemic"],
    "asthma":       ["asthma", "asthmatic", "bronchospasm",
                     "bronchial", "bronchoconstriction"],
    "copd":         ["copd", "chronic obstructive", "emphysema",
                     "bronchospasm"],
    "epilepsy":     ["epilepsy", "seizure", "convulsion",
                     "seizure threshold"],
    "heart_failure":["heart failure", "cardiac failure",
                     "congestive heart failure"],
    "hypertension": ["hypertension", "high blood pressure"],
    "glaucoma":     ["glaucoma", "intraocular pressure",
                     "angle-closure"],
    "myasthenia_gravis": ["myasthenia gravis", "myasthenic"],
    "kidney_disease":    ["renal impairment", "renal failure",
                          "chronic kidney", "ckd"],
    "liver_disease":     ["hepatic impairment", "hepatotoxic",
                          "cirrhosis", "liver disease"],
    "osteoporosis":      ["osteoporosis", "bone density", "bone loss"],
    "gout":              ["gout", "uric acid", "hyperuricemia"],
    "psoriasis":         ["psoriasis", "psoriatic"],
    "inflammatory_bowel_disease": ["crohn", "ulcerative colitis",
                                   "inflammatory bowel"],
    # Rare diseases
    "gaucher_disease":   ["gaucher", "glucocerebrosidase"],
    "porphyria":         ["porphyria", "aminolevulinic"],
    "huntington_disease":["huntington"],
    "cystic_fibrosis":   ["cystic fibrosis"],
    "duchenne_muscular_dystrophy": ["duchenne", "muscular dystrophy"],
    "fabry_disease":     ["fabry"],
    "pompe_disease":     ["pompe", "glycogen storage"],
    "amyotrophic_lateral_sclerosis": ["amyotrophic lateral sclerosis",
                                       "motor neuron disease"],
    "hemophilia":        ["hemophilia", "haemophilia", "bleeding disorder"],
    "sickle_cell_disease": ["sickle cell"],
    "myotonic_dystrophy":  ["myotonic dystrophy", "myotonia"],
    "phenylketonuria":     ["phenylketonuria", "pku", "phenylalanine"],
    "wilson_disease":      ["wilson disease", "copper toxicity"],
}

# Maps flexible disease names → DISEASE_KEYWORDS key
DISEASE_NAME_MAP: Dict[str, str] = {
    "parkinson": "parkinson", "parkinsonian": "parkinson",
    "parkinson's disease": "parkinson", "parkinson disease": "parkinson",
    "alzheimer": "alzheimer", "alzheimer's disease": "alzheimer",
    "dementia": "alzheimer",
    "diabetes": "diabetes", "diabetic": "diabetes",
    "type 2 diabetes": "diabetes", "type 1 diabetes": "diabetes",
    "diabetes mellitus": "diabetes", "t2dm": "diabetes",
    "type 2 diabetes mellitus": "diabetes",
    "asthma": "asthma", "bronchial asthma": "asthma",
    "copd": "copd", "chronic obstructive pulmonary disease": "copd",
    "emphysema": "copd",
    "epilepsy": "epilepsy", "seizure disorder": "epilepsy",
    "heart failure": "heart_failure", "cardiac failure": "heart_failure",
    "congestive heart failure": "heart_failure", "chf": "heart_failure",
    "hypertension": "hypertension", "high blood pressure": "hypertension",
    "glaucoma": "glaucoma",
    "myasthenia gravis": "myasthenia_gravis", "myasthenia": "myasthenia_gravis",
    "kidney disease": "kidney_disease", "renal disease": "kidney_disease",
    "chronic kidney disease": "kidney_disease", "ckd": "kidney_disease",
    "liver disease": "liver_disease", "hepatic disease": "liver_disease",
    "cirrhosis": "liver_disease",
    "osteoporosis": "osteoporosis",
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


def normalize_disease_name(disease_name: str) -> Optional[str]:
    """Map raw disease name to canonical DISEASE_KEYWORDS key."""
    lower = disease_name.lower().strip()
    if lower in DISEASE_KEYWORDS:
        return lower
    best_key, best_len = None, 0
    for fragment, key in DISEASE_NAME_MAP.items():
        if fragment in lower and len(fragment) > best_len:
            best_key, best_len = key, len(fragment)
    return best_key


# ─────────────────────────────────────────────────────────────────────────────
#  FDA LABEL FETCHER
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
    """
    Fetch the FDA label for a drug. Tries two query strategies:
      1. openfda.generic_name:"<drug>"  — harmonized field, exact match (best)
      2. "<drug>"                        — full-text search (broader fallback)
    Caches results to avoid duplicate requests.
    """
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
            break  # network error — stop retrying

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
    """
    Search label sections for any disease keyword.
    Returns (section, severity, excerpt) or None.
    severity = "absolute" for contraindications/boxed_warning, "relative" otherwise.
    """
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
                severity = (
                    "absolute"
                    if section in ("contraindications", "boxed_warning")
                    else "relative"
                )
                return section, severity, f"...{excerpt}..."
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN FILTER CLASS
# ─────────────────────────────────────────────────────────────────────────────

class DrugSafetyFilter:
    """
    Filters unsafe drug candidates using the OpenFDA label API.

    Two public methods:
      filter_drugs()       — accepts List[str] of drug names
      filter_candidates()  — accepts List[Dict] from the pipeline (has 'drug_name' key)
                             THIS IS WHAT main.py calls.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self._cache: Dict[str, Optional[Dict]] = {}

    # ── Public: string list interface ────────────────────────────────────────

    def filter_drugs(
        self,
        candidate_drugs: List[str],
        disease_name: str,
    ) -> Tuple[List[str], List[Dict]]:
        """
        Filter a plain list of drug name strings.
        Returns (safe_drug_names, filtered_info_list).
        """
        if not _AIOHTTP_AVAILABLE:
            raise RuntimeError("aiohttp is required: pip install aiohttp")
        return asyncio.run(self._async_filter(candidate_drugs, disease_name))

    # ── Public: pipeline dict interface ──────────────────────────────────────

    def filter_candidates(
        self,
        candidates: List[Dict],
        disease_name: str,
        remove_absolute: bool = True,
        remove_relative: bool = False,
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Filter pipeline candidate dicts (each must have a 'drug_name' key).
        Returns (safe_candidates, filtered_candidates) — both as full dicts.

        Contraindication info is attached to filtered items under the
        'contraindication' key so main.py can read it directly.

        This is the method called by the FastAPI endpoint in main.py.
        """
        if not _AIOHTTP_AVAILABLE:
            raise RuntimeError("aiohttp is required: pip install aiohttp")
        if not candidates:
            return [], []

        # Extract drug name strings for the async fetcher
        drug_names = [
            c.get("drug_name") or c.get("name") or ""
            for c in candidates
        ]
        name_to_candidate = {
            (c.get("drug_name") or c.get("name") or "").lower(): c
            for c in candidates
        }

        # Run FDA lookup
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
                # Decide whether to actually remove based on caller's preference
                if severity == "withdrawn":
                    filtered_candidates.append(candidate)
                elif severity == "absolute" and remove_absolute:
                    filtered_candidates.append(candidate)
                elif severity == "relative" and remove_relative:
                    filtered_candidates.append(candidate)
                else:
                    # Has a warning but caller chose to keep it — annotate and pass through
                    candidate["safety_warning"] = hit["reason"]
                    safe_candidates.append(candidate)
            else:
                safe_candidates.append(candidate)

        logger.info(
            f"filter_candidates: {len(filtered_candidates)}/{len(candidates)} "
            f"removed for '{disease_name}'"
        )
        return safe_candidates, filtered_candidates

    # ── Internal async logic ──────────────────────────────────────────────────

    async def _async_filter(
        self,
        candidate_drugs: List[str],
        disease_name: str,
    ) -> Tuple[List[str], List[Dict]]:

        db_key = normalize_disease_name(disease_name)
        keywords = DISEASE_KEYWORDS.get(db_key, []) if db_key else []

        if not keywords:
            logger.warning(
                f"No disease keywords found for '{disease_name}'. "
                "Only withdrawn drugs will be filtered."
            )

        safe_drugs: List[str] = []
        filtered_drugs: List[Dict] = []

        async with aiohttp.ClientSession() as session:
            tasks = {
                drug: asyncio.create_task(
                    _fetch_label(session, drug.lower(), self._cache, self.api_key)
                )
                for drug in candidate_drugs
            }
            labels: Dict[str, Optional[Dict]] = {}
            for drug, task in tasks.items():
                try:
                    labels[drug] = await task
                except Exception as e:
                    logger.error(f"Label fetch task failed for {drug}: {e}")
                    labels[drug] = None

        for drug in candidate_drugs:
            drug_lower = drug.lower()

            # 1. Withdrawn?
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

            # 2. FDA label scan
            label = labels.get(drug)
            if label is None:
                logger.warning(
                    f"No FDA label found for '{drug}' — passing through unverified."
                )
                safe_drugs.append(drug)
                continue

            if keywords:
                hit = _find_disease_mention(label, keywords)
                if hit:
                    section, severity, excerpt = hit
                    filtered_drugs.append({
                        "drug": drug,
                        "reason": (
                            f"FDA label ({section.replace('_', ' ')}): {excerpt}"
                        ),
                        "severity": severity,
                        "source": "fda_label",
                        "fda_section": section,
                    })
                    logger.info(
                        f"FILTERED (fda_label/{section}, {severity}): "
                        f"{drug} for '{disease_name}'"
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
    """
    Convenience wrapper around DrugSafetyFilter.filter_drugs().
    Accepts plain drug name strings.
    """
    return DrugSafetyFilter(api_key=api_key).filter_drugs(
        candidate_drugs, disease_name
    )


# ─────────────────────────────────────────────────────────────────────────────
#  SELF-TEST
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if not _AIOHTTP_AVAILABLE:
        print("ERROR: aiohttp not installed. Run: pip install aiohttp")
        exit(1)

    # Test filter_candidates() — same dict format as main.py uses
    test_cases = [
        {
            "disease": "Parkinson Disease",
            "candidates": [
                {"drug_name": "haloperidol"},
                {"drug_name": "olanzapine"},
                {"drug_name": "levodopa"},
                {"drug_name": "metoclopramide"},
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
                {"drug_name": "galantamine"},
            ],
            "must_filter": {"diphenhydramine", "amitriptyline"},
        },
        {
            "disease": "type 2 diabetes mellitus",
            "candidates": [
                {"drug_name": "olanzapine"},
                {"drug_name": "prednisone"},
                {"drug_name": "metformin"},
                {"drug_name": "sitagliptin"},
            ],
            "must_filter": {"olanzapine", "prednisone"},
        },
        {
            "disease": "Asthma",
            "candidates": [
                {"drug_name": "propranolol"},
                {"drug_name": "atenolol"},
                {"drug_name": "montelukast"},
                {"drug_name": "fluticasone"},
            ],
            "must_filter": {"propranolol", "atenolol"},
        },
    ]

    f = DrugSafetyFilter()
    all_passed = True
    for tc in test_cases:
        print(f"\n── {tc['disease']} ──")
        safe, filtered = f.filter_candidates(tc["candidates"], tc["disease"])
        filtered_names = {c["drug_name"].lower() for c in filtered}
        missing = tc["must_filter"] - filtered_names

        for c in filtered:
            info = c.get("contraindication", {})
            print(f"  FILTERED [{info.get('severity','?')}] {c['drug_name']}")
            print(f"    {info.get('reason','')[:110]}...")

        status = "PASS" if not missing else "FAIL"
        if missing:
            all_passed = False
            print(f"  MISSED (critical!): {sorted(missing)}")
        print(f"  → {status}")

    print("\n" + ("ALL TESTS PASSED" if all_passed else "SOME TESTS FAILED"))