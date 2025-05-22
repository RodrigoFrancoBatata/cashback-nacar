from flask import Flask, render_template, request, redirect
import json
from datetime import datetime

app = Flask(__name__)

# Carrega os dados do JSON
def carregar_dados():
    with open("clientes.json", "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_dados(dados):
    with open("clientes.json", "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

# Página inicial
@app.route("/")
def home():
    dados = carregar_dados()
    return render_template("index.html", clientes=dados["clientes"])

# Página de cliente
@app.route("/cliente/<int:id>")
def cliente(id):
    dados = carregar_dados()
    cliente = next((c for c in dados["clientes"] if c["id"] == id), None)
    return render_template("cliente.html", cliente=cliente, cpf=cliente["cpf"])

# Formulário de novo cliente
@app.route("/novo")
def novo_cliente():
    return render_template("novo.html")

# Processar novo cliente
@app.route("/cadastrar", methods=["POST"])
def cadastrar_cliente():
    nome = request.form["nome"]
    cpf = request.form["cpf"]
    telefone = request.form["telefone"]
    saldo = float(request.form["saldo"])

    dados = carregar_dados()
    novo_id = max([c["id"] for c in dados["clientes"]], default=0) + 1

    novo = {
        "id": novo_id,
        "nome": nome,
        "cpf": cpf,
        "telefone": telefone,
        "cashback": saldo,
        "historico": []
    }

    dados["clientes"].append(novo)
    salvar_dados(dados)
    return redirect("/")

# Adicionar cashback via formulário (com número da venda e valor da venda)
@app.route("/cashback/<cpf>", methods=["POST"])
def adicionar_cashback(cpf):
    numero_venda = request.form["venda"]
    valor_venda = float(request.form["venda_valor"])
    valor_cashback = round(valor_venda * 0.05, 2)

    dados = carregar_dados()
    for cliente in dados["clientes"]:
        if cliente["cpf"] == cpf:
            cliente["cashback"] += valor_cashback
            cliente.setdefault("historico", []).append({
                "tipo": "entrada",
                "valor": valor_cashback,
                "venda": numero_venda,
                "data": datetime.now().strftime("%d/%m/%Y %H:%M")
            })
            salvar_dados(dados)
            return redirect(f"/cliente/{cliente['id']}")

    return "Cliente não encontrado", 404

# Resgatar cashback
@app.route("/resgatar/<cpf>", methods=["POST"])
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
                    "data": datetime.now().strftime("%d/%m/%Y %H:%M")
                })
                salvar_dados(dados)
                return redirect(f"/cliente/{cliente['id']}")
            else:
                return "Saldo insuficiente para resgate", 400

    return "Cliente não encontrado", 404

from flask import Response
import csv
import io

@app.route("/exportar/<cpf>")
def exportar_csv(cpf):
    dados = carregar_dados()
    cliente = next((c for c in dados["clientes"] if c["cpf"] == cpf), None)
    if not cliente:
        return "Cliente não encontrado", 404

    historico = cliente.get("historico", [])

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Data", "Tipo", "Valor", "Número da Venda"])

    for item in historico:
        writer.writerow([
            item.get("data", ""),
            item.get("tipo", ""),
            f"{item.get('valor', 0):.2f}",
            item.get("venda", "-")
        ])

    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={cliente['nome'].replace(' ', '_')}_historico.csv"}
    )


if __name__ == "__main__":
    app.run(debug=True)




