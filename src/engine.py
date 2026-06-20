import pandas as pd
import numpy as np
import random
from typing import Dict, List, Tuple

# Configuração de bairros de referência em São Paulo e preços médios por m2
BAIRROS_REFERENCIA = {
    "Itaim Bibi": {"min_m2": 18000, "max_m2": 26000},
    "Pinheiros": {"min_m2": 14000, "max_m2": 20000},
    "Jardins": {"min_m2": 16000, "max_m2": 23000},
    "Moema": {"min_m2": 13000, "max_m2": 18000},
    "Perdizes": {"min_m2": 11000, "max_m2": 15000},
    "Vila Mariana": {"min_m2": 10000, "max_m2": 14000},
    "Tatuapé": {"min_m2": 8000, "max_m2": 11000},
    "Santana": {"min_m2": 7000, "max_m2": 9500}
}

TIPOLOGIAS = ["Apartamento", "Casa", "Cobertura"]

def gerar_dados_imoveis(n_imoveis: int = 150, seed: int = 42) -> pd.DataFrame:
    """
    Gera uma base de dados sintética realista de imóveis em São Paulo,
    incluindo alguns outliers subprecificados injetados intencionalmente.
    """
    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)

    dados = []
    
    # Gerando os imóveis normais
    for i in range(n_imoveis):
        imovel_id = f"SP-{1000 + i}"
        bairro = random.choice(list(BAIRROS_REFERENCIA.keys()))
        ref = BAIRROS_REFERENCIA[bairro]
        
        # Atributos físicos do imóvel
        tipo = random.choices(TIPOLOGIAS, weights=[0.75, 0.20, 0.05])[0]
        
        # Área m² depende da tipologia
        if tipo == "Apartamento":
            area = int(np.random.normal(75, 25))
            area = max(35, min(area, 220))
        elif tipo == "Cobertura":
            area = int(np.random.normal(180, 50))
            area = max(110, min(area, 400))
        else: # Casa
            area = int(np.random.normal(150, 60))
            area = max(80, min(area, 500))
            
        # Quartos e vagas baseados na área
        if area < 60:
            quartos = 1
            vagas = random.choices([0, 1], weights=[0.4, 0.6])[0]
        elif area < 110:
            quartos = random.choice([2, 3])
            vagas = random.choice([1, 2])
        else:
            quartos = random.choice([3, 4])
            vagas = random.choice([2, 3, 4])
            
        dias_mercado = random.randint(1, 120)
        
        # Preço por m² base da região com pequena variação
        preco_m2_base = np.random.uniform(ref["min_m2"], ref["max_m2"])
        
        # Ajuste de preço conforme tipologia e atributos
        fator_tipo = 1.25 if tipo == "Cobertura" else (0.95 if tipo == "Casa" else 1.0)
        fator_vagas = 1.0 + (vagas * 0.03)
        
        preco_m2_final = preco_m2_base * fator_tipo * fator_vagas
        preco_venda = int(preco_m2_final * area)
        
        dados.append({
            "id": imovel_id,
            "bairro": bairro,
            "tipo": tipo,
            "area_m2": area,
            "quartos": quartos,
            "vagas": vagas,
            "dias_mercado": dias_mercado,
            "preco_venda": preco_venda,
            "preco_m2": round(preco_venda / area, 2),
            "is_outlier": False
        })
        
    df = pd.DataFrame(dados)
    
    # Injetando Outliers Subprecificados (cerca de 8% da base)
    n_outliers = int(n_imoveis * 0.08)
    indices_outliers = np.random.choice(df.index, n_outliers, replace=False)
    
    for idx in indices_outliers:
        # Reduz o preço em 25% a 40% para simular a assimetria
        desconto = np.random.uniform(0.25, 0.40)
        preco_original = df.loc[idx, "preco_venda"]
        preco_com_desconto = int(preco_original * (1 - desconto))
        
        df.loc[idx, "preco_venda"] = preco_com_desconto
        df.loc[idx, "preco_m2"] = round(preco_com_desconto / df.loc[idx, "area_m2"], 2)
        df.loc[idx, "is_outlier"] = True
        
    return df

def calcular_metricas_bairro(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula as métricas de preço médio por m² e desvio padrão para cada bairro.
    Para evitar que outliers contaminem drasticamente a média do bairro,
    calculamos as métricas usando os imóveis não-outliers ou mediana robusta.
    """
    # Usamos mediana e estatísticas robustas ou excluímos temporariamente outliers
    df_base = df[~df["is_outlier"]] if "is_outlier" in df.columns else df
    
    metricas = df_base.groupby("bairro").agg(
        media_preco_m2=("preco_m2", "mean"),
        mediana_preco_m2=("preco_m2", "median"),
        std_preco_m2=("preco_m2", "std"),
        total_imoveis=("id", "count")
    ).reset_index()
    
    # Trata caso onde std seja NaN ou muito baixo por pouca amostragem
    metricas["std_preco_m2"] = metricas["std_preco_m2"].fillna(metricas["media_preco_m2"] * 0.1)
    
    return metricas

def identificar_outliers_subprecificados(df: pd.DataFrame, desvios_limiar: float = 1.3) -> pd.DataFrame:
    """
    Identifica imóveis cujos preços por m² estão significativamente abaixo
    da média da região. Adiciona colunas de desconto percentual, lucro estimado
    e ROI esperado caso o imóvel retorne ao valor de mercado médio.
    """
    metricas = calcular_metricas_bairro(df)
    
    # Merge das métricas de bairro com o DataFrame principal
    df_analisado = df.merge(metricas, on="bairro", how="left")
    
    # Condição 1: Preço por m² abaixo do limiar estatístico (média - X * desvio padrão)
    condicao_estatistica = df_analisado["preco_m2"] < (df_analisado["media_preco_m2"] - desvios_limiar * df_analisado["std_preco_m2"])
    
    # Condição 2: Pelo menos 20% abaixo da média do bairro (regra de segurança comercial)
    condicao_comercial = df_analisado["preco_m2"] < (df_analisado["media_preco_m2"] * 0.80)
    
    # O imóvel é considerado uma oportunidade se atender a qualquer uma das condições
    df_analisado["oportunidade_detectada"] = condicao_estatistica | condicao_comercial
    
    # Cálculos financeiros de ROI e Lucro
    # Preço justo de mercado estimado para aquela metragem
    df_analisado["preco_mercado_estimado"] = (df_analisado["media_preco_m2"] * df_analisado["area_m2"]).astype(int)
    df_analisado["lucro_estimado"] = df_analisado["preco_mercado_estimado"] - df_analisado["preco_venda"]
    
    # ROI estimado (Lucro Estimado / Preço de Aquisição)
    df_analisado["roi_estimado"] = round((df_analisado["lucro_estimado"] / df_analisado["preco_venda"]) * 100, 2)
    df_analisado["desconto_percentual"] = round(((df_analisado["preco_mercado_estimado"] - df_analisado["preco_venda"]) / df_analisado["preco_mercado_estimado"]) * 100, 2)
    
    # Limpa valores negativos para imóveis acima da média
    df_analisado.loc[df_analisado["lucro_estimado"] < 0, "lucro_estimado"] = 0
    df_analisado.loc[df_analisado["roi_estimado"] < 0, "roi_estimado"] = 0.0
    df_analisado.loc[df_analisado["desconto_percentual"] < 0, "desconto_percentual"] = 0.0
    
    return df_analisado
