# 🏢 ImobiIntel - Inteligência de Mercado Imobiliário

Plataforma avançada de análise de inteligência de mercado imobiliário projetada para identificar **assimetrias de valor** e **oportunidades de alto ROI** em bairros consolidados de São Paulo. A solução conta com mineração e simulação de dados robustos, auditoria preditiva via inteligência artificial (Gemini API), e persistência estruturada em tempo real (Firebase Firestore).

---

## 🛠️ Stack Tecnológica

* **Linguagem & Backend:** Python 3.10+
* **Processamento de Dados:** Pandas & Numpy
* **Visualização Científica:** Plotly & Streamlit
* **Inteligência Artificial:** Gemini API (`google-generativeai`)
* **Banco de Dados (DB):** Firebase Firestore (`firebase-admin`)
* **Testes & Qualidade:** PyTest & Flake8
* **Automação & CI/CD:** GitHub Actions

---

## 📁 Estrutura do Projeto

```
ProjetoFinal/
├── .github/
│   └── workflows/
│       └── deploy.yml         # Pipeline de Integração Contínua (CI)
├── src/
│   ├── __init__.py
│   ├── engine.py              # Geração de dados de mercado e cálculo de outliers
│   ├── gemini_service.py      # Agente de IA para análise preditiva (Gemini)
│   └── firebase_service.py    # Barramento de persistência Firestore (online/offline)
├── tests/
│   ├── __init__.py
│   ├── test_engine.py         # Testes de unidade da engine estatística
│   └── test_firebase.py       # Testes de integração do banco local/firestore
├── app.py                     # Painel visual interativo do Streamlit
├── requirements.txt           # Gerenciador de dependências Python
├── .env                       # Chaves de API e segredos de ambiente
└── README.md                  # Documento de instruções do projeto
```

---

## 🚀 Como Executar Localmente

### 1. Clonar o projeto e criar o ambiente virtual
```bash
# Crie um ambiente virtual
python -m venv venv

# Ative o ambiente virtual
# No Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# No Linux/Mac:
source venv/bin/activate
```

### 2. Instalar as dependências
```bash
pip install -r requirements.txt
```

### 3. Configurar as Variáveis de Ambiente
Crie ou altere o arquivo `.env` na raiz do projeto e preencha as variáveis de ambiente necessárias:
```env
# Chave de API do Google Gemini
GEMINI_API_KEY=sua_chave_do_gemini_aqui

# Credenciais da Conta de Serviço do Firebase Admin SDK
FIREBASE_PROJECT_ID=seu_projeto_firebase_id
FIREBASE_CLIENT_EMAIL=seu_cliente_email_firebase@gserviceaccount.com
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nsua_chave_privada_aqui\n-----END PRIVATE KEY-----\n"
```

> [!TIP]
> **Modo Offline de Segurança:** Caso você não insira credenciais válidas do Firebase, o sistema ativará automaticamente o **Modo Local (Offline)**. Ele persistirá todos os dados estruturados e históricos em um arquivo `db_offline.json` local e gerará análises financeiras e de riscos de fallback locais, garantindo que o dashboard funcione de forma 100% autônoma e funcional para demonstrações.

### 4. Rodar o Painel Interativo
```bash
streamlit run app.py
```

### 5. Executar os Testes Unitários
```bash
pytest
```

---

## ☁️ Deploy e CI/CD

### ⚙️ GitHub Actions (CI)
O projeto já conta com um workflow configurado em [deploy.yml](file:///c:/Users/Aluno/Desktop/ProjetoFinal/.github/workflows/deploy.yml). A cada `push` ou `pull request` nas branches `main` ou `master`, o GitHub Actions executa automaticamente:
1. Instalação do Python e dependências do `requirements.txt`.
2. Verificações rápidas de linting com `flake8`.
3. Execução completa do conjunto de testes com `pytest` (utilizando mocks automáticos para credenciais).

### 🚀 Deploy no Streamlit Community Cloud
Para implantar a aplicação gratuitamente no Streamlit Community Cloud:
1. Suba o código para um repositório no seu GitHub.
2. Acesse [share.streamlit.io](https://share.streamlit.io/) e faça login com sua conta do GitHub.
3. Clique em **"New app"**, selecione o repositório, a branch (ex: `main`) e o arquivo principal `app.py`.
4. Clique em **"Advanced settings..."** e, na seção **"Secrets"**, cole o conteúdo completo do seu arquivo `.env`:
   ```toml
   GEMINI_API_KEY="sua_chave_real"
   FIREBASE_PROJECT_ID="seu_projeto_id"
   FIREBASE_CLIENT_EMAIL="seu_email_conta_servico"
   FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nsua_chave_real\n-----END PRIVATE KEY-----\n"
   ```
5. Clique em **"Deploy!"**. O aplicativo estará online em poucos minutos e atualizará automaticamente a cada novo commit.
