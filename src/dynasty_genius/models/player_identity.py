from pydantic import BaseModel, Field
from typing import Optional

class PlayerIdentity(BaseModel):
    """
    Canonical identity mapping for a player across all supported sources.
    This is the foundation of the Silver layer identity resolution.
    """
    dg_id: str = Field(..., description="Canonical Dynasty Genius ID (e.g. josh_allen_qb_1996)")
    full_name: str
    position: str
    birth_date: Optional[str] = None
    nfl_team: Optional[str] = None
    jersey_number: Optional[str] = None
    
    # Source-specific IDs
    sleeper_id: Optional[str] = None
    pff_id: Optional[str] = None
    pfr_id: Optional[str] = None
    playerprofiler_id: Optional[str] = None
    
    # Metadata
    last_updated_ts: Optional[str] = None
    verification_status: str = "PENDING"  # PENDING, VERIFIED, CONFLICT, VERIFIED_NFL_DRAFT
    age_verified: bool = False
    identity_verified: bool = False
