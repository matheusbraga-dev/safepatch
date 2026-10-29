"""SafePatch: Ferramenta de auditoria e comparação de pacotes compactados (.jar, .war, .zip)."""

__version__ = "1.3.0"

from safepatch.application.casos_de_uso import CompararPacotesCasoDeUso
from safepatch.application.dtos import ParametrosComparacao
from safepatch.domain.excecoes import (
    ArquivoNaoEncontradoError,
    DescompilacaoError,
    ExportacaoError,
    ConexaoSSHError,
    AutenticacaoSSHError,
    TransferenciaRemotaError,
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
from safepatch.domain.protocolos import (
    ProtocoloAuditoria,
    ProtocoloComparador,
    ProtocoloDiferenciador,
    ProtocoloExportador,
    ProtocoloLeitor,
)
from safepatch.infrastructure.auditoria.gravador_auditoria import (
    CAMINHO_PADRAO_AUDITORIA,
    GravadorAuditoriaJSONL,
)
from safepatch.infrastructure.comparacao.comparador_conjuntos import (
    ComparadorPacotesConjuntos,
)
from safepatch.infrastructure.descompilador.executor_cfr import DescompiladorCFR
from safepatch.infrastructure.diff.motor_diff import MotorDiff
from safepatch.infrastructure.exportadores.exportador_html import ExportadorHTML
from safepatch.infrastructure.exportadores.exportador_json import ExportadorJSON
from safepatch.infrastructure.exportadores.exportador_markdown import ExportadorMarkdown
from safepatch.infrastructure.leitores.leitor_diretorio import LeitorDiretorio
from safepatch.infrastructure.leitores.leitor_fonte import LeitorFonteJava
from safepatch.infrastructure.leitores.leitor_universal import LeitorPacoteUniversal
from safepatch.infrastructure.leitores.leitor_zip import LeitorPacoteZip
from safepatch.infrastructure.remoto.transporte import ItemRemotoInfo
from safepatch.infrastructure.remoto.resolvedor_ssh import ResolvedorCaminhoRemoto
from safepatch.infrastructure.remoto.uri_ssh import (
    InfoDestinoSSH,
    eh_destino_ssh,
    parsear_destino_ssh,
)
from safepatch.shared.formatacao import formatar_bytes, formatar_delta

__all__ = [
    "__version__",
    "ArquivoInfo",
    "ArquivoModificadoInfo",
    "RelatorioComparacao",
    "ParametrosComparacao",
    "CompararPacotesCasoDeUso",
    "LeitorPacoteZip",
    "LeitorDiretorio",
    "LeitorFonteJava",
    "LeitorPacoteUniversal",
    "ComparadorPacotesConjuntos",
    "DescompiladorCFR",
    "MotorDiff",
    "ExportadorJSON",
    "ExportadorMarkdown",
    "ExportadorHTML",
    "InfoDestinoSSH",
    "ItemRemotoInfo",
    "eh_destino_ssh",
    "parsear_destino_ssh",
    "ResolvedorCaminhoRemoto",
    "ProtocoloAuditoria",
    "GravadorAuditoriaJSONL",
    "CAMINHO_PADRAO_AUDITORIA",
    "SafePatchError",
    "PacoteInvalidoError",
    "ArquivoNaoEncontradoError",
    "FormatoNaoSuportadoError",
    "PacoteCorrompidoError",
    "DescompilacaoError",
    "ExportacaoError",
    "ConexaoSSHError",
    "AutenticacaoSSHError",
    "TransferenciaRemotaError",
    "formatar_bytes",
    "formatar_delta",
]
