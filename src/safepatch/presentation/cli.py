"""Interface de linha de comando (CLI) do SafePatch."""

import argparse
import io
import sys
from typing import Optional, Sequence

from safepatch import __version__
from safepatch.application.casos_de_uso import CompararPacotesCasoDeUso
from safepatch.application.dtos import ParametrosComparacao
from safepatch.domain.excecoes import PacoteInvalidoError, SafePatchError
from safepatch.presentation.console import RenderizadorConsole


def criar_parser() -> argparse.ArgumentParser:
    """Cria e configura o analisador de argumentos da CLI."""
    parser = argparse.ArgumentParser(
        prog="safepatch",
        description="SafePatch: Plataforma de Auditoria e Comparação de Pacotes (.jar, .war, .zip)",
    )

    # Versão
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Exibe a versão do SafePatch e encerra",
    )

    # Argumentos obrigatórios
    parser.add_argument(
        "--base",
        required=True,
        help="Caminho para o pacote base (ex: cliente_v1.jar)",
    )
    parser.add_argument(
        "--alvo",
        required=True,
        help="Caminho para o pacote alvo (ex: pacote_atualizacao.jar)",
    )

    # Filtros e visualização
    parser.add_argument(
        "-i",
        "--ignorar",
        action="append",
        default=[],
        help="Padrão glob de arquivos a ignorar (ex: 'META-INF/*' ou '*.md'). Pode ser repetido.",
    )
    parser.add_argument(
        "-d",
        "--diff",
        action="store_true",
        help="Mostra a diferença detalhada (diff descompilado estilo git) do conteúdo dos arquivos",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Exibe todos os arquivos no console sem limite de amostragem",
    )
    parser.add_argument(
        "--limite",
        type=int,
        default=10,
        help="Limite de arquivos exibidos por categoria no console (padrão: 10)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Desativa a coloração ANSI na saída do terminal",
    )

    # Exportação de relatórios
    parser.add_argument(
        "--json",
        dest="caminho_json",
        help="Caminho para exportar relatório estruturado em JSON",
    )
    parser.add_argument(
        "--markdown",
        "--md",
        dest="caminho_md",
        help="Caminho para exportar relatório em Markdown",
    )
    parser.add_argument(
        "--html",
        dest="caminho_html",
        help="Caminho para exportar relatório visual em HTML",
    )

    # CI/CD
    parser.add_argument(
        "--fail-on-conflict",
        action="store_true",
        help="Encerra com código de saída 2 se houver arquivos modificados (conflitos)",
    )

    return parser


def executar_cli(argv: Optional[Sequence[str]] = None) -> int:
    """Executa o ciclo da CLI e retorna o código de saída apropriado (0, 1 ou 2)."""
    parser = criar_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as err:
        return err.code if isinstance(err.code, int) else 0

    print("Iniciando varredura dos pacotes...")

    parametros = ParametrosComparacao(
        caminho_base=args.base,
        caminho_alvo=args.alvo,
        padroes_ignorar=args.ignorar,
        incluir_diff=args.diff,
        caminho_json=args.caminho_json,
        caminho_md=args.caminho_md,
        caminho_html=args.caminho_html,
    )

    caso_de_uso = CompararPacotesCasoDeUso(notificador=print)

    try:
        relatorio = caso_de_uso.executar(parametros)
    except PacoteInvalidoError as err:
        print(f"Erro: {err}")
        return 1
    except SafePatchError as err:
        print(f"Erro operacional: {err}")
        return 1
    except Exception as err:
        print(f"Erro inesperado: {err}")
        return 1

    # Renderiza o resultado no console
    renderizador = RenderizadorConsole(
        usar_cores=not args.no_color,
        limite=args.limite,
        verbose=args.verbose,
        mostrar_diff=args.diff,
        caminho_base=args.base,
        caminho_alvo=args.alvo,
    )
    renderizador.renderizar(relatorio)

    # Código de saída para CI/CD
    if args.fail_on_conflict and relatorio.tem_conflitos:
        print(f"\n[FALHA CI/CD] {relatorio.total_modificados} conflito(s) detectado(s).")
        return 2

    return 0


def main() -> None:
    """Ponto de entrada oficial da linha de comando."""
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, io.UnsupportedOperation):
            pass

    codigo_saida = executar_cli()
    sys.exit(codigo_saida)


if __name__ == "__main__":
    main()
