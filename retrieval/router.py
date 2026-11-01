"""Intent router for classifying queries into lookup, traversal, semantic, or unanswerable."""

import re

from extraction.entity_resolve import normalize_entity_string
from retrieval.schemas import IntentClassification

DISRUPTION_KEYWORDS: list[str] = [
    "strike",
    "disrupt",
    "disrupted",
    "disruption",
    "impact",
    "impacted",
    "affect",
    "affected",
    "at risk",
    "risk",
    "halt",
    "halted",
    "shutdown",
    "delay",
    "delayed",
    "bottleneck",
    "congestion",
    "alternative",
    "alternatives",
    "exposure",
    "exposed",
    "sole source",
    "sole-sourced",
    "single point of failure",
    "earthquake",
    "typhoon",
    "storm",
    "shortage",
    "embargo",
]

LOOKUP_KEYWORDS: list[str] = [
    "who supplies",
    "which supplier",
    "located in",
    "what country",
    "what tier",
    "lead time",
    "reliability score",
    "unit cost",
    "sku",
    "un_locode",
    "throughput",
    "annual revenue",
    "bill of materials",
    "bom",
    "components of",
    "where is",
    "who produces",
    "list suppliers",
    "show details",
]

UNANSWERABLE_PATTERNS: list[str] = [
    r"\b(ceo|cfo|executive|salary|compensation|bonus)\b",
    r"\b(stock price|market cap|dividend|nasdaq|nyse)\b",
    r"\b(weather in|temperature in|forecast for)\b(?!.*port)",
    r"\b(recipe|dinner|restaurant|movie|song|sports|football|basketball)\b",
    r"\b(who is the president|who is the prime minister)\b",
    r"\b(personal life|founder net worth|headcount|hiring)\b",
]

PORT_NAMES: list[str] = [
    "shanghai",
    "singapore",
    "ningbo",
    "shenzhen",
    "busan",
    "los angeles",
    "long beach",
    "rotterdam",
    "antwerp",
    "hamburg",
    "kaohsiung",
    "tokyo",
    "baltimore",
    "montreal",
]

ENTITY_ID_PATTERNS: list[str] = [
    r"\b(sup-\d{3})\b",
    r"\b(cmp-\d{4})\b",
    r"\b(prd-\d{3})\b",
    r"\b(fac-\d{3})\b",
    r"\b(cust-\d{3})\b",
    r"\b(port-[a-z]{3})\b",
]


def extract_recognized_entities(query: str) -> list[str]:
    """Extract recognized port, supplier, component, or product identifiers from query."""
    found: list[str] = []
    norm = normalize_entity_string(query)

    for port in PORT_NAMES:
        if port in norm:
            found.append(f"Port of {port.title()}")

    for pattern in ENTITY_ID_PATTERNS:
        matches = re.findall(pattern, query, re.IGNORECASE)
        for m in matches:
            found.append(m.upper())

    product_names = [
        "ultrabook",
        "titanbook",
        "airlite",
        "tabsight",
        "hyperrack",
        "cloudcore",
        "storagevault",
    ]
    for p in product_names:
        if p in norm:
            found.append(p.title())

    return list(dict.fromkeys(found))


def find_disruption_keywords(query: str) -> list[str]:
    """Identify supply chain disruption keywords present in user question."""
    norm = normalize_entity_string(query)
    return [kw for kw in DISRUPTION_KEYWORDS if kw in norm]


def is_unanswerable_query(query: str) -> bool:
    """Check whether query asks about topics out of scope of supply chain knowledge base."""
    return any(re.search(pattern, query, re.IGNORECASE) for pattern in UNANSWERABLE_PATTERNS)


def classify_intent(query: str) -> IntentClassification:
    """Classify user query into lookup, impact_traversal, semantic, or unanswerable."""
    cleaned = query.strip()
    if not cleaned:
        return IntentClassification(
            intent="unanswerable",
            confidence=1.0,
            reasoning="Empty input query",
            extracted_entities=[],
            disruption_keywords=[],
        )

    # 1. Unanswerable check
    if is_unanswerable_query(cleaned):
        return IntentClassification(
            intent="unanswerable",
            confidence=0.95,
            reasoning=(
                "Question references out-of-domain concepts "
                "(e.g. executive salary, financial markets, sports)"
            ),
            extracted_entities=[],
            disruption_keywords=[],
        )

    entities = extract_recognized_entities(cleaned)
    disruptions = find_disruption_keywords(cleaned)
    norm = normalize_entity_string(cleaned)

    # 2. Impact traversal: Disruption keyword + named entity or downstream propagation
    has_propagation_phrase = any(
        phrase in norm
        for phrase in [
            "which products",
            "what products",
            "alternative suppliers",
            "who can replace",
            "exposure",
            "downstream",
            "total revenue",
            "concentration risk",
        ]
    )

    if (disruptions and (entities or has_propagation_phrase)) or (
        has_propagation_phrase and entities
    ):
        return IntentClassification(
            intent="impact_traversal",
            confidence=0.92,
            reasoning="Query asks for disruption impact propagation across graph entities",
            extracted_entities=entities,
            disruption_keywords=disruptions,
        )

    # 3. Lookup: Direct factual inquiry with identified entity or lookup phrasing
    is_lookup_phrase = any(kw in norm for kw in LOOKUP_KEYWORDS)
    if (is_lookup_phrase and entities) or (entities and len(disruptions) == 0):
        # Specific factual lookup for entity
        return IntentClassification(
            intent="lookup",
            confidence=0.88,
            reasoning="Query targets specific factual properties of named supply chain entity",
            extracted_entities=entities,
            disruption_keywords=[],
        )

    # 4. Default: Semantic search across news articles
    return IntentClassification(
        intent="semantic",
        confidence=0.80,
        reasoning=(
            "Open-ended or thematic supply chain question routed to vector search + graph expansion"
        ),
        extracted_entities=entities,
        disruption_keywords=disruptions,
    )
