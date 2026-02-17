"""
🎬 IPTV Bot Profissional v3.0 - Telethon Edition
Bot completo para gerenciamento de playlists IPTV via Telegram.

Todas as funcionalidades preservadas do original (telebot):
- Navegação por canais, filmes e séries com paginação
- Sistema de seleções e geração de M3U personalizados
- Download de conteúdo (apenas dono)
- Compartilhamento para grupos (apenas dono)
- Painel administrativo
- Rate limiting e cache inteligente
- Renomeação de categorias
- Limpeza automática de arquivos

Convertido para Telethon (asyncio) com melhorias de performance.
"""

import asyncio
import time
import os
import requests
import json
from urllib.parse import urlparse, parse_qs

from telethon import TelegramClient, events, Button
from config import BOT_TOKEN, API_ID, API_HASH, OWNER_ID, CLEANUP_INTERVAL

from backend import backend
from frontend import IPTVFrontend
from canais import CanalManager
from filmes import FilmeManager
from series import SerieManager
from comandos import ComandoManager
from download import DownloadManager

# ===== CLIENTE TELETHON =====
client = TelegramClient('iptv_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ===== INICIALIZAÇÃO DOS MANAGERS =====
frontend = IPTVFrontend(client)
comando_manager = ComandoManager(client, backend, frontend)
canal_manager = CanalManager(client, backend, frontend)
filme_manager = FilmeManager(client, backend, frontend)
serie_manager = SerieManager(client, backend, frontend)
download_manager = DownloadManager(client, backend)

# Dados dos usuários (config de playlist por chat_id)
user_data = {}


# ===== FUNÇÕES UTILITÁRIAS =====

def extract_playlist_info(url: str) -> dict:
    """Extrai informações da playlist IPTV a partir da URL"""
    try:
        parsed = urlparse(url)
        server = f"{parsed.scheme}://{parsed.netloc}"
        query_params = parse_qs(parsed.query)

        username = query_params.get('username', [None])[0]
        password = query_params.get('password', [None])[0]

        if username and password:
            return {
                'server': server,
                'username': username,
                'password': password,
                'api_url': f"{server}/player_api.php"
            }
        return None
    except Exception as e:
        print(f"Erro ao extrair info da playlist: {e}")
        return None


def test_connection(config: dict) -> bool:
    """Testa a conexão com o servidor IPTV"""
    try:
        params = {
            'username': config['username'],
            'password': config['password'],
            'action': 'get_account_info'
        }
        response = requests.get(config['api_url'], params=params, timeout=10)
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, dict) and ('user_info' in data or not data.get('error')):
                    return True
                return False
            except json.JSONDecodeError:
                return True
        return False
    except Exception:
        return False


# ===== HANDLER: /start =====
@client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    welcome_text = """🎬 **Bem-vindo ao IPTV Bot Profissional v3.0!** 📺

🚀 **O bot mais avançado para IPTV no Telegram!**

**✨ Recursos únicos:**
• 🛡️ Sistema anti-spam profissional
• 📄 Geração de arquivos M3U personalizados com categorias
• ⭐ Sistema de seleções individual e por categoria completa
• 📊 Informações detalhadas do servidor
• 🔄 Cache inteligente para performance
• 📱 Interface com paginação completa
• 💾 Download de filmes e episódios (apenas dono)
• 📤 Envio para grupos (apenas dono)
• 🏷️ Renomeação de categorias personalizadas

**🎯 Como usar:**
1️⃣ Envie a URL da sua playlist IPTV
2️⃣ Navegue pelos conteúdos com paginação
3️⃣ Selecione itens individuais ou categorias completas
4️⃣ Renomeie categorias conforme desejar
5️⃣ Gere arquivos M3U personalizados

**📝 Formato da URL:**
`http://servidor.com/get.php?username=user&password=pass`

**🔥 Pronto para uma experiência incrível?**
Envie sua URL de playlist para começar!"""

    await event.respond(welcome_text, parse_mode='md')


# ===== HANDLER: /admin =====
@client.on(events.NewMessage(pattern='/admin'))
async def admin_handler(event):
    if backend.is_owner(event.sender_id):
        buttons = comando_manager.create_admin_buttons()
        await event.respond("""👑 **PAINEL ADMINISTRATIVO**

Bem-vindo, Administrador!

**🎛️ Controles especiais disponíveis:**
• 📊 Estatísticas completas do sistema
• 👥 Gerenciamento de usuários
• 🗄️ Controle de cache
• 💾 Sistema de downloads
• 📋 Visualização de logs

**🔓 Permissões especiais ativas:**
• ✅ Downloads ilimitados
• ✅ Envio para grupos
• ✅ Sem rate limiting
• ✅ Acesso total ao sistema""", buttons=buttons, parse_mode='md')
    else:
        await event.respond("❌ Comando disponível apenas para o administrador.")


