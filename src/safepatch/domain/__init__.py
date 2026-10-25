"""Módulo de domínio do SafePatch."""

from .excecoes import (
    ArquivoNaoEncontradoError,
    DescompilacaoError,
    DescompilacaoTimeoutError,
    ExportacaoError,
    FormatoNaoSuportadoError,
    LimiteTamanhoExcedidoError,
    PacoteCorrompidoError,
    PacoteInvalidoError,
    SafePatchError,
)
from .modelos import ArquivoInfo, ArquivoModificadoInfo, RelatorioComparacao
from .protocolos import (
    ProtocoloComparador,
    ProtocoloDescompilador,
    ProtocoloDiferenciador,
    ProtocoloExportador,
    ProtocoloLeitor,
)

__all__ = [
    "ArquivoInfo",
    "ArquivoModificadoInfo",
    "RelatorioComparacao",
    "SafePatchError",
    "PacoteInvalidoError",
    "ArquivoNaoEncontradoError",
    "FormatoNaoSuportadoError",
    "PacoteCorrompidoError",
    "LimiteTamanhoExcedidoError",
    "DescompilacaoError",
    "DescompilacaoTimeoutError",
    "ExportacaoError",
    "ProtocoloLeitor",
    "ProtocoloComparador",
    "ProtocoloDescompilador",
    "ProtocoloDiferenciador",
    "ProtocoloExportador",
]
