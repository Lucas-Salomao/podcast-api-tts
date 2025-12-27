# 🎙️ Podcast Generator API

API de alta performance para geração de podcasts usando **Gemini 2.5 Flash** (roteirização) + **Gemini 2.5 Pro TTS** (síntese de voz multi-speaker), com persistência em **GCP Cloud Storage** e **PostgreSQL**.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)
![Gemini](https://img.shields.io/badge/Gemini-2.5-orange)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## 📖 Índice

- [Visão Geral](#-visão-geral)
- [Arquitetura de Alto Nível](#-arquitetura-de-alto-nível)
- [Arquitetura Modular](#-arquitetura-modular)
- [Camada de Persistência](#-camada-de-persistência)
- [Fluxo de Dados](#-fluxo-de-dados)
- [Tags TTS para Scripts](#-tags-tts-para-scripts)
- [API Endpoints](#-api-endpoints)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Instalação e Uso](#-instalação-e-uso)
- [Deploy em Produção](#-deploy-em-produção)

---

## 🎯 Visão Geral

O **Podcast Generator API** transforma temas em podcasts de áudio realistas e envolventes. A solução utiliza:

| Componente | Tecnologia | Função |
|------------|------------|--------|
| **Backend** | FastAPI + Python 3.12 | API REST assíncrona de alta performance |
| **Roteirização** | Gemini 2.5 Flash | Geração de scripts com TTS markup tags |
| **Síntese de Voz** | Gemini 2.5 Pro TTS | Multi-speaker com 30+ vozes disponíveis |
| **Processamento de Docs** | Docling (IBM) | Extração de texto de PDF, DOCX, XLSX, PPTX, TXT |
| **Armazenamento** | GCP Cloud Storage | Áudio persistido com URLs assinadas |
| **Banco de Dados** | PostgreSQL (Supabase) | Metadados de podcasts por usuário |
| **Containerização** | Docker | Deploy portável e escalável (CPU-only) |

### Features

- ✅ **Multi-host**: Suporta 2 apresentadores (limitação da API TTS)
- ✅ **30 vozes**: Femininas e masculinas com personalidades distintas
- ✅ **Upload de documentos**: PDF, DOCX, XLSX, PPTX, TXT (até 20 arquivos)
- ✅ **Extração inteligente**: Docling com OCR, tabelas e layout avançado
- ✅ **TTS Markup Tags**: `[sigh]`, `[laughing]`, `[pause]` para áudio natural
- ✅ **Persistência**: Salva podcasts no GCP Storage + metadados no PostgreSQL
- ✅ **Histórico por usuário**: Lista, reproduz e deleta podcasts anteriores
- ✅ **URLs assinadas**: Acesso seguro a arquivos privados

---

## 🏗️ Arquitetura de Alto Nível

```mermaid
flowchart TB
    subgraph Cliente["🖥️ Cliente"]
        FE[Frontend Next.js]
    end

    subgraph API["⚡ Podcast Generator API"]
        direction TB
        FAST[FastAPI Server]
        
        subgraph Services["Services Layer"]
            DS[Document Service<br/>Docling]
            ES[Enhance Service]
            SS[Script Service]
            TTS[TTS Service]
            STORAGE[Storage Service<br/>GCS]
            REPO[Podcast Repository]
        end
        
        subgraph Database["Data Layer"]
            DB[(PostgreSQL)]
        end
    end

    subgraph External["☁️ Google Cloud"]
        GEMINI_LLM[Gemini 2.5 Flash<br/>LLM]
        GEMINI_TTS[Gemini 2.5 Pro<br/>TTS]
        GCS[Cloud Storage<br/>Bucket]
    end

    FE -->|"POST /podcast/generate<br/>+ documentos[] + user_id"| FAST
    FAST --> DS
    FAST --> ES
    FAST --> SS
    FAST --> TTS
    FAST --> STORAGE
    FAST --> REPO
    
    DS -->|"Extrai texto"| SS
    ES -->|"Aprimora texto"| GEMINI_LLM
    SS -->|"Gera script"| GEMINI_LLM
    TTS -->|"Sintetiza áudio"| GEMINI_TTS
    STORAGE -->|"Upload WAV"| GCS
    REPO -->|"CRUD"| DB
    
    FAST -->|"audio/wav"| FE

    style Cliente fill:#e1f5fe
    style API fill:#fff3e0
    style External fill:#f3e5f5
    style DS fill:#c8e6c9
    style STORAGE fill:#ffecb3
    style REPO fill:#ffecb3
```

---

## 🧩 Arquitetura Modular

O projeto segue uma arquitetura **modular e desacoplada** com separação clara de responsabilidades:

```mermaid
graph TD
    subgraph "Entry Point"
        MAIN["main.py<br/>(entry point)"]
    end

    subgraph "app/"
        APP_MAIN["app/main.py<br/>FastAPI Factory + Lifespan"]
        
        subgraph "core/"
            CONFIG["config.py<br/>Settings & ENV"]
            LOGGING["logging.py<br/>Logger Setup"]
        end
        
        subgraph "db/"
            DATABASE["database.py<br/>SQLAlchemy Async"]
            MODELS["models.py<br/>Podcast Model"]
        end
        
        subgraph "models/"
            SCHEMAS["schemas.py<br/>Pydantic Models"]
            VOICES["voices.py<br/>Voice Configs"]
        end
        
        subgraph "services/"
            DOCUMENT["document_service.py<br/>Document Processing"]
            ENHANCE["enhance_service.py<br/>Text Enhancement"]
            SCRIPT["script_service.py<br/>Script + TTS Tags"]
            TTS["tts_service.py<br/>Audio Synthesis"]
            STORAGE["storage_service.py<br/>GCS Upload"]
            PODCAST_REPO["podcast_repository.py<br/>Database CRUD"]
        end
        
        subgraph "utils/"
            AUDIO["audio.py<br/>WAV Processing"]
        end
        
        subgraph "routers/"
            R_HEALTH["health.py<br/>GET /"]
            R_ENHANCE["enhance.py<br/>POST /enhance"]
            R_PODCAST["podcast.py<br/>POST/GET/DELETE /podcast/*"]
            R_VOICES["voices.py<br/>GET /vozes"]
        end
    end

    MAIN --> APP_MAIN
    APP_MAIN --> CONFIG
    APP_MAIN --> LOGGING
    APP_MAIN -->|"on_startup"| DATABASE
    APP_MAIN --> R_HEALTH
    APP_MAIN --> R_ENHANCE
    APP_MAIN --> R_PODCAST
    APP_MAIN --> R_VOICES

    R_ENHANCE --> ENHANCE
    R_PODCAST --> DOCUMENT
    R_PODCAST --> SCRIPT
    R_PODCAST --> TTS
    R_PODCAST --> STORAGE
    R_PODCAST --> PODCAST_REPO
    R_VOICES --> VOICES
    
    PODCAST_REPO --> DATABASE
    PODCAST_REPO --> MODELS

    style MAIN fill:#ffcdd2
    style APP_MAIN fill:#c8e6c9
    style DATABASE fill:#ffecb3
    style MODELS fill:#ffecb3
    style STORAGE fill:#bbdefb
    style PODCAST_REPO fill:#bbdefb
```

---

## 💾 Camada de Persistência

### Arquitetura de Dados

```mermaid
erDiagram
    PODCASTS {
        uuid id PK
        varchar user_id "WSO2 sub"
        varchar title
        text theme
        int duration_minutes
        text audio_url
        varchar audio_path "GCS blob path"
        timestamp created_at
    }
    
    GCS_BUCKET ||--o{ PODCASTS : "audio_path"
```

### Fluxo de Persistência

```mermaid
sequenceDiagram
    participant Client as 🖥️ Cliente
    participant API as ⚡ FastAPI
    participant TTS as 🔊 TTS Service
    participant Storage as 📦 Storage Service
    participant Repo as 🗄️ Repository
    participant GCS as ☁️ GCS Bucket
    participant DB as 🐘 PostgreSQL

    Client->>API: POST /podcast/generate<br/>{tema, user_id}
    API->>TTS: generate_audio()
    TTS-->>API: audio_bytes
    
    alt user_id provided
        API->>Storage: upload_audio(bytes, user_id)
        Storage->>GCS: PUT blob
        GCS-->>Storage: blob_path
        Storage-->>API: (audio_url, audio_path)
        
        API->>Repo: create(user_id, title, audio_path)
        Repo->>DB: INSERT INTO podcasts
        DB-->>Repo: podcast_id
        Repo-->>API: Podcast
    end
    
    API-->>Client: audio/wav + X-Podcast-Id header
```

### URLs Assinadas

Como o bucket é **privado**, usamos URLs assinadas para acesso:

```mermaid
sequenceDiagram
    participant Client as 🖥️ Cliente
    participant API as ⚡ FastAPI
    participant Repo as 🗄️ Repository
    participant Storage as 📦 Storage
    participant GCS as ☁️ GCS

    Client->>API: GET /podcast/list?user_id=xxx
    API->>Repo: list_by_user(user_id)
    Repo-->>API: [Podcast, ...]
    
    loop Para cada podcast
        API->>Storage: get_signed_url(audio_path, 1h)
        Storage->>GCS: Generate signed URL
        GCS-->>Storage: signed_url
        Storage-->>API: signed_url
    end
    
    API-->>Client: {podcasts: [{..., audio_url: signed_url}]}
```

---

## 🎤 Tags TTS para Scripts

O gerador de scripts inclui instruções para usar **markup tags** que enriquecem a síntese de voz:

### Sons Não-Verbais

| Tag | Descrição | Exemplo |
|-----|-----------|---------|
| `[sigh]` | Insere suspiro | `[sigh] Isso é complicado...` |
| `[laughing]` | Insere risada | `[laughing] Essa foi boa!` |
| `[uhm]` | Hesitação natural | `Então, [uhm] deixa eu pensar...` |

### Modificadores de Estilo

| Tag | Descrição | Exemplo |
|-----|-----------|---------|
| `[sarcasm]` | Tom sarcástico | `[sarcasm] Que surpresa...` |
| `[whispering]` | Sussurro | `[whispering] Isso é segredo.` |
| `[shouting]` | Volume alto | `[shouting] Incrível!` |
| `[extremely fast]` | Fala acelerada | `[extremely fast] Termos e condições...` |

### Pausas e Ritmo

| Tag | Duração | Uso |
|-----|---------|-----|
| `[short pause]` | ~250ms | Entre cláusulas |
| `[medium pause]` | ~500ms | Entre frases |
| `[long pause]` | ~1000ms | Efeito dramático |

### Exemplo de Script Gerado

```
Speaker 1: Olá pessoal! [short pause] Bem-vindos a mais um episódio.
Speaker 2: Hoje vamos falar sobre [uhm] um tema que todo mundo quer saber...
Speaker 1: [laughing] É verdade! [medium pause] Então vamos direto ao ponto.
Speaker 2: [sigh] Olha, esse assunto é complexo, mas vou explicar de forma simples.
```

---

## 🔌 API Endpoints

### Visão Geral

```mermaid
graph LR
    subgraph Endpoints["API Endpoints"]
        direction TB
        E1["GET /<br/>Health Check"]
        E2["POST /enhance<br/>Aprimora texto"]
        E3["GET /vozes<br/>Lista vozes"]
        E4["POST /podcast/script<br/>Gera script"]
        E5["POST /podcast/generate<br/>Gera + salva podcast"]
        E6["GET /podcast/list<br/>Lista por usuário"]
        E7["GET /podcast/{id}<br/>Busca com URL assinada"]
        E8["DELETE /podcast/{id}<br/>Remove podcast"]
    end

    style E1 fill:#c8e6c9
    style E2 fill:#bbdefb
    style E3 fill:#fff9c4
    style E4 fill:#ffccbc
    style E5 fill:#ffccbc
    style E6 fill:#e1bee7
    style E7 fill:#e1bee7
    style E8 fill:#ffcdd2
```

### Tabela de Endpoints

| Método | Endpoint | Descrição | Autenticação |
|--------|----------|-----------|--------------|
| `GET` | `/` | Health check | Não |
| `POST` | `/enhance` | Aprimora texto com IA | Não |
| `GET` | `/vozes` | Lista vozes disponíveis | Não |
| `POST` | `/podcast/script` | Gera apenas o script | Não |
| `POST` | `/podcast/generate` | Gera podcast + salva se `user_id` | user_id (opcional) |
| `GET` | `/podcast/list` | Lista podcasts do usuário | user_id (query) |
| `GET` | `/podcast/{id}` | Retorna podcast específico | user_id (query) |
| `DELETE` | `/podcast/{id}` | Deleta podcast | user_id (query) |

### Exemplos de Uso

```bash
# Gerar podcast e salvar
curl -X POST http://localhost:8000/podcast/generate \
  -F "tema=Inteligência Artificial na Indústria 4.0" \
  -F "duracao_minutos=3" \
  -F "num_hosts=2" \
  -F "user_id=user123" \
  -F 'hosts_vozes=[{"hostNumber":1,"vozId":"Zephyr"},{"hostNumber":2,"vozId":"Puck"}]' \
  --output podcast.wav

# Listar podcasts do usuário
curl "http://localhost:8000/podcast/list?user_id=user123" | jq

# Deletar podcast
curl -X DELETE "http://localhost:8000/podcast/abc123?user_id=user123"
```

---

## 📁 Estrutura do Projeto

```
podcast-api-tts/
├── main.py                         # Entry point
├── Dockerfile                      # Container config
├── pyproject.toml                  # Dependencies (uv)
├── .env                            # Environment variables
│
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app factory + lifespan
│   │
│   ├── core/
│   │   ├── config.py               # Settings & environment
│   │   └── logging.py              # Logging configuration
│   │
│   ├── db/                         # 🆕 Database layer
│   │   ├── database.py             # SQLAlchemy async engine
│   │   └── models.py               # Podcast model
│   │
│   ├── models/
│   │   ├── schemas.py              # Pydantic request/response
│   │   └── voices.py               # TTS voice configurations
│   │
│   ├── services/
│   │   ├── document_service.py     # Document extraction (Docling)
│   │   ├── enhance_service.py      # Text enhancement (LLM)
│   │   ├── script_service.py       # Script generation + TTS tags
│   │   ├── tts_service.py          # Audio synthesis (TTS)
│   │   ├── storage_service.py      # 🆕 GCS upload + signed URLs
│   │   └── podcast_repository.py   # 🆕 Database CRUD
│   │
│   ├── utils/
│   │   └── audio.py                # WAV encoding utilities
│   │
│   └── routers/
│       ├── health.py               # GET /
│       ├── enhance.py              # POST /enhance
│       ├── podcast.py              # POST/GET/DELETE /podcast/*
│       └── voices.py               # GET /vozes
│
└── scripts/
    ├── install_docling.sh          # Install PyTorch CPU + Docling
    └── download_models.py          # Pre-cache Docling models
```

---

## 🛠️ Instalação e Uso

### Pré-requisitos

- **Python 3.12+**
- **uv** (recomendado) ou **pip**
- **API Key do Google Gemini**
- **Bucket GCS** (para persistência)
- **PostgreSQL** (Supabase ou outro)

### Variáveis de Ambiente

```env
# Gemini API
GEMINI_API_KEY=sua_chave_aqui

# GCP Storage
BUCKET_AUDIOS=nome-do-bucket

# PostgreSQL (Supabase)
DB_HOST=aws-0-us-west-2.pooler.supabase.com
DB_PORT=6543
DB_NAME=podcast
DB_USER=postgres.xxxx
DB_PASSWORD=xxx
DB_SSLMODE=require
```

### Instalação Local

```bash
# 1. Clone o repositório
git clone <repo-url>
cd podcast-api-tts

# 2. Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com suas credenciais

# 3. Instale as dependências
uv sync

# 4. Execute o servidor
uv run python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Executando com Docker

```bash
# Build da imagem
docker build -t podcast-api .

# Run do container
docker run -p 8000:8000 --env-file .env podcast-api
```

---

## ☁️ Deploy em Produção

### Google Cloud Run

```bash
gcloud run deploy podcast-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="GEMINI_API_KEY=xxx,BUCKET_AUDIOS=xxx,DB_HOST=xxx,..."
```

### Arquitetura de Deploy

```mermaid
flowchart TB
    subgraph GCP["☁️ Google Cloud Platform"]
        CR[Cloud Run<br/>podcast-api]
        GCS[Cloud Storage<br/>BUCKET_AUDIOS]
        GEMINI[Gemini API]
    end
    
    subgraph Supabase["🐘 Supabase"]
        PG[(PostgreSQL)]
    end
    
    subgraph Users["👥 Usuários"]
        WEB[Web App]
    end
    
    WEB -->|HTTPS| CR
    CR -->|API Calls| GEMINI
    CR -->|Upload/Download| GCS
    CR -->|CRUD| PG
    
    style GCP fill:#e8f5e9
    style Supabase fill:#e3f2fd
    style Users fill:#fff3e0
```

---

## 🎤 Vozes Disponíveis

O sistema suporta **30 vozes** do Gemini TTS (limitado a 2 por podcast):

| Femininas | Masculinas |
|-----------|------------|
| Achernar, Aoede, Autonoe | Achird, Algenib, Algieba |
| Callirrhoe, Despina, Erinome | Alnilam, Charon, Enceladus |
| Gacrux, Kore, Laomedeia | Fenrir, Iapetus, Orus |
| Leda, Pulcherrima, Sulafat | Puck, Rasalgethi, Sadachbia |
| Vindemiatrix, Zephyr | Sadaltager, Schedar, Umbriel, Zubenelgenubi |

---

## 📄 Licença

MIT License - veja [LICENSE](LICENSE) para detalhes.
