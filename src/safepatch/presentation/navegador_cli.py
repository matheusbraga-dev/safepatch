"""Navegador de arquivos remotos para terminal e linha de comando do SafePatch."""

import sys
from pathlib import Path
from typing import List, Optional

from safepatch.infrastructure.remoto.resolvedor_ssh import ResolvedorCaminhoRemoto
from safepatch.infrastructure.remoto.transporte import ItemRemotoInfo
from safepatch.infrastructure.remoto.uri_ssh import parsear_destino_ssh


def formatar_tabela_remota(
    itens: List[ItemRemotoInfo],
    caminho_atual: str,
    servidor: str,
    indice_selecionado: Optional[int] = None,
) -> str:
    """Gera uma visualização tabular formatada dos arquivos e pastas remotos."""
    linhas = [
        f"Servidor:  {servidor}",
        f"Diretório: {caminho_atual}",
        "",
        "    TIPO   TAMANHO      MODIFICADO               NOME",
        "-" * 72,
    ]

    total_pastas = 0
    total_arquivos = 0

    for idx, item in enumerate(itens):
        if item.eh_diretorio:
            total_pastas += 1
            tipo_tag = "[DIR]"
        elif item.eh_pacote:
            total_arquivos += 1
            tipo_tag = "[JAR]"
        else:
            total_arquivos += 1
            tipo_tag = "[ARQ]"

        marcador = "> " if indice_selecionado is not None and idx == indice_selecionado else "  "
        num_str = f"[{idx + 1}]".rjust(5)
        tam_str = item.tamanho_formatado.rjust(10)
        mod_str = (item.modificado_em[:19].replace("T", " ") if item.modificado_em else "-").ljust(22)
        nome_exibicao = f"{item.nome}/" if item.eh_diretorio and not item.nome.endswith("/") else item.nome

        linhas.append(f"{marcador}{num_str} {tipo_tag} {tam_str}  {mod_str} {nome_exibicao}")

    linhas.append("-" * 72)
    linhas.append(f"Total: {len(itens)} itens ({total_pastas} pastas, {total_arquivos} arquivos)")
    return "\n".join(linhas)


