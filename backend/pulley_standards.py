"""
Pulley Standards and Calculation Logic
Belt Conveyor Pulley Price Calculator
"""
import math

# ============= PULLEY CONSTANTS =============

# Pulley Types
PULLEY_TYPES = ["Drive", "Tail", "Bend", "Snub", "Take-up"]

# Pipe Diameters (mm)
PIPE_DIAMETERS = [139, 152, 168, 193, 219, 245, 273, 323, 355, 406, 455, 508, 609, 630, 800, 1000]

# Pipe Wall Thicknesses (mm)
PIPE_THICKNESSES = [4.8, 5.4, 6.3, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26]

# Which thicknesses are available per pipe diameter
# Based on the actual Excel template data
PIPE_THICKNESS_MAP = {
    139: [4.8, 5.4],
    152: [4.8, 5.4],
    168: [4.8, 5.4],
    193: [5.4, 6.3],
    219: [6.3, 8, 10, 12],
    245: [6.3, 8, 10, 12],
    273: [6.3, 8, 10, 12],
    323: [6.3, 8, 10, 12, 14],
    355: [8, 10, 12, 14],
    406: [8, 10, 12, 14, 16, 18],
    455: [8, 10, 12, 14, 16, 18],
    508: [8, 10, 12, 14, 16, 18, 20],
    609: [8, 10, 12, 14, 16, 18, 20],
    630: [8, 10, 12, 14, 16, 18, 20, 22],
    800: [8, 10, 12, 14, 16, 18, 20, 22, 24],
    1000: [8, 10, 12, 14, 16, 18, 20, 22, 24, 26],
}

# Shaft Diameters (mm) — from user's pricing sheet
SHAFT_DIAMETERS = [53, 55, 63, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145, 150, 155, 160, 165, 170, 175, 180, 185, 190, 195, 200, 205, 210, 215, 220, 225, 230, 235, 240, 245, 250, 255, 260, 265, 270, 275, 280, 285, 290, 295, 300]

# Shaft Materials
SHAFT_MATERIALS = ["MS", "EN-8", "EN-9", "EN-19"]

# End Plate Thicknesses (mm) - 6 to 50 in steps of 2
END_PLATE_THICKNESSES = list(range(6, 52, 2))

# Hub Types
HUB_TYPES = ["no_hub", "with_hub", "kla"]

# Hub Dia options (mm) - for "With Hub" type — from user's pricing
HUB_DIAMETERS = [100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 210, 220, 230, 240, 250, 260, 270, 280, 290, 300, 310, 320, 330, 340, 350, 360, 370, 380, 390, 400, 410, 420, 430, 440, 450]

# KLA Shaft @ Hub options (mm) - 25 to 290 in steps of 5
KLA_SHAFT_HUB_OPTIONS = list(range(25, 295, 5))

# Rubber Lagging Types
RUBBER_LAGGING_TYPES = ["none", "plain", "diamond", "ceramic"]

# Rubber Lagging Thicknesses (mm)
RUBBER_PLAIN_THICKNESSES = [6, 8, 10, 12]
RUBBER_CERAMIC_THICKNESSES = [12, 16, 22]

# Steel density (kg/m³)
STEEL_DENSITY = 7850

# ============= PRICING FROM USER'S EXCEL TEMPLATE =============

# Pipe rates: { pipe_dia: { thickness: rate_per_kg } } — from pulley_pricing_template.xlsx
PIPE_RATES = {
    139: {4.8: 70.0, 5.4: 71.0},
    152: {4.8: 70.0, 5.4: 71.0},
    168: {4.8: 72.0, 5.4: 73.0},
    193: {5.4: 74.0, 6.3: 75.0},
    219: {6.3: 70.0, 8: 71.0, 10: 72.0, 12: 73.0},
    245: {6.3: 70.0, 8: 71.0, 10: 72.0, 12: 73.0},
    273: {6.3: 72.0, 8: 73.0, 10: 74.0, 12: 75.0},
    323: {6.3: 72.0, 8: 73.0, 10: 74.0, 12: 75.0, 14: 76.0},
    355: {8: 75.0, 10: 76.0, 12: 77.0, 14: 78.0},
    406: {8: 75.0, 10: 76.0, 12: 77.0, 14: 78.0, 16: 79.0, 18: 80.0},
    455: {8: 75.0, 10: 76.0, 12: 77.0, 14: 78.0, 16: 79.0, 18: 80.0},
    508: {8: 75.0, 10: 76.0, 12: 77.0, 14: 78.0, 16: 79.0, 18: 80.0, 20: 81.0},
    609: {8: 78.0, 10: 79.0, 12: 80.0, 14: 81.0, 16: 82.0, 18: 83.0, 20: 84.0},
    630: {8: 85.0, 10: 86.0, 12: 87.0, 14: 88.0, 16: 89.0, 18: 90.0, 20: 91.0, 22: 92.0},
    800: {8: 85.0, 10: 86.0, 12: 87.0, 14: 88.0, 16: 89.0, 18: 90.0, 20: 91.0, 22: 92.0, 24: 93.0},
    1000: {8: 90.0, 10: 91.0, 12: 92.0, 14: 93.0, 16: 94.0, 18: 95.0, 20: 96.0, 22: 97.0, 24: 98.0, 26: 99.0},
}

