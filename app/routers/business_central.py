from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from typing import Optional, Dict, List
import logging
from ..services.business_central_service import bc_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/business-central", tags=["Business Central"])

@router.get("/health")
async def health_check():
    """Verifica se o serviço está funcionando"""
    try:
        # Verificar se está configurado
        if not bc_service.is_configured:
            return {
                "status": "not_configured",
                "message": "Business Central service is not configured. Please set BC_AZURE_* environment variables.",
                "configured": False
            }
        
        # Tentar obter um token para verificar a conectividade
        token = bc_service._get_access_token()
        return {
            "status": "healthy",
            "message": "Business Central service is operational",
            "environment": bc_service.environment_name,
            "configured": True
        }
    except Exception as e:
        logger.error(f"Business Central health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Business Central service unavailable: {str(e)}")

@router.get("/dashboard/summary")
async def get_dashboard_summary():
    """Obtém resumo dos dados para a dashboard - usa endpoints oficiais se token delegado disponível"""
    try:
        # Usar token delegado se disponível
        delegated_token = getattr(bc_service, 'delegated_token', None)
        summary = bc_service.get_dashboard_summary(delegated_token=delegated_token)
        return summary
    except Exception as e:
        logger.error(f"Failed to get dashboard summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard data: {str(e)}")

@router.get("/customers")
async def get_customers(
    limit: int = Query(10000, ge=1, le=50000),
    offset: int = Query(0, ge=0)
):
    """Obtém lista de clientes com paginação - usa endpoints oficiais se token delegado disponível"""
    try:
        # Usar token delegado se disponível
        delegated_token = getattr(bc_service, 'delegated_token', None)
        customers = bc_service.get_customer_overview_paginated(limit, offset, delegated_token=delegated_token)
        total_count = bc_service.get_customer_count(delegated_token=delegated_token)
        return {
            "customers": customers, 
            "count": len(customers),
            "total_count": total_count,
            "has_more": (offset + limit) < total_count,
            "next_offset": offset + limit if (offset + limit) < total_count else None
        }
    except Exception as e:
        logger.error(f"Failed to get customers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get customers: {str(e)}")

@router.get("/sales-orders")
async def get_sales_orders(limit: int = Query(10000, ge=1, le=50000)):
    """Obtém encomendas de venda por vendedor"""
    try:
        orders = bc_service.get_sales_orders_by_person(limit)
        return {"orders": orders, "count": len(orders)}
    except Exception as e:
        logger.error(f"Failed to get sales orders: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get sales orders: {str(e)}")

@router.get("/sales")
async def get_sales(
    limit: int = Query(10000, ge=1, le=50000),
    offset: int = Query(0, ge=0)
):
    """Obtém lista de vendas com paginação - usa endpoints oficiais se token delegado disponível"""
    try:
        # Usar token delegado se disponível
        delegated_token = getattr(bc_service, 'delegated_token', None)
        sales = bc_service.get_sales_list_paginated(limit, offset, delegated_token=delegated_token)
        total_count = bc_service.get_sales_count(delegated_token=delegated_token)
        return {
            "sales": sales, 
            "count": len(sales),
            "total_count": total_count,
            "has_more": (offset + limit) < total_count,
            "next_offset": offset + limit if (offset + limit) < total_count else None
        }
    except Exception as e:
        logger.error(f"Failed to get sales: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get sales: {str(e)}")

@router.get("/purchases")
async def get_purchases(
    limit: int = Query(10000, ge=1, le=50000),
    offset: int = Query(0, ge=0)
):
    """Obtém lista de compras com paginação usando endpoints oficiais"""
    try:
        # Usar token delegado se disponível
        delegated_token = getattr(bc_service, 'delegated_token', None)
        purchases = bc_service.get_purchase_list_paginated(limit, offset, delegated_token)
        total_count = bc_service.get_purchase_count(delegated_token)
        return {
            "purchases": purchases, 
            "count": len(purchases),
            "total_count": total_count,
            "has_more": (offset + limit) < total_count,
            "next_offset": offset + limit if (offset + limit) < total_count else None
        }
    except Exception as e:
        logger.error(f"Failed to get purchases: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get purchases: {str(e)}")

