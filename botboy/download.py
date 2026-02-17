import os
import asyncio
import requests
import time
from telethon import Button
from config import DOWNLOAD_DIR, MAX_FILE_SIZE


class DownloadManager:
    def __init__(self, client, backend):
        self.client = client
        self.backend = backend
        self.download_dir = DOWNLOAD_DIR
        self.max_file_size = MAX_FILE_SIZE

        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

    def is_download_allowed(self, user_id):
        return self.backend.is_owner(user_id)

    def get_file_formats(self, config, stream_id, content_type='movie'):
        try:
            if content_type == 'movie':
                params = {
                    'username': config['username'],
                    'password': config['password'],
                    'action': 'get_movie_info',
                    'movie_id': stream_id
                }
            else:
                params = {
                    'username': config['username'],
                    'password': config['password'],
                    'action': 'get_episode_info',
                    'episode_id': stream_id
                }

            info = self.backend.make_api_request(config, params)

            if info and 'movie_data' in info:
                formats = []
                movie_data = info['movie_data']

                if movie_data.get('container_extension'):
                    formats.append({
                        'quality': 'Original',
                        'format': movie_data['container_extension'],
                        'size': 'Tamanho original'
                    })

                container = movie_data.get('container_extension', 'mp4')
                if container in ['mkv', 'mp4', 'avi']:
                    formats.extend([
                        {'quality': 'HD 720p', 'format': 'mp4', 'size': '~1.5GB'},
                        {'quality': 'Full HD 1080p', 'format': 'mp4', 'size': '~3GB'},
                        {'quality': 'SD 480p', 'format': 'mp4', 'size': '~800MB'}
                    ])

                return formats

            return [{'quality': 'Padrão', 'format': 'mp4', 'size': 'Tamanho variável'}]

        except Exception as e:
            print(f"Error getting file formats: {e}")
            return [{'quality': 'Padrão', 'format': 'mp4', 'size': 'Tamanho variável'}]

    async def show_download_options(self, chat_id, message, config, stream_id, content_type):
        try:
            if not self.is_download_allowed(chat_id):
                buttons = [[Button.inline("🔙 Voltar", data=f"{content_type}_play_{stream_id}".encode())]]
                await message.edit("❌ **Download restrito!**\n\nApenas o proprietário do bot pode fazer downloads.", buttons=buttons, parse_mode='md')
                return

            formats = self.get_file_formats(config, stream_id, content_type)

            buttons = []
            for i, fmt in enumerate(formats):
                btn_text = f"📥 {fmt['quality']} ({fmt['format'].upper()}) - {fmt['size']}"
                buttons.append([Button.inline(btn_text, data=f"download_start_{content_type}_{stream_id}_{i}".encode())])

            buttons.append([Button.inline("🔙 Voltar", data=f"{content_type}_play_{stream_id}".encode())])

            text = f"""💾 **OPÇÕES DE DOWNLOAD**

**📋 Escolha o formato:**
• Diferentes qualidades disponíveis
• Download direto para você

**⚠️ Importante:**
• Downloads podem demorar alguns minutos
• Apenas o proprietário pode baixar"""

            await message.edit(text, buttons=buttons, parse_mode='md')

        except Exception as e:
            print(f"Error showing download options: {e}")

    async def start_download(self, chat_id, message, config, stream_id, content_type, format_index):
        try:
            if not self.is_download_allowed(chat_id):
                await message.edit("❌ Acesso negado!")
                return

            formats = self.get_file_formats(config, stream_id, content_type)
            selected = formats[int(format_index)] if int(format_index) < len(formats) else formats[0]

            if content_type == 'movie':
                download_url = f"{config['server']}/movie/{config['username']}/{config['password']}/{stream_id}.{selected['format']}"
            else:
                download_url = f"{config['server']}/series/{config['username']}/{config['password']}/{stream_id}.{selected['format']}"

            filename = f"download_{stream_id}.{selected['format']}"
            filepath = os.path.join(self.download_dir, filename)

            await message.edit(f"💾 **INICIANDO DOWNLOAD**\n\n📁 **Formato:** {selected['quality']}\n⏳ **Progresso:** 0%\n\n**Aguarde...**", parse_mode='md')

            # Download real com progresso
            try:
                response = requests.get(download_url, stream=True, timeout=300)
                total_size = int(response.headers.get('content-length', 0))

                with open(filepath, 'wb') as f:
                    downloaded = 0
                    last_update = 0
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            progress = int((downloaded / total_size * 100)) if total_size > 0 else 0

                            if progress - last_update >= 15:
                                last_update = progress
                                bar = '▓' * (progress // 10) + '░' * (10 - progress // 10)
                                try:
                                    await message.edit(
                                        f"💾 **FAZENDO DOWNLOAD**\n\n📁 **Formato:** {selected['quality']}\n⏳ **Progresso:** {progress}%\n{bar}",
                                        parse_mode='md'
                                    )
                                except:
                                    pass

                # Envia o arquivo
                await message.edit("📤 **Enviando arquivo...**", parse_mode='md')
                await self.client.send_file(
                    chat_id, filepath,
                    caption=f"🎬 **Download concluído!**\n📁 Formato: {selected['quality']}",
                    parse_mode='md'
                )

                os.remove(filepath)
                await message.edit("✅ **Arquivo enviado com sucesso!**\n🗑️ Arquivo removido do servidor.", parse_mode='md')

            except Exception as dl_error:
                print(f"Download error: {dl_error}")
                if os.path.exists(filepath):
                    os.remove(filepath)
                await message.edit("❌ Erro durante o download. Tente novamente.")

        except Exception as e:
            print(f"Error starting download: {e}")
            await message.edit("❌ Erro ao iniciar download.")

    async def handle_callback(self, event, config):
        data = event.data.decode()
        chat_id = event.chat_id
        message = await event.get_message()

        try:
            if data.startswith("download_options_"):
                parts = data.split("_")
                content_type = parts[2]
                stream_id = parts[3] if len(parts) > 3 else '0'
                await self.show_download_options(chat_id, message, config, stream_id, content_type)

            elif data.startswith("download_start_"):
                parts = data.split("_")
                content_type = parts[2]
                stream_id = parts[3]
                format_index = parts[4]
                await self.start_download(chat_id, message, config, stream_id, content_type, format_index)

        except Exception as e:
            print(f"Error in download callback: {e}")
            await event.answer("❌ Erro ao processar download")

    def cleanup_old_files(self):
        try:
            if not os.path.exists(self.download_dir):
                return
            current_time = time.time()
            for filename in os.listdir(self.download_dir):
                filepath = os.path.join(self.download_dir, filename)
                if os.path.isfile(filepath) and (current_time - os.path.getctime(filepath)) > 3600:
                    os.remove(filepath)
                    print(f"Removed old download file: {filename}")
        except Exception as e:
            print(f"Error cleaning up downloads: {e}")
