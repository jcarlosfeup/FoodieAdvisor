from foodie_collector.ingestion.raw_loader import OSM_RESTAURANTS, classify, deduplicate, payload_hash


def restaurant(osm_id, name="Tasca", lat=41.1):
    return {"osm_type": "node", "osm_id": osm_id, "latitude": lat, "longitude": -8.6, "tags": {"name": name}}


def hashed(record):
    return {**record, "_payload_hash": payload_hash(record, OSM_RESTAURANTS.fields)}


def test_payload_hash_ignores_key_order_and_metadata():
    a = {"osm_type": "node", "osm_id": 1, "latitude": 1.0, "longitude": 2.0, "tags": {"a": "1", "b": "2"}}
    b = {"tags": {"b": "2", "a": "1"}, "longitude": 2.0, "latitude": 1.0, "osm_id": 1, "osm_type": "node"}
    assert payload_hash(a, OSM_RESTAURANTS.fields) == payload_hash(
        {**b, "_run_id": "x"}, OSM_RESTAURANTS.fields
    )


def test_payload_hash_changes_when_tags_change():
    assert payload_hash(restaurant(1), OSM_RESTAURANTS.fields) != payload_hash(
        restaurant(1, name="Tasca Nova"), OSM_RESTAURANTS.fields
    )


def test_classify_splits_new_changed_and_unchanged():
    stored = {("node", 1): hashed(restaurant(1))["_payload_hash"], ("node", 2): "old-hash"}
    records = [hashed(restaurant(1)), hashed(restaurant(2)), hashed(restaurant(3))]

    new, changed, unchanged = classify(OSM_RESTAURANTS, records, stored)

    assert [r["osm_id"] for r in new] == [3]
    assert [r["osm_id"] for r in changed] == [2]
    assert unchanged == [("node", 1)]


def test_deduplicate_keeps_first_and_rejects_repeats():
    unique, rejections = deduplicate(
        OSM_RESTAURANTS, [restaurant(1), restaurant(1, name="Dup"), restaurant(2)]
    )
    assert [r["tags"]["name"] for r in unique] == ["Tasca", "Tasca"]
    assert [(r.source_record_id, r.reason) for r in rejections] == [("node/1", "duplicate_in_batch")]
