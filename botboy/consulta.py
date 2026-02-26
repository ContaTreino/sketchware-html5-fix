# ══════════════════════════════════════════════
# 🔍  CONSULTA CPF — INFO BOT PRO V4.0
# 👨‍💻 Créditos: Edivaldo Silva @Edkd1
# ══════════════════════════════════════════════

import re
import json
import requests
import ssl
import logging
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# ── SSL Config ──
try:
    requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS = (
        "TLS_AES_128_GCM_SHA256:TLS_CHACHA20_POLY1305_SHA256:TLS_AES_256_GCM_SHA384:"
        "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256:TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256:"
        "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256:TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256:"
        "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384:TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384:"
        "ECDHE:!COMP"
    )
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    logging.captureWarnings(True)
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass

# ── Configuração da API ──
API_CONSULTA_URL = "https://searchapi.dnnl.live/consulta"
API_CONSULTA_TOKEN = "4150"


def extrair_cpf(texto: str) -> str:
    """Extrai CPF de uma mensagem — com ou sem pontuação.
    Aceita: 123.456.789-00, 123456789-00, 12345678900, etc."""
    # 1) Tenta formato com pontuação: 000.000.000-00
    match = re.search(r'(\d{3}[.\s]?\d{3}[.\s]?\d{3}[-.\s]?\d{2})', texto)
    if match:
        return re.sub(r'[.\-/\s]', '', match.group(1))
    # 2) Tenta 11 dígitos seguidos
    match = re.search(r'(\d{11})', texto)
    if match:
        return match.group(1)
    return ""


def validar_cpf(cpf: str) -> bool:
    """Valida se o CPF tem 11 dígitos numéricos."""
    cpf_limpo = re.sub(r'[.\-/\s]', '', cpf)
    return cpf_limpo.isdigit() and len(cpf_limpo) == 11


def limpar_cpf(cpf: str) -> str:
    """Remove formatação do CPF."""
    return re.sub(r'[.\-/\s]', '', cpf)


def consultar_cpf(cpf: str) -> str:
    """Consulta CPF na API e retorna texto formatado profissional."""
    params = {
        "token_api": API_CONSULTA_TOKEN,
        "cpf": cpf
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (educational script)",
        "Accept": "application/json"
    }

    try:
        response = requests.get(
            API_CONSULTA_URL, params=params,
            headers=headers, timeout=10, verify=False
        )
    except requests.exceptions.RequestException as e:
        return f"❌ **Erro de conexão com a API**\n`{e}`"

    try:
        data = response.json()
    except json.JSONDecodeError:
        return "⚠️ Resposta da API não está em JSON."

    if response.status_code != 200:
        mensagem = data.get("mensagem", "Erro desconhecido da API")
        return f"❌ **Erro:** {mensagem}"

    if "dados" not in data or not data["dados"]:
        return "❌ Nenhum registro encontrado para este CPF."

    registro = data["dados"][0]

    def s(v):
        return str(v) if v else "Não informado"

    return f"""╔══════════════════════════╗
║  📄 **CONSULTA CPF**       ║
╚══════════════════════════╝

👤 **Nome:** `{s(registro.get('NOME'))}`
🔢 **CPF:** `{s(registro.get('CPF'))}`
📅 **Nascimento:** `{s(registro.get('NASC'))}`
⚧ **Sexo:** `{s(registro.get('SEXO'))}`

👩 **Mãe:** `{s(registro.get('NOME_MAE'))}`
👨 **Pai:** `{s(registro.get('NOME_PAI'))}`

🪪 **RG:** `{s(registro.get('RG'))}`
🏛️ **Órgão Emissor:** `{s(registro.get('ORGAO_EMISSOR'))}`
📍 **UF Emissão:** `{s(registro.get('UF_EMISSAO'))}`

🗳️ **Título Eleitor:** `{s(registro.get('TITULO_ELEITOR'))}`
💰 **Renda:** `{s(registro.get('RENDA'))}`
📱 **SO:** `{s(registro.get('SO'))}`

━━━━━━━━━━━━━━━━━━━━━
_👨‍💻 @Edkd1 | Info Bot Pro v4.0_"""