# ===== HANDLER: /stats =====
@client.on(events.NewMessage(pattern='/stats'))
async def stats_handler(event):
    stats = backend.get_stats()
    await event.respond(f"""📊 **Estatísticas do Bot**

👥 Usuários ativos: {stats['active_users']}
💾 Items no cache: {stats['cache_size']}
⭐ Seleções salvas: {stats['selections']}
🔄 Total de requisições: {stats['total_requests']}
⏱️ Uptime: {int(time.time() - stats['uptime'])}s

**🚀 Bot IPTV Profissional v3.0 (Telethon)**""", parse_mode='md')


# ===== HANDLER: MENSAGENS DE TEXTO (URLs e contexto) =====
@client.on(events.NewMessage(func=lambda e: e.is_private and not e.text.startswith('/')))
async def message_handler(event):
    chat_id = event.chat_id
    text = event.text.strip()

    # Verifica contexto de ação pendente
    if chat_id in backend.user_context:
        context = backend.user_context[chat_id]

        if context.get('action') == 'share':
            await comando_manager.process_group_share(event, context)
            del backend.user_context[chat_id]
            return

        elif context.get('action') == 'rename_category':
            category_name = text.strip()
            if category_name:
                category_type = context['category_type']
                category_id = context['category_id']
                config = context['config']

                added_count = backend.add_full_category(
                    chat_id, config, category_type, category_id, category_name
                )

                if added_count > 0:
                    await event.respond(
                        f"""✅ **Categoria adicionada com sucesso!**

🏷️ **Nome:** {category_name}
📊 **Tipo:** {category_type.title()}
📝 **Itens adicionados:** {added_count}

**🎉 Categoria completa salva para o arquivo M3U!**""",
                        parse_mode='md'
                    )
                else:
                    await event.respond(
                        "❌ **Erro ao adicionar categoria**\n\nNenhum item foi encontrado nesta categoria.",
                        parse_mode='md'
                    )
            else:
                await event.respond("❌ **Nome inválido**\n\nPor favor, envie um nome válido.", parse_mode='md')

            del backend.user_context[chat_id]
            return

    # Rate limiting
    if not backend.check_rate_limit(chat_id):
        await frontend.show_rate_limit_error(chat_id)
        return

    # Verifica URL
    if not text.startswith('http'):
        await event.respond("""❌ **URL inválida!**

Por favor, envie uma URL válida no formato:
`http://servidor.com/get.php?username=user&password=pass`

**Exemplo correto:**
`http://exemplo.com/get.php?username=meuuser&password=minhasenha`""", parse_mode='md')
        return

    # Mensagem de carregamento
    loading_msg = await event.respond(
        "⏳ **Analisando playlist...**\n\n🔍 Verificando servidor\n📡 Testando conexão\n⚡ Validando credenciais",
        parse_mode='md'
    )

    try:
        config = extract_playlist_info(text)

        if not config:
            await loading_msg.edit("""❌ **URL inválida!**

A URL deve conter `username` e `password`.

**Formato correto:**
`http://servidor.com/get.php?username=USER&password=PASS`""", parse_mode='md')
            return

        if not test_connection(config):
            await loading_msg.edit(f"""❌ **Falha na conexão!**

Não foi possível conectar com o servidor.

**Dados da conexão:**
🌐 **Servidor:** {config.get('server', 'N/A')}
👤 **Usuário:** {config.get('username', 'N/A')}

**Possíveis causas:**
• Servidor offline ou sobrecarregado
• Credenciais incorretas ou expiradas
• Problema de rede temporário

**💡 Sugestões:**
• Verifique se as credenciais estão corretas
• Tente novamente em alguns minutos""", parse_mode='md')
            return

        # Salva config
        user_data[chat_id] = config

        await loading_msg.edit("""✅ **Conexão estabelecida com sucesso!**

🎉 Playlist configurada e validada
🚀 Sistema pronto para uso
⚡ Cache otimizado ativado

**Preparando menu principal...**""", parse_mode='md')

        await asyncio.sleep(1.5)
        await loading_msg.delete()
        await frontend.show_main_menu(chat_id)

    except Exception as e:
        print(f"Error handling playlist URL: {e}")
        try:
            await loading_msg.edit("❌ **Erro interno**\n\nTente novamente em alguns segundos.", parse_mode='md')
        except:
            pass


