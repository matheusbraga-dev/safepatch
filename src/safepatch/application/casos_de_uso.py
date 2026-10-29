"""Casos de uso para orquestração da auditoria de pacotes."""

from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union

from safepatch.application.dtos import ParametrosComparacao
from safepatch.domain.excecoes import ArquivoNaoEncontradoError
from safepatch.domain.modelos import RelatorioComparacao
from safepatch.domain.protocolos import (
    ProtocoloAuditoria,
    ProtocoloComparador,
    ProtocoloDiferenciador,
    ProtocoloExportador,
    ProtocoloLeitor,
)
from safepatch.infrastructure.auditoria.gravador_auditoria import GravadorAuditoriaJSONL
from safepatch.infrastructure.comparacao.comparador_conjuntos import ComparadorPacotesConjuntos
from safepatch.infrastructure.diff.motor_diff import MotorDiff
from safepatch.infrastructure.exportadores.exportador_html import ExportadorHTML
from safepatch.infrastructure.exportadores.exportador_json import ExportadorJSON
from safepatch.infrastructure.exportadores.exportador_markdown import ExportadorMarkdown
from safepatch.infrastructure.leitores.leitor_universal import LeitorPacoteUniversal
from safepatch.infrastructure.remoto.resolvedor_ssh import ResolvedorCaminhoRemoto

