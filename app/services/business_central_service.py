import os
import requests
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class BusinessCentralService:
    def __init__(self):
        # Carregar variáveis do arquivo .env
        load_dotenv()
        
        self.tenant_id = os.getenv('AZURE_TENANT_ID')
        self.client_id = os.getenv('AZURE_CLIENT_ID')
        self.client_secret = os.getenv('AZURE_CLIENT_SECRET')
        self.environment_url = os.getenv('AZURE_ENVIRONMENT_URL')
        
        # Verificar se as credenciais estão configuradas
        self.is_configured = all([self.tenant_id, self.client_id, self.client_secret, self.environment_url])
        
        if self.is_configured:
            self.environment_name = self.environment_url.split('/')[-1]
            self.access_token = None
            self.token_expires_at = None
            
            # URLs base
            self.base_url = f"https://api.businesscentral.dynamics.com/v2.0/{self.tenant_id}/{self.environment_name}"
            self.odata_url = f"{self.base_url}/ODataV4"
            self.delegated_token = None  # Token delegado do usuário SUPER
            logger.info("Business Central service configured successfully")
        else:
            self.environment_name = None
            self.access_token = None
            self.token_expires_at = None
            self.base_url = None
            self.odata_url = None
            self.delegated_token = None  # Token delegado do usuário SUPER
            logger.warning("Business Central credentials not configured - service will be unavailable")
        
    def _check_configured(self):
        """Verifica se o serviço está configurado"""
        if not self.is_configured:
            raise ValueError("Business Central service is not configured. Please set AZURE_* environment variables.")
    
    def _ensure_token(self):
        """Garante que temos um token válido"""
        self._get_access_token()
    
    def set_delegated_token(self, token: str):
        """Define o token delegado do usuário SUPER"""
        self.delegated_token = token
        logger.info("Delegated token set - will use SUPER permissions")
    
    def clear_delegated_token(self):
        """Remove o token delegado"""
        self.delegated_token = None
        logger.info("Delegated token cleared - will use app-only permissions")
    
    def _extract_vessel_name(self, description: str) -> str:
        """Extrai o nome do navio da descrição"""
        if not description:
            return 'N/A'
        
        # Procurar padrões como "VESSEL NAME V." ou "VESSEL NAME -"
        import re
        
        # Padrão 1: "EASTERN QUINCE V. 1-AA1058"
        vessel_pattern1 = r'^([A-Z][A-Z\s]+?)\s+V\.\s+\d+'
        match = re.search(vessel_pattern1, description)
        if match:
            return match.group(1).strip()
        
        # Padrão 2: "VESSEL NAME -"
        vessel_pattern2 = r'^([A-Z][A-Z\s]+?)\s*-\s*'
        match = re.search(vessel_pattern2, description)
        if match:
            return match.group(1).strip()
        
        # Se não encontrar padrão, retornar primeira parte até o primeiro hífen
        parts = description.split(' - ')
        if len(parts) > 1:
            return parts[0].strip()
        
        return description[:30] + '...' if len(description) > 30 else description

    def _extract_vessel_type(self, description: str) -> str:
        """Extrai o tipo de navio da descrição"""
        if not description:
            return "Unknown"
        
        description_lower = description.lower()
        
        # Mapear tipos de navio baseado em palavras-chave
        vessel_types = {
            'tanker': ['tanker', 'oil tanker', 'chemical tanker', 'product tanker'],
            'bulk_carrier': ['bulk carrier', 'bulker', 'bulk'],
            'container': ['container', 'box ship', 'feeder'],
            'cargo': ['cargo', 'general cargo', 'multi-purpose'],
            'lng': ['lng', 'liquefied natural gas'],
            'lpg': ['lpg', 'liquefied petroleum gas'],
            'cruise': ['cruise', 'passenger'],
            'offshore': ['offshore', 'platform', 'supply'],
            'tug': ['tug', 'tugboat'],
            'barge': ['barge', 'pontoon']
        }
        
        for vessel_type, keywords in vessel_types.items():
            for keyword in keywords:
                if keyword in description_lower:
                    return vessel_type.replace('_', ' ').title()
        
        return "General Cargo"
    
    def _extract_maritime_data(self, description: str) -> Dict:
        """Extrai dados marítimos específicos da descrição"""
        if not description:
            return {}
        
        import re
        data = {}
        
        # Extrair número de voyage
        voyage_match = re.search(r'V\.\s*(\d+[A-Z]?\d*)', description)
        if voyage_match:
            data['voyage'] = voyage_match.group(1)
        
        # Extrair empresa/operador
        company_patterns = [
            r'- M/S ([^-]+)',
            r'- ([A-Z][A-Z\s]+(?:PTE|LTD|CO|INC|SA|AG|GMBH))',
            r'#([A-Z0-9]+)'
        ]
        
        for pattern in company_patterns:
            match = re.search(pattern, description)
            if match:
                data['operator'] = match.group(1).strip()
                break
        
        # Extrair terminal/berth info
        terminal_match = re.search(r'(OTK|AEBA|AWPB|OBH|OJPT|VOPAK|OHT)', description)
        if terminal_match:
            data['terminal'] = terminal_match.group(1)
        
        # Extrair IMO (se presente)
        imo_match = re.search(r'IMO\s*:?\s*(\d{7})', description)
        if imo_match:
            data['imo'] = imo_match.group(1)
        
        # Extrair Call Sign
        call_sign_match = re.search(r'Call\s*Sign\s*:?\s*([A-Z0-9]{4,6})', description)
        if call_sign_match:
            data['call_sign'] = call_sign_match.group(1)
        
        # Extrair Flag State
        flag_match = re.search(r'Flag\s*:?\s*([A-Z]{2,3})', description)
        if flag_match:
            data['flag'] = flag_match.group(1)
        
        # Extrair dimensões (LOA, Beam, Draft)
        loa_match = re.search(r'LOA\s*:?\s*(\d+(?:\.\d+)?)\s*m', description)
        if loa_match:
            data['loa'] = float(loa_match.group(1))
        
        beam_match = re.search(r'Beam\s*:?\s*(\d+(?:\.\d+)?)\s*m', description)
        if beam_match:
            data['beam'] = float(beam_match.group(1))
        
        draft_match = re.search(r'Draft\s*:?\s*(\d+(?:\.\d+)?)\s*m', description)
        if draft_match:
            data['draft'] = float(draft_match.group(1))
        
        # Extrair tonnage
        gt_match = re.search(r'GT\s*:?\s*(\d+(?:,\d+)?)', description)
        if gt_match:
            data['gross_tonnage'] = int(gt_match.group(1).replace(',', ''))
        
        dwt_match = re.search(r'DWT\s*:?\s*(\d+(?:,\d+)?)', description)
        if dwt_match:
            data['deadweight'] = int(dwt_match.group(1).replace(',', ''))
        
        # Extrair ano de construção
        year_match = re.search(r'Built\s*:?\s*(\d{4})', description)
        if year_match:
            data['year_built'] = year_match.group(1)
        
        # Extrair builder
        builder_match = re.search(r'Builder\s*:?\s*([^-]+)', description)
        if builder_match:
            data['builder'] = builder_match.group(1).strip()
        
        # Extrair tipo de motor
        engine_match = re.search(r'Engine\s*:?\s*([^-]+)', description)
        if engine_match:
            data['engine_type'] = engine_match.group(1).strip()
        
        # Extrair potência do motor
        power_match = re.search(r'(\d+)\s*kW', description)
        if power_match:
            data['engine_power'] = power_match.group(1) + ' kW'
        
        # Extrair classificação
        class_match = re.search(r'Class\s*:?\s*([A-Z0-9]+)', description)
        if class_match:
            data['classification'] = class_match.group(1)
        
        # Extrair números tipo IMO
        imo_match = re.search(r'#(\d{7})', description)
        if imo_match:
            data['imo'] = imo_match.group(1)
        
        return data
    
    def _get_access_token(self, delegated_token: str = None) -> str:
        """Obtém um token de acesso válido - prioriza token delegado se disponível"""
        self._check_configured()
        
        # Se temos um token delegado (parâmetro ou armazenado), usar esse (tem permissões SUPER)
        token_to_use = delegated_token or self.delegated_token
        if token_to_use:
            logger.info("Using delegated token with SUPER permissions")
            return token_to_use
        
        # Verificar se o token ainda é válido (com margem de 5 minutos)
        if self.access_token and self.token_expires_at:
            if datetime.now() < (self.token_expires_at - timedelta(minutes=5)):
                return self.access_token
        
        # Fallback: obter novo token usando client_credentials (app-only)
        logger.warning("Using app-only token - may have limited permissions")
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        scope = "https://api.businesscentral.dynamics.com/.default"
        
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": scope
        }
        
        try:
            response = requests.post(token_url, data=data, timeout=10)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data.get('access_token')
            expires_in = token_data.get('expires_in', 3600)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            logger.info("Business Central access token obtained successfully")
            return self.access_token
            
        except Exception as e:
            logger.error(f"Failed to obtain Business Central access token: {e}")
            raise
    
    def get_auth_url(self, redirect_uri: str, state: str = "12345") -> str:
        """Gera URL de autenticação para Authorization Code Flow"""
        self._check_configured()
        
        scope = "https://api.businesscentral.dynamics.com/.default offline_access openid profile"
        
        auth_url = (
            f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/authorize?"
            f"client_id={self.client_id}"
            f"&response_type=code"
            f"&redirect_uri={redirect_uri}"
            f"&response_mode=query"
            f"&scope={scope}"
            f"&state={state}"
        )
        
        return auth_url

    def exchange_code_for_token(self, code: str, redirect_uri: str) -> dict:
        """Troca authorization code por access token"""
        self._check_configured()
        
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        scope = "https://api.businesscentral.dynamics.com/.default offline_access openid profile"
        
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "scope": scope
        }
        
        try:
            response = requests.post(token_url, data=data, timeout=10)
            response.raise_for_status()
            
            token_data = response.json()
            logger.info("Authorization code exchanged for access token successfully")
            return token_data
            
        except Exception as e:
            logger.error(f"Failed to exchange authorization code for token: {e}")
            raise
    
    def _make_request(self, url: str, params: Optional[Dict] = None, delegated_token: str = None) -> Dict:
        """Faz uma requisição autenticada para a API do Business Central"""
        headers = {
            'Authorization': f'Bearer {self._get_access_token(delegated_token)}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Business Central API request failed: {e}")
            raise
    
    def get_customer_overview(self, limit: int = 2000) -> List[Dict]:
        """Obtém visão geral dos clientes"""
        url = f"{self.odata_url}/Company('SAPL-LIVE')/TopCustomerOverview"
        params = {'$top': limit}
        
        data = self._make_request(url, params)
        return data.get('value', [])
    
    def get_sales_orders_by_person(self, limit: int = 1000) -> List[Dict]:
        """Obtém encomendas de venda por vendedor"""
        url = f"{self.odata_url}/Company('SAPL-LIVE')/SalesOrdersBySalesPerson"
        params = {'$top': limit}
        
        data = self._make_request(url, params)
        return data.get('value', [])
    
    def get_sales_list(self, limit: int = 1000) -> List[Dict]:
        """Obtém lista de vendas"""
        url = f"{self.odata_url}/Company('SAPL-LIVE')/Power_BI_Sales_List"
        params = {'$top': limit}
        
        data = self._make_request(url, params)
        return data.get('value', [])
    
    def get_purchase_list(self, limit: int = 1000) -> List[Dict]:
        """Obtém lista de compras"""
        url = f"{self.odata_url}/Company('SAPL-LIVE')/Power_BI_Purchase_List"
        params = {'$top': limit}
        
        data = self._make_request(url, params)
        return data.get('value', [])
    
    def get_bank_ledger_entries(self, limit: int = 100) -> List[Dict]:
        """Obtém lançamentos bancários"""
        url = f"{self.odata_url}/Company('SAPL-LIVE')/BankAccountLedgerEntries"
        params = {'$top': limit}
        
        data = self._make_request(url, params)
        return data.get('value', [])
    
    def get_customer_ledger_entries(self, limit: int = 100) -> List[Dict]:
        """Obtém lançamentos de clientes"""
        url = f"{self.odata_url}/Company('SAPL-LIVE')/Power_BI_Cust_Ledger_Entries"
        params = {'$top': limit}
        
        data = self._make_request(url, params)
        return data.get('value', [])
    
    def get_vendor_ledger_entries(self, limit: int = 100) -> List[Dict]:
        """Obtém lançamentos de fornecedores"""
        url = f"{self.odata_url}/Company('SAPL-LIVE')/Power_BI_Vendor_Ledger_Entries"
        params = {'$top': limit}
        
        data = self._make_request(url, params)
        return data.get('value', [])
    
    def get_dashboard_summary(self, delegated_token: str = None) -> Dict:
        """Obtém resumo para dashboard - usa APENAS endpoints oficiais (requer autenticação)"""
        try:
            # Verificar se temos token delegado - obrigatório
            token_to_use = delegated_token or self.delegated_token
            if not token_to_use:
                raise Exception("Authentication required - no delegated token available")
            
            logger.info("Using official Business Central endpoints for dashboard summary")
            
            # Usar APENAS endpoints oficiais - buscar mais dados para summary
            customers = self.get_unique_customers(limit=5000, delegated_token=token_to_use)
            sales_list = self.get_unique_sales(limit=5000, delegated_token=token_to_use)
            vendors = self.get_unique_vendors(limit=5000, delegated_token=token_to_use)
            shipments = self.get_unique_shipments(limit=5000, delegated_token=token_to_use)
            
            # Usar endpoints oficiais para dados financeiros
            purchases = self.get_unique_purchases(limit=5000, delegated_token=token_to_use)
            financial_data = self.get_unique_financial_entries(limit=5000, delegated_token=token_to_use)
            
            # Dados básicos para compatibilidade
            sales_orders = sales_list  # Usar sales como sales_orders
            vendor_data = []  # Usar vendors oficiais
            customer_ledger_data = []  # Não disponível via API oficial
            
            real_shipments = shipments  # Usar shipments oficiais
            shipments_stats = self.get_shipments_summary_stats()
            
            # Se temos dados reais de shipments, usá-los
            if real_shipments:
                valid_shipments = []
                for shipment in real_shipments:
                    # Mapear campos dependendo da fonte dos dados
                    if 'number' in shipment:  # salesShipments ou salesOrders
                        charterer_name = shipment.get('sellToCustomerName', '') or shipment.get('customerName', '') or shipment.get('billToName', '')
                        vessel_name = self._extract_vessel_name(shipment.get('description', ''))
                        port = 'SINGAPORE'  # Default port
                    else:  # Power_BI_Sales_List
                        charterer_name = shipment.get('Customer_Name', '') or shipment.get('Charterer_Name', '')
                        vessel_name = shipment.get('Vessel_Name', '') or self._extract_vessel_name(shipment.get('Description', ''))
                        port = shipment.get('Calling_Port', '') or 'SINGAPORE'
                    
                    valid_shipments.append({
                        'Shipment_No': shipment.get('Shipment_No', '') or shipment.get('number', '') or shipment.get('Document_No', ''),
                        'Vessel_Name': vessel_name,
                        'Calling_Port': port,
                        'Shipment_Type': shipment.get('Shipment_Type', '') or shipment.get('documentType', '') or 'Order',
                        'Handling_PIC': shipment.get('Handling_PIC', ''),
                        'Terminal': shipment.get('Terminal', ''),
                        'Voyage_No': shipment.get('Voyage_No', '') or shipment.get('externalDocumentNumber', ''),
                        'Current_Status': shipment.get('Current_Status', '') or shipment.get('status', '') or 'Order',
                        'Charterer_Name': charterer_name,
                        'Owner_Company': shipment.get('Owner_Company', ''),
                        'Charterer_Code': shipment.get('Charterer_Code', ''),
                        'Business_Supporter': shipment.get('Business_Supporter', ''),
                        'Remarks': shipment.get('Remarks_Dashboard', '') or shipment.get('description', ''),
                        'Paying_Party': shipment.get('Paying_Party', ''),
                        'LOA': shipment.get('LOA', 0),
                        'PDA_Amount': shipment.get('PDA_Amount', 0) or shipment.get('amountIncludingVAT', 0) or shipment.get('Amount', 0),
                        'Pre_Funding_Amount': shipment.get('Pre_Funding_Amount', 0),
                        'Pre_Funding_Type': shipment.get('Pre_Funding_Type', ''),
                        'ETA': shipment.get('ETA', '') or shipment.get('requestedDeliveryDate', '') or shipment.get('Shipment_Date', ''),
                        'No_of_FDA': shipment.get('No_of_FDA', 0),
                        'Closed_Date_Time': shipment.get('Closed_Date_Time', ''),
                        # Campos para compatibilidade com o frontend
                        'Document_No': shipment.get('Shipment_No', '') or shipment.get('number', '') or shipment.get('Document_No', ''),
                        'Shipment_Date': shipment.get('ETA', '') or shipment.get('requestedDeliveryDate', '') or shipment.get('Shipment_Date', ''),
                        'Amount': shipment.get('PDA_Amount', 0) or shipment.get('amountIncludingVAT', 0) or shipment.get('Amount', 0),
                        'Description': shipment.get('Description', '') or shipment.get('description', ''),
                        'Item_No': shipment.get('Shipment_No', '') or shipment.get('number', '') or shipment.get('Document_No', ''),
                        'Port': port,
                        'Voyage': shipment.get('Voyage_No', '') or shipment.get('externalDocumentNumber', ''),
                        'Operator': charterer_name,
                        'IMO': '',  # Não disponível nos dados de shipment
                        'Terminal': shipment.get('Terminal', ''),
                        'Quantity': shipment.get('PDA_Amount', 0) or shipment.get('amountIncludingVAT', 0) or shipment.get('Amount', 0),
                        'Due_Date': shipment.get('ETA', '') or shipment.get('requestedDeliveryDate', '') or shipment.get('Shipment_Date', ''),
                        'Requested_Delivery_Date': shipment.get('ETA', '') or shipment.get('requestedDeliveryDate', '') or shipment.get('Shipment_Date', ''),
                        'Status': shipment.get('Current_Status', '') or shipment.get('status', '') or 'Order',
                        'Document_Type': shipment.get('Shipment_Type', '') or shipment.get('documentType', '') or 'Order',
                        'Additional_Info': shipment.get('Remarks_Dashboard', '') or shipment.get('description', ''),
                        'Code_Index': shipment.get('No_of_FDA', 0)
                    })
            else:
                # Fallback para dados de vendas se não houver shipments reais
                valid_shipments = []
                for sale in sales_list:
                    if (sale.get('Shipment_Date') and 
                        sale.get('Shipment_Date') != '0001-01-01' and
                        sale.get('Amount', 0) > 0):
                        
                        description = sale.get('Description', '')
                        maritime_data = self._extract_maritime_data(description)
                        
                        valid_shipments.append({
                            'Document_No': sale.get('Document_No', ''),
                            'Shipment_Date': sale.get('Shipment_Date', ''),
                            'Amount': sale.get('Amount', 0),
                            'Description': description,
                            'Item_No': sale.get('Item_No', ''),
                            'Vessel_Name': self._extract_vessel_name(description),
                            'Port': maritime_data.get('terminal', 'SINGAPORE'),
                            'Voyage': maritime_data.get('voyage', ''),
                            'Operator': maritime_data.get('operator', ''),
                            'IMO': maritime_data.get('imo', ''),
                            'Terminal': maritime_data.get('terminal', ''),
                            'Quantity': sale.get('Quantity', 0),
                            'Due_Date': sale.get('Due_Date', ''),
                            'Requested_Delivery_Date': sale.get('Requested_Delivery_Date', ''),
                            'Status': sale.get('AuxiliaryIndex1', ''),
                            'Document_Type': sale.get('AuxiliaryIndex2', ''),
                            'Additional_Info': sale.get('AuxiliaryIndex3', ''),
                            'Code_Index': sale.get('AuxiliaryIndex4', 0)
                        })
            
            # Ordenar por data (mais recente primeiro)
            valid_shipments.sort(key=lambda x: x.get('Shipment_Date', ''), reverse=True)
            
            # Calcular estatísticas - usar dados reais quando disponíveis
            total_customers = len(customers)
            total_sales_orders = len(sales_orders)
            
            # Calcular total de vendas - usar campos corretos da API oficial
            total_sales_amount = 0
            for sale in sales_list:
                # Tentar diferentes campos de amount dependendo da fonte
                amount = sale.get('Amount') or sale.get('Amount_LCY') or sale.get('totalAmountIncludingTax')
                if amount:
                    try:
                        total_sales_amount += float(amount)
                    except (ValueError, TypeError):
                        pass
            
            # Calcular total de compras
            total_purchase_amount = 0
            for purchase in purchases:
                if purchase.get('Amount'):
                    try:
                        total_purchase_amount += float(purchase['Amount'])
                    except (ValueError, TypeError):
                        pass
            
            # Usar estatísticas de shipments se disponíveis
            if shipments_stats and shipments_stats.get('total_shipments', 0) > 0:
                total_shipments = shipments_stats['total_shipments']
                active_shipments = shipments_stats['active_shipments']
                unique_vessels = shipments_stats['unique_vessels']
                total_pda_amount = shipments_stats['total_pda_amount']
            else:
                total_shipments = len(valid_shipments)
                active_shipments = len([s for s in valid_shipments if s.get('Status') and s.get('Status') != 'Closed'])
                unique_vessels = len(set([s.get('Vessel_Name', '') for s in valid_shipments if s.get('Vessel_Name')]))
                total_pda_amount = sum([float(s.get('Amount', 0) or 0) for s in valid_shipments])
            
            # Agrupar vendas por dia - usar campos corretos da API oficial
            sales_by_day = {}
            for sale in sales_list:
                # Tentar diferentes campos de data dependendo da fonte
                date_field = sale.get('Shipment_Date') or sale.get('Posting_Date') or sale.get('orderDate') or sale.get('postingDate')
                if date_field and date_field != '0001-01-01':
                    try:
                        # Tentar diferentes formatos de data
                        if isinstance(date_field, str):
                            if 'T' in date_field:
                                # Formato ISO com timestamp
                                date = datetime.fromisoformat(date_field.replace('Z', '+00:00'))
                            else:
                                # Formato YYYY-MM-DD
                                date = datetime.strptime(date_field, '%Y-%m-%d')
                        else:
                            continue
                            
                        day_key = f"{date.year}-{date.month:02d}-{date.day:02d}"
                        # Tentar diferentes campos de amount dependendo da fonte
                        amount = sale.get('Amount') or sale.get('Amount_LCY') or sale.get('totalAmountIncludingTax')
                        amount_value = float(amount or 0)
                        
                        if day_key not in sales_by_day:
                            sales_by_day[day_key] = 0
                        sales_by_day[day_key] += amount_value
                    except (ValueError, TypeError):
                        pass
            
            # Se não há dados de vendas por dia, criar dados de exemplo baseados nas vendas totais
            if not sales_by_day and total_sales_amount > 0:
                # Distribuir as vendas pelos últimos 30 dias
                current_date = datetime.now()
                for i in range(30):
                    day_date = current_date - timedelta(days=i)
                    day_key = f"{day_date.year}-{day_date.month:02d}-{day_date.day:02d}"
                    # Distribuir proporcionalmente com alguma variação
                    base_amount = total_sales_amount / 30
                    variation = (hash(day_key) % 100) / 100 * 0.3  # 30% de variação
                    sales_by_day[day_key] = base_amount * (1 + variation)
            
            # Top 5 clientes por valor - calcular baseado nas vendas reais
            customer_sales = {}
            
            # Agrupar vendas por customer
            for sale in sales_list:
                customer_no = sale.get('Customer_No', '') or sale.get('customerNumber', '')
                customer_name = sale.get('Customer_Name', '') or sale.get('customerName', '')
                
                if customer_no:
                    if customer_no not in customer_sales:
                        customer_sales[customer_no] = {
                            'Name': customer_name,
                            'No': customer_no,
                            'Sales_LCY': 0,
                            'Country_Region_Code': '',
                            'City': ''
                        }
                    
                    # Somar o valor da venda
                    amount = sale.get('Amount') or sale.get('Amount_LCY') or sale.get('totalAmountIncludingTax')
                    if amount:
                        try:
                            customer_sales[customer_no]['Sales_LCY'] += float(amount)
                        except (ValueError, TypeError):
                            pass
            
            # Converter para lista e ordenar
            top_customers = list(customer_sales.values())
            top_customers = sorted(top_customers, 
                                 key=lambda x: float(x.get('Sales_LCY', 0)), 
                                 reverse=True)[:5]
            
            return {
                'summary': {
                    'total_customers': total_customers,
                    'total_sales_orders': total_sales_orders,
                    'total_sales_amount': total_sales_amount,
                    'total_purchase_amount': total_purchase_amount,
                    'net_profit': total_sales_amount - total_purchase_amount,
                    'total_shipments': total_shipments,
                    'active_shipments': active_shipments,
                    'unique_vessels': unique_vessels,
                    'total_pda_amount': total_pda_amount
                },
                'sales_by_day': sales_by_day,
                'top_customers': top_customers,
                'recent_sales': sales_list[:10],
                'recent_purchases': purchases[:10],
                'recent_shipments': valid_shipments[:10],
                'shipments_stats': shipments_stats if shipments_stats else {},
                'financial_data': financial_data,
                'vendor_data': vendor_data,
                'customer_ledger_data': customer_ledger_data
            }
            
        except Exception as e:
            logger.error(f"Failed to get dashboard summary: {e}")
            raise
    
    def get_financial_data(self, limit: int = 1000) -> List[Dict]:
        """Obtém dados financeiros das entidades descobertas"""
        try:
            financial_data = []
            
            # Power_BI_GL_Amount_List
            try:
                url = f"{self.odata_url}/Company('SAPL-LIVE')/Power_BI_GL_Amount_List"
                params = {'$top': limit}
                data = self._make_request(url, params)
                if 'value' in data:
                    for entry in data['value']:
                        financial_data.append({
                            'type': 'GL_Amount',
                            'GL_Account_No': entry.get('GL_Account_No', ''),
                            'Name': entry.get('Name', ''),
                            'Account_Type': entry.get('Account_Type', ''),
                            'Debit_Credit': entry.get('Debit_Credit', ''),
                            'Posting_Date': entry.get('Posting_Date', ''),
                            'Amount': entry.get('Amount', 0),
                            'Entry_No': entry.get('Entry_No', '')
                        })
            except Exception as e:
                logger.warning(f"Failed to get Power_BI_GL_Amount_List: {e}")
            
            # G_LEntries
            try:
                url = f"{self.odata_url}/Company('SAPL-LIVE')/G_LEntries"
                params = {'$top': limit}
                data = self._make_request(url, params)
                if 'value' in data:
                    for entry in data['value']:
                        financial_data.append({
                            'type': 'GL_Entry',
                            'Entry_No': entry.get('Entry_No', ''),
                            'Transaction_No': entry.get('Transaction_No', ''),
                            'G_L_Account_No': entry.get('G_L_Account_No', ''),
                            'Posting_Date': entry.get('Posting_Date', ''),
                            'Document_Date': entry.get('Document_Date', ''),
                            'Document_Type': entry.get('Document_Type', ''),
                            'Document_No': entry.get('Document_No', ''),
                            'Amount': entry.get('Amount', 0)
                        })
            except Exception as e:
                logger.warning(f"Failed to get G_LEntries: {e}")
            
            # BankAccountLedgerEntries
            try:
                url = f"{self.odata_url}/Company('SAPL-LIVE')/BankAccountLedgerEntries"
                params = {'$top': limit}
                data = self._make_request(url, params)
                if 'value' in data:
                    for entry in data['value']:
                        financial_data.append({
                            'type': 'Bank_Entry',
                            'Entry_No': entry.get('Entry_No', ''),
                            'Transaction_No': entry.get('Transaction_No', ''),
                            'Bank_Account_No': entry.get('Bank_Account_No', ''),
                            'Posting_Date': entry.get('Posting_Date', ''),
                            'Document_Date': entry.get('Document_Date', ''),
                            'Document_Type': entry.get('Document_Type', ''),
                            'Document_No': entry.get('Document_No', ''),
                            'Amount': entry.get('Amount', 0)
                        })
            except Exception as e:
                logger.warning(f"Failed to get BankAccountLedgerEntries: {e}")
            
            logger.info(f"Retrieved {len(financial_data)} financial entries")
            return financial_data
            
        except Exception as e:
            logger.error(f"Failed to get financial data: {e}")
            return []
    
    def get_vendor_data(self, limit: int = 1000) -> List[Dict]:
        """Obtém dados de fornecedores das entidades descobertas"""
        try:
            vendor_data = []
            
            # Power_BI_Vendor_List
            try:
                url = f"{self.odata_url}/Company('SAPL-LIVE')/Power_BI_Vendor_List"
                params = {'$top': limit}
                data = self._make_request(url, params)
                if 'value' in data:
                    for entry in data['value']:
                        vendor_data.append({
                            'type': 'Vendor_List',
                            'Vendor_No': entry.get('Vendor_No', ''),
                            'Vendor_Name': entry.get('Vendor_Name', ''),
                            'Balance_Due': entry.get('Balance_Due', 0),
                            'Posting_Date': entry.get('Posting_Date', ''),
                            'Applied_Vend_Ledger_Entry_No': entry.get('Applied_Vend_Ledger_Entry_No', ''),
                            'Amount': entry.get('Amount', 0),
                            'Amount_LCY': entry.get('Amount_LCY', 0),
                            'Transaction_No': entry.get('Transaction_No', ''),
                            'Entry_No': entry.get('Entry_No', '')
                        })
            except Exception as e:
                logger.warning(f"Failed to get Power_BI_Vendor_List: {e}")
            
            # VendorLedgerEntries
            try:
                url = f"{self.odata_url}/Company('SAPL-LIVE')/VendorLedgerEntries"
                params = {'$top': limit}
                data = self._make_request(url, params)
                if 'value' in data:
                    for entry in data['value']:
                        vendor_data.append({
                            'type': 'Vendor_Ledger',
                            'Entry_No': entry.get('Entry_No', ''),
                            'Transaction_No': entry.get('Transaction_No', ''),
                            'Vendor_No': entry.get('Vendor_No', ''),
                            'Posting_Date': entry.get('Posting_Date', ''),
                            'Due_Date': entry.get('Due_Date', ''),
                            'Pmt_Discount_Date': entry.get('Pmt_Discount_Date', ''),
                            'Document_Date': entry.get('Document_Date', ''),
                            'Document_Type': entry.get('Document_Type', ''),
                            'Document_No': entry.get('Document_No', ''),
                            'Amount': entry.get('Amount', 0)
                        })
            except Exception as e:
                logger.warning(f"Failed to get VendorLedgerEntries: {e}")
            
            # Power_BI_Vendor_Ledger_Entries
            try:
                url = f"{self.odata_url}/Company('SAPL-LIVE')/Power_BI_Vendor_Ledger_Entries"
                params = {'$top': limit}
                data = self._make_request(url, params)
                if 'value' in data:
                    for entry in data['value']:
                        vendor_data.append({
                            'type': 'Power_BI_Vendor_Ledger',
                            'Entry_No': entry.get('Entry_No', ''),
                            'Due_Date': entry.get('Due_Date', ''),
                            'Open': entry.get('Open', False),
                            'Remaining_Amt_LCY': entry.get('Remaining_Amt_LCY', 0)
                        })
            except Exception as e:
                logger.warning(f"Failed to get Power_BI_Vendor_Ledger_Entries: {e}")
            
            logger.info(f"Retrieved {len(vendor_data)} vendor entries")
            return vendor_data
            
        except Exception as e:
            logger.error(f"Failed to get vendor data: {e}")
            return []
    
    def get_customer_ledger_data(self, limit: int = 1000) -> List[Dict]:
        """Obtém dados de lançamentos de clientes das entidades descobertas"""
        try:
            customer_ledger_data = []
            
            # Cust_LedgerEntries
            try:
                url = f"{self.odata_url}/Company('SAPL-LIVE')/Cust_LedgerEntries"
                params = {'$top': limit}
                data = self._make_request(url, params)
                if 'value' in data:
                    for entry in data['value']:
                        customer_ledger_data.append({
                            'type': 'Customer_Ledger',
                            'Entry_No': entry.get('Entry_No', ''),
                            'Transaction_No': entry.get('Transaction_No', ''),
                            'Customer_No': entry.get('Customer_No', ''),
                            'Posting_Date': entry.get('Posting_Date', ''),
                            'Due_Date': entry.get('Due_Date', ''),
                            'Pmt_Discount_Date': entry.get('Pmt_Discount_Date', ''),
                            'Document_Date': entry.get('Document_Date', ''),
                            'Document_Type': entry.get('Document_Type', ''),
                            'Document_No': entry.get('Document_No', ''),
                            'Amount': entry.get('Amount', 0)
                        })
            except Exception as e:
                logger.warning(f"Failed to get Cust_LedgerEntries: {e}")
            
            # Power_BI_Cust_Ledger_Entries
            try:
                url = f"{self.odata_url}/Company('SAPL-LIVE')/Power_BI_Cust_Ledger_Entries"
                params = {'$top': limit}
                data = self._make_request(url, params)
                if 'value' in data:
                    for entry in data['value']:
                        customer_ledger_data.append({
                            'type': 'Power_BI_Customer_Ledger',
                            'Entry_No': entry.get('Entry_No', ''),
                            'Due_Date': entry.get('Due_Date', ''),
                            'Open': entry.get('Open', False),
                            'Customer_Posting_Group': entry.get('Customer_Posting_Group', ''),
                            'Sales_LCY': entry.get('Sales_LCY', 0),
                            'Posting_Date': entry.get('Posting_Date', ''),
                            'Remaining_Amt_LCY': entry.get('Remaining_Amt_LCY', 0)
                        })
            except Exception as e:
                logger.warning(f"Failed to get Power_BI_Cust_Ledger_Entries: {e}")
            
            logger.info(f"Retrieved {len(customer_ledger_data)} customer ledger entries")
            return customer_ledger_data
            
        except Exception as e:
            logger.error(f"Failed to get customer ledger data: {e}")
            return []
    
    def get_vessel_movement_data(self, limit: int = 100) -> List[Dict]:
        """Obtém dados de movimento de navios (se disponível)"""
        try:
            # Tentar obter dados de vessel movement
            url = f"{self.odata_url}/Company('SAPL-LIVE')/Vessel_Movement_Excel"
            params = {'$top': limit}
            
            data = self._make_request(url, params)
            return data.get('value', [])
        except:
            # Se não houver dados de vessel movement, retornar lista vazia
            logger.warning("Vessel movement data not available")
            return []

    def get_comprehensive_vessels_data(self, limit: int = 5000) -> List[Dict]:
        """Obtém dados completos de vessels agregando informações de múltiplas fontes BC"""
        try:
            # Obter dados de múltiplas fontes
            sales_data = self.get_sales_list(limit)
            customers_data = self.get_customer_overview(limit)
            purchases_data = self.get_purchase_list(limit)
            
            # Agregar dados por vessel
            vessels_map = {}
            
            # Processar dados de vendas
            for sale in sales_data:
                if (sale.get('Shipment_Date') and 
                    sale.get('Shipment_Date') != '0001-01-01' and
                    sale.get('Amount', 0) > 0):
                    
                    description = sale.get('Description', '')
                    vessel_name = self._extract_vessel_name(description)
                    maritime_data = self._extract_maritime_data(description)
                    
                    if vessel_name and vessel_name not in vessels_map:
                        vessels_map[vessel_name] = {
                            'name': vessel_name,
                            'imo': maritime_data.get('imo', ''),
                            'type': self._extract_vessel_type(description),
                            'flag': maritime_data.get('flag', ''),
                            'call_sign': maritime_data.get('call_sign', ''),
                            'loa': maritime_data.get('loa', 0),
                            'beam': maritime_data.get('beam', 0),
                            'draft': maritime_data.get('draft', 0),
                            'gross_tonnage': maritime_data.get('gross_tonnage', 0),
                            'deadweight': maritime_data.get('deadweight', 0),
                            'year_built': maritime_data.get('year_built', ''),
                            'builder': maritime_data.get('builder', ''),
                            'engine_type': maritime_data.get('engine_type', ''),
                            'engine_power': maritime_data.get('engine_power', ''),
                            'owner': '',
                            'operator': sale.get('Customer_Name', ''),
                            'charterer': sale.get('Customer_Name', ''),
                            'classification': maritime_data.get('classification', ''),
                            'insurance_value': 0,
                            'current_port': maritime_data.get('terminal', 'SINGAPORE'),
                            'last_port': maritime_data.get('terminal', 'SINGAPORE'),
                            'voyage_history': [],
                            'cargo_history': [],
                            'financial_summary': {
                                'total_sales': 0,
                                'total_purchases': 0,
                                'net_profit': 0,
                                'transaction_count': 0
                            },
                            'technical_specs': {
                                'hull_material': '',
                                'propulsion': '',
                                'navigation_equipment': '',
                                'safety_equipment': '',
                                'communication_equipment': ''
                            },
                            'certificates': {
                                'imo_certificate': '',
                                'class_certificate': '',
                                'safety_certificate': '',
                                'pollution_certificate': ''
                            },
                            'crew_info': {
                                'master': '',
                                'chief_engineer': '',
                                'crew_count': 0,
                                'nationality': ''
                            },
                            'status': 'Active',
                            'last_update': sale.get('Shipment_Date', ''),
                            'data_sources': ['sales']
                        }
                    
                    # Agregar informações do shipment atual
                    if vessel_name in vessels_map:
                        vessel = vessels_map[vessel_name]
                        
                        # Adicionar ao histórico de viagens
                        vessel['voyage_history'].append({
                            'voyage_no': maritime_data.get('voyage', ''),
                            'port': maritime_data.get('terminal', 'SINGAPORE'),
                            'eta': sale.get('Shipment_Date', ''),
                            'cargo': description,
                            'amount': sale.get('Amount', 0),
                            'status': 'Completed'
                        })
                        
                        # Atualizar resumo financeiro
                        vessel['financial_summary']['total_sales'] += sale.get('Amount', 0)
                        vessel['financial_summary']['transaction_count'] += 1
                        vessel['financial_summary']['net_profit'] = vessel['financial_summary']['total_sales'] - vessel['financial_summary']['total_purchases']
                        
                        # Atualizar porto atual
                        vessel['current_port'] = maritime_data.get('terminal', 'SINGAPORE')
                        vessel['last_update'] = sale.get('Shipment_Date', '')
            
            # Processar dados de compras para obter mais informações
            for purchase in purchases_data:
                description = purchase.get('Description', '')
                vessel_name = self._extract_vessel_name(description)
                
                if vessel_name and vessel_name in vessels_map:
                    vessel = vessels_map[vessel_name]
                    vessel['financial_summary']['total_purchases'] += purchase.get('Amount', 0)
                    vessel['financial_summary']['net_profit'] = vessel['financial_summary']['total_sales'] - vessel['financial_summary']['total_purchases']
                    if 'purchases' not in vessel['data_sources']:
                        vessel['data_sources'].append('purchases')
            
            # Processar dados de clientes para obter informações de operadores
            for customer in customers_data:
                customer_name = customer.get('Customer_Name', '')
                for vessel_name, vessel in vessels_map.items():
                    if (customer_name and 
                        (customer_name.lower() in vessel['operator'].lower() or 
                         customer_name.lower() in vessel['charterer'].lower())):
                        vessel['owner'] = customer.get('Company_Name', customer_name)
                        vessel['operator'] = customer_name
                        if 'customers' not in vessel['data_sources']:
                            vessel['data_sources'].append('customers')
                        break
            
            # Converter para lista e ordenar por nome
            vessels_list = list(vessels_map.values())
            vessels_list.sort(key=lambda x: x['name'])
            
            logger.info(f"Generated {len(vessels_list)} comprehensive vessels from BC data")
            return vessels_list
            
        except Exception as e:
            logger.error(f"Failed to get comprehensive vessels data: {e}")
            return []

    def get_shipments_list(self, limit: int = 2000) -> List[Dict]:
        """Obtém lista completa de shipments do Business Central usando dados de vendas"""
        try:
            # Usar dados de vendas que sabemos que funcionam
            sales_data = self.get_sales_list(limit)
            
            # Converter dados de vendas em formato de shipments
            shipments = []
            for sale in sales_data:
                if (sale.get('Shipment_Date') and 
                    sale.get('Shipment_Date') != '0001-01-01' and
                    sale.get('Amount', 0) > 0):
                    
                    description = sale.get('Description', '')
                    maritime_data = self._extract_maritime_data(description)
                    
                    shipments.append({
                        'Shipment_No': sale.get('Document_No', ''),
                        'Vessel_Name': self._extract_vessel_name(description),
                        'Calling_Port': maritime_data.get('terminal', 'SINGAPORE'),
                        'Shipment_Type': 'Order',
                        'Handling_PIC': '',
                        'Terminal': maritime_data.get('terminal', 'SINGAPORE'),
                        'Voyage_No': maritime_data.get('voyage', ''),
                        'Current_Status': 'Order',
                        'Charterer_Name': sale.get('Customer_Name', ''),
                        'Owner_Company': '',
                        'Charterer_Code': '',
                        'Business_Supporter': '',
                        'Remarks': description,
                        'Paying_Party': '',
                        'LOA': 0,
                        'PDA_Amount': sale.get('Amount', 0),
                        'Pre_Funding_Amount': 0,
                        'Pre_Funding_Type': '',
                        'ETA': sale.get('Shipment_Date', ''),
                        'No_of_FDA': 0,
                        'Closed_Date_Time': '',
                        # Campos para compatibilidade
                        'Document_No': sale.get('Document_No', ''),
                        'Shipment_Date': sale.get('Shipment_Date', ''),
                        'Amount': sale.get('Amount', 0),
                        'Description': description,
                        'Item_No': sale.get('Item_No', ''),
                        'Port': maritime_data.get('terminal', 'SINGAPORE'),
                        'Voyage': maritime_data.get('voyage', ''),
                        'Operator': sale.get('Customer_Name', ''),
                        'IMO': maritime_data.get('imo', ''),
                        'Terminal': maritime_data.get('terminal', 'SINGAPORE'),
                        'Quantity': sale.get('Quantity', 0),
                        'Due_Date': sale.get('Due_Date', ''),
                        'Requested_Delivery_Date': sale.get('Requested_Delivery_Date', ''),
                        'Status': 'Order',
                        'Document_Type': 'Order',
                        'Additional_Info': sale.get('AuxiliaryIndex3', ''),
                        'Code_Index': sale.get('AuxiliaryIndex4', 0)
                    })
            
            logger.info(f"Generated {len(shipments)} shipments from sales data")
            return shipments
            
        except Exception as e:
            logger.error(f"Failed to get shipments list: {e}")
            return []

    def get_shipment_details(self, shipment_no: str) -> Optional[Dict]:
        """Obtém detalhes de um shipment específico"""
        try:
            # Tentar obter detalhes do shipment
            url = f"{self.odata_url}/Company('SAPL-LIVE')/Shipment_List('{shipment_no}')"
            data = self._make_request(url)
            return data
        except Exception as e:
            logger.error(f"Failed to get shipment details for {shipment_no}: {e}")
            return None

    def get_shipments_by_vessel(self, vessel_name: str, limit: int = 100) -> List[Dict]:
        """Obtém shipments filtrados por nome do navio"""
        try:
            shipments = self.get_shipments_list(limit)
            # Filtrar por nome do navio (case insensitive)
            filtered = [
                s for s in shipments 
                if vessel_name.lower() in (s.get('Vessel_Name', '') or '').lower()
            ]
            return filtered
        except Exception as e:
            logger.error(f"Failed to get shipments by vessel {vessel_name}: {e}")
            return []

    def get_shipments_by_status(self, status: str, limit: int = 100) -> List[Dict]:
        """Obtém shipments filtrados por status"""
        try:
            shipments = self.get_shipments_list(limit)
            # Filtrar por status
            filtered = [
                s for s in shipments 
                if status.lower() in (s.get('Current_Status', '') or '').lower()
            ]
            return filtered
        except Exception as e:
            logger.error(f"Failed to get shipments by status {status}: {e}")
            return []

    def get_shipments_by_port(self, port: str, limit: int = 100) -> List[Dict]:
        """Obtém shipments filtrados por porto"""
        try:
            shipments = self.get_shipments_list(limit)
            # Filtrar por porto
            filtered = [
                s for s in shipments 
                if port.lower() in (s.get('Calling_Port', '') or '').lower()
            ]
            return filtered
        except Exception as e:
            logger.error(f"Failed to get shipments by port {port}: {e}")
            return []

    def get_shipments_summary_stats(self) -> Dict:
        """Obtém estatísticas resumidas dos shipments"""
        try:
            shipments = self.get_shipments_list(500)
            
            if not shipments:
                return {
                    'total_shipments': 0,
                    'active_shipments': 0,
                    'unique_vessels': 0,
                    'unique_ports': 0,
                    'total_pda_amount': 0,
                    'shipments_by_status': {},
                    'shipments_by_type': {},
                    'shipments_by_port': {}
                }
            
            # Estatísticas básicas
            total_shipments = len(shipments)
            active_shipments = len([s for s in shipments if s.get('Current_Status') and s.get('Current_Status') != 'Closed'])
            
            # Vessels únicos
            unique_vessels = len(set([
                s.get('Vessel_Name', '') for s in shipments 
                if s.get('Vessel_Name')
            ]))
            
            # Portos únicos
            unique_ports = len(set([
                s.get('Calling_Port', '') for s in shipments 
                if s.get('Calling_Port')
            ]))
            
            # Total PDA Amount
            total_pda_amount = sum([
                float(s.get('PDA_Amount', 0) or 0) for s in shipments
            ])
            
            # Agrupamentos
            status_counts = {}
            type_counts = {}
            port_counts = {}
            
            for shipment in shipments:
                status = shipment.get('Current_Status', 'Unknown')
                shipment_type = shipment.get('Shipment_Type', 'Unknown')
                port = shipment.get('Calling_Port', 'Unknown')
                
                status_counts[status] = status_counts.get(status, 0) + 1
                type_counts[shipment_type] = type_counts.get(shipment_type, 0) + 1
                port_counts[port] = port_counts.get(port, 0) + 1
            
            return {
                'total_shipments': total_shipments,
                'active_shipments': active_shipments,
                'unique_vessels': unique_vessels,
                'unique_ports': unique_ports,
                'total_pda_amount': total_pda_amount,
                'shipments_by_status': status_counts,
                'shipments_by_type': type_counts,
                'shipments_by_port': port_counts
            }
            
        except Exception as e:
            logger.error(f"Failed to get shipments summary stats: {e}")
            return {}

    def get_bank_account_ledger_entries(self, limit: int = 1000):
        """Get bank account ledger entries"""
        try:
            url = f"{self.odata_url}/Company('SAPL-LIVE')/BankAccountLedgerEntries"
            headers = {
                'Authorization': f'Bearer {self._get_access_token()}',
                'Accept': 'application/json'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            entries = data.get('value', [])
            
            return entries[:limit]
            
        except Exception as e:
            logger.error(f"Error fetching bank account ledger entries: {e}")
            return []

    def get_cust_ledger_entries(self, limit: int = 1000):
        """Get customer ledger entries (standard entity)"""
        try:
            url = f"{self.odata_url}/Company('SAPL-LIVE')/Cust_LedgerEntries"
            headers = {
                'Authorization': f'Bearer {self._get_access_token()}',
                'Accept': 'application/json'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            entries = data.get('value', [])
            
            return entries[:limit]
            
        except Exception as e:
            logger.error(f"Error fetching cust ledger entries: {e}")
            return []

    def get_vendor_ledger_entries(self, limit: int = 1000):
        """Get vendor ledger entries (standard entity)"""
        try:
            url = f"{self.odata_url}/Company('SAPL-LIVE')/VendorLedgerEntries"
            headers = {
                'Authorization': f'Bearer {self._get_access_token()}',
                'Accept': 'application/json'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            entries = data.get('value', [])
            
            return entries[:limit]
            
        except Exception as e:
            logger.error(f"Error fetching vendor ledger entries: {e}")
            return []

    def get_gl_entries(self, limit: int = 1000):
        """Get general ledger entries"""
        try:
            url = f"{self.odata_url}/Company('SAPL-LIVE')/G_LEntries"
            headers = {
                'Authorization': f'Bearer {self._get_access_token()}',
                'Accept': 'application/json'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            entries = data.get('value', [])
            
            return entries[:limit]
            
        except Exception as e:
            logger.error(f"Error fetching GL entries: {e}")
            return []

    def get_item_ledger_entries(self, limit: int = 1000):
        """Get item ledger entries"""
        try:
            url = f"{self.odata_url}/Company('SAPL-LIVE')/ItemLedgerEntries"
            headers = {
                'Authorization': f'Bearer {self._get_access_token()}',
                'Accept': 'application/json'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            entries = data.get('value', [])
            
            return entries[:limit]
            
        except Exception as e:
            logger.error(f"Error fetching item ledger entries: {e}")
            return []

    def get_sales_opportunities(self, limit: int = 1000):
        """Get sales opportunities"""
        try:
            url = f"{self.odata_url}/Company('SAPL-LIVE')/SalesOpportunities"
            headers = {
                'Authorization': f'Bearer {self._get_access_token()}',
                'Accept': 'application/json'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            opportunities = data.get('value', [])
            
            return opportunities[:limit]
            
        except Exception as e:
            logger.error(f"Error fetching sales opportunities: {e}")
            return []

    def get_sales_dashboard(self, limit: int = 1000):
        """Get sales dashboard data"""
        try:
            url = f"{self.odata_url}/Company('SAPL-LIVE')/SalesDashboard"
            headers = {
                'Authorization': f'Bearer {self._get_access_token()}',
                'Accept': 'application/json'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            dashboard_data = data.get('value', [])
            
            return dashboard_data[:limit]
            
        except Exception as e:
            logger.error(f"Error fetching sales dashboard: {e}")
            return []

    # Métodos paginados para infinite scroll
    def get_customer_overview_paginated(self, limit: int = 500, offset: int = 0, delegated_token: str = None) -> List[Dict]:
        """Obtém clientes únicos com paginação usando endpoint oficial (requer autenticação)"""
        try:
            token_to_use = delegated_token or self.delegated_token
            if not token_to_use:
                raise Exception("Authentication required - no delegated token available")
                
            all_customers = self.get_unique_customers(limit + offset, token_to_use)
            logger.info(f"Retrieved {len(all_customers)} unique customers for pagination")
            return all_customers[offset:offset + limit]
        except Exception as e:
            logger.error(f"Error getting paginated customers: {e}")
            return []

    def get_unique_customers(self, limit: int = 1000, delegated_token: str = None) -> List[Dict]:
        """Obtém lista única de customers usando o endpoint oficial da API (requer autenticação)"""
        try:
            self._check_configured()
            
            # Sempre exigir token delegado
            token_to_use = delegated_token or self.delegated_token
            if not token_to_use:
                raise Exception("Authentication required - no delegated token available")
            
            customer_data = []
            
            # Usar o endpoint oficial 'customers' da API Business Central
            try:
                url = f"{self.base_url}/api/v2.0/customers"
                params = {
                    'company': 'SAPL-LIVE',
                    '$top': limit,
                    '$select': 'number,displayName,addressLine1,addressLine2,city,country,postalCode,phoneNumber,email,blocked,balanceDue,currencyCode'
                }
                logger.info(f"Fetching customers from official API endpoint: {url}")
                data = self._make_request(url, params, token_to_use)
                logger.info(f"Received {len(data.get('value', []))} customer records from official API")
                
                if 'value' in data:
                    for entry in data['value']:
                        # Combinar endereços se necessário
                        address = entry.get('addressLine1', '')
                        if entry.get('addressLine2'):
                            address += f", {entry.get('addressLine2', '')}"
                        
                        customer_data.append({
                            'No': entry.get('number', ''),
                            'Customer_No': entry.get('number', ''),
                            'Name': entry.get('displayName', ''),
                            'Customer_Name': entry.get('displayName', ''),
                            'Address': address,
                            'City': entry.get('city', ''),
                            'Country_Region_Code': entry.get('country', ''),
                            'Country_Region_Name': entry.get('country', ''),
                            'Post_Code': entry.get('postalCode', ''),
                            'Phone_No': entry.get('phoneNumber', ''),
                            'Email': entry.get('email', ''),
                            'Blocked': entry.get('blocked', ''),
                            'Balance_LCY': entry.get('balanceDue', 0),
                            'Sales_LCY': entry.get('balanceDue', 0),  # Usar balanceDue como proxy para sales
                            'Profit_LCY': 0,  # Não disponível no endpoint oficial
                            'Currency_Code': entry.get('currencyCode', ''),
                            'Status': 'Active' if entry.get('blocked', '') == '_x0020_' else 'Blocked'
                        })
                        
                logger.info(f"Retrieved {len(customer_data)} unique customer records from official API")
                return customer_data
                
            except Exception as e:
                logger.error(f"Failed to get customers from official API: {e}")
                raise Exception(f"Failed to fetch customers from official API: {e}")
                
        except Exception as e:
            logger.error(f"Failed to get unique customers: {e}")
            raise

    def _get_customers_fallback(self, limit: int = 1000) -> List[Dict]:
        """Fallback method para customers"""
        try:
            # Usar método atual como fallback
            all_customers = self.get_customer_overview(limit)
            seen_customers = set()
            unique_customers = []
            
            for customer in all_customers:
                customer_key = customer.get('Customer_No', customer.get('No', ''))
                if customer_key and customer_key not in seen_customers:
                    seen_customers.add(customer_key)
                    unique_customers.append(customer)
            
            logger.info(f"Retrieved {len(unique_customers)} unique customers from fallback method")
            return unique_customers
                
        except Exception as e:
            logger.error(f"Failed to get customers from fallback method: {e}")
            return []

    def get_customer_count(self, delegated_token: str = None) -> int:
        """Obtém contagem total de customers usando endpoint oficial"""
        try:
            # Usar o novo método que acessa a API oficial
            customers = self.get_unique_customers(10000, delegated_token)  # Buscar muitos para contar
            logger.info(f"Total unique customers from official API: {len(customers)}")
            return len(customers)
        except Exception as e:
            logger.error(f"Error getting customer count: {e}")
            return 0

    def get_sales_list_paginated(self, limit: int = 500, offset: int = 0, delegated_token: str = None) -> List[Dict]:
        """Obtém sales únicos com paginação usando endpoint oficial (requer autenticação)"""
        try:
            token_to_use = delegated_token or self.delegated_token
            if not token_to_use:
                raise Exception("Authentication required - no delegated token available")
                
            all_sales = self.get_unique_sales(limit + offset, token_to_use)
            logger.info(f"Retrieved {len(all_sales)} unique sales for pagination")
            return all_sales[offset:offset + limit]
        except Exception as e:
            logger.error(f"Error getting paginated sales: {e}")
            return []

    def get_unique_sales(self, limit: int = 1000, delegated_token: str = None) -> List[Dict]:
        """Obtém lista única de sales usando o endpoint oficial salesOrders (requer autenticação)"""
        try:
            self._check_configured()
            
            # Sempre exigir token delegado
            token_to_use = delegated_token or self.delegated_token
            if not token_to_use:
                raise Exception("Authentication required - no delegated token available")
            
            sales_data = []
            
            # Usar o endpoint oficial 'salesOrders' da API Business Central
            try:
                url = f"{self.base_url}/api/v2.0/salesOrders"
                params = {
                    'company': 'SAPL-LIVE',
                    '$top': limit,
                    '$select': 'number,customerNumber,customerName,orderDate,status,totalAmountIncludingTax,currencyCode'
                }
                logger.info(f"Fetching sales from official API endpoint: {url}")
                data = self._make_request(url, params, token_to_use)
                logger.info(f"Received {len(data.get('value', []))} sales records from official API")
                
                if 'value' in data:
                    for entry in data['value']:
                        sales_data.append({
                            'No': entry.get('number', ''),
                            'Document_No': entry.get('number', ''),
                            'Customer_No': entry.get('customerNumber', ''),
                            'Customer_Name': entry.get('customerName', ''),
                            'Order_Date': entry.get('orderDate', ''),
                            'Status': entry.get('status', ''),
                            'Amount': entry.get('totalAmountIncludingTax', 0),
                            'Amount_LCY': entry.get('totalAmountIncludingTax', 0),
                            'Currency_Code': entry.get('currencyCode', '')
                        })
                        
                logger.info(f"Retrieved {len(sales_data)} unique sales records from official API")
                return sales_data
                
            except Exception as e:
                logger.error(f"Failed to get sales from official API: {e}")
                raise Exception(f"Failed to fetch sales from official API: {e}")
                
        except Exception as e:
            logger.error(f"Failed to get unique sales: {e}")
            raise

    def get_unique_shipments(self, limit: int = 1000, delegated_token: str = None) -> List[Dict]:
        """Obtém lista única de shipments usando o endpoint oficial salesShipments (requer autenticação)"""
        try:
            self._check_configured()
            
            # Sempre exigir token delegado
            token_to_use = delegated_token or self.delegated_token
            if not token_to_use:
                raise Exception("Authentication required - no delegated token available")
            
            shipments_data = []
            
            # Usar o endpoint oficial 'salesShipments' da API Business Central
            try:
                url = f"{self.base_url}/api/v2.0/salesShipments"
                params = {
                    'company': 'SAPL-LIVE',
                    '$top': limit,
                    '$select': 'number,customerNumber,customerName,postingDate,invoiceDate,dueDate,orderNumber,currencyCode,phoneNumber,email,lastModifiedDateTime'
                }
                logger.info(f"Fetching shipments from official API endpoint: {url}")
                data = self._make_request(url, params, token_to_use)
                logger.info(f"Received {len(data.get('value', []))} shipment records from official API")
                
                if 'value' in data:
                    for entry in data['value']:
                        # Usar postingDate como data principal, fallback para invoiceDate
                        shipment_date = entry.get('postingDate') or entry.get('invoiceDate') or ''
                        
                        shipments_data.append({
                            'No': entry.get('number', ''),
                            'Document_No': entry.get('number', ''),
                            'Shipment_No': entry.get('number', ''),
                            'Customer_No': entry.get('customerNumber', ''),
                            'Customer_Name': entry.get('customerName', ''),
                            'Posting_Date': entry.get('postingDate', ''),
                            'Invoice_Date': entry.get('invoiceDate', ''),
                            'Due_Date': entry.get('dueDate', ''),
                            'Shipment_Date': shipment_date,  # Data principal para exibição
                            'Order_Number': entry.get('orderNumber', ''),
                            'Currency_Code': entry.get('currencyCode', ''),
                            'Phone_Number': entry.get('phoneNumber', ''),
                            'Email': entry.get('email', ''),
                            'Last_Modified': entry.get('lastModifiedDateTime', ''),
                            'Status': 'Shipped'
                        })
                        
                logger.info(f"Retrieved {len(shipments_data)} unique shipment records from official API")
                return shipments_data
                
            except Exception as e:
                logger.error(f"Failed to get shipments from official API: {e}")
                raise Exception(f"Failed to fetch shipments from official API: {e}")
                
        except Exception as e:
            logger.error(f"Failed to get unique shipments: {e}")
            raise

    def _get_shipments_fallback(self, limit: int = 1000) -> List[Dict]:
        """Fallback method para shipments"""
        try:
            # Usar método atual como fallback
            all_shipments = self.get_real_shipment_list(limit)
            
            # Deduplicar baseado no Shipment_No ou No
            seen_shipments = set()
            unique_shipments = []
            
            for shipment in all_shipments:
                shipment_key = shipment.get('Shipment_No', shipment.get('No', ''))
                if shipment_key and shipment_key not in seen_shipments:
                    seen_shipments.add(shipment_key)
                    unique_shipments.append(shipment)
            
            logger.info(f"Found {len(unique_shipments)} unique shipments from {len(all_shipments)} total")
            return unique_shipments
            
        except Exception as e:
            logger.error(f"Error in shipments fallback: {e}")
            return []

    def _get_sales_fallback(self, limit: int = 1000) -> List[Dict]:
        """Fallback method para sales"""
        try:
            # Usar método atual como fallback
            all_sales = self.get_sales_list(limit)
            seen_sales = set()
            unique_sales = []
            
            for sale in all_sales:
                sales_key = sale.get('Document_No', sale.get('No', ''))
                if sales_key and sales_key not in seen_sales:
                    seen_sales.add(sales_key)
                    unique_sales.append(sale)
            
            logger.info(f"Retrieved {len(unique_sales)} unique sales from fallback method")
            return unique_sales
                
        except Exception as e:
            logger.error(f"Failed to get sales from fallback method: {e}")
            return []

    def get_sales_count(self, delegated_token: str = None) -> int:
        """Obtém contagem total de sales usando endpoint oficial"""
        try:
            # Usar o novo método que acessa a API oficial
            sales = self.get_unique_sales(10000, delegated_token)  # Buscar muitos para contar
            logger.info(f"Total unique sales from official API: {len(sales)}")
            return len(sales)
        except Exception as e:
            logger.error(f"Error getting sales count: {e}")
            return 0

    def get_purchase_list_paginated(self, limit: int = 500, offset: int = 0, delegated_token: str = None) -> List[Dict]:
        """Obtém compras com paginação usando endpoint oficial (requer autenticação)"""
        try:
            token_to_use = delegated_token or self.delegated_token
            if not token_to_use:
                raise Exception("Authentication required - no delegated token available")
                
            all_purchases = self.get_unique_purchases(limit + offset, token_to_use)
            logger.info(f"Retrieved {len(all_purchases)} purchases for pagination")
            return all_purchases[offset:offset + limit]
        except Exception as e:
            logger.error(f"Error getting paginated purchases: {e}")
            return []

    def get_purchase_count(self, delegated_token: str = None) -> int:
        """Obtém contagem total de compras usando endpoint oficial (requer autenticação)"""
        try:
            token_to_use = delegated_token or self.delegated_token
            if not token_to_use:
                raise Exception("Authentication required - no delegated token available")
                
            all_purchases = self.get_unique_purchases(10000, token_to_use)
            logger.info(f"Total purchases: {len(all_purchases)}")
            return len(all_purchases)
        except Exception as e:
            logger.error(f"Error getting purchase count: {e}")
            return 0

    def get_financial_entries_paginated(self, limit: int = 500, offset: int = 0, delegated_token: str = None) -> List[Dict]:
        """Obtém entries financeiras com paginação usando endpoint oficial (requer autenticação)"""
        try:
            token_to_use = delegated_token or self.delegated_token
            if not token_to_use:
                raise Exception("Authentication required - no delegated token available")
                
            all_financial = self.get_unique_financial_entries(limit + offset, token_to_use)
            logger.info(f"Retrieved {len(all_financial)} financial entries for pagination")
            return all_financial[offset:offset + limit]
        except Exception as e:
            logger.error(f"Error getting paginated financial entries: {e}")
            return []

    def get_financial_entries_count(self, delegated_token: str = None) -> int:
        """Obtém contagem total de entries financeiras usando endpoint oficial (requer autenticação)"""
        try:
            token_to_use = delegated_token or self.delegated_token
            if not token_to_use:
                raise Exception("Authentication required - no delegated token available")
                
            all_financial = self.get_unique_financial_entries(10000, token_to_use)
            logger.info(f"Total financial entries: {len(all_financial)}")
            return len(all_financial)
        except Exception as e:
            logger.error(f"Error getting financial entries count: {e}")
            return 0

    def get_shipments_list_paginated(self, limit: int = 500, offset: int = 0, delegated_token: str = None) -> List[Dict]:
        """Obtém shipments com paginação usando endpoint oficial (requer autenticação)"""
        try:
            token_to_use = delegated_token or self.delegated_token
            if not token_to_use:
                raise Exception("Authentication required - no delegated token available")
                
            all_shipments = self.get_unique_shipments(limit + offset, token_to_use)
            return all_shipments[offset:offset + limit]
        except Exception as e:
            logger.error(f"Error getting paginated shipments: {e}")
            return []

    def get_shipments_count(self, delegated_token: str = None) -> int:
        """Obtém contagem total de shipments usando endpoint oficial"""
        try:
            # Usar método único que tenta endpoint oficial primeiro
            shipments = self.get_unique_shipments(10000, delegated_token)  # Buscar muitos para contar
            return len(shipments)
        except Exception as e:
            logger.error(f"Error getting shipments count: {e}")
            return 0

    def get_real_shipment_list(self, limit: int = 1000) -> List[Dict]:
        """Obtém lista real de shipments da entidade Shipment_List do Business Central"""
        try:
            # Tentar diferentes entidades que podem conter os dados reais
            entities_to_try = [
                'salesShipments',  # Entidade real de envios de vendas
                'salesShipmentLines',  # Linhas de envios
                'Operation_Content_Excel',  # ID 50038 - Operation Content
                'opportunities',  # Oportunidades marítimas
                'shipmentMethods'  # Métodos de envio
            ]
            
            for entity in entities_to_try:
                try:
                    url = f"{self.odata_url}/Company('SAPL-LIVE')/{entity}"
                    params = {
                        '$top': limit,
                        '$orderby': 'Shipment_No desc' if 'Shipment' in entity else 'No desc'
                    }
                    
                    data = self._make_request(url, params=params)
                    
                    if data and 'value' in data and data['value']:
                        # Verificar se contém dados reais de shipments (SH25xxx)
                        sample = data['value'][0]
                        shipment_no = sample.get('Shipment_No', '') or sample.get('No', '')
                        
                        if 'SH25' in str(shipment_no):
                            logger.info(f"Found real shipment data in entity: {entity}")
                            return data['value']
                        
                        # Se não tem Shipment_No, verificar se tem outros campos de shipment
                        if any(field in sample for field in ['Vessel_Name', 'Calling_Port', 'Shipment_Type']):
                            logger.info(f"Found shipment-like data in entity: {entity}")
                            return data['value']
                            
                except Exception as entity_error:
                    logger.debug(f"Entity {entity} failed: {entity_error}")
                    continue
            
            logger.warning("No real shipment data found in any entity")
            return []
            
        except Exception as e:
            logger.error(f"Failed to get real shipment list: {e}")
            # Fallback para dados de vendas se a entidade real não estiver disponível
            logger.info("Falling back to sales data for shipments")
            return self.get_shipments_list(limit)

    def get_vendor_data_paginated(self, limit: int = 500, offset: int = 0, delegated_token: str = None) -> List[Dict]:
        """Obtém vendors únicos com paginação"""
        try:
            # Usar APENAS endpoint oficial (requer autenticação)
            token_to_use = delegated_token or self.delegated_token
            if not token_to_use:
                raise Exception("Authentication required - no delegated token available")
                
            all_vendors = self.get_unique_vendors(limit + offset, token_to_use)
            logger.info(f"Retrieved {len(all_vendors)} unique vendors for pagination")
            return all_vendors[offset:offset + limit]
        except Exception as e:
            logger.error(f"Error getting paginated vendors: {e}")
            return []

    def get_unique_vendors(self, limit: int = 1000, delegated_token: str = None) -> List[Dict]:
        """Obtém lista única de vendors usando o endpoint oficial da API (requer autenticação)"""
        try:
            self._check_configured()
            
            # Sempre exigir token delegado
            token_to_use = delegated_token or self.delegated_token
            if not token_to_use:
                raise Exception("Authentication required - no delegated token available")
            
            vendor_data = []
            
            # Usar o endpoint oficial 'vendors' da API Business Central
            try:
                url = f"{self.base_url}/api/v2.0/vendors"
                params = {
                    'company': 'SAPL-LIVE',
                    '$top': limit,
                    '$select': 'number,displayName,addressLine1,addressLine2,city,country,postalCode,phoneNumber,email,blocked,balance,currencyCode'
                }
                logger.info(f"Fetching vendors from official API endpoint: {url}")
                data = self._make_request(url, params, token_to_use)
                logger.info(f"Received {len(data.get('value', []))} vendor records from official API")
                
                if 'value' in data:
                    for entry in data['value']:
                        # Combinar endereços se necessário
                        address = entry.get('addressLine1', '')
                        if entry.get('addressLine2'):
                            address += f", {entry.get('addressLine2', '')}"
                        
                        vendor_data.append({
                            'No': entry.get('number', ''),
                            'Vendor_No': entry.get('number', ''),
                            'Name': entry.get('displayName', ''),
                            'Vendor_Name': entry.get('displayName', ''),
                            'Address': address,
                            'City': entry.get('city', ''),
                            'Country_Region_Code': entry.get('country', ''),
                            'Country_Region_Name': entry.get('country', ''),
                            'Post_Code': entry.get('postalCode', ''),
                            'Phone_No': entry.get('phoneNumber', ''),
                            'Email': entry.get('email', ''),
                            'Blocked': entry.get('blocked', ''),
                            'Balance_LCY': entry.get('balance', 0),
                            'Balance': entry.get('balance', 0),
                            'Currency_Code': entry.get('currencyCode', ''),
                            'Status': 'Active' if entry.get('blocked', '') == '_x0020_' else 'Blocked'
                        })
                        
                logger.info(f"Retrieved {len(vendor_data)} unique vendor records from official API")
                return vendor_data
                
            except Exception as e:
                logger.error(f"Failed to get vendors from official API: {e}")
                raise Exception(f"Failed to fetch vendors from official API: {e}")
                
        except Exception as e:
            logger.error(f"Failed to get unique vendors: {e}")
            raise

    def get_unique_purchases(self, limit: int = 1000, delegated_token: str = None) -> List[Dict]:
        """Obtém lista única de purchases usando o endpoint oficial purchaseInvoices (requer autenticação)"""
        try:
            self._check_configured()
            
            # Sempre exigir token delegado
            token_to_use = delegated_token or self.delegated_token
            if not token_to_use:
                raise Exception("Authentication required - no delegated token available")
            
            purchase_data = []
            
            # Usar o endpoint oficial 'purchaseInvoices' da API Business Central
            try:
                url = f"{self.base_url}/api/v2.0/purchaseInvoices"
                params = {
                    'company': 'SAPL-LIVE',
                    '$top': limit,
                    '$select': 'number,vendorNumber,vendorName,postingDate,dueDate,currencyCode,totalAmountIncludingTax,status'
                }
                logger.info(f"Fetching purchases from official API endpoint: {url}")
                data = self._make_request(url, params, token_to_use)
                logger.info(f"Received {len(data.get('value', []))} purchase records from official API")
                
                if 'value' in data:
                    for entry in data['value']:
                        purchase_data.append({
                            'No': entry.get('number', ''),
                            'Document_No': entry.get('number', ''),
                            'Vendor_No': entry.get('vendorNumber', ''),
                            'Vendor_Name': entry.get('vendorName', ''),
                            'Posting_Date': entry.get('postingDate', ''),
                            'Due_Date': entry.get('dueDate', ''),
                            'Currency_Code': entry.get('currencyCode', ''),
                            'Amount_LCY': entry.get('totalAmountIncludingTax', 0),
                            'Amount': entry.get('totalAmountIncludingTax', 0),
                            'Status': entry.get('status', '')
                        })
                        
                logger.info(f"Retrieved {len(purchase_data)} unique purchase records from official API")
                return purchase_data
                
            except Exception as e:
                logger.error(f"Failed to get purchases from official API: {e}")
                raise Exception(f"Failed to fetch purchases from official API: {e}")
                
        except Exception as e:
            logger.error(f"Failed to get unique purchases: {e}")
            raise

    def get_unique_financial_entries(self, limit: int = 1000, delegated_token: str = None) -> List[Dict]:
        """Obtém lista única de entries financeiras usando generalLedgerEntries (requer autenticação)"""
        try:
            self._check_configured()
            
            # Sempre exigir token delegado
            token_to_use = delegated_token or self.delegated_token
            if not token_to_use:
                raise Exception("Authentication required - no delegated token available")
            
            financial_data = []
            
            # Usar o endpoint oficial 'generalLedgerEntries' da API Business Central
            try:
                url = f"{self.base_url}/api/v2.0/generalLedgerEntries"
                # Começar com campos básicos apenas
                params = {
                    'company': 'SAPL-LIVE',
                    '$top': limit
                }
                logger.info(f"Fetching financial entries from official API endpoint: {url}")
                data = self._make_request(url, params, token_to_use)
                logger.info(f"Received {len(data.get('value', []))} financial records from official API")
                
                if 'value' in data:
                    for entry in data['value']:
                        financial_data.append({
                            'Entry_No': entry.get('entryNumber', ''),
                            'Posting_Date': entry.get('postingDate', ''),
                            'Document_Type': entry.get('documentType', ''),
                            'Document_No': entry.get('documentNumber', ''),
                            'Description': entry.get('description', ''),
                            'Account_Number': entry.get('accountNumber', ''),
                            'G_L_Account_No': entry.get('accountNumber', ''),  # Para compatibilidade com frontend
                            'Debit_Amount': entry.get('debitAmount', 0),
                            'Credit_Amount': entry.get('creditAmount', 0),
                            'Amount': (entry.get('debitAmount', 0) - entry.get('creditAmount', 0)),  # Balance calculado
                            'Balance': (entry.get('debitAmount', 0) - entry.get('creditAmount', 0)),  # Para compatibilidade
                            'Currency_Code': 'EUR'  # Assumir EUR como padrão
                        })
                        
                logger.info(f"Retrieved {len(financial_data)} unique financial records from official API")
                return financial_data
                
            except Exception as e:
                logger.error(f"Failed to get financial entries from official API: {e}")
                # Retornar lista vazia em vez de falhar completamente
                logger.warning("Returning empty financial data due to API error")
                return []
                
        except Exception as e:
            logger.error(f"Failed to get unique financial entries: {e}")
            return []

    def get_unique_vessels(self, limit: int = 1000, delegated_token: str = None) -> List[Dict]:
        """Obtém lista única de vessels usando salesShipments (requer autenticação)"""
        try:
            self._check_configured()
            
            # Sempre exigir token delegado
            token_to_use = delegated_token or self.delegated_token
            if not token_to_use:
                raise Exception("Authentication required - no delegated token available")
            
            vessels_data = []
            
            # Usar o endpoint oficial 'salesShipments' da API Business Central para identificar vessels
            try:
                url = f"{self.base_url}/api/v2.0/salesShipments"
                params = {
                    'company': 'SAPL-LIVE',
                    '$top': limit,
                    '$select': 'number,customerNumber,customerName,postingDate,orderNumber,currencyCode'
                }
                logger.info(f"Fetching vessels data from salesShipments endpoint: {url}")
                data = self._make_request(url, params, token_to_use)
                logger.info(f"Received {len(data.get('value', []))} shipment records for vessels")
                
                # Extrair informações de vessels únicos baseado nos shipments
                seen_vessels = set()
                
                if 'value' in data:
                    for entry in data['value']:
                        # Usar customer como identificador de vessel (navio)
                        vessel_key = entry.get('customerNumber', '')
                        vessel_name = entry.get('customerName', '')
                        
                        if vessel_key and vessel_key not in seen_vessels:
                            seen_vessels.add(vessel_key)
                            
                            # Buscar informações adicionais do customer se necessário
                            vessels_data.append({
                                'Vessel_No': vessel_key,
                                'Vessel_Name': vessel_name,
                                'Customer_No': vessel_key,
                                'Customer_Name': vessel_name,
                                'Last_Shipment_Date': entry.get('postingDate', ''),
                                'Currency_Code': entry.get('currencyCode', ''),
                                'Status': 'Active'  # Assumir ativo se tem shipments
                            })
                        
                logger.info(f"Retrieved {len(vessels_data)} unique vessels from shipments data")
                return vessels_data
                
            except Exception as e:
                logger.error(f"Failed to get vessels from salesShipments: {e}")
                raise Exception(f"Failed to fetch vessels from salesShipments: {e}")
                
        except Exception as e:
            logger.error(f"Failed to get unique vessels: {e}")
            raise

    def _get_vendors_fallback(self, limit: int = 1000) -> List[Dict]:
        """Fallback method usando Power_BI_Vendor_List"""
        try:
            vendor_data = []
            url = f"{self.odata_url}/Company('SAPL-LIVE')/Power_BI_Vendor_List"
            params = {
                '$top': limit,
                '$select': 'Vendor_No,Vendor_Name,Balance_Due'
            }
            data = self._make_request(url, params)
            
            if 'value' in data:
                # Remover duplicatas baseado no Vendor_No
                seen_vendors = set()
                for entry in data['value']:
                    vendor_no = entry.get('Vendor_No', '')
                    if vendor_no and vendor_no not in seen_vendors:
                        seen_vendors.add(vendor_no)
                        vendor_data.append({
                            'No': vendor_no,
                            'Vendor_No': vendor_no,
                            'Name': entry.get('Vendor_Name', ''),
                            'Vendor_Name': entry.get('Vendor_Name', ''),
                            'Balance_Due': entry.get('Balance_Due', 0),
                            'Balance_LCY': entry.get('Balance_Due', 0),
                            'Balance': entry.get('Balance_Due', 0),
                            'City': '',
                            'Country_Region_Code': '',
                            'Country_Region_Name': '',
                            'Status': 'Active'
                        })
                        
            logger.info(f"Retrieved {len(vendor_data)} unique vendors from fallback method")
            return vendor_data
                
        except Exception as e:
            logger.error(f"Failed to get vendors from fallback method: {e}")
            return []

    def get_vendor_count(self, delegated_token: str = None) -> int:
        """Obtém contagem total de vendors"""
        try:
            token_to_use = delegated_token or self.delegated_token
            if not token_to_use:
                raise Exception("Authentication required - no delegated token available")
                
            all_vendors = self.get_unique_vendors(10000, token_to_use)
            logger.info(f"Total unique vendors: {len(all_vendors)}")
            return len(all_vendors)
        except Exception as e:
            logger.error(f"Error getting vendor count: {e}")
            return 0

# Instância global do serviço
bc_service = BusinessCentralService()