# ===== HANDLER: CALLBACKS (BOTÕES INLINE) =====
@client.on(events.CallbackQuery)
async def callback_handler(event):
    chat_id = event.chat_id
    data = event.data.decode()

    try:
        # Rate limiting
        if not backend.check_rate_limit(chat_id):
            await event.answer("⚠️ Muitas solicitações! Aguarde alguns segundos.", alert=True)
            return

        message = await event.get_message()

        # ===== MENU PRINCIPAL =====
        if data == "nova_playlist":
            await message.edit("""🔄 **Nova Playlist**

📝 Envie a nova URL da playlist IPTV:

**Formato:**
`http://servidor.com/get.php?username=USER&password=PASS`

**💡 Dica:** Cole a URL completa com username e password.""", parse_mode='md')

        elif data == "menu_principal":
            await frontend.show_main_menu(chat_id, message)

        elif data == "server_info":
            if chat_id not in user_data:
                await event.answer("❌ Configure uma playlist primeiro!")
                return
            server_info = backend.get_server_info(user_data[chat_id])
            await frontend.show_server_info(chat_id, message, server_info)

        elif data == "menu_selections":
            selections = backend.get_user_selections(chat_id)
            await frontend.show_selections_menu(chat_id, message, selections)

        elif data == "generate_m3u":
            if chat_id not in user_data:
                await event.answer("❌ Configure uma playlist primeiro!")
                return

            selections = backend.get_user_selections(chat_id)
            total = len(selections.get('channels', [])) + len(selections.get('movies', [])) + len(selections.get('series', []))

            if total == 0:
                await event.answer("❌ Nenhum item selecionado!", alert=True)
                return

            filename = backend.generate_m3u_file(chat_id, user_data[chat_id])
            if filename:
                await client.send_file(
                    chat_id, filename,
                    caption=f"""📄 **Arquivo M3U Personalizado Gerado!**

✅ **Conteúdo incluído:**
• 📺 Canais: {len(selections.get('channels', []))}
• 🎬 Filmes: {len(selections.get('movies', []))}
• 📺 Séries: {len(selections.get('series', []))}
• 📊 **Total: {total} itens**

🏷️ **Categorias personalizadas mantidas**
🎯 **Pronto para usar em qualquer player IPTV**""",
                    parse_mode='md'
                )
                try:
                    os.remove(filename)
                except:
                    pass
                await event.answer("✅ Arquivo M3U enviado com sucesso!")
            else:
                await event.answer("❌ Erro ao gerar arquivo M3U")

        elif data == "clear_selections":
            if chat_id in backend.user_selections:
                backend.user_selections[chat_id] = {'channels': [], 'movies': [], 'series': []}
            await event.answer("🗑️ Todas as seleções foram removidas!")
            selections = backend.get_user_selections(chat_id)
            await frontend.show_selections_menu(chat_id, message, selections)

        # ===== MENUS DE CONTEÚDO =====
        elif data == "menu_canais":
            if chat_id not in user_data:
                await event.answer("❌ Configure uma playlist primeiro!")
                return
            await canal_manager.show_categories(chat_id, message, user_data[chat_id])

        elif data == "menu_filmes":
            if chat_id not in user_data:
                await event.answer("❌ Configure uma playlist primeiro!")
                return
            await filme_manager.show_categories(chat_id, message, user_data[chat_id])

        elif data == "menu_series":
            if chat_id not in user_data:
                await event.answer("❌ Configure uma playlist primeiro!")
                return
            await serie_manager.show_categories(chat_id, message, user_data[chat_id])

        # ===== DOWNLOADS =====
        elif data.startswith("download_"):
            await download_manager.handle_callback(event, user_data.get(chat_id))

        # ===== PAINEL ADMIN =====
        elif data == "admin_panel" and backend.is_owner(chat_id):
            buttons = comando_manager.create_admin_buttons()
            stats = backend.stats
            await message.edit(f"""👑 **PAINEL ADMINISTRATIVO**

**📊 Estatísticas:**
• Requisições: {stats['total_requests']}
• Cache hits: {stats['cache_hits']}
• Usuários ativos: {len(backend.user_selections)}

**🛠️ Controles disponíveis:**
• 📊 Estatísticas detalhadas
• 🗄️ Limpeza de cache""", buttons=buttons, parse_mode='md')

        elif data.startswith("admin_") and backend.is_owner(chat_id):
            if data == "admin_stats":
                stats = backend.get_stats()
                buttons = comando_manager.create_admin_buttons()
                await message.edit(f"""📊 **ESTATÍSTICAS DETALHADAS**

**📈 Uso do sistema:**
• Total de requisições: {stats['total_requests']}
• Cache hits: {stats['cache_hits']}
• Tamanho do cache: {stats['cache_size']} itens

**👥 Usuários:**
• Usuários ativos: {stats['active_users']}
• Seleções salvas: {stats['selections']}

**⚡ Sistema:**
• Uptime: {int(time.time() - stats['uptime'])}s""", buttons=buttons, parse_mode='md')

            elif data == "admin_clear_cache":
                cleared = backend.clear_cache()
                await event.answer(f"🗄️ Cache limpo! {cleared} itens removidos.")

        # ===== DOWNLOADS/SHARE DO DONO =====
        elif data.startswith(("canal_download_", "filme_download_", "serie_download_", "episode_download_")):
            if not backend.is_owner(chat_id):
                await event.answer("❌ Apenas o dono pode fazer downloads!", alert=True)
                return
            parts = data.split("_")
            await comando_manager.handle_download_request(event, parts[0], parts[2], user_data.get(chat_id))

        elif data.startswith(("canal_share_", "filme_share_", "serie_share_")):
            if not backend.is_owner(chat_id):
                await event.answer("❌ Apenas o dono pode enviar para grupos!", alert=True)
                return
            parts = data.split("_")
            await comando_manager.handle_share_request(event, parts[0], parts[2], user_data.get(chat_id))

        # ===== ADICIONAR CATEGORIA COMPLETA =====
        elif data.startswith("add_full_category_"):
            if chat_id not in user_data:
                await event.answer("❌ Configure uma playlist primeiro!")
                return

            parts = data.split("_")
            if len(parts) >= 4:
                category_type = parts[3]
                category_id = parts[4] if len(parts) > 4 else parts[3]

                await event.answer("📝 Envie o nome personalizado para esta categoria")

                await client.send_message(
                    chat_id,
                    f"""🏷️ **Renomear Categoria Completa**

**📁 Tipo:** {category_type.title()}
**🆔 ID:** {category_id}

**💡 Envie o nome que deseja usar para esta categoria no M3U:**

**Exemplos:**
• "Meus Canais de Esporte"
• "Filmes de Ação Favoritos"
• "Séries Netflix Premium"

📝 **Digite o nome personalizado:**""",
                    parse_mode='md'
                )

                backend.user_context[chat_id] = {
                    'action': 'rename_category',
                    'category_type': category_type,
                    'category_id': category_id,
                    'config': user_data[chat_id]
                }

        # ===== DELEGAÇÃO PARA MANAGERS =====
        elif data.startswith("canal_"):
            await canal_manager.handle_callback(event, user_data.get(chat_id))

        elif data.startswith("filme_"):
            await filme_manager.handle_callback(event, user_data.get(chat_id))

        elif data.startswith("serie_"):
            await serie_manager.handle_callback(event, user_data.get(chat_id))

        elif data in ("page_info", "empty"):
            await event.answer("ℹ️ Informação de página" if data == "page_info" else "")

        else:
            await event.answer("⚠️ Ação não reconhecida")

        # Responde callback para remover loading
        try:
            await event.answer()
        except:
            pass

    except Exception as e:
        print(f"Callback error: {e}")
        try:
            await event.answer("❌ Erro interno. Tente novamente.")
        except:
            pass


