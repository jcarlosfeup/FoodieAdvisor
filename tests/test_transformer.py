from api.transformer import transform_places


def test_transform_places_flattens_google_response_and_keeps_place_id():
    result = transform_places(
        [{
            "id": "places/abc",
            "displayName": {"text": "Cafe"},
            "rating": 4.6,
            "userRatingCount": 12,
            "priceLevel": "PRICE_LEVEL_MODERATE",
            "location": {"latitude": 41.1, "longitude": -8.6},
        }],
        "Porto",
    )
    assert result == [{
        "google_place_id": "places/abc", "name": "Cafe", "city": "Porto",
        "rating": 4.6, "ratings_count": 12, "price_level": "PRICE_LEVEL_MODERATE",
        "latitude": 41.1, "longitude": -8.6,
    }]


def test_transform_places_skips_places_without_names():
    assert transform_places([{"id": "places/missing-name"}], "Porto") == []