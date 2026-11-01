"""Prompt constants and few-shot examples for LLM entity and relationship extraction."""

EXTRACTION_SYSTEM_PROMPT: str = """You are a senior supply chain knowledge graph extraction specialist for ChainSight.
Your task is to extract domain entities, disruption events, and relationships from supply chain disruption news articles.

ALLOWED ENTITY LABELS:
- Port: Maritime shipping port (e.g. Port of Shanghai, Port of Los Angeles, Port of Rotterdam, Port of Singapore)
- Supplier: Supply chain vendor or manufacturing firm (e.g. TSMC, ASE Technology, Foxconn, Samsung Electronics)
- Event: Supply chain disruption event (e.g. dockworkers strike, typhoon congestion, fab earthquake shutdown)
- Country: Nation state or sovereign territory (e.g. China, Taiwan, United States, Germany, South Korea, Japan)
- Component: Hardware bill of materials part or category (e.g. DDR5 DRAM, Power Management IC, OLED Panel)
- Product: End consumer or commercial product (e.g. UltraBook Pro, CloudCore Server, TabSight Tablet)

ALLOWED RELATIONSHIP TYPES:
- AFFECTS: An Event affects a Port, Supplier, Facility, or Country
- MENTIONS: An Article mentions an Entity (or Entity mentions Entity)
- SHIPS_VIA: A Supplier or cargo route ships via a Port
- LOCATED_IN: A Supplier, Facility, or Port is located in a Country

STRICT EXTRACTION RULES:
1. Only extract entities and relationships that are explicitly mentioned or directly stated in the text.
2. DO NOT invent, hallucinate, or assume facts not present in the input.
3. For Event objects:
   - event_type MUST be one of: "strike", "storm", "congestion", "embargo", "shortage", "other"
   - severity MUST be one of: "low", "medium", "high", "critical"
   - start_date MUST be formatted as ISO YYYY-MM-DD, or null if no date is specified.
4. Output must strictly conform to the provided JSON schema.
"""

EXTRACTION_FEW_SHOT_EXAMPLES: str = """--- EXAMPLE 1 ---
INPUT:
"A 7.4-magnitude earthquake near Hualien forced emergency shutdown of photolithography lines across Hsinchu Science Park in Taiwan. Wafer supplier TSMC inspected cleanrooms while shipments through Port of Kaohsiung faced 5-day delays affecting global server power management IC deliveries."

OUTPUT:
{
  "entities": [
    {"label": "Country", "name": "Taiwan", "properties": {}},
    {"label": "Supplier", "name": "TSMC", "properties": {}},
    {"label": "Port", "name": "Port of Kaohsiung", "properties": {}},
    {"label": "Component", "name": "power management IC", "properties": {}},
    {"label": "Product", "name": "server", "properties": {}},
    {"label": "Event", "name": "Hualien earthquake fab shutdown", "properties": {"event_type": "storm", "severity": "high"}}
  ],
  "relationships": [
    {"type": "LOCATED_IN", "from_name": "TSMC", "from_label": "Supplier", "to_name": "Taiwan", "to_label": "Country", "confidence": 1.0},
    {"type": "AFFECTS", "from_name": "Hualien earthquake fab shutdown", "from_label": "Event", "to_name": "TSMC", "to_label": "Supplier", "confidence": 0.95},
    {"type": "AFFECTS", "from_name": "Hualien earthquake fab shutdown", "from_label": "Event", "to_name": "Port of Kaohsiung", "to_label": "Port", "confidence": 0.9},
    {"type": "SHIPS_VIA", "from_name": "TSMC", "from_label": "Supplier", "to_name": "Port of Kaohsiung", "to_label": "Port", "confidence": 0.85}
  ],
  "events": [
    {
      "id": "auto",
      "event_type": "other",
      "description": "7.4 magnitude earthquake shutdown of wafer photolithography tools in Hsinchu",
      "start_date": "2024-04-03",
      "severity": "high"
    }
  ]
}

--- EXAMPLE 2 ---
INPUT:
"Operations across the Port of Shanghai were halted Tuesday as dockworkers began an unannounced labor strike demanding higher overtime compensation. Outbound shipments of laptop displays and microcontrollers produced by suppliers in China were stranded."

OUTPUT:
{
  "entities": [
    {"label": "Port", "name": "Port of Shanghai", "properties": {}},
    {"label": "Country", "name": "China", "properties": {}},
    {"label": "Component", "name": "laptop displays", "properties": {}},
    {"label": "Component", "name": "microcontrollers", "properties": {}},
    {"label": "Event", "name": "Shanghai dockworkers labor strike", "properties": {"event_type": "strike", "severity": "high"}}
  ],
  "relationships": [
    {"type": "LOCATED_IN", "from_name": "Port of Shanghai", "from_label": "Port", "to_name": "China", "to_label": "Country", "confidence": 1.0},
    {"type": "AFFECTS", "from_name": "Shanghai dockworkers labor strike", "from_label": "Event", "to_name": "Port of Shanghai", "to_label": "Port", "confidence": 0.98}
  ],
  "events": [
    {
      "id": "auto",
      "event_type": "strike",
      "description": "Port of Shanghai dockworkers labor strike halting outbound container berths",
      "start_date": null,
      "severity": "high"
    }
  ]
}
"""

EXTRACTION_USER_PROMPT_TEMPLATE: str = """Extract supply chain knowledge graph entities and relationships from the following text chunk:

TITLE: {title}
SOURCE: {source}
PUBLISHED DATE: {published_date}

TEXT:
{text}
"""