@router.get("/bank-entries")
async def get_bank_entries(limit: int = Query(10000, ge=1, le=50000)):
    """Obtém lançamentos bancários"""
    try:
        entries = bc_service.get_bank_ledger_entries(limit)
        return {"entries": entries, "count": len(entries)}
    except Exception as e:
        logger.error(f"Failed to get bank entries: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get bank entries: {str(e)}")

@router.get("/vessel-movements")
async def get_vessel_movements(limit: int = Query(10000, ge=1, le=50000)):
    """Obtém dados de movimento de navios"""
    try:
        movements = bc_service.get_vessel_movement_data(limit)
        return {"movements": movements, "count": len(movements)}
    except Exception as e:
        logger.error(f"Failed to get vessel movements: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get vessel movements: {str(e)}")

@router.get("/shipments")
async def get_shipments(
    limit: int = Query(10000, ge=1, le=50000),
    offset: int = Query(0, ge=0)
):
    """Obtém lista completa de shipments com paginação - usa endpoints oficiais se token delegado disponível"""
    try:
        # Usar token delegado se disponível
        delegated_token = getattr(bc_service, 'delegated_token', None)
        shipments = bc_service.get_shipments_list_paginated(limit, offset, delegated_token=delegated_token)
        total_count = bc_service.get_shipments_count(delegated_token=delegated_token)
        return {
            "shipments": shipments, 
            "count": len(shipments),
            "total_count": total_count,
            "has_more": (offset + limit) < total_count,
            "next_offset": offset + limit if (offset + limit) < total_count else None
        }
    except Exception as e:
        logger.error(f"Failed to get shipments: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get shipments: {str(e)}")

@router.get("/shipments/stats")
async def get_shipments_stats():
    """Obtém estatísticas resumidas dos shipments"""
    try:
        stats = bc_service.get_shipments_summary_stats()
        return {"stats": stats}
    except Exception as e:
        logger.error(f"Failed to get shipments stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get shipments stats: {str(e)}")

@router.get("/shipments/by-vessel/{vessel_name}")
async def get_shipments_by_vessel(vessel_name: str, limit: int = Query(10000, ge=1, le=50000)):
    """Obtém shipments filtrados por nome do navio"""
    try:
        shipments = bc_service.get_shipments_by_vessel(vessel_name, limit)
        return {"shipments": shipments, "count": len(shipments), "vessel_name": vessel_name}
    except Exception as e:
        logger.error(f"Failed to get shipments by vessel {vessel_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get shipments by vessel: {str(e)}")

@router.get("/shipments/by-status/{status}")
async def get_shipments_by_status(status: str, limit: int = Query(10000, ge=1, le=50000)):
    """Obtém shipments filtrados por status"""
    try:
        shipments = bc_service.get_shipments_by_status(status, limit)
        return {"shipments": shipments, "count": len(shipments), "status": status}
    except Exception as e:
        logger.error(f"Failed to get shipments by status {status}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get shipments by status: {str(e)}")

@router.get("/shipments/by-port/{port}")
async def get_shipments_by_port(port: str, limit: int = Query(10000, ge=1, le=50000)):
    """Obtém shipments filtrados por porto"""
    try:
        shipments = bc_service.get_shipments_by_port(port, limit)
        return {"shipments": shipments, "count": len(shipments), "port": port}
    except Exception as e:
        logger.error(f"Failed to get shipments by port {port}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get shipments by port: {str(e)}")

@router.get("/shipments/{shipment_no}")
async def get_shipment_details(shipment_no: str):
    """Obtém detalhes de um shipment específico"""
    try:
        shipment = bc_service.get_shipment_details(shipment_no)
        if not shipment:
            raise HTTPException(status_code=404, detail=f"Shipment {shipment_no} not found")
        return {"shipment": shipment}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get shipment details for {shipment_no}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get shipment details: {str(e)}")

