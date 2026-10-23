from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from foodie_api.dependencies import get_repository
from foodie_api.repository import Repository
from foodie_api.schemas import CityDetail, CityList, CountryList

router = APIRouter(prefix="/api/v1", tags=["places"])


@router.get("/countries", response_model=CountryList)
def list_countries(repository: Annotated[Repository, Depends(get_repository)]) -> CountryList:
    """Countries that have at least one city with restaurants."""
    return CountryList(items=repository.countries())


@router.get("/cities", response_model=CityList)
def list_cities(
    repository: Annotated[Repository, Depends(get_repository)],
    country: Annotated[
        str | None, Query(pattern=r"^[A-Za-z]{2}$", description="ISO 3166-1 alpha-2 country code, e.g. PT")
    ] = None,
    q: Annotated[
        str | None,
        Query(
            min_length=1, max_length=100, description="Name search; also matches local names (Lisboa, Oporto)"
        ),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> CityList:
    """Cities with restaurants, for the city selector and autocomplete."""
    return CityList(items=repository.cities(country, q.strip() if q else None, limit))


@router.get(
    "/cities/{city_id}", response_model=CityDetail, responses={404: {"description": "City not found"}}
)
def get_city(
    repository: Annotated[Repository, Depends(get_repository)],
    city_id: Annotated[int, Path(ge=1, description="GeoNames geonameid")],
) -> CityDetail:
    city = repository.city(city_id)
    if city is None:
        raise HTTPException(status_code=404, detail=f"city {city_id} not found")
    return city
