"""Application service coordinating Google collection and persistence."""

from api.transformer import transform_places


class RestaurantCollectionService:
    def __init__(self, places_client, restaurant_repository):
        self.places_client = places_client
        self.restaurant_repository = restaurant_repository

    def collect(self, city_name: str, country_name: str | None = None) -> list[dict]:
        location = city_name if not country_name else f"{city_name}, {country_name}"

        cuisine = f"{country_name} traditional" if country_name else "local"

        raw_places = self.places_client.search_restaurants(f"{cuisine} restaurants in {location}")

        restaurants = transform_places(raw_places, city_name)

        self.restaurant_repository.save_restaurants(restaurants)
        return restaurants