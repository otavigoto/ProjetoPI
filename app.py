import mysql.connector
from flask import Flask, render_template, url_for, redirect, request, session, flash
from flask_mail import Mail, Message
from datetime import datetime
from random import randrange

app = Flask(__name__)
app.secret_key = 'shhhhhh'  # Chave de segurança para as sessões, que mantém o usuário logado e protege dados sensíveis.

# Função para abrir uma conexão com o Banco de Dados MySQL.
def get_db():
    try:
        conexao = mysql.connector.connect(
            host='127.0.0.1',       # IP do banco de dados.
            user='root',            # Usuário de login do banco.
            password='otavio2912',   # Senha do banco de dados.
            database='bd_betinha',   # Nome do banco de dados que estamos usando.
        )
        return conexao
    except mysql.connector.Error as err:
        print(f"Erro: {err}")
        return None

# Lista que armazena os eventos para exibir na interface.
lista_itens_eventos = []

# Configurações para envio de e-mail
mail_settings = {
    "MAIL_SERVER": 'smtp.gmail.com',     # Servidor de e-mail (aqui, o Gmail).
    "MAIL_PORT": 465,                    # Porta de envio do e-mail.
    "MAIL_USE_TLS": False,               # TLS desativado.
    "MAIL_USE_SSL": True,                # SSL ativado para segurança.
    "MAIL_USERNAME": 'trabalhobetinha777@gmail.com',  # E-mail remetente.
    "MAIL_PASSWORD": 'oabc hsen ryxu evla'            # Senha do e-mail.
}
app.config.update(mail_settings)
mail = Mail(app)

# Função para aplicar taxa de saque dependendo do valor sacado.
def aplicarTaxaSaque(valor_saque):
    if valor_saque <= 100:
        taxa = 0.04  # 4% de taxa
    elif valor_saque <= 1000:
        taxa = 0.03  # 3% de taxa
    elif valor_saque <= 5000:
        taxa = 0.02  # 2% de taxa
    elif valor_saque <= 100000:
        taxa = 0.01  # 1% de taxa
    else:
        taxa = 0     # Sem taxa
    valor_final = valor_saque * (1 - taxa)  # Calcula o valor final após aplicar a taxa
    return valor_saque

# Função para movimentar saldo do usuário (saque ou depósito).
def movimentarSaldo(valor, tipo_saldo, tipo_transacao, titulo_transacao):
    id_user = session.get('userid')  # Identifica o usuário logado pelo ID.
    connection = get_db()
    if connection:
        cursor = connection.cursor()
        saldo = float(session['saldo'])  # Obtém o saldo atual do usuário.

        if tipo_transacao == 'saque':  # Verifica se é um saque.
            if saldo >= valor:
                valor = aplicarTaxaSaque(valor)  # Aplica a taxa de saque.

                # Atualiza o saldo do usuário no banco de dados ao deduzir o valor do saque.
                cursor.execute('UPDATE carteira SET saldo = saldo - %s WHERE id_usuarios = %s', (valor, id_user))
                flash('Saque concluído com sucesso!', 'success')
            else:
                flash('Saldo insuficiente para saque', 'error')
                return False
        elif tipo_transacao == 'deposito':  # Verifica se é um depósito.
            # Atualiza o saldo do usuário no banco de dados, somando o valor do depósito ao saldo atual.
            cursor.execute(f'UPDATE carteira SET {tipo_saldo} = {saldo} + %s WHERE id_usuarios = %s', (valor, id_user))
            flash('Depósito concluído com sucesso!', 'success')

        # Insere um histórico da transação no banco de dados para registrar o saque ou depósito.
        cursor.execute(
            'INSERT INTO historico_saldo (titulo, valor, data_transacao, id_usuarios) VALUES (%s, %s, NOW(), %s)',
            (titulo_transacao, -valor if tipo_transacao == 'saque' else valor, id_user)
        )

        connection.commit()  # Confirma as mudanças no banco.
        cursor.close()
        connection.close()

