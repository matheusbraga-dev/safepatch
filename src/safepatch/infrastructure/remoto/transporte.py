"""Contrato e protocolo para motores de transporte SSH."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple
from safepatch.infrastructure.remoto.uri_ssh import InfoDestinoSSH

# Callback de progresso: (bytes_transferidos, total_bytes)
CallbackProgressoBytes = Callable[[int, int], None]


@dataclass(frozen=True)
class ItemRemotoInfo:
    """Representa um item (arquivo ou diretório) no servidor remoto."""

    nome: str
    caminho: str
    eh_diretorio: bool
    tamanho_bytes: int = 0
    modificado_em: Optional[str] = None
    permissoes: Optional[str] = None

    @property
    def eh_pacote(self) -> bool:
        """Indica se é um pacote Java (.jar, .war, .zip, .ear)."""
        ext = self.nome.lower()
        return ext.endswith((".jar", ".war", ".zip", ".ear"))

    @property
    def tamanho_formatado(self) -> str:
        """Formata o tamanho em bytes para leitura humana (ex: '12.4 MB')."""
        if self.eh_diretorio:
            return "<DIR>"
        bytes_val = float(self.tamanho_bytes)
        for unidade in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_val < 1024.0 or unidade == "TB":
                return f"{bytes_val:.1f} {unidade}" if unidade != "B" else f"{int(bytes_val)} B"
            bytes_val /= 1024.0
        return f"{self.tamanho_bytes} B"

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário serializável em JSON."""
        return {
            "nome": self.nome,
            "caminho": self.caminho,
            "eh_diretorio": self.eh_diretorio,
            "eh_pacote": self.eh_pacote,
            "tamanho_bytes": self.tamanho_bytes,
            "tamanho_formatado": self.tamanho_formatado,
            "modificado_em": self.modificado_em,
            "permissoes": self.permissoes,
        }


class ProtocoloTransporteSSH(Protocol):
    """Contrato abstrato para implementações de transporte SSH (Paramiko ou OpenSSH nativo)."""

    def baixar_arquivo(
        self,
        destino: InfoDestinoSSH,
        caminho_destino_local: Path,
        notificador_progresso: Optional[CallbackProgressoBytes] = None,
    ) -> Path:
        """Transfere um arquivo remoto via SSH/SFTP para o destino local."""
        ...

    def enviar_arquivo(
        self,
        caminho_origem_local: Path,
        destino: InfoDestinoSSH,
        notificador_progresso: Optional[CallbackProgressoBytes] = None,
    ) -> None:
        """Transfere um arquivo local via SSH/SFTP para o destino remoto."""
        ...

    def listar_diretorio(
        self,
        destino: InfoDestinoSSH,
        caminho_dir: Optional[str] = None,
    ) -> List[ItemRemotoInfo]:
        """Lista os arquivos e subdiretórios de um caminho remoto."""
        ...

    def executar_comando(
        self,
        destino: InfoDestinoSSH,
        comando: str,
    ) -> Tuple[int, str, str]:
        """Executa um comando no servidor remoto e retorna (codigo_saida, stdout, stderr)."""
        ...

    def calcular_sha256(
        self,
        destino: InfoDestinoSSH,
        caminho_remoto: Optional[str] = None,
    ) -> str:
        """Calcula o hash SHA-256 do arquivo no servidor remoto."""
        ...
