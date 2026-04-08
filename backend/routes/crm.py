"""CRM Routes — Lead Management, Follow-up Reminders, Activity Timeline"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from routes import db, get_current_user, require_role, get_ist_now, utc_to_ist, IST, UserRole
import logging

router = APIRouter(prefix="/crm")

# ============= LEAD MODELS =============

LEAD_STAGES = ["new", "contacted", "quoted", "negotiation", "won", "lost"]
LEAD_SOURCES = ["phone", "email", "walk_in", "referral", "website", "other"]


class LeadCreate(BaseModel):
    name: str
    company: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    source: str = "phone"
    notes: Optional[str] = None
    product_interest: Optional[str] = None  # "roller", "pulley", "both"
    estimated_value: Optional[float] = None
    assigned_to: Optional[str] = None


class LeadUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    stage: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    product_interest: Optional[str] = None
    estimated_value: Optional[float] = None
    assigned_to: Optional[str] = None
    lost_reason: Optional[str] = None


class FollowUpCreate(BaseModel):
    lead_id: str
    due_date: str  # ISO date string
    note: str
    follow_up_type: str = "call"  # call, email, meeting, other


class ActivityCreate(BaseModel):
    lead_id: Optional[str] = None
    customer_id: Optional[str] = None
    activity_type: str  # note, call, email, meeting, quote_sent, rfq_received, status_change, attachment
    description: str
    metadata: Optional[Dict[str, Any]] = None


# ============= LEAD ROUTES =============

@router.get("/leads")
async def get_leads(
    stage: Optional[str] = None,
    source: Optional[str] = None,
    assigned_to: Optional[str] = None,
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))
):
    query = {}
    if stage:
        query["stage"] = stage
    if source:
        query["source"] = source
    if assigned_to:
        query["assigned_to"] = assigned_to

    leads = await db.leads.find(query, {"_id": 0}).sort("updated_at", -1).to_list(500)

    # Add overdue follow-up flag
    now = get_ist_now()
    for lead in leads:
        next_followup = await db.followups.find_one(
            {"lead_id": lead["id"], "completed": False, "due_date": {"$lt": now.isoformat()}},
            {"_id": 0}
        )
        lead["has_overdue_followup"] = next_followup is not None

    return {"leads": leads, "total": len(leads)}


@router.post("/leads")
async def create_lead(lead: LeadCreate, current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))):
    now = get_ist_now()
    lead_id = str(ObjectId())
    lead_dict = lead.dict()
    lead_dict.update({
        "id": lead_id,
        "stage": "new",
        "created_by": current_user.get("email"),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    })
    await db.leads.insert_one(lead_dict)

    # Log activity
    await _log_activity(lead_id=lead_id, activity_type="lead_created",
                        description=f"Lead created: {lead.name}" + (f" ({lead.company})" if lead.company else ""),
                        user=current_user)

    del lead_dict["_id"]
    return {"message": "Lead created", "lead": lead_dict}


@router.get("/leads/{lead_id}")
async def get_lead(lead_id: str, current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))):
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Get follow-ups
    followups = await db.followups.find({"lead_id": lead_id}, {"_id": 0}).sort("due_date", 1).to_list(50)
    # Get activities
    activities = await db.activities.find({"lead_id": lead_id}, {"_id": 0}).sort("created_at", -1).to_list(100)

    return {"lead": lead, "followups": followups, "activities": activities}


@router.put("/leads/{lead_id}")
async def update_lead(lead_id: str, update: LeadUpdate, current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))):
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    update_dict = {k: v for k, v in update.dict().items() if v is not None}
    update_dict["updated_at"] = get_ist_now().isoformat()

    # Track stage change
    old_stage = lead.get("stage")
    new_stage = update_dict.get("stage")

    await db.leads.update_one({"id": lead_id}, {"$set": update_dict})

    if new_stage and new_stage != old_stage:
        await _log_activity(lead_id=lead_id, activity_type="status_change",
                            description=f"Stage changed: {old_stage} → {new_stage}",
                            user=current_user, metadata={"old_stage": old_stage, "new_stage": new_stage})

        # If won, auto-create customer if not exists
        if new_stage == "won" and lead.get("email"):
            existing = await db.customers.find_one({"email": lead["email"]})
            if not existing:
                from routes import generate_customer_code
                code = await generate_customer_code()
                await db.customers.insert_one({
                    "name": lead.get("name"), "company": lead.get("company"),
                    "email": lead.get("email"), "phone": lead.get("phone"),
                    "customer_code": code, "created_by": current_user.get("email"),
                    "created_at": datetime.utcnow(), "notes": f"Converted from lead {lead_id}",
                })
                await _log_activity(lead_id=lead_id, activity_type="lead_converted",
                                    description=f"Lead converted to customer ({code})", user=current_user)

    return {"message": "Lead updated"}


@router.delete("/leads/{lead_id}")
async def delete_lead(lead_id: str, current_user: dict = Depends(require_role([UserRole.ADMIN]))):
    result = await db.leads.delete_one({"id": lead_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    await db.followups.delete_many({"lead_id": lead_id})
    await db.activities.delete_many({"lead_id": lead_id})
    return {"message": "Lead deleted"}


# ============= FOLLOW-UP ROUTES =============

@router.get("/followups")
async def get_followups(
    overdue_only: bool = False,
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))
):
    query = {"completed": False}
    if overdue_only:
        query["due_date"] = {"$lt": get_ist_now().isoformat()}

    followups = await db.followups.find(query, {"_id": 0}).sort("due_date", 1).to_list(200)

    # Enrich with lead info
    for fu in followups:
        lead = await db.leads.find_one({"id": fu.get("lead_id")}, {"_id": 0, "name": 1, "company": 1, "stage": 1})
        fu["lead"] = lead

    return {"followups": followups, "total": len(followups)}


@router.post("/followups")
async def create_followup(fu: FollowUpCreate, current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))):
    lead = await db.leads.find_one({"id": fu.lead_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    now = get_ist_now()
    fu_id = str(ObjectId())
    fu_dict = fu.dict()
    fu_dict.update({
        "id": fu_id,
        "completed": False,
        "created_by": current_user.get("email"),
        "created_at": now.isoformat(),
    })
    await db.followups.insert_one(fu_dict)

    await _log_activity(lead_id=fu.lead_id, activity_type="followup_scheduled",
                        description=f"Follow-up scheduled: {fu.follow_up_type} on {fu.due_date}",
                        user=current_user)

    del fu_dict["_id"]
    return {"message": "Follow-up created", "followup": fu_dict}


@router.put("/followups/{followup_id}/complete")
async def complete_followup(followup_id: str, current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))):
    fu = await db.followups.find_one({"id": followup_id})
    if not fu:
        raise HTTPException(status_code=404, detail="Follow-up not found")

    await db.followups.update_one({"id": followup_id}, {"$set": {
        "completed": True, "completed_at": get_ist_now().isoformat(), "completed_by": current_user.get("email")
    }})

    await _log_activity(lead_id=fu.get("lead_id"), activity_type="followup_completed",
                        description=f"Follow-up completed: {fu.get('follow_up_type')}", user=current_user)

    return {"message": "Follow-up marked complete"}


# ============= ACTIVITY TIMELINE =============

@router.get("/activities")
async def get_activities(
    lead_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    limit: int = 50,
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))
):
    query = {}
    if lead_id:
        query["lead_id"] = lead_id
    if customer_id:
        query["customer_id"] = customer_id

    activities = await db.activities.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return {"activities": activities, "total": len(activities)}


@router.post("/activities")
async def create_activity(activity: ActivityCreate, current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))):
    now = get_ist_now()
    act_dict = activity.dict()
    act_dict.update({
        "id": str(ObjectId()),
        "created_by": current_user.get("email"),
        "created_by_name": current_user.get("name"),
        "created_at": now.isoformat(),
    })
    await db.activities.insert_one(act_dict)
    del act_dict["_id"]
    return {"message": "Activity logged", "activity": act_dict}


# ============= CRM DASHBOARD SUMMARY =============

@router.get("/summary")
async def get_crm_summary(current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))):
    now = get_ist_now()

    # Lead counts by stage
    pipeline = [{"$group": {"_id": "$stage", "count": {"$sum": 1}}}]
    stage_counts_raw = await db.leads.aggregate(pipeline).to_list(10)
    stage_counts = {s["_id"]: s["count"] for s in stage_counts_raw}

    total_leads = sum(stage_counts.values())
    won = stage_counts.get("won", 0)
    lost = stage_counts.get("lost", 0)
    active = total_leads - won - lost

    # Overdue follow-ups
    overdue_count = await db.followups.count_documents({
        "completed": False, "due_date": {"$lt": now.isoformat()}
    })

    # Today's follow-ups
    today_start = now.replace(hour=0, minute=0, second=0).isoformat()
    today_end = now.replace(hour=23, minute=59, second=59).isoformat()
    today_followups = await db.followups.count_documents({
        "completed": False, "due_date": {"$gte": today_start, "$lte": today_end}
    })

    # Estimated pipeline value
    value_pipeline = [
        {"$match": {"stage": {"$in": ["new", "contacted", "quoted", "negotiation"]}}},
        {"$group": {"_id": None, "total": {"$sum": {"$ifNull": ["$estimated_value", 0]}}}}
    ]
    value_result = await db.leads.aggregate(value_pipeline).to_list(1)
    pipeline_value = value_result[0]["total"] if value_result else 0

    # Recent activities
    recent = await db.activities.find({}, {"_id": 0}).sort("created_at", -1).to_list(10)

    return {
        "total_leads": total_leads,
        "active_leads": active,
        "won": won,
        "lost": lost,
        "stage_counts": stage_counts,
        "overdue_followups": overdue_count,
        "today_followups": today_followups,
        "pipeline_value": pipeline_value,
        "conversion_rate": round((won / total_leads * 100) if total_leads > 0 else 0, 1),
        "recent_activities": recent,
    }


@router.get("/options")
async def get_crm_options(current_user: dict = Depends(get_current_user)):
    return {
        "lead_stages": LEAD_STAGES,
        "lead_sources": LEAD_SOURCES,
        "followup_types": ["call", "email", "meeting", "other"],
        "activity_types": ["note", "call", "email", "meeting", "quote_sent", "rfq_received", "status_change", "attachment"],
    }


# ============= HELPER =============

async def _log_activity(lead_id: str = None, customer_id: str = None,
                        activity_type: str = "note", description: str = "",
                        user: dict = None, metadata: dict = None):
    now = get_ist_now()
    act = {
        "id": str(ObjectId()),
        "lead_id": lead_id,
        "customer_id": customer_id,
        "activity_type": activity_type,
        "description": description,
        "metadata": metadata or {},
        "created_by": user.get("email") if user else None,
        "created_by_name": user.get("name") if user else None,
        "created_at": now.isoformat(),
    }
    await db.activities.insert_one(act)
