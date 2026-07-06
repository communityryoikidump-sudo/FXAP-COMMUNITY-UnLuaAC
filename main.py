import os
import asyncio
import google.generativeai as genai
from pathlib import Path
import time
from datetime import datetime
import sys

class Colors:
    PURPLE    = '\x1b[95m'
    CYAN      = '\x1b[96m'
    DARK_CYAN = '\x1b[36m'
    BLUE      = '\x1b[94m'
    GREEN     = '\x1b[92m'
    YELLOW    = '\x1b[93m'
    RED       = '\x1b[91m'
    BOLD      = '\x1b[1m'
    UNDERLINE = '\x1b[4m'
    END       = '\x1b[0m'


def print_banner():
    os.system('cls' if os.name == 'nt' else 'clear')
    banner = f"""
{Colors.PURPLE}{Colors.BOLD}
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║      ███████╗██╗  ██╗ █████╗ ██████╗                     ║
║      ██╔════╝╚██╗██╔╝██╔══██╗██╔══██╗                    ║
║      █████╗   ╚███╔╝ ███████║██████╔╝                    ║
║      ██╔══╝   ██╔██╗ ██╔══██║██╔═══╝                     ║
║      ██║     ██╔╝ ██╗██║  ██║██║                         ║
║      ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝                         ║
║                                                           ║
║              {Colors.CYAN}L I M P A D O R   L U A{Colors.PURPLE}                    ║
║         {Colors.CYAN}discord.gg/RkfQN5g3V{Colors.PURPLE}                            ║
╚═══════════════════════════════════════════════════════════╝
{Colors.END}
"""
    print(banner)
    print(f"{Colors.DARK_CYAN}{'=' * 65}{Colors.END}")


def print_header(text):
    padding = 4
    width = len(text) + padding * 2
    top    = '╔' + '═' * width + '╗'
    middle = '║' + ' ' * padding + text + ' ' * padding + '║'
    bottom = '╚' + '═' * width + '╝'
    print(f"\n{Colors.BLUE}{Colors.BOLD}{top}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}{middle}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}{bottom}{Colors.END}")


def print_status(message, status='info'):
    timestamp = datetime.now().strftime('%H:%M:%S')
    if status == 'success':
        symbol = f"{Colors.GREEN}✓{Colors.END}"
    elif status == 'error':
        symbol = f"{Colors.RED}✗{Colors.END}"
    elif status == 'warning':
        symbol = f"{Colors.YELLOW}[AVISO]{Colors.END}"
    elif status == 'working':
        symbol = f"{Colors.CYAN}[..]{Colors.END}"
    else:
        symbol = f"{Colors.BLUE}[INFO]{Colors.END}"
    print(f"{Colors.DARK_CYAN}[{timestamp}]{Colors.END} {symbol} {message}")


def print_progress_bar(iteration, total, prefix='', suffix='', length=50, fill='█'):
    percent      = '{0:.1f}'.format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar          = fill * filled_length + '-' * (length - filled_length)
    progress_bar = f"{Colors.PURPLE}{bar}{Colors.END}"
    print(f'\r{prefix} |{progress_bar}| {percent}% {suffix}', end='\r')
    if iteration == total:
        print()


def get_api_key():
    print_header('CONFIGURAÇÃO DA API')
    print(f"\n{Colors.YELLOW}⚠  Você precisa de uma chave de API do Google Gemini para usar o Limpador.{Colors.END}")
    print(f"{Colors.CYAN}• Obtenha uma em: https://aistudio.google.com/app/apikey{Colors.END}")
    print(f"{Colors.CYAN}• Sua chave não será salva e será usada apenas nesta sessão{Colors.END}\n")
    while True:
        api_key = input(f"{Colors.BOLD}Digite sua chave da API Gemini:{Colors.END} ").strip()
        if api_key:
            print_status('Chave da API aceita!', 'success')
            return api_key
        print_status('Por favor, insira uma chave de API válida', 'error')


def build_prompt(code: str) -> str:
    return f"""Você é um especialista em desofuscação de código Lua para FiveM/GTA RP.

O código abaixo foi gerado por um compilador/ofuscador Lua que converte variáveis locais para nomes genéricos como L0_1, L1_1, L2_1, A0_2, A1_2, etc. Sua tarefa é reverter isso para código legível e limpo.

REGRAS OBRIGATÓRIAS:
1. Analise o contexto e uso de cada variável (L0_1, L1_1, etc.) e renomeie para nomes descritivos em inglês (ex: playerCoords, vehicleId, isOnDuty, callback, etc.)
2. Renomeie parâmetros de função (A0_2, A1_2) para nomes descritivos baseados no que recebem
3. Simplifique atribuições múltiplas desnecessárias (ex: L1_2 = func; L2_2 = arg; L1_2(L2_2) vira func(arg))
4. Remova variáveis intermediárias desnecessárias que só servem de alias
5. Mantenha a lógica, eventos, callbacks e funcionalidade 100% idênticos ao original
6. Use indentação de 4 espaços
7. Mantenha todos os nomes de eventos, NUI callbacks e server callbacks EXATAMENTE iguais
8. Retorne APENAS o código Lua limpo, sem explicações, sem markdown, sem ```

Código para desofuscar e limpar:
{code}"""


MODELS = [
    'gemini-2.5-flash',
    'gemini-2.0-flash',
    'gemini-2.0-flash-lite',
    'gemini-exp-1206',
    'gemini-2.0-flash-001',
]

INPUT_DIR  = 'Input'
OUTPUT_DIR = 'Output'

current_model_index = 0


def get_next_model():
    """Retorna o próximo modelo disponível na lista."""
    global current_model_index
    current_model_index += 1
    if current_model_index < len(MODELS):
        return genai.GenerativeModel(MODELS[current_model_index])
    return None


