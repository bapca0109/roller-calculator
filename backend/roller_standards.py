# IS-9295:2024 - Standard Pipe Diameters (mm) - UPDATED
PIPE_DIAMETERS = [63.5, 76.1, 88.9, 114.3, 127.0, 139.7, 152.4, 159.0, 165.0]

# Shaft Diameters (mm)
SHAFT_DIAMETERS = [20, 25, 30, 35, 40, 45, 50]

# Bearing Selection based on Shaft Diameter - UPDATED with 420204 series
BEARING_OPTIONS = {
    20: ["6204", "6304", "420204"],
    25: ["6205", "6305", "420205"],
    30: ["6206", "6306", "420206"],
    35: ["6207", "6307"],
    40: ["6208", "6308"],
    45: ["6209", "6309"],
    50: ["6210", "6310"]
}

# Bearing Outside Diameters (mm) for housing selection - UPDATED
BEARING_OD = {
    "6204": 47, "6304": 52, "420204": 47,
    "6205": 52, "6305": 62, "420205": 52,
    "6206": 62, "6306": 72, "420206": 62,
    "6207": 72, "6307": 80,
    "6208": 80, "6308": 90,
    "6209": 85, "6309": 100,
    "6210": 90, "6310": 110
}

# Bearing Costs by Make (INR per piece) - ACTUAL PRICES
BEARING_COSTS = {
    # 20mm shaft bearings
    "6204": {"china": 20, "skf": 70, "fag": 70, "timken": 61},
    "6304": {"china": 30, "skf": 97, "fag": 89, "timken": 85},
    "420204": {"fag": 54},  # FAG only
    
    # 25mm shaft bearings
    "6205": {"china": 26, "skf": 84, "fag": 70, "timken": 70},  # Timken TBD, using FAG as placeholder
    "6305": {"skf": 178, "fag": 124, "timken": 124},  # China NA, Timken TBD
    "420205": {"fag": 60},  # FAG only
    
    # 30mm shaft bearings
    "6206": {"china": 40, "skf": 135, "fag": 105, "timken": 105},  # Timken TBD, using FAG as placeholder
    "6306": {"skf": 216, "fag": 177, "timken": 177},  # China NA, Timken TBD
    "420206": {"fag": 83},  # FAG only
    
    # 35mm shaft bearings
    "6207": {"skf": 205, "fag": 190, "timken": 190},  # China NA, Timken TBD
    "6307": {"skf": 342, "fag": 225, "timken": 216},
    
    # 40mm shaft bearings
    "6208": {"skf": 264, "fag": 210, "timken": 210},  # China NA, Timken TBD
    "6308": {"skf": 320, "fag": 275, "timken": 275},  # China NA, Timken TBD
    
    # 45mm shaft bearings
    "6209": {"skf": 320, "fag": 270, "timken": 270},  # China & Timken TBD
    "6309": {"skf": 520, "fag": 400, "timken": 400},  # China NA, FAG & Timken TBD
    
    # 50mm shaft bearings
    "6210": {"skf": 515, "fag": 400, "timken": 400},  # China, FAG & Timken TBD
    "6310": {"skf": 1046, "fag": 800, "timken": 800},  # China, FAG & Timken TBD
}

# Housing Selection: pipe_dia -> [(housing_dia, [bearing_bores])] - UPDATED
HOUSING_OPTIONS = {
    63.5: [(56, [47])],
    76.1: [(72, [47, 52])],
    88.9: [(84, [47, 52, 62])],
    114.3: [(108, [47, 52, 62, 72])],
    127.0: [(121, [47, 52, 62, 72, 80])],
    139.7: [(133, [52, 62, 72, 80, 90])],
    152.4: [(146, [52, 62, 72, 80, 90])],
    159.0: [(153, [62, 72, 80, 90, 100])],
    165.0: [(159, [52, 62, 72, 80, 90, 100])]
}

# Housing Costs (INR per piece) - ACTUAL PRICES
HOUSING_COSTS = {
    "56/47": 21,
    "72/47": 22, "72/52": 24,
    "84/47": 23, "84/52": 25, "84/62": 28,
    "108/47": 33, "108/52": 35, "108/62": 45, "108/72": 50,
    "121/47": 42, "121/52": 45, "121/62": 50, "121/72": 57, "121/80": 68,
    "133/52": 50, "133/62": 55, "133/72": 60, "133/80": 65, "133/90": 70,
    "146/52": 57, "146/62": 60, "146/72": 65, "146/80": 70, "146/90": 80,
    "153/62": 60, "153/72": 65, "153/80": 70, "153/90": 80, "153/100": 90,
    "159/52": 65, "159/62": 70, "159/72": 75, "159/80": 80, "159/90": 100, "159/100": 120
}

