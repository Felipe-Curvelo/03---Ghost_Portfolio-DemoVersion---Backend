import datetime
import os
from collections import defaultdict
from uuid import uuid4


import requests
from flask import Flask, jsonify, request, session, url_for, redirect, render_template, flash
from flask_cors import CORS, cross_origin
from flask_jwt_extended import (JWTManager, create_access_token,
                                get_jwt_identity, jwt_required)
from flask_jwt_extended.internal_utils import get_jwt_manager
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from mysql.connector import Error, pooling
from werkzeug.security import check_password_hash, generate_password_hash

from config import ApplicationConfig
from logic import format_db_row_to_transaction
from forms import ResetPasswordForm


#CONFIG INICIAIS
app = Flask(__name__)
app.config.from_object(ApplicationConfig)
jwt = JWTManager(app)
db = SQLAlchemy(app)
db.init_app(app)
mail=Mail(app)
cors = CORS(app)

def get_uuid():
    return uuid4().hex

picFolder = os.path.join('static', 'pics')
app.config['UPLOAD_FOLDER'] = picFolder

#Importações de preços e nomes para formatação no frontend
LIVE_PRICE_URL = os.environ["LIVE_PRICE"]
MAP_URL = os.environ["MAP"]
USD_URL = os.environ["USD"]

###INFOS PARA O CAMPO DE SELEÇÃO DE CRIPTOMOEDAS NO FRONTEND
json_data = requests.get(MAP_URL).json()
data = json_data


symbol_to_coin_id_map = dict()
for currency in data:
        id_c = currency['id']
        name_c = currency['name']
        symbol_to_coin_id_map[name_c] = id_c


name_to_symbol_map = dict()
for currency in data:
        name_c = currency['name']
        symbol_c=currency['symbol']
        image_c=currency['image']
        name_to_symbol_map[name_c] = symbol_c

name_to_image_map = dict()
for currency in data:
        name_c = currency['name']
        image_c=currency['image']
        name_to_image_map[name_c] = image_c

###BASE DE DADOS
class Users(db.Model):
    id = db.Column(db.String(32), primary_key=True, unique=True, default=get_uuid)
    name = db.Column(db.Text, nullable=False)
    surname = db.Column(db.Text, nullable=False)
    email = db.Column(db.String(345), unique=True)
    password = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default= datetime.datetime.now())

    ##DEF PARA GERAÇÃO DE EMAIL EM CASO DE RECUPERAÇÃO DE SENHA
    def get_token(user):
        access_token = create_access_token(identity=user.id)
        return access_token

    @staticmethod
    def decode_token(token, csrf_value=None, allow_expired=True):
        jwt_manager = get_jwt_manager()
        token_id = jwt_manager._decode_jwt_from_config(token, csrf_value, allow_expired)
        return token_id
##################
###############
#############################
################
###########
#####FUNÇÃO PARA EMAIL DE RESET DE SENHA


###############
def send_mail(user):
    token=user.get_token()
    msg = Message('Pedido de Reset de Senha', recipients=[user.email],sender='noreply@ghostportfolio.com')
    msg.body = f''' Para resetar sua senha, clique no link abaixo.

    {url_for('reset_token',token=token,_external=True)}


    Se você não pediu para sua senha ser resetada, por favor, ignore este e-mail.

    Caso tente acessar o link por um aparelho celular e não consegua, tente visualizar em um computador.

    '''
    mail.send(msg)

##############POOL DE CONEXÃO COM O BANCO DE DADOS

connection_pool = pooling.MySQLConnectionPool(pool_name=os.environ["POOL_NAME"],
                                                  pool_size=8,
                                                  pool_reset_session=False,
                                                  host=os.environ["POOL_HOST"],
                                                  database=os.environ["POOL_DATABASE"],
                                                  user=os.environ["POOL_USER"],
                                                  password=os.environ["POOL_PASSWORD"])

######ROTAS###################
##############################

######ABERTAS


@app.route("/")
def root():
    return jsonify ({"Hello":"There"})

