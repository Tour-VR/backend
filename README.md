# TourVR — Backend

API REST do TourVR: autenticação de usuários e, nas próximas fases, o conteúdo do tour.

**Stack:** Python 3.11 · FastAPI · Uvicorn · MongoDB (pymongo assíncrono) · JWT · pytest.

## Como rodar

O caminho principal é pelo repositório orquestrador
[`quest-project`](https://github.com/Tour-VR/quest-project), que sobe MongoDB, backend e
painel com Docker Compose. Na raiz do `quest-project`:

```bash
bash scripts/setup.sh   # uma vez: baixa os submódulos
bash scripts/up.sh      # sobe tudo
```

API em http://localhost:8000 · Swagger em http://localhost:8000/docs ·
saúde em http://localhost:8000/health/

**Alternativa sem Docker** (exige um MongoDB acessível), dentro desta pasta:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # e edite
uvicorn main:app --reload --port 8000
```

## Como testar

```bash
pytest -v
```

Os testes usam MongoDB mockado; não precisam de banco rodando.

## Documentação

A documentação do projeto fica no orquestrador, não aqui:

- Base de conhecimento: https://github.com/Tour-VR/quest-project/tree/main/docs
- Este serviço: [`docs/03-artefato-backend.md`](https://github.com/Tour-VR/quest-project/blob/main/docs/03-artefato-backend.md)
- Contrato da API: [`docs/06-contrato-api.md`](https://github.com/Tour-VR/quest-project/blob/main/docs/06-contrato-api.md)
