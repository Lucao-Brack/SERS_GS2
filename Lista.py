import csv
import os
import sys
from dataclasses import dataclass
from datetime import date

PREM = {
    "tarifa": 1.00,            # R$/kWh com tributos (fallback; o CSV oficial + reajuste + tributos recalcula) -> use a da sua conta
    "reajuste_tarifa": 0.04,   # ao ano (est)
    "desconto": 0.1375,        # taxa de desconto ao ano = Selic (oficial BCB) - sobrescrito pelo CSV
    "horizonte": 10,           # anos: periodo de referencia comum
    "p_chuveiro_kw": 5.5,      # kW (est; ver etiqueta do chuveiro)
    "fe_rede": 0.0385,         # kgCO2/kWh (oficial; MCTI, media do SIN em 2023) - sobrescrito pelo CSV
    "fe_rede_alto": 0.1264,    # kgCO2/kWh (oficial; MCTI, 2021, ano seco) - sobrescrito pelo CSV
    "fe_ciclo_fv": 0.041,      # kgCO2eq/kWh gerado (pub; IPCC AR5 - verificar)
    "hsp": 4.6,                # kWh/m2.dia (est; conferir CRESESB)
    "pr": 0.80,                # desempenho do sistema FV (est)
    "painel_kwp": 0.55,        # kWp por painel (est)
    "custo_wp": 4.00,          # R$/Wp instalado (est; fontes: 2,45 a 4,20)
    "degradacao": 0.005,       # ao ano (est)
    "autoconsumo": 0.30,       # fracao da geracao usada na hora (est)
    "fio_b": 0.20,             # R$/kWh (est)
    "pct_fio_b": {2027: 0.75, 2028: 0.90},   # Lei 14.300; 2029+ assumido 1,00
    "disponibilidade": 50,     # kWh minimo faturavel (bifasico, pub)
    "inicio_fv": 2027,         # primeiro ano completo de operacao
    "inversor_ano": 12, "inversor_frac": 0.15, "manut_fv": 100, "vida_fv": 25,
    "st_fracao": 0.70, "st_custo": 5000, "st_manut": 100, "st_vida": 15,
    "banho_novo_min": 6, "led_antiga_w": 15, "led_nova_w": 9, "led_custo": 12,
    "standby_w": 8, "standby_h": 20, "regua_custo": 40, "efic_vida": 12,
    "gel_antiga": 60, "gel_nova": 30, "gel_custo": 3000, "gel_vida": 15,

  ARQ_OFICIAL = os.path.join(os.getcwd(), "dados_energia.csv")
REAJUSTE_2026_B1 = 0.0902   # est/conferir: reajuste residencial BT Enel SP de jul/2026 (ANEEL, via imprensa)
FATOR_TRIBUTOS = 1.265

def carregar_oficiais(caminho=ARQ_OFICIAL):
    """Le o CSV de dados oficiais. Cada linha: id, descricao, valor, unidade, orgao_fonte, documento, url, ..."""
    with open(caminho, encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f))
    for l in linhas:
        l["valor"] = float(l["valor"])
    return linhas

def aplicar_oficiais(prem, linhas):
    """Sobrepoe em PREM os valores que existem como dado oficial. Devolve os ids efetivamente usados."""
    v = {l["id"]: l["valor"] for l in linhas}
    usados = []
    if "tarifa_b1_enel_sp_2025_rs_kwh" in v:
        prem["tarifa"] = round(v["tarifa_b1_enel_sp_2025_rs_kwh"] * (1 + REAJUSTE_2026_B1) * FATOR_TRIBUTOS, 4)
        usados.append("tarifa_b1_enel_sp_2025_rs_kwh")
    for id_, chave in (("fe_sin_2023_tco2_mwh", "fe_rede"), ("fe_sin_2021_tco2_mwh", "fe_rede_alto"),
                       ("custo_disponibilidade_bifasico_kwh", "disponibilidade"), ("selic_aa", "desconto")):
        if id_ in v:
            prem[chave] = v[id_]
            usados.append(id_)
    pct = {int(k[-4:]): x for k, x in v.items() if k.startswith("fio_b_pct_")}
    if pct:
        prem["pct_fio_b"] = pct
        usados += [k for k in v if k.startswith("fio_b_pct_")]
    return usados

