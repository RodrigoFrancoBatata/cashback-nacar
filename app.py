# ✅ app.py atualizado com clientes inativos
from flask import Flask, render_template, request, redirect, Response, flash
import json
from datetime import datetime, timedelta
import csv
import io

app = Flask(__name__)
app.secret_key = "segredo"

# Marcar clientes como inativos após 6 meses
def marcar_inativos(clientes):
    hoje = datetime.now()
    for c in clientes:
        historico = c.get("historico", [])
        if not historico:
            c["inativo"] = True
            continue
        ult_data = max([
            datetime.strptime(item["data"], "%d/%m/%Y %H:%M")
            for item in historico if "data" in item
        ], default=hoje)
        c["inativo"] = (hoje - ult_data) > timedelta(days=180)
    return clientes

def carregar_dados():
    with open("clientes.json", "r", encoding="utf-8") as f:
        dados = json.load(f)
    dados["clientes"] = marcar_inativos(dados["clientes"])
    return dados

def salvar_dados(dados):
    with open("clientes.json", "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

@app.route("/")
def home():
    dados = carregar_dados()
    clientes = dados["clientes"]

    total_cashback = sum(c.get("cashback", 0) for c in clientes)
    total_resgatado = sum(
        item["valor"]
        for c in clientes
        for item in c.get("historico", [])
        if item.get("tipo") == "resgate"
    )

    top_clientes = sorted(clientes, key=lambda c: c.get("cashback", 0), reverse=True)[:5]

    return render_template("index.html", clientes=clientes, total_cashback=total_cashback,
                           total_resgatado=total_resgatado, top_clientes=top_clientes)

@app.route("/cliente/<int:id>")
def cliente(id):
    dados = carregar_dados()
    cliente = next((c for c in dados["clientes"] if c["id"] == id), None)
    return render_template("cliente.html", cliente=cliente, cpf=cliente["cpf"])

@app.route("/novo")
def novo_cliente():
    return render_template("novo.html")

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
    flash("Cliente cadastrado com sucesso!", "sucesso")
    return redirect("/")

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
            flash("Cashback adicionado com sucesso!", "sucesso")
            return redirect(f"/cliente/{cliente['id']}")

    return "Cliente não encontrado", 404

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
                flash("Resgate realizado com sucesso!", "sucesso")
                return redirect(f"/cliente/{cliente['id']}")
            else:
                flash("Saldo insuficiente para resgate.", "erro")
                return redirect(f"/cliente/{cliente['id']}")

    return "Cliente não encontrado", 404

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

# Necessário para Render
app = app
