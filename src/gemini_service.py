import os
import json
import logging
from typing import Dict, Any
import google.generativeai as genai
from dotenv import load_dotenv

# Configura logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carrega variáveis de ambiente
load_dotenv()

# Configura a API do Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key and api_key != "sua_chave_do_gemini_aqui":
    genai.configure(api_key=api_key)
    logger.info("Gemini API configurada com sucesso.")
else:
    logger.warning("GEMINI_API_KEY não encontrada ou é o valor padrão. O serviço utilizará análises mockadas.")

def analisar_oportunidade(imovel: Dict[str, Any], regiao: Dict[str, Any]) -> Dict[str, Any]:
    """
    Usa o Gemini API para gerar uma análise aprofundada de um imóvel identificado como outlier,
    avaliando score de oportunidade, riscos, justificativa e ROI.
    Se a API falhar ou não estiver configurada, gera uma resposta simulada estruturada.
    """
    prompt = f"""
    Você é um Analista Sênior de Investimentos Imobiliários especializado no mercado de São Paulo.
    Sua tarefa é analisar uma oportunidade de investimento em um imóvel que foi identificado como subprecificado (outlier) em relação à sua região.

    Dados do Imóvel:
    - ID do Imóvel: {imovel.get('id')}
    - Bairro: {imovel.get('bairro')}
    - Tipo: {imovel.get('tipo')}
    - Área Útil: {imovel.get('area_m2')} m²
    - Quartos: {imovel.get('quartos')}
    - Vagas de Garagem: {imovel.get('vagas')}
    - Dias no Mercado: {imovel.get('dias_mercado')}
    - Preço de Venda Atual: R$ {imovel.get('preco_venda'):,}
    - Preço por m² do Imóvel: R$ {imovel.get('preco_m2'):,.2f}

    Dados Comparativos da Região ({imovel.get('bairro')}):
    - Preço Médio por m² da Região: R$ {regiao.get('media_preco_m2'):,.2f}
    - Mediana do m² da Região: R$ {regiao.get('mediana_preco_m2'):,.2f}
    - Desvio Padrão do m²: R$ {regiao.get('std_preco_m2'):,.2f}
    - Lucro Bruto Estimado na Revenda (valor de mercado - preço atual): R$ {imovel.get('lucro_estimado'):,}
    - ROI Estimado para Retorno ao Preço Médio: {imovel.get('roi_estimado')}%
    - Desconto em Relação à Média do Bairro: {imovel.get('desconto_percentual')}%

    Gere uma análise de viabilidade detalhada em formato JSON. O JSON deve ter exatamente os seguintes campos:
    {{
        "score_oportunidade": <um número inteiro de 0 a 100 representando a atratividade do negócio>,
        "justificativa": "<uma justificativa detalhada e profissional em português brasileiro sobre o potencial de ganho financeiro e assimetria de valor, citando os dados fornecidos>",
        "analise_risco": "<uma descrição detalhada em português dos riscos específicos (por exemplo: dias no mercado altos indicando baixa liquidez, necessidade de reforma, custos cartorários, ou volatilidade do bairro)>",
        "principais_fatores": [
            "<fator 1 (ex: Alta assimetria de preço)>",
            "<fator 2 (ex: Liquidez do bairro ou tamanho adequado)>",
            "<fator 3 (ex: Necessidade de reforma ou custo de capital)>",
            "<fator 4 (ex: Risco de vacância ou liquidez da região)>"
        ]
    }}

    IMPORTANTE: Retorne APENAS o objeto JSON e nada mais. Não inclua blocos de código markdown ou texto explicativo extra.
    """

    # Verifica se a API está configurada para fazer a chamada real
    if api_key and api_key != "sua_chave_do_gemini_aqui":
        try:
            # Usando gemini-1.5-flash que é rápido e suporta retorno estruturado
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            # Parseia o JSON retornado pela API
            analise = json.loads(response.text.strip())
            logger.info(f"Análise Gemini gerada com sucesso para o imóvel {imovel.get('id')}.")
            return analise
            
        except Exception as e:
            logger.error(f"Erro ao chamar a API do Gemini: {e}. Usando análise de contingência.")
            # Fallback em caso de erro da API
            return gerar_analise_contingencia(imovel, regiao)
    else:
        # Fallback se não houver chave configurada
        return gerar_analise_contingencia(imovel, regiao)

def gerar_analise_contingencia(imovel: Dict[str, Any], regiao: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gera uma análise de fallback caso a chave da API do Gemini não esteja configurada ou falhe.
    Essa análise utiliza cálculos matemáticos da engine para formular um texto de justificativa coerente.
    """
    roi = imovel.get("roi_estimado", 0.0)
    desconto = imovel.get("desconto_percentual", 0.0)
    bairro = imovel.get("bairro")
    dias = imovel.get("dias_mercado", 30)
    lucro = imovel.get("lucro_estimado", 0)
    
    # Lógica de cálculo do Score baseada nas métricas financeiras reais
    score = int(min(95, 40 + (desconto * 1.2) - (dias * 0.15)))
    score = max(10, score)
    
    # Justificativa dinâmica baseada nos dados reais de assimetria
    justificativa = (
        f"O imóvel localizado em {bairro} apresenta uma assimetria severa de valor, "
        f"sendo listado com um desconto de {desconto}% em relação ao preço médio praticado no bairro. "
        f"Com um preço de m² de R$ {imovel.get('preco_m2'):,.2f} versus a média regional de R$ {regiao.get('media_preco_m2'):,.2f}, "
        f"o investidor possui uma margem de segurança robusta. "
        f"O lucro bruto estimado para revenda a preço de mercado é de R$ {lucro:,}, "
        f"representando um ROI potencial projetado de {roi}% sobre a aquisição."
    )
    
    # Análise de risco dinâmica
    if dias > 90:
        risco_liquidez = "O imóvel está há mais de 90 dias no mercado, sinalizando possível baixa liquidez ou problemas estruturais que exigem auditoria rigorosa antes da compra."
    elif dias > 60:
        risco_liquidez = "O tempo de exposição do anúncio (mais de 60 dias) sugere que a negociação pode ser estendida e a liquidez imediata é moderada."
    else:
        risco_liquidez = "O imóvel é novo no mercado, indicando alta liquidez, exigindo rápida tomada de decisão por parte do investidor antes que outros compradores identifiquem a assimetria."
        
    risco_bairro = ""
    if bairro in ["Itaim Bibi", "Pinheiros", "Jardins"]:
        risco_bairro = "A região é de altíssima renda e forte demanda, reduzindo o risco de vacância e flutuação de preço, mas o capital inicial requerido é alto."
    else:
        risco_bairro = "Bairro residencial consolidado, porém com sensibilidade de preço mais acentuada. Superestimar o preço de saída após reforma pode alongar o tempo de revenda."

    analise_risco = (
        f"{risco_liquidez} {risco_bairro} Adicionalmente, devem ser previstos custos com ITBI, registro (cerca de 4% do valor total) e potencial reforma, "
        f"que pode consumir de 5% a 15% do valor do imóvel, dependendo do estado atual de conservação."
    )
    
    fatores = [
        f"Desconto de {desconto}% sobre a média local do m².",
        f"Lucro de revenda projetado em R$ {lucro:,}.",
        f"Bairro {bairro} possui infraestrutura urbana completa.",
        f"Tempo de mercado de {dias} dias exige atenção na negociação."
    ]
    
    return {
        "score_oportunidade": score,
        "justificativa": justificativa,
        "analise_risco": analise_risco,
        "principais_fatores": fatores
    }
