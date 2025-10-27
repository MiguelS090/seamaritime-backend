import logging
from typing import Dict, Any, List, Optional
from langchain.tools import tool
from pydantic import Field
from app.AI.chat_graph.q88_state import Q88LLMResult, Q88LLMFields, Q88LLMSummary, Q88FieldData
from app.services.azure_ocr_service import AzureOCRService
from app.AI.shared.models.structured_llm import get_structured_azure_model
import json
import time
import re

logger = logging.getLogger(__name__)

class Q88ExtractionTool:
    """
    Tool para extração estruturada de campos Q88 usando IA com Structured Output.
    
    Esta classe usa Azure OpenAI com structured output nativo, garantindo que
    a resposta do modelo sempre siga o schema Q88LLMResult sem necessidade de
    parsing manual ou correção de JSON malformado.
    
    Suporta todos os tipos de Q88: Oil Tanker, Gas/LPG, Chemical Tanker
    """
    
    def __init__(self):
        # Usar structured output ao invés de modelo genérico
        self.structured_llm = get_structured_azure_model(
            schema=Q88LLMResult,
            model_name="gpt-4o",  # Voltar ao modelo original mais confiável
            temperature=0.0,
            max_tokens=8000  # Otimizado para 50 campos essenciais para Business Central
        )
        
        # Mapeamento unificado de campos Q88
        self.unified_fields = self._get_unified_q88_fields()
        
        # Mapeamento específico por tipo (campos adicionais)
        self.type_specific_fields = {
            'oil_tanker': self._get_oil_tanker_specific_fields(),
            'gas_lpg': self._get_gas_lpg_specific_fields(), 
            'chemical': self._get_chemical_specific_fields()
        }
    
    def extract_q88_fields_structured(self, ocr_text: str, ocr_metadata: Dict[str, Any]) -> Q88LLMResult:
        """
        Extração inteligente via IA usando Structured Output nativo com otimização de performance.
        
        Este método usa Azure OpenAI com structured output, garantindo que a resposta
        seja sempre um objeto Q88LLMResult validado, sem necessidade de parsing manual.
        
        Suporta: Oil Tanker, Gas/LPG, Chemical Tanker
        
        Args:
            ocr_text: Texto extraído pelo OCR
            ocr_metadata: Metadados do OCR (tabelas, páginas, etc.)
            
        Returns:
            Q88LLMResult: Resultado estruturado e validado automaticamente
        """
        try:
            # 1. Detectar tipo de Q88 automaticamente
            q88_type = self._detect_q88_type(ocr_text)
            
            # 2. Criar prompt otimizado para o tipo detectado
            prompt = self._create_typed_prompt(ocr_text, ocr_metadata, q88_type)
            
            # 3. ✅ STRUCTURED OUTPUT - Chamar modelo estruturado
            result = self.structured_llm.invoke(prompt)
            
            # 5. Validar e completar campos em falta (se necessário)
            result = self._validate_and_complete_fields(result, q88_type)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro na extração via IA: {str(e)}")
            logger.exception("Detalhes do erro:")
            return self._create_empty_result(f"Erro IA: {str(e)}")
    
    def _detect_q88_type(self, ocr_text: str) -> str:
        """Detecta automaticamente o tipo de Q88 baseado no conteúdo"""
        text_lower = ocr_text.lower()
        
        # Detectar Oil Tanker
        oil_indicators = ['oil tanker', 'crude oil', 'product tanker', 'double hull', 'cargo oil', 'oil pollution']
        if any(indicator in text_lower for indicator in oil_indicators):
            return 'oil_tanker'
        
        # Detectar Gas/LPG
        gas_indicators = ['lpg', 'lng', 'liquefied gas', 'gas carrier', 'propane', 'butane', 'vcm', 'vinyl chloride']
        if any(indicator in text_lower for indicator in gas_indicators):
            return 'gas_lpg'
        
        # Detectar Chemical
        chemical_indicators = ['chemical tanker', 'chemical carrier', 'imo type', 'certificate of fitness', 'chemicals']
        if any(indicator in text_lower for indicator in chemical_indicators):
            return 'chemical'
        
        # Default para Oil Tanker se não conseguir detectar
        return 'oil_tanker'
    
    def _get_unified_q88_fields(self) -> Dict[str, List[str]]:
        """Campos otimizados para Business Central Integration - apenas campos essenciais"""
        return {
            # ===== VESSEL INFORMATION (Essencial para BC) =====
            'VesselName': ['vessel\'s name', 'vessel name', '1.1 vessel\'s name', '1.2 vessel\'s name', 'vessel\'s name:', 'vessel name:', 'name of vessel', 'ship name'],
            'IMONumber': ['imo number', 'imo', '1.3 imo number', '1.1 vessel\'s name (imo number)', 'imo number:', 'imo:', 'imo no', 'imo no.'],
            'Flag': ['flag', '1.7 flag', 'flag/port of registry', '1.2 flag/port of registry'],
            'CallSign': ['call sign', '1.9 call sign', 'call sign/mmsi', '1.5 call sign/mmsi'],
            'VesselType': ['type of vessel', '1.11 type of vessel', 'oil tanker', 'lpg carrier', 'lng carrier', 'gas carrier', 'chemical tanker', 'chemical carrier'],
            'MMSI': ['mmsi', 'call sign/mmsi', '1.5 call sign/mmsi'],
            'PortOfRegistry': ['port of registry', '1.8 port of registry', 'flag/port of registry', '1.2 flag/port of registry'],
            'DateUpdated': ['date updated', 'last updated', 'update date'],
            'PreviousName': ['previous name', 'vessel\'s previous name', 'former name'],
            
            # ===== OWNERSHIP (Crítico para BC) =====
            'RegisteredOwner': ['registered owner', '1.10 registered owner', '1.13 registered owner', 'owner'],
            'TechnicalOperator': ['technical operator', '1.11 technical operator', '1.14 technical operator'],
            'CommercialOperator': ['commercial operator', '1.12 commercial operator', '1.15 commercial operator'],
            'DisponentOwner': ['disponent owner', '1.13 disponent owner', '1.16 disponent owner'],
            
            # ===== DIMENSIONS & TONNAGES (Relevante para BC) =====
            'LOA': ['length overall', 'loa', '1.27 length overall', '1.18 length overall'],
            'Beam': ['extreme breadth', 'beam', '1.29 extreme breadth', '1.19 extreme breadth'],
            'GrossTonnage': ['gross tonnage', '1.36 gross tonnage', '1.22 gross tonnage', 'gt', '1.36', 'gross tonnage/reduced gross tonnage'],
            'NetTonnage': ['net tonnage', '1.35 net tonnage', '1.23 net tonnage', 'nt', '1.35'],
            'SummerDWT': ['summer dwt', '1.37 summer dwt', '1.24 summer dwt', 'summer deadweight'],
            'WinterDWT': ['winter dwt', '1.38 winter dwt', '1.25 winter dwt', 'winter deadweight'],
            'TropicalDWT': ['tropical dwt', '1.39 tropical dwt', '1.26 tropical dwt', 'tropical deadweight'],
            
            # ===== CONTACT DETAILS (Melhorado para BC) =====
            'ContactDetails': ['contact details', 'satcom', 'email', 'phone', 'fax', 'telex'],
            'MasterEmail': ['master email', 'email', 'master\'s email', 'captain email'],
            'MasterPhone': ['master phone', 'phone', 'master\'s phone', 'captain phone'],
            'InmarsatNumber': ['inmarsat', 'inmarsat number', 'satcom number', 'satellite number'],
            'MasterPIC': ['master pic', 'master', 'captain', 'master\'s name', 'captain\'s name'],
            
            # ===== CLASSIFICATION (Importante para compliance) =====
            'ClassificationSociety': ['classification society', '1.18 classification society', '1.7 classification society'],
            'ClassNotation': ['class notation', '1.19 class notation', '1.8 class notation'],
            'ClassConditions': ['class conditions', 'conditions of class'],
            'LastDryDock': ['last dry dock', '1.21 last dry dock', 'date/place of last dry-dock'],
            'NextDryDockDue': ['next dry dock due', '1.22 next dry dock due'],
            'NextAnnualSurveyDue': ['next annual survey due', 'annual survey'],
            
            # ===== INSURANCE (Relevante para operações) =====
            'PIClub': ['p & i club', '1.14 p & i club', '1.16 p & i club', 'p&i club'],
            'HullMachineryInsurer': ['hull & machinery insured by', '1.16 hull & machinery'],
            'HullMachineryValue': ['hull & machinery insured value', '1.17 hull & machinery value'],
            'ExpirationDate': ['expiration date', 'expiry date', 'valid until'],
            
            # ===== CONSTRUCTION (Informação básica) =====
            'Builder': ['builder', '1.5 builder', 'where built', 'date delivered/builder', '1.3 date delivered/builder'],
            'DateDelivered': ['date delivered', '1.4 date delivered', 'date delivered/builder', '1.3 date delivered/builder'],
            
            # ===== CERTIFICATES ESSENCIAIS (Compliance) =====
            'ISM': ['ism', 'safety management certificate', '2.7'],
            'DOC': ['document of compliance', 'doc', '2.8'],
            'IOPPC': ['international oil pollution prevention certificate', 'ioppc', '2.5'],
            'ISSC': ['international ship security certificate', 'issc', '2.14'],
            'MLC': ['maritime labour convention', 'mlc', '2.7'],
            'IAPP': ['international air pollution prevention certificate', 'iapp', '2.17'],
            
            # ===== CREW (Informação operacional) =====
            'CrewNationality': ['crew nationality', 'nationality of crew', 'crew composition'],
            'NumberOfOfficers': ['number of officers', 'officers', 'deck officers', 'engine officers'],
            'NumberOfCrew': ['number of crew', 'total crew', 'crew members'],
            'WorkingLanguage': ['working language', 'language', 'communication language'],
            'ManningAgency': ['manning agency', 'crew agency', 'manning company'],
            
            # ===== CARGO CAPABILITIES (Relevante para operações) =====
            'DoubleHullVessel': ['double hull', 'double hull vessel', 'hull type', '1.12 type of hull'],
            'MaxLoadingRate': ['maximum loading rate', 'max loading rate', 'loading rate'],
            'CargoRestrictions': ['cargo restrictions', 'restrictions', 'cargo limitations'],
            'MaxCargoTemp': ['maximum cargo temperature', 'max cargo temp', 'cargo temperature'],
            
            # ===== PROPULSION (Informação técnica básica) =====
            'MainEngineType': ['main engine type', 'engine type', 'main engine'],
            'MainEngineHP': ['main engine hp', 'engine horsepower', 'main engine power'],
            'BallastSpeed': ['ballast speed', 'speed in ballast', 'ballast condition speed'],
            'LadenSpeed': ['laden speed', 'speed when laden', 'loaded speed'],
            'FuelType': ['fuel type', 'bunker fuel', 'fuel oil type'],
            
            # ===== RECENT HISTORY (Operacional) =====
            'LastThreeCargoes': ['last three cargoes', 'recent cargoes', 'previous cargoes'],
            'SIREDate': ['sire date', 'sire inspection', 'sire inspection date'],
            'PortStateDeficiencies': ['port state deficiencies', 'deficiencies', 'port state control'],
            'AdditionalInfo': ['additional information', 'remarks', 'notes', 'comments']
        }
    
    def _get_oil_tanker_specific_fields(self) -> Dict[str, List[str]]:
        """Campos específicos para Oil Tanker - OTIMIZADO"""
        return {
            # Campos específicos já incluídos nos campos unificados otimizados
        }
    
    def _get_gas_lpg_specific_fields(self) -> Dict[str, List[str]]:
        """Campos específicos para Gas/LPG - OTIMIZADO"""
        return {
            # Campos específicos já incluídos nos campos unificados otimizados
        }
    
    def _get_chemical_specific_fields(self) -> Dict[str, List[str]]:
        """Campos específicos para Chemical Tanker - OTIMIZADO"""
        return {
            # Campos específicos já incluídos nos campos unificados otimizados
        }
    
    # Métodos antigos removidos - usando apenas _get_unified_q88_fields otimizado
    
    def _create_typed_prompt(self, ocr_text: str, ocr_metadata: Dict[str, Any], q88_type: str) -> str:
        """Cria prompt específico para o tipo de Q88 detectado"""
        # Combinar campos unificados com campos específicos do tipo
        unified_fields = self.unified_fields
        specific_fields = self.type_specific_fields.get(q88_type, {})
        
        # Combinar todos os campos
        field_mappings = {**unified_fields, **specific_fields}
        
        # Informações sobre tabelas se existirem
        tables_info = ""
        if ocr_metadata.get('tables'):
            tables_info = f"\n\nTABELAS ENCONTRADAS ({len(ocr_metadata['tables'])}):\n"
            for i, table in enumerate(ocr_metadata['tables']):
                tables_info += f"Tabela {i+1}: {table.get('row_count', 0)} linhas x {table.get('column_count', 0)} colunas\n"
        
        # Criar lista de campos esperados
        expected_fields = list(field_mappings.keys())
        fields_list = "\n".join([f"- {field}: {', '.join(patterns)}" for field, patterns in field_mappings.items()])
        
        # Prompt otimizado para 50 campos essenciais para Business Central
        prompt = f"""Extract Q88 maritime document fields for Business Central integration:

TEXT: {ocr_text[:15000]}{'...' if len(ocr_text) > 15000 else ''}

INSTRUCTIONS:
1. Extract values for {len(expected_fields)} ESSENTIAL fields for Business Central
2. Use "Not Found" only if field is truly missing
3. Focus on vessel identification, ownership, dimensions, and operational data
4. For PDFs: values may be on next line after label - LOOK CAREFULLY!

KEY EXTRACTION PATTERNS:
- Vessel Info: "Vessel's name: SHIP NAME" → VesselName: "SHIP NAME"
- IMO: "IMO: 1234567" → IMONumber: "1234567"
- Ownership: "Registered owner:" → RegisteredOwner: "Company Name"
- Dimensions: "Length overall: 184.95 Metres" → LOA: "184.95 Metres"
- Tonnages: "Gross Tonnage: 29,593.00" → GrossTonnage: "29,593.00"
- DWT: "Summer DWT: 45,853.00 Metric Tonnes" → SummerDWT: "45,853.00 Metric Tonnes"
- Contact: "Email: brave@company.com" → MasterEmail: "brave@company.com"
- Certificates: "ISM: Jul 16, 2025" → ISM: "Jul 16, 2025"
- Crew: "Number of officers: 9" → NumberOfOfficers: "9"
- Engine: "Main engine: HUDONG 6S50MCC" → MainEngineType: "HUDONG 6S50MCC"

ESSENTIAL FIELDS TO EXTRACT:
{chr(10).join([f"- {field}" for field in expected_fields])}

Return structured JSON with fields and summary. Focus on Business Central relevant data."""
        return prompt
    
    def _generate_json_template(self, fields: List[str]) -> str:
        """Gera template JSON para os campos"""
        template_lines = []
        for field in fields:
            template_lines.append(f'    "{field}": {{"value": "valor encontrado ou Not Found", "confidence": 0.9, "source": "ai-extraction", "raw_text": "texto original"}}')
        return ",\n".join(template_lines)
    
    def _parse_structured_response(self, response_content: str, q88_type: str) -> Q88LLMResult:
        """
        ⚠️ MÉTODO OBSOLETO - Mantido apenas para compatibilidade
        
        Este método fazia parsing manual de JSON retornado pelo modelo.
        Com structured output nativo, este parsing não é mais necessário.
        
        DEPRECADO: Será removido na próxima versão.
        """
        try:
            # Limpar resposta da IA
            cleaned_response = response_content.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            
            # Encontrar JSON na resposta
            json_start = cleaned_response.find('{')
            json_end = cleaned_response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("Nenhum JSON encontrado na resposta")
            
            json_str = cleaned_response[json_start:json_end]
            
            # Tentar corrigir JSON malformado
            try:
                parsed_data = json.loads(json_str)
            except json.JSONDecodeError as json_error:
                logger.warning(f"⚠️ JSON malformado, tentando corrigir: {str(json_error)}")
                json_str = self._fix_malformed_json(json_str)
                parsed_data = json.loads(json_str)
            
            # Validar estrutura
            if 'fields' not in parsed_data or 'summary' not in parsed_data:
                raise ValueError("Resposta da IA não contém campos 'fields' e 'summary'")
            
            # Converter campos
            fields_data = {}
            for field_name, field_info in parsed_data['fields'].items():
                if field_info and isinstance(field_info, dict):
                    value = field_info.get('value')
                    
                    # Tratamento: se não há valor, usar "Not Found"
                    if not value or value == "null" or (isinstance(value, str) and value.strip() == ""):
                        value = "Not Found"
                    
                    fields_data[field_name] = Q88FieldData(
                        value=value,
                        confidence=field_info.get('confidence', 0.8),
                        source=field_info.get('source', 'ai-extraction'),
                        raw_text=field_info.get('raw_text')
                    )
                else:
                    # Se field_info é None ou não é dict, criar campo com "Not Found"
                    logger.warning(f"⚠️ Campo {field_name} tem dados inválidos: {field_info}")
                    fields_data[field_name] = Q88FieldData(
                        value="Not Found",
                        confidence=0.0,
                        source="ai-extraction",
                        raw_text="Invalid field data"
                    )
            
            # Garantir summary
            summary_data = parsed_data.get('summary', {})
            summary_data.setdefault('document_type', f'Q88 ({q88_type.upper()})')
            summary_data.setdefault('processing_notes', 'Extração completa')
            
            # Calcular estatísticas do summary
            found_fields = sum(1 for field_data in fields_data.values() 
                             if field_data.value != "Not Found")
            total_fields = len(fields_data)
            completion_percentage = (found_fields / total_fields) * 100 if total_fields > 0 else 0.0
            
            summary_data.setdefault('total_fields_found', found_fields)
            summary_data.setdefault('total_fields_expected', total_fields)
            summary_data.setdefault('completion_percentage', completion_percentage)
            
            # Normalizar e filtrar campos desconhecidos antes de instanciar o Pydantic
            try:
                allowed_fields = set(getattr(Q88LLMFields, '__fields__', {}) or getattr(Q88LLMFields, 'model_fields', {}).keys())
            except Exception:
                allowed_fields = set()

            # Mapeamentos de sinónimos vindos do LLM para os nomes suportados
            synonym_mapping = {
                'CertificateOfFitnessGas': 'COFGas',
                'CertificateOfFitnessChemicals': 'COFChemicals',
                'CertificateOfClass': 'CertificateOfClass',
                # adicionar outros se surgirem
            }

            normalized_fields_data = {}
            for key, value in fields_data.items():
                mapped_key = synonym_mapping.get(key, key)
                if not allowed_fields or mapped_key in allowed_fields:
                    normalized_fields_data[mapped_key] = value
                else:
                    logger.debug(f"🔎 Ignorando campo não suportado pelo schema: {key}")

            # Criar objetos Pydantic
            fields = Q88LLMFields(**normalized_fields_data)
            summary = Q88LLMSummary(**summary_data)
            
            return Q88LLMResult(fields=fields, summary=summary)
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar resposta da IA: {str(e)}")
            return self._create_empty_result(f"Erro no parsing: {str(e)}")
    
    def _validate_and_complete_fields(self, result: Q88LLMResult, q88_type: str) -> Q88LLMResult:
        """Valida e completa campos em falta baseado no tipo de Q88"""
        # Combinar campos unificados com campos específicos do tipo
        unified_fields = self.unified_fields
        specific_fields = self.type_specific_fields.get(q88_type, {})
        field_mappings = {**unified_fields, **specific_fields}
        expected_fields = list(field_mappings.keys())

        # Campos suportados no schema Pydantic
        try:
            allowed_fields = set(getattr(Q88LLMFields, '__fields__', {}) or getattr(Q88LLMFields, 'model_fields', {}).keys())
        except Exception:
            allowed_fields = set()

        # Sinónimos que o LLM pode emitir ou que existam no mapeamento
        synonym_mapping = {
            'CertificateOfFitnessGas': 'COFGas',
            'CertificateOfFitnessChemicals': 'COFChemicals',
        }
        
        # Adicionar campos em falta como "Not Found"
        for field_name in expected_fields:
            normalized_name = synonym_mapping.get(field_name, field_name)
            if allowed_fields and normalized_name not in allowed_fields:
                continue
            if not hasattr(result.fields, normalized_name):
                setattr(result.fields, normalized_name, Q88FieldData(
                    value="Not Found",
                    confidence=0.0,
                    source="validation",
                    raw_text=""
                ))
        
        # Recalcular summary
        found_fields = 0
        for field_name in expected_fields:
            normalized_name = synonym_mapping.get(field_name, field_name)
            field_obj = getattr(result.fields, normalized_name, None)
            field_value = getattr(field_obj, 'value', 'Not Found') if field_obj is not None else 'Not Found'
            if field_value != 'Not Found':
                found_fields += 1
        
        result.summary.total_fields_found = found_fields
        # Só contar campos realmente suportados para o total esperado
        supported_expected = [synonym_mapping.get(n, n) for n in expected_fields if (not allowed_fields or synonym_mapping.get(n, n) in allowed_fields)]
        result.summary.total_fields_expected = len(supported_expected)
        result.summary.completion_percentage = (
            (found_fields / result.summary.total_fields_expected) * 100 if result.summary.total_fields_expected else 0.0
        )
        
        return result
    
    def _create_empty_result(self, error_message: str) -> Q88LLMResult:
        """Cria resultado vazio em caso de erro"""
        return Q88LLMResult(
            fields=Q88LLMFields(),
            summary=Q88LLMSummary(
                total_fields_found=0,
                total_fields_expected=50,
                completion_percentage=0.0,
                document_type="Q88 (UNKNOWN)",
                processing_notes=error_message
            )
        )
    
    def _fix_malformed_json(self, json_str: str) -> str:
        """
        ⚠️ MÉTODO OBSOLETO - Mantido apenas para compatibilidade
        
        Com structured output nativo, o modelo NUNCA retorna JSON malformado.
        
        DEPRECADO: Será removido na próxima versão.
        """

        # Corrigir vírgulas em falta antes de }
        json_str = re.sub(r'(\w+)\s*}', r'\1}', json_str)
        
        # Corrigir vírgulas em falta antes de ]
        json_str = re.sub(r'(\w+)\s*]', r'\1]', json_str)
        
        # Corrigir aspas em falta
        json_str = re.sub(r':\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*[,}]', r': "\1"\2', json_str)
        
        # Remover vírgulas extras antes de }
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        
        return json_str