# IS-8598:2019 - Standard Roller Lengths by Belt Width (mm)
ROLLER_LENGTHS = {
    400: [690, 755],
    500: [740, 790],
    650: [940, 1000],
    800: [1090],
    1000: [1190, 1240],
    1200: [1390, 1440],
    1400: [1590, 1640],
    1600: [1790, 1840],
    1800: [1990, 2040],
    2000: [2190, 2240]
}

# Pipe Weight per meter (kg/m) - IS-1239 Light/Medium/Heavy Classes
# Type A = Light, Type B = Medium, Type C = Heavy
PIPE_WEIGHT_PER_METER = {
    63.5: {  # 60mm OD per IS-1239
        "A": 4.11,   # Light: 2.90mm thickness
        "B": 5.10,   # Medium: 3.65mm thickness
        "C": 6.17    # Heavy: 4.47mm thickness
    },
    76.1: {  # 76mm OD per IS-1239
        "A": 5.84,   # Light: 3.25mm thickness
        "B": 6.61,   # Medium: 3.65mm thickness
        "C": 7.90    # Heavy: 4.47mm thickness
    },
    88.9: {  # 88mm OD per IS-1239
        "A": 6.81,   # Light: 3.25mm thickness
        "B": 8.47,   # Medium: 4.05mm thickness
        "C": 10.10   # Heavy: 4.85mm thickness
    },
    114.3: {  # 114mm OD per IS-1239
        "A": 9.89,   # Light: 3.65mm thickness
        "B": 12.10,  # Medium: 4.50mm thickness
        "C": 14.40   # Heavy: 5.40mm thickness
    },
    127.0: {  # 127mm OD
        "A": 12.13,  # Light: 4.0mm thickness
        "B": 15.0,   # Medium: 4.85mm thickness
        "C": 16.5    # Heavy: 5.40mm thickness
    },
    139.7: {  # 139mm OD
        "A": 13.38,  # Light: 4.0mm thickness
        "B": 16.5,   # Medium: calculated
        "C": 18.5    # Heavy: 5.40mm thickness
    },
    152.4: {  # 152mm OD
        "A": 15.0,   # Light: calculated
        "B": 18.0,   # Medium: 4.85mm thickness
        "C": 20.0    # Heavy: 5.40mm thickness
    },
    159.0: {  # 159mm OD
        "A": 15.8,   # Light: calculated
        "B": 19.0,   # Medium: calculated
        "C": 21.0    # Heavy: calculated
    },
    165.0: {  # 165mm OD
        "A": 16.5,   # Light: calculated
        "B": 20.0,   # Medium: calculated
        "C": 21.5    # Heavy: 5.40mm thickness
    }
}

# Shaft Weight per meter (kg/m) based on diameter
SHAFT_WEIGHT_PER_METER = {
    20: 2.47,
    25: 3.85,
    30: 5.55,
    35: 7.55,
    40: 9.87,
    45: 12.48,
    50: 15.41
}

# Raw Material Costs - ACTUAL PRICES
PIPE_COST_PER_KG = 67  # INR per kg - UNIFORM for all diameters
SHAFT_COST_PER_KG = 62  # INR per kg

# Seal Set Costs (INR per set) - BEARING-SPECIFIC - ACTUAL PRICES
SEAL_COSTS = {
    # 20mm shaft bearings
    "6204": 13,
    "6304": 18,
    "420204": 13,  # Same as 6204
    
    # 25mm shaft bearings
    "6205": 18,
    "6305": 25,
    "420205": 18,  # Same as 6205
    
    # 30mm shaft bearings
    "6206": 25,
    "6306": 40,
    "420206": 25,  # Same as 6206
    
    # 35mm shaft bearings
    "6207": 40,
    "6307": 50,
    
    # 40mm shaft bearings
    "6208": 50,
    "6308": 90,
    
    # 45mm shaft bearings
    "6209": 90,
    "6309": 120,
    
    # 50mm shaft bearings
    "6210": 120,
    "6310": 140
}

# Circlip Costs (INR per piece) - Based on Shaft Diameter - ACTUAL PRICES
# 4 pieces per roller
CIRCLIP_COSTS = {
    20: 1.0,
    25: 1.5,
    30: 2.0,
    35: 2.5,
    40: 3.0,
    45: 10.0,
    50: 12.0
}

# Impact Roller - Rubber Lagging Options
# Format: pipe_dia -> [rubber_dia_options]
RUBBER_LAGGING_OPTIONS = {
    60: [90, 114],
    76: [114, 127, 140],
    89: [127, 140, 152],
    114: [139, 152, 165, 190],
    127: [165, 190],
    139: [165, 190],
    152: [190]
}