def mostrar_oficiais(linhas, usados):
    print("\nDADOS OFICIAIS LIDOS DO CSV (dados/dados_energia.csv)")
    for l in linhas:
        marca = "*" if l["id"] in usados else " "
        print(f" {marca} {l['id']:<48}{l['valor']:>10g} {l['unidade']:<12} {l['orgao_fonte']}")
    print("  (* = usado nos calculos desta resposta; os demais ficam disponiveis para o assistente consultar)")
    print(f"  Tarifa com tributos estimada: R$ {PREM['tarifa']:.2f}/kWh = oficial B1 Enel SP x (1 + reajuste 2026 de "
          f"{REAJUSTE_2026_B1:.2%}, conferir) x fator de tributos {FATOR_TRIBUTOS} (est, conferir na conta).")

ANOS_MAX = 25

@dataclass
class Residencia:
    consumo: float = 242.0        # kWh/mes (da conta de luz)
    pessoas: int = 4
    banho_min: float = 8.0        # minutos por pessoa por dia
    moradia: str = "casa"         # casa | apartamento
    telhado: bool = True
    geladeira_antiga: bool = True
    lampadas: int = 10 

def chuveiro_kwh(r, p=PREM):
    """E = P x t. Potencia (kW) x horas de banho no mes."""
    return p["p_chuveiro_kw"] * r.pessoas * r.banho_min / 60 * 30


def vazao_equivalente(p=PREM, t_fria=20, t_banho=38):
    """Checagem fisica: P = m.c.dT  ->  L/min que o chuveiro aquece (esperado 3 a 6)."""
    return p["p_chuveiro_kw"] / (4.186 * (t_banho - t_fria)) * 60


def kwh_eficiencia(r, p=PREM):
    banho = chuveiro_kwh(r, p) * (1 - p["banho_novo_min"] / r.banho_min) if r.banho_min > p["banho_novo_min"] else 0
    led = r.lampadas * (p["led_antiga_w"] - p["led_nova_w"]) / 1000 * 5 * 30
    standby = p["standby_w"] / 1000 * p["standby_h"] * 30
    return banho, led, standby


def dimensionar_fv(consumo, p=PREM):
    """Numero de paineis para cobrir (consumo - minimo faturavel)."""
    por_painel = p["hsp"] * 30.4 * p["pr"] * p["painel_kwp"]
    n = max(round(max(consumo - p["disponibilidade"], 0) / por_painel), 0)
    return n, n * por_painel, n * p["painel_kwp"] * 1000 * p["custo_wp"]


def conta_fv(consumo, geracao, pct, fio_b, tarifa, p=PREM):
    """Conta mensal com FV (Lei 14.300): autoconsumo nao paga Fio B; injetado compensado paga;
    nunca se fatura menos que o custo de disponibilidade."""
    autoc = min(p["autoconsumo"] * geracao, consumo)
    comp = min(geracao - autoc, max(consumo - autoc - p["disponibilidade"], 0))
    fat = max(consumo - autoc - comp, p["disponibilidade"])
    return fat * tarifa + comp * pct * fio_b

def avaliar(invest, economia_no_ano, kwh_evitados_mes, p=PREM, co2_extra=0.0):
    """economia_no_ano(ano) -> R$ liquidos no ano. Devolve metricas comuns a todas as alternativas."""
    acum, vpl, payback, fluxo = -invest, -invest, None, []
    for ano in range(1, ANOS_MAX + 1):
        e = economia_no_ano(ano)
        ant, acum = acum, acum + e
        vpl += e / (1 + p["desconto"]) ** ano
        if payback is None and acum >= 0:
            payback = ano - 1 + (-ant / e if e > 0 else 0)
        fluxo.append(acum)
    H = p["horizonte"]
    kwh_ano = kwh_evitados_mes * 12
    return {"invest": invest, "eco1": economia_no_ano(1), "payback": payback,
            "saldo10": fluxo[H - 1] if H <= ANOS_MAX else None,
            "vpl10": sum(economia_no_ano(a) / (1 + p["desconto"]) ** a for a in range(1, H + 1)) - invest,
            "fluxo": fluxo, "kwh_ano": kwh_ano,
            "co2": kwh_ano * p["fe_rede"] - co2_extra,
            "co2_alto": kwh_ano * p["fe_rede_alto"] - co2_extra}


