"""SafePatch: Ferramenta de auditoria e comparação de pacotes compactados (.jar, .war, .zip)."""

__version__ = "1.0.0"

from safepatch.application.casos_de_uso import CompararPacotesCasoDeUso
from safepatch.application.dtos import ParametrosComparacao
from safepatch.domain.excecoes import (
    ArquivoNaoEncontradoError,
    DescompilacaoError,
    ExportacaoError,
    FormatoNaoSuportadoError,
    PacoteCorrompidoError,
    PacoteInvalidoError,
    SafePatchError,
)
from safepatch.domain.modelos import (
    ArquivoInfo,
    ArquivoModificadoInfo,
    RelatorioComparacao,
)
from safepatch.infrastructure.comparacao.comparador_conjuntos import (
    ComparadorPacotesConjuntos,
)
from safepatch.infrastructure.descompilador.executor_cfr import DescompiladorCFR
from safepatch.infrastructure.diff.motor_diff import MotorDiff
from safepatch.infrastructure.exportadores.exportador_html import ExportadorHTML
from safepatch.infrastructure.exportadores.exportador_json import ExportadorJSON
from safepatch.infrastructure.exportadores.exportador_markdown import ExportadorMarkdown
from safepatch.infrastructure.leitores.leitor_zip import LeitorPacoteZip
from safepatch.shared.formatacao import formatar_bytes, formatar_delta

__all__ = [
    "__version__",
    "ArquivoInfo",
    "ArquivoModificadoInfo",
    "RelatorioComparacao",
    "ParametrosComparacao",
    "CompararPacotesCasoDeUso",
    "LeitorPacoteZip",
    "ComparadorPacotesConjuntos",
    "DescompiladorCFR",
    "MotorDiff",
    "ExportadorJSON",
    "ExportadorMarkdown",
    "ExportadorHTML",
    "SafePatchError",
    "PacoteInvalidoError",
    "ArquivoNaoEncontradoError",
    "FormatoNaoSuportadoError",
    "PacoteCorrompidoError",
    "DescompilacaoError",
    "ExportacaoError",
    "formatar_bytes",
    "formatar_delta",
]