# Rubber Ring Costs (INR per ring, 35mm thick) - ACTUAL PRICES
# Format: "pipe/rubber" -> cost_per_ring
RUBBER_RING_COSTS = {
    "60/90": 16,
    "60/114": 20,
    "76/114": 20,
    "76/127": 22,
    "76/140": 30,
    "89/127": 32,
    "89/140": 36,
    "89/152": 42,
    "114/139": 35,
    "114/152": 40,
    "114/165": 47,
    "114/190": 72,
    "127/165": 55,
    "127/190": 68,
    "139/165": 54,
    "139/190": 63,
    "152/190": 65
}

RUBBER_RING_THICKNESS = 35  # mm

# Locking Ring Costs (INR per roller) - For Impact Rollers
# Added to raw material before applying 2.112× formula
LOCKING_RING_COSTS = {
    60: 18,
    76: 20,
    89: 22,
    114: 26,
    127: 28,
    139: 30,
    152: 32,
    159: 34,
    165: 38
}

# Product Code Mappings
ROLLER_TYPE_CODES = {
    "carrying": "CR",
    "return": "RR",
    "impact": "IR"
}

BEARING_MAKE_CODES = {
    "china": "C",
    "skf": "S",
    "fag": "F",
    "timken": "T"
}

BEARING_SERIES_MAP = {
    "6204": "62", "6205": "62", "6206": "62", "6207": "62", "6208": "62", "6209": "62", "6210": "62",
    "6304": "63", "6305": "63", "6306": "63", "6307": "63", "6308": "63", "6309": "63", "6310": "63",
    "420204": "42", "420205": "42", "420206": "42"
}

def generate_product_code(roller_type, shaft_dia, pipe_dia, pipe_length, pipe_type, bearing_number, bearing_make, rubber_dia=None):
    """
    Generate product code/SKU for conveyor rollers
    
    Format for Standard Rollers: [TYPE][SHAFT] [PIPE][LENGTH][THICKNESS] [SERIES][MAKE]
    Example: CR20 89200A 62S
    
    Format for Impact Rollers: [TYPE][SHAFT] [PIPE/RUBBER][LENGTH][THICKNESS] [SERIES][MAKE]
    Example: IR20 89/140 1190A 62S
    """
    # Roller type
    type_code = ROLLER_TYPE_CODES.get(roller_type.lower(), "CR")
    
    # Shaft diameter
    shaft_code = str(int(shaft_dia))
    
    # Pipe diameter (with rubber for impact rollers)
    if rubber_dia:
        pipe_code = f"{int(pipe_dia)}/{int(rubber_dia)}"
    else:
        pipe_code = str(int(pipe_dia))
    
    # Length in mm
    length_code = str(int(pipe_length))
    
    # Pipe thickness type
    thickness_code = pipe_type.upper()
    
    # Bearing series
    series_code = BEARING_SERIES_MAP.get(bearing_number, "62")
    
    # Bearing make
    make_code = BEARING_MAKE_CODES.get(bearing_make.lower(), "C")
    
    # Combine all parts
    product_code = f"{type_code}{shaft_code} {pipe_code}{length_code}{thickness_code} {series_code}{make_code}"
    
    return product_code

# Cost Calculation Constants - AS PER YOUR FORMULA
LAYOUT_MARKUP = 0.32  # 32% layout/manufacturing cost
PROFIT_MARKUP = 0.60  # 60% profit margin
# Final multiplier: 1.32 × 1.60 = 2.112

# Packing Charges (Applied AFTER final product price calculation)
PACKING_CHARGES = {
    "pallet": 0.04,      # 4% for pallet packing
    "wooden_box": 0.08,  # 8% for wooden box packing
    "none": 0.0          # No packing
}

def calculate_shaft_length(pipe_length_mm):
    """Calculate shaft length: pipe length + 70mm (35mm on each side)"""
    return pipe_length_mm + 70

def calculate_rubber_cost(pipe_dia, rubber_dia, pipe_length_mm):
    """
    Calculate rubber lagging cost for impact rollers.
    Number of rings = pipe_length / 35mm
    Total cost = number of rings × cost per ring
    """
    rubber_key = f"{int(pipe_dia)}/{int(rubber_dia)}"
    
    if rubber_key not in RUBBER_RING_COSTS:
        return 0  # No rubber for this combination
    
    number_of_rings = pipe_length_mm / RUBBER_RING_THICKNESS
    cost_per_ring = RUBBER_RING_COSTS[rubber_key]
    total_rubber_cost = number_of_rings * cost_per_ring
    
    return round(total_rubber_cost, 2)

def get_housing_for_pipe_and_bearing(pipe_dia, bearing_number):
    """Get compatible housing based on pipe diameter and bearing"""
    bearing_od = BEARING_OD.get(bearing_number)
    if not bearing_od:
        return None
    
    housing_options = HOUSING_OPTIONS.get(pipe_dia, [])
    for housing_dia, bearing_bores in housing_options:
        if bearing_od in bearing_bores:
            return f"{housing_dia}/{bearing_od}"
    return None