# ===== LIMPEZA AUTOMÁTICA =====
async def cleanup_worker():
    """Worker assíncrono para limpeza automática de arquivos"""
    while True:
        try:
            backend.clean_old_files()
            download_manager.cleanup_old_files()
        except Exception as e:
            print(f"Cleanup error: {e}")
        await asyncio.sleep(CLEANUP_INTERVAL)


# ===== MAIN =====
async def main():
    print("🚀 Bot IPTV Profissional v3.0 (Telethon) iniciado!")
    print("📡 Sistema anti-spam ativado")
    print("💾 Cache inteligente configurado")
    print("🧹 Limpeza automática de arquivos ativa")
    print("👑 Privilégios especiais para o dono configurados")
    print("🏷️ Sistema de categorias personalizáveis ativo")
    print("📱 Paginação completa implementada")
    print("💾 Sistema de downloads para filmes e séries ativo")
    print("⚡ Aceita múltiplos formatos de URL IPTV")
    print("🛡️ Sistema robusto de tratamento de erros ativo")
    print("Pressione Ctrl+C para parar")

    # Inicia limpeza em background
    asyncio.create_task(cleanup_worker())

    # Mantém o bot rodando
    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        client.loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\n👋 Bot finalizado com segurança!")
        print("🧹 Limpeza final executada")
        backend.clean_old_files()