# Shaft rates: { shaft_dia: { material: rate_per_kg } } — from user's pricing sheet
SHAFT_RATES = {
    53: {"MS": 60.0, "EN-8": 62.0, "EN-9": 63.0, "EN-19": 83.0},
    55: {"MS": 60.2, "EN-8": 62.2, "EN-9": 63.2, "EN-19": 83.2},
    63: {"MS": 60.4, "EN-8": 62.4, "EN-9": 63.4, "EN-19": 83.4},
    70: {"MS": 60.6, "EN-8": 62.6, "EN-9": 63.6, "EN-19": 83.6},
    75: {"MS": 60.8, "EN-8": 62.8, "EN-9": 63.8, "EN-19": 83.8},
    80: {"MS": 61.0, "EN-8": 63.0, "EN-9": 64.0, "EN-19": 84.0},
    85: {"MS": 61.2, "EN-8": 63.2, "EN-9": 64.2, "EN-19": 84.2},
    90: {"MS": 61.4, "EN-8": 63.4, "EN-9": 64.4, "EN-19": 84.4},
    95: {"MS": 61.6, "EN-8": 63.6, "EN-9": 64.6, "EN-19": 84.6},
    100: {"MS": 61.8, "EN-8": 63.8, "EN-9": 64.8, "EN-19": 84.8},
    105: {"MS": 62.0, "EN-8": 64.0, "EN-9": 65.0, "EN-19": 85.0},
    110: {"MS": 62.2, "EN-8": 64.2, "EN-9": 65.2, "EN-19": 85.2},
    115: {"MS": 62.4, "EN-8": 64.4, "EN-9": 65.4, "EN-19": 85.4},
    120: {"MS": 62.6, "EN-8": 64.6, "EN-9": 65.6, "EN-19": 85.6},
    125: {"MS": 62.8, "EN-8": 64.8, "EN-9": 65.8, "EN-19": 85.8},
    130: {"MS": 63.0, "EN-8": 65.0, "EN-9": 66.0, "EN-19": 86.0},
    135: {"MS": 63.2, "EN-8": 65.2, "EN-9": 66.2, "EN-19": 86.2},
    140: {"MS": 63.4, "EN-8": 65.4, "EN-9": 66.4, "EN-19": 86.4},
    145: {"MS": 63.6, "EN-8": 65.6, "EN-9": 66.6, "EN-19": 86.6},
    150: {"MS": 63.8, "EN-8": 65.8, "EN-9": 66.8, "EN-19": 86.8},
    155: {"MS": 64.0, "EN-8": 66.0, "EN-9": 67.0, "EN-19": 87.0},
    160: {"MS": 64.2, "EN-8": 66.2, "EN-9": 67.2, "EN-19": 87.2},
    165: {"MS": 64.4, "EN-8": 66.4, "EN-9": 67.4, "EN-19": 87.4},
    170: {"MS": 64.6, "EN-8": 66.6, "EN-9": 67.6, "EN-19": 87.6},
    175: {"MS": 64.8, "EN-8": 66.8, "EN-9": 67.8, "EN-19": 87.8},
    180: {"MS": 65.0, "EN-8": 67.0, "EN-9": 68.0, "EN-19": 88.0},
    185: {"MS": 65.2, "EN-8": 67.2, "EN-9": 68.2, "EN-19": 88.2},
    190: {"MS": 65.4, "EN-8": 67.4, "EN-9": 68.4, "EN-19": 88.4},
    195: {"MS": 65.6, "EN-8": 67.6, "EN-9": 68.6, "EN-19": 88.6},
    200: {"MS": 65.8, "EN-8": 67.8, "EN-9": 68.8, "EN-19": 88.8},
    205: {"MS": 66.0, "EN-8": 68.0, "EN-9": 69.0, "EN-19": 89.0},
    210: {"MS": 66.2, "EN-8": 68.2, "EN-9": 69.2, "EN-19": 89.2},
    215: {"MS": 66.4, "EN-8": 68.4, "EN-9": 69.4, "EN-19": 89.4},
    220: {"MS": 66.6, "EN-8": 68.6, "EN-9": 69.6, "EN-19": 89.6},
    225: {"MS": 66.8, "EN-8": 68.8, "EN-9": 69.8, "EN-19": 89.8},
    230: {"MS": 67.0, "EN-8": 69.0, "EN-9": 70.0, "EN-19": 90.0},
    235: {"MS": 67.2, "EN-8": 69.2, "EN-9": 70.2, "EN-19": 90.2},
    240: {"MS": 67.4, "EN-8": 69.4, "EN-9": 70.4, "EN-19": 90.4},
    245: {"MS": 67.6, "EN-8": 69.6, "EN-9": 70.6, "EN-19": 90.6},
    250: {"MS": 67.8, "EN-8": 69.8, "EN-9": 70.8, "EN-19": 90.8},
    255: {"MS": 68.0, "EN-8": 70.0, "EN-9": 71.0, "EN-19": 91.0},
    260: {"MS": 68.2, "EN-8": 70.2, "EN-9": 71.2, "EN-19": 91.2},
    265: {"MS": 68.4, "EN-8": 70.4, "EN-9": 71.4, "EN-19": 91.4},
    270: {"MS": 68.6, "EN-8": 70.6, "EN-9": 71.6, "EN-19": 91.6},
    275: {"MS": 68.8, "EN-8": 70.8, "EN-9": 71.8, "EN-19": 91.8},
    280: {"MS": 69.0, "EN-8": 71.0, "EN-9": 72.0, "EN-19": 92.0},
    285: {"MS": 69.2, "EN-8": 71.2, "EN-9": 72.2, "EN-19": 92.2},
    290: {"MS": 69.4, "EN-8": 71.4, "EN-9": 72.4, "EN-19": 92.4},
    295: {"MS": 69.6, "EN-8": 71.6, "EN-9": 72.6, "EN-19": 92.6},
    300: {"MS": 69.8, "EN-8": 71.8, "EN-9": 72.8, "EN-19": 92.8},
}

