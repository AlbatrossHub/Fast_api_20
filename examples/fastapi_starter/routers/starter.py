from typing import Annotated

from pydantic import BaseModel

from odoo.addons.base.models.res_partner import ResPartner
from odoo.addons.fastapi.dependencies import authenticated_partner

from fastapi import APIRouter, Depends

router = APIRouter(tags=["starter"])


class HealthInfo(BaseModel):
    status: str


class PartnerInfo(BaseModel):
    id: int
    name: str
    email: str | None = None


@router.get("/health", response_model=HealthInfo)
def health() -> HealthInfo:
    """Liveness probe, no authentication."""
    return HealthInfo(status="ok")


@router.get("/me", response_model=PartnerInfo)
def me(
    partner: Annotated[ResPartner, Depends(authenticated_partner)],
) -> PartnerInfo:
    """The partner of the authenticated caller."""
    return PartnerInfo(id=partner.id, name=partner.name, email=partner.email or None)
