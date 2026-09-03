# Lash Designer Scheduling API

Backend em Django REST Framework para agendamento de lash designer.
Qualquer pessoa consegue **visualizar** a agenda/serviços pelo link público;
para **efetuar um agendamento** é necessário cadastro + login (JWT).

## Stack

- Django 6 + Django REST Framework
- Autenticação via JWT (`djangorestframework-simplejwt`), login por **email**
- SQLite em dev (trocar por Postgres em produção via `DATABASES` no `settings.py`)
- Testes com `pytest` + `pytest-django`, seguindo TDD

## Setup

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # ajuste SECRET_KEY antes de ir pra produção

python manage.py migrate
python manage.py createsuperuser   # cria a conta da lash designer (marque is_professional=True depois no admin)
python manage.py runserver
```

Rodar os testes:

```bash
pytest              # roda toda a suíte
pytest -v           # com detalhe de cada teste
pytest scheduling/   # só uma app
```

## Estrutura

```
users/          -> CustomUser (login por email), cadastro, JWT
professionals/  -> Professional (perfil público + slug do link de agenda)
scheduling/     -> Service, WorkingHours, TimeOff, Appointment
                   + scheduling/availability.py (cálculo de horários livres)
```

Cada app segue o mesmo padrão: `models.py`, `serializers.py`, `views.py`,
`urls.py`, e uma pasta `tests/` com `test_models.py` / `test_api.py` etc.

## Endpoints

### Públicos (sem login)

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/public/<slug>/` | Perfil da profissional + lista de serviços |
| GET | `/api/public/<slug>/availability/?date=YYYY-MM-DD&service_id=1` | Horários livres naquele dia para aquele serviço |

### Autenticação / cadastro

| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/auth/register/` | Cadastro de cliente (`email`, `password`, `name`, `phone`) |
| POST | `/api/auth/token/` | Login — retorna `access` e `refresh` (JWT) |
| POST | `/api/auth/token/refresh/` | Renova o `access` token |
| GET/PATCH | `/api/auth/me/` | Dados da usuária autenticada |

### Agendamentos (exige `Authorization: Bearer <access_token>`)

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/appointments/` | Lista os agendamentos da própria cliente |
| POST | `/api/appointments/` | Cria agendamento (`professional`, `service`, `start_datetime`) |
| DELETE | `/api/appointments/<id>/` | Cancela (soft-delete) o próprio agendamento |

O backend valida automaticamente: horário no passado, conflito de horário
com outro agendamento da mesma profissional, e se o serviço realmente
pertence à profissional informada.

## Como a "profissional única, mas escalável" funciona

Mesmo com uma única lash designer hoje, o modelo já é multi-profissional:
- `Professional` é uma entidade própria (não é o `User` direto), com slug único.
- Toda consulta de agenda/serviço/agendamento é sempre filtrada por `professional`.
- Basta cadastrar um segundo `Professional` (outro `User` com `is_professional=True`)
  que o sistema já funciona com dois links de agenda independentes — nenhuma
  mudança de schema necessária.

## Próximos passos sugeridos

- Notificação de lembrete por e-mail (job assíncrono, ex: Celery + Redis)
- Frontend em React consumindo essa API
- Deploy: Postgres + variáveis de ambiente via `.env` / secrets do provedor
- Regras extras: mínimo de antecedência para agendar, reagendamento, WhatsApp/pagamento (fase 2)
