# Guia de Deploy — Sistema EBZ Orçamentos

## Visão Geral

- **Frontend** (as telas) → Vercel
- **Backend** (Python/API) → Railway
- **Banco de dados** (PostgreSQL) → Railway

---

## PASSO 1 — Criar conta no GitHub e subir o projeto

1. Acesse https://github.com e crie uma conta (se não tiver)
2. Crie um repositório chamado `sistema-orcamentos`
3. Faça upload de toda a pasta `SistemaOrcamento-Web`

---

## PASSO 2 — Deploy do Backend no Railway

1. Acesse https://railway.app e crie conta com GitHub
2. Clique em **"New Project"** → **"Deploy from GitHub repo"**
3. Selecione o repositório `sistema-orcamentos`
4. Railway vai detectar automaticamente o `Procfile`

### Adicionar banco de dados PostgreSQL:
1. No projeto Railway, clique em **"+ New"** → **"Database"** → **"PostgreSQL"**
2. Clique no banco criado → aba **"Variables"**
3. Copie o valor de `DATABASE_URL`

### Configurar variáveis de ambiente do backend:
No serviço do backend (não do banco), vá em **Variables** e adicione:
```
DATABASE_URL = (cole o valor copiado acima)
SECRET_KEY = (gere uma senha longa aleatória, ex: minha-chave-super-secreta-2024)
ADMIN_PASSWORD = (sua senha desejada para entrar no sistema)
FRONTEND_URL = https://SEU-PROJETO.vercel.app
```

### Configurar diretório raiz:
Nas configurações do serviço Railway, em **"Root Directory"**, coloque:
```
SistemaOrcamento-Web/backend
```

5. Após o deploy, copie a URL do Railway (ex: `https://sistema-orcamentos.up.railway.app`)

---

## PASSO 3 — Deploy do Frontend no Vercel

1. Acesse https://vercel.com e crie conta com GitHub
2. Clique em **"New Project"** → importe `sistema-orcamentos`
3. Em **"Root Directory"**, coloque: `SistemaOrcamento-Web/frontend`
4. Clique em **Deploy**
5. Copie a URL gerada (ex: `https://sistema-orcamentos.vercel.app`)

### Atualizar a URL do backend no frontend:
Edite o arquivo `frontend/js/config.js`:
```js
const API_URL = "https://sistema-orcamentos.up.railway.app/api";
```
Substitua pela URL real do seu Railway.

Faça commit e push → Vercel redeploya automaticamente.

---

## PASSO 4 — Acesso ao sistema

1. Abra a URL do Vercel no navegador
2. Login: **admin** / senha que você definiu em `ADMIN_PASSWORD`
3. Na primeira entrada, configure materiais, ambientes e serviços em **Configurações**

---

## Atualizar o sistema no futuro

Basta editar os arquivos e fazer push para o GitHub.
Railway e Vercel vão detectar e atualizar automaticamente.

---

## Senhas e segurança

- Altere a senha padrão na página **Configurações → Alterar Senha**
- Guarde a `SECRET_KEY` do Railway em lugar seguro
- Não compartilhe as variáveis de ambiente

---

## Estrutura de pastas

```
SistemaOrcamento-Web/
├── backend/          ← API Python (Railway)
│   ├── main.py
│   ├── database.py
│   ├── auth.py
│   ├── routers/
│   └── utils/
└── frontend/         ← Telas HTML (Vercel)
    ├── index.html    ← Login
    ├── dashboard.html
    ├── orcamento.html
    ├── historico.html
    ├── clientes.html
    ├── cobrancas.html
    ├── montador.html
    └── configuracoes.html
```
