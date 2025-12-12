import httpx
from typing import List
from fastapi import HTTPException

BASE_URL = "https://marketplace-api.wildberries.ru/api/v3"

async def get_orders_by_supply(token: str, supply_id: str) -> List[dict]:
    url = f"{BASE_URL}/orders"
    headers = {"Authorization": token}

    limit = 1000
    next_val = 0
    result: List[dict] = []

    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            params = {
                "limit": limit,
                "next": next_val,
            }
            resp = await client.get(url, headers=headers, params=params)

            if resp.status_code >= 400:
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"WB /orders error: {resp.text}",
                )

            data = resp.json()
            orders = data.get("orders", [])
            result.extend(o for o in orders if o.get("supplyId") == supply_id)

            next_val = data.get("next")
            if not next_val:
                break

    return result

async def get_stickers_for_orders(token: str, order_ids: list[int]) -> dict[str, int]:
    url = f"{BASE_URL}/orders/stickers"
    headers = {"Authorization": token}
    params = {
        "type": "png",
        "width": 58,
        "height": 40,
    }
    payload = {
        "orders": order_ids,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, headers=headers, params=params, json=payload)

    if resp.status_code >= 400:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"WB /orders/stickers error: {resp.text}",
        )

    data = resp.json()
    stickers = data.get("stickers", [])
    for s in stickers:
        print("WB STICKER:", repr(s["barcode"]))
    return {s["barcode"]: s["orderId"] for s in stickers}

async def get_photo_by_nmid(token: str, nm_ids: List[int]) -> dict:
    url = "https://suppliers-api.wildberries.ru/content/v1/cards/cursor/list"
    headers = {"Authorization": token}
    payload = {
        "filter": {"nmID": nm_ids},
        "sort": {"cursor": {"limit": 1}}
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)

    response.raise_for_status()
    return response.json()

async def bind_kiz_real(token: str, kiz_code: str, order_id: int) -> dict:
    url = f"{BASE_URL}/orders/{order_id}/meta/sgtin"
    headers = {"Authorization": token}
    payload = {"sgtins": [kiz_code[:44]]}

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.put(url, headers=headers, json=payload)

    if response.status_code == 204:
        return {"success": f"✅ КИЗ {kiz_code[:20]}... привязан к заказу {order_id}"}
    elif response.status_code == 400:
        return {"error": f"❌ Неверный КИЗ формат: {response.text[:100]}"}
    else:
        return {"error": f"Ошибка {response.status_code}: {response.text[:200]}"}

async def attach_sgtin(token: str, order_id: int, code: str) -> None:
    url = f"{BASE_URL}/orders/{order_id}/meta/sgtin"
    headers = {"Authorization": token}
    payload = {"sgtins": [code]}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.put(url, headers=headers, json=payload)

    if resp.status_code >= 400:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"WB /orders/{order_id}/meta/sgtin error: {resp.text}",
        )

def get_wb_photo_url(nm_id: int) -> str:
    if not nm_id:
        return ""
    
    vol = nm_id // 100000
    part = nm_id // 1000
    
    if vol <= 143:
        host = "basket-01.wb.ru"
    elif vol <= 287:
        host = "basket-02.wb.ru"
    elif vol <= 431:
        host = "basket-03.wb.ru"
    elif vol <= 719:
        host = "basket-04.wb.ru"
    elif vol <= 1007:
        host = "basket-05.wb.ru"
    elif vol <= 1061:
        host = "basket-06.wb.ru"
    elif vol <= 1115:
        host = "basket-07.wb.ru"
    elif vol <= 1169:
        host = "basket-08.wb.ru"
    elif vol <= 1313:
        host = "basket-09.wb.ru"
    elif vol <= 1601:
        host = "basket-10.wb.ru"
    else:
        host = "basket-11.wb.ru"
    
    return f"https://{host}/vol{vol:03d}/part{part:03d}/{nm_id}/images/big/1.webp"

async def get_wb_photo_by_article(article: str, nm_id: str, content_token: str):
    """✅ ИЩЕМ среди ВСЕХ 500 ваших карточек по vendorCode!"""
    nm_id_str = str(nm_id)
    
    url = "https://content-api.wildberries.ru/content/v2/get/cards/list"
    payload = {
        "settings": {
            "filter": {
                "vendorCode": article,
                "withPhoto": -1
            },
            "cursor": {"limit": 500}  # ← МАКСИМУМ!
        }
    }
    
    try:
        print(f"🎯 Content API: vendorCode='{article}' (limit=500)")
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload, headers={"Authorization": f"Bearer {content_token}"})
            data = resp.json()
            
            cards_count = len(data.get("cards", []))
            print(f"🔍 Найдено {cards_count} ваших карточек с '{article}'")
            
            # ✅ ИЩЕМ НАШ nmId среди ВСЕХ 500!
            for i, card in enumerate(data.get("cards", [])):
                card_nm = str(card.get("nmID", ""))
                card_vendor = card.get("vendorCode", "")
                
                if i < 5 or i > cards_count - 5:  # Первые/последние
                    print(f"  {i+1:3d}. nmID={card_nm}, vendor='{card_vendor}'")
                
                if card_nm == nm_id_str:
                    photos = card.get("photos", [])
                    if photos and photos[0].get("big"):
                        photo_url = photos[0]["big"]
                        print(f"✅ НАЙДЕН НА позиции {i+1}: {photo_url}")
                        return photo_url
            
            print(f"❌ nmId={nm_id_str} не найден в {cards_count} карточках")
            
    except Exception as e:
        print(f"❌ Content API: {e}")
    
    print("🔗 PLACEHOLDER")
    return f"https://via.placeholder.com/150x150/2563eb/ffffff?text=WB{nm_id_str[:6]}"
