"""Modelos de dados imutáveis do domínio SafePatch."""

from dataclasses import dataclass, field
from typing import List, Optional
from safepatch.shared.formatacao import formatar_bytes, formatar_delta


@dataclass(frozen=True)
class ArquivoInfo:
    """Metadados de um arquivo contido dentro de um pacote compactado ou código-fonte."""

    caminho: str
    hash_sha256: str
    tamanho_bytes: int
    caminho_origem: Optional[str] = None

    @property
    def tamanho_formatado(self) -> str:
        return formatar_bytes(self.tamanho_bytes)

    @property
    def eh_fonte_java(self) -> bool:
        """Indica se este arquivo representa um código-fonte Java (.java)."""
        caminho_ref = self.caminho_origem or self.caminho
        return caminho_ref.lower().endswith(".java")


@dataclass(frozen=True)
class ArquivoModificadoInfo:
    """Representa um arquivo presente em ambos os pacotes com conteúdos divergentes (conflito)."""

    caminho: str
    base: ArquivoInfo
    alvo: ArquivoInfo

    @property
    def delta_bytes(self) -> int:
        return self.alvo.tamanho_bytes - self.base.tamanho_bytes

    @property
    def delta_formatado(self) -> str:
        return formatar_delta(self.delta_bytes)

    @property
    def comparando_fonte_com_bytecode(self) -> bool:
        """Indica se a comparação é entre bytecode (.class) e código-fonte (.java)."""
        return self.base.eh_fonte_java != self.alvo.eh_fonte_java


@dataclass
class RelatorioComparacao:
    """Relatório estruturado consolidando as diferenças entre o pacote base e o pacote alvo."""

    pacote_base: str
    pacote_alvo: str
    adicionados: List[ArquivoInfo] = field(default_factory=list)
    removidos: List[ArquivoInfo] = field(default_factory=list)
    inalterados: List[ArquivoInfo] = field(default_factory=list)
    modificados: List[ArquivoModificadoInfo] = field(default_factory=list)
    ignorados: List[str] = field(default_factory=list)

    @property
    def tem_conflitos(self) -> bool:
        """Indica se foram encontrados arquivos modificados entre os pacotes."""
        return len(self.modificados) > 0

    @property
    def total_modificados(self) -> int:
        return len(self.modificados)

    @property
    def total_adicionados(self) -> int:
        return len(self.adicionados)

    @property
    def total_removidos(self) -> int:
        return len(self.removidos)

    @property
    def total_inalterados(self) -> int:
        return len(self.inalterados)

    @property
    def total_ignorados(self) -> int:
        return len(self.ignorados)