# Rota da página inicial.
@app.route('/')
@app.route('/index')
def index():
    if 'loggedin' in session:
        return redirect(url_for('home'))
    else:
        return render_template('index.html', title='Index')

# Rota para a página de registro de usuários.
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'loggedin' in session:
        return redirect(url_for('index'))
    elif request.method == 'POST':
        connection = get_db()
        cursor = connection.cursor()

        admin = 'N'  # Define o tipo do usuário (não é admin por padrão).
        name = request.form.get('name')  # Pega o nome do formulário.
        email = request.form.get('email')  # Pega o e-mail do formulário.
        password = request.form.get('password')  # Pega a senha do formulário.
        birth = request.form.get('birth')  # Pega a data de nascimento.

        # Consulta SQL para verificar se o e-mail já está registrado.
        cursor.execute('SELECT * FROM usuarios WHERE email = %s', (email,))
        account = cursor.fetchone()

        if account:  # Se já existe, informa o usuário.
            cursor.close()
            connection.close()
            flash('Conta já existe!')
            return redirect(url_for('register'))
        else:
            # Insere um novo usuário no banco de dados.
            # 'usuarios' tabela: armazena informações sobre os usuários, incluindo id, tipo de conta, nome, email, senha e data de nascimento.
            cursor.execute('INSERT INTO usuarios VALUES (%s, %s, %s, %s, %s, %s)', (None, admin, name, email, password, birth))

            # Cria uma carteira inicial para o novo usuário.
            # 'carteira' tabela: guarda o saldo de cada usuário e suas informações financeiras (inicializa com saldo zero).
            cursor.execute('SELECT * FROM usuarios WHERE email = %s', (email,))
            id_user = cursor.fetchone()
            cursor.execute('INSERT INTO carteira VALUES (%s, %s, %s, %s, %s, %s, %s)', (None, id_user[0], 0, 0, 0, 0, 0))
            connection.commit()
            cursor.close()
            connection.close()

            flash('Cadastro realizado com sucesso!')
            return redirect(url_for('login'))

    return render_template('register.html', title='Register')

# Rota para login dos usuários.
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'loggedin' in session:
        return redirect(url_for('index'))
    msg = ''
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        connection = get_db()
        if connection:
            cursor = connection.cursor()
            # Verifica as credenciais do usuário, conferindo se o e-mail e a senha estão corretos.
            cursor.execute('SELECT * FROM usuarios WHERE email = %s AND senha = %s', (email, password))
            account = cursor.fetchone()

            if account:
                # Salva as informações de sessão do usuário após o login.
                session['loggedin'] = True
                session['userid'] = account[0]
                session['admin'] = account[1]
                session['name'] = account[2]
                session['email'] = account[3]
                flash('Entrou com sucesso!')

                # Consulta SQL para obter o saldo do usuário para exibir na interface.
                cursor.execute('SELECT saldo FROM carteira WHERE id_usuarios = %s', (session['userid'],))
                resultado = cursor.fetchone()
                session['saldo'] = resultado[0] if resultado else None

                if session['admin'] == 'N':
                    return render_template('askBuyCredits.html', title='Comprar Créditos')
                else:
                    return redirect(url_for('home'))
            else:
                flash('Email ou senha incorretos')
            cursor.close()
            connection.close()

    return render_template('login.html', title='Login', msg=msg)

# Rota para comprar créditos.
@app.route('/askBuyCredits', methods=['POST'])
def askBuyCredits():
    valor_deposito = request.form.get('valor_deposito')
    movimentarSaldo(valor_deposito, 'saldo', 'deposito', 'deposito')
    return redirect(url_for('index'))

# Rota para o logout (sair) do usuário.
@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('admin', None)
    session.pop('email', None)
    session.pop('userid', None)
    session.pop('name', None)
    session.pop('saldo', None)
    return redirect(url_for('login'))
    
