"""Three-stage entity resolution engine for deduplication and canonical graph linking."""

import difflib
import re

from extraction.schemas import ExtractedEntity, ResolvedEntityReference

KNOWN_PORT_ALIASES: dict[str, tuple[str, str, str]] = {
    "shanghai": ("PORT-SHA", "Port of Shanghai", "CNSHA"),
    "port of shanghai": ("PORT-SHA", "Port of Shanghai", "CNSHA"),
    "shanghai port": ("PORT-SHA", "Port of Shanghai", "CNSHA"),
    "singapore": ("PORT-SIN", "Port of Singapore", "SGSIN"),
    "port of singapore": ("PORT-SIN", "Port of Singapore", "SGSIN"),
    "singapore port": ("PORT-SIN", "Port of Singapore", "SGSIN"),
    "ningbo": ("PORT-NGB", "Port of Ningbo-Zhoushan", "CNNGB"),
    "port of ningbo": ("PORT-NGB", "Port of Ningbo-Zhoushan", "CNNGB"),
    "port of ningbo-zhoushan": ("PORT-NGB", "Port of Ningbo-Zhoushan", "CNNGB"),
    "ningbo-zhoushan": ("PORT-NGB", "Port of Ningbo-Zhoushan", "CNNGB"),
    "shenzhen": ("PORT-SZX", "Port of Shenzhen", "CNSZX"),
    "port of shenzhen": ("PORT-SZX", "Port of Shenzhen", "CNSZX"),
    "yantian": ("PORT-SZX", "Port of Shenzhen", "CNSZX"),
    "shekou": ("PORT-SZX", "Port of Shenzhen", "CNSZX"),
    "busan": ("PORT-PUS", "Port of Busan", "KRPUS"),
    "port of busan": ("PORT-PUS", "Port of Busan", "KRPUS"),
    "los angeles": ("PORT-LAX", "Port of Los Angeles", "USLAX"),
    "port of los angeles": ("PORT-LAX", "Port of Los Angeles", "USLAX"),
    "port of la": ("PORT-LAX", "Port of Los Angeles", "USLAX"),
    "la port": ("PORT-LAX", "Port of Los Angeles", "USLAX"),
    "long beach": ("PORT-LGB", "Port of Long Beach", "USLGB"),
    "port of long beach": ("PORT-LGB", "Port of Long Beach", "USLGB"),
    "rotterdam": ("PORT-RTM", "Port of Rotterdam", "NLRTM"),
    "port of rotterdam": ("PORT-RTM", "Port of Rotterdam", "NLRTM"),
    "antwerp": ("PORT-ANR", "Port of Antwerp-Bruges", "BEANR"),
    "antwerp-bruges": ("PORT-ANR", "Port of Antwerp-Bruges", "BEANR"),
    "port of antwerp": ("PORT-ANR", "Port of Antwerp-Bruges", "BEANR"),
    "port of antwerp-bruges": ("PORT-ANR", "Port of Antwerp-Bruges", "BEANR"),
    "hamburg": ("PORT-HAM", "Port of Hamburg", "DEHAM"),
    "port of hamburg": ("PORT-HAM", "Port of Hamburg", "DEHAM"),
    "kaohsiung": ("PORT-KHH", "Port of Kaohsiung", "TWKHH"),
    "port of kaohsiung": ("PORT-KHH", "Port of Kaohsiung", "TWKHH"),
    "tokyo": ("PORT-TYO", "Port of Tokyo", "JPTYO"),
    "port of tokyo": ("PORT-TYO", "Port of Tokyo", "JPTYO"),
}

KNOWN_COUNTRY_ALIASES: dict[str, tuple[str, str]] = {
    "china": ("CN", "China"),
    "prc": ("CN", "China"),
    "taiwan": ("TW", "Taiwan"),
    "united states": ("US", "United States"),
    "usa": ("US", "United States"),
    "us": ("US", "United States"),
    "america": ("US", "United States"),
    "south korea": ("KR", "South Korea"),
    "korea": ("KR", "South Korea"),
    "japan": ("JP", "Japan"),
    "germany": ("DE", "Germany"),
    "netherlands": ("NL", "Netherlands"),
    "holland": ("NL", "Netherlands"),
    "belgium": ("BE", "Belgium"),
    "singapore": ("SG", "Singapore"),
    "vietnam": ("VN", "Vietnam"),
    "malaysia": ("MY", "Malaysia"),
    "india": ("IN", "India"),
    "indonesia": ("ID", "Indonesia"),
    "mexico": ("MX", "Mexico"),
    "united kingdom": ("GB", "United Kingdom"),
    "uk": ("GB", "United Kingdom"),
    "britain": ("GB", "United Kingdom"),
    "france": ("FR", "France"),
    "thailand": ("TH", "Thailand"),
}


