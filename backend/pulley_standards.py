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
# Based on the Excel template structure (non-dash cells)
PIPE_THICKNESS_MAP = {
    139: [4.8, 5.4],
    152: [4.8, 5.4],
    168: [4.8, 5.4],
    193: [5.4, 6.3],
    219: [6.3, 8, 10, 12],
    245: [6.3, 8, 10, 12],
    273: [6.3, 8, 10, 12],
    323: [8, 10, 12, 14, 16],
    355: [8, 10, 12, 14, 16],
    406: [10, 12, 14, 16, 18, 20],
    455: [10, 12, 14, 16, 18, 20],
    508: [12, 14, 16, 18, 20, 22],
    609: [14, 16, 18, 20, 22, 24],
    630: [14, 16, 18, 20, 22, 24],
    800: [18, 20, 22, 24, 26],
    1000: [20, 22, 24, 26],
}

# Shaft Diameters (mm) - 50 to 300 in steps of 5
SHAFT_DIAMETERS = list(range(50, 305, 5))

# Shaft Materials
SHAFT_MATERIALS = ["MS", "EN-8", "EN-9", "EN-19"]

# End Plate Thicknesses (mm) - 6 to 50 in steps of 2
END_PLATE_THICKNESSES = list(range(6, 52, 2))

# Hub Types
HUB_TYPES = ["no_hub", "with_hub", "kla"]

# Hub Dia options (mm) - for "With Hub" type
HUB_DIAMETERS = list(range(100, 460, 10))  # 100-450 in steps of 10

# KLA Shaft @ Hub options (mm) - 25 to 290 in steps of 5
KLA_SHAFT_HUB_OPTIONS = list(range(25, 295, 5))

# Rubber Lagging Types
RUBBER_LAGGING_TYPES = ["none", "plain", "diamond", "ceramic"]

# Rubber Lagging Thicknesses (mm)
RUBBER_PLAIN_THICKNESSES = [8, 10, 12, 14, 16, 18, 20]
RUBBER_CERAMIC_THICKNESSES = [12, 15, 22]

# Steel density (kg/m³)
STEEL_DENSITY = 7850

# ============= MOCK PRICING (Placeholder until user uploads Excel) =============

# Pipe rates: { pipe_dia: { thickness: rate_per_kg } }
PIPE_RATES = {}
for dia in PIPE_DIAMETERS:
    PIPE_RATES[dia] = {}
    for thk in PIPE_THICKNESS_MAP.get(dia, []):
        # Mock rate: 70-80 range based on template examples
        PIPE_RATES[dia][thk] = 72.0

# Shaft rates: { shaft_dia: { material: rate_per_kg } }
SHAFT_RATES = {}
for dia in SHAFT_DIAMETERS:
    SHAFT_RATES[dia] = {
        "MS": 65.0,
        "EN-8": 75.0,
        "EN-9": 85.0,
        "EN-19": 95.0,
    }

# End Plate MS rate per kg
END_PLATE_RATE = 68.0

# Hub MS rate per kg (for "With Hub")
HUB_RATE = 68.0

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
    8: 450,
    10: 520,
    12: 600,
    14: 680,
    16: 760,
    18: 850,
    20: 950,
}

RUBBER_CERAMIC_RATES = {
    12: 2800,
    15: 3200,
    22: 4500,
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
    """
    od = pipe_dia  # mm
    id_val = pipe_dia - 2 * wall_thickness  # mm
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
    Area = π × (pipe_dia + 2 × rubber_thickness) × face_length
    (outer surface of the lagging)
    """
    outer_dia = pipe_dia + 2 * rubber_thickness  # mm
    # Circumference × length
    area_mm2 = math.pi * outer_dia * face_length
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
):
    """
    Calculate complete pulley cost breakdown
    Returns dict with all cost components
    """
    cost_breakdown = {}

    # 1. Pipe Cost
    pipe_rate = PIPE_RATES.get(pipe_dia, {}).get(pipe_thickness, 72.0)
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

    # 3. End Plate Cost (2 plates)
    ep_weight_single = calculate_end_plate_weight(pipe_dia, shaft_dia_centre, end_plate_thickness)
    ep_weight_total = ep_weight_single * 2
    ep_cost = ep_weight_total * END_PLATE_RATE
    cost_breakdown["end_plate_weight_single_kg"] = ep_weight_single
    cost_breakdown["end_plate_weight_total_kg"] = ep_weight_total
    cost_breakdown["end_plate_rate"] = END_PLATE_RATE
    cost_breakdown["end_plate_cost"] = round(ep_cost, 2)

    # 4. Hub Cost
    hub_cost = 0
    kla_info = None
    if hub_type == "with_hub" and hub_dia and hub_length:
        hub_weight_single = calculate_hub_weight(hub_dia, shaft_dia_centre, hub_length)
        hub_weight_total = hub_weight_single * 2
        hub_cost = hub_weight_total * HUB_RATE
        cost_breakdown["hub_weight_single_kg"] = hub_weight_single
        cost_breakdown["hub_weight_total_kg"] = hub_weight_total
        cost_breakdown["hub_rate"] = HUB_RATE
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

    # Pricing calculation (similar pattern to roller)
    unit_price = total_raw_material
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
        "hub_type": hub_type,
        "hub_diameter_mm": hub_dia,
        "hub_length_mm": hub_length,
        "shaft_dia_hub_mm": shaft_dia_hub,
        "kla_model": kla_info["model"] if kla_info else None,
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
