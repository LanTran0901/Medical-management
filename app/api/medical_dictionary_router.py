from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_medical_dictionary_service
from app.application.dtos.medical_dictionary_dto import (
	DictionaryDetailResponse,
	DictionarySearchItemResponse,
	DictionarySearchResponse,
)
from app.application.usecases.medical_dictionary_usecases import MedicalDictionaryService
from app.domain.entities.medical_dictionary import DictionaryEntryType

router = APIRouter(prefix="/medical-dictionary", tags=["medical-dictionary"])


@router.get("/search", response_model=DictionarySearchResponse)
async def search_dictionary(
	q: str = Query(..., min_length=1),
	type: DictionaryEntryType | None = Query(None),
	page: int = Query(1, ge=1),
	limit: int = Query(20, ge=1, le=100),
	svc: MedicalDictionaryService = Depends(get_medical_dictionary_service),
) -> DictionarySearchResponse:
	items, total = await svc.search(q=q, entry_type=type, page=page, limit=limit)
	return DictionarySearchResponse(
		items=[DictionarySearchItemResponse.from_entity(x) for x in items],
		total=total,
		page=page,
		limit=limit,
		has_next=(page * limit) < total,
	)


@router.get("/{entry_type}/{item_id}", response_model=DictionaryDetailResponse)
async def get_dictionary_detail(
	entry_type: DictionaryEntryType,
	item_id: str,
	svc: MedicalDictionaryService = Depends(get_medical_dictionary_service),
) -> DictionaryDetailResponse:
	try:
		entry = await svc.get_detail(entry_type=entry_type, item_id=item_id)
	except ValueError as exc:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
	return DictionaryDetailResponse.from_entity(entry)
