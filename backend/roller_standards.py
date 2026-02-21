# IS-9295:2024 - Standard Pipe Diameters (mm)
PIPE_DIAMETERS = [63.5, 76.1, 88.9, 101.6, 108.0, 114.3, 127.0, 139.7, 152.4, 159.0, 165.0, 219.1]

# Shaft Diameters (mm)
SHAFT_DIAMETERS = [20, 25, 30, 35, 40, 45, 50]

# Bearing Selection based on Shaft Diameter
BEARING_OPTIONS = {
    20: ["6204", "6304"],
    25: ["6205", "6305"],
    30: ["6206", "6306"],
    35: ["6207", "6307"],
    40: ["6208", "6308"],
    45: ["6209", "6309"],
    50: ["6210", "6310"]
}

# Bearing Outside Diameters (mm) for housing selection
BEARING_OD = {
    "6204": 47, "6304": 52,
    "6205": 52, "6305": 62,
    "6206": 62, "6306": 72,
    "6207": 72, "6307": 80,
    "6208": 80, "6308": 90,
    "6209": 85, "6309": 100,
    "6210": 90, "6310": 110
}

# Housing Selection: pipe_dia -> [(housing_dia, [bearing_bores])]
HOUSING_OPTIONS = {
    63.5: [(56, [47])],
    76.1: [(72, [47, 52])],
    88.9: [(84, [47, 52, 62])],
    101.6: [(96, [47, 52, 62, 72])],
    108.0: [(102, [47, 52, 62, 72])],
    114.3: [(108, [47, 52, 62, 72])],
    127.0: [(121, [47, 52, 62, 72, 80])],
    139.7: [(133, [52, 62, 72, 80, 90])],
    152.4: [(146, [52, 62, 72, 80, 90])],
    159.0: [(153, [62, 72, 80, 90, 100])],
    165.0: [(159, [62, 72, 80, 90, 100])],
    219.1: [(213, [72, 80, 90, 100, 110])]
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

# Raw Material Costs (INR per unit)
RAW_MATERIAL_COSTS = {
    # Pipe costs per kg (varies by diameter)
    "pipe_cost_per_kg": {
        63.5: 55,
        76.1: 55,
        88.9: 52,
        101.6: 52,
        108.0: 50,
        114.3: 50,
        127.0: 48,
        139.7: 48,
        152.4: 46,
        159.0: 46,
        165.0: 45,
        219.1: 45
    },
    # Pipe weight per meter (kg/m) - approximate
    "pipe_weight_per_meter": {
        63.5: 4.5,
        76.1: 5.8,
        88.9: 7.2,
        101.6: 8.5,
        108.0: 9.1,
        114.3: 9.8,
        127.0: 11.5,
        139.7: 13.2,
        152.4: 15.0,
        159.0: 15.8,
        165.0: 16.5,
        219.1: 22.0
    },
    # Shaft cost per kg
    "shaft_cost_per_kg": 75,
    # Shaft weight per meter (kg/m) based on diameter
    "shaft_weight_per_meter": {
        20: 2.47,
        25: 3.85,
        30: 5.55,
        35: 7.55,
        40: 9.87,
        45: 12.48,
        50: 15.41
    },
    # Bearing costs (INR per piece)
    "bearing_costs": {
        "6204": 120, "6304": 180,
        "6205": 140, "6305": 220,
        "6206": 170, "6306": 280,
        "6207": 210, "6307": 340,
        "6208": 260, "6308": 420,
        "6209": 310, "6309": 500,
        "6210": 370, "6310": 600
    },
    # Housing costs (INR per piece) - varies by size
    "housing_cost_base": 150,
    "housing_cost_multiplier": {
        56: 1.0,
        72: 1.1,
        84: 1.2,
        96: 1.3,
        102: 1.4,
        108: 1.5,
        121: 1.7,
        133: 1.9,
        146: 2.1,
        153: 2.2,
        159: 2.3,
        213: 3.0
    },
    # Seal set costs (INR per set of 2)
    "seal_costs": {
        20: 80,
        25: 90,
        30: 100,
        35: 110,
        40: 120,
        45: 130,
        50: 140
    }
}

# Cost Calculation Constants
LAYOUT_MARKUP = 0.32  # 32% layout/manufacturing cost
PROFIT_MARKUP = 0.60  # 60% profit margin

def calculate_shaft_length(pipe_length_mm):
    """Calculate shaft length: pipe length + 70mm (35mm on each side)"""
    return pipe_length_mm + 70

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

def calculate_raw_material_cost(pipe_dia, pipe_length_mm, shaft_dia, bearing_number):
    """Calculate total raw material cost for a roller"""
    costs = RAW_MATERIAL_COSTS
    
    # Pipe cost
    pipe_length_m = pipe_length_mm / 1000
    pipe_weight = costs["pipe_weight_per_meter"][pipe_dia] * pipe_length_m
    pipe_cost = pipe_weight * costs["pipe_cost_per_kg"][pipe_dia]
    
    # Shaft cost (for 2 shafts)
    shaft_length_mm = calculate_shaft_length(pipe_length_mm)
    shaft_length_m = shaft_length_mm / 1000
    shaft_weight = costs["shaft_weight_per_meter"][shaft_dia] * shaft_length_m * 2  # 2 sides
    shaft_cost = shaft_weight * costs["shaft_cost_per_kg"]
    
    # Bearing cost (2 bearings)
    bearing_cost = costs["bearing_costs"][bearing_number] * 2
    
    # Housing cost (2 housings)
    housing = get_housing_for_pipe_and_bearing(pipe_dia, bearing_number)
    if housing:
        housing_dia = int(housing.split('/')[0])
        housing_multiplier = costs["housing_cost_multiplier"].get(housing_dia, 1.5)
        housing_cost = costs["housing_cost_base"] * housing_multiplier * 2
    else:
        housing_cost = costs["housing_cost_base"] * 2
    
    # Seal set cost (2 seal sets)
    seal_cost = costs["seal_costs"][shaft_dia] * 2
    
    total_raw_material = pipe_cost + shaft_cost + bearing_cost + housing_cost + seal_cost
    
    return {
        "pipe_cost": round(pipe_cost, 2),
        "shaft_cost": round(shaft_cost, 2),
        "bearing_cost": round(bearing_cost, 2),
        "housing_cost": round(housing_cost, 2),
        "seal_cost": round(seal_cost, 2),
        "total_raw_material": round(total_raw_material, 2)
    }

def calculate_final_price(raw_material_cost):
    """Calculate final price: Raw Material × 1.32 × 1.60"""
    layout_cost = raw_material_cost * LAYOUT_MARKUP
    subtotal_with_layout = raw_material_cost + layout_cost
    profit = subtotal_with_layout * PROFIT_MARKUP
    final_price = subtotal_with_layout + profit
    
    # Simpler: final_price = raw_material_cost * 1.32 * 1.60 = raw_material_cost * 2.112
    
    return {
        "raw_material_cost": round(raw_material_cost, 2),
        "layout_cost": round(layout_cost, 2),
        "profit": round(profit, 2),
        "final_price": round(final_price, 2)
    }
