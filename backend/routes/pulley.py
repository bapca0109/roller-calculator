"""Pulley Calculator Routes"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
from routes import db, get_current_user, ROOT_DIR
import pulley_standards as ps

router = APIRouter()


@router.get("/pulley-standards")
async def get_pulley_standards(current_user: dict = Depends(get_current_user)):
    return {
        "pulley_types": ps.PULLEY_TYPES,
        "pipe_diameters": ps.PIPE_DIAMETERS,
        "pipe_thickness_map": {str(k): v for k, v in ps.PIPE_THICKNESS_MAP.items()},
        "shaft_diameters": ps.SHAFT_DIAMETERS,
        "shaft_materials": ps.SHAFT_MATERIALS,
        "end_plate_thicknesses": ps.END_PLATE_THICKNESSES,
        "hub_types": ps.HUB_TYPES,
        "hub_diameters": ps.HUB_DIAMETERS,
        "kla_shaft_hub_options": ps.KLA_SHAFT_HUB_OPTIONS,
        "rubber_lagging_types": ps.RUBBER_LAGGING_TYPES,
        "rubber_plain_thicknesses": ps.RUBBER_PLAIN_THICKNESSES,
        "rubber_ceramic_thicknesses": ps.RUBBER_CERAMIC_THICKNESSES,
    }


class PulleyCostRequest(BaseModel):
    pulley_type: str = "Drive"
    pipe_diameter: int
    pipe_thickness: float
    face_length: float
    shaft_diameter_centre: int
    shaft_material: str = "MS"
    shaft_length: float
    end_plate_thickness: int
    end_plate_qty: int = 2
    hub_type: str = "no_hub"
    hub_diameter: Optional[int] = None
    hub_length: Optional[float] = None
    shaft_dia_hub: Optional[int] = None
    rubber_type: str = "none"
    rubber_thickness: Optional[int] = None
    quantity: int = 1
    packing_type: str = "none"
    stress_relieving: bool = False


class PulleyCostResponse(BaseModel):
    configuration: Dict[str, Any]
    cost_breakdown: Dict[str, Any]
    pricing: Dict[str, Any]
    gst: Optional[Dict[str, Any]] = None
    freight: Optional[Dict[str, Any]] = None
    grand_total: float


@router.post("/calculate-pulley-cost", response_model=PulleyCostResponse)
async def calculate_pulley_cost(request: PulleyCostRequest, current_user: dict = Depends(get_current_user)):
    if request.pipe_diameter not in ps.PIPE_DIAMETERS:
        raise HTTPException(status_code=400, detail=f"Invalid pipe diameter. Must be one of {ps.PIPE_DIAMETERS}")
    available_thk = ps.get_available_thicknesses(request.pipe_diameter)
    if request.pipe_thickness not in available_thk:
        raise HTTPException(status_code=400, detail=f"Invalid thickness for {request.pipe_diameter}mm pipe. Available: {available_thk}")
    if request.shaft_diameter_centre not in ps.SHAFT_DIAMETERS:
        raise HTTPException(status_code=400, detail=f"Invalid shaft diameter. Must be one of {ps.SHAFT_DIAMETERS}")
    if request.shaft_material not in ps.SHAFT_MATERIALS:
        raise HTTPException(status_code=400, detail=f"Invalid shaft material. Must be one of {ps.SHAFT_MATERIALS}")
    if request.hub_type == "with_hub":
        if not request.hub_diameter or not request.hub_length:
            raise HTTPException(status_code=400, detail="Hub diameter and hub length required for 'With Hub' type")
        min_hub_dia = request.shaft_diameter_centre + 40
        if request.hub_diameter < min_hub_dia:
            raise HTTPException(status_code=400, detail=f"Hub diameter must be >= {min_hub_dia}mm (Shaft Dia + 40mm)")
    elif request.hub_type == "kla":
        if not request.shaft_dia_hub:
            raise HTTPException(status_code=400, detail="Shaft Dia @ Hub is required for KLA hub type")
        kla_info = ps.get_kla_model(request.shaft_dia_hub)
        if not kla_info:
            raise HTTPException(status_code=400, detail=f"No KLA model found for shaft dia @ hub = {request.shaft_dia_hub}mm")
    if request.rubber_type in ["plain", "diamond"]:
        if not request.rubber_thickness or request.rubber_thickness not in ps.RUBBER_PLAIN_THICKNESSES:
            raise HTTPException(status_code=400, detail=f"Invalid rubber thickness for plain/diamond. Must be one of {ps.RUBBER_PLAIN_THICKNESSES}")
    elif request.rubber_type == "ceramic":
        if not request.rubber_thickness or request.rubber_thickness not in ps.RUBBER_CERAMIC_THICKNESSES:
            raise HTTPException(status_code=400, detail=f"Invalid rubber thickness for ceramic. Must be one of {ps.RUBBER_CERAMIC_THICKNESSES}")

    result = ps.calculate_pulley_cost(
        pulley_type=request.pulley_type, pipe_dia=request.pipe_diameter,
        pipe_thickness=request.pipe_thickness, face_length=request.face_length,
        shaft_dia_centre=request.shaft_diameter_centre, shaft_material=request.shaft_material,
        shaft_length=request.shaft_length, end_plate_thickness=request.end_plate_thickness,
        hub_type=request.hub_type, hub_dia=request.hub_diameter, hub_length=request.hub_length,
        shaft_dia_hub=request.shaft_dia_hub, rubber_type=request.rubber_type,
        rubber_thickness=request.rubber_thickness, quantity=request.quantity,
        packing_type=request.packing_type, end_plate_qty=request.end_plate_qty,
        stress_relieving=request.stress_relieving,
    )
    return PulleyCostResponse(**result)


@router.get("/pulley-thicknesses/{pipe_dia}")
async def get_pulley_thicknesses(pipe_dia: int, current_user: dict = Depends(get_current_user)):
    thicknesses = ps.get_available_thicknesses(pipe_dia)
    if not thicknesses:
        raise HTTPException(status_code=404, detail=f"No thicknesses found for pipe diameter {pipe_dia}mm")
    return {"pipe_diameter": pipe_dia, "thicknesses": thicknesses}


@router.get("/pulley-kla-model/{shaft_dia_hub}")
async def get_pulley_kla_model(shaft_dia_hub: int, current_user: dict = Depends(get_current_user)):
    kla_info = ps.get_kla_model(shaft_dia_hub)
    if not kla_info:
        raise HTTPException(status_code=404, detail=f"No KLA model for shaft dia @ hub = {shaft_dia_hub}mm")
    return kla_info


@router.get("/download/pulley-template")
async def download_pulley_template():
    file_path = ROOT_DIR / "static" / "pulley_pricing_template.xlsx"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Template file not found")
    return FileResponse(path=str(file_path), filename="pulley_pricing_template.xlsx",
                       media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
