# SERS_GS2
CITIZEN ASSIST AI
# Citizen Assist AI – Módulo de Energia

**Disciplina:** Soluções em Energias Renováveis e Sustentáveis · Ciência da Computação (1CC)
**Projeto:** Global Solution 2026 – Citizen Assist AI

> Este README identifica a **contribuição da disciplina de Energias Renováveis e Sustentáveis** ao Citizen Assist AI. Todo o código desta contribuição está na pasta `energia/`. Se o repositório for compartilhado com outras disciplinas, as demais pastas pertencem a elas.

## Integrantes


| Lucas Barros | 571528 |
| Renan Eskildssen | 571097 |
| Murillo Boyadjian | 570774 |

---

## 1. Público e problema

**Público atendido:** moradores da Grande São Paulo (área da Enel SP) que usam o assistente e querem **reduzir a conta de luz**, sem precisar de conhecimento técnico.

**Necessidade energética:** reduzir o consumo e o custo de eletricidade de uma residência. O estudo dá atenção especial ao **chuveiro elétrico**, que costuma ser um dos maiores consumidores de uma casa.

**Como o assistente ajuda:** o usuário informa alguns dados simples (consumo da conta, pessoas, banho, tipo de moradia, telhado). O assistente compara alternativas, indica o que faz mais sentido **para aquela situação** e explica as limitações, em linguagem acessível.

## 2. Funcionalidades de energia

- Cálculo do consumo do chuveiro (energia = potência × tempo) e checagem física da vazão (P = m·c·ΔT).
- Comparação de alternativas para a **mesma residência e o mesmo período (10 anos)**:
  1. **Eficiência básica:** banho mais curto, lâmpadas LED e régua contra standby;
  2. **Aquecedor solar de água** (fonte renovável térmica);
  3. **Energia solar fotovoltaica on-grid** (fonte renovável elétrica), com as regras da Lei 14.300 (Fio B, custo de disponibilidade);
  4. **Troca de geladeira antiga** (opcional).
- Para cada alternativa: investimento, economia no 1º ano, retorno (payback), saldo e VPL em 10 anos, e CO₂ evitado.
- Análise de **sensibilidade** (tarifa e custo dos painéis).
- Recomendação em regras claras (ex.: apartamento sem telhado não recebe recomendação de painel ou aquecedor).
- Toda resposta traz **limitações, premissas e fontes**.

## 3. Estrutura do repositório

```
energia/
├── citizen_assist_energia.py     # aplicativo completo em um arquivo (lê o CSV; modo --demo)
├── calculos.py                   # motor de cálculo modular
├── assistente_energia.py         # ferramenta do assistente (tool), regras e prompt
├── mini_calculo.py               # versão curta das fórmulas, para explicação
├── demo_video.py                 # demonstração interativa curta
├── rodar_analise.py              # gera tabelas e gráficos em saidas/
├── dados/
│   ├── dados_energia.csv         # dados oficiais, com órgão, documento e link por linha
│   ├── premissas.json            # premissas estimadas (e valores de reserva), com origem
│   └── perfil_residencia.csv     # inventário de equipamentos do perfil-tipo (estimado)
├── base_conhecimento/            # documentos para o RAG (energia_01 a energia_06)
├── docs/
│   ├── analise_energetica.md     # contexto, cálculos, comparação, sensibilidade, limitações
│   ├── referencias.md            # fontes
│   ├── testes_usuarios.md        # protocolo e registro dos testes com usuários
│   └── integracao_assistente.md  # como ligar ao assistente
├── saidas/                       # tabelas CSV e gráficos gerados
└── testes/test_calculos.py       # 25 testes automatizados
```

## 4. Como executar

Requisitos: Python 3.10 ou superior. Só os gráficos precisam de `matplotlib`.

```bash
cd energia
pip install matplotlib                      # opcional (gráficos)

python citizen_assist_energia.py --demo     # demonstração automática com os dados do CSV
python citizen_assist_energia.py            # modo interativo (responde às perguntas)
python rodar_analise.py                     # gera as tabelas e gráficos em saidas/
python -m unittest discover -s testes -v    # roda os 25 testes
python assistente_energia.py --consumo 242 --pessoas 4 --moradia casa --telhado sim --geladeira-antiga sim --lampadas 10
```

> Mantenha o arquivo `dados/dados_energia.csv` dentro da pasta `dados/`. Se ele não for encontrado, o programa avisa e usa valores estimados.

### Perguntas feitas pelo assistente (modo interativo)

| Pergunta | Para que serve |
|---|---|
| Consumo na conta (kWh/mês) | Base de todo o cálculo |
| Quantas pessoas moram | Calcula o uso do chuveiro |
| Minutos de banho por pessoa | Calcula o uso do chuveiro |
| Casa ou apartamento | Define se cabem painéis e aquecedor |
| Tem telhado livre? | Define a viabilidade de painéis e aquecedor |
| Geladeira com mais de 10 anos? | Inclui ou não a troca de geladeira |
| Lâmpadas não-LED | Calcula a economia com LED |
| Tarifa da sua conta (opcional) | Deixa o resultado mais preciso |