# End Plate MS rate per kg — from user's pricing (varies by thickness)
END_PLATE_RATES = {
    6: 65.0, 8: 65.0, 10: 65.0,
    12: 67.0, 14: 67.0, 16: 67.0,
    18: 70.0, 20: 70.0, 22: 70.0,
    24: 72.0, 26: 72.0, 28: 72.0, 30: 72.0,
    32: 76.0, 34: 76.0, 36: 76.0, 38: 76.0, 40: 76.0, 42: 76.0, 44: 76.0, 46: 76.0, 48: 76.0, 50: 76.0,
}

# Hub MS rate per kg (for "With Hub") — from user's pricing, varies by hub dia
HUB_RATES = {
    100: 62.0, 110: 62.2, 120: 62.4, 130: 62.6, 140: 62.8,
    150: 63.0, 160: 63.2, 170: 63.4, 180: 63.6, 190: 63.8,
    200: 64.0, 210: 64.2, 220: 64.4, 230: 64.6, 240: 64.8,
    250: 65.0, 260: 65.2, 270: 65.4, 280: 65.6, 290: 65.8,
    300: 66.0, 310: 66.2, 320: 66.4, 330: 66.6, 340: 66.8,
    350: 67.0, 360: 67.2, 370: 67.4, 380: 67.6, 390: 67.8,
    400: 68.0, 410: 68.2, 420: 68.4, 430: 68.6, 440: 68.8,
    450: 69.0,
}

# KLA Pricing: { model: { min_shaft, max_shaft, price } }
# Mock KLA models
KLA_MODELS = {
    "KLA-25": {"min_shaft": 25, "max_shaft": 35, "price": 850},
    "KLA-35": {"min_shaft": 36, "max_shaft": 50, "price": 1200},
    "KLA-50": {"min_shaft": 51, "max_shaft": 70, "price": 1800},
    "KLA-70": {"min_shaft": 71, "max_shaft": 90, "price": 2500},
    "KLA-90": {"min_shaft": 91, "max_shaft": 120, "price": 3500},
    "KLA-120": {"min_shaft": 121, "max_shaft": 150, "price": 4800},
    "KLA-150": {"min_shaft": 151, "max_shaft": 180, "price": 6500},
    "KLA-180": {"min_shaft": 181, "max_shaft": 220, "price": 8500},
    "KLA-220": {"min_shaft": 221, "max_shaft": 260, "price": 11000},
    "KLA-260": {"min_shaft": 261, "max_shaft": 290, "price": 14000},
}

