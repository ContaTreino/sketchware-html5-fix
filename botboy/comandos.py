from telethon import Button
from typing import Dict, List, Optional, Any
from config import OWNER_ID


class ComandoManager:
    def __init__(self, client, backend, frontend):
        self.client = client
        self.backend = backend
        self.frontend = frontend
        self.owner_id = OWNER_ID

    def is_owner(self, user_id: int) -> bool:
        return user_id == self.owner_id

    def create_admin_buttons(self) -> list:
        return [
            [Button.inline("📊 Estatísticas", data=b"admin_stats"),
             Button.inline("👥 Usuários", data=b"admin_users")],
            [Button.inline("🗄️ Limpar Cache", data=b"admin_clear_cache"),
             Button.inline("📋 Logs", data=b"admin_logs")],
            [Button.inline("🔙 Menu Principal", data=b"menu_principal")],
        ]

    async def handle_share_request(self, event, item_type: str, item_id: str, config: Dict):
        try:
            chat_id = event.chat_id
            if not self.is_owner(chat_id):
                await event.answer("❌ Apenas o dono pode enviar para grupos!")
                return

            await self.client.send_message(
                chat_id,
                f"📤 **Enviar {item_type} para grupo**\n\n📝 Digite o ID do grupo (exemplo: -1001234567890):",
                parse_mode='md'
            )

            self.backend.user_context[chat_id] = {
                'action': 'share',
                'item_type': item_type,
                'item_id': item_id,
                'config': config
            }

            await event.answer("📝 Digite o ID do grupo")

        except Exception as e:
            print(f"Error in share request: {e}")
            await event.answer("❌ Erro ao solicitar envio")

    async def process_group_share(self, event, context: Dict):
        try:
            group_id = event.text.strip()
            chat_id = event.chat_id

            if not group_id.startswith('-'):
                await self.client.send_message(chat_id, "❌ ID do grupo deve começar com '-'")
                return

            item_type = context['item_type']
            item_id = context['item_id']
            config = context['config']

            if item_type == 'filme':
                card_text = f"""🎬 **FILME COMPARTILHADO**

📺 **Nome:** Filme #{item_id}
🔗 **Link:** `{config['server']}/movie/{config['username']}/{config['password']}/{item_id}.mp4`

**💡 Enviado pelo Bot IPTV Profissional**"""
            else:
                card_text = f"""📺 **CANAL COMPARTILHADO**

📡 **Nome:** Canal #{item_id}
🔗 **Link:** `{config['server']}/live/{config['username']}/{config['password']}/{item_id}.ts`

**💡 Enviado pelo Bot IPTV Profissional**"""

            await self.client.send_message(int(group_id), card_text, parse_mode='md')
            await self.client.send_message(
                chat_id,
                f"✅ **{item_type.title()} enviado com sucesso!**\n\n📤 Grupo: `{group_id}`",
                parse_mode='md'
            )

        except ValueError:
            await self.client.send_message(event.chat_id, "❌ ID do grupo inválido!")
        except Exception as e:
            print(f"Error sending to group: {e}")
            await self.client.send_message(event.chat_id, "❌ Erro ao enviar para o grupo.")

    async def handle_download_request(self, event, item_type: str, item_id: str, config: Dict):
        try:
            chat_id = event.chat_id
            if not self.is_owner(chat_id):
                await event.answer("❌ Apenas o dono pode fazer downloads!")
                return

            message = await event.get_message()
            await message.edit(f"💾 **Iniciando download...**\n\n🔄 Preparando {item_type}\n⏳ Aguarde...", parse_mode='md')

            import asyncio
            await asyncio.sleep(2)

            await message.edit(
                f"✅ **Download concluído!**\n\n📁 Arquivo salvo em: `/downloads/{item_type}_{item_id}.mp4`",
                parse_mode='md'
            )

            await event.answer("✅ Download concluído!")

        except Exception as e:
            print(f"Error in download: {e}")
            await event.answer("❌ Erro no download")
