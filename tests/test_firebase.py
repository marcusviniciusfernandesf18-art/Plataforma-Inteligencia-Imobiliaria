import pytest
import os
import json
from src.firebase_service import (
    salvar_regiao_e_metricas, 
    salvar_imovel_com_insight, 
    recuperar_regioes_e_imoveis, 
    recuperar_historico_precos,
    modo_offline,
    ARQUIVO_OFFLINE_DB
)

@pytest.fixture(autouse=True)
def clean_offline_db():
    """Garante um banco offline limpo antes e depois de cada teste."""
    if os.path.exists(ARQUIVO_OFFLINE_DB):
        try:
            os.remove(ARQUIVO_OFFLINE_DB)
        except Exception:
            pass
    yield
    if os.path.exists(ARQUIVO_OFFLINE_DB):
        try:
            os.remove(ARQUIVO_OFFLINE_DB)
        except Exception:
            pass

def test_salvar_e_recuperar_regiao_e_imovel():
    # Testa no modo offline (forçado ou de fallback padrão do ambiente de teste)
    bairro = "Pinheiros"
    metricas = {
        "media_preco_m2": 15000.0,
        "mediana_preco_m2": 14900.0,
        "std_preco_m2": 800.0,
        "total_imoveis": 15
    }
    
    # Salva as métricas da região
    salvar_regiao_e_metricas(bairro, metricas)
    
    imovel = {
        "id": "SP-9999",
        "tipo": "Apartamento",
        "area_m2": 80,
        "quartos": 2,
        "vagas": 1,
        "preco_venda": 960000,
        "preco_m2": 12000.0,
        "oportunidade_detectada": True,
        "preco_mercado_estimado": 1200000,
        "lucro_estimado": 240000,
        "roi_estimado": 25.0,
        "desconto_percentual": 20.0
    }
    
    insight = {
        "score_oportunidade": 88,
        "justificativa": "Excelente margem de segurança no m².",
        "analise_risco": "Risco de liquidez padrão da região.",
        "principais_fatores": ["Desconto real", "Ótima localização"]
    }
    
    # Salva o imóvel com o insight
    salvar_imovel_com_insight(bairro, imovel, insight)
    
    # Recupera todos os imóveis salvos
    lista_imoveis = recuperar_regioes_e_imoveis()
    
    assert len(lista_imoveis) >= 1
    imovel_recuperado = next((x for x in lista_imoveis if x["id"] == "SP-9999"), None)
    
    assert imovel_recuperado is not None
    assert imovel_recuperado["bairro"] == bairro
    assert imovel_recuperado["preco_venda"] == 960000
    assert imovel_recuperado["insight_ia"]["score_oportunidade"] == 88
    assert imovel_recuperado["insight_ia"]["justificativa"] == "Excelente margem de segurança no m²."

def test_recuperar_historico_precos():
    bairro = "Moema"
    imovel = {
        "id": "SP-8888",
        "tipo": "Casa",
        "area_m2": 120,
        "preco_venda": 1100000,
        "preco_m2": 9166.67,
        "oportunidade_detectada": True
    }
    
    # Salva o imóvel (cria o primeiro registro histórico)
    salvar_imovel_com_insight(bairro, imovel)
    
    # Altera o preço e salva novamente para criar um novo registro histórico
    imovel["preco_venda"] = 1050000
    imovel["preco_m2"] = 8750.0
    salvar_imovel_com_insight(bairro, imovel)
    
    # Recupera o histórico de preços
    historico = recuperar_historico_precos(bairro, "SP-8888")
    
    # Deve conter 2 registros de histórico devido aos dois salvamentos
    assert len(historico) == 2
    assert historico[0]["preco_venda"] == 1100000
    assert historico[1]["preco_venda"] == 1050000
