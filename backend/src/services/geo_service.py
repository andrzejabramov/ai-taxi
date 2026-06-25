import httpx
import re
from loguru import logger

from src.settings import settings
from src.middleware.request_id import request_id_ctx
from src.exceptions.base import ValidationError

# === 2GIS endpoints ===
DGIS_GEOCODING = "https://catalog-maps.dgis.ru/1.0/items"
DGIS_ROUTING = "https://routing.api.2gis.com/carrouting/6.0.0/global"

# === OpenStreetMap fallback ===
OSM_NOMINATIM = "https://nominatim.openstreetmap.org/search"
OSM_ROUTING = "https://router.project-osrm.org/route/v1/driving"

# === Yandex Geocoder ===
YANDEX_GEOCODER = "https://geocode-maps.yandex.ru/1.x/"


def simplify_address(address: str) -> str:
    """
    Упрощает адрес для лучшего поиска в Nominatim.
    Убирает слова: "посёлок", "улица", "дом" и их сокращения.
    """
    # Слова, которые ломают поиск
    words_to_remove = [
        "посёлок",
        "пос.",
        "пос ",
        "улица",
        "ул.",
        "ул ",
        "дом",
        "д.",
        "д ",
        "корпус",
        "к.",
        "к ",
        "строение",
        "стр.",
        "стр ",
    ]

    result = address.lower()
    for word in words_to_remove:
        result = result.replace(word, "")

    # Убираем лишние пробелы и запятые
    result = re.sub(r"\s+", " ", result)
    result = result.replace(" ,", ",").replace(", ", ",").strip()

    return result


async def geocode_address(address: str) -> dict:
    """
    Геокодинг: адрес → координаты.
    Приоритет:
    1. Yandex Geocoder (если есть ключ)
    2. OSM Nominatim (fallback с предобработкой)
    """
    request_id = request_id_ctx.get()

    if settings.use_yandex_geocoder:
        logger.info(
            "🗺 Geocoding address",
            extra={"request_id": request_id, "address": address, "provider": "yandex"},
        )
        return await _geocode_yandex(address, request_id)
    else:
        logger.info(
            "🗺 Geocoding address",
            extra={
                "request_id": request_id,
                "address": address,
                "provider": "osm-nominatim",
            },
        )
        return await _geocode_osm(address, request_id)