@app.route('/home')
def home():
  # Verifica se o usuário está logado na sessão; se não, redireciona para a página de login
  if 'loggedin' not in session:
    return redirect(url_for('login'))
  else:
    # Estabelece uma conexão com o banco de dados e cria um cursor para executar consultas
    connection = get_db()
    cursor = connection.cursor()

    # Consulta eventos aprovados e cujas apostas ainda estão abertas
    cursor.execute(f'SELECT * FROM eventos WHERE is_aprovado = "S" AND data_fim_aposta > NOW()')
    result = cursor.fetchall()
    total = len(result)  # Conta o número total de eventos retornados
    
    if result:
      # Consulta eventos que estão aprovados e com data de aposta entre o momento atual e os próximos 20 dias
      cursor.execute('SELECT * FROM eventos WHERE is_aprovado = "S" AND data_fim_aposta BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 20 DAY);')
      dataapostas = cursor.fetchall()
      
      # Seleciona os três eventos com maior número de apostas, aprovados e com data de fim de aposta ainda válida
      cursor.execute('SELECT e.* FROM eventos e JOIN ( SELECT num_apostas FROM eventos GROUP BY num_apostas ORDER BY num_apostas DESC LIMIT 3 ) AS top_eventos ON e.num_apostas = top_eventos.num_apostas AND is_aprovado = "S" AND data_fim_aposta > NOW()')
      maisapostas = cursor.fetchall()
      
      # Fecha o cursor e a conexão com o banco
      cursor.close()
      connection.close()

      # Renderiza a página inicial com as informações dos eventos
      if dataapostas:
        return render_template('home.html', title='HomePage', result=result, total=total, dataapostas=dataapostas, maisapostas=maisapostas)
      else:
        return render_template('home.html', title='HomePage', result=result, total=total)

    # Fecha o cursor e a conexão com o banco
    cursor.close()
    connection.close()
    
  # Renderiza a página inicial caso não haja resultados
  return render_template('home.html', title='HomePage', result=result, total=total)

@app.route('/apostar-evento/<int:evento_id>', methods=['GET', 'POST'])
def apostar(evento_id):
  # Verifica se o usuário está logado e não é admin; apenas usuários comuns podem apostar
  if 'loggedin' in session and session['admin'] == 'N':
    connection = get_db()
    cursor = connection.cursor()

    # Verifica se o evento é aprovado e ainda está aberto para apostas
    cursor.execute('SELECT * FROM eventos WHERE id_eventos = %s AND is_aprovado = "S" AND data_fim_aposta > NOW() AND data_inicio_aposta < NOW()', (evento_id,))
    result = cursor.fetchone()
    
    # Se o evento não está disponível para apostas, exibe mensagem e redireciona para a página inicial
    if not result:
        flash('Apostas ja terminaram ou vão começar', 'error')
        cursor.close()
        connection.close()
        return redirect(url_for('home'))

    # Obtém o ID do usuário a partir da sessão
    user_id = session['userid']
    
    # Busca o saldo do usuário na tabela de carteira
    cursor.execute('SELECT * FROM carteira WHERE id_usuarios = %s', (user_id,))
    saldo = cursor.fetchone()

    # Se o método de solicitação é POST, significa que o usuário está tentando apostar
    if request.method == 'POST':
        valor_aposta = request.form.get('valor_aposta')
        resposta = request.form.get('naoapostar')
        
        # Caso o usuário selecione "não apostar", redireciona para a página inicial
        if resposta == 'naoapostar':
          cursor.close()
          connection.close()
          return redirect(url_for('home'))
        else:
          valor_aposta = float(valor_aposta)

          # Verifica se o saldo do usuário é suficiente para a aposta
          if saldo[4] < valor_aposta:
              flash('Saldo insuficiente para essa aposta', 'error')
              cursor.close()
              connection.close()
              return redirect(url_for('formsBuyCredits'))
          # Verifica se o valor da aposta está dentro do limite permitido pelo evento
          elif result[4] < valor_aposta or result[5] > valor_aposta:
              flash('Quantidade apostada inválida', 'error')
              cursor.close()
              connection.close()
              return redirect(url_for('home'))
          else:
              # Atualiza o saldo do usuário na tabela de carteira
              cursor.execute(
                  'UPDATE carteira SET saldo = saldo - %s WHERE id_usuarios = %s',
                  (valor_aposta, user_id)
              )
              
              # Incrementa o número de apostas no evento
              cursor.execute(
                  'UPDATE eventos SET num_apostas = num_apostas + %s WHERE id_eventos = %s',
                  (1, evento_id)
              )

              # Insere os dados da aposta na tabela de aposta_eventos
              cursor.execute(
                  'INSERT INTO aposta_eventos (id_eventos, id_usuarios, valor) VALUES (%s, %s, %s)',
                  (evento_id, user_id, valor_aposta)
              )

              # Confirma as transações no banco de dados
              connection.commit()

              flash('Aposta realizada com sucesso!', 'success')
              return redirect(url_for('home'))

    # Fecha o cursor e a conexão com o banco
    cursor.close()
    connection.close()
    # Renderiza a página de aposta para o evento específico
    return render_template('betEvent.html', title='Apostar', result=result)
  else:
    # Redireciona para a página inicial se o usuário não estiver logado ou for admin
    return redirect(url_for('home'))

