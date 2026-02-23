"""
Roller Drawing Generator
Generates technical drawings with BOM and specifications
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Table, TableStyle
from io import BytesIO
import math
from datetime import datetime


def generate_roller_drawing(
    product_code: str,
    roller_type: str,
    pipe_diameter: float,
    pipe_length: float,
    pipe_type: str,
    shaft_diameter: float,
    bearing: str,
    bearing_make: str,
    housing: str,
    weight_kg: float,
    unit_price: float = 0,  # Made optional, not displayed
    rubber_diameter: float = None,
    belt_widths: list = None,
    quantity: int = 1,
    shaft_end_type: str = "B",  # A (+26mm), B (+36mm), C (+56mm), custom
    custom_shaft_extension: int = None
) -> BytesIO:
    """
    Generate a technical drawing PDF for a roller
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Calculate shaft length based on shaft end type
    shaft_extensions = {"A": 26, "B": 36, "C": 56}
    if shaft_end_type == "custom" and custom_shaft_extension is not None:
        shaft_extension = custom_shaft_extension
    else:
        shaft_extension = shaft_extensions.get(shaft_end_type.upper(), 36)
    shaft_length = pipe_length + shaft_extension
    
    # Colors
    primary_color = colors.HexColor('#960018')  # Carmine red
    dark_color = colors.HexColor('#1A1A2E')
    gray_color = colors.HexColor('#666666')
    light_gray = colors.HexColor('#E0E0E0')
    
    # ============= HEADER =============
    # Logo area
    c.setFillColor(primary_color)
    c.rect(0, height - 80, width, 80, fill=1, stroke=0)
    
    # Company name
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(20*mm, height - 35, "CONVERO SOLUTIONS")
    
    c.setFont("Helvetica", 10)
    c.drawString(20*mm, height - 50, "Belt Conveyor Components & Solutions")
    
    # Drawing number box
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.white)
    c.rect(width - 80*mm, height - 70, 70*mm, 55, fill=0, stroke=1)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(width - 78*mm, height - 30, "DRAWING NO:")
    c.setFont("Helvetica", 11)
    c.drawString(width - 78*mm, height - 45, product_code)
    c.setFont("Helvetica", 8)
    c.drawString(width - 78*mm, height - 60, f"Date: {datetime.now().strftime('%d-%m-%Y')}")
    
    # ============= TITLE BLOCK =============
    y_pos = height - 100
    c.setFillColor(dark_color)
    c.setFont("Helvetica-Bold", 16)
    
    roller_type_text = {
        'carrying': 'CARRYING ROLLER',
        'impact': 'IMPACT ROLLER', 
        'return': 'RETURN ROLLER'
    }.get(roller_type.lower(), 'CONVEYOR ROLLER')
    
    c.drawString(20*mm, y_pos, roller_type_text)
    
    c.setFont("Helvetica", 11)
    c.setFillColor(gray_color)
    c.drawString(20*mm, y_pos - 18, f"Product Code: {product_code}")
    
    # ============= DRAWING AREA =============
    drawing_y = y_pos - 50
    drawing_height = 180
    
    # Drawing border
    c.setStrokeColor(light_gray)
    c.setLineWidth(1)
    c.rect(15*mm, drawing_y - drawing_height, width - 30*mm, drawing_height, fill=0, stroke=1)
    
    # Draw roller schematic
    draw_roller_schematic(
        c, 
        center_x=width/2,
        center_y=drawing_y - drawing_height/2,
        pipe_diameter=pipe_diameter,
        pipe_length=pipe_length,
        shaft_diameter=shaft_diameter,
        shaft_length=shaft_length,  # Pass calculated shaft length
        rubber_diameter=rubber_diameter,
        roller_type=roller_type
    )
    
    # ============= DIMENSIONS TABLE =============
    dim_y = drawing_y - drawing_height - 20
    c.setFillColor(primary_color)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20*mm, dim_y, "DIMENSIONS")
    
    dim_y -= 5
    
    # Shaft end type display
    shaft_end_label = {
        "A": "Type A (+26mm)",
        "B": "Type B (+36mm)",
        "C": "Type C (+56mm)",
        "custom": f"Custom (+{shaft_extension}mm)"
    }.get(shaft_end_type, f"Type {shaft_end_type}")
    
    dim_data = [
        ['Parameter', 'Value', 'Unit'],
        ['Pipe Outside Diameter', f'{pipe_diameter}', 'mm'],
        ['Pipe Length', f'{pipe_length}', 'mm'],
        ['Pipe Type', f'Type {pipe_type} ({"Light" if pipe_type == "A" else "Medium" if pipe_type == "B" else "Heavy"})', '-'],
        ['Shaft Diameter', f'{shaft_diameter}', 'mm'],
        ['Shaft End Type', shaft_end_label, '-'],
        ['Shaft Length', f'{int(shaft_length)}', 'mm'],
        ['Total Weight', f'{weight_kg}', 'kg'],
    ]
    
    if rubber_diameter:
        dim_data.insert(3, ['Rubber Outside Diameter', f'{rubber_diameter}', 'mm'])
    
    if belt_widths:
        dim_data.append(['Belt Width Compatibility', ', '.join(map(str, belt_widths)), 'mm'])
    
    dim_table = Table(dim_data, colWidths=[60*mm, 50*mm, 20*mm])
    dim_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    table_width, table_height = dim_table.wrap(0, 0)
    dim_table.drawOn(c, 20*mm, dim_y - table_height - 5)
    
    # ============= BILL OF MATERIALS =============
    bom_y = dim_y - table_height - 30
    c.setFillColor(primary_color)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20*mm, bom_y, "BILL OF MATERIALS")
    
    bom_y -= 5
    
    bom_data = [
        ['Sr.', 'Component', 'Specification', 'Qty'],
        ['1', 'Pipe', f'OD {pipe_diameter}mm, Type {pipe_type}', '1'],
        ['2', 'Shaft', f'Ø{shaft_diameter}mm x {shaft_length}mm', '1'],
        ['3', 'Bearing', f'{bearing} ({bearing_make.upper()})', '2'],
        ['4', 'Housing', f'{housing}', '2'],
        ['5', 'Seal Set', f'For {bearing}', '2'],
        ['6', 'Circlip', f'For Ø{shaft_diameter}mm shaft', '4'],
    ]
    
    if rubber_diameter:
        num_rings = int(pipe_length / 35)
        bom_data.append(['7', 'Rubber Rings', f'Ø{rubber_diameter}mm x 35mm thick', str(num_rings)])
        bom_data.append(['8', 'Locking Ring', f'For Ø{int(pipe_diameter)}mm pipe', '1'])
    
    bom_table = Table(bom_data, colWidths=[12*mm, 35*mm, 65*mm, 18*mm])
    bom_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (3, 0), (3, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    bom_width, bom_height = bom_table.wrap(0, 0)
    bom_table.drawOn(c, 20*mm, bom_y - bom_height - 5)
    
    # ============= PRICING (Right side) =============
    price_x = width - 75*mm
    price_y = dim_y
    
    c.setFillColor(primary_color)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(price_x, price_y, "PRICING")
    
    price_y -= 20
    c.setFillColor(dark_color)
    c.setFont("Helvetica", 10)
    c.drawString(price_x, price_y, f"Unit Price:")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(price_x + 25*mm, price_y, f"Rs. {unit_price:.2f}")
    
    price_y -= 18
    c.setFont("Helvetica", 10)
    c.drawString(price_x, price_y, f"Quantity:")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(price_x + 25*mm, price_y, f"{quantity} pcs")
    
    price_y -= 18
    c.setFont("Helvetica", 10)
    c.drawString(price_x, price_y, f"Total:")
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(primary_color)
    c.drawString(price_x + 25*mm, price_y, f"Rs. {unit_price * quantity:.2f}")
    
    # ============= MATERIAL SPECS BOX =============
    spec_y = price_y - 40
    c.setFillColor(primary_color)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(price_x, spec_y, "MATERIAL SPECS")
    
    spec_y -= 18
    c.setFillColor(dark_color)
    c.setFont("Helvetica", 9)
    
    specs = [
        f"Pipe: IS-9295 ERW Steel",
        f"Shaft: EN8/EN9 Steel",
        f"Bearing: {bearing_make.upper()} Grade",
        f"Housing: Cast Iron",
        f"Seals: Nitrile Rubber",
    ]
    
    if rubber_diameter:
        specs.append(f"Rubber: Natural Rubber")
    
    for spec in specs:
        c.drawString(price_x, spec_y, spec)
        spec_y -= 14
    
    # ============= FOOTER =============
    footer_y = 25
    c.setStrokeColor(light_gray)
    c.line(15*mm, footer_y + 15, width - 15*mm, footer_y + 15)
    
    c.setFillColor(gray_color)
    c.setFont("Helvetica", 8)
    c.drawString(20*mm, footer_y, "CONVERO SOLUTIONS | Belt Conveyor Components")
    c.drawRightString(width - 20*mm, footer_y, f"Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}")
    
    # Notes
    c.setFont("Helvetica-Oblique", 7)
    c.drawString(20*mm, footer_y - 12, "* All dimensions in mm unless specified. Prices subject to change. GST extra as applicable.")
    
    c.save()
    buffer.seek(0)
    return buffer


def draw_roller_schematic(c, center_x, center_y, pipe_diameter, pipe_length, shaft_diameter, rubber_diameter=None, roller_type='carrying'):
    """
    Draw a simplified roller schematic with dimensions
    """
    # Scale factor to fit drawing
    max_width = 140 * mm
    max_height = 80 * mm
    
    # Calculate scale
    actual_length = pipe_length + 100  # Include shaft extensions
    scale = min(max_width / actual_length, max_height / (rubber_diameter or pipe_diameter))
    scale = min(scale, 0.4)  # Cap the scale
    
    # Scaled dimensions
    pipe_len = pipe_length * scale
    pipe_dia = pipe_diameter * scale
    shaft_dia = shaft_diameter * scale
    shaft_ext = 35 * scale  # Shaft extension on each side
    
    if rubber_diameter:
        rubber_dia = rubber_diameter * scale
    else:
        rubber_dia = pipe_dia
    
    # Colors
    pipe_color = colors.HexColor('#4A90A4')
    shaft_color = colors.HexColor('#666666')
    rubber_color = colors.HexColor('#2D5016')
    dim_color = colors.HexColor('#333333')
    
    # Draw shaft (full length)
    shaft_total = pipe_len + 2 * shaft_ext
    c.setFillColor(shaft_color)
    c.rect(center_x - shaft_total/2, center_y - shaft_dia/2, shaft_total, shaft_dia, fill=1, stroke=0)
    
    # Draw pipe
    c.setFillColor(pipe_color)
    c.rect(center_x - pipe_len/2, center_y - pipe_dia/2, pipe_len, pipe_dia, fill=1, stroke=0)
    
    # Draw rubber lagging for impact rollers
    if rubber_diameter and roller_type.lower() == 'impact':
        c.setFillColor(rubber_color)
        c.rect(center_x - pipe_len/2, center_y - rubber_dia/2, pipe_len, rubber_dia, fill=1, stroke=0)
        # Redraw pipe as inner (cutaway effect)
        c.setFillColor(pipe_color)
        c.setStrokeColor(colors.white)
        c.setLineWidth(1)
        pipe_inner = pipe_dia * 0.8
        c.rect(center_x - pipe_len/2, center_y - pipe_inner/2, pipe_len, pipe_inner, fill=1, stroke=1)
    
    # Draw bearings (simplified as circles at ends)
    bearing_dia = pipe_dia * 0.7
    c.setFillColor(colors.HexColor('#FFD700'))
    c.setStrokeColor(colors.HexColor('#B8860B'))
    c.setLineWidth(1)
    c.circle(center_x - pipe_len/2 + 5, center_y, bearing_dia/2, fill=1, stroke=1)
    c.circle(center_x + pipe_len/2 - 5, center_y, bearing_dia/2, fill=1, stroke=1)
    
    # Dimension lines
    c.setStrokeColor(dim_color)
    c.setFillColor(dim_color)
    c.setLineWidth(0.5)
    c.setFont("Helvetica", 7)
    
    # Pipe length dimension (top)
    dim_y_top = center_y + rubber_dia/2 + 15
    c.line(center_x - pipe_len/2, dim_y_top, center_x + pipe_len/2, dim_y_top)
    c.line(center_x - pipe_len/2, dim_y_top - 3, center_x - pipe_len/2, dim_y_top + 3)
    c.line(center_x + pipe_len/2, dim_y_top - 3, center_x + pipe_len/2, dim_y_top + 3)
    c.drawCentredString(center_x, dim_y_top + 5, f"{pipe_length} mm")
    
    # Total shaft length dimension (top)
    dim_y_shaft = dim_y_top + 20
    c.line(center_x - shaft_total/2, dim_y_shaft, center_x + shaft_total/2, dim_y_shaft)
    c.line(center_x - shaft_total/2, dim_y_shaft - 3, center_x - shaft_total/2, dim_y_shaft + 3)
    c.line(center_x + shaft_total/2, dim_y_shaft - 3, center_x + shaft_total/2, dim_y_shaft + 3)
    c.drawCentredString(center_x, dim_y_shaft + 5, f"{pipe_length + 70} mm (shaft)")
    
    # Diameter dimension (right side)
    dim_x_right = center_x + shaft_total/2 + 20
    if rubber_diameter:
        c.line(dim_x_right, center_y - rubber_dia/2, dim_x_right, center_y + rubber_dia/2)
        c.line(dim_x_right - 3, center_y - rubber_dia/2, dim_x_right + 3, center_y - rubber_dia/2)
        c.line(dim_x_right - 3, center_y + rubber_dia/2, dim_x_right + 3, center_y + rubber_dia/2)
        c.saveState()
        c.translate(dim_x_right + 8, center_y)
        c.rotate(90)
        c.drawCentredString(0, 0, f"Ø{rubber_diameter} mm")
        c.restoreState()
    else:
        c.line(dim_x_right, center_y - pipe_dia/2, dim_x_right, center_y + pipe_dia/2)
        c.line(dim_x_right - 3, center_y - pipe_dia/2, dim_x_right + 3, center_y - pipe_dia/2)
        c.line(dim_x_right - 3, center_y + pipe_dia/2, dim_x_right + 3, center_y + pipe_dia/2)
        c.saveState()
        c.translate(dim_x_right + 8, center_y)
        c.rotate(90)
        c.drawCentredString(0, 0, f"Ø{pipe_diameter} mm")
        c.restoreState()
    
    # Shaft diameter (left side, smaller)
    dim_x_left = center_x - shaft_total/2 - 15
    c.line(dim_x_left, center_y - shaft_dia/2, dim_x_left, center_y + shaft_dia/2)
    c.line(dim_x_left - 3, center_y - shaft_dia/2, dim_x_left + 3, center_y - shaft_dia/2)
    c.line(dim_x_left - 3, center_y + shaft_dia/2, dim_x_left + 3, center_y + shaft_dia/2)
    c.saveState()
    c.translate(dim_x_left - 5, center_y)
    c.rotate(90)
    c.drawCentredString(0, 0, f"Ø{shaft_diameter}")
    c.restoreState()
    
    # Labels
    c.setFont("Helvetica", 6)
    c.drawCentredString(center_x, center_y - rubber_dia/2 - 10, "PIPE" if not rubber_diameter else "RUBBER + PIPE")
    c.drawString(center_x - shaft_total/2 + 2, center_y + shaft_dia/2 + 3, "SHAFT")
