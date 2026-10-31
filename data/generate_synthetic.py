"""Generate realistic synthetic supply chain data for ChainSight graph RAG."""

import csv
import math
import random
from pathlib import Path

from faker import Faker

from data.models import (
    Component,
    ComponentPartOfProduct,
    Country,
    Customer,
    Facility,
    FacilityShipsToCustomer,
    Port,
    Product,
    Supplier,
    SupplierAlternativeFor,
    SupplierOperatesFacility,
    SupplierProducesComponent,
    SupplierShipsViaPort,
)

FAKE = Faker()
Faker.seed(42)
random.seed(42)


def get_country_definitions() -> list[Country]:
    """Return 20 realistic countries including 8 high geopolitical risk countries."""
    raw_countries = [
        # code, name, region, risk_index (8 >= 0.60)
        ("CN", "China", "East Asia", 0.68),
        ("TW", "Taiwan", "East Asia", 0.64),
        ("VN", "Vietnam", "Southeast Asia", 0.62),
        ("IN", "India", "South Asia", 0.61),
        ("MY", "Malaysia", "Southeast Asia", 0.63),
        ("PH", "Philippines", "Southeast Asia", 0.65),
        ("ID", "Indonesia", "Southeast Asia", 0.61),
        ("MX", "Mexico", "North America", 0.62),
        ("KR", "South Korea", "East Asia", 0.35),
        ("JP", "Japan", "East Asia", 0.22),
        ("SG", "Singapore", "Southeast Asia", 0.15),
        ("US", "United States", "North America", 0.25),
        ("DE", "Germany", "Western Europe", 0.20),
        ("NL", "Netherlands", "Western Europe", 0.18),
        ("BE", "Belgium", "Western Europe", 0.21),
        ("GB", "United Kingdom", "Western Europe", 0.24),
        ("FR", "France", "Western Europe", 0.22),
        ("TH", "Thailand", "Southeast Asia", 0.48),
        ("IE", "Ireland", "Western Europe", 0.19),
        ("IL", "Israel", "Middle East", 0.58),
    ]
    return [
        Country(code=code, name=name, region=region, risk_index=risk)
        for code, name, region, risk in raw_countries
    ]