@app.route('/finalizarApostas', methods=['GET', 'POST'])
def finalizarApostas():
  # Verifica se o usuário logado é admin e está na sessão; apenas admin pode finalizar apostas
  if session['admin'] == 'S' and 'loggedin' in session:
    connection = get_db()
    cursor = connection.cursor()

    # Seleciona eventos aprovados que já foram concluídos
    cursor.execute(
                    'SELECT * FROM eventos WHERE is_aprovado = "S" AND data_fim_evento < NOW();'
                )
    eventos = cursor.fetchall()
    
    # Se não houver eventos finalizados, exibe uma mensagem
    if not eventos:
      flash('Nenhum evento finalizado')
    
    # Fecha o cursor e a conexão com o banco de dados
    cursor.close()
    connection.close()

    return render_template('finalizarApostas.html', title='Finalizar Apostas',eventos=eventos)
  else:
    return redirect(url_for('home'))
  
#Rota de finalizar apostas
@app.route('/finalizarApostas/<int:evento_id>', methods=['GET', 'POST'])
def finalizar(evento_id):
  # Se for admin e estiver logado
  if session['admin'] == 'S' and 'loggedin' in session:
    #Conexão com o banco de dados
    connection = get_db()
    cursor = connection.cursor()
    
    #Selecionar tudo da tabela aposta_eventos que o id do evento seja igual ao url /finalizarApostas/<int:evento_id>
    cursor.execute('SELECT * FROM aposta_eventos WHERE id_eventos = %s', (evento_id,))
    
    #Aposta_eventos recebe todos os evento com id_eventos iguais ao url
    aposta_eventos = cursor.fetchall()
    
    
    #Se possuir tabelas
    if aposta_eventos:
      total=0
      totalganhadores=0
      
      #Criar uma lista de ganhadores [[id_usuario, quantidade_apostada,] [...]]
      ganhadores = []
      #Criar uma lista de dinheiro dos perdedores [quantidade_apostada, ...]
      perdedores = []
      
      #Passar por todas as apostas do evento
      for eventos in (aposta_eventos):
        
        #Utiliza randrange para pegar um numero aleatório entre 0 e 10
        ganhou = randrange(0, 10)
        
        #Se o numero aleatório for maior que 7, adiciona aos ganhadores(id_usuario, dinheiro_apostado), senão, adiciona aos perdedores(dinheiro_apostado)
        if ganhou > 7:
          ganhadores.append([eventos[1], eventos[3]])
        else:
          perdedores.append(eventos[3])
          
      #Passar por todos os perdedores e somar todos as apostas   
      for i in (perdedores):
        total += i
      #Passar por todos os ganhadores e somar suas apostas
      for i in (ganhadores):
        totalganhadores += i[1]
        
      #Dividir o total de perdedores pelo total de ganhadores
      divisao = total / totalganhadores
      
      
      #Passar por todos os ganhadores, calculando a porcentagem de ganho atraves da quantidade apostada e atualizando o bd
      for i in (ganhadores):
        #calculo da porcentagem de acordo com a aposta do usuario
        retorno = divisao * i[1]
        
        #Atualiza a carteira do usuario, somando a aposta inicial com o retorno
        cursor.execute('UPDATE carteira SET saldo = saldo + %s + %s WHERE id_usuarios = %s',(retorno, i[1], i[0],))
        
      #Ao passar por todos os ganhadores, remove o evento ao coloca-lo como reprovado
      cursor.execute('UPDATE eventos SET is_aprovado = "N" WHERE id_eventos = %s', (evento_id,))
      
    #Envia ao banco
    connection.commit()
    
    #Fecha a conexao
    cursor.close()
    connection.close()
    
  #Caso não seja admin ou esteja logado
  else:
    return redirect(url_for('home'))
  
  #Retorna a tela anterior
  return redirect(url_for('finalizarApostas'))