class NavegadorRemotoTerminal:
    """Orquestrador de exploração e navegação interativa no terminal por teclado."""

    def __init__(self, resolvedor: ResolvedorCaminhoRemoto):
        self.resolvedor = resolvedor

    def exibir_listagem(
        self,
        destino_uri: str,
        caminho_dir: Optional[str] = None,
        chave_ssh: Optional[str] = None,
        porta_ssh: Optional[int] = None,
        senha_ssh: Optional[str] = None,
    ) -> List[ItemRemotoInfo]:
        """Obtém e exibe no console a listagem estática do diretório."""
        destino = parsear_destino_ssh(
            destino_uri,
            chave_privada=chave_ssh,
            porta_padrao=porta_ssh,
            senha_padrao=senha_ssh,
        )
        if not destino:
            raise ValueError(f"Destino SSH inválido: {destino_uri}")

        caminho_efetivo = caminho_dir or destino.caminho_remoto or "/"
        itens = self.resolvedor.listar_remoto(
            destino_uri=destino_uri,
            caminho_dir=caminho_efetivo,
            chave_ssh=chave_ssh,
            porta_ssh=porta_ssh,
            senha_ssh=senha_ssh,
        )

        # Adiciona entrada para subir de nível '..' se não estiver na raiz
        itens_com_pai: List[ItemRemotoInfo] = []
        if caminho_efetivo not in ("/", ""):
            partes = caminho_efetivo.rstrip("/").rsplit("/", 1)
            pai = partes[0] if partes[0] else "/"
            itens_com_pai.append(
                ItemRemotoInfo(
                    nome="..",
                    caminho=pai,
                    eh_diretorio=True,
                )
            )
        itens_com_pai.extend(itens)

        tabela = formatar_tabela_remota(
            itens=itens_com_pai,
            caminho_atual=caminho_efetivo,
            servidor=destino.uri_segura,
        )
        print(tabela)
        return itens_com_pai

    def navegar_interativo(
        self,
        destino_uri: str,
        chave_ssh: Optional[str] = None,
        porta_ssh: Optional[int] = None,
        senha_ssh: Optional[str] = None,
    ) -> Optional[str]:
        """Inicia sessão interativa no terminal com suporte a setas e seleção de arquivos."""
        destino = parsear_destino_ssh(
            destino_uri,
            chave_privada=chave_ssh,
            porta_padrao=porta_ssh,
            senha_padrao=senha_ssh,
        )
        if not destino:
            raise ValueError(f"Destino SSH inválido: {destino_uri}")

        caminho_atual = destino.caminho_remoto or "/"
        indice_selecionado = 0

        while True:
            itens = self.resolvedor.listar_remoto(
                destino_uri=destino_uri,
                caminho_dir=caminho_atual,
                chave_ssh=chave_ssh,
                porta_ssh=porta_ssh,
                senha_ssh=senha_ssh,
            )

            lista_exibicao: List[ItemRemotoInfo] = []
            if caminho_atual not in ("/", ""):
                partes = caminho_atual.rstrip("/").rsplit("/", 1)
                pai = partes[0] if partes[0] else "/"
                lista_exibicao.append(ItemRemotoInfo(nome="..", caminho=pai, eh_diretorio=True))
            lista_exibicao.extend(itens)

            if not lista_exibicao:
                print(f"Diretório vazio: {caminho_atual}")
                return None

            indice_selecionado = max(0, min(indice_selecionado, len(lista_exibicao) - 1))

            # Exibe estado atual
            tabela = formatar_tabela_remota(
                itens=lista_exibicao,
                caminho_atual=caminho_atual,
                servidor=destino.uri_segura,
                indice_selecionado=indice_selecionado,
            )
            print("\n" + tabela)
            print("Navegação: [↑/↓ ou Número] Mover | [Enter] Abrir/Selecionar | [q] Sair")

            # Leitura de comando ou tecla
            item_atual = lista_exibicao[indice_selecionado]

            tecla = self._ler_entrada_teclado()
            if tecla == "UP":
                indice_selecionado = (indice_selecionado - 1) % len(lista_exibicao)
            elif tecla == "DOWN":
                indice_selecionado = (indice_selecionado + 1) % len(lista_exibicao)
            elif tecla in ("ENTER", "OPEN"):
                if item_atual.eh_diretorio:
                    caminho_atual = item_atual.caminho
                    indice_selecionado = 0
                else:
                    uri_arquivo = f"{destino.uri_segura.rsplit('/', 1)[0]}/{item_atual.nome}"
                    print(f"\n[OK] Arquivo selecionado: {item_atual.caminho}")
                    return item_atual.caminho
            elif tecla == "BACK":
                if caminho_atual not in ("/", ""):
                    partes = caminho_atual.rstrip("/").rsplit("/", 1)
                    caminho_atual = partes[0] if partes[0] else "/"
                    indice_selecionado = 0
            elif tecla in ("QUIT", "ESC"):
                print("\nNavegação remota cancelada.")
                return None
            elif tecla.isdigit():
                idx_num = int(tecla) - 1
                if 0 <= idx_num < len(lista_exibicao):
                    escolhido = lista_exibicao[idx_num]
                    if escolhido.eh_diretorio:
                        caminho_atual = escolhido.caminho
                        indice_selecionado = 0
                    else:
                        print(f"\n[OK] Arquivo selecionado: {escolhido.caminho}")
                        return escolhido.caminho

    def _ler_entrada_teclado(self) -> str:
        """Lê entrada interativa (setas ou comando) compatível com Windows e Unix."""
        if sys.platform == "win32":
            try:
                import msvcrt
                char = msvcrt.getch()
                if char in (b"\x00", b"\xe0"):
                    sub = msvcrt.getch()
                    if sub == b"H":
                        return "UP"
                    if sub == b"P":
                        return "DOWN"
                elif char in (b"\r", b"\n"):
                    return "ENTER"
                elif char == b"\x08":
                    return "BACK"
                elif char in (b"q", b"Q", b"\x1b"):
                    return "QUIT"
                elif char.isdigit():
                    return char.decode("ascii")
            except Exception:
                pass

        # Fallback de linha padrão para terminais não-raw ou redirecionados
        try:
            cmd = input("Digite o número do item, '..' para voltar ou 'q' para sair: ").strip()
            if cmd.lower() in ("q", "sair", "exit"):
                return "QUIT"
            if cmd == "..":
                return "BACK"
            if cmd.isdigit():
                return cmd
            return "ENTER"
        except (EOFError, KeyboardInterrupt):
            return "QUIT"