@router.get("/entities")
async def list_available_entities():
    """Lista todas as entidades disponíveis"""
    try:
        # Obter lista de entidades do root da API
        entities_url = f"{bc_service.base_url}/api/v2.0"
        headers = {
            'Authorization': f'Bearer {bc_service._get_access_token()}',
            'Accept': 'application/json'
        }
        
        import requests
        response = requests.get(entities_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        entities = data.get('value', [])
        
        return {
            "entities": [entity.get('name', 'Unknown') for entity in entities],
            "count": len(entities)
        }
    except Exception as e:
        logger.error(f"Failed to list entities: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list entities: {str(e)}")

@router.get("/vendors")
async def get_vendors(
    limit: int = Query(10000, ge=1, le=50000),
    offset: int = Query(0, ge=0)
):
    """Get vendor data from Business Central with pagination - uses official endpoints if delegated token available"""
    try:
        # Usar token delegado se disponível
        delegated_token = getattr(bc_service, 'delegated_token', None)
        vendors = bc_service.get_vendor_data_paginated(limit, offset, delegated_token=delegated_token)
        total_count = bc_service.get_vendor_count(delegated_token=delegated_token)
        return {
            "vendors": vendors,
            "count": len(vendors),
            "total_count": total_count,
            "has_more": (offset + limit) < total_count,
            "next_offset": offset + limit if (offset + limit) < total_count else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching vendors: {str(e)}")

@router.get("/ledger")
async def get_ledger(limit: int = Query(2000, ge=1, le=5000)):
    """Get customer ledger data from Business Central"""
    try:
        ledger = bc_service.get_customer_ledger_data(limit)
        return {
            "ledger": ledger,
            "count": len(ledger)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching ledger: {str(e)}")

@router.get("/bank-ledger")
async def get_bank_ledger(limit: int = Query(2000, ge=1, le=5000)):
    """Get bank account ledger entries from Business Central"""
    try:
        entries = bc_service.get_bank_account_ledger_entries(limit)
        return {
            "entries": entries,
            "count": len(entries)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching bank ledger: {str(e)}")

@router.get("/cust-ledger")
async def get_cust_ledger(limit: int = Query(2000, ge=1, le=5000)):
    """Get customer ledger entries (standard entity) from Business Central"""
    try:
        entries = bc_service.get_cust_ledger_entries(limit)
        return {
            "entries": entries,
            "count": len(entries)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching cust ledger: {str(e)}")

@router.get("/vendor-ledger")
async def get_vendor_ledger(limit: int = Query(2000, ge=1, le=5000)):
    """Get vendor ledger entries (standard entity) from Business Central"""
    try:
        entries = bc_service.get_vendor_ledger_entries(limit)
        return {
            "entries": entries,
            "count": len(entries)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching vendor ledger: {str(e)}")

@router.get("/gl-entries")
async def get_gl_entries(
    limit: int = Query(2000, ge=1, le=5000),
    offset: int = Query(0, ge=0)
):
    """Get general ledger entries from Business Central using official endpoints"""
    try:
        # Usar token delegado se disponível
        delegated_token = getattr(bc_service, 'delegated_token', None)
        entries = bc_service.get_financial_entries_paginated(limit, offset, delegated_token)
        total_count = bc_service.get_financial_entries_count(delegated_token)
        return {
            "entries": entries,
            "count": len(entries),
            "total_count": total_count,
            "has_more": (offset + limit) < total_count,
            "next_offset": offset + limit if (offset + limit) < total_count else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching GL entries: {str(e)}")

@router.get("/vessels")
async def get_vessels(
    limit: int = Query(10000, ge=1, le=50000),
    offset: int = Query(0, ge=0)
):
    """Get vessels data using salesShipments endpoint"""
    try:
        # Usar token delegado se disponível
        delegated_token = getattr(bc_service, 'delegated_token', None)
        all_vessels = bc_service.get_unique_vessels(limit + offset, delegated_token)
        vessels = all_vessels[offset:offset + limit]
        total_count = len(all_vessels)
        return {
            "vessels": vessels,
            "count": len(vessels),
            "total_count": total_count,
            "has_more": (offset + limit) < total_count,
            "next_offset": offset + limit if (offset + limit) < total_count else None
        }
    except Exception as e:
        logger.error(f"Failed to get vessels: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get vessels: {str(e)}")

@router.get("/item-ledger")
async def get_item_ledger(limit: int = Query(2000, ge=1, le=5000)):
    """Get item ledger entries from Business Central"""
    try:
        entries = bc_service.get_item_ledger_entries(limit)
        return {
            "entries": entries,
            "count": len(entries)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching item ledger: {str(e)}")

@router.get("/sales-opportunities")
async def get_sales_opportunities(limit: int = Query(2000, ge=1, le=5000)):
    """Get sales opportunities from Business Central"""
    try:
        opportunities = bc_service.get_sales_opportunities(limit)
        return {
            "opportunities": opportunities,
            "count": len(opportunities)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching sales opportunities: {str(e)}")

@router.get("/sales-dashboard")
async def get_sales_dashboard(limit: int = Query(2000, ge=1, le=5000)):
    """Get sales dashboard data from Business Central"""
    try:
        dashboard_data = bc_service.get_sales_dashboard(limit)
        return {
            "dashboard": dashboard_data,
            "count": len(dashboard_data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching sales dashboard: {str(e)}")

@router.get("/vessels-comprehensive")
async def get_comprehensive_vessels(limit: int = Query(5000, ge=1, le=10000)):
    """Get comprehensive vessel data aggregated from multiple BC sources"""
    try:
        vessels = bc_service.get_comprehensive_vessels_data(limit)
        return {
            "vessels": vessels,
            "count": len(vessels)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching comprehensive vessels: {str(e)}")

@router.get("/shipment-list")
async def get_shipment_list(limit: int = Query(1000, ge=1, le=10000)):
    """Get real shipment list data from Business Central Shipment_List entity"""
    try:
        shipments = bc_service.get_real_shipment_list(limit)
        return {
            "shipments": shipments,
            "count": len(shipments)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching real shipment list: {str(e)}")

# Endpoints de autenticação Authorization Code Flow
@router.get("/auth/login")
async def start_auth_flow(request: Request):
    """Inicia o fluxo de autenticação Authorization Code"""
    try:
        # URL de callback baseada no request
        base_url = str(request.base_url).rstrip('/')
        redirect_uri = f"{base_url}/business-central/auth/callback"
        
        auth_url = bc_service.get_auth_url(redirect_uri)
        
        return RedirectResponse(url=auth_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting auth flow: {str(e)}")

@router.get("/auth/callback")
async def auth_callback(code: str, state: str = "12345"):
    """Callback para receber o authorization code e redirecionar para o frontend"""
    try:
        # URL de callback baseada no request (você pode ajustar conforme necessário)
        redirect_uri = "http://localhost:8000/business-central/auth/callback"
        
        # Trocar code por token
        token_data = bc_service.exchange_code_for_token(code, redirect_uri)
        
        # Definir o token delegado no serviço para usar em todas as chamadas
        access_token = token_data.get("access_token")
        if access_token:
            bc_service.set_delegated_token(access_token)
            logger.info("Delegated token set in Business Central service")
        
        # Redirecionar para o frontend com os dados do token
        frontend_url = "http://localhost:3000/dashboard/business-central"
        token_params = f"auth_success=true&token={access_token}&expires_in={token_data.get('expires_in', 3600)}"
        redirect_url = f"{frontend_url}?{token_params}"
        
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except Exception as e:
        logger.error(f"Error in auth callback: {e}")
        # Em caso de erro, redirecionar para o frontend com erro
        frontend_url = "http://localhost:3000/dashboard/business-central"
        error_params = f"auth_error=true&message={str(e)}"
        redirect_url = f"{frontend_url}?{error_params}"
        return RedirectResponse(url=redirect_url, status_code=302)

@router.post("/auth/refresh")
async def refresh_token(refresh_token: str):
    """Refresca o access token usando refresh_token"""
    try:
        # Implementar refresh token logic se necessário
        return {"message": "Refresh token functionality not implemented yet"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing token: {str(e)}")
