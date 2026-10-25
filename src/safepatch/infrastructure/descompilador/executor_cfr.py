"""Motor de descompilação de bytecode Java via CFR Decompiler com fallback para javap."""

import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import List, Optional, Union

from safepatch.config.configuracoes import CONFIGURACOES_PADRAO, ConfiguracoesSafePatch
from safepatch.domain.excecoes import LimiteTamanhoExcedidoError
from safepatch.domain.protocolos import ProtocoloDescompilador

CaminhoPath = Union[str, Path]


class DescompiladorCFR(ProtocoloDescompilador):
    """Descompila arquivos .class contidos em pacotes compactados em código-fonte legível."""

    def __init__(
        self,
        caminho_cfr_jar: Optional[CaminhoPath] = None,
        java_cmd: Optional[str] = None,
        javap_cmd: Optional[str] = None,
        configuracoes: ConfiguracoesSafePatch = CONFIGURACOES_PADRAO,
    ):
        self.configuracoes = configuracoes
        self.java_cmd = java_cmd or shutil.which("java")
        self.javap_cmd = javap_cmd or shutil.which("javap")
        self._caminho_cfr = self._resolver_caminho_cfr(caminho_cfr_jar)

    def _resolver_caminho_cfr(self, caminho_fornecido: Optional[CaminhoPath]) -> Optional[Path]:
        """Localiza o jar do CFR de forma determinística no pacote ou diretório do usuário."""
        if caminho_fornecido:
            p = Path(caminho_fornecido).resolve()
            if p.is_file():
                return p

        # 1. Local padrão do pacote instalado (src/safepatch/bin/cfr.jar)
        caminho_pacote = Path(__file__).resolve().parent.parent.parent / "bin" / "cfr.jar"
        if caminho_pacote.is_file():
            return caminho_pacote

        # 2. Diretório home do usuário (~/.safepatch/cfr.jar)
        caminho_home = Path.home() / ".safepatch" / "cfr.jar"
        if caminho_home.is_file():
            return caminho_home

        return None

    def descompilar(self, caminho_pacote: CaminhoPath, caminho_interno: str) -> Optional[List[str]]:
        """Extrai temporariamente o .class e executa descompilação segura com timeout."""
        caminho_pacote_path = Path(caminho_pacote).resolve()

        try:
            with zipfile.ZipFile(caminho_pacote_path, "r") as zf:
                info = zf.getinfo(caminho_interno)
                if info.file_size > self.configuracoes.tamanho_maximo_descompactado:
                    raise LimiteTamanhoExcedidoError(
                        caminho_interno,
                        info.file_size,
                        self.configuracoes.tamanho_maximo_descompactado,
                    )
                dados_bytecode = zf.read(caminho_interno)
        except Exception:
            return None

        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_class = Path(tmp_dir) / "Target.class"
            temp_class.write_bytes(dados_bytecode)
            temp_name = str(temp_class)

            # 1. Tentar descompilação CFR para código Java limpo
            if self._caminho_cfr and self.java_cmd:
                try:
                    res = subprocess.run(
                        [
                            self.java_cmd,
                            "-jar",
                            str(self._caminho_cfr),
                            temp_name,
                            "--silent",
                            "true",
                            "--comments",
                            "false",
                            "--showversion",
                            "false",
                        ],
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=self.configuracoes.tempo_limite_subprocesso,
                    )
                    if res.returncode == 0 and res.stdout.strip():
                        return [linha + "\n" for linha in res.stdout.splitlines()]
                except (subprocess.TimeoutExpired, OSError):
                    pass

            # 2. Fallback: javap estruturado
            if self.javap_cmd:
                try:
                    res = subprocess.run(
                        [self.javap_cmd, "-c", "-p", temp_name],
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=self.configuracoes.tempo_limite_subprocesso,
                    )
                    if res.returncode == 0 and res.stdout.strip():
                        return [linha + "\n" for linha in res.stdout.splitlines()]
                except (subprocess.TimeoutExpired, OSError):
                    pass

        return None
