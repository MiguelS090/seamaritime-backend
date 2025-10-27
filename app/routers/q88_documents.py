from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
import json
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.patch("/q88/documents/{filename}/fields")
async def update_q88_field(
    filename: str,
    request: Dict[str, Any]
):
    """
    Atualiza um campo específico de um documento Q88
    """
    try:
        # Extrair dados do JSON
        field_name = request.get('field_name')
        new_value = request.get('new_value')
        edited_by = request.get('edited_by', 'user')
        
        if not field_name or not new_value:
            raise HTTPException(status_code=400, detail="field_name and new_value are required")
        
        # Caminho para o arquivo JSON
        documents_dir = Path("documents/processed")
        # Se filename não tem extensão, adicionar .json
        if not filename.endswith('.json'):
            filename = f"{filename}.json"
        file_path = documents_dir / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Ler o arquivo atual
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Atualizar o campo específico
        if 'llm_result' in data and 'fields' in data['llm_result']:
            if field_name in data['llm_result']['fields']:
                # Atualizar o valor do campo
                data['llm_result']['fields'][field_name]['value'] = new_value
                data['llm_result']['fields'][field_name]['confidence'] = 1.0  # Confiança máxima para edições manuais
                data['llm_result']['fields'][field_name]['source'] = 'manual_edit'
                data['llm_result']['fields'][field_name]['edited_by'] = edited_by
                
                # Salvar o arquivo atualizado
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Field {field_name} updated in {filename} by {edited_by}")
                
                return {
                    "success": True,
                    "message": f"Field {field_name} updated successfully",
                    "updated_field": {
                        "field_name": field_name,
                        "new_value": new_value,
                        "confidence": 1.0,
                        "source": "manual_edit",
                        "edited_by": edited_by
                    }
                }
            else:
                raise HTTPException(status_code=404, detail=f"Field {field_name} not found in document")
        else:
            raise HTTPException(status_code=400, detail="Invalid document structure")
            
    except Exception as e:
        logger.error(f"Error updating field {field_name} in {filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating field: {str(e)}")

@router.get("/q88/documents")
async def get_q88_documents():
    """
    Lista todos os documentos Q88 processados
    """
    try:
        documents_dir = Path("documents/processed")
        documents = []
        
        if not documents_dir.exists():
            return {"documents": []}
        
        for file_path in documents_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Extrair informações básicas do documento
                vessel_name = "Unknown"
                imo = "Unknown"
                port = "Unknown"
                terminal = "Unknown"
                status = "Processed"
                confidence = 95
                extracted_fields = 0
                processing_date = "Unknown"
                
                if 'llm_result' in data and 'fields' in data['llm_result']:
                    fields = data['llm_result']['fields']
                    extracted_fields = len([f for f in fields.values() if f.get('value') and f['value'] != 'Not Found'])
                    
                    # Tentar extrair informações básicas
                    vessel_name = fields.get('VesselName', {}).get('value', 'Unknown')
                    imo = fields.get('IMONumber', {}).get('value', 'Unknown')
                    port = fields.get('Port', {}).get('value', 'Unknown')
                    terminal = fields.get('Terminal', {}).get('value', 'Unknown')
                    
                    # Calcular confiança média
                    confidences = [f.get('confidence', 0) for f in fields.values() if f.get('confidence')]
                    if confidences:
                        confidence = round(sum(confidences) / len(confidences) * 100)
                
                # Extrair data de processamento do nome do arquivo ou metadados
                if 'processing_date' in data:
                    processing_date = data['processing_date']
                elif 'timestamp' in data:
                    processing_date = data['timestamp']
                else:
                    # Tentar extrair do nome do arquivo (formato: VesselName_IMO_YYYYMMDD_HHMMSS.json)
                    parts = file_path.stem.split('_')
                    if len(parts) >= 4:
                        try:
                            date_part = parts[-2]
                            time_part = parts[-1]
                            processing_date = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
                        except:
                            processing_date = file_path.stem
                
                documents.append({
                    "id": file_path.stem,
                    "filename": file_path.name,
                    "vesselName": vessel_name,
                    "imo": imo,
                    "port": port,
                    "terminal": terminal,
                    "status": status,
                    "confidence": confidence,
                    "extractedFields": extracted_fields,
                    "processingDate": processing_date,
                    "dateProcessed": processing_date,
                    "data": data  # Incluir dados completos para o modal
                })
                
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                continue
        
        # Ordenar por data de processamento (mais recente primeiro)
        documents.sort(key=lambda x: x.get('processingDate', ''), reverse=True)
        
        return {"documents": documents}
        
    except Exception as e:
        logger.error(f"Error fetching Q88 documents: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching documents: {str(e)}")