CaminhoPath = Union[str, Path]


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
        notificador_evento: Optional[Callable[[Dict[str, Any]], None]] = None,
        motor_diff: Optional[ProtocoloDiferenciador] = None,
        resolvedor_remoto: Optional[ResolvedorCaminhoRemoto] = None,
        auditor: Optional[ProtocoloAuditoria] = None,
        desativar_auditoria: bool = False,
    ):
        self.leitor = leitor or LeitorPacoteUniversal()
        self.motor_diff = motor_diff or MotorDiff()
        self.comparador_factory = comparador_factory or (
            lambda ignorar, filtro: ComparadorPacotesConjuntos(
                padroes_ignorar=ignorar,
                padroes_filtro=filtro,
                diferenciador=self.motor_diff,
            )
        )
        self.exportador_json = exportador_json or ExportadorJSON(diferenciador=self.motor_diff)
        self.exportador_md = exportador_md or ExportadorMarkdown()
        self.exportador_html = exportador_html or ExportadorHTML()
        self.notificador = notificador or (lambda msg: None)
        self.notificador_evento = notificador_evento or (lambda evt: None)
        self.resolvedor_remoto = resolvedor_remoto or ResolvedorCaminhoRemoto(
            notificador=self.notificador,
            notificador_evento=self.notificador_evento,
        )
        self.auditor = auditor if auditor is not None else (None if desativar_auditoria else GravadorAuditoriaJSONL())

    def _notificar_etapa(self, etapa: str, percentual: float, mensagem: str) -> None:
        """Emite notificação de texto e evento estruturado para a GUI."""
        self.notificador(mensagem)
        self.notificador_evento({
            "evento": "progresso",
            "etapa": etapa,
            "percentual": percentual,
            "mensagem": mensagem,
        })

    def executar(self, parametros: ParametrosComparacao) -> RelatorioComparacao:
        """Executa o ciclo completo de ingestão, comparação e exportação condicional."""
        auditor = None
        if not parametros.desativar_auditoria:
            if parametros.caminho_auditoria:
                auditor = GravadorAuditoriaJSONL(parametros.caminho_auditoria)
            else:
                auditor = self.auditor

        try:
            with self.resolvedor_remoto as resolvedor:
                base_path = resolvedor.resolver(
                    caminho=parametros.caminho_base,
                    chave_ssh=parametros.chave_ssh,
                    porta_ssh=parametros.porta_ssh,
                    senha_ssh=parametros.senha_ssh,
                    dir_copia_local=parametros.dir_copia_local,
                )
                alvo_path = resolvedor.resolver(
                    caminho=parametros.caminho_alvo,
                    chave_ssh=parametros.chave_ssh,
                    porta_ssh=parametros.porta_ssh,
                    senha_ssh=parametros.senha_ssh,
                )

                self._notificar_etapa("inicio", 0.0, "Iniciando varredura dos pacotes...")

                # 1. Ingestão da base
                self._notificar_etapa("leitura_base", 20.0, f"Lendo pacote base: {base_path.name}...")
                inventario_base = self.leitor.mapear(base_path)

                # 2. Ingestão do alvo
                self._notificar_etapa("leitura_alvo", 50.0, f"Lendo pacote alvo: {alvo_path.name}...")
                inventario_alvo = self.leitor.mapear(alvo_path)

                # 3. Comparação de inventários
                self._notificar_etapa("comparacao", 75.0, "Analisando diferenças e detectando conflitos...")
                try:
                    comparador = self.comparador_factory(
                        tuple(parametros.padroes_ignorar), tuple(parametros.padroes_filtro)
                    )
                except TypeError:
                    comparador = self.comparador_factory(tuple(parametros.padroes_ignorar))

                try:
                    relatorio = comparador.comparar(
                        nome_base=base_path.name,
                        inventario_base=inventario_base,
                        nome_alvo=alvo_path.name,
                        inventario_alvo=inventario_alvo,
                        caminho_base=base_path,
                        caminho_alvo=alvo_path,
                    )
                except TypeError:
                    relatorio = comparador.comparar(
                        nome_base=base_path.name,
                        inventario_base=inventario_base,
                        nome_alvo=alvo_path.name,
                        inventario_alvo=inventario_alvo,
                    )

                # 4. Exportações condicionais
                if parametros.caminho_json or parametros.caminho_md or parametros.caminho_html:
                    self._notificar_etapa("exportacao", 90.0, "Exportando relatórios...")

                if parametros.caminho_json:
                    self.exportador_json.exportar(
                        relatorio,
                        caminho_arquivo=parametros.caminho_json,
                        incluir_diff=parametros.incluir_diff,
                        caminho_base=base_path,
                        caminho_alvo=alvo_path,
                    )
                    if str(parametros.caminho_json).strip() != "-":
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

                self._notificar_etapa("concluido", 100.0, "Comparação concluída com sucesso.")

                if auditor:
                    auditor.registrar(
                        operacao="comparacao",
                        detalhes={
                            "pacote_base": str(parametros.caminho_base),
                            "pacote_alvo": str(parametros.caminho_alvo),
                            "total_modificados": relatorio.total_modificados,
                            "total_adicionados": relatorio.total_adicionados,
                            "total_removidos": relatorio.total_removidos,
                            "total_inalterados": relatorio.total_inalterados,
                            "arquivos_modificados": [m.caminho for m in relatorio.modificados],
                            "tem_conflitos": relatorio.tem_conflitos,
                        },
                        sucesso=True,
                    )

                return relatorio
        except Exception as err:
            if auditor:
                auditor.registrar(
                    operacao="comparacao",
                    detalhes={
                        "pacote_base": str(parametros.caminho_base),
                        "pacote_alvo": str(parametros.caminho_alvo),
                    },
                    sucesso=False,
                    erro=str(err),
                )
            raise

    def obter_diff_arquivo(
        self,
        caminho_base: CaminhoPath,
        caminho_alvo: CaminhoPath,
        caminho_interno: str,
        chave_ssh: Optional[str] = None,
        porta_ssh: Optional[int] = None,
        senha_ssh: Optional[str] = None,
        desativar_auditoria: bool = False,
    ) -> Dict[str, Any]:
        """Obtém o diff sob demanda para um arquivo individual (útil para inspeção em GUIs)."""
        auditor = self.auditor if not desativar_auditoria else None

        try:
            with self.resolvedor_remoto as resolvedor:
                base_path = resolvedor.resolver(
                    caminho=caminho_base,
                    chave_ssh=chave_ssh,
                    porta_ssh=porta_ssh,
                    senha_ssh=senha_ssh,
                )
                alvo_path = resolvedor.resolver(
                    caminho=caminho_alvo,
                    chave_ssh=chave_ssh,
                    porta_ssh=porta_ssh,
                    senha_ssh=senha_ssh,
                )

                self._notificar_etapa("inicio_diff", 10.0, f"Obtendo inventários para inspecionar '{caminho_interno}'...")
                inventario_base = self.leitor.mapear(base_path)
                inventario_alvo = self.leitor.mapear(alvo_path)

                caminho_normalizado = caminho_interno.replace("\\", "/").lstrip("/")

                # Verifica se caminho existe exatamente ou se requer resolução
                candidato_base = caminho_normalizado if caminho_normalizado in inventario_base else None
                candidato_alvo = caminho_normalizado if caminho_normalizado in inventario_alvo else None

                if not candidato_base and not candidato_alvo:
                    # Busca tolerante a case ou sufixo
                    for k in inventario_base:
                        if k.lower() == caminho_normalizado.lower() or k.endswith("/" + caminho_normalizado):
                            candidato_base = k
                            break
                    for k in inventario_alvo:
                        if k.lower() == caminho_normalizado.lower() or k.endswith("/" + caminho_normalizado):
                            candidato_alvo = k
                            break

                if not candidato_base and not candidato_alvo:
                    raise ArquivoNaoEncontradoError(
                        f"O arquivo '{caminho_interno}' não foi encontrado no pacote base nem no pacote alvo."
                    )

                caminho_resolvido = candidato_base or candidato_alvo
                self._notificar_etapa("descompilando", 50.0, f"Gerando diff para '{caminho_resolvido}'...")

                if candidato_base and candidato_alvo:
                    arq_base = inventario_base[candidato_base]
                    arq_alvo = inventario_alvo[candidato_alvo]
                    if arq_base.hash_sha256 == arq_alvo.hash_sha256:
                        resultado = {
                            "caminho": caminho_resolvido,
                            "status": "inalterado",
                            "diff": "",
                            "linhas": [],
                        }
                    else:
                        linhas = self.motor_diff.diff_modificado(base_path, alvo_path, caminho_resolvido)
                        resultado = {
                            "caminho": caminho_resolvido,
                            "status": "modificado",
                            "diff": "".join(linhas),
                            "linhas": linhas,
                        }
                elif candidato_alvo:
                    linhas = self.motor_diff.diff_adicionado(alvo_path, caminho_resolvido)
                    resultado = {
                        "caminho": caminho_resolvido,
                        "status": "adicionado",
                        "diff": "".join(linhas),
                        "linhas": linhas,
                    }
                else:
                    linhas = self.motor_diff.diff_removido(base_path, caminho_resolvido)
                    resultado = {
                        "caminho": caminho_resolvido,
                        "status": "removido",
                        "diff": "".join(linhas),
                        "linhas": linhas,
                    }

                self._notificar_etapa("concluido_diff", 100.0, f"Diff gerado para '{caminho_resolvido}'.")

                if auditor:
                    auditor.registrar(
                        operacao="diff_arquivo",
                        detalhes={
                            "pacote_base": str(caminho_base),
                            "pacote_alvo": str(caminho_alvo),
                            "caminho_interno": caminho_resolvido,
                            "status": resultado["status"],
                        },
                        sucesso=True,
                    )

                return resultado
        except Exception as err:
            if auditor:
                auditor.registrar(
                    operacao="diff_arquivo",
                    detalhes={
                        "pacote_base": str(caminho_base),
                        "pacote_alvo": str(caminho_alvo),
                        "caminho_interno": caminho_interno,
                    },
                    sucesso=False,
                    erro=str(err),
                )
            raise
