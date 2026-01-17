import aiohttp
import os


async def get_temperature(city: str) -> float | None:
    api_key = os.getenv("WEATHER_API_KEY")
    if not api_key or not city:
        return None

    url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": api_key,
        "units": "metric",
        "lang": "ru",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return round(data["main"]["temp"], 1)
                else:
                    return None
    except Exception:
        return None