def load_reference_ports(ref_csv_path: Path) -> list[Port]:
    """Load reference ports with real coordinates and UN/LOCODEs from CSV."""
    ports: list[Port] = []
    with open(ref_csv_path, encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            ports.append(
                Port(
                    id=row["id"],
                    name=row["name"],
                    country_code=row["country_code"],
                    un_locode=row["un_locode"],
                    lat=float(row["lat"]),
                    lon=float(row["lon"]),
                    throughput_teu_annual=int(row["throughput_teu_annual"]),
                )
            )
    return ports


def generate_suppliers(countries: list[Country]) -> list[Supplier]:
    """Generate 40 suppliers distributed across tiers with 60% in East/Southeast Asia."""
    suppliers: list[Supplier] = []
    asian_country_codes = ["CN", "TW", "KR", "VN", "JP", "MY", "SG"]
    other_country_codes = [c.code for c in countries if c.code not in asian_country_codes]

    company_suffixes = [
        "Semiconductor",
        "Technologies",
        "Precision",
        "Optics",
        "Electronics",
        "Micro",
        "Materials",
        "Components",
    ]

    # 10 Tier-1, 20 Tier-2, 10 Tier-3
    tiers = [1] * 10 + [2] * 20 + [3] * 10
    for idx, tier in enumerate(tiers, start=1):
        # 60% probability of selecting an Asian manufacturing country
        if random.random() < 0.60:
            c_code = random.choice(asian_country_codes)
        else:
            c_code = random.choice(other_country_codes)

        # Reliability score from Beta(8, 2)
        rel_score = round(random.betavariate(8, 2), 3)

        # Lead time days from LogNormal(mean=3.5, sigma=0.5) ~ 20 to 65 days
        raw_lead = math.exp(random.normalvariate(3.5, 0.5))
        lead_time = max(7, min(120, int(raw_lead)))

        company_name = f"{FAKE.last_name()} {random.choice(company_suffixes)}"
        suppliers.append(
            Supplier(
                id=f"SUP-{idx:03d}",
                name=company_name,
                country_code=c_code,
                reliability_score=rel_score,
                lead_time_days=lead_time,
                tier=tier,
            )
        )
    return suppliers


def generate_facilities(
    suppliers: list[Supplier],
) -> tuple[list[Facility], list[SupplierOperatesFacility]]:
    """Generate 55 facilities operated by suppliers with realistic capacity and coords."""
    facilities: list[Facility] = []
    operates: list[SupplierOperatesFacility] = []
    fac_types = ["factory", "factory", "warehouse", "dc"]

    # Ensure each supplier has at least 1 facility; 15 suppliers have 2 facilities -> 55 total
    extra_facility_supplier_ids = set(random.sample([s.id for s in suppliers], 15))
    fac_idx = 1

    for s in suppliers:
        num_facs = 2 if s.id in extra_facility_supplier_ids else 1
        for sub_idx in range(num_facs):
            fac_id = f"FAC-{fac_idx:03d}"
            f_type = random.choice(fac_types) if sub_idx > 0 else "factory"
            capacity = random.randint(50000, 5000000)

            # Approximate coordinate offset from country or supplier
            lat = round(random.uniform(-40.0, 55.0), 4)
            lon = round(random.uniform(-120.0, 140.0), 4)

            name = f"{s.name} {f_type.capitalize()} #{sub_idx + 1}"
            facility = Facility(
                id=fac_id,
                name=name,
                supplier_id=s.id,
                country_code=s.country_code,
                facility_type=f_type,
                capacity_units=capacity,
                lat=lat,
                lon=lon,
            )
            facilities.append(facility)
            operates.append(
                SupplierOperatesFacility(
                    supplier_id=s.id,
                    facility_id=fac_id,
                    since_year=random.randint(2005, 2022),
                )
            )
            fac_idx += 1

    return facilities, operates


def generate_components() -> list[Component]:
    """Generate 60 components across hardware categories with 15 marked sole-sourced."""
    categories = [
        (
            "Compute",
            [
                "CPU SoC Gen4",
                "AI Neural Accelerator",
                "RISC-V Microcontroller",
                "DSP Core",
                "Power Management IC",
                "Clock Generator",
            ],
        ),
        (
            "Memory",
            [
                "DDR5 DRAM 16GB",
                "LPDDR5X Module",
                "NVMe NAND 512GB",
                "EEPROM Configuration Chip",
                "SRAM Cache Die",
                "NOR Flash Module",
            ],
        ),
        (
            "Display & Optical",
            [
                "OLED Retina Panel",
                "AMOLED Flex Display",
                "Mini-LED Backlight Unit",
                "Touch Controller IC",
                "Front Camera Sensor 12MP",
                "LiDAR Sensor Module",
            ],
        ),
        (
            "Connectivity",
            [
                "Wi-Fi 7 / BT 5.4 Combo IC",
                "5G Sub-6GHz Modem",
                "RF Transceiver Front-End",
                "GNSS Location Chip",
                "NFC Secure Element",
                "Ethernet PHY Controller",
            ],
        ),
        (
            "Power & Battery",
            [
                "Lithium-Cobalt Battery 5000mAh",
                "GaN Fast Charger Controller",
                "Battery Management ASIC",
                "DC-DC Buck Converter",
                "Wireless Charging Coil",
                "Current Sensor",
            ],
        ),
        (
            "Chassis & Passive",
            [
                "CNC Aluminum Chassis",
                "Titanium Frame Structural Bezel",
                "Vapor Chamber Heat Sink",
                "Multilayer Ceramic Capacitor Set",
                "Graphene Thermal Pad",
                "Shielding Cans",
            ],
        ),
    ]

    all_components: list[Component] = []
    comp_idx = 1
    # We want 60 components total: 10 per category
    for cat_name, subparts in categories:
        for i in range(10):
            base_name = subparts[i % len(subparts)]
            comp_id = f"CMP-{comp_idx:04d}"
            cost = round(random.uniform(2.5, 350.0), 2)
            lead = max(10, min(140, int(math.exp(random.normalvariate(3.6, 0.4)))))
            all_components.append(
                Component(
                    id=comp_id,
                    name=f"{base_name} (v{comp_idx})",
                    category=cat_name,
                    unit_cost_usd=cost,
                    lead_time_days=lead,
                    is_sole_sourced=False,
                )
            )
            comp_idx += 1

    # Exactly 15 sole-sourced components
    sole_sourced_indices = random.sample(range(len(all_components)), 15)
    for idx in sole_sourced_indices:
        all_components[idx].is_sole_sourced = True

    return all_components


def generate_products() -> list[Product]:
    """Generate 9 products spanning Laptop, Tablet, and Server families."""
    products_def = [
        ("PRD-001", "UltraBook Pro 14", "LAP-UB14-01", "Laptop", 85000000.0, 32.5),
        ("PRD-002", "TitanBook Creator 16", "LAP-TB16-02", "Laptop", 62000000.0, 35.0),
        ("PRD-003", "AirLite Student 13", "LAP-AL13-03", "Laptop", 45000000.0, 24.0),
        ("PRD-004", "TabSight Air 11", "TAB-AIR11-01", "Tablet", 52000000.0, 38.0),
        ("PRD-005", "TabSight Pro Max 13", "TAB-PRO13-02", "Tablet", 71000000.0, 41.5),
        ("PRD-006", "TabSight Lite 8", "TAB-LT08-03", "Tablet", 28000000.0, 26.0),
        ("PRD-007", "HyperRack Edge Server E1", "SRV-EDGE-01", "Server", 115000000.0, 45.0),
        ("PRD-008", "CloudCore AI Node G8", "SRV-AINODE-02", "Server", 240000000.0, 48.5),
        ("PRD-009", "StorageVault SAN 4U", "SRV-SAN4U-03", "Server", 92000000.0, 42.0),
    ]
    return [
        Product(
            id=pid,
            name=name,
            sku=sku,
            family=family,
            revenue_usd_annual=rev,
            margin_pct=margin,
        )
        for pid, name, sku, family, rev, margin in products_def
    ]


def generate_customers(countries: list[Country]) -> list[Customer]:
    """Generate 15 enterprise customers across global regions."""
    segments = [
        "Enterprise Cloud",
        "Automotive OEM",
        "Defense & Aerospace",
        "Healthcare Systems",
        "Global Retail",
        "Telecom Infrastructure",
    ]
    customer_country_codes = ["US", "DE", "JP", "GB", "FR", "KR", "NL", "SG"]
    customers: list[Customer] = []
    for idx in range(1, 16):
        c_id = f"CUST-{idx:03d}"
        name = f"{FAKE.company()} Group"
        c_code = random.choice(customer_country_codes)
        rev = round(random.uniform(5000000.0, 85000000.0), 2)
        segment = random.choice(segments)
        customers.append(
            Customer(
                id=c_id,
                name=name,
                country_code=c_code,
                annual_revenue_usd=rev,
                segment=segment,
            )
        )
    return customers


def generate_produces_and_alternatives(
    suppliers: list[Supplier],
    components: list[Component],
    countries: list[Country],
) -> tuple[list[SupplierProducesComponent], list[SupplierAlternativeFor]]:
    """Map suppliers to components and establish ALTERNATIVE_FOR relationships."""
    country_risk_map = {c.code: c.risk_index for c in countries}
    produces: list[SupplierProducesComponent] = []
    alternatives: list[SupplierAlternativeFor] = []

    # Map tier 1 suppliers sorted by higher country risk for sole-sourced items
    tier1_suppliers = [s for s in suppliers if s.tier == 1]
    tier2_suppliers = [s for s in suppliers if s.tier == 2]
    tier3_suppliers = [s for s in suppliers if s.tier == 3]

    high_risk_tier1 = sorted(
        tier1_suppliers,
        key=lambda s: country_risk_map.get(s.country_code, 0.0),
        reverse=True,
    )

    component_suppliers_map: dict[str, list[str]] = {c.id: [] for c in components}

    # Assign suppliers to each component
    for idx, c in enumerate(components):
        if c.is_sole_sourced:
            # Preferentially assign to tier 1 supplier in high-risk country
            chosen_supplier = high_risk_tier1[idx % len(high_risk_tier1)]
            produces.append(
                SupplierProducesComponent(
                    supplier_id=chosen_supplier.id,
                    component_id=c.id,
                    annual_volume=random.randint(50000, 1000000),
                    is_primary=True,
                )
            )
            component_suppliers_map[c.id].append(chosen_supplier.id)
        else:
            # Multi-sourced: 2 or 3 suppliers
            num_producers = random.choice([2, 3])
            candidate_pool = tier1_suppliers + tier2_suppliers
            chosen = random.sample(candidate_pool, num_producers)
            for p_idx, s in enumerate(chosen):
                is_prim = p_idx == 0
                produces.append(
                    SupplierProducesComponent(
                        supplier_id=s.id,
                        component_id=c.id,
                        annual_volume=random.randint(25000, 600000),
                        is_primary=is_prim,
                    )
                )
                component_suppliers_map[c.id].append(s.id)

    # Distribute tier 3 suppliers for raw materials and subcomponents
    for s3 in tier3_suppliers:
        sub_components = random.sample(components, random.randint(2, 4))
        for c in sub_components:
            if s3.id not in component_suppliers_map[c.id]:
                produces.append(
                    SupplierProducesComponent(
                        supplier_id=s3.id,
                        component_id=c.id,
                        annual_volume=random.randint(10000, 200000),
                        is_primary=False,
                    )
                )
                component_suppliers_map[c.id].append(s3.id)

    # Generate ~25 ALTERNATIVE_FOR edges where components have >1 supplier
    qual_statuses = ["Qualified", "Preferred Alternative", "Backup Qualified", "Audit Pending"]
    alt_count = 0
    for c in components:
        if len(component_suppliers_map[c.id]) >= 2:
            s_primary = component_suppliers_map[c.id][0]
            for s_alt in component_suppliers_map[c.id][1:]:
                alternatives.append(
                    SupplierAlternativeFor(
                        supplier_id=s_primary,
                        alternative_supplier_id=s_alt,
                        component_id=c.id,
                        qualification_status=random.choice(qual_statuses),
                    )
                )
                alt_count += 1
                if alt_count >= 25:
                    break
        if alt_count >= 25:
            break

    return produces, alternatives


def generate_bom(
    components: list[Component], products: list[Product]
) -> list[ComponentPartOfProduct]:
    """Generate Bill of Materials (BOM) linking components to products."""
    bom: list[ComponentPartOfProduct] = []

    # Group components by category
    category_map: dict[str, list[Component]] = {}
    for c in components:
        category_map.setdefault(c.category, []).append(c)

    # Each product needs 2-3 components from each category (12-18 components per product)
    for p in products:
        for _cat_name, cat_comps in category_map.items():
            num_to_pick = random.randint(2, 3)
            selected = random.sample(cat_comps, min(num_to_pick, len(cat_comps)))
            for c in selected:
                bom.append(
                    ComponentPartOfProduct(
                        component_id=c.id,
                        product_id=p.id,
                        quantity=random.choice([1, 1, 2, 4]),
                        is_critical=c.is_sole_sourced or (random.random() < 0.4),
                    )
                )
    return bom


def generate_ships_via(suppliers: list[Supplier], ports: list[Port]) -> list[SupplierShipsViaPort]:
    """Assign 1 to 2 shipping ports to each supplier based on proximity or trade route."""
    ships_via: list[SupplierShipsViaPort] = []
    port_by_country: dict[str, list[Port]] = {}
    for p in ports:
        port_by_country.setdefault(p.country_code, []).append(p)

    for s in suppliers:
        # If port exists in supplier's country, pick it as primary
        local_ports = port_by_country.get(s.country_code, [])
        primary_port = random.choice(local_ports) if local_ports else random.choice(ports)

        transit_days = random.randint(3, 28)
        ships_via.append(
            SupplierShipsViaPort(
                supplier_id=s.id,
                port_id=primary_port.id,
                primary=True,
                avg_transit_days=transit_days,
            )
        )

        # 40% of suppliers also have a secondary port
        if random.random() < 0.40:
            secondary_port = random.choice([p for p in ports if p.id != primary_port.id])
            ships_via.append(
                SupplierShipsViaPort(
                    supplier_id=s.id,
                    port_id=secondary_port.id,
                    primary=False,
                    avg_transit_days=transit_days + random.randint(2, 10),
                )
            )

    return ships_via


def generate_shipments(
    facilities: list[Facility], customers: list[Customer]
) -> list[FacilityShipsToCustomer]:
    """Generate 200 shipment fulfillment records linking facilities to customers."""
    shipments: list[FacilityShipsToCustomer] = []
    for _ in range(200):
        f = random.choice(facilities)
        c = random.choice(customers)
        vol = random.randint(500, 50000)
        shipments.append(
            FacilityShipsToCustomer(
                facility_id=f.id,
                customer_id=c.id,
                annual_volume_units=vol,
            )
        )
    return shipments


def write_csv_file(path: Path, rows: list[dict[str, str | int | float | bool]]) -> None:
    """Write list of row dictionaries to destination CSV path."""
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with open(path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_generation(data_dir: Path) -> None:
    """Run full synthetic generation pipeline and write output CSVs."""
    raw_dir = data_dir / "raw" / "synthetic"
    ref_port_csv = data_dir / "reference" / "ports_unlocode.csv"

    print("Generating countries...")
    countries = get_country_definitions()
    write_csv_file(raw_dir / "countries.csv", [c.model_dump() for c in countries])

    print("Loading ports...")
    ports = load_reference_ports(ref_port_csv)
    write_csv_file(raw_dir / "ports.csv", [p.model_dump() for p in ports])

    print("Generating suppliers...")
    suppliers = generate_suppliers(countries)
    write_csv_file(raw_dir / "suppliers.csv", [s.model_dump() for s in suppliers])

    print("Generating facilities and operations...")
    facilities, operates = generate_facilities(suppliers)
    write_csv_file(raw_dir / "facilities.csv", [f.model_dump() for f in facilities])
    write_csv_file(raw_dir / "operates.csv", [o.model_dump() for o in operates])

    print("Generating components...")
    components = generate_components()
    write_csv_file(raw_dir / "components.csv", [c.model_dump() for c in components])

    print("Generating products...")
    products = generate_products()
    write_csv_file(raw_dir / "products.csv", [p.model_dump() for p in products])

    print("Generating customers...")
    customers = generate_customers(countries)
    write_csv_file(raw_dir / "customers.csv", [c.model_dump() for c in customers])

    print("Generating produces & alternatives...")
    produces, alternatives = generate_produces_and_alternatives(suppliers, components, countries)
    write_csv_file(raw_dir / "produces.csv", [p.model_dump() for p in produces])
    write_csv_file(raw_dir / "alternative_suppliers.csv", [a.model_dump() for a in alternatives])

    print("Generating Bill of Materials (BOM)...")
    bom = generate_bom(components, products)
    write_csv_file(raw_dir / "bom.csv", [b.model_dump() for b in bom])

    print("Generating shipping routes (SHIPS_VIA)...")
    ships_via = generate_ships_via(suppliers, ports)
    write_csv_file(raw_dir / "ships_via.csv", [s.model_dump() for s in ships_via])

    print("Generating customer fulfillment shipments (SHIPS_TO)...")
    shipments = generate_shipments(facilities, customers)
    write_csv_file(raw_dir / "shipments.csv", [s.model_dump() for s in shipments])

    sole_count = sum(1 for c in components if c.is_sole_sourced)
    print(
        f"Synthetic data generation complete in {raw_dir}:\n"
        f"  - Countries: {len(countries)}\n"
        f"  - Ports: {len(ports)}\n"
        f"  - Suppliers: {len(suppliers)}\n"
        f"  - Facilities: {len(facilities)}\n"
        f"  - Components: {len(components)} ({sole_count} sole-sourced)\n"
        f"  - Products: {len(products)}\n"
        f"  - Customers: {len(customers)}\n"
        f"  - Produces edges: {len(produces)}\n"
        f"  - BOM edges: {len(bom)}\n"
        f"  - Ships via edges: {len(ships_via)}\n"
        f"  - Alternatives edges: {len(alternatives)}\n"
        f"  - Shipments edges: {len(shipments)}"
    )


if __name__ == "__main__":
    run_generation(Path("data"))