def tarifa_ano(ano, p=PREM):
    return p["tarifa"] * (1 + p["reajuste_tarifa"]) ** (ano - 1)


def economia_simples(kwh_mes, vida, manut=0.0, p=PREM):
    return lambda ano: (kwh_mes * 12 * tarifa_ano(ano, p) - manut) if ano <= vida else 0.0

def comparar(r, p=PREM):
    res = {}
    banho, led, sb = kwh_eficiencia(r, p)
    k_ef = banho + led + sb
    res["Eficiencia basica"] = avaliar(r.lampadas * p["led_custo"] + p["regua_custo"],
                                       economia_simples(k_ef, p["efic_vida"], 0, p), k_ef, p)
    if r.geladeira_antiga:
        k = p["gel_antiga"] - p["gel_nova"]
        res["Geladeira Procel A"] = avaliar(p["gel_custo"], economia_simples(k, p["gel_vida"], 0, p), k, p)
    if r.moradia == "casa" and r.telhado:
        k = p["st_fracao"] * chuveiro_kwh(r, p)
        res["Aquecedor solar (renovavel)"] = avaliar(p["st_custo"], economia_simples(k, p["st_vida"], p["st_manut"], p), k, p)
    if r.telhado:
        n, ger0, inv = dimensionar_fv(r.consumo, p)
        if n > 0:
            def eco_fv(ano):
                if ano > p["vida_fv"]:
                    return 0.0
                t = tarifa_ano(ano, p)
                ger = ger0 * (1 - p["degradacao"]) ** (ano - 1)
                pct = p["pct_fio_b"].get(p["inicio_fv"] + ano - 1, 1.0)
                conta = conta_fv(r.consumo, ger, pct, p["fio_b"] * (1 + p["reajuste_tarifa"]) ** (ano - 1), t, p)
                manut = p["manut_fv"] + (p["inversor_frac"] * inv if ano == p["inversor_ano"] else 0)
                return (r.consumo * t - conta) * 12 - manut
            kwh_ev = r.consumo - conta_fv_kwh(r.consumo, ger0, p)
            res[f"Fotovoltaico ({n} paineis, renovavel)"] = avaliar(inv, eco_fv, kwh_ev, p, co2_extra=ger0 * 12 * p["fe_ciclo_fv"])
    return res


def conta_fv_kwh(consumo, geracao, p=PREM):
    """kWh faturados no mes com FV (mesma logica de conta_fv)."""
    autoc = min(p["autoconsumo"] * geracao, consumo)
    comp = min(geracao - autoc, max(consumo - autoc - p["disponibilidade"], 0))
    return max(consumo - autoc - comp, p["disponibilidade"])

