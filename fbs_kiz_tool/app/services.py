# fbs_kiz_tool/app/services.py — ИСПРАВЛЕННЫЙ КОД

from .cache import orders_cache
from .api_wb import get_photo_by_nmid, bind_kiz_real, get_wb_photo_url, get_wb_photo_by_article

async def process_fbs_qr(qr_string: str, token: str, content_token: str = None):
    # ✅ Правильная нормализация для WB стикеров
    scanned_code = qr_string.strip()
    if scanned_code.startswith('*'):
        scanned_code = scanned_code
    else:
        scanned_code = scanned_code.lstrip("*").lstrip("!")  
    
    print(f"Ищем штрихкод: '{scanned_code}'")
    
    barcode_map: dict[str, int] = orders_cache.get("barcode_map", {})
    order_id = barcode_map.get(scanned_code)  # ← order_id ОПРЕДЁЛЁН ЗДЕСЬ!
    
    if not order_id:
        available = [k for k in barcode_map.keys() if 'Cq7KpbsX' in k]
        print(f"Доступные с Cq7KpbsX: {available}")
        return {"error": f"Штрихкод '{scanned_code}' не найден. Длина: {len(scanned_code)}"}
    
    order_data = orders_cache.get("orders", {}).get(order_id)  # ← order_id ИСПОЛЬЗУЕТСЯ ЗДЕСЬ!
    if not order_data:
        return {"error": f"Заказ {order_id} не найден в кеше"}

    orders_cache["current"] = {
        "order_id": order_id,
        "data": order_data
    }

    # ✅ FBS article → Content API
    nm_id = order_data.get("nmId")
    article = order_data.get("article") or order_data.get("vendorCode")
    print(f"🔍 FBS: nmId={nm_id}, article='{article}'")
    
    photo = None
    if nm_id and article:
        photo_token = content_token or token
        photo = await get_wb_photo_by_article(article, nm_id, photo_token)
    print(f"🔍 ОТДАЕМ В HTML: nmId={nm_id}, photo='{photo}' (длина={len(photo) if photo else 0})")
    
    return {
        "success": f"✅ Заказ {order_id} отсканирован",
        "order_id": order_id,
        "article": article,
        "nmId": nm_id,
        "barcode": scanned_code,
        "photo": photo
    }

async def bind_kiz(token: str, kiz: str, supply_id: str) -> dict:
    current = orders_cache.get("current")
    if not current:
        return {"error": "Сначала отсканируйте стикер"}

    order_id = current["order_id"]
    return await bind_kiz_real(token, kiz, order_id)
