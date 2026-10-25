"""Módulo de infraestrutura do SafePatch."""

from .comparacao.comparador_conjuntos import ComparadorPacotesConjuntos
from .descompilador.executor_cfr import DescompiladorCFR
from .diff.motor_diff import MotorDiff
from .exportadores.exportador_html import ExportadorHTML
from .exportadores.exportador_json import ExportadorJSON
from .exportadores.exportador_markdown import ExportadorMarkdown
from .leitores.leitor_zip import LeitorPacoteZip
from .sistema_arquivos.escritor_atomico import escrever_arquivo_atomico

__all__ = [
    "LeitorPacoteZip",
    "ComparadorPacotesConjuntos",
    "DescompiladorCFR",
    "MotorDiff",
    "ExportadorJSON",
    "ExportadorMarkdown",
    "ExportadorHTML",
    "escrever_arquivo_atomico",
]