###CRIAÇÃO DE USUÁRIO
@app.route("/sign-up", methods=['POST'])
def sign_up():
        username =  request.json["username"]
        usersurname =  request.json["usersurname"]
        email1 =  request.json["email1"]
        email2 =  request.json["email2"]
        password1 =  request.json["password1"]
        password2 =  request.json["password2"]

        email_exists = Users.query.filter_by(email=email1).first()
        if email1 != email2:
            return jsonify({ "Erro": "Emails não coincidem"}), 409
        elif email_exists:
            return jsonify({ "Erro": "Email já está em uso!"}), 409
        elif password1 != password2:
            return jsonify({ "Erro": "As duas senhas precisam ser iguais!"}), 409
        elif len(email1) < 5:
            return jsonify({ "Erro": "Email inválido!"}), 409
        elif len(password1) < 8:
            return jsonify({ "Erro": "A senha precisa ter no mínimo 8 caracteres!"}), 409
        else:
            hashed_password = generate_password_hash(password1, method='sha256')
            new_user = Users(name=username, surname=usersurname, email=email1, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
        
        return jsonify({
            "id": new_user.id,
            "nome": new_user.name,
            "sobrenome": new_user.surname,
            "email": new_user.email,
            "password": new_user.password,
            "data_criacao": new_user.created_at.strftime("%d/%m/%Y")
        })

@app.route("/login", methods=["POST"])
def login():
    email =  request.json["email"]
    password =  request.json["password"]

    user = Users.query.filter_by(email=email).first()

    if not check_password_hash(user.password, password):
        return jsonify({"error": "Senha errada"}), 401

    username = user.id
    

    access_token = create_access_token(identity=username)
    return jsonify({
        
        "user":{
            "id": user.id,
            "email": user.email
        }, "token":access_token}     
    )

##########RESET DE SENHA

@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    email =  request.json["email"]

    user = Users.query.filter_by(email=email).first()

    if not user:
        return jsonify({"erro": "usuário não existe"}), 401

    send_mail(user)
    return jsonify({"success": "Email enviado"}),200

@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    
    userdecode = Users.decode_token(token)['sub']
    
    user = Users.query.filter_by(id=userdecode).first()

    if token is None:
        return flash("Seu período para reset expirou, faça o pedido novamente", 'warning')
    if userdecode is None:
        return flash("Este usuário não existe em nossa base de dados", 'warning')

    form=ResetPasswordForm()
    if request.method == 'POST' and form.validate():
        hashed_password = generate_password_hash(form.password.data, method='sha256')
        user.password=hashed_password
        db.session.commit()
        return redirect(os.environ["REDIRECT_PASSWORD"])
        
    
    return render_template('change_password.html', title="Trocar senha",  form=form)




##########################################################################################

######PROTEGIDAS

@app.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    # Access the identity of the current user with get_jwt_identity
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200

@app.route("/transactions", methods=["POST"])
@jwt_required()
@cross_origin()
def new_transaction():
    user_id = get_jwt_identity()

    name = request.json["name"]
    type = request.json["type"]
    amount = request.json["amount"]
    price_purchased_at = request.json["price_purchased_at"]
    no_of_coins = float(request.json["no_of_coins"])

    if type == '1':

        try:    
            connection_object = connection_pool.get_connection()

            if connection_object.is_connected():
                cursor = connection_object.cursor()
                insert_statement = f"INSERT INTO transaction (name, type, amount, price_purchased_at, no_of_coins, user_id) VALUES ('{name}', {type}, {amount}, {price_purchased_at}, {no_of_coins}, '{user_id}')"
                cursor.execute(insert_statement)
                cursor.fetchall()
                connection_object.commit()

                return jsonify(request.json)

        except Error as e:
            print("Error while connecting to MySQL using Connection pool ", e)

        finally:
                if connection_object.is_connected():
                    cursor.close()
                    connection_object.close()
    
    if type == '2':
    
        try:
            connection_object = connection_pool.get_connection()

            if connection_object.is_connected():
                connection_object = connection_pool.get_connection()
                cursor = connection_object.cursor()
                weighted_statment=weighted_statment= f"SELECT name, type=1, sum(no_of_coins * price_purchased_at) / sum(no_of_coins) as price_average, SUM(no_of_coins) AS total_coins FROM transaction where user_id='{user_id}' GROUP BY name"
                cursor.execute(weighted_statment)
                rows = cursor.fetchall()
                for row in rows:
                    coin = row[0]
                    transaction_type = row[1]
                    transaction_amount = row[2]
                    transaction_coins = row[3]
            
                    price_purchased_at = transaction_amount
            
            cursor.close()
            connection_object.close()

            connection_object = connection_pool.get_connection()

            if connection_object.is_connected():
                cursor = connection_object.cursor()
                insert_sell_statement = f"INSERT INTO transaction (name, type, amount, price_purchased_at, no_of_coins, user_id) VALUES ('{name}', {type}, {amount}, {price_purchased_at}, {no_of_coins}, '{user_id}')"
                cursor.execute(insert_sell_statement)
                cursor.fetchall()
                connection_object.commit()
            
            return jsonify(request.json)
        
        except Error as e:
            print("Error while connecting to MySQL using Connection pool ", e)

        finally:
                if connection_object.is_connected():
                    cursor.close()
                    connection_object.close()


@app.route("/transactions")
@jwt_required()
@cross_origin()
def get_transactions():

    user_id = get_jwt_identity()

    try:    
        connection_object = connection_pool.get_connection()

        if connection_object.is_connected():
            cursor = connection_object.cursor()
            select_byId = f"SELECT * FROM transaction WHERE user_id = '{user_id}'"     
            cursor.execute(select_byId)
            rows = cursor.fetchall()
            return jsonify(
                [
                    format_db_row_to_transaction(row)
                    for row in rows
                ]
            )
    except Error as e:
        print("Error while connecting to MySQL using Connection pool ", e)

    finally:
            if connection_object.is_connected():
                cursor.close()
                connection_object.close()

@app.route("/get_rollups_by_coin")
@jwt_required()
@cross_origin()
def get_rollups_by_coin_byid():

    user_id = get_jwt_identity()

    try:
        portfolio = defaultdict(
            lambda: {
                "coins": 0,
                "total_cost": 0,
                "total_equity": 0,
                "live_price": 0,
                "variation24h":0,
                "symbol":"",
                "image":"",
                "average_p":0,
                "p_l":0,
                "p_l_p":0,
                "bitcoin_lp":0,
                "usd_cot":0,
                "brl_conv_total":0,
            }
        )

        conn = connection_pool.get_connection()
        cur = conn.cursor()
        select_statement = f"SELECT name, type, SUM(amount)/100 AS total_amount, SUM(no_of_coins) AS total_coins FROM transaction where user_id='{user_id}' GROUP BY name, type"
        cur.execute(select_statement)
        rows = cur.fetchall()
        for row in rows:
            coin = row[0]
            transaction_type = row[1]
            transaction_amount = row[2]
            transaction_coins = row[3]
            

            #compra
            if transaction_type == 1:
                portfolio[coin]['total_cost'] += transaction_amount
                portfolio[coin]['coins'] += transaction_coins
            else:
                #venda
                portfolio[coin]['total_cost'] -= transaction_amount
                portfolio[coin]['coins'] -= transaction_coins


        symbol_to_coin_id_map
        name_to_symbol_map
        

        rollup_response=[]

        for name in portfolio:
            response = requests.get(
                f"{LIVE_PRICE_URL}?ids={symbol_to_coin_id_map[name]}&vs_currencies=usd&include_24hr_change=true"
            ).json()
            response2 = requests.get(
                f"{LIVE_PRICE_URL}?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
            ).json()
            response3 = requests.get(USD_URL).json()
            live_price = response[symbol_to_coin_id_map[name]]['usd']
            variation24h = response[symbol_to_coin_id_map[name]]['usd_24h_change']
            symbol = name_to_symbol_map[name]
            image = name_to_image_map[name]
            bitcoin_lp = response2['bitcoin']['usd']
            usd_cot = response3["USDBRL"]["bid"]
            

            portfolio[name]['usd_cot'] = usd_cot
            portfolio[name]['bitcoin_lp'] = bitcoin_lp 
            portfolio[name]['image'] = image       
            portfolio[name]['symbol'] = symbol
            portfolio[name]['name'] = name
            portfolio[name]['live_price'] = live_price
            portfolio[name]['total_equity'] = float(
                float(portfolio[name]['coins']) * live_price
            )
            portfolio[name]['variation24h'] = variation24h
            portfolio[name]['average_p'] = float(portfolio[name]['total_cost'])/float(portfolio[name]['coins'])
            portfolio[name]['p_l'] = float(
                float(portfolio[name]['coins']) * live_price - portfolio[name]['total_cost'])
            portfolio[name]['p_l_p'] = float(portfolio[name]['p_l'] / portfolio[name]['total_cost']) * 100
            brl_conv_total = float(usd_cot) * portfolio[name]['total_equity']
            

            

            rollup_response.append({
                "name": name,
                "symbol":symbol.upper(),
                "image":image,
                "live_price": portfolio[name]['live_price'],
                "total_equity": portfolio[name]['total_equity'],
                "coins": portfolio[name]['coins'],
                "total_cost": portfolio[name]['total_cost'],
                "variation24h": portfolio[name]['variation24h'],
                "average_p": portfolio[name]['average_p'],
                "p_l": portfolio[name]['p_l'],
                "p_l_p": portfolio[name]['p_l_p'],
                "bitcoin_lp": bitcoin_lp,
                "usd_cot": usd_cot,
                "brl_conv_total": brl_conv_total,
                
            })

        return jsonify(rollup_response)

    except Error as e:
        print("Error while connecting to MySQL using Connection pool ", e)

    finally:
            if conn.is_connected():
                cur.close()
                conn.close()

@app.route("/transactions", methods=["DELETE"])
@jwt_required()
@cross_origin()
def delete_transaction_byid():
    user_id = get_jwt_identity()

    try:    
        connection_object = connection_pool.get_connection()
        if connection_object.is_connected():
            name = request.json["name"]

            cursor = connection_object.cursor()
            

            delete_statement = f"DELETE FROM transaction WHERE user_id='{user_id}' AND name = '{name}'"
            cursor.execute(delete_statement)
            cursor.fetchall()
            connection_object.commit()

            return jsonify({"excluído":"Sucesso"})
        if connection_object.is_connected():
            cursor.close()
            connection_object.close()

    except Error as e:
        print("Error while connecting to MySQL using Connection pool ", e)

    finally:
            if connection_object.is_connected():
                cursor.close()
                connection_object.close()

#######FINAL
#######################################
if __name__ == "__main__":
    app.run(debug=True)