#Rota de criar novos eventos
@app.route('/createNewEvent', methods=['GET', 'POST',])
def createNewEvent():
  #Apenas clientes e logados
  if session['admin'] == 'N' and 'loggedin' in session:
    
    #Quando utilizar o método post (enviar o formulário)
    if request.method == 'POST':
      
      #Obter todas as informações do formulário
      id_usuarios = session['userid']
      titulo = request.form.get('titulo')
      descricao = request.form.get('descricao')
      valor_max_aposta = request.form.get('valor_max_aposta')
      valor_min_aposta = request.form.get('valor_min_aposta')
      is_aprovado = 'I'
      data_inicio_aposta = request.form.get('data_inicio_aposta')
      data_fim_evento = request.form.get('data_fim_evento')
      data_fim_aposta = request.form.get('data_fim_aposta')
      categoria = request.form.get('opcoes')
      
      #Receber a data e o horário atual
      data_atual = datetime.now()
      
      #Transofrmar as datas dos formulários em tipo datetime
      data1 = datetime.strptime(data_inicio_aposta,"%Y-%m-%dT%H:%M")
      data2 = datetime.strptime(data_fim_aposta, "%Y-%m-%dT%H:%M")
      
      #Formatar a data_fim_evento para ter horário
      datatotal = data_fim_evento + 'T00:00'
      
      #Transformar a ultima data em tipo datetime
      data3 = datetime.strptime(datatotal, "%Y-%m-%dT%H:%M")
      
      #Compara se as datas estão em ordem correta
      if data1 > data2 or data1 == data2 or data2 >= data3:
        flash('Data de inicio de apostas maior que o fim ou fim da aposta é menor ou igual ao fim do evento')
        
        #Recarregar a página
        return render_template('newEvent.html', title='Criar Evento')
      
      #Valor mínimo não pode ser maior que o valor máximo
      elif valor_min_aposta > valor_max_aposta:
        flash('Valor maximo menor que o valor minimo')
        
        #Recarrega a página
        return render_template('newEvent.html', title='Criar Evento')
      
      #Não permite criar eventos no passado
      elif data_atual > data1 or data_atual > data2 or data_atual > data3:
        flash('Evento não pode ser no passado')
        
        #Recarrega a página
        return render_template('newEvent.html', title='Criar Evento')
      else:
        
        #Abre a conexao com o bd
        connection = get_db()
        cursor = connection.cursor()
        
        #Insere na tabela eventos os valores:(%s)
        cursor.execute('INSERT INTO eventos VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s,%s)', (None,id_usuarios,titulo,descricao,valor_max_aposta,valor_min_aposta,is_aprovado,data_inicio_aposta,data_fim_evento,data_fim_aposta,0,categoria))
        
        #Envia ao banco
        connection.commit()
        
        #Fecha a conexao
        cursor.close()
        connection.close()
        
        #Redireciona ao home
        return redirect(url_for('home'))
  else:
    
    #Redireciona ao home caso não esteja logado ou seja admin
    return redirect(url_for('home'))
  
  #Carrega o html newEvent
  return render_template('newEvent.html', title='Criar Evento')