def normalize_entity_string(text: str) -> str:
    """Normalize casing, strip punctuation, and trim whitespace from entity string."""
    cleaned = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"\s+", " ", cleaned)


def resolve_port_entity(name: str) -> ResolvedEntityReference | None:
    """Resolve a port name using exact UN/LOCODE, canonical names, or alias matching."""
    norm = normalize_entity_string(name)

    # 1. Exact alias or un_locode match
    if norm in KNOWN_PORT_ALIASES:
        pid, canonical_name, _ = KNOWN_PORT_ALIASES[norm]
        return ResolvedEntityReference(
            original_name=name,
            target_id=pid,
            target_name=canonical_name,
            target_label="Port",
            resolution_method="exact",
            confidence=1.0,
        )

    # 2. Substring or fuzzy matching
    best_match: str | None = None
    best_score: float = 0.0
    for alias_key in KNOWN_PORT_ALIASES:
        if alias_key in norm or norm in alias_key:
            score = 0.90
        else:
            score = difflib.SequenceMatcher(None, norm, alias_key).ratio()

        if score > best_score:
            best_score = score
            best_match = alias_key

    if best_match and best_score >= 0.80:
        pid, canonical_name, _ = KNOWN_PORT_ALIASES[best_match]
        return ResolvedEntityReference(
            original_name=name,
            target_id=pid,
            target_name=canonical_name,
            target_label="Port",
            resolution_method="fuzzy",
            confidence=round(best_score, 2),
        )

    return None


def resolve_country_entity(name: str) -> ResolvedEntityReference | None:
    """Resolve a country reference using ISO-3166-1 alpha-2 codes or common names."""
    norm = normalize_entity_string(name)

    if norm in KNOWN_COUNTRY_ALIASES:
        code, canonical_name = KNOWN_COUNTRY_ALIASES[norm]
        return ResolvedEntityReference(
            original_name=name,
            target_id=code,
            target_name=canonical_name,
            target_label="Country",
            resolution_method="exact",
            confidence=1.0,
        )

    for alias_key, (code, canonical_name) in KNOWN_COUNTRY_ALIASES.items():
        score = difflib.SequenceMatcher(None, norm, alias_key).ratio()
        if score >= 0.85:
            return ResolvedEntityReference(
                original_name=name,
                target_id=code,
                target_name=canonical_name,
                target_label="Country",
                resolution_method="fuzzy",
                confidence=round(score, 2),
            )

    return None


def resolve_entity(
    entity: ExtractedEntity,
    supplier_registry: dict[str, str] | None = None,
    component_registry: dict[str, str] | None = None,
) -> ResolvedEntityReference:
    """Resolve extracted entity to existing knowledge graph node or create new reference."""
    label = entity.label
    name = entity.name.strip()

    # 1. Port Resolution
    if label == "Port":
        port_res = resolve_port_entity(name)
        if port_res:
            return port_res

    # 2. Country Resolution
    if label == "Country":
        country_res = resolve_country_entity(name)
        if country_res:
            return country_res

    # 3. Supplier Resolution against known registry
    if label == "Supplier" and supplier_registry:
        norm = normalize_entity_string(name)
        for supp_name, supp_id in supplier_registry.items():
            s_norm = normalize_entity_string(supp_name)
            if norm == s_norm:
                return ResolvedEntityReference(
                    original_name=name,
                    target_id=supp_id,
                    target_name=supp_name,
                    target_label="Supplier",
                    resolution_method="exact",
                    confidence=1.0,
                )
            if norm in s_norm or s_norm in norm:
                return ResolvedEntityReference(
                    original_name=name,
                    target_id=supp_id,
                    target_name=supp_name,
                    target_label="Supplier",
                    resolution_method="fuzzy",
                    confidence=0.88,
                )

    # 4. Component Resolution against known registry
    if label == "Component" and component_registry:
        norm = normalize_entity_string(name)
        for comp_name, comp_id in component_registry.items():
            c_norm = normalize_entity_string(comp_name)
            if norm in c_norm or c_norm in norm:
                return ResolvedEntityReference(
                    original_name=name,
                    target_id=comp_id,
                    target_name=comp_name,
                    target_label="Component",
                    resolution_method="fuzzy",
                    confidence=0.85,
                )

    # 5. Fallback: New extracted entity node
    safe_id = f"ext_{label.lower()}_{re.sub(r'[^a-zA-Z0-9]', '_', name.lower())[:24]}"
    return ResolvedEntityReference(
        original_name=name,
        target_id=safe_id,
        target_name=name,
        target_label=label,
        resolution_method="new",
        confidence=0.75,
    )