def imprimir(r, res, p=PREM):
    sh = chuveiro_kwh(r, p)
    print(f"\n{r.moradia.capitalize()} | {r.pessoas} pessoas | {r.consumo:.0f} kWh/mes | tarifa R$ {p['tarifa']:.2f}/kWh")
    print(f"Chuveiro: {sh:.0f} kWh/mes ({100 * sh / r.consumo:.0f}% do consumo)  [vazao equivalente {vazao_equivalente(p):.1f} L/min]")
    if sh > 0.65 * r.consumo:
        print("ATENCAO: chuveiro > 65% do consumo; confira os dados informados.")
    print(f"\n{'Alternativa':<36}{'Invest.':>9}{'Eco.1o ano':>12}{'Retorno':>10}{'Saldo 10a':>11}{'CO2 liq*':>10}")
    for nome, m in res.items():
        pb = f"{m['payback']:.1f}a" if m["payback"] else ">25a"
        print(f"{nome:<36}{m['invest']:>9.0f}{m['eco1']:>12.0f}{pb:>10}{m['saldo10']:>11.0f}{m['co2']:>10.1f}")
    print("* kgCO2/ano com o fator medio do SIN em 2023 (MCTI, oficial); no FV ja desconta o ciclo de vida dos paineis.")
    for nome, m in res.items():
        if "Fotovoltaico" in nome:
            print(f"  FV: CO2 liquido ~{m['co2']:.0f} kg/ano (rede atual, quase toda renovavel) e ~{m['co2_alto']:.0f} kg/ano "
                  "se a rede estiver como em 2021 (MCTI). O ganho e financeiro, nao de carbono.")
    recomendar(r, res)
    print("\nLIMITACOES: estimativas, nao garantias; tarifa, impostos, clima e habitos mudam o resultado; "
          "sem financiamento; peca 3 orcamentos; FV depende de telhado e aprovacao da distribuidora.")
    print("FONTES OFICIAIS: ANEEL/MME (tarifa B1 Enel SP, Informativo Tarifario 1S/2026), MCTI (fator de emissao do SIN), "
          "Lei 14.300/2022 art. 27 (Fio B), Lei 15.235/2025 (Tarifa Social), BCB (Selic). "
          "Estimativas: custos de FV/aquecedor, habitos de uso, irradiacao (conferir CRESESB).")
  def recomendar(r, res):
    passos = ["Comece pela eficiencia: custo baixo e retorno rapido."]
    for nome, m in res.items():
        if "Fotovoltaico" in nome:
            if m["payback"] and m["payback"] <= 7 and m["saldo10"] > 0:
                passos.append("Se o imovel e seu e voce tem o valor para investir, o fotovoltaico tende a render mais.")
            else:
                passos.append("O fotovoltaico nao se mostrou vantajoso em 10 anos neste cenario.")
        if "Aquecedor" in nome:
            passos.append("Aquecedor solar: " + ("compensa neste caso." if m["vpl10"] > 0 else
                          "retorno lento; so vale com orcamento menor ou banho muito usado."))
        if "Geladeira" in nome and m["vpl10"] < 0:
            passos.append("Geladeira: troque so quando precisar substituir a atual.")
    print("\nRECOMENDACAO:")
    for i, t in enumerate(passos, 1):
        print(f"{i}. {t}")
    if r.moradia == "apartamento" or not r.telhado:
        print("* Sem telhado: pergunte a distribuidora/condominio sobre geracao compartilhada (Lei 14.300).")
    print("* Familia de baixa renda: a Tarifa Social da desconto de 100% no consumo ate 80 kWh/mes (Lei 15.235/2025); "
          "consulte a distribuidora. Nesse caso, a economia de cada kWh poupado pode ser menor.")

def sensibilidade(r, p=PREM):
    print("\nSENSIBILIDADE (retorno do fotovoltaico em anos)")
    for tarifa in (0.80, 0.90, 1.00, 1.10, 1.20):
        q = dict(p, tarifa=tarifa)
        for nome, m in comparar(r, q).items():
            if "Fotovoltaico" in nome:
                print(f"  tarifa R$ {tarifa:.2f}/kWh -> retorno {m['payback']:.1f} anos | saldo 10 anos R$ {m['saldo10']:.0f}")
    for custo in (2.5, 3.0, 4.0, 5.0):
        q = dict(p, custo_wp=custo)
        for nome, m in comparar(r, q).items():
            if "Fotovoltaico" in nome:
                print(f"  custo R$ {custo:.2f}/Wp     -> retorno {m['payback']:.1f} anos")

          def grafico(res, arquivo="saidas/grafico_demo.png"):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("Instale matplotlib para gerar o grafico (pip install matplotlib).")
        return
    os.makedirs(os.path.dirname(arquivo), exist_ok=True)
    plt.figure(figsize=(8, 4.5))
    for nome, m in res.items():
        plt.plot(range(0, 21), [-m["invest"]] + m["fluxo"][:20], label=nome)
    plt.axhline(0, color="gray", lw=0.8)
    plt.xlabel("Anos"); plt.ylabel("Saldo acumulado (R$)"); plt.legend(fontsize=8)
    plt.title("Saldo acumulado por alternativa (estimativa)")
    plt.tight_layout(); plt.savefig(arquivo, dpi=150); plt.close()
    print(f"Grafico salvo em {arquivo}")

