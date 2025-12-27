# Script de Deploy para o Google Cloud Run

# Configurações
$PROJECT_ID = "gerador-de-podcast" # Substitua pelo seu Project ID ou configure via gcloud config set project
$SERVICE_NAME = "gerador-de-podcast-api"
$REGION = "us-east1" # Escolha a região desejada

# Verifica se o gcloud está instalado
if (-not (Get-Command "gcloud" -ErrorAction SilentlyContinue)) {
    Write-Error "Google Cloud SDK (gcloud) não encontrado. Por favor, instale-o primeiro."
    exit 1
}

# Verifica se o usuário está logado
Write-Host "Verificando autenticação..."
gcloud auth print-identity-token | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Por favor, faça login no Google Cloud..."
    gcloud auth login
}

# Define o projeto (força o uso do projeto definido no script)
Write-Host "Configurando projeto: $PROJECT_ID"
gcloud config set project $PROJECT_ID

$currentProject = gcloud config get-value project
Write-Host "Usando projeto: $currentProject"

# Habilita as APIs necessárias (pode demorar um pouco na primeira vez)
Write-Host "Habilitando APIs necessárias (Cloud Build, Cloud Run, Artifact Registry)..."
gcloud services enable cloudbuild.googleapis.com run.googleapis.com artifactregistry.googleapis.com

# Configuração do Artifact Registry
$REPO_NAME = "cloud-run-source-deploy"
$IMAGE_NAME = "gerador-de-podcast-api"
$IMAGE_TAG = "$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$IMAGE_NAME"

# Cria o repositório no Artifact Registry se não existir
Write-Host "Verificando/Criando repositório no Artifact Registry..."
# O comando pode falhar se o repo já existir, então ignoramos o erro (ou poderíamos verificar antes)
gcloud artifacts repositories create $REPO_NAME `
    --repository-format=docker `
    --location=$REGION `
    --description="Docker repository for Cloud Run" `
    --quiet 2>$null

# Build da imagem e push para o Artifact Registry
Write-Host "Construindo imagem e enviando para o Artifact Registry..."
gcloud builds submit --tag $IMAGE_TAG .

if ($LASTEXITCODE -ne 0) {
    Write-Error "Falha no build da imagem."
    exit 1
}

# Deploy usando a imagem criada
Write-Host "Iniciando Deploy para o Cloud Run..."
gcloud run deploy $SERVICE_NAME `
    --image $IMAGE_TAG `
    --region $REGION `
    --allow-unauthenticated `
    --port 8080

if ($LASTEXITCODE -eq 0) {
    Write-Host "Deploy concluído com sucesso!"
}
else {
    Write-Error "Falha no deploy."
}