import re as _re

def _extract_retry_delay(error_msg: str) -> int:
    match = _re.search(r'retry_delay\s*\{\s*seconds:\s*(\d+)', str(error_msg))
    if match:
        return int(match.group(1)) + 1
    return 5


def clean_lua_code(model_holder: list, code: str, filename: str) -> str:
    """Manda o código Lua completo pro Gemini e retorna limpo. Troca de modelo se atingir rate limit."""
    prompt = f"""You are an expert Lua programmer.
Task: Clean, deobfuscate, and refactor the code below.
1. Rename obfuscated variables (L0_1, L1_1, A0_2, etc.) to meaningful names based on context.
2. Deobfuscate variable names where obvious.
3. Simplify redundant intermediate variable assignments.
4. Keep all event names, callback names and game function calls exactly the same.
5. Return ONLY raw Lua code.

{code}"""

    while model_holder[0] is not None:
        model = model_holder[0]
        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=65536,
                )
            )
            result = response.text.strip()
            if result.startswith('```'):
                result = result.split('\n', 1)[1] if '\n' in result else result
                result = result.rsplit('```', 1)[0].strip()
            return result
        except Exception as e:
            err_str = str(e)
            if '429' in err_str:
                next_model = get_next_model()
                if next_model:
                    model_holder[0] = next_model
                    print_status(f"Rate limited, switching to {MODELS[current_model_index]}", 'warning')
                else:
                    wait = _extract_retry_delay(err_str)
                    print_status(f"Todos os modelos esgotados. Aguardando {wait}s...", 'warning')
                    time.sleep(wait)
                    # Reinicia do primeiro modelo
                    current_model_index_reset = 0
                    model_holder[0] = genai.GenerativeModel(MODELS[0])
            else:
                print_status(f"Erro: {e}", 'error')
                return code  # devolve original em caso de erro não-quota

    return code


def split_into_chunks(code: str, max_lines: int = 150) -> list[str]:
    """Divide o código em blocos de max_lines linhas respeitando funções."""
    lines = code.split('\n')
    if len(lines) <= max_lines:
        return [code]

    chunks = []
    current = []
    for line in lines:
        current.append(line)
        # Tenta cortar em fim de função ou bloco vazio entre funções
        if len(current) >= max_lines:
            stripped = line.strip()
            if stripped == 'end' or stripped == '' or stripped.startswith('--'):
                chunks.append('\n'.join(current))
                current = []
    if current:
        chunks.append('\n'.join(current))
    return chunks


async def process_file(model_holder: list, input_path: Path, output_path: Path, file_index: int, total_files: int):
    """Processa um arquivo .lua completo de uma vez."""
    filename = input_path.name
    print_status(f"[{file_index}/{total_files}] Processando: {Colors.CYAN}{filename}{Colors.END}", 'working')

    code = input_path.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    print_status(f"  Linhas originais: {len(lines)}", 'info')

    cleaned_code = await asyncio.to_thread(clean_lua_code, model_holder, code, filename)

    if cleaned_code and cleaned_code != code:
        cleaned_lines = cleaned_code.split('\n')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(cleaned_code, encoding='utf-8')
        print_status(f"  ✓ Successfully cleaned {filename}", 'success')
        print_status(f"  Linhas: {len(lines)} → {len(cleaned_lines)}", 'info')
        return True
    else:
        print_status(f"  Failed to clean {filename}", 'error')
        return False


async def main_async(api_key: str):
    global current_model_index
    current_model_index = 0

    genai.configure(api_key=api_key)
    print_status('API do Gemini configurada com sucesso!', 'success')

    model_holder = [genai.GenerativeModel(MODELS[0])]
    print_status(f"Modelo inicial: {Colors.GREEN}{MODELS[0]}{Colors.END}", 'success')

    # Verifica pasta Input
    input_dir = Path(INPUT_DIR)
    if not input_dir.exists():
        input_dir.mkdir(parents=True)
        print_status(f"Pasta '{INPUT_DIR}' criada. Coloque seus arquivos .lua lá e rode novamente.", 'warning')
        return

    lua_files = list(input_dir.rglob('*.lua'))
    if not lua_files:
        print_status(f"Nenhum arquivo .lua encontrado em '{INPUT_DIR}'.", 'warning')
        return

    print_status(f"Encontrados {Colors.CYAN}{len(lua_files)}{Colors.END} arquivo(s) .lua", 'info')
    print(f"\n{Colors.DARK_CYAN}{'=' * 65}{Colors.END}\n")

    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.time()
    success_count = 0

    for i, input_path in enumerate(lua_files, 1):
        relative = input_path.relative_to(input_dir)
        output_path = output_dir / relative

        ok = await process_file(model_holder, input_path, output_path, i, len(lua_files))
        if ok:
            success_count += 1
        print()

    elapsed = time.time() - start_time
    print(f"\n{Colors.DARK_CYAN}{'=' * 65}{Colors.END}")
    print_status(f"Concluído! {success_count}/{len(lua_files)} arquivo(s) processado(s) em {elapsed:.1f}s", 'success')
    print_status(f"Arquivos salvos em: {Colors.GREEN}{output_dir.resolve()}{Colors.END}", 'info')


def main():
    print_banner()
    api_key = get_api_key()

    print(f"\n{Colors.DARK_CYAN}{'=' * 65}{Colors.END}\n")

    try:
        asyncio.run(main_async(api_key))
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Interrompido pelo usuário.{Colors.END}")
    except Exception as e:
        print_status(f"Erro inesperado: {e}", 'error')
        import traceback
        traceback.print_exc()

    print(f"\n{Colors.BLUE}Pressione Enter para sair...{Colors.END}")
    input()


if __name__ == '__main__':
    main()