def get_bearing_cost(bearing_number, make="china"):
    """Get bearing cost by make. Defaults to cheapest available if make not available."""
    bearing_prices = BEARING_COSTS.get(bearing_number, {})
    
    # If requested make is available, return it
    if make.lower() in bearing_prices:
        return bearing_prices[make.lower()]
    
    # Otherwise return the cheapest available option
    if bearing_prices:
        return min(bearing_prices.values())
    
    return 0  # Shouldn't happen if bearing exists

def calculate_raw_material_cost(pipe_dia, pipe_length_mm, shaft_dia, bearing_number, bearing_make="china", rubber_dia=None, pipe_type="B"):
    """
    Calculate total raw material cost for a roller (optionally with rubber lagging for impact rollers)
    pipe_type: "A" (Light), "B" (Medium), "C" (Heavy) - defaults to "B" (Medium)
    """
    
    # Pipe cost - now depends on pipe type (A/B/C)
    pipe_length_m = pipe_length_mm / 1000
    pipe_weight_per_m = PIPE_WEIGHT_PER_METER[pipe_dia].get(pipe_type, PIPE_WEIGHT_PER_METER[pipe_dia]["B"])
    pipe_weight = pipe_weight_per_m * pipe_length_m
    pipe_cost = pipe_weight * PIPE_COST_PER_KG
    
    # Shaft cost (for 2 shafts)
    shaft_length_mm = calculate_shaft_length(pipe_length_mm)
    shaft_length_m = shaft_length_mm / 1000
    shaft_weight = SHAFT_WEIGHT_PER_METER[shaft_dia] * shaft_length_m * 2  # 2 sides
    shaft_cost = shaft_weight * SHAFT_COST_PER_KG
    
    # Bearing cost (2 bearings)
    bearing_unit_cost = get_bearing_cost(bearing_number, bearing_make)
    bearing_cost = bearing_unit_cost * 2
    
    # Housing cost (2 housings)
    housing = get_housing_for_pipe_and_bearing(pipe_dia, bearing_number)
    if housing and housing in HOUSING_COSTS:
        housing_cost = HOUSING_COSTS[housing] * 2
    else:
        housing_cost = 0  # Default if housing not found
    
    # Seal set cost (2 seal sets)
    seal_cost = SEAL_COSTS.get(bearing_number, 0) * 2
    
    # Circlip cost (4 circlips per roller)
    circlip_cost = CIRCLIP_COSTS[shaft_dia] * 4
    
    # Rubber lagging cost (optional, for impact rollers)
    rubber_cost = 0
    locking_ring_cost = 0
    if rubber_dia:
        rubber_cost = calculate_rubber_cost(pipe_dia, rubber_dia, pipe_length_mm)
        # Add locking ring cost for impact rollers
        locking_ring_cost = LOCKING_RING_COSTS.get(int(pipe_dia), 0)
    
    total_raw_material = pipe_cost + shaft_cost + bearing_cost + housing_cost + seal_cost + circlip_cost + rubber_cost + locking_ring_cost
    
    result = {
        "pipe_cost": round(pipe_cost, 2),
        "shaft_cost": round(shaft_cost, 2),
        "bearing_cost": round(bearing_cost, 2),
        "housing_cost": round(housing_cost, 2),
        "seal_cost": round(seal_cost, 2),
        "circlip_cost": round(circlip_cost, 2),
        "total_raw_material": round(total_raw_material, 2)
    }
    
    if rubber_dia:
        result["rubber_cost"] = round(rubber_cost, 2)
        result["locking_ring_cost"] = round(locking_ring_cost, 2)
        number_of_rings = pipe_length_mm / RUBBER_RING_THICKNESS
        result["rubber_rings"] = round(number_of_rings, 1)
    
    return result

def calculate_final_price(raw_material_cost):
    """
    Calculate final price using your formula:
    Total = Raw Material × 1.32 × 1.60 = Raw Material × 2.112
    
    Where:
    - 1.32 = Raw Material + 32% Layout cost
    - 1.60 = 60% Profit on (Raw Material + Layout)
    """
    layout_cost = raw_material_cost * LAYOUT_MARKUP
    subtotal_with_layout = raw_material_cost + layout_cost
    profit = subtotal_with_layout * PROFIT_MARKUP
    final_price = subtotal_with_layout + profit
    
    return {
        "raw_material_cost": round(raw_material_cost, 2),
        "layout_cost": round(layout_cost, 2),
        "subtotal_with_layout": round(subtotal_with_layout, 2),
        "profit": round(profit, 2),
        "final_price": round(final_price, 2),
        "multiplier": 2.112  # For reference
    }
