import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# Configura logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Variáveis globais para controle do Firestore
db_client = None
modo_offline = True
ARQUIVO_OFFLINE_DB = "db_offline.json"

def inicializar_firebase() -> bool:
    """
    Inicializa o Firebase Admin SDK usando credenciais fornecidas no arquivo .env.
    Se não for possível inicializar, ativa o modo offline com banco local em JSON.
    """
    global db_client, modo_offline
    
    project_id = os.getenv("FIREBASE_PROJECT_ID")
    client_email = os.getenv("FIREBASE_CLIENT_EMAIL")
    private_key = os.getenv("FIREBASE_PRIVATE_KEY")
    
    # Valida chaves
    if not (project_id and client_email and private_key) or \
       project_id == "seu_projeto_firebase_id" or \
       "sua_chave_privada_aqui" in private_key:
        logger.warning("Credenciais do Firebase incompletas ou padrão no .env. Ativando Modo Offline (Armazenamento Local JSON).")
        modo_offline = True
        return False
        
    try:
        # Prepara a chave privada substituindo quebras de linha escapadas por quebras reais
        formatted_private_key = private_key.replace("\\n", "\n")
        
        # Estrutura o certificado em formato de dicionário
        cred_dict = {
            "type": "service_account",
            "project_id": project_id,
            "private_key": formatted_private_key,
            "client_email": client_email,
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        
        # Inicializa o App do Firebase caso ainda não tenha sido inicializado
        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            
        db_client = firestore.client()
        modo_offline = False
        logger.info("Firebase Firestore inicializado com sucesso!")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao inicializar Firebase Admin SDK: {e}. Ativando Modo Offline.")
        modo_offline = True
        return False

# Executa inicialização ao carregar o módulo
inicializar_firebase()

# =====================================================================
# FUNÇÕES DE PERSISTÊNCIA OFFLINE (Fallback Local JSON)
# =====================================================================

def _ler_banco_offline() -> Dict[str, Any]:
    """Lê o arquivo local de persistência JSON."""
    if not os.path.exists(ARQUIVO_OFFLINE_DB):
        return {"regioes": {}}
    try:
        with open(ARQUIVO_OFFLINE_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Erro ao ler banco offline: {e}")
        return {"regioes": {}}

def _salvar_banco_offline(dados: Dict[str, Any]) -> None:
    """Grava as modificações no arquivo local de persistência JSON."""
    try:
        with open(ARQUIVO_OFFLINE_DB, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Erro ao salvar banco offline: {e}")

# =====================================================================
# FUNÇÕES PÚBLICAS DE NEGÓCIO (Funcionam tanto Online quanto Offline)
# =====================================================================

def salvar_regiao_e_metricas(bairro: str, metricas: Dict[str, Any]) -> None:
    """
    Salva ou atualiza os dados gerais e estatísticas da região no Firestore.
    Caminho Firestore: regioes/{bairro}
    """
    dados_regiao = {
        "bairro": bairro,
        "media_preco_m2": float(metricas.get("media_preco_m2", 0.0)),
        "mediana_preco_m2": float(metricas.get("mediana_preco_m2", 0.0)),
        "std_preco_m2": float(metricas.get("std_preco_m2", 0.0)),
        "total_imoveis": int(metricas.get("total_imoveis", 0)),
        "ultima_atualizacao": datetime.now().isoformat()
    }
    
    if not modo_offline and db_client is not None:
        try:
            db_client.collection("regioes").document(bairro).set(dados_regiao)
            logger.info(f"Métricas da região {bairro} salvas no Firestore.")
        except Exception as e:
            logger.error(f"Erro ao salvar região no Firestore: {e}")
    else:
        # Lógica offline
        db = _ler_banco_offline()
        if bairro not in db["regioes"]:
            db["regioes"][bairro] = {"metadata": {}, "imoveis": {}}
        db["regioes"][bairro]["metadata"] = dados_regiao
        _salvar_banco_offline(db)
        logger.info(f"Métricas da região {bairro} salvas localmente (Offline).")

def salvar_imovel_com_insight(bairro: str, imovel: Dict[str, Any], insight: Optional[Dict[str, Any]] = None) -> None:
    """
    Salva ou atualiza um imóvel e seus insights gerados no Firestore.
    Caminho Firestore: regioes/{bairro}/imoveis/{imovel_id}
    E grava no histórico de preços: regioes/{bairro}/imoveis/{imovel_id}/historico_precos/{timestamp}
    """
    imovel_id = imovel.get("id")
    if not imovel_id:
        return
        
    dados_imovel = {
        "id": imovel_id,
        "bairro": bairro,
        "tipo": imovel.get("tipo"),
        "area_m2": int(imovel.get("area_m2", 0)),
        "quartos": int(imovel.get("quartos", 0)),
        "vagas": int(imovel.get("vagas", 0)),
        "dias_mercado": int(imovel.get("dias_mercado", 0)),
        "preco_venda": int(imovel.get("preco_venda", 0)),
        "preco_m2": float(imovel.get("preco_m2", 0.0)),
        "oportunidade_detectada": bool(imovel.get("oportunidade_detectada", False)),
        "preco_mercado_estimado": int(imovel.get("preco_mercado_estimado", 0)),
        "lucro_estimado": int(imovel.get("lucro_estimado", 0)),
        "roi_estimado": float(imovel.get("roi_estimado", 0.0)),
        "desconto_percentual": float(imovel.get("desconto_percentual", 0.0)),
        "ultima_atualizacao": datetime.now().isoformat()
    }
    
    if insight:
        dados_imovel["insight_ia"] = {
            "score_oportunidade": int(insight.get("score_oportunidade", 0)),
            "justificativa": insight.get("justificativa"),
            "analise_risco": insight.get("analise_risco"),
            "principais_fatores": insight.get("principais_fatores", []),
            "data_geracao": datetime.now().isoformat()
        }
        
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    registro_historico = {
        "preco_venda": int(imovel.get("preco_venda", 0)),
        "preco_m2": float(imovel.get("preco_m2", 0.0)),
        "data": datetime.now().isoformat()
    }
    
    if not modo_offline and db_client is not None:
        try:
            # Salva o imóvel principal
            ref_imovel = db_client.collection("regioes").document(bairro).collection("imoveis").document(imovel_id)
            ref_imovel.set(dados_imovel, merge=True)
            
            # Grava no histórico de preços
            ref_imovel.collection("historico_precos").document(timestamp_str).set(registro_historico)
            logger.debug(f"Imóvel {imovel_id} e histórico persistidos no Firestore.")
        except Exception as e:
            logger.error(f"Erro ao salvar imóvel no Firestore: {e}")
    else:
        # Lógica offline
        db = _ler_banco_offline()
        if bairro not in db["regioes"]:
            db["regioes"][bairro] = {"metadata": {}, "imoveis": {}}
            
        if imovel_id not in db["regioes"][bairro]["imoveis"]:
            db["regioes"][bairro]["imoveis"][imovel_id] = {"historico_precos": {}}
            
        # Preserva histórico de preços anterior se houver
        historico_existente = db["regioes"][bairro]["imoveis"][imovel_id].get("historico_precos", {})
        historico_existente[timestamp_str] = registro_historico
        
        db["regioes"][bairro]["imoveis"][imovel_id] = dados_imovel
        db["regioes"][bairro]["imoveis"][imovel_id]["historico_precos"] = historico_existente
        
        _salvar_banco_offline(db)
        logger.debug(f"Imóvel {imovel_id} e histórico salvos localmente (Offline).")

def recuperar_regioes_e_imoveis() -> List[Dict[str, Any]]:
    """
    Recupera todas as regiões e os imóveis persistidos no banco.
    Retorna uma lista flat de dicionários contendo os dados dos imóveis e o bairro correspondente.
    """
    imoveis_recuperados = []
    
    if not modo_offline and db_client is not None:
        try:
            regioes_refs = db_client.collection("regioes").stream()
            for reg_doc in regioes_refs:
                bairro = reg_doc.id
                imoveis_refs = db_client.collection("regioes").document(bairro).collection("imoveis").stream()
                for imovel_doc in imoveis_refs:
                    dados = imovel_doc.to_dict()
                    imoveis_recuperados.append(dados)
            logger.info(f"Recuperados {len(imoveis_recuperados)} imóveis do Firestore.")
        except Exception as e:
            logger.error(f"Erro ao recuperar imóveis do Firestore: {e}. Tentando ler base offline.")
            # Se der erro de conexão com Firestore, tenta carregar offline
            imoveis_recuperados = _recuperar_imoveis_offline()
    else:
        imoveis_recuperados = _recuperar_imoveis_offline()
        
    return imoveis_recuperados

def _recuperar_imoveis_offline() -> List[Dict[str, Any]]:
    """Recupera imóveis salvos localmente no arquivo JSON offline."""
    imoveis_recuperados = []
    db = _ler_banco_offline()
    for bairro, dados_bairro in db.get("regioes", {}).items():
        for imovel_id, dados_imovel in dados_bairro.get("imoveis", {}).items():
            # Remove a chave de histórico de preços para retornar apenas dados estruturados planos
            dados_copia = dados_imovel.copy()
            if "historico_precos" in dados_copia:
                del dados_copia["historico_precos"]
            imoveis_recuperados.append(dados_copia)
    logger.info(f"Recuperados {len(imoveis_recuperados)} imóveis da base local offline.")
    return imoveis_recuperados

def recuperar_historico_precos(bairro: str, imovel_id: str) -> List[Dict[str, Any]]:
    """
    Recupera o histórico de preços de um determinado imóvel.
    Retorna uma lista ordenada cronologicamente de alterações de preço.
    """
    historico = []
    
    if not modo_offline and db_client is not None:
        try:
            docs = db_client.collection("regioes").document(bairro)\
                             .collection("imoveis").document(imovel_id)\
                             .collection("historico_precos").stream()
            for doc in docs:
                dados = doc.to_dict()
                dados["id_registro"] = doc.id
                historico.append(dados)
            # Ordena pelo timestamp
            historico.sort(key=lambda x: x.get("data", ""))
        except Exception as e:
            logger.error(f"Erro ao obter histórico de preços do Firestore: {e}")
    else:
        # Recupera local
        db = _ler_banco_offline()
        try:
            regiao_db = db.get("regioes", {}).get(bairro, {})
            imovel_db = regiao_db.get("imoveis", {}).get(imovel_id, {})
            historico_dict = imovel_db.get("historico_precos", {})
            for key, val in historico_dict.items():
                historico.append(val)
            historico.sort(key=lambda x: x.get("data", ""))
        except Exception as e:
            logger.error(f"Erro ao recuperar histórico local: {e}")
            
    return historico
