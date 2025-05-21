from flask import Flask, render_template, request, redirect, session, url_for
import json

app = Flask(__name__)
app.secret_key = "chave-secreta-nacar"  # Troque por uma segura depois

# Usuário e senha fixos por enquanto
USUARIO = "admin"
SENHA = "1234"

def carregar_dados():
    with open("clientes.json", "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_dados(dados):
    with open("clientes.json", "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["usuario"] == USUARIO and request.form["senha"] == SENHA:
            session["logado"] = True
            return redirect("/")
        else:
            return "Credenciais inválidas", 403
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

def login_requerido(func):
    def wrapper(*args, **kwargs):
        if not session.get("logado"):
            return redirect("/login")
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

@app.route("/")
@login_requerido
def home():
    dados = carregar_dados()
    return render_template("index.html", clientes=dados["clientes"])

@app.route("/cliente/<int:id>")
@login_requerido
def cliente(id):
    dados = carregar_dados()
    cliente = next((c for c in dados["clientes"] if c["id"] == id), None)
    return render_template("cliente.html", cliente=cliente, cpf=cliente["cpf"])

@app.route("/novo")
@login_requerido
def novo_cliente():
    return render_template("novo.html")

@app.route("/cadastrar", methods=["POST"])
@login_requerido
def cadastrar_cliente():
    nome = request.form["nome"]
    cpf = request.form["cpf"]
    saldo = float(request.form["saldo"])

    dados = carregar_dados()
    novo_id = max([c["id"] for c in dados["clientes"]], default=0) + 1

    novo = {
        "id": novo_id,
        "nome": nome,
        "cpf": cpf,
        "cashback": saldo,
        "historico": []
    }

    dados["clientes"].append(novo)
    salvar_dados(dados)
    return redirect("/")

@app.route("/cashback/<cpf>", methods=["POST"])
@login_requerido
def adicionar_cashback(cpf):
    valor = float(request.form["valor"])
    numero_venda = request.form["venda"]

    dados = carregar_dados()
    for cliente in dados["clientes"]:
        if cliente["cpf"] == cpf:
            cliente["cashback"] += valor
            cliente.setdefault("historico", []).append({
                "tipo": "entrada",
                "valor": valor,
                "venda": numero_venda,
                "data": __import__("datetime").datetime.now().strftime("%d/%m/%Y %H:%M")
            })
            salvar_dados(dados)
            return redirect(f"/cliente/{cliente['id']}")
    return "Cliente não encontrado", 404

@app.route("/resgatar/<cpf>", methods=["POST"])
@login_requerido
def resgatar_cashback(cpf):
    valor_resgate = float(request.form["resgate"])
    dados = carregar_dados()
    for cliente in dados["clientes"]:
        if cliente["cpf"] == cpf:
            if cliente["cashback"] >= valor_resgate:
                cliente["cashback"] -= valor_resgate
                cliente.setdefault("historico", []).append({
                    "tipo": "resgate",
                    "valor": valor_resgate,
                    "data": __import__("datetime").datetime.now().strftime("%d/%m/%Y %H:%M")
                })
                salvar_dados(dados)
                return redirect(f"/cliente/{cliente['id']}")
            else:
                return "Saldo insuficiente para resgate", 400
    return "Cliente não encontrado", 404

if __name__ == "__main__":
    app.run(debug=True)


