# LashApp

API para gerenciamento de uma agenda de lash designer. O sistema permite
publicar uma agenda, consultar horários disponíveis, administrar serviços e
horários de trabalho e registrar agendamentos de clientes.

O projeto está preparado para mais de uma profissional: cada profissional
possui seu próprio perfil público, serviços e agenda.

## Funcionalidades

- Cadastro de clientes e autenticação por e-mail com JWT.
- Perfil público da profissional e link de agenda por `slug`.
- Consulta pública de serviços, horários de trabalho e disponibilidade.
- Criação, listagem, aprovação, rejeição e cancelamento de agendamentos.
- Cadastro e gerenciamento de serviços, horários de trabalho, pausas e cupons.
- Anamnese vinculada ao agendamento.
- Geração de ficha de anamnese em PDF e armazenamento de assinaturas.
- Área administrativa do Django para operação do sistema.
- Suíte de testes com `pytest` e `pytest-django`.

## Tecnologias

- Python 3.11
- Django 6.1
- Django REST Framework
- Simple JWT
- SQLite para desenvolvimento
- WeasyPrint e ReportLab para documentos PDF
- WhiteNoise e Gunicorn para execução em produção
- Docker

## Estrutura do repositório

```text
.
├── lashapp-backend/
│   ├── lashapp/
│   │   ├── config/          # Configurações e URLs do Django
│   │   ├── users/           # Usuários, cadastro e autenticação
│   │   ├── professionals/  # Perfis das profissionais
│   │   ├── scheduling/     # Serviços, agenda e agendamentos
│   │   ├── anamnesis/      # Anamnese e geração de PDFs
│   │   ├── manage.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── private_media/      # PDFs e assinaturas que não devem ser públicos
├── LICENSE
└── README.md
```

Os comandos abaixo devem ser executados em
`lashapp-backend/lashapp`.

## Configuração local

### Pré-requisitos

- Python 3.11 ou compatível com o projeto.
- `pip` e `venv`.
- Dependências nativas do WeasyPrint quando aplicável.

No Ubuntu/Debian, instale as bibliotecas necessárias para PDF:

```bash
sudo apt-get update
sudo apt-get install -y \
  libpango-1.0-0 \
  libpangoft2-1.0-0 \
  libharfbuzz0b \
  libffi-dev \
  shared-mime-info
```

No Windows, as DLLs do GTK/Pango usadas pelo WeasyPrint precisam estar
disponíveis no `PATH`. A API pode iniciar sem elas, mas a geração de PDFs
ficará pendente até que a dependência seja configurada.

### Instalação

Linux/macOS:

```bash
cd lashapp-backend/lashapp
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Windows PowerShell:

```powershell
cd lashapp-backend\lashapp
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edite o arquivo `.env` e defina, no mínimo:

```dotenv
SECRET_KEY=uma-chave-secreta
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
TIME_ZONE=America/Sao_Paulo
PRIVATE_MEDIA_ROOT=..\private_media
```

`PRIVATE_MEDIA_ROOT` deve apontar para um diretório persistente fora do
armazenamento público servido pelo Nginx ou pela aplicação. Não versionar o
arquivo `.env` nem credenciais reais.

### Banco de dados e execução

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

A API ficará disponível em `http://127.0.0.1:8000`.

O usuário profissional pode ser configurado pelo Django Admin em
`http://127.0.0.1:8000/admin/`.

## Docker

O `Dockerfile` está em `lashapp-backend/lashapp`. Para criar a imagem e
executar o servidor:

```bash
cd lashapp-backend/lashapp
docker build -t lashapp-api .
docker run --rm -p 8000:8000 --env-file .env lashapp-api
```

Antes de usar o container em produção:

- configure um banco persistente, preferencialmente PostgreSQL;
- monte um volume persistente para `PRIVATE_MEDIA_ROOT`;
- configure `SECRET_KEY`, `ALLOWED_HOSTS` e `DEBUG=False`;
- configure HTTPS, proxy reverso e política de CORS;
- execute as migrações no ambiente de destino.

## API

Todas as rotas da aplicação usam o prefixo `/api`.

### Rotas públicas

| Método | Rota | Descrição |
| --- | --- | --- |
| `GET` | `/public/<slug>/` | Perfil e serviços da profissional |
| `GET` | `/public/<slug>/availability/` | Horários disponíveis |
| `GET` | `/public/<slug>/working-hours/` | Horários de trabalho publicados |
| `GET` | `/public/<slug>/schedule/` | Agenda pública |
| `POST` | `/public/<slug>/appointments/` | Solicitação pública de agendamento |

Para consultar disponibilidade, informe a data e o serviço, por exemplo:

```text
GET /api/public/minha-agenda/availability/?date=2026-10-15&service_id=1
```

### Autenticação

| Método | Rota | Descrição |
| --- | --- | --- |
| `POST` | `/auth/register/` | Cadastro de cliente |
| `POST` | `/auth/token/` | Login e emissão dos tokens JWT |
| `POST` | `/auth/token/refresh/` | Renovação do token de acesso |
| `GET/PATCH` | `/auth/me/` | Consulta e atualização do usuário autenticado |
| `GET/POST` | `/auth/clients/` | Listagem e cadastro de clientes |

Envie o token de acesso nas rotas protegidas:

```http
Authorization: Bearer <access-token>
```

### Agendamentos e gestão

| Método | Rota | Descrição |
| --- | --- | --- |
| `GET/POST` | `/appointments/` | Lista ou cria agendamentos |
| `DELETE` | `/appointments/<id>/` | Cancela um agendamento |
| `POST` | `/appointments/<id>/approve/` | Aprova um agendamento |
| `POST` | `/appointments/<id>/reject/` | Rejeita um agendamento |
| `GET/POST` | `/services/` | Lista ou cria serviços |
| `GET/PATCH/DELETE` | `/services/<id>/` | Gerencia um serviço |
| `GET/POST` | `/services/working-hours/` | Gerencia horários de trabalho |
| `GET/POST` | `/services/lunch-breaks/` | Gerencia pausas |
| `GET/POST` | `/coupons/` | Lista ou cria cupons |
| `GET/POST` | `/anamneses/` | Lista ou cria anamneses |
| `POST` | `/anamneses/prefill/` | Pré-preenche uma anamnese |
| `GET` | `/anamneses/<id>/pdf/` | Baixa o PDF da anamnese |

As permissões e os campos aceitos por cada rota são definidos pelos
serializers e views do backend. A API valida, entre outras regras, horários
no passado, conflitos de agenda e a relação entre serviço e profissional.

## Testes

Na pasta `lashapp-backend/lashapp`:

```bash
pytest
pytest -v
pytest scheduling/
```

## Armazenamento e privacidade

Anamneses podem conter dados pessoais e de saúde. PDFs e assinaturas devem
ser mantidos em `PRIVATE_MEDIA_ROOT`, sem exposição direta por arquivos
estáticos ou pelo servidor web. Em produção, restrinja o acesso por
permissões do sistema operacional, mantenha backups protegidos e não
inclua esses arquivos no controle de versão.

## Licença

Este repositório está sob uma licença proprietária de visualização
(`LICENSE`). O código pode ser consultado para avaliação e referência
educacional, mas não pode ser usado, copiado, modificado, distribuído ou
hospedado sem autorização prévia do titular dos direitos.
