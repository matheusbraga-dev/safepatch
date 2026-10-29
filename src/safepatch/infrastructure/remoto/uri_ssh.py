"""Módulo de identificação e análise de destinos remotos via SSH/SFTP."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union
from urllib.parse import unquote, urlparse

CaminhoPath = Union[str, Path]


@dataclass(frozen=True)
class InfoDestinoSSH:
    """Metadados estruturados de um destino remoto acessível por SSH."""

    host: str
    caminho_remoto: str
    usuario: Optional[str] = None
    senha: Optional[str] = None
    porta: int = 22
    chave_privada: Optional[str] = None

    @property
    def nome_arquivo(self) -> str:
        """Extrai o nome do arquivo a partir do caminho remoto."""
        partes = self.caminho_remoto.replace("\\", "/").rstrip("/").split("/")
        return partes[-1] if partes else "pacote_remoto.jar"

    @property
    def uri_segura(self) -> str:
        """Retorna uma URI legível sem expor a senha caso tenha sido fornecida."""
        user_part = f"{self.usuario}@" if self.usuario else ""
        port_part = f":{self.porta}" if self.porta != 22 else ""
        caminho_limpo = self.caminho_remoto.replace("\\", "/").lstrip("/")
        return f"ssh://{user_part}{self.host}{port_part}/{caminho_limpo}"

    @property
    def especificador_scp(self) -> str:
        """Retorna no formato SCP (usuario@host:caminho)."""
        prefixo = f"{self.usuario}@" if self.usuario else ""
        return f"{prefixo}{self.host}:{self.caminho_remoto}"


def eh_destino_ssh(caminho: CaminhoPath) -> bool:
    """Verifica se um caminho representa um destino remoto via SSH."""
    return parsear_destino_ssh(caminho) is not None


def parsear_destino_ssh(
    caminho: CaminhoPath,
    chave_privada: Optional[str] = None,
    porta_padrao: Optional[int] = None,
    senha_padrao: Optional[str] = None,
) -> Optional[InfoDestinoSSH]:
    """Analisa um caminho e retorna InfoDestinoSSH se for uma URI ou destino SSH válido.

    Formatos suportados:
      - URI SSH: ssh://usuario:senha@host:porta/caminho/arquivo.jar
      - URI SFTP: sftp://usuario@host/caminho/arquivo.jar
      - SCP clássico: usuario@host:/caminho/arquivo.jar ou host:/caminho/arquivo.jar
    """
    if isinstance(caminho, Path):
        texto = str(caminho)
    else:
        texto = str(caminho).strip()

    if not texto:
        return None

    # Descarta caminhos locais com letra de unidade Windows (ex: C:\, D:/)
    if re.match(r"^[a-zA-Z]:[\\/]", texto):
        return None

    # 1. Formato URI: ssh://... ou sftp://...
    if texto.startswith(("ssh://", "sftp://")):
        parsed = urlparse(texto)
        if not parsed.hostname:
            return None

        porta = parsed.port or porta_padrao or 22
        usuario = unquote(parsed.username) if parsed.username else None
        senha = unquote(parsed.password) if parsed.password else senha_padrao
        caminho_remoto = unquote(parsed.path)

        if not caminho_remoto:
            caminho_remoto = "/"

        return InfoDestinoSSH(
            host=parsed.hostname,
            caminho_remoto=caminho_remoto,
            usuario=usuario,
            senha=senha,
            porta=porta,
            chave_privada=chave_privada,
        )

    # 2. Formato clássico SCP: [usuario@]host:/caminho/remoto
    # Requer ':' seguido de caminho que não seja letra de unidade Windows
    padrao_scp = r"^(?:(?P<usuario>[a-zA-Z0-9_\-\.]+)@)?(?P<host>[a-zA-Z0-9_\-\.]+):(?P<caminho>[^:].*)$"
    match = re.match(padrao_scp, texto)
    if match:
        grupos = match.groupdict()
        host = grupos["host"]
        # Se host tem apenas 1 letra (ex: C), é unidade Windows sem barra, descarta
        if len(host) == 1 and host.isalpha():
            return None

        caminho_remoto = grupos["caminho"]
        if not caminho_remoto:
            return None

        return InfoDestinoSSH(
            host=host,
            caminho_remoto=caminho_remoto,
            usuario=grupos.get("usuario"),
            senha=senha_padrao,
            porta=porta_padrao or 22,
            chave_privada=chave_privada,
        )

    return None
