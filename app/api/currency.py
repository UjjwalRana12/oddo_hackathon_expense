from fastapi import APIRouter, Depends
from ..services.currency_service import currency_service

router = APIRouter()

@router.get("/countries")
async def get_countries_and_currencies():
    """
    Get all countries and their currencies
    """
    try:
        countries_data = await currency_service.get_countries_and_currencies()
        return {
            "success": True,
            "data": countries_data
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/convert")
async def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str
):
    """
    Convert amount from one currency to another
    """
    try:
        converted_amount = await currency_service.convert_currency(
            amount, from_currency, to_currency
        )
        
        if converted_amount is None:
            return {
                "success": False,
                "error": "Could not convert currency"
            }
        
        exchange_rate = await currency_service.get_exchange_rate(
            from_currency, to_currency
        )
        
        return {
            "success": True,
            "data": {
                "from_currency": from_currency,
                "to_currency": to_currency,
                "amount": amount,
                "converted_amount": converted_amount,
                "exchange_rate": exchange_rate
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }