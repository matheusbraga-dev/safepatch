"""Casos de uso para orquestração da auditoria de pacotes."""

from pathlib import Path
from typing import Callable, Optional

from safepatch.application.dtos import ParametrosComparacao
from safepatch.domain.modelos import RelatorioComparacao
from safepatch.domain.protocolos import (
    ProtocoloComparador,
    ProtocoloExportador,
    ProtocoloLeitor,
)
from safepatch.infrastructure.comparacao.comparador_conjuntos import ComparadorPacotesConjuntos
from safepatch.infrastructure.exportadores.exportador_html import ExportadorHTML
from safepatch.infrastructure.exportadores.exportador_json import ExportadorJSON
from safepatch.infrastructure.exportadores.exportador_markdown import ExportadorMarkdown
from safepatch.infrastructure.leitores.leitor_universal import LeitorPacoteUniversal


class CompararPacotesCasoDeUso:
    """Orquestra a leitura, confronto, enriquecimento e exportação de pacotes e diretórios."""

    def __init__(
        self,
        leitor: Optional[ProtocoloLeitor] = None,
        comparador_factory: Optional[Callable[..., ProtocoloComparador]] = None,
        exportador_json: Optional[ProtocoloExportador] = None,
        exportador_md: Optional[ProtocoloExportador] = None,
        exportador_html: Optional[ProtocoloExportador] = None,
        notificador: Optional[Callable[[str], None]] = None,
    ):
        self.leitor = leitor or LeitorPacoteUniversal()
        self.comparador_factory = comparador_factory or (
            lambda ignorar, filtro: ComparadorPacotesConjuntos(
                padroes_ignorar=ignorar, padroes_filtro=filtro
            )
        )
        self.exportador_json = exportador_json or ExportadorJSON()
        self.exportador_md = exportador_md or ExportadorMarkdown()
        self.exportador_html = exportador_html or ExportadorHTML()
        self.notificador = notificador or (lambda msg: None)

    def executar(self, parametros: ParametrosComparacao) -> RelatorioComparacao:
        """Executa o ciclo completo de ingestão, comparação e exportação condicional."""
        base_path = Path(parametros.caminho_base)
        alvo_path = Path(parametros.caminho_alvo)

        # 1. Ingestão da base
        self.notificador(f"Lendo pacote base: {base_path.name}...")
        inventario_base = self.leitor.mapear(base_path)

        # 2. Ingestão do alvo
        self.notificador(f"Lendo pacote alvo: {alvo_path.name}...")
        inventario_alvo = self.leitor.mapear(alvo_path)

        # 3. Comparação de inventários
        self.notificador("Analisando diferenças e detectando conflitos...")
        try:
            comparador = self.comparador_factory(
                tuple(parametros.padroes_ignorar), tuple(parametros.padroes_filtro)
            )
        except TypeError:
            comparador = self.comparador_factory(tuple(parametros.padroes_ignorar))
        relatorio = comparador.comparar(
            nome_base=base_path.name,
            inventario_base=inventario_base,
            nome_alvo=alvo_path.name,
            inventario_alvo=inventario_alvo,
        )

        # 4. Exportações condicionais
        if parametros.caminho_json:
            self.exportador_json.exportar(
                relatorio,
                caminho_arquivo=parametros.caminho_json,
                incluir_diff=parametros.incluir_diff,
                caminho_base=base_path,
                caminho_alvo=alvo_path,
            )
            self.notificador(f"[OK] Relatório JSON exportado para: {parametros.caminho_json}")

        if parametros.caminho_md:
            self.exportador_md.exportar(
                relatorio,
                caminho_arquivo=parametros.caminho_md,
                incluir_diff=parametros.incluir_diff,
                caminho_base=base_path,
                caminho_alvo=alvo_path,
            )
            self.notificador(f"[OK] Relatório Markdown exportado para: {parametros.caminho_md}")

        if parametros.caminho_html:
            self.exportador_html.exportar(
                relatorio,
                caminho_arquivo=parametros.caminho_html,
                incluir_diff=parametros.incluir_diff,
                caminho_base=base_path,
                caminho_alvo=alvo_path,
            )
            self.notificador(f"[OK] Relatório HTML exportado para: {parametros.caminho_html}")

        return relatorio
