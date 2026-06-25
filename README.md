# 🌿 Yoona Head Spa

Sistema web de gestão integrada para o **Yoona Head Spa** — um spa de terapias capilares de Cuiabá-MT. O sistema cobre todo o ciclo de atendimento: do **agendamento online do cliente** (sem necessidade de login) até o **fechamento financeiro** com cálculo de comissões dos profissionais.

> Projeto desenvolvido para a disciplina de **Programação Web** — IFMT, 7º semestre (2026/1).
> Autora: **Ana Beatriz Schuindt**.

**Stack:** Python · Django 6 · SQLite · HTML/CSS/JavaScript

---

## 📑 Sumário

1. [Motivação](#-motivação)
2. [Funcionalidades principais](#-funcionalidades-principais)
3. [Arquitetura](#-arquitetura)
4. [Estrutura de diretórios](#-estrutura-de-diretórios)
5. [Tecnologias](#-tecnologias)
6. [Passo a passo para replicar](#-passo-a-passo-para-replicar)
7. [Acessos e URLs principais](#-acessos-e-urls-principais)
8. [Backup e restauração do banco](#-backup-e-restauração-do-banco)

---

## 💡 Motivação

O Yoona Head Spa controlava seus atendimentos de forma manual (agenda em papel e WhatsApp), o que gerava problemas comuns de um negócio de serviços por hora marcada:

- **Conflito de horários** — risco de marcar dois clientes no mesmo horário.
- **Falta de histórico clínico** — sem registro estruturado de alergias, sensibilidades e procedimentos anteriores, essenciais antes de aplicar cosméticos.
- **Controle financeiro frágil** — cálculo de comissões dos terapeutas feito à mão, sujeito a erros.
- **Atrito no agendamento** — exigir cadastro com senha afasta o cliente.

O objetivo do sistema é **automatizar o agendamento**, manter um **prontuário digital (anamnese)** em conformidade com a **LGPD** e **automatizar o controle de comissões**, tudo num painel único — sem depender do admin técnico do Django para a operação do dia a dia.

---

## ✨ Funcionalidades principais

O sistema atende a três perfis de usuário:

### 👤 Cliente (área pública, sem login)

- Visualização do **catálogo de terapias** (com fotos, duração e preço).
- **Identificação por CPF** (sem senha) — clientes recorrentes são reconhecidos; novos preenchem um cadastro rápido.
- **Agendamento online** com calendário e grade de horários dinâmica (carregada via AJAX), que bloqueia horários ocupados, horários já passados e datas indisponíveis.
- **Aplicação de voucher** de desconto no resumo, com cálculo do valor final em tempo real.
- **Ficha de anamnese** (saúde capilar) com campos condicionais e consentimento LGPD.

### 🛠️ Administrador (painel)

- **CRUD de terapias/serviços** com upload de imagem e paginação.
- **Gestão diária da agenda**: vincular terapeuta e mudar o status do atendimento.
- **Conclusão de atendimento** que **gera a comissão automaticamente** (imutável).
- **Bloqueios de agenda** (dias da semana recorrentes ou datas específicas).
- **CRUD de vouchers** (percentual ou valor fixo, com limite de uso e validade).
- **Relatório de comissões** (fechamento de caixa) com filtros por terapeuta e período.
- **Cadastro de terapeutas** que **cria o login** do profissional junto.
- **Gestão de clientes**: lista com busca por nome/CPF, ficha 360º com histórico de agendamentos e edição de cadastro.

### 💆 Terapeuta (login próprio)

- **Agenda do dia** com apenas os seus atendimentos.
- **Consulta de anamnese** dos seus clientes, com **alertas visuais de risco** (alergias/sensibilidade em destaque vermelho) e **restrição de acesso por vínculo (LGPD)** — não vê fichas de clientes de outros profissionais.

---

## 🏗️ Arquitetura

### Padrão MVT (Model–View–Template)

O projeto segue o padrão do Django:

- **Model** — define os dados e as regras de negócio (validações, propriedades calculadas, imutabilidade).
- **View** — orquestra a requisição; majoritariamente **Class-Based Views (CBV)** genéricas (`ListView`, `CreateView`, `UpdateView`, `DetailView`) e algumas `View` customizadas.
- **Template** — camada de apresentação em HTML, com dois layouts-base.

### Divisão em módulos (apps)

A lógica é separada por **domínio de negócio**, em 4 aplicações + o pacote de configuração:

| Módulo                     | Responsabilidade                                                                            | Principais entidades                                           |
| --------------------------- | ------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| **`yoona/`**        | Configuração do projeto, roteamento central, autenticação e redirecionamento por perfil | —                                                             |
| **`servicos/`**     | Catálogo de terapias e seu gerenciamento                                                   | `Servico`                                                    |
| **`clientes/`**     | Identificação por CPF, cadastro, anamnese e gestão de clientes                           | `Cliente`, `Anamnese`                                      |
| **`terapeutas/`**   | Profissionais e seu percentual de comissão (com login vinculado)                           | `Terapeuta` (1–1 com `User`)                              |
| **`agendamentos/`** | Agenda, vouchers, descontos, comissões e bloqueios                                         | `Agendamento`, `Voucher`, `Comissao`, `BloqueioAgenda` |

> O mixin de segurança **`AdminStaffRequiredMixin`** é definido em `servicos/views.py` e **reutilizado** pelos demais apps, centralizando a proteção das telas administrativas.

### Modelo de dados (entidades e relações)

```
User (Django) 1───1 Terapeuta
                         │
Cliente 1───1 Anamnese   │ (N)
   │ (N)                 │
   └──────── Agendamento ───────── (N) Servico
                  │ │ │
        (N) Voucher │ └── 1───1 Comissao ──── (N) Terapeuta
                    │
              BloqueioAgenda (independente: regras de disponibilidade)
```

- **Cliente 1–1 Anamnese**: cada cliente tem no máximo uma ficha de saúde.
- **Agendamento**: liga `Cliente`, `Servico`, `Terapeuta` (opcional) e `Voucher` (opcional).
- **Agendamento 1–1 Comissao**: gerada ao concluir; a comissão guarda o **valor absoluto** (não recalcula se a taxa do terapeuta mudar depois).
- **Terapeuta 1–1 User**: o login é um usuário padrão do Django (senha com hash).

### Camada de apresentação

- **`base_cliente.html`** — layout mobile-first da área pública (identidade verde/dourado).
- **`base_admin.html`** — layout de dashboard com menu lateral, usado pelo admin **e** pelo terapeuta.
- Calendário com **Flatpickr**; ícones **FontAwesome** (locais); fontes **Google Fonts**.

### Fluxos principais

**1. Agendamento (cliente):**
`CPF → escolha de serviço/data/horário → voucher (opcional) → confirmação → anamnese.`
A confirmação roda dentro de `transaction.atomic()` + `select_for_update()` para **evitar que dois clientes reservem o mesmo horário** (condição de corrida).

**2. Conclusão e comissão (admin):**
`Agenda do dia → vincular terapeuta → status "Concluído" → comissão gerada automaticamente.`
O valor da comissão = `valor_final × percentual_comissao`, gravado de forma **imutável**.

### Decisões técnicas e de segurança

- **Concorrência:** transações atômicas + travamento de linha no agendamento e na aplicação de voucher.
- **Integridade financeira:** `Comissao.save()` lança erro se houver tentativa de alteração; o admin do Django desabilita adicionar/editar comissões.
- **LGPD:** CPF mascarado na ficha clínica e **acesso à anamnese restrito por vínculo** (terapeuta só vê seus clientes).
- **Autenticação:** áreas administrativas protegidas por mixin (`login` + `is_staff`); senhas com hash; proteção **CSRF**; **logout via POST** (exigência do Django 6).

---

## 📁 Estrutura de diretórios

```
yoona/
├── manage.py                  # utilitário de linha de comando do Django
├── requirements.txt           # dependências do projeto
├── db.sqlite3                 # banco de dados (ignorado pelo Git)
│
├── yoona/                     # CONFIGURAÇÃO DO PROJETO
│   ├── settings.py            # apps, templates, static, media, autenticação
│   ├── urls.py                # roteador central
│   ├── views.py               # login, painéis e redirecionamento por perfil
│   └── static/assets/css/     # yoona-cliente.css / yoona-admin.css (tema)
│
├── servicos/                  # APP: catálogo de terapias
├── clientes/                  # APP: clientes, CPF e anamnese
├── terapeutas/                # APP: terapeutas e comissão
├── agendamentos/              # APP: agenda, vouchers, comissões, bloqueios
│   └── (cada app: models.py, forms.py, views.py, urls.py, admin.py, migrations/)
│
├── templates/                 # HTML (base_cliente, base_admin + telas)
├── media/                     # uploads de imagem (ignorado pelo Git)
└── static/                    # arquivos coletados / FontAwesome
```

> 📘 Para a documentação **função por função**, consulte o arquivo `Documentacao_Yoona.pdf`.

---

## 🧰 Tecnologias

| Categoria      | Tecnologia                                       |
| -------------- | ------------------------------------------------ |
| Linguagem      | Python 3.13                                      |
| Framework      | Django 6.0.5                                     |
| Banco de dados | SQLite                                           |
| Imagens        | Pillow (campo de imagem dos serviços)           |
| Front-end      | HTML5, CSS3, JavaScript (Flatpickr, FontAwesome) |

---

## 🚀 Passo a passo para replicar

### Pré-requisitos

- **Python 3.13+** instalado
- **Git** instalado

### 1. Clonar o repositório

```bash
git clone <url-do-repositorio>
cd yoona
```

### 2. Criar e ativar o ambiente virtual

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\activate
```

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar as dependências

```bash
pip install -r requirements.txt
```

### 4. Aplicar as migrações (cria o banco)

```bash
python manage.py migrate
```

### 5. Criar um superusuário (administrador)

```bash
python manage.py createsuperuser
```

> Informe usuário, e-mail e senha quando solicitado. Esse usuário acessa o painel administrativo.

### 6. Executar o servidor

```bash
python manage.py runserver
```

### 7. Acessar no navegador

- Área do cliente: **http://127.0.0.1:8000/**
- Painel (login): **http://127.0.0.1:8000/login/**

> 💡 Em uma cópia recém-clonada **não há dados** (o banco é ignorado pelo Git). Cadastre alguns serviços e ao menos um terapeuta pelo painel para testar o fluxo completo — ou restaure um backup (seção abaixo).

---

## 🔑 Acessos e URLs principais

| Área                | URL                           | Acesso    |
| -------------------- | ----------------------------- | --------- |
| Site / catálogo     | `/`                         | Público  |
| Agendamento (CPF)    | `/agendar/`                 | Público  |
| Login                | `/login/`                   | —        |
| Painel — Serviços  | `/painel/admin/`            | Admin     |
| Painel — Agenda     | `/painel/admin/agenda/`     | Admin     |
| Painel — Vouchers   | `/painel/admin/vouchers/`   | Admin     |
| Painel — Comissões | `/painel/admin/comissoes/`  | Admin     |
| Painel — Terapeutas | `/painel/admin/terapeutas/` | Admin     |
| Painel — Clientes   | `/painel/admin/clientes/`   | Admin     |
| Agenda do terapeuta  | `/painel/terapeuta/`        | Terapeuta |
| Admin do Django      | `/admin_django/`            | Admin     |

---

---

Projeto acadêmico — Yoona Head Spa · IFMT · Programação Web · 2026/1