# Rubber Lagging rates (₹/sqm)
RUBBER_PLAIN_RATES = {
    6: 3300,
    10: 5800,
    12: 6400,
}

RUBBER_CERAMIC_RATES = {
    12: 20000,
    16: 24000,
    22: 30000,
}

# ============= CALCULATION FUNCTIONS =============


def get_available_thicknesses(pipe_dia):
    """Get available wall thicknesses for a pipe diameter"""
    return PIPE_THICKNESS_MAP.get(pipe_dia, [])


def get_kla_model(shaft_dia_at_hub):
    """Get KLA model and price based on shaft diameter at hub"""
    for model_name, model_data in KLA_MODELS.items():
        if model_data["min_shaft"] <= shaft_dia_at_hub <= model_data["max_shaft"]:
            return {
                "model": model_name,
                "price": model_data["price"],
                "min_shaft": model_data["min_shaft"],
                "max_shaft": model_data["max_shaft"],
            }
    return None


def calculate_pipe_weight(pipe_dia, wall_thickness, face_length):
    """
    Calculate pipe weight in kg
    Weight = π/4 × (OD² - ID²) × length × density
    All dimensions in mm, convert to meters for density calc
    Note: Always use thickness + 2mm for weight calculation
    """
    od = pipe_dia  # mm
    effective_thickness = wall_thickness + 2  # Always add 2mm for weight calc
    id_val = pipe_dia - 2 * effective_thickness  # mm
    length = face_length  # mm

    # Volume in mm³
    volume_mm3 = (math.pi / 4) * (od**2 - id_val**2) * length
    # Convert to m³ (1m = 1000mm, so 1m³ = 1e9 mm³)
    volume_m3 = volume_mm3 / 1e9
    # Weight in kg
    weight = volume_m3 * STEEL_DENSITY
    return round(weight, 3)


def calculate_shaft_weight(shaft_dia, shaft_length):
    """
    Calculate shaft weight in kg
    Weight = π/4 × dia² × length × density
    """
    volume_mm3 = (math.pi / 4) * (shaft_dia**2) * shaft_length
    volume_m3 = volume_mm3 / 1e9
    weight = volume_m3 * STEEL_DENSITY
    return round(weight, 3)


def calculate_end_plate_weight(pipe_dia, shaft_dia, thickness):
    """
    Calculate single end plate weight in kg
    End plate is a disc with OD=pipe_dia and bore=shaft_dia
    Weight = π/4 × (OD² - bore²) × thickness × density
    """
    volume_mm3 = (math.pi / 4) * (pipe_dia**2 - shaft_dia**2) * thickness
    volume_m3 = volume_mm3 / 1e9
    weight = volume_m3 * STEEL_DENSITY
    return round(weight, 3)


def calculate_hub_weight(hub_dia, shaft_dia, hub_length):
    """
    Calculate single hub weight in kg
    Hub is a hollow cylinder with OD=hub_dia and ID=shaft_dia
    """
    volume_mm3 = (math.pi / 4) * (hub_dia**2 - shaft_dia**2) * hub_length
    volume_m3 = volume_mm3 / 1e9
    weight = volume_m3 * STEEL_DENSITY
    return round(weight, 3)


def calculate_rubber_lagging_area(pipe_dia, face_length, rubber_thickness):
    """
    Calculate rubber lagging surface area in sqm
    Area = π × pipe_dia × face_length
    (based on pipe OD only, rubber thickness NOT added)
    """
    # Circumference × length based on pipe OD
    area_mm2 = math.pi * pipe_dia * face_length
    area_sqm = area_mm2 / 1e6
    return round(area_sqm, 4)