#Rota de aprovar eventos
@app.route('/approveEvents', methods=['GET', 'POST'])
def approveEvents():
  
  #Coloca como padrão a variavel idle = I
  idle = ['I']
  
  #Caso não esteja logado ou não seja admin
  if 'loggedin' not in session or session['admin'] == 'N':
    
    #Redireciona ao login
    return redirect(url_for('login'))
  else:
    
      #Conexao com o bd
      connection = get_db()
      cursor = connection.cursor()
    
      #Selecionar todos atributos dos eventos que estão esperando aprovação (is_aprovado = idle) e ainda não acabou o período de apostas (data_fim_apostas > NOW())
      cursor.execute('SELECT * FROM eventos WHERE is_aprovado = %s AND data_fim_aposta > NOW()', (idle))
      
      #Receber o valor selecionado do banco
      account = cursor.fetchall()
      
      #Fechar a conexao
      cursor.close()
      connection.close()
      total = len(account)
      
      #Se existir um evento (account)
      if account:
        #Carregar o html approveEvent
        return render_template('approveEvent.html', title='HomePage',account=account, total=total)
      else:
        #Caso não tenha nenhum evento para ser aprovado ou rejeitado, exibir:
        flash('Não há nenhum evento para ser aprovado')
        
      #Com o método POST:
      if request.method == 'POST':
        #Redirecionar ao home
        return redirect(url_for('home'))
  
  #Carregar o html approveEvent
  return render_template('approveEvent.html', title='HomePage', account=account, total=total)

#Rota para aprovar o evento selecionado
@app.route('/aprovar-evento/<int:evento_id>')
def aprovar_evento(evento_id):
  #Se o usuario for admin e estiver logado
  if session['admin'] == 'S' and 'loggedin' in session:
    
    #Conxao com o bd
    connection = get_db()
    cursor = connection.cursor()
    
    #Atualiza na tabela eventos para o evento ser aprovado, tendo o mesmo id do evento selecionado
    cursor.execute("UPDATE eventos SET is_aprovado = 'S' WHERE id_eventos = %s", (evento_id,))
    
    #Enviar atualização e fechar a conexao
    connection.commit()
    cursor.close()
    connection.close()
  else:
    #Retornar ao home
    return redirect(url_for('home'))
  #Ir para rota approveEvents
  return redirect(url_for('approveEvents'))

#Rota para desaprovar evento selecionado
@app.route('/desaprovar-evento/<int:evento_id>', methods=['GET', 'POST'])
def desaprovar_evento(evento_id):
  
  #Se for admin e estiver logado
  if session['admin'] == 'S' and 'loggedin' in session:
    #Pegar o input "justificativa" do formulario
    justificativa = request.form.get('opcoes')
    
    #abrir conexao com o bd
    connection = get_db()
    cursor = connection.cursor()
    
    #Selecionar o usuario que criou o evento selecionado
    cursor.execute(f'SELECT id_usuarios FROM eventos WHERE id_eventos = {evento_id}')
    #atribuir id do usuario para a variavel
    evento = cursor.fetchone()
    
    #Selecionar o email do usuario selecionado anteriormente
    cursor.execute('SELECT email FROM usuarios WHERE id_usuarios = %s', (evento[0],))
    #atribuir email para a variavel
    usuario = cursor.fetchone()

    #escolher assunto para enviar ao email do criador do evento
    destinatario = usuario[0]
    assunto = f'Evento {evento_id} Rejeitado'
    mensagem = f'O evento {evento_id} foi rejeitado pela seguinte razão: {justificativa}'

    #Se conseguir executar:
    try:
        #mensagem para ser enviada para o email e o destinatario
        msg = Message(assunto, sender=app.config['MAIL_USERNAME'], recipients=[destinatario])
        msg.body = mensagem
        
        #enviar a mensagem
        mail.send(msg)
        
        #feedback para o admin
        flash('Email enviado com sucesso!')
        
        #atualizar o evento para desaprovado
        cursor.execute(f"UPDATE eventos SET is_aprovado = 'N' WHERE id_eventos = {evento_id}")
        
        #enviar mudança do banco de dados
        connection.commit()
        
        
    #Senão
    except Exception as e:
        #mensagem para o admin
        flash(f'Erro ao enviar o email: {e}')
    
    #fechar conexao com o banco de dados
    cursor.close()
    connection.close()    
    
    #redirecionar para a rota approveEvents
    return redirect(url_for('approveEvents'))
  else:
    #redirecionar para o home
    return redirect(url_for('home'))
  