def registrar_teste(arquivo="saidas/testes_usuarios.csv"):
    """Registra feedback SEM dados pessoais (so codigo do participante e notas)."""
    os.makedirs(os.path.dirname(arquivo), exist_ok=True)
    novo = not os.path.exists(arquivo)
    print("\nRegistro de teste com usuario (nao digite nome, endereco ou CPF)")
    cod = input("Codigo do participante (ex.: P1): ").strip() or "P?"
    perfil = input("Perfil (ex.: apto, 3 pessoas): ").strip()
    nota = input("Entendeu a resposta? (1-5): ").strip()
    est = input("Ficou claro que sao estimativas? (1-5): ").strip()
    coment = input("Comentario / o que ajustar: ").strip()
    with open(arquivo, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if novo:
            w.writerow(["data", "participante", "perfil", "entendeu_1a5", "estimativa_clara_1a5", "comentario"])
        w.writerow([date.today().isoformat(), cod, perfil, nota, est, coment])
    print("Registrado.")

def ler(texto, padrao, tipo=str):
    v = input(f"{texto} [{padrao}]: ").strip()
    try:
        return tipo(v) if v else padrao
    except ValueError:
        print("Valor invalido, usando o padrao.")
        return padrao

  def ler_residencia():
    r = Residencia()
    r.consumo = ler("Consumo na conta (kWh/mes)", r.consumo, float)
    r.pessoas = ler("Quantas pessoas moram", r.pessoas, int)
    r.banho_min = ler("Minutos de banho por pessoa", r.banho_min, float)
    r.moradia = "apartamento" if ler("Casa ou apartamento", "casa").lower().startswith("apart") else "casa"
    r.telhado = ler("Tem telhado livre? (sim/nao)", "sim").lower() in ("sim", "s")
    r.geladeira_antiga = ler("Geladeira com mais de 10 anos? (sim/nao)", "sim").lower() in ("sim", "s")
    r.lampadas = ler("Lampadas nao-LED", r.lampadas, int)
    t = ler("Tarifa da sua conta em R$/kWh (0 = usar estimativa)", 0.0, float)
    if t > 0:
        PREM["tarifa"] = t
    return r


def main():
    print("=== Assistente de Energia - Citizen Assist AI ===")
    try:
        linhas = carregar_oficiais()
        usados = aplicar_oficiais(PREM, linhas)
    except FileNotFoundError:
        linhas, usados = [], []
        print("Aviso: dados/dados_energia.csv nao encontrado; usando valores estimados de PREM.")
    if linhas:
        mostrar_oficiais(linhas, usados)
    if "--demo" in sys.argv:
        print("\n--- DEMONSTRACAO: familia de 4 pessoas em casa, 242 kWh/mes, 8 min de banho por pessoa ---")
        r = Residencia()
        res = comparar(r)
        imprimir(r, res)
        sensibilidade(r)
        return
    r = ler_residencia()
    res = comparar(r)
    imprimir(r, res)
    while True:
        op = input("\n[1] Sensibilidade  [2] Grafico  [3] Registrar teste com usuario  [4] Nova analise  [0] Sair: ").strip()
        if op == "1":
            sensibilidade(r)
        elif op == "2":
            grafico(res)
        elif op == "3":
            registrar_teste()
        elif op == "4":
            r = ler_residencia(); res = comparar(r); imprimir(r, res)
        elif op == "0":
            break


if __name__ == "__main__":
    main()