def calculate_pulley_cost(
    pulley_type,
    pipe_dia,
    pipe_thickness,
    face_length,
    shaft_dia_centre,
    shaft_material,
    shaft_length,
    end_plate_thickness,
    hub_type,
    hub_dia=None,
    hub_length=None,
    shaft_dia_hub=None,
    rubber_type="none",
    rubber_thickness=None,
    quantity=1,
    packing_type="none",
    end_plate_qty=2,
    stress_relieving=False,
):
    """
    Calculate complete pulley cost breakdown
    Returns dict with all cost components
    """
    cost_breakdown = {}
    cost_breakdown["stress_relieving"] = stress_relieving
    sr_surcharge = 10.0 if stress_relieving else 0.0

    # 1. Pipe Cost
    pipe_rate = PIPE_RATES.get(pipe_dia, {}).get(pipe_thickness, 72.0)
    # For pipe dia 630, 800, 1000 with face length > 1250mm, add Rs.8/kg
    if pipe_dia in [630, 800, 1000] and face_length > 1250:
        pipe_rate += 8.0
    pipe_rate += sr_surcharge  # Stress relieving surcharge
    pipe_weight = calculate_pipe_weight(pipe_dia, pipe_thickness, face_length)
    pipe_cost = pipe_weight * pipe_rate
    cost_breakdown["pipe_weight_kg"] = pipe_weight
    cost_breakdown["pipe_rate"] = pipe_rate
    cost_breakdown["pipe_cost"] = round(pipe_cost, 2)

    # 2. Shaft Cost
    shaft_rate = SHAFT_RATES.get(shaft_dia_centre, {}).get(shaft_material, 65.0)
    shaft_weight = calculate_shaft_weight(shaft_dia_centre, shaft_length)
    shaft_cost = shaft_weight * shaft_rate
    cost_breakdown["shaft_weight_kg"] = shaft_weight
    cost_breakdown["shaft_rate"] = shaft_rate
    cost_breakdown["shaft_cost"] = round(shaft_cost, 2)

    # 3. End Plate Cost (2/3/4 plates based on end_plate_qty)
    ep_rate = END_PLATE_RATES.get(end_plate_thickness, 72.0) + sr_surcharge
    ep_weight_single = calculate_end_plate_weight(pipe_dia, shaft_dia_centre, end_plate_thickness)
    ep_weight_total = ep_weight_single * end_plate_qty
    ep_cost = ep_weight_total * ep_rate
    cost_breakdown["end_plate_qty"] = end_plate_qty
    cost_breakdown["end_plate_weight_single_kg"] = ep_weight_single
    cost_breakdown["end_plate_weight_total_kg"] = ep_weight_total
    cost_breakdown["end_plate_rate"] = ep_rate
    cost_breakdown["end_plate_cost"] = round(ep_cost, 2)

    # 4. Hub Cost
    hub_cost = 0
    kla_info = None
    if hub_type == "with_hub" and hub_dia and hub_length:
        hub_rate = HUB_RATES.get(hub_dia, 65.0) + sr_surcharge
        hub_weight_single = calculate_hub_weight(hub_dia, shaft_dia_centre, hub_length)
        hub_weight_total = hub_weight_single * 2
        hub_cost = hub_weight_total * hub_rate
        cost_breakdown["hub_weight_single_kg"] = hub_weight_single
        cost_breakdown["hub_weight_total_kg"] = hub_weight_total
        cost_breakdown["hub_rate"] = hub_rate
        cost_breakdown["hub_cost"] = round(hub_cost, 2)
    elif hub_type == "kla" and shaft_dia_hub:
        kla_info = get_kla_model(shaft_dia_hub)
        if kla_info:
            hub_cost = kla_info["price"] * 2  # 2 KLAs per pulley
            cost_breakdown["kla_model"] = kla_info["model"]
            cost_breakdown["kla_price_each"] = kla_info["price"]
            cost_breakdown["hub_cost"] = round(hub_cost, 2)
        else:
            cost_breakdown["hub_cost"] = 0
    else:
        cost_breakdown["hub_cost"] = 0

    # 5. Rubber Lagging Cost
    rubber_cost = 0
    if rubber_type != "none" and rubber_thickness:
        lagging_area = calculate_rubber_lagging_area(pipe_dia, face_length, rubber_thickness)
        if rubber_type == "ceramic":
            rubber_rate = RUBBER_CERAMIC_RATES.get(rubber_thickness, 0)
        else:
            rubber_rate = RUBBER_PLAIN_RATES.get(rubber_thickness, 0)
        rubber_cost = lagging_area * rubber_rate
        cost_breakdown["rubber_area_sqm"] = lagging_area
        cost_breakdown["rubber_rate_per_sqm"] = rubber_rate
        cost_breakdown["rubber_cost"] = round(rubber_cost, 2)
    else:
        cost_breakdown["rubber_cost"] = 0

    # Total raw material cost per pulley
    total_raw_material = pipe_cost + shaft_cost + ep_cost + hub_cost + rubber_cost
    cost_breakdown["total_raw_material"] = round(total_raw_material, 2)

    # Calculate total pulley weight
    total_weight_single = pipe_weight + shaft_weight + ep_weight_total
    if hub_type == "with_hub" and hub_dia and hub_length:
        total_weight_single += cost_breakdown.get("hub_weight_total_kg", 0)
    cost_breakdown["single_pulley_weight_kg"] = round(total_weight_single, 3)
    cost_breakdown["total_weight_kg"] = round(total_weight_single * quantity, 3)

    # Pricing calculation: Total Raw Material × 1.3 (Labour) × 1.6 (Profit)
    labour_cost = total_raw_material * 0.3
    after_labour = total_raw_material * 1.3
    profit = after_labour * 0.6
    unit_price = after_labour * 1.6
    order_value = unit_price * quantity

    # Packing
    packing_percent = 0
    if packing_type == "standard":
        packing_percent = 1
    elif packing_type == "pallet":
        packing_percent = 4
    elif packing_type == "wooden_box":
        packing_percent = 8
    elif packing_type.startswith("custom_"):
        try:
            packing_percent = float(packing_type.replace("custom_", ""))
        except ValueError:
            packing_percent = 0

    packing_charges = order_value * (packing_percent / 100)
    final_price = order_value + packing_charges

    pricing = {
        "raw_material_cost": round(total_raw_material, 2),
        "labour_factor": 1.3,
        "labour_cost": round(labour_cost, 2),
        "after_labour": round(after_labour, 2),
        "profit_factor": 1.6,
        "profit": round(profit, 2),
        "unit_price": round(unit_price, 2),
        "quantity": quantity,
        "order_value": round(order_value, 2),
        "discount_percent": 0,
        "discount_amount": 0,
        "price_after_discount": round(order_value, 2),
        "packing_type": packing_type,
        "packing_percent": packing_percent,
        "packing_charges": round(packing_charges, 2),
        "final_price": round(final_price, 2),
    }

    # GST (18%)
    taxable_amount = final_price
    gst_rate = 9  # CGST + SGST = 18%
    cgst = taxable_amount * gst_rate / 100
    sgst = taxable_amount * gst_rate / 100
    total_gst = cgst + sgst

    gst_data = {
        "taxable_amount": round(taxable_amount, 2),
        "gst_type": "CGST + SGST",
        "cgst_rate": gst_rate,
        "cgst_amount": round(cgst, 2),
        "sgst_rate": gst_rate,
        "sgst_amount": round(sgst, 2),
        "igst_rate": 0,
        "igst_amount": 0,
        "total_gst": round(total_gst, 2),
        "destination_state": "Maharashtra",
        "is_same_state": True,
    }

    grand_total = final_price + total_gst

    # Build product code
    type_prefix = {
        "Drive": "DR",
        "Tail": "TL",
        "Bend": "BN",
        "Snub": "SN",
        "Take-up": "TU",
    }
    prefix = type_prefix.get(pulley_type, "PL")
    mat_code = {"MS": "M", "EN-8": "E8", "EN-9": "E9", "EN-19": "E19"}.get(shaft_material, "M")
    product_code = f"{prefix}{shaft_dia_centre} {pipe_dia}x{pipe_thickness} {face_length} {mat_code}"

    configuration = {
        "product_code": product_code,
        "product_type": "pulley",
        "pulley_type": pulley_type,
        "pipe_diameter_mm": pipe_dia,
        "pipe_thickness_mm": pipe_thickness,
        "face_length_mm": face_length,
        "shaft_diameter_centre_mm": shaft_dia_centre,
        "shaft_material": shaft_material,
        "shaft_length_mm": shaft_length,
        "end_plate_thickness_mm": end_plate_thickness,
        "end_plate_qty": end_plate_qty,
        "hub_type": hub_type,
        "hub_diameter_mm": hub_dia,
        "hub_length_mm": hub_length,
        "shaft_dia_hub_mm": shaft_dia_hub,
        "kla_model": kla_info["model"] if kla_info else None,
        "stress_relieving": stress_relieving,
        "rubber_type": rubber_type,
        "rubber_thickness_mm": rubber_thickness,
        "quantity": quantity,
    }

    return {
        "configuration": configuration,
        "cost_breakdown": cost_breakdown,
        "pricing": pricing,
        "gst": gst_data,
        "freight": None,
        "grand_total": round(grand_total, 2),
    }