#rota para pesquisar eventos
@app.route('/searchEvents', methods=['GET', 'POST',])
def searchEvents():
  return render_template('home.html', title='HomePage')

#Resultado dos eventos pesquisados
@app.route('/resultEvents', methods=['GET', 'POST',])
def resultEvents():
  #Se for admin e estiver logado
  if session['admin'] == 'S' and 'loggedin' in session:
    
    #conexao com o banco
    connection = get_db()
    cursor = connection.cursor()
    
    #pegar input do formulário
    q = request.args.get('q')
    
    #Selecionar eventos que possuem o mesmo titulo e estejam aprovados
    cursor.execute(f'SELECT * FROM eventos WHERE titulo LIKE "{q}" AND is_aprovado = "S"')
    result = cursor.fetchall()
    
    #fechar conexao com o banco
    cursor.close()
    connection.close()
    total = len(result)
    #Se encontrar eventos:
    if result:
      flash('Eventos encontrados')
    #senao
    else:
      flash('Não há eventos relacionados')
      
    #carregar o html resultEvents
    return render_template('resultEvents.html', title='Pesquisa', q = result, total=total)
  else:
    #redirecionar para home
    return redirect(url_for('home'))
  
#Eventos organizados por categorias
@app.route('/categoryEvents', methods=['GET', 'POST',])
def categoryEvents():
  #Se estiver logado e nao for admin
  if session['admin'] == 'N' and 'loggedin' in session:
    
    #conexao com o banco de dados
    connection = get_db()
    cursor = connection.cursor()
    
    #Pegar inputs do formulário
    opcoes = request.form.get('opcoes') or request.args.get('opcoes')
    
    sort_by = request.form.get('sort_by')
    
    print(f"Categoria: {opcoes}, Sort By: {sort_by}")
    
    #tipos de organização
    order_clause = ""
    if sort_by == "titulo_asc":
        order_clause = "ORDER BY titulo ASC"
    elif sort_by == "titulo_desc":
        order_clause = "ORDER BY titulo DESC"
    elif sort_by == "valor_minimo_asc":
        order_clause = "ORDER BY valor_min_aposta ASC"
    elif sort_by == "valor_minimo_desc":
        order_clause = "ORDER BY valor_min_aposta DESC"
        
    #texto completo para executar no banco, com o tipo de organização escolhido
    query = f"""
          SELECT * FROM eventos 
          WHERE categoria LIKE %s 
          AND is_aprovado = 'S' 
          AND data_fim_aposta > NOW() 
          {order_clause}
      """
    #Executar todos os comando que foram mesclados na variável query
    cursor.execute(query, (opcoes,))
    
    result = cursor.fetchall()
    
    total = len(result)
    
    print("Resultados:", result)

    #Fechar conexao
    cursor.close()
    connection.close()
    
    #Carregar html categoryEvents
    return render_template('categoryEvents.html', title='Categorias',total=total, result=result, opcoes=opcoes)
  else:
    #redirecionar para a rota home
    return redirect(url_for('home'))