@tool
def extract_q88_fields_structured_tool(ocr_text: str, ocr_metadata: Dict[str, Any]) -> Q88LLMResult:
    """
    Extrai campos Q88 de forma estruturada usando IA com detecção automática de tipo.
    Suporta: Oil Tanker, Gas/LPG, Chemical Tanker
    
    Args:
        ocr_text: Texto extraído pelo OCR
        ocr_metadata: Metadados do OCR (páginas, linhas, tabelas)
        
    Returns:
        Q88LLMResult: Resultado estruturado com campos e summary
    """
    tool = Q88ExtractionTool()
    return tool.extract_q88_fields_structured(ocr_text, ocr_metadata)

@tool
def process_q88_document_ocr(file_path: str) -> Dict[str, Any]:
    """
    Processa documento Q88 usando Azure OCR para extrair texto.
    
    Args:
        file_path: Caminho para o ficheiro Q88
        
    Returns:
        Dict com texto extraído e metadados
    """
    try:
        ocr_service = AzureOCRService()
        result = ocr_service.process_q88_document(file_path)
        return result
        
    except Exception as e:
        return {
            "fullText": "",
            "organizedLines": [],
            "tables": [],
            "totalPages": 0,
            "error": str(e)
        }

def get_q88_tools():
    """Retorna lista de tools para processamento Q88"""
    return [
        process_q88_document_ocr,
        extract_q88_fields_structured_tool
    ]