"""Leitor de pacotes compactados (.jar, .war, .zip) com streaming e segurança."""

import hashlib
import zipfile
from pathlib import Path
from typing import Dict, Union

from safepatch.config.configuracoes import CONFIGURACOES_PADRAO, ConfiguracoesSafePatch
from safepatch.domain.excecoes import (
    ArquivoNaoEncontradoError,
    FormatoNaoSuportadoError,
    LimiteTamanhoExcedidoError,
    PacoteCorrompidoError,
)
from safepatch.domain.modelos import ArquivoInfo
from safepatch.domain.protocolos import ProtocoloLeitor

CaminhoPath = Union[str, Path]


class LeitorPacoteZip(ProtocoloLeitor):
    """Leitor de pacotes .jar, .war e .zip em streaming com controle de integridade SHA-256."""

    def __init__(self, configuracoes: ConfiguracoesSafePatch = CONFIGURACOES_PADRAO):
        self.configuracoes = configuracoes

    def validar_pacote(self, caminho: CaminhoPath) -> Path:
        """Valida a existência e formato de extensão do pacote compactado."""
        caminho_path = Path(caminho).resolve()

        if not caminho_path.exists() or not caminho_path.is_file():
            raise ArquivoNaoEncontradoError(str(caminho))

        sufixo = caminho_path.suffix.lower()
        if sufixo not in self.configuracoes.extensoes_suportadas:
            raise FormatoNaoSuportadoError(str(caminho), self.configuracoes.extensoes_suportadas)

        return caminho_path

    def mapear(self, caminho_pacote: CaminhoPath) -> Dict[str, ArquivoInfo]:
        """Lê o pacote compactado e mapeia os arquivos físicos internos."""
        caminho_valido = self.validar_pacote(caminho_pacote)
        inventario: Dict[str, ArquivoInfo] = {}

        try:
            with zipfile.ZipFile(caminho_valido, "r") as arquivo_zip:
                for info in arquivo_zip.infolist():
                    if info.is_dir():
                        continue

                    # Proteção contra Zip Bomb (exaustão de memória/disco)
                    if info.file_size > self.configuracoes.tamanho_maximo_descompactado:
                        raise LimiteTamanhoExcedidoError(
                            info.filename,
                            info.file_size,
                            self.configuracoes.tamanho_maximo_descompactado,
                        )

                    hash_sha256 = self._calcular_hash_streaming(arquivo_zip, info)
                    registro = ArquivoInfo(
                        caminho=info.filename,
                        hash_sha256=hash_sha256,
                        tamanho_bytes=info.file_size,
                    )
                    inventario[registro.caminho] = registro
        except zipfile.BadZipFile as err:
            raise PacoteCorrompidoError(str(caminho_valido), str(err)) from err

        return inventario

    def _calcular_hash_streaming(
        self, arquivo_zip: zipfile.ZipFile, info_arquivo: zipfile.ZipInfo
    ) -> str:
        """Calcula o hash SHA-256 lendo em blocos sob demanda para manter baixo consumo de memória."""
        sha256 = hashlib.sha256()

        with arquivo_zip.open(info_arquivo) as fluxo:
            while True:
                bloco = fluxo.read(self.configuracoes.tamanho_bloco)
                if not bloco:
                    break
                sha256.update(bloco)

        return sha256.hexdigest()
