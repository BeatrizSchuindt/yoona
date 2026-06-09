from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Cliente, Anamnese
from .forms import CPFForm, NovoCadastroForm, AnamneseForm


class IdentificacaoView(View):
    """
    US03 — Identificação do cliente via CPF, sem criação de senha.

    Fluxo:
      GET  → exibe formulário com campo CPF
      POST (só cpf)          → valida CPF
          · CPF inválido          → volta com erro
          · CPF encontrado no BD  → salva cliente_id na sessão → redireciona para agendamento
          · CPF válido / não cadastrado → re-renderiza com campos extras (nome + telefone)
      POST (cpf + nome + tel) → cria novo Cliente → salva cliente_id na sessão → redireciona
    """

    template_name = 'identificacao.html'

    def get(self, request):
        # Limpa qualquer identificação anterior ao iniciar novo fluxo
        request.session.pop('cliente_id', None)
        return render(request, self.template_name, {'form_cpf': CPFForm()})

    def post(self, request):
        # ── Etapa 2: CPF + dados de cadastro ──────────────────────────────
        if 'nome_completo' in request.POST:
            form_cadastro = NovoCadastroForm(request.POST)
            if form_cadastro.is_valid():
                dados = form_cadastro.cleaned_data
                cliente = Cliente.objects.create(
                    cpf=dados['cpf'],
                    nome_completo=dados['nome_completo'],
                    telefone=dados['telefone'],
                )
                request.session['cliente_id'] = cliente.pk
                messages.success(
                    request,
                    f'Bem-vinda, {cliente.nome_completo.split()[0]}! '
                    'Cadastro realizado. Agora escolha o serviço e horário.'
                )
                return redirect('agendamentos:solicitacao')

            # Formulário de cadastro inválido → re-renderiza com erros
            return render(request, self.template_name, {
                'form_cpf': CPFForm(initial={'cpf': request.POST.get('cpf', '')}),
                'form_cadastro': form_cadastro,
                'mostrar_cadastro': True,
            })

        # ── Etapa 1: apenas CPF ───────────────────────────────────────────
        form_cpf = CPFForm(request.POST)
        if not form_cpf.is_valid():
            return render(request, self.template_name, {'form_cpf': form_cpf})

        cpf_formatado = form_cpf.cleaned_data['cpf']

        try:
            cliente = Cliente.objects.get(cpf=cpf_formatado)
            # Cliente recorrente encontrado
            request.session['cliente_id'] = cliente.pk
            messages.success(
                request,
                f'Olá, {cliente.nome_completo.split()[0]}! '
                'Identificação confirmada. Agora escolha o serviço e horário.'
            )
            return redirect('agendamentos:solicitacao')

        except Cliente.DoesNotExist:
            # Novo cliente — exibe campos extras
            form_cadastro = NovoCadastroForm(initial={'cpf': cpf_formatado})
            return render(request, self.template_name, {
                'form_cpf': form_cpf,
                'form_cadastro': form_cadastro,
                'cpf_novo': cpf_formatado,
                'mostrar_cadastro': True,
            })


class AnamneseView(View):
    """
    US06 — Ficha de Saúde Capilar.
    GET  → exibe formulário vazio (novo cliente) ou pré-preenchido (recorrente)
    POST → cria ou atualiza a anamnese vinculada ao cliente da sessão
    """

    template_name = 'anamnese.html'

    def _checar_sessao(self, request):
        cliente_id = request.session.get('cliente_id')
        if not cliente_id:
            return None
        try:
            return Cliente.objects.get(pk=cliente_id)
        except Cliente.DoesNotExist:
            return None

    def get(self, request):
        cliente = self._checar_sessao(request)
        if not cliente:
            messages.warning(request, 'Identifique-se para acessar a ficha de saúde.')
            return redirect('clientes:identificacao')

        try:
            anamnese = cliente.anamnese
            form = AnamneseForm(instance=anamnese)
        except Anamnese.DoesNotExist:
            anamnese = None
            form = AnamneseForm()

        return render(request, self.template_name, {
            'form': form,
            'cliente': cliente,
            'anamnese_existente': anamnese is not None,
        })

    def post(self, request):
        cliente = self._checar_sessao(request)
        if not cliente:
            return redirect('clientes:identificacao')

        try:
            anamnese = cliente.anamnese
        except Anamnese.DoesNotExist:
            anamnese = None

        form = AnamneseForm(request.POST, instance=anamnese)
        if form.is_valid():
            ficha = form.save(commit=False)
            ficha.cliente = cliente
            ficha.save()
            request.session.pop('agendamento_id', None)
            messages.success(
                request,
                'Ficha salva com sucesso! Obrigado por nos ajudar a cuidar melhor de você.'
            )
            return redirect('servicos:home')

        return render(request, self.template_name, {
            'form': form,
            'cliente': cliente,
            'anamnese_existente': anamnese is not None,
        })