#Rota para a carteira do usuario
@app.route('/myWallet')
def myWallet():
  #Caso esteja logado e nao seja admin
  if 'loggedin' in session and session['admin'] == 'N':

      #abrir conexao
      connection = get_db()
      
      #variável com o id do usuario logado
      id_user = session['userid']
      
      #Se houver conexao
      if connection:
        
          #Selecionar o saldo da carteira do usuario logado
          cursor = connection.cursor()
          cursor.execute(
          f'SELECT saldo FROM carteira WHERE id_usuarios = %s',
          (id_user,))
          resultado = cursor.fetchone()
          print(resultado)
          
          #Se encontrar um saldo
          if resultado is not None:
              session['saldo'] = resultado[0]  # Acessa o primeiro valor retornado
          
          #Se não encontrar um saldo
          else:
              session['saldo'] = None  # Ou outra lógica de tratamento de erro
          saldo = session['saldo']

          #Selecionar tudo da tabela historico_saldo e ordenar por data
          cursor.execute(
          'SELECT * FROM historico_saldo WHERE id_usuarios = %s ORDER BY data_transacao DESC',
          (id_user,))
          historico = cursor.fetchall()
        # Formatação dos dados
          historico_formatado = []

          cont = 1
          
          #passa por todo o histórico do usuário
          for item in historico:
              #caso tenho mais de 15 históricos
              if cont == 15:
                  break
              transacao = {
                  "id": item[0],
                  "tipo": item[1],
                  "valor": item[2],
                  "data": item[3].strftime('%d/%m/%Y %H:%M')  # Formato de data legível
              }
              
              #adicionar todos os itens acima em uma lista
              historico_formatado.append(transacao)
              cont+=1
              
          #fechar conexao
          cursor.close()
          connection.close()
          
      #Carregar html myWallet
      return render_template('myWallet.html', title='Carteira',saldo=saldo,historico=historico_formatado)
  else:
    
      #redirecionar para a rota home
      return redirect(url_for('home'))
    
#Rota para comprar Creditos
@app.route('/formsBuyCredits', methods=['GET'])
def formsBuyCredits():
    #Carregar html fromsBuyCredits
    return render_template('formsBuyCredits.html', title='Comprar Crétidos')

#Rota para sacar Creditos
@app.route('/formsWithdrawCredits')
def formsWithdrawCredits():
    #Carregar html formsWithdrawCredits
    return render_template('formsWithdrawCredits.html', title='Comprar Créditos')
  
#Rota para comprar os créditos
@app.route('/buyCredits',methods=['POST',])
def buyCredits():
  
  #Se não for admin e estiver logado
  if session['admin'] == 'N' and 'loggedin' in session:
    #receber o valor do formulário
    valor_deposito = request.form.get('valor_deposito')
    print(valor_deposito)
    
    #ir para a função movimentarSaldo(no começo do código)
    movimentarSaldo(valor_deposito,'saldo','deposito','deposito')
    
    #redirecionar para a rota myWallet
    return redirect(url_for('myWallet'))
  
  #Senão
  else:
    #exibir mensagem
    flash('admin não pode comprar créditos')
    
    #redirecionar para home
    return redirect(url_for('home'))

#Rota para sacar os créditos
@app.route('/withdrawCredits',methods=['POST',])
def withdrawCredits():
  #Se não for admin e estiver logado
  if session['admin'] == 'N' and 'loggedin' in session:
    
    #Criar conexao com o db
    connection = get_db()
    
    #Resgatar todos os inputs do formulário
    banco = request.form.get('banco')
    agencia = request.form.get('agencia')
    tipoConta = request.form.get('tipoConta')
    chavePix = request.form.get('chavePix')
    valor_a_retirar = request.form.get('valor_a_retirar')
    id_user = session.get('userid')

    #chamar função movimentarSaldo(no começo do código)
    status = movimentarSaldo(valor_a_retirar,'saldo','saque','saque')

    #Se estiver conectado com o banco e retornar TRUE
    if connection and status == True:
      
        #Criar conexao com o bd
        cursor = connection.cursor()
        
        #Aatualizar na carteira a agencia,banco,chavePix do usuário
        cursor.execute('UPDATE carteira SET agencia = %s, banco = %s, chavePix = %s WHERE id_usuarios LIKE %s',(agencia,banco,chavePix,id_user))
        
        #Exibir mensagem
        flash('Saque concluido', 'success')
        
        #Enviar ao bd e fechar conexao
        connection.commit()
        cursor.close()
        connection.close()

    #redirecionar ao myWallet
    return redirect(url_for('myWallet'))
  else:
    #exibir mensagem:
    flash('admin não pode sacar créditos')
    
    #redirecionar ao home
    return redirect(url_for('home'))
  
if __name__ == '__main__':
  app.run(debug=True)