## 5. Dados utilizados

**Dados oficiais** (arquivo `dados/dados_energia.csv`; o código lê este arquivo):

| Dado | Fonte |
|---|---|
| Tarifa B1 residencial Enel SP (R$ 0,72518/kWh, sem tributos) | ANEEL, via MME – Informativo Tarifário do Setor Elétrico, 1º sem. 2026 |
| Tarifa média residencial e bandeiras tarifárias | ANEEL, via MME |
| Tarifa Social (100% de desconto até 80 kWh/mês) | Lei 15.235/2025, via MME |
| Fator de emissão do SIN (2021: 0,1264; 2023: 0,0385 tCO₂/MWh) | MCTI |
| Fio B escalonado (60% em 2026, 75% em 2027, 90% em 2028) | Lei 14.300/2022, art. 27 |
| Custo de disponibilidade (50 kWh, bifásico) | ANEEL, REN 1.000/2021 |
| Selic (13,75% a.a.), usada como taxa de desconto | Banco Central do Brasil |

Cada linha do CSV tem uma coluna **verificação** que diz o que foi conferido e o que ainda deve ser conferido na fonte primária.

**Dados estimados** (identificados como tais em `premissas.json`): tarifa com tributos (R$ 1,00/kWh), reajuste futuro da tarifa (4% a.a.), hábitos de uso do perfil-tipo (4 pessoas, 8 min de banho, ~242 kWh/mês), custo dos painéis (R$ 4,00/Wp), custo do aquecedor solar (R$ 5.000), irradiação (4,6 kWh/m²·dia) e fração solar do aquecedor (70%).

**Unidades e período:** potência em W/kW, energia em kWh, base mensal; comparação em 10 anos.

## 6. Resultados e comparação (perfil-tipo, estimativas)

| Alternativa | Investimento | Economia no 1º ano | Retorno | Saldo em 10 anos |
|---|---|---|---|---|
| Eficiência básica | R$ 160 | R$ 430 | 0,4 ano | R$ 4.998 |
| Troca de geladeira | R$ 3.000 | R$ 360 | 7,3 anos | R$ 1.323 |
| Aquecedor solar (renovável) | R$ 5.000 | R$ 639 | 6,8 anos | R$ 2.876 |
| Fotovoltaico (renovável) | R$ 6.600 | R$ 1.883 | 3,4 anos | R$ 14.839 |

**Principais conclusões**
- Comece pela eficiência: custo baixo e retorno rápido.
- O fotovoltaico rende mais, mas exige imóvel próprio, telhado adequado e capital. O aquecedor solar tem retorno mais lento.
- A troca de geladeira só vale quando for substituir a atual.
- **Meio ambiente:** como a rede brasileira já é muito renovável, o carbono evitado é pequeno. No fotovoltaico, o saldo de CO₂ no ciclo de vida fica perto de zero (−5,5 kg/ano com o fator de 2023). O ganho é principalmente financeiro e de autonomia.
- A ordem das alternativas se manteve nas faixas testadas na sensibilidade, mas os prazos mudam bastante.

Detalhes, fórmulas, sensibilidade e justificativas: `docs/analise_energetica.md`.

## 7. Testes

- **Testes automatizados:** 25 testes cobrem física, conservação de energia na compensação, regras de recomendação, presença de ressalvas e fontes na resposta e leitura do CSV oficial.
- **Testes com usuários:** protocolo, perguntas e tabelas de registro em `docs/testes_usuarios.md`. *(Preencher com os testes reais do grupo: situações testadas, comentários recebidos e ajustes feitos, sem dados pessoais.)*

## 8. Limitações

- Todos os valores de economia, geração e custo são **estimativas, não garantias**.
- Tarifa, tributos, bandeiras, clima e hábitos mudam o resultado; use a tarifa da sua conta.
- Os custos de instalação são médias de mercado; peça pelo menos três orçamentos.
- Não inclui financiamento.
- O fotovoltaico depende de telhado, sombra e aprovação da distribuidora; a regra do Fio B a partir de 2029 depende da ANEEL.
- O perfil-tipo é estimado. Para famílias que recebem Tarifa Social, a economia de cada kWh pode ser menor.

## 9. Referências

Lista completa em `docs/referencias.md`. Principais:
- MME/SNEE. *Informativo Tarifário do Setor Elétrico – 1º semestre 2026* (dados da ANEEL).
- Lei nº 14.300/2022 (art. 27) e Lei nº 15.235/2025.
- MCTI. Fatores de emissão de CO₂ do Sistema Interligado Nacional.
- ANEEL. Resolução Normativa nº 1.000/2021.
- Fontes de custo de sistemas fotovoltaicos: Greener (2025), Cenário Energia (2026).
