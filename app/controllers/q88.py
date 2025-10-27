import logging
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.q88 import Q88Form as Q88FormModel, Q88Section as Q88SectionModel, Q88Field as Q88FieldModel
from app.schemas.q88 import Q88Form, Q88Section, Q88Field, Q88FormResponse, FieldType
from app.services.azure_ocr_service import AzureOCRService
from app.AI.chat_graph.q88_chat_graph import Q88ChatGraph
from app.services.q88_document_service import Q88DocumentService

logger = logging.getLogger(__name__)

class Q88Controller:
    """Controller para gerenciar formulários Q88"""
    
    def __init__(self):
        self.ocr_service = AzureOCRService()
        self.q88_chat_graph = Q88ChatGraph()
        self.document_service = Q88DocumentService()
    
    async def create_q88_form(self, file: UploadFile = File(...), db: Session = None) -> Q88FormResponse:
        """Cria um novo formulário Q88 usando o método antigo (compatibilidade)"""
        try:
            # Salvar arquivo
            file_path = await self._save_uploaded_file(file)
            
            try:
                # 1. Extrair TODO o texto com Azure Document Intelligence
                logger.info("📄 Etapa 1: Extraindo texto completo do documento...")
                extracted_data = self.ocr_service.process_q88_document(file_path)
                
                # 2. Processar com IA para identificar campos Q88 (método antigo)
                logger.info("🤖 Etapa 2: Processando com IA para identificar campos...")
                # Usar método antigo por compatibilidade
                ai_processed_data = await self._process_with_old_ai(extracted_data)
                
                # 3. Converter resultado para estrutura Q88
                logger.info("🔄 Etapa 3: Convertendo para estrutura Q88...")
                q88_form = self._convert_ai_result_to_q88_form(ai_processed_data, file.filename, file_path)
                
                # 4. Salvar no banco de dados
                logger.info("💾 Etapa 4: Salvando no banco de dados...")
                db_form = await self._save_q88_form_to_db(q88_form, db)
                
                # 5. Retornar resposta
                return Q88FormResponse(
                    form_id=db_form.form_id,
                    sections=db_form.sections,
                    processing_status=db_form.processing_status,
                    created_at=db_form.created_at,
                    updated_at=db_form.updated_at,
                    file_path=db_form.file_path,
                    ocr_model_version=db_form.ocr_model_version,
                    total_confidence_score=db_form.total_confidence_score,
                    completion_percentage=db_form.get_completion_percentage(),
                    fields_needing_review=len(db_form.get_all_fields_needing_review())
                )
                
            except Exception as processing_error:
                logger.error(f"❌ Erro no processamento AI: {str(processing_error)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Erro no processamento: {str(processing_error)}"
                )
            finally:
                # Limpar arquivo temporário
                if Path(file_path).exists():
                    Path(file_path).unlink()
                    
        except Exception as e:
            logger.error(f"❌ Erro geral no controller: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Erro interno: {str(e)}"
            )
    
    async def create_q88_form_ai(self, file: UploadFile = File(...), db: Session = None) -> Q88FormResponse:
        """Cria um novo formulário Q88 usando o novo fluxo AI"""
        try:
            # Salvar arquivo
            file_path = await self._save_uploaded_file(file)
            
            try:
                # 1. Extrair TODO o texto com Azure Document Intelligence
                logger.info("📄 Etapa 1: Extraindo texto completo do documento...")
                ocr_result = self.ocr_service.process_q88_document(file_path)
                
                # 2. IA mapeia tokens para campos Q88 (detecção automática de tipo)
                logger.info("🧠 Etapa 2: Mapeando tokens para campos Q88 com IA...")
                from app.AI.chat_graph.tools.q88_tools import extract_q88_fields_structured_tool
                
                # Otimização: usar await para processamento assíncrono
                ai_result = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    extract_q88_fields_structured_tool,
                    ocr_result.get('fullText', ''),
                    ocr_result
                )
                
                # 3. Convert AI result to Q88Form format
                logger.info("🔄 Step 3: Converting AI result to Q88 format...")
                q88_form = self._convert_ai_result_to_q88_form(ai_result, file.filename, file_path)
                
                # 4. Save to database
                logger.info("💾 Step 4: Saving to database...")
                db_form = await self._save_q88_form_to_db(q88_form, db)
                
                # 4.5. ✅ NEW: Save document as JSON
                logger.info("💾 Step 4.5: Saving document as JSON...")
                try:
                    # Ensure all fields have raw_text filled
                    self._ensure_raw_text_in_fields(ai_result)
                    
                    saved_doc = self.document_service.save_document(
                        llm_result=ai_result,
                        original_filename=file.filename,
                file_path=file_path,
                        saved_by=None
                    )
                    logger.info(f"✅ JSON document saved: {saved_doc.metadata.document_id}")
                except Exception as doc_error:
                    logger.error(f"❌ Error saving JSON document: {doc_error}")
                    import traceback
                    logger.error(f"❌ Traceback: {traceback.format_exc()}")
                
                # 5. Return response
                return Q88FormResponse(
                    form_id=db_form.form_id,
                    sections=db_form.sections,
                    processing_status=db_form.processing_status,
                    created_at=db_form.created_at,
                    updated_at=db_form.updated_at,
                    file_path=db_form.file_path,
                    ocr_model_version=db_form.ocr_model_version,
                    total_confidence_score=db_form.total_confidence_score,
                    completion_percentage=db_form.get_completion_percentage(),
                    fields_needing_review=len(db_form.get_all_fields_needing_review())
                )
                
            except Exception as processing_error:
                logger.error(f"❌ Erro no processamento AI: {str(processing_error)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Erro no processamento: {str(processing_error)}"
                )
            finally:
                # Limpar arquivo temporário
                if Path(file_path).exists():
                    Path(file_path).unlink()
                    
        except Exception as e:
            logger.error(f"❌ Erro geral no controller: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Erro interno: {str(e)}"
            )
    
    async def _process_with_old_ai(self, extracted_data):
        """Método de compatibilidade para processamento antigo"""
        # Implementação temporária - pode ser removida quando não precisar mais
        from app.AI.chat_graph.tools.q88_tools import Q88ExtractionTool
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Obter texto OCR (pode vir como full_text ou fullText)
        ocr_text = extracted_data.get("full_text") or extracted_data.get("fullText", "")
        logger.info(f"🔄 Iniciando processamento IA com dados: {len(ocr_text)} caracteres")
        
        extraction_tool = Q88ExtractionTool()
        result = extraction_tool.extract_q88_fields_structured(
            ocr_text,
            extracted_data
        )
        
        logger.info(f"📊 Resultado IA: {result}")
        logger.info(f"📊 Campos encontrados: {len(result.fields.__dict__) if result.fields else 0}")
        
        # Converter para formato antigo
        fields_dict = {}
        if result.fields:
            for k, v in result.fields.__dict__.items():
                if v is not None:  # Incluir todos os campos, mesmo "Not Found"
                    fields_dict[k] = v.dict()
                    field_value = v.value if hasattr(v, 'value') else 'N/A'
                    logger.info(f"✅ Campo {k}: '{field_value}'")
            else:
                    logger.info(f"❌ Campo {k}: None")
        
        logger.info(f"📋 Total de campos processados: {len(fields_dict)}")
        
        return {
            "structuredFields": {
                "fields": fields_dict,
                "summary": result.summary.dict() if result.summary else {}
            },
            "processingTime": 0  # Será calculado pelo controller
        }
    
    async def _save_uploaded_file(self, file: UploadFile) -> str:
        """Salva arquivo enviado em ficheiro temporário e retorna o caminho"""
        import os
        import uuid
        import tempfile
        
        # Validar extensão do arquivo
        allowed_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.docx', '.xlsx', '.pptx'}
        file_extension = Path(file.filename).suffix.lower()
        
        if file_extension not in allowed_extensions:
            raise ValueError(f"Formato de arquivo não suportado: {file_extension}. Formatos permitidos: {', '.join(allowed_extensions)}")
        
        # Criar ficheiro temporário persistente até limpeza manual
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=file_extension, prefix="q88_")
        os.close(tmp_fd)
        
        # Salvar conteúdo no temporário
        with open(tmp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"📁 Temp file saved: {file.filename} ({file_extension}) -> {tmp_path}")
        
        return str(tmp_path)
    
    def _ensure_raw_text_in_fields(self, ai_result):
        """Ensures all fields have raw_text filled"""
        from app.AI.chat_graph.q88_state import Q88FieldData
        
        if not ai_result or not hasattr(ai_result, 'fields'):
            return
            
        fields_dict = ai_result.fields.dict() if hasattr(ai_result.fields, 'dict') else ai_result.fields
        
        for field_name, field_data in fields_dict.items():
            if field_data and isinstance(field_data, dict):
                # Se raw_text não estiver preenchido, usar o valor
                if not field_data.get('raw_text') and field_data.get('value'):
                    field_data['raw_text'] = field_data['value']
                elif not field_data.get('raw_text'):
                    field_data['raw_text'] = field_data.get('source', 'N/A')
    
    def _convert_ai_result_to_q88_form(self, ai_result, filename: str, file_path: str) -> Q88Form:
        """Converte resultado da IA para estrutura Q88"""
        import time
        from app.AI.chat_graph.q88_state import Q88LLMResult
        
        # Verificar se o resultado é válido
        if not ai_result or not isinstance(ai_result, Q88LLMResult):
            raise ValueError("Resultado da IA é None ou formato inválido")
        
        # Gerar ID único para o formulário
        form_id = f"q88_{int(time.time())}_{Path(file_path).stem}"
        
        # Obter campos estruturados da IA
        ai_fields = ai_result.fields
        
        # Organizar campos em seções
        sections = self._organize_ai_fields_into_sections(ai_fields)
        
        # Criar formulário Q88
        q88_form = Q88Form(
            form_id=form_id,
            filename=filename,
            file_path=file_path,
            sections=sections,
            processing_status="completed",
            ocr_model_version="ai-powered-extraction",
            total_confidence_score=self._calculate_average_confidence(ai_result.fields)
        )
        
        return q88_form

    def _organize_ai_fields_into_sections(self, ai_fields) -> List[Q88Section]:
        """Organiza campos identificados pela IA em seções lógicas"""
        import logging
        from app.AI.chat_graph.q88_state import Q88LLMFields, Q88FieldData
        
        logger = logging.getLogger(__name__)
        
        # Converter ai_fields para dict se for objeto Q88LLMFields
        if hasattr(ai_fields, '__dict__'):
            fields_dict = {}
            for field_name in dir(ai_fields):
                if not field_name.startswith('_'):
                    field_value = getattr(ai_fields, field_name)
                    if isinstance(field_value, Q88FieldData):
                        fields_dict[field_name] = field_value
            ai_fields = fields_dict
        
        # Organizing fields into sections
        
        sections = []
        
        # Mapeamento de campos para seções (OTIMIZADO para Business Central - apenas 12 categorias essenciais)
        section_mapping = {
            "Vessel Information": [
                "VesselName", "IMONumber", "Flag", "CallSign", "VesselType", "MMSI", "PortOfRegistry", "DateUpdated", "PreviousName"
            ],
            "Ownership": [
                "RegisteredOwner", "TechnicalOperator", "CommercialOperator", "DisponentOwner"
            ],
            "Dimensions & Tonnages": [
                "LOA", "Beam", "GrossTonnage", "NetTonnage", "SummerDWT", "WinterDWT", "TropicalDWT"
            ],
            "Contact Details": [
                "ContactDetails", "MasterEmail", "MasterPhone", "InmarsatNumber", "MasterPIC"
            ],
            "Classification": [
                "ClassificationSociety", "ClassNotation", "ClassConditions", "LastDryDock", "NextDryDockDue", "NextAnnualSurveyDue"
            ],
            "Insurance": [
                "PIClub", "HullMachineryInsurer", "HullMachineryValue", "ExpirationDate"
            ],
            "Construction": [
                "Builder", "DateDelivered"
            ],
            "Certificates Essential": [
                "ISM", "DOC", "IOPPC", "ISSC", "MLC", "IAPP"
            ],
            "Crew": [
                "CrewNationality", "NumberOfOfficers", "NumberOfCrew", "WorkingLanguage", "ManningAgency"
            ],
            "Cargo Capabilities": [
                "DoubleHullVessel", "MaxLoadingRate", "CargoRestrictions", "MaxCargoTemp"
            ],
            "Propulsion": [
                "MainEngineType", "MainEngineHP", "BallastSpeed", "LadenSpeed", "FuelType"
            ],
            "Recent History": [
                "LastThreeCargoes", "SIREDate", "PortStateDeficiencies", "AdditionalInfo"
            ]
        }
        
        section_order = 0
        for section_name, field_names in section_mapping.items():
            fields = []
            field_index = 0
            
            for field_name in field_names:
                if field_name in ai_fields:
                    field_data = ai_fields[field_name]
                    
                    # Extrair dados do Q88FieldData
                    if hasattr(field_data, 'value'):
                        field_value = field_data.value
                        confidence = field_data.confidence
                    else:
                        field_value = field_data.get('value', 'Not Found')
                        confidence = field_data.get('confidence', 0.8)
                    
                    # Determinar tipo do campo
                    field_type = self._determine_field_type(field_value)
                    
                    # Criar campo Q88 - incluir sempre, mesmo se for "Not Found"
                    q88_field = Q88Field(
                        index=field_index,
                        label=field_name,
                        field_type=field_type,
                        values=[field_value] if field_value and field_value != "Not Found" else ["Not Found"],
                        confidence_scores=[confidence],
                        need_confirmation=confidence < 0.7
                    )
                    
                    fields.append(q88_field)
                    field_index += 1
                else:
                    # Criar campo mesmo se não estiver nos dados da IA
                    q88_field = Q88Field(
                        index=field_index,
                        label=field_name,
                        field_type=FieldType.TEXT,
                        values=["Not Found"],
                        confidence_scores=[0.0],
                        need_confirmation=True
                    )
                    fields.append(q88_field)
                    field_index += 1
            
            # Criar seção sempre, mesmo se não tiver campos válidos
            if fields:
                section = Q88Section(
                    name=section_name,
                    order=section_order,
                    fields=fields
                )
                sections.append(section)
                section_order += 1
        
        return sections
    
    def _determine_field_type(self, value: str) -> FieldType:
        """Determina o tipo de campo baseado no valor"""
        if not value or value == "Not Found":
            return FieldType.TEXT
    
        # Verificar se é numérico
        try:
            float(value.replace(',', '').replace(' ', ''))
            return FieldType.NUMBER
        except ValueError:
            pass
        
        # Verificar se é data
        import re
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'\d{1,2}\s+\w+\s+\d{4}',
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}'
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, value):
                return FieldType.DATE
        
            return FieldType.TEXT
    
    def _calculate_average_confidence(self, fields) -> float:
        """Calcula a confiança média dos campos"""
        if not fields:
            return 0.0
        
        total_confidence = 0.0
        field_count = 0
        
        for field_name in dir(fields):
            if not field_name.startswith('_'):
                field_value = getattr(fields, field_name)
                if hasattr(field_value, 'confidence'):
                    total_confidence += field_value.confidence
                    field_count += 1
        
        return total_confidence / field_count if field_count > 0 else 0.0
    
    async def _save_q88_form_to_db(self, q88_form: Q88Form, db: Session) -> Q88FormModel:
        """Salva formulário Q88 no banco de dados"""
        try:
            # Criar registro principal
            db_form = Q88FormModel(
                form_id=q88_form.form_id,
                file_path=q88_form.file_path,
                processing_status=q88_form.processing_status,
                ocr_model_version=q88_form.ocr_model_version,
                total_confidence_score=q88_form.total_confidence_score
            )
            
            db.add(db_form)
            db.flush()  # Para obter o ID
            
            # Salvar seções e campos
            for section in q88_form.sections:
                db_section = Q88SectionModel(
                    form_id=db_form.id,
                    name=section.name,
                    order=section.order
                )
                db.add(db_section)
                db.flush()
                
                for field in section.fields:
                    db_field = Q88FieldModel(
                        section_id=db_section.id,
                        field_index=field.index,
                        label=field.label,
                        field_type=field.field_type.value,
                        values=field.values,
                        confidence_scores=field.confidence_scores,
                        need_confirmation=field.need_confirmation
                    )
                    db.add(db_field)
            
            db.commit()
            db.refresh(db_form)
        
            logger.info(f"✅ Q88 form saved to database: {db_form.form_id}")
            return db_form
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error saving Q88 form: {str(e)}")
            raise
    
    async def upload_q88_async(self, file: UploadFile = File(...)) -> Dict[str, str]:
        """Upload assíncrono de arquivo Q88"""
        import uuid
        import time
        
        # Gerar ID único para o processamento
        form_id = f"q88_{int(time.time())}_{uuid.uuid4()}"
        
        # Salvar arquivo
        file_path = await self._save_uploaded_file(file)
        
        # Criar registro inicial no banco
        db = SessionLocal()
        try:
            db_form = Q88FormModel(
                form_id=form_id,
                file_path=file_path,
                processing_status="processing"
            )
            db.add(db_form)
            db.commit()
            db.refresh(db_form)
            
            # Iniciar processamento assíncrono
            asyncio.create_task(self._process_q88_document_async(file_path, db_form.id, file.filename))
            
            return {"form_id": form_id, "status": "processing"}
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Erro no upload assíncrono: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            db.close()
    
    async def _process_q88_document_async(self, file_path: str, form_db_id: int, original_filename: str):
        """Processa documento Q88 de forma assíncrona"""
        # Criar nova sessão para o processamento assíncrono
        async_db = SessionLocal()
        try:
            # 1. Extrair TODO o texto com Azure Document Intelligence
            await self._update_progress(async_db, form_db_id, "📄 Extraindo texto do documento...", "processing")
            extracted_data = self.ocr_service.process_q88_document(file_path)
            
            # 2. Processar com IA para identificar campos Q88
            await self._update_progress(async_db, form_db_id, "🤖 Processando com IA...", "processing")
            from app.AI.chat_graph.tools.q88_tools import Q88ExtractionTool
            
            # Obter texto OCR (pode vir como full_text ou fullText)
            ocr_text = extracted_data.get("full_text") or extracted_data.get("fullText", "")
            
            extraction_tool = Q88ExtractionTool()
            ai_result = extraction_tool.extract_q88_fields_structured(
                ocr_text,
                extracted_data
            )
            
            # 3. Converter resultado para estrutura Q88
            await self._update_progress(async_db, form_db_id, "🔄 Convertendo dados...", "processing")
            q88_form = self._convert_ai_result_to_q88_form(ai_result, "document.pdf", file_path)
            
            # Atualizar o registro existente no banco
            q88_form_db = async_db.query(Q88FormModel).filter(Q88FormModel.id == form_db_id).first()
            if q88_form_db:
                # Atualizar dados do formulário
                q88_form_db.processing_status = "completed"
                q88_form_db.ocr_model_version = q88_form.ocr_model_version
                q88_form_db.total_confidence_score = q88_form.total_confidence_score
                
                # Salvar seções e campos
                for section in q88_form.sections:
                    db_section = Q88SectionModel(
                        form_id=q88_form_db.id,
                        name=section.name,
                        order=section.order
                    )
                    async_db.add(db_section)
                    async_db.flush()
                    
                    for field in section.fields:
                        db_field = Q88FieldModel(
                            section_id=db_section.id,
                            field_index=field.index,
                            label=field.label,
                            field_type=field.field_type.value,
                            values=field.values,
                            confidence_scores=field.confidence_scores,
                            need_confirmation=field.need_confirmation
                        )
                        async_db.add(db_field)
                
                async_db.commit()
                
                # ✅ NOVO: Salvar documento em JSON (assíncrono)
                try:
                    # Garantir que todos os campos têm raw_text preenchido
                    self._ensure_raw_text_in_fields(ai_result)
                    
                    saved_doc = self.document_service.save_document(
                        llm_result=ai_result,
                        original_filename=original_filename,
            file_path=file_path,
                        saved_by=None
                    )
                except Exception as doc_error:
                    logger.error(f"❌ Error saving JSON document (async): {doc_error}")
            
        except Exception as e:
            async_db.rollback()
            logger.error(f"❌ Error in async processing: {str(e)}")
            
            # Atualizar status para erro
            try:
                await self._update_progress(async_db, form_db_id, f"❌ Error: {str(e)}", "error")
            except:
                pass
        finally:
            async_db.close()
    
    async def _update_progress(self, db: Session, form_id: int, message: str, status: str):
        """Atualiza progresso do processamento"""
        try:
            form = db.query(Q88FormModel).filter(Q88FormModel.id == form_id).first()
            if form:
                form.processing_status = status
                db.commit()
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar progresso: {str(e)}")
    
    async def get_q88_status(self, form_id: str) -> Dict[str, Any]:
        """Obtém status do processamento Q88"""
        db = SessionLocal()
        try:
            form = db.query(Q88FormModel).filter(Q88FormModel.form_id == form_id).first()
            if not form:
                raise HTTPException(status_code=404, detail="Formulário não encontrado")
            
            result = {
                "form_id": form.form_id,
                "status": form.processing_status,
                "created_at": form.created_at,
                "updated_at": form.updated_at
            }
            
            # Se o processamento estiver completo, incluir os dados extraídos
            if form.processing_status == "completed":
                # Buscar seções e campos
                sections = db.query(Q88SectionModel).filter(Q88SectionModel.form_id == form.id).all()
                sections_data = []
                
                for section in sections:
                    fields = db.query(Q88FieldModel).filter(Q88FieldModel.section_id == section.id).all()
                    fields_data = []
                    
                    for field in fields:
                        # Lidar com field.values que pode ser None, lista vazia, ou lista com valores
                        if field.values and isinstance(field.values, list) and len(field.values) > 0:
                            field_value = field.values[0]
                        elif field.values and isinstance(field.values, str):
                            field_value = field.values
                        else:
                            field_value = "Not Found"
                        
                        # Lidar com confidence_scores que pode ser None, lista vazia, ou lista com valores
                        if field.confidence_scores and isinstance(field.confidence_scores, list) and len(field.confidence_scores) > 0:
                            confidence_score = field.confidence_scores[0]
                        elif field.confidence_scores and isinstance(field.confidence_scores, (int, float)):
                            confidence_score = field.confidence_scores
                        else:
                            confidence_score = 0.0
                        
                        fields_data.append({
                            "label": field.label,
                            "value": field_value,
                            "field_type": field.field_type,
                            "confidence_scores": confidence_score,
                            "need_confirmation": field.need_confirmation
                        })
                    
                    sections_data.append({
                        "name": section.name,
                        "order": section.order,
                        "fields": fields_data
                    })
                
                result["sections"] = sections_data
                result["filename"] = form.file_path.split('/')[-1] if form.file_path else "unknown"
                result["file_path"] = form.file_path
            
            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro ao verificar status do formulário Q88: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Erro interno: {str(e)}"
            )
        finally:
            db.close()
