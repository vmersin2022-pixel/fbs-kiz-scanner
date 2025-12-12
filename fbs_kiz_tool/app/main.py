from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from .services import bind_kiz, process_fbs_qr
from .ui_web import render_order_info
from .api_wb import get_orders_by_supply, get_stickers_for_orders
from .cache import orders_cache

app = FastAPI()

app.mount("/static", StaticFiles(directory="fbs_kiz_tool/app/static"), name="static")
templates = Jinja2Templates(directory="fbs_kiz_tool/app/templates")
@app.get("/")
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/start")
async def start(
    request: Request,
    token: str = Form(...),
    content_token: str = Form(None),  # ← НОВОЕ!
    supply_id: str = Form(...)
):
    orders = await get_orders_by_supply(token, supply_id)
    confirm_orders = orders  # уже отфильтрованы

    orders_cache["orders"] = {o["id"]: o for o in confirm_orders}
    if confirm_orders:
        order_ids = [o["id"] for o in confirm_orders]
        barcode_map = await get_stickers_for_orders(token, order_ids)
        print("BARCODE_MAP:", barcode_map)
        orders_cache["barcode_map"] = barcode_map

    return templates.TemplateResponse("index.html", {
        "request": request,
        "token": token,
        "content_token": content_token,  # ← НОВОЕ!
        "supply_id": supply_id,
        "confirm_count": len(confirm_orders)
    })

@app.post("/scan")
async def scan_input(
    request: Request,
    input_value: str = Form(...),
    token: str = Form(...),
    content_token: str = Form(None),  # ← НОВОЕ!
    supply_id: str = Form(...)
):
    code = input_value.strip()

    # короткий код — стикер WB, длинный — КИЗ
    if len(code) < 20:
        result = await process_fbs_qr(code, token, content_token)  # ← 3 параметра!
    else:
        result = await bind_kiz(token, code, supply_id)

    return templates.TemplateResponse("index.html", {  # ← Заменил render_order_info
        "request": request,
        "token": token,
        "content_token": content_token,  # ← НОВОЕ!
        "supply_id": supply_id,
        "order_info": result  # ← Для Jinja2
    })
