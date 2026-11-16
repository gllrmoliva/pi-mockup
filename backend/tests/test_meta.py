from httpx import AsyncClient


async def test_meta(client: AsyncClient) -> None:
    response = await client.get("/api/v1/meta")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Hito"
    assert body["version"] == "0.1.0"
    assert body["environment"] == "test"
