from fastapi.templating import Jinja2Templates
from fastapi import Request

templates = Jinja2Templates(directory="app/templates")

def render_order_info(request: Request, order_data: dict, token: str, supply_id: str):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "token": token,
        "supply_id": supply_id,
        "confirm_count": 0,
        "order_info": order_data
    })
