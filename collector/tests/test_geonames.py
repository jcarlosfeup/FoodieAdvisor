import zipfile

import httpx

from foodie_collector.sources.geonames import GeoNamesDownloader, parse_cities, parse_countries

PORTO = (
    "2735943\tPorto\tPorto\tOporto,Porto\t41.14961\t-8.61099\tP\tPPLA\tPT\t\t17\t1312\t131210\t\t"
    "249633\t\t94\tEurope/Lisbon\t2024-05-14"
)
PORTO_ALEGRE = (
    "3452925\tPorto Alegre\tPorto Alegre\t\t-30.03283\t-51.23019\tP\tPPLA\tBR\t\t23\t4314902\t\t\t"
    "1488252\t\t46\tAmerica/Sao_Paulo\t2023-01-01"
)
COUNTRY_INFO = [
    "# GeoNames country info",
    "#ISO\tISO3\tISO-Numeric\tfips\tCountry\tCapital\tArea(in sq km)\tPopulation\tContinent\ttld\t"
    "CurrencyCode\tCurrencyName\tPhone\tPostal Code Format\tPostal Code Regex\tLanguages\tgeonameid\t"
    "neighbours\tEquivalentFipsCode",
    "PT\tPRT\t620\tPO\tPortugal\tLisbon\t92391.0\t10281762\tEU\t.pt\tEUR\tEuro\t351\t####-###\t"
    "^(\\d{7})$\tpt-PT,mwl\t2264397\tES\t",
]


def test_parse_cities_types_all_columns_and_distinguishes_same_names():
    result = parse_cities([PORTO, PORTO_ALEGRE])

    porto, porto_alegre = result.records
    assert porto["geonameid"] == 2735943
    assert porto["country_code"] == "PT"
    assert porto["population"] == 249633
    assert porto["elevation"] is None
    assert porto["modification_date"].isoformat() == "2024-05-14"
    assert porto_alegre["country_code"] == "BR"
    assert result.rejections == []


def test_parse_cities_rejects_bad_rows_without_stopping():
    bad_latitude = PORTO.replace("41.14961", "north", 1)
    short_row = "123\tNowhere"
    result = parse_cities([bad_latitude, short_row, PORTO_ALEGRE, ""])

    assert [r["geonameid"] for r in result.records] == [3452925]
    assert [r.reason.split(":")[0] for r in result.rejections] == ["invalid_value", "unexpected_column_count"]


def test_parse_cities_keeps_quote_characters_in_names():
    quoted = PORTO.replace("\tPorto\tPorto\t", '\t"Porto"\t"Porto"\t', 1)
    assert parse_cities([quoted]).records[0]["name"] == '"Porto"'


def test_parse_countries_skips_comments_and_maps_columns():
    result = parse_countries(COUNTRY_INFO)

    [portugal] = result.records
    assert portugal["iso_alpha2"] == "PT"
    assert portugal["name"] == "Portugal"
    assert portugal["neighbours"] == "ES"
    assert portugal["geonameid"] == 2264397


def test_downloader_caches_files_and_reads_zipped_cities(tmp_path):
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("cities5000.txt", PORTO + "\n")
    requests = []

    def handler(request):
        requests.append(request.url.path)
        return httpx.Response(200, content=archive.read_bytes())

    downloader = GeoNamesDownloader(
        httpx.Client(transport=httpx.MockTransport(handler)),
        "https://geonames.test/dump/",
        tmp_path / "cache",
        max_attempts=1,
        backoff_seconds=0,
    )

    assert downloader.cities("cities5000") == [PORTO]
    assert downloader.cities("cities5000") == [PORTO]
    assert requests == ["/dump/cities5000.zip"]

    downloader.cities("cities5000", refresh=True)
    assert len(requests) == 2
