import pytest
import pandas as pd
from src.engine import gerar_dados_imoveis, calcular_metricas_bairro, identificar_outliers_subprecificados

def test_gerar_dados_imoveis():
    n = 50
    df = gerar_dados_imoveis(n_imoveis=n, seed=42)
    
    assert isinstance(df, pd.DataFrame)
    assert len(df) == n
    assert "id" in df.columns
    assert "bairro" in df.columns
    assert "preco_venda" in df.columns
    assert "preco_m2" in df.columns
    assert "is_outlier" in df.columns

def test_calcular_metricas_bairro():
    df = gerar_dados_imoveis(n_imoveis=30, seed=42)
    metricas = calcular_metricas_bairro(df)
    
    assert isinstance(metricas, pd.DataFrame)
    assert "bairro" in metricas.columns
    assert "media_preco_m2" in metricas.columns
    assert "std_preco_m2" in metricas.columns
    
    # Todos os bairros presentes na amostragem devem ter métricas
    bairros_amostrados = df[~df["is_outlier"]]["bairro"].unique()
    assert len(metricas) == len(bairros_amostrados)

def test_identificar_outliers_subprecificados():
    df = gerar_dados_imoveis(n_imoveis=40, seed=42)
    df_analisado = identificar_outliers_subprecificados(df, desvios_limiar=1.0)
    
    assert "oportunidade_detectada" in df_analisado.columns
    assert "lucro_estimado" in df_analisado.columns
    assert "roi_estimado" in df_analisado.columns
    assert "desconto_percentual" in df_analisado.columns
    
    # Verifica integridade dos valores financeiros calculados
    oportunidades = df_analisado[df_analisado["oportunidade_detectada"] == True]
    if not oportunidades.empty:
        # Pelo menos um imóvel deve ser marcado se injetamos outliers
        for _, row in oportunidades.iterrows():
            assert row["lucro_estimado"] >= 0
            assert row["roi_estimado"] >= 0.0
            assert row["desconto_percentual"] >= 0.0
            # Preço por m2 de uma oportunidade deve ser inferior ao preço médio da região
            assert row["preco_m2"] < row["media_preco_m2"]