async def _geocode_yandex(address: str, request_id: str) -> dict:
    """Геокодинг через Yandex Geocoder API"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                YANDEX_GEOCODER,
                params={
                    "apikey": settings.YANDEX_GEOCODER_API_KEY,
                    "geocode": address,
                    "format": "json",
                    "results": 1,
                },
            )
            response.raise_for_status()
            data = response.json()

        features = (
            data.get("response", {})
            .get("GeoObjectCollection", {})
            .get("featureMember", [])
        )
        if not features:
            raise ValidationError("Адрес не найден", {"address": address})

        geo = features[0]["GeoObject"]
        coords = geo["Point"]["pos"].split()  # "lon lat"
        name = geo["metaDataProperty"]["GeocoderMetaData"]["text"]

        result = {
            "lat": float(coords[1]),
            "lon": float(coords[0]),
            "name": name,
        }

        logger.info(
            "✅ Address geocoded (Yandex)",
            extra={
                "request_id": request_id,
                "lat": result["lat"],
                "lon": result["lon"],
            },
        )
        return result

    except httpx.HTTPStatusError as e:
        logger.error(
            "❌ Yandex geocoding HTTP error",
            extra={"request_id": request_id, "status_code": e.response.status_code},
        )
        raise ValidationError(
            "Ошибка геокодинга Yandex", {"status_code": e.response.status_code}
        )
    except ValidationError:
        raise
    except Exception as e:
        logger.error(
            "❌ Yandex geocoding failed",
            extra={"request_id": request_id, "error": str(e)},
        )
        raise ValidationError("Не удалось найти адрес", {"error": str(e)})


async def _geocode_osm(address: str, request_id: str) -> dict:
    """Геокодинг через Nominatim (OpenStreetMap) с предобработкой"""
    try:
        # Предобрабатываем адрес
        simplified = simplify_address(address)

        logger.debug(
            "🔧 Address simplified",
            extra={
                "request_id": request_id,
                "original": address,
                "simplified": simplified,
            },
        )

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                OSM_NOMINATIM,
                params={
                    "q": simplified,
                    "format": "json",
                    "limit": 3,
                    "countrycodes": "ru",
                    "accept-language": "ru",
                    "addressdetails": 1,
                },
                headers={"User-Agent": "TaxiAgent/1.0 (educational project)"},
            )
            response.raise_for_status()
            data = response.json()

        if not data:
            raise ValidationError("Адрес не найден", {"address": address})

        item = data[0]
        result = {
            "lat": float(item["lat"]),
            "lon": float(item["lon"]),
            "name": item.get("display_name", address),
        }

        logger.info(
            "✅ Address geocoded (OSM)",
            extra={
                "request_id": request_id,
                "lat": result["lat"],
                "lon": result["lon"],
                "name": result["name"][:80],
                "variants_found": len(data),
            },
        )
        return result

    except httpx.HTTPStatusError as e:
        logger.error(
            "❌ OSM geocoding HTTP error",
            extra={"request_id": request_id, "status_code": e.response.status_code},
        )
        raise ValidationError(
            "Ошибка геокодинга OSM", {"status_code": e.response.status_code}
        )
    except ValidationError:
        raise
    except Exception as e:
        logger.error(
            "❌ OSM geocoding failed", extra={"request_id": request_id, "error": str(e)}
        )
        raise ValidationError("Не удалось найти адрес", {"error": str(e)})


async def build_route(start: tuple[float, float], end: tuple[float, float]) -> dict:
    """
    Построение маршрута по дорогам.
    - Если есть DGIS_API_KEY → 2GIS Routing API (POST с JSON)
    - Иначе → OSRM (OpenStreetMap, бесплатно, без ключа)
    """
    request_id = request_id_ctx.get()

    provider = "2gis" if settings.use_2gis else "osrm"
    logger.info(
        "🛣 Building route",
        extra={
            "request_id": request_id,
            "start": start,
            "end": end,
            "provider": provider,
        },
    )

    if settings.use_2gis:
        return await _route_2gis(start, end, request_id)
    else:
        return await _route_osrm(start, end, request_id)


async def _route_2gis(
    start: tuple[float, float], end: tuple[float, float], request_id: str
) -> dict:
    """Маршрут через 2GIS Routing API (POST с JSON)"""
    payload = {
        "points": [{"lat": start[0], "lon": start[1]}, {"lat": end[0], "lon": end[1]}],
        "format": "geojson",
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                DGIS_ROUTING,
                params={"key": settings.DGIS_API_KEY},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        result = data.get("result", [])
        if not result:
            raise ValidationError("Маршрут не построен", {"start": start, "end": end})

        route = result[0]

        # Собираем геометрию из всех частей маршрута
        path = []

        # 1. begin_pedestrian_path
        begin_path = route.get("begin_pedestrian_path", {})
        begin_geom = begin_path.get("geometry", {}).get("selection", "")
        path.extend(_parse_linestring(begin_geom))

        # 2. maneuvers[].outcoming_path.geometry[].selection
        for maneuver in route.get("maneuvers", []):
            outcoming = maneuver.get("outcoming_path", {})
            for geom in outcoming.get("geometry", []):
                selection = geom.get("selection", "")
                path.extend(_parse_linestring(selection))

        # 3. end_pedestrian_path
        end_path = route.get("end_pedestrian_path", {})
        end_geom = end_path.get("geometry", {}).get("selection", "")
        path.extend(_parse_linestring(end_geom))

        # Убираем дубликаты
        if path:
            unique_path = [path[0]]
            for point in path[1:]:
                if point != unique_path[-1]:
                    unique_path.append(point)
            path = unique_path

        # Извлекаем distance и duration
        distance_m = int(route.get("total_distance", 0))
        duration_s = int(route.get("total_duration", 0))

        result_data = {
            "geometry": path,
            "distance_m": distance_m,
            "duration_s": duration_s,
        }

        logger.info(
            "✅ Route built (2GIS)",
            extra={
                "request_id": request_id,
                "distance_m": result_data["distance_m"],
                "duration_s": result_data["duration_s"],
                "points_count": len(path),
            },
        )
        return result_data

    except httpx.HTTPStatusError as e:
        logger.error(
            "❌ 2GIS routing HTTP error",
            extra={
                "request_id": request_id,
                "status_code": e.response.status_code,
                "response": e.response.text[:200],
            },
        )
        raise ValidationError(
            "Ошибка построения маршрута 2GIS", {"status_code": e.response.status_code}
        )
    except ValidationError:
        raise
    except Exception as e:
        logger.error(
            "❌ 2GIS routing failed", extra={"request_id": request_id, "error": str(e)}
        )
        raise ValidationError("Не удалось построить маршрут", {"error": str(e)})


async def _route_osrm(
    start: tuple[float, float], end: tuple[float, float], request_id: str
) -> dict:
    """Маршрут через OSRM (OpenStreetMap)"""
    coords = f"{start[1]},{start[0]};{end[1]},{end[0]}"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{OSM_ROUTING}/{coords}",
                params={
                    "overview": "full",
                    "geometries": "geojson",
                },
            )
            response.raise_for_status()
            data = response.json()

        if data.get("code") != "Ok" or not data.get("routes"):
            raise ValidationError(
                "Маршрут не построен",
                {"start": start, "end": end, "osrm_code": data.get("code")},
            )

        route = data["routes"][0]
        coords_list = route["geometry"]["coordinates"]
        path = [[c[1], c[0]] for c in coords_list]

        result = {
            "geometry": path,
            "distance_m": int(route.get("distance", 0)),
            "duration_s": int(route.get("duration", 0)),
        }

        logger.info(
            "✅ Route built (OSRM)",
            extra={
                "request_id": request_id,
                "distance_m": result["distance_m"],
                "duration_s": result["duration_s"],
            },
        )
        return result

    except httpx.HTTPStatusError as e:
        logger.error(
            "❌ OSRM routing HTTP error",
            extra={
                "request_id": request_id,
                "status_code": e.response.status_code,
                "response": e.response.text[:200],
            },
        )
        raise ValidationError(
            "Ошибка построения маршрута OSRM", {"status_code": e.response.status_code}
        )
    except ValidationError:
        raise
    except Exception as e:
        logger.error(
            "❌ OSRM routing failed", extra={"request_id": request_id, "error": str(e)}
        )
        raise ValidationError("Не удалось построить маршрут", {"error": str(e)})


def _parse_linestring(linestring: str) -> list[list[float]]:
    """
    Парсит LINESTRING(lon1 lat1, lon2 lat2, ...) → [[lat, lon], ...]
    """
    if not linestring or not linestring.startswith("LINESTRING("):
        return []

    coords_str = linestring.replace("LINESTRING(", "").replace(")", "")
    coords = []
    for point in coords_str.split(","):
        parts = point.strip().split()
        if len(parts) == 2:
            lon, lat = float(parts[0]), float(parts[1])
            coords.append([lat, lon])
    return coords
