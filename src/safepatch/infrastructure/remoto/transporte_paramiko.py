"""Transporte SSH baseado na biblioteca Paramiko (SFTP de alta performance)."""

import hashlib
import re
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from safepatch.domain.excecoes import AutenticacaoSSHError, TransferenciaRemotaError
from safepatch.infrastructure.remoto.transporte import (
    CallbackProgressoBytes,
    ItemRemotoInfo,
    ProtocoloTransporteSSH,
)
from safepatch.infrastructure.remoto.uri_ssh import InfoDestinoSSH

try:
    import paramiko
    TEM_PARAMIKO = True
except ImportError:
    paramiko = None
    TEM_PARAMIKO = False


class TransporteParamiko(ProtocoloTransporteSSH):
    """Implementação do transporte SSH utilizando Paramiko e SFTP."""

    def __init__(self, timeout: int = 30):
        if not TEM_PARAMIKO:
            raise ImportError(
                "A biblioteca 'paramiko' não está instalada. "
                "Instale via 'pip install safepatch[ssh]' ou utilize o transporte nativo do sistema."
            )
        self.timeout = timeout

    def _criar_cliente(self, destino: InfoDestinoSSH) -> "paramiko.SSHClient":
        """Instancia e conecta o cliente SSH com as credenciais fornecidas."""
        cliente = paramiko.SSHClient()
        cliente.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        kwargs = {
            "hostname": destino.host,
            "port": destino.porta,
            "timeout": self.timeout,
        }
        if destino.usuario:
            kwargs["username"] = destino.usuario
        if destino.senha:
            kwargs["password"] = destino.senha
        if destino.chave_privada:
            caminho_chave = Path(destino.chave_privada).expanduser().resolve()
            if not caminho_chave.is_file():
                raise TransferenciaRemotaError(f"Arquivo de chave privada não encontrado: {destino.chave_privada}")
            kwargs["key_filename"] = str(caminho_chave)

        try:
            cliente.connect(**kwargs)
            return cliente
        except paramiko.AuthenticationException as err:
            cliente.close()
            raise AutenticacaoSSHError(
                f"Falha de autenticação SSH no host '{destino.host}' para o usuário '{destino.usuario}': {err}"
            ) from err
        except Exception as err:
            cliente.close()
            raise TransferenciaRemotaError(
                f"Erro ao conectar via SSH em '{destino.uri_segura}': {err}"
            ) from err

    def baixar_arquivo(
        self,
        destino: InfoDestinoSSH,
        caminho_destino_local: Path,
        notificador_progresso: Optional[CallbackProgressoBytes] = None,
    ) -> Path:
        """Transfere o arquivo remoto utilizando SFTP com relatório de progresso em bytes."""
        cliente = self._criar_cliente(destino)
        sftp = None
        try:
            sftp = cliente.open_sftp()
            try:
                stat_remoto = sftp.stat(destino.caminho_remoto)
                tamanho_total = stat_remoto.st_size
            except Exception:
                tamanho_total = 0

            def callback_interno(transferidos: int, total: int) -> None:
                if notificador_progresso:
                    total_efetivo = total if total > 0 else tamanho_total
                    notificador_progresso(transferidos, total_efetivo)

            caminho_destino_local.parent.mkdir(parents=True, exist_ok=True)
            sftp.get(destino.caminho_remoto, str(caminho_destino_local), callback=callback_interno)
            return caminho_destino_local
        except FileNotFoundError as err:
            raise TransferenciaRemotaError(
                f"O arquivo remoto '{destino.caminho_remoto}' não existe no servidor '{destino.host}'."
            ) from err
        except Exception as err:
            raise TransferenciaRemotaError(
                f"Falha na transferência SFTP do arquivo '{destino.caminho_remoto}': {err}"
            ) from err
        finally:
            if sftp:
                try:
                    sftp.close()
                except Exception:
                    pass
            try:
                cliente.close()
            except Exception:
                pass

    def enviar_arquivo(
        self,
        caminho_origem_local: Path,
        destino: InfoDestinoSSH,
        notificador_progresso: Optional[CallbackProgressoBytes] = None,
    ) -> None:
        """Transfere o arquivo local para o servidor remoto utilizando SFTP."""
        origem = Path(caminho_origem_local).resolve()
        if not origem.is_file():
            raise TransferenciaRemotaError(f"Arquivo local para envio não encontrado: {origem}")

        cliente = self._criar_cliente(destino)
        sftp = None
        try:
            sftp = cliente.open_sftp()
            tamanho_total = origem.stat().st_size

            def callback_interno(transferidos: int, total: int) -> None:
                if notificador_progresso:
                    total_efetivo = total if total > 0 else tamanho_total
                    notificador_progresso(transferidos, total_efetivo)

            sftp.put(str(origem), destino.caminho_remoto, callback=callback_interno)
        except Exception as err:
            raise TransferenciaRemotaError(
                f"Falha no envio de arquivo via SFTP para '{destino.uri_segura}': {err}"
            ) from err
        finally:
            if sftp:
                try:
                    sftp.close()
                except Exception:
                    pass
            try:
                cliente.close()
            except Exception:
                pass

    def executar_comando(
        self,
        destino: InfoDestinoSSH,
        comando: str,
    ) -> Tuple[int, str, str]:
        """Executa um comando no servidor remoto utilizando canal SSH."""
        cliente = self._criar_cliente(destino)
        try:
            stdin, stdout, stderr = cliente.exec_command(comando, timeout=self.timeout)
            codigo = stdout.channel.recv_exit_status()
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            return codigo, out, err
        except Exception as err:
            raise TransferenciaRemotaError(f"Erro ao executar comando via SSH: {err}") from err
        finally:
            try:
                cliente.close()
            except Exception:
                pass

    def calcular_sha256(
        self,
        destino: InfoDestinoSSH,
        caminho_remoto: Optional[str] = None,
    ) -> str:
        """Calcula o hash SHA-256 do arquivo remoto via comando ou streaming SFTP."""
        alvo = caminho_remoto or destino.caminho_remoto
        cliente = self._criar_cliente(destino)
        try:
            # 1. Tenta calcular rapidamente via utilitários do SO remoto
            cmd_remoto = (
                f"sha256sum '{alvo}' 2>/dev/null || "
                f"shasum -a 256 '{alvo}' 2>/dev/null || "
                f"python3 -c \"import hashlib, sys; print(hashlib.sha256(open(sys.argv[1], 'rb').read()).hexdigest())\" '{alvo}'"
            )
            stdin, stdout, stderr = cliente.exec_command(cmd_remoto, timeout=self.timeout)
            codigo = stdout.channel.recv_exit_status()
            if codigo == 0:
                texto = stdout.read().decode("utf-8", errors="replace")
                match = re.search(r"\b([a-fA-F0-9]{64})\b", texto)
                if match:
                    return match.group(1).lower()

            # 2. Fallback resiliente: lê stream pelo SFTP caso o servidor não permita shell
            sftp = cliente.open_sftp()
            try:
                hasher = hashlib.sha256()
                with sftp.open(alvo, "rb") as remoto_fp:
                    while True:
                        bloco = remoto_fp.read(65536)
                        if not bloco:
                            break
                        hasher.update(bloco)
                return hasher.hexdigest().lower()
            finally:
                sftp.close()
        except Exception as err:
            raise TransferenciaRemotaError(
                f"Não foi possível calcular o SHA-256 do arquivo remoto '{alvo}': {err}"
            ) from err
        finally:
            try:
                cliente.close()
            except Exception:
                pass

    def listar_diretorio(
        self,
        destino: InfoDestinoSSH,
        caminho_dir: Optional[str] = None,
    ) -> List[ItemRemotoInfo]:
        """Lista os arquivos e subdiretórios remotos via SFTP."""
        alvo = caminho_dir or destino.caminho_remoto or "."
        cliente = self._criar_cliente(destino)
        sftp = None
        try:
            sftp = cliente.open_sftp()
            attrs = sftp.listdir_attr(alvo)
            caminho_base = alvo.rstrip("/")
            itens: List[ItemRemotoInfo] = []

            for attr in attrs:
                nome = attr.filename
                if nome in (".", ".."):
                    continue

                eh_dir = stat.S_ISDIR(attr.st_mode) if attr.st_mode else False
                caminho_completo = f"{caminho_base}/{nome}"
                mtime_str = (
                    datetime.fromtimestamp(attr.st_mtime, timezone.utc).isoformat()
                    if attr.st_mtime
                    else None
                )

                itens.append(
                    ItemRemotoInfo(
                        nome=nome,
                        caminho=caminho_completo,
                        eh_diretorio=eh_dir,
                        tamanho_bytes=attr.st_size if not eh_dir else 0,
                        modificado_em=mtime_str,
                    )
                )

            itens.sort(key=lambda x: (not x.eh_diretorio, x.nome.lower()))
            return itens
        except FileNotFoundError as err:
            raise TransferenciaRemotaError(
                f"O diretório remoto '{alvo}' não foi encontrado no servidor '{destino.host}'."
            ) from err
        except Exception as err:
            raise TransferenciaRemotaError(
                f"Erro ao listar diretório remoto '{alvo}' via SFTP: {err}"
            ) from err
        finally:
            if sftp:
                try:
                    sftp.close()
                except Exception:
                    pass
            try:
                cliente.close()
            except Exception:
                pass
