"""Transporte SSH nativo do sistema operacional (utiliza binários OpenSSH como scp e ssh)."""

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from safepatch.domain.excecoes import AutenticacaoSSHError, TransferenciaRemotaError
from safepatch.infrastructure.remoto.transporte import (
    CallbackProgressoBytes,
    ItemRemotoInfo,
    ProtocoloTransporteSSH,
)
from safepatch.infrastructure.remoto.uri_ssh import InfoDestinoSSH


class TransporteNativoOpenSSH(ProtocoloTransporteSSH):
    """Implementação do transporte SSH utilizando o cliente OpenSSH (scp/ssh) nativo do SO.

    Mantém a filosofia de Zero Dependências Externas do SafePatch.
    """

    def __init__(self, binario_scp: Optional[str] = None, binario_ssh: Optional[str] = None):
        self.binario_scp = binario_scp or shutil.which("scp")
        self.binario_ssh = binario_ssh or shutil.which("ssh")

    def _verificar_scp(self) -> None:
        """Verifica se o cliente OpenSSH (scp) está presente no PATH do sistema."""
        if not self.binario_scp:
            raise TransferenciaRemotaError(
                "O binário 'scp' do OpenSSH não foi encontrado no PATH do sistema operacional. "
                "Instale o cliente OpenSSH ou utilize 'pip install safepatch[ssh]' para transporte via Paramiko."
            )

    def _verificar_ssh(self) -> None:
        """Verifica se o cliente OpenSSH (ssh) está presente no PATH do sistema."""
        if not self.binario_ssh:
            raise TransferenciaRemotaError(
                "O binário 'ssh' do OpenSSH não foi encontrado no PATH do sistema operacional. "
                "Instale o cliente OpenSSH ou utilize 'pip install safepatch[ssh]' para transporte via Paramiko."
            )

    def _montar_opcoes_comuns(self, destino: InfoDestinoSSH, flag_porta: str = "-P") -> List[str]:
        """Monta argumentos comuns para scp (-P) e ssh (-p)."""
        opts: List[str] = []
        if destino.porta and destino.porta != 22:
            opts.extend([flag_porta, str(destino.porta)])

        if destino.chave_privada:
            caminho_chave = Path(destino.chave_privada).expanduser().resolve()
            if not caminho_chave.is_file():
                raise TransferenciaRemotaError(f"Arquivo de chave privada não encontrado: {destino.chave_privada}")
            opts.extend(["-i", str(caminho_chave)])

        opts.extend(["-o", "StrictHostKeyChecking=accept-new"])
        if not destino.senha:
            opts.extend(["-o", "BatchMode=yes"])

        return opts

    def baixar_arquivo(
        self,
        destino: InfoDestinoSSH,
        caminho_destino_local: Path,
        notificador_progresso: Optional[CallbackProgressoBytes] = None,
    ) -> Path:
        """Transfere o arquivo remoto utilizando o utilitário nativo scp."""
        self._verificar_scp()
        caminho_destino_local.parent.mkdir(parents=True, exist_ok=True)

        comando = [self.binario_scp]
        comando.extend(self._montar_opcoes_comuns(destino, flag_porta="-P"))
        comando.append(destino.especificador_scp)
        comando.append(str(caminho_destino_local))

        try:
            resultado = subprocess.run(comando, capture_output=True, text=True, check=False)
        except Exception as err:
            raise TransferenciaRemotaError(f"Erro ao executar o comando 'scp': {err}") from err

        if resultado.returncode != 0:
            detalhe = resultado.stderr.strip() or resultado.stdout.strip() or f"Código de saída {resultado.returncode}"
            if "Permission denied" in detalhe or "Host key verification failed" in detalhe:
                raise AutenticacaoSSHError(f"Falha de autenticação SSH no servidor '{destino.host}': {detalhe}")
            if "No such file" in detalhe or "does not exist" in detalhe:
                raise TransferenciaRemotaError(
                    f"O arquivo remoto '{destino.caminho_remoto}' não foi encontrado no servidor '{destino.host}'."
                )
            raise TransferenciaRemotaError(f"Falha na transferência remota via SCP de '{destino.uri_segura}': {detalhe}")

        if not caminho_destino_local.is_file():
            raise TransferenciaRemotaError(
                f"A transferência SCP concluiu mas o arquivo de destino não foi gerado: {caminho_destino_local}"
            )

        if notificador_progresso:
            tamanho = caminho_destino_local.stat().st_size
            notificador_progresso(tamanho, tamanho)

        return caminho_destino_local

    def enviar_arquivo(
        self,
        caminho_origem_local: Path,
        destino: InfoDestinoSSH,
        notificador_progresso: Optional[CallbackProgressoBytes] = None,
    ) -> None:
        """Transfere um arquivo local para o servidor remoto utilizando scp."""
        self._verificar_scp()
        origem = Path(caminho_origem_local).resolve()
        if not origem.is_file():
            raise TransferenciaRemotaError(f"Arquivo local para envio não encontrado: {origem}")

        comando = [self.binario_scp]
        comando.extend(self._montar_opcoes_comuns(destino, flag_porta="-P"))
        comando.append(str(origem))
        comando.append(destino.especificador_scp)

        try:
            resultado = subprocess.run(comando, capture_output=True, text=True, check=False)
        except Exception as err:
            raise TransferenciaRemotaError(f"Erro ao executar upload via 'scp': {err}") from err

        if resultado.returncode != 0:
            detalhe = resultado.stderr.strip() or resultado.stdout.strip() or f"Código de saída {resultado.returncode}"
            if "Permission denied" in detalhe or "Host key verification failed" in detalhe:
                raise AutenticacaoSSHError(f"Falha de autenticação SSH no servidor '{destino.host}': {detalhe}")
            raise TransferenciaRemotaError(f"Falha no envio de arquivo via SCP para '{destino.uri_segura}': {detalhe}")

        if notificador_progresso:
            tamanho = origem.stat().st_size
            notificador_progresso(tamanho, tamanho)

    def executar_comando(
        self,
        destino: InfoDestinoSSH,
        comando: str,
    ) -> Tuple[int, str, str]:
        """Executa um comando remoto utilizando o utilitário nativo ssh."""
        self._verificar_ssh()
        cmd = [self.binario_ssh]
        cmd.extend(self._montar_opcoes_comuns(destino, flag_porta="-p"))

        alvo_ssh = f"{destino.usuario}@{destino.host}" if destino.usuario else destino.host
        cmd.append(alvo_ssh)
        cmd.append(comando)

        try:
            resultado = subprocess.run(cmd, capture_output=True, text=True, check=False)
            return resultado.returncode, resultado.stdout, resultado.stderr
        except Exception as err:
            raise TransferenciaRemotaError(f"Erro ao executar comando via SSH: {err}") from err

    def calcular_sha256(
        self,
        destino: InfoDestinoSSH,
        caminho_remoto: Optional[str] = None,
    ) -> str:
        """Calcula o hash SHA-256 do arquivo remoto executando ferramentas nativas (sha256sum/shasum/python3)."""
        alvo = caminho_remoto or destino.caminho_remoto
        cmd_remoto = (
            f"sha256sum '{alvo}' 2>/dev/null || "
            f"shasum -a 256 '{alvo}' 2>/dev/null || "
            f"python3 -c \"import hashlib, sys; print(hashlib.sha256(open(sys.argv[1], 'rb').read()).hexdigest())\" '{alvo}'"
        )
        codigo, stdout, stderr = self.executar_comando(destino, cmd_remoto)
        if codigo != 0:
            raise TransferenciaRemotaError(
                f"Não foi possível calcular o SHA-256 de '{alvo}' no servidor '{destino.host}': {stderr.strip()}"
            )

        match = re.search(r"\b([a-fA-F0-9]{64})\b", stdout)
        if not match:
            raise TransferenciaRemotaError(
                f"Saída inesperada ao calcular SHA-256 remoto de '{alvo}': {stdout.strip()}"
            )
        return match.group(1).lower()

    def listar_diretorio(
        self,
        destino: InfoDestinoSSH,
        caminho_dir: Optional[str] = None,
    ) -> List[ItemRemotoInfo]:
        """Lista os arquivos e subdiretórios remotos."""
        alvo = caminho_dir or destino.caminho_remoto or "."

        # Tenta listar estruturadamente via script python one-liner remoto
        script_python = (
            "python3 -c \""
            "import os, sys, json, datetime; "
            "p = os.path.expanduser(sys.argv[1]); "
            "res = []; "
            "try:\n"
            "    entries = list(os.scandir(p))\n"
            "    for e in entries:\n"
            "        try:\n"
            "            st = e.stat(follow_symlinks=False)\n"
            "            eh_d = e.is_dir()\n"
            "            mtime = datetime.datetime.fromtimestamp(st.st_mtime, datetime.timezone.utc).isoformat() if st.st_mtime else None\n"
            "            res.append({'nome': e.name, 'caminho': e.path.replace('\\\\\\\\', '/'), 'eh_diretorio': eh_d, 'tamanho_bytes': st.st_size if not eh_d else 0, 'modificado_em': mtime})\n"
            "        except Exception:\n"
            "            pass\n"
            "    print('__SAFEPATCH_JSON__' + json.dumps(res))\n"
            "except Exception as err:\n"
            "    print('__ERR__' + str(err), file=sys.stderr)\n"
            f"\" '{alvo}'"
        )

        codigo, stdout, stderr = self.executar_comando(destino, script_python)
        if codigo == 0 and "__SAFEPATCH_JSON__" in stdout:
            partes = stdout.split("__SAFEPATCH_JSON__", 1)
            try:
                dados = json.loads(partes[1].strip())
                itens = [
                    ItemRemotoInfo(
                        nome=item["nome"],
                        caminho=item["caminho"],
                        eh_diretorio=item["eh_diretorio"],
                        tamanho_bytes=item.get("tamanho_bytes", 0),
                        modificado_em=item.get("modificado_em"),
                    )
                    for item in dados
                ]
                # Ordena: diretórios primeiro, depois arquivos alfabeticamente
                itens.sort(key=lambda x: (not x.eh_diretorio, x.nome.lower()))
                return itens
            except Exception:
                pass

        # Fallback: comando ls -la
        codigo_ls, stdout_ls, stderr_ls = self.executar_comando(destino, f"ls -la '{alvo}'")
        if codigo_ls != 0:
            raise TransferenciaRemotaError(
                f"Erro ao listar diretório remoto '{alvo}' no servidor '{destino.host}': {stderr_ls.strip()}"
            )

        itens_ls: List[ItemRemotoInfo] = []
        caminho_base = alvo.rstrip("/")
        for linha in stdout_ls.splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("total"):
                continue
            partes = linha.split(None, 8)
            if len(partes) < 9:
                continue

            perms = partes[0]
            nome = partes[8]
            if nome in (".", ".."):
                continue

            eh_dir = perms.startswith("d")
            try:
                tamanho = int(partes[4]) if not eh_dir else 0
            except ValueError:
                tamanho = 0

            caminho_completo = f"{caminho_base}/{nome}"
            itens_ls.append(
                ItemRemotoInfo(
                    nome=nome,
                    caminho=caminho_completo,
                    eh_diretorio=eh_dir,
                    tamanho_bytes=tamanho,
                    permissoes=perms,
                )
            )

        itens_ls.sort(key=lambda x: (not x.eh_diretorio, x.nome.lower()))
        return itens_ls
