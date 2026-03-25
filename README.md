# OculosVR Backend

API REST do painel administrativo **OculosVR / TourVR**, construída com FastAPI, MongoDB e autenticação JWT. Fornece os endpoints de autenticação, gerenciamento de usuários e health check consumidos pelo frontend React.

---

## Sumário

1. [Visão geral](#1-visão-geral)
2. [Objetivo](#2-objetivo)
3. [Stack e tecnologias](#3-stack-e-tecnologias)
4. [Requisitos para execução](#4-requisitos-para-execução)
5. [Instalação](#5-instalação)
6. [Configuração do ambiente](#6-configuração-do-ambiente)
7. [Execução em desenvolvimento](#7-execução-em-desenvolvimento)
8. [Endpoints disponíveis](#8-endpoints-disponíveis)
9. [Scripts disponíveis](#9-scripts-disponíveis)
10. [Estrutura de pastas](#10-estrutura-de-pastas)
11. [Arquitetura resumida](#11-arquitetura-resumida)
12. [Fluxo de autenticação](#12-fluxo-de-autenticação)
13. [Modelos e schemas](#13-modelos-e-schemas)
14. [Banco de dados](#14-banco-de-dados)
15. [Segurança](#15-segurança)
16. [Testes](#16-testes)
17. [Variáveis de ambiente](#17-variáveis-de-ambiente)
18. [Convenções e boas práticas identificadas](#18-convenções-e-boas-práticas-identificadas)
19. [Estado atual do projeto](#19-estado-atual-do-projeto)
20. [Limitações e pontos de atenção](#20-limitações-e-pontos-de-atenção)
21. [Próximos passos sugeridos](#21-próximos-passos-sugeridos)
22. [Troubleshooting](#22-troubleshooting)
23. [Guia rápido para novos desenvolvedores](#23-guia-rápido-para-novos-desenvolvedores)
24. [Licença](#24-licença)

---

## 1. Visão geral

Este módulo é o backend do projeto **OculosVR**, responsável por:

- Expor uma API REST documentada automaticamente via Swagger UI e ReDoc;
- Autenticar administradores com credenciais email/senha e emitir tokens JWT;
- Persistir dados de usuários no MongoDB;
- Reportar a saúde da aplicação e da conexão com o banco de dados;
- Fornecer os dados do usuário autenticado ao frontend via endpoint protegido.

A API é consumida exclusivamente pelo frontend React hospedado em `http://localhost:3000` durante o desenvolvimento.

---

## 2. Objetivo

Fornecer a camada de dados e autenticação para o painel administrativo OculosVR. O escopo atual identificado no código cobre:

- Registro de novos usuários administradores;
- Login com validação de credenciais e emissão de JWT;
- Recuperação dos dados do usuário autenticado;
- Health check com status do MongoDB;
- Suite de testes automatizados cobrindo os fluxos críticos.

---

## 3. Stack e tecnologias

| Componente | Tecnologia | Versão |
|---|---|---|
| Framework web | FastAPI | 0.135.1 |
| Servidor ASGI | Uvicorn | 0.42.0 |
| Banco de dados | MongoDB | 6+ |
| Driver MongoDB | pymongo (AsyncMongoClient) | 4.16.0 |
| Autenticação | JWT — python-jose | 3.5.0 |
| Hash de senha | passlib + bcrypt | 1.7.4 / 4.0.1 |
| Validação e config | Pydantic v2 + pydantic-settings | 2.13.1 |
| HTTP client de teste | httpx | 0.28.1 |
| Testes | pytest | 9.0.2 |
| Linguagem | Python | 3.11+ |

---

## 4. Requisitos para execução

- Python 3.11 ou superior
- MongoDB 6+ rodando localmente ou acessível via URI (MongoDB Atlas)
- `pip` para instalação das dependências

---

## 5. Instalação

### Via script de automação (recomendado)

```powershell
# A partir da raiz do monorepo
.\scripts\install-backend.ps1
```

### Manual

```powershell
cd "Oculos VR backend"

# Criar ambiente virtual
python -m venv .venv

# Ativar o ambiente virtual (Windows)
.venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt
```

---

## 6. Configuração do ambiente

Copie o arquivo de exemplo e ajuste as variáveis:

```powershell
Copy-Item .env.example .env
```

Edite o `.env` gerado:

```env
APP_NAME=OculosVR Backend
APP_ENV=development
APP_DEBUG=true
APP_HOST=0.0.0.0
APP_PORT=8000
APP_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

MONGODB_URL=mongodb://localhost:27017
MONGODB_DB=oculosvr_db

JWT_SECRET_KEY=troque_por_uma_chave_segura
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

> **Atenção:** nunca versione o arquivo `.env`. Ele está incluído no `.gitignore`.

---

## 7. Execução em desenvolvimento

### Via script de automação

```powershell
# A partir da raiz do monorepo
.\scripts\run-backend.ps1
```

### Manual

```powershell
cd "Oculos VR backend"
.venv\Scripts\activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

| Interface | URL |
|---|---|
| API (raiz) | http://127.0.0.1:8000 |
| Swagger UI | http://127.0.0.1:8000/docs |
| ReDoc | http://127.0.0.1:8000/redoc |
| Health check | http://127.0.0.1:8000/health/ |

---

## 8. Endpoints disponíveis

### Públicos

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/` | Metadata da API: nome, versão, URL dos docs, health |
| `GET` | `/health/` | Status da API e conexão com MongoDB |
| `POST` | `/auth/register` | Cria novo usuário |
| `POST` | `/auth/login` | Autentica usuário e retorna JWT |

### Protegidos (requerem `Authorization: Bearer <token>`)

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/users/me` | Retorna dados do usuário autenticado |

### Detalhes de payload

**`POST /auth/register`**

```json
{
  "email": "admin@exemplo.com",
  "password": "senha_segura",
  "full_name": "Nome Completo",
  "username": "nome_usuario"
}
```

**`POST /auth/login`**

```json
{
  "email": "admin@exemplo.com",
  "password": "senha_segura"
}
```

Resposta:

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

**`GET /users/me`** — Header obrigatório: `Authorization: Bearer <token>`

```json
{
  "email": "admin@exemplo.com",
  "full_name": "Nome Completo",
  "username": "nome_usuario",
  "role": "user",
  "is_active": true,
  "created_at": "2026-01-01T00:00:00",
  "updated_at": "2026-01-01T00:00:00"
}
```

---

## 9. Scripts disponíveis

| Script | Localização | Descrição |
|---|---|---|
| `install-backend.ps1` | `scripts/` | Cria venv e instala dependências |
| `run-backend.ps1` | `scripts/` | Sobe o Uvicorn com hot-reload |
| `test-backend.ps1` | `scripts/` | Executa a suite pytest |

---

## 10. Estrutura de pastas

```text
Oculos VR backend/
├── main.py                     ← ponto de entrada ASGI (importa app/main.py)
├── requirements.txt            ← dependências Python
├── .env.example                ← template de variáveis de ambiente
├── README.md
│
└── app/
    ├── main.py                 ← fábrica FastAPI, CORS, lifespan, roteamento
    │
    ├── core/
    │   ├── config.py           ← Settings (pydantic-settings, lê .env)
    │   ├── database.py         ← MongoDBManager: conexão, ciclo de vida
    │   └── security.py         ← hash de senha, criação/decodificação de JWT
    │
    ├── api/
    │   ├── deps.py             ← dependências FastAPI (serviços, auth de token)
    │   └── v1/
    │       ├── router.py       ← agrega sub-routers (/health, /auth, /users)
    │       └── routes/
    │           ├── auth.py     ← POST /auth/register, POST /auth/login
    │           ├── users.py    ← GET /users/me
    │           └── health.py   ← GET /health/
    │
    ├── models/
    │   └── user.py             ← UserModel (dataclass — estrutura do documento MongoDB)
    │
    ├── schemas/
    │   └── user.py             ← Pydantic: UserCreate, UserLogin, TokenResponse,
    │                              UserRegisterResponse, UserMeResponse
    │
    ├── repositories/
    │   └── user_repository.py  ← find_by_email(), create_user() (acesso direto ao MongoDB)
    │
    └── services/
        └── user_service.py     ← register_user(), login_user() (regras de negócio)

tests/
├── conftest.py                 ← fixtures: mongo_up, mongo_down, client (TestClient)
├── test_health.py              ← 6 testes de health e CORS
└── test_auth_flow.py           ← 10 testes de registro, login e /users/me
```

---

## 11. Arquitetura resumida

A aplicação segue uma arquitetura em camadas com separação clara de responsabilidades:

```
Request HTTP
     │
     ▼
app/main.py  ←── CORS Middleware
     │
     ▼
api/v1/router.py
     │
     ├─ routes/health.py    →  retorna status
     ├─ routes/auth.py      →  deps.get_user_service() → UserService
     └─ routes/users.py     →  deps.get_current_user() → UserService
                                        │
                                        ▼
                                  services/user_service.py
                                        │
                                        ▼
                               repositories/user_repository.py
                                        │
                                        ▼
                                    MongoDB
```

### Ponto de entrada

O arquivo `main.py` na raiz é o ponto de entrada ASGI e simplesmente importa `app` de `app/main.py`. A fábrica em `app/main.py` configura:

- **Lifespan**: estabelece e encerra a conexão com o MongoDB;
- **CORS**: lê as origens permitidas de `Settings.cors_origins`;
- **Rotas**: inclui `api_router` com prefixo `/api/v1` implícito nos sub-routers.

### Injeção de dependências

`app/api/deps.py` centraliza duas dependências críticas:

- `get_user_service()`: instancia `UserService` com o `UserRepository` já conectado ao banco via `request.state`;
- `get_current_user()`: valida o Bearer token JWT e retorna o usuário autenticado, lançando `401` ou `503` conforme o caso.

---

## 12. Fluxo de autenticação

```
1. POST /auth/login
   └─ UserService.login_user(email, password)
       ├─ UserRepository.find_by_email(email)
       │   └─ [404] usuário não encontrado
       ├─ security.verify_password(password, hashed)
       │   └─ [401] senha incorreta
       └─ security.create_access_token({"sub": email})
           └─ retorna TokenResponse {access_token, token_type}

2. GET /users/me
   └─ deps.get_current_user(token)
       ├─ security.decode_access_token(token)
       │   └─ [401] token inválido ou expirado
       └─ UserRepository.find_by_email(email_do_token)
           ├─ [404] usuário não encontrado
           └─ retorna UserMeResponse
```

O token JWT contém o campo `sub` com o e-mail do usuário. O algoritmo padrão é `HS256` e a expiração é configurável via `ACCESS_TOKEN_EXPIRE_MINUTES`.

---

## 13. Modelos e schemas

### UserModel (dataclass — `app/models/user.py`)

Representa o documento armazenado no MongoDB:

| Campo | Tipo | Descrição |
|---|---|---|
| `email` | `str` | Identificador único do usuário |
| `hashed_password` | `str` | Senha em bcrypt |
| `full_name` | `str \| None` | Nome completo (opcional) |
| `username` | `str \| None` | Nome de usuário (opcional) |
| `role` | `str` | Papel do usuário (padrão: `"user"`) |
| `is_active` | `bool` | Indica se a conta está ativa |
| `created_at` | `datetime` | Timestamp de criação |
| `updated_at` | `datetime` | Timestamp da última atualização |

### Schemas Pydantic (`app/schemas/user.py`)

| Schema | Uso | Campos |
|---|---|---|
| `UserCreate` | Entrada — registro | `email`, `password`, `full_name?`, `username?` |
| `UserLogin` | Entrada — login | `email`, `password` |
| `TokenResponse` | Saída — login | `access_token`, `token_type` |
| `UserRegisterResponse` | Saída — registro | Dados públicos sem senha |
| `UserMeResponse` | Saída — `/users/me` | Dados completos sem senha |

---

## 14. Banco de dados

O MongoDB é acessado de forma assíncrona via `AsyncMongoClient` do pymongo. A conexão é gerenciada pelo `MongoDBManager` em `app/core/database.py`, que:

- Abre a conexão durante o lifespan da aplicação;
- Detecta credenciais placeholder (`<db_password>`) e aborta sem tentativa de rede;
- Disponibiliza a instância do cliente em `request.state` para injeção de dependências;
- Reporta o status da conexão no endpoint `/health/`.

A coleção utilizada é `users`, criada automaticamente no banco definido por `MONGODB_DB`.

---

## 15. Segurança

Todas as funções de segurança estão centralizadas em `app/core/security.py`:

| Função | Descrição |
|---|---|
| `hash_password(plain)` | Gera hash bcrypt via passlib |
| `verify_password(plain, hashed)` | Comparação em tempo constante |
| `create_access_token(data, expires_delta?)` | Gera JWT assinado com `JWT_SECRET_KEY` |
| `decode_access_token(token)` | Decodifica e valida o JWT; retorna `None` se inválido |

**Práticas identificadas:**
- Senhas nunca trafegam após o registro;
- Tokens não são armazenados no backend (stateless);
- CORS configurado explicitamente por lista de origens;
- Erros de autenticação retornam `401` sem revelar detalhes do motivo.

---

## 16. Testes

A suite de testes está em `tests/` e cobre os fluxos críticos da aplicação com MongoDB mockado.

### Executar

```powershell
# Via script
.\scripts\test-backend.ps1

# Manual
cd "Oculos VR backend"
.venv\Scripts\activate
pytest -v
```

### Cobertura dos testes

**`tests/test_health.py`** — 6 testes:

| Teste | Descrição |
|---|---|
| Rota raiz | Retorna metadata da API (nome, versão, docs) |
| CORS preflight | Aceita origem do frontend em `/auth/login` |
| Health com banco ativo | Reporta `database: "up"` |
| Health com banco inativo | Reporta `database: "down"` |
| Health com credencial placeholder | Detecta sem chamada de rede |
| Formato da resposta | Valida estrutura do JSON |

**`tests/test_auth_flow.py`** — 10 testes:

| Teste | Descrição |
|---|---|
| Registro com sucesso | Retorna dados públicos do usuário |
| Registro com e-mail duplicado | Retorna `409 Conflict` |
| Login com sucesso | Retorna `access_token` e `token_type` |
| Login com senha incorreta | Retorna `401 Unauthorized` |
| Login com usuário inexistente | Retorna `404 Not Found` |
| Registro com banco inativo | Retorna `503 Service Unavailable` |
| Login com banco inativo | Retorna `503 Service Unavailable` |
| `/users/me` com token válido | Retorna dados do usuário |
| `/users/me` com token inválido | Retorna `401 Unauthorized` |
| `/users/me` sem token | Retorna `401 Unauthorized` |

### Fixtures (`tests/conftest.py`)

| Fixture | Descrição |
|---|---|
| `mongo_up` | Mocka conexão MongoDB bem-sucedida |
| `mongo_down` | Mocka falha de conexão MongoDB |
| `client` | `TestClient` FastAPI com MongoDB mockado |

---

## 17. Variáveis de ambiente

Todas as variáveis são carregadas pelo `Settings` em `app/core/config.py` via `pydantic-settings`. O arquivo `.env` deve estar na raiz do módulo backend.

| Variável | Padrão | Obrigatório | Descrição |
|---|---|---|---|
| `APP_NAME` | `OculosVR Backend` | Não | Nome exibido na metadata da API |
| `APP_ENV` | `development` | Não | Ambiente (`development`, `production`) |
| `APP_DEBUG` | `true` | Não | Modo debug do FastAPI |
| `APP_HOST` | `0.0.0.0` | Não | Host de bind do Uvicorn |
| `APP_PORT` | `8000` | Não | Porta do servidor |
| `APP_CORS_ORIGINS` | `http://localhost:3000,...` | **Sim** | Origens CORS permitidas (separadas por vírgula) |
| `MONGODB_URL` | `mongodb://localhost:27017` | **Sim** | URI de conexão ao MongoDB |
| `MONGODB_DB` | `oculosvr_db` | **Sim** | Nome do banco de dados |
| `JWT_SECRET_KEY` | `change_me_in_local_env` | **Sim** | Chave secreta para assinar tokens JWT |
| `JWT_ALGORITHM` | `HS256` | Não | Algoritmo de assinatura JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Não | Tempo de expiração do token em minutos |

> **Segurança:** substitua `JWT_SECRET_KEY` por um valor forte antes de qualquer deploy. Nunca versione o `.env`.

---

## 18. Convenções e boas práticas identificadas

- **Separação de camadas:** rotas, serviços, repositórios e modelos estão em pastas distintas com responsabilidades bem definidas;
- **Injeção de dependências:** uso consistente do sistema de `Depends()` do FastAPI para injeção de serviços e autenticação;
- **Schemas separados de modelos:** `models/` define a estrutura do banco; `schemas/` define os contratos HTTP de entrada e saída;
- **Configuração centralizada:** todas as variáveis de ambiente são lidas uma única vez via `Settings` e injetadas onde necessário;
- **Gerenciamento de ciclo de vida:** conexão com MongoDB aberta/fechada via `@asynccontextmanager` no lifespan;
- **Testes com mocks:** o MongoDB é mockado nos testes, garantindo independência de ambiente externo;
- **Respostas de erro padronizadas:** erros de banco retornam `503` com mensagem consistente via `build_database_http_exception()`;
- **Senhas nunca retornam:** os schemas de saída (`UserMeResponse`, `UserRegisterResponse`) nunca expõem `hashed_password`.

---

## 19. Estado atual do projeto

| Funcionalidade | Status |
|---|---|
| Registro de usuário | ✅ Implementado |
| Login com JWT | ✅ Implementado |
| Endpoint `/users/me` protegido | ✅ Implementado |
| Health check com status do MongoDB | ✅ Implementado |
| Suite de testes automatizados (16 testes) | ✅ Implementado |
| CORS configurado para o frontend | ✅ Implementado |
| Configuração via variáveis de ambiente | ✅ Implementado |
| Hash seguro de senhas (bcrypt) | ✅ Implementado |
| Documentação automática (Swagger/ReDoc) | ✅ Disponível |
| Endpoints adicionais (ambientes VR, sessões) | 🔲 Não implementados |
| Atualização de perfil do usuário | 🔲 Não implementado |
| Roles/permissões além do campo `role` | 🔲 Não implementado |
| Refresh de token | 🔲 Não implementado |

---

## 20. Limitações e pontos de atenção

- **Registro somente via Swagger:** não há endpoint de convite ou interface administrativa para criar usuários; o registro é aberto via `POST /auth/register`;
- **Sem refresh token:** o token JWT expira e o usuário precisa fazer login novamente; não há mecanismo de renovação;
- **Campo `role` não utilizado nas rotas:** o campo existe no modelo, mas não há controle de acesso baseado em papel implementado nas rotas;
- **Sem paginação:** os repositórios atuais não implementam paginação para listagens;
- **MongoDB sem índice explícito:** o índice único no campo `email` não está criado por código; depende de configuração manual ou migração;
- **Sem logging estruturado:** a aplicação não tem um sistema de logs configurado além do output padrão do Uvicorn.

---

## 21. Próximos passos sugeridos

1. **Criar índice único no campo `email`** no MongoDB para garantir integridade mesmo sem a verificação de duplicata no serviço;
2. **Implementar refresh token** para melhorar a experiência do usuário e reduzir logins repetidos;
3. **Adicionar endpoints de domínio** (ambientes VR, sessões, configurações) conforme a evolução do produto;
4. **Implementar controle de acesso por `role`** utilizando dependências FastAPI para proteger rotas administrativas;
5. **Adicionar logging estruturado** (ex.: `structlog`) para facilitar observabilidade em produção;
6. **Configurar paginação** nos repositórios antes de crescimento do volume de dados;
7. **Adicionar validação de força de senha** no schema `UserCreate`.

---

## 22. Troubleshooting

**`ModuleNotFoundError` ao iniciar**
O ambiente virtual não está ativado ou as dependências não foram instaladas. Execute:
```powershell
.venv\Scripts\activate
pip install -r requirements.txt
```

**`Connection refused` ao MongoDB**
Verifique se o MongoDB está em execução na porta configurada. O endpoint `/health/` informa o status detalhado da conexão.

**`JWT_SECRET_KEY` com valor padrão em produção**
Risco de segurança crítico. Gere uma chave segura:
```python
import secrets; print(secrets.token_hex(32))
```

**Erro `CORS policy` no frontend**
A origem do frontend não está em `APP_CORS_ORIGINS`. Adicione `http://localhost:3000` (ou a URL correta) no `.env`.

**`503 Service Unavailable` em todas as rotas**
O MongoDB não conectou durante o lifespan. Verifique `MONGODB_URL` e o status do banco.

**Credencial placeholder detectada**
O `MongoDBManager` detecta `<db_password>` na URI e aborta a conexão sem tentativa de rede. Substitua pela URI real no `.env`.

**Testes falhando por conexão real ao MongoDB**
Os testes usam mocks e não devem depender de MongoDB ativo. Verifique se as fixtures `mongo_up` / `mongo_down` do `conftest.py` estão sendo carregadas corretamente.

---

## 23. Guia rápido para novos desenvolvedores

Para compreender esta base rapidamente, siga esta ordem de leitura:

1. **`app/core/config.py`** — entenda todas as variáveis de ambiente e como o `Settings` as carrega;

2. **`app/core/database.py`** — entenda como o MongoDB é conectado, o ciclo de vida e o health check;

3. **`app/core/security.py`** — veja como senhas são hash e como JWTs são criados e validados;

4. **`app/models/user.py`** e **`app/schemas/user.py`** — entenda a diferença entre o modelo do banco e os schemas de entrada/saída;

5. **`app/repositories/user_repository.py`** — veja as queries MongoDB disponíveis;

6. **`app/services/user_service.py`** — entenda as regras de negócio de registro e login;

7. **`app/api/deps.py`** — veja como a injeção de dependências e a autenticação de token funcionam;

8. **`app/api/v1/routes/`** — leia as rotas `auth.py`, `users.py` e `health.py` para ver o fluxo completo de request → response;

9. **`tests/`** — leia os testes como documentação executável dos comportamentos esperados.

Para rodar o ambiente completo:

```powershell
Copy-Item .env.example .env
# edite .env com suas configurações locais
.\scripts\install-backend.ps1
.\scripts\run-backend.ps1
```

---

## 24. Licença

Nenhum arquivo de licença foi identificado neste repositório. A distribuição e o uso deste código estão sujeitos às definições do proprietário do projeto.
