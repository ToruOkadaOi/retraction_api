"""Taxonomy mapping natural language misconduct concepts to Retraction Watch tags and PubPeer utilities."""

import re
from typing import Any

PUBPEER_REGEX = re.compile(
    r"https?://(?:www\.)?pubpeer\.com/(?:publications/|search\?q=)?([A-Za-z0-9]+)",
    re.IGNORECASE,
)


def extract_pubpeer_url(notes: str | None) -> str | None:
    if not notes:
        return None
    match = PUBPEER_REGEX.search(notes)
    if match:
        identifier = match.group(1)
        return f"https://pubpeer.com/publications/{identifier}"
    return None


MISCONDUCT_TAXONOMY: dict[str, dict[str, Any]] = {
    "image_manipulation": {
        "description": "Duplicated, altered, spliced, or fabricated scientific images (Western blots, microscopy, gel electrophoresis).",
        "tags": [
            "Falsification/Fabrication of Images",
            "Duplication of Image",
            "Manipulation of Images",
            "Concerns/Issues About Image",
        ],
    },
    "fake_peer_review": {
        "description": "Compromised or fabricated peer reviews, fake reviewer email accounts, or rogue editor collusion.",
        "tags": [
            "Fake Peer Review",
            "Rogue Editor",
            "Compromised Peer Review",
            "Investigation by Journal/Publisher",
        ],
    },
    "paper_mill": {
        "description": "Commercial paper mill operations producing fraudulent, template-generated, or purchased manuscripts.",
        "tags": [
            "Paper Mill",
            "Similarity to Paper Mill Products",
            "Unreliable Authorship",
            "Forged Authorship",
        ],
    },
    "data_fabrication": {
        "description": "Falsification, fabrication, or invention of experimental, clinical, or statistical data.",
        "tags": [
            "Falsification/Fabrication of Data",
            "Fabrication of Data",
            "Unreliable Data",
            "Concerns/Issues About Data",
        ],
    },
    "plagiarism": {
        "description": "Unattributed copying of text, data, figures, or ideas from previously published works.",
        "tags": [
            "Plagiarism of Text",
            "Plagiarism of Data",
            "Plagiarism of Article",
            "Duplication of Text",
            "Euphemisms for Plagiarism",
        ],
    },
    "author_dispute": {
        "description": "Authorship added without consent, gift authorship, forged author identities, or co-author conflict.",
        "tags": [
            "Author Dispute",
            "Forged Authorship",
            "Unreliable Authorship",
            "False/Forged Author Name",
        ],
    },
    "ethics_and_consent": {
        "description": "Missing institutional review board (IRB) approval, forged ethical clearance, or clinical consent violations.",
        "tags": [
            "Lack of IRB/Ethics Approval",
            "Informed Consent Issues",
            "Ethical Violations",
        ],
    },
    "honest_error": {
        "description": "Non-fraudulent errors, inability to reproduce findings, reagent contamination, or author-initiated self-corrections.",
        "tags": [
            "Error in Data",
            "Error in Analyses",
            "Unreliable Results",
            "Results Not Reproducible",
            "Contamination",
            "Error in Text",
        ],
    },
}


def get_taxonomy_concepts() -> list[dict[str, Any]]:
    return [
        {
            "concept": concept,
            "description": info["description"],
            "tags": info["tags"],
        }
        for concept, info in MISCONDUCT_TAXONOMY.items()
    ]


def map_concept_to_tags(concept: str) -> list[str]:
    concept_lower = concept.strip().lower()
    for key, info in MISCONDUCT_TAXONOMY.items():
        if key == concept_lower or concept_lower in key:
            return info["tags"]
    return []
