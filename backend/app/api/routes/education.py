"""
Education concepts API.

Routes:
  GET /api/education/concepts           — list all concepts
  GET /api/education/concepts/{slug}    — get one concept by slug
"""
from fastapi import APIRouter, HTTPException

from app.education.content import CONCEPTS, get_concept

__all__ = ["router"]

router = APIRouter(prefix="/education", tags=["education"])


@router.get("/concepts")
async def list_concepts() -> list[dict]:
    """Return all trading concept explanations."""
    return list(CONCEPTS.values())


@router.get("/concepts/{slug}")
async def get_concept_by_slug(slug: str) -> dict:
    """Return a single concept by URL slug."""
    concept = get_concept(slug)
    if concept is None:
        raise HTTPException(status_code=404, detail=f"Concept '{slug}' not found")
    return concept
