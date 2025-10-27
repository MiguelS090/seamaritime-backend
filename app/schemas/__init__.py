# app/schemas/__init__.py

# Schemas de usuário
from .user import UserRead, UserCreate, UserUpdate, UserLogin, UserAzure, Token

# Schemas de chat
from .chat import ChatRead, ChatCreate, UpdateChatTitleRequest

# Schemas de configuração do DB
from .configDB import ConfigRead, ConfigCreate, ConfigUpdate

# Schemas de arquivo
from .file import FileRead, FileCreate, FileUpdate

# Schemas de mensagem
from .message import MessageRead, MessageCreate, MessageUpdate, MessageResponse, IAResponse
