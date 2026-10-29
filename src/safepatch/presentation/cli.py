import argparse
import io
import json
import sys
from typing import Optional, Sequence

from safepatch import __version__
from safepatch.application.casos_de_uso import CompararPacotesCasoDeUso
from safepatch.application.dtos import ParametrosComparacao
from safepatch.domain.excecoes import PacoteInvalidoError, SafePatchError
from safepatch.infrastructure.sistema_arquivos.escritor_atomico import escrever_arquivo_atomico
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

    # Argumentos de comparação
    parser.add_argument(
        "--base",
        required=False,
        help="Caminho para o pacote, diretório ou código-fonte base (ex: cliente.jar, pasta ou User.java)",
    )
    parser.add_argument(
        "--alvo",
        required=False,
        help="Caminho para o pacote, diretório ou código-fonte alvo (ex: src/main/java, pasta ou User.java)",
    )

    # Filtros e visualização
    parser.add_argument(
        "-f",
        "--filtro",
        action="append",
        default=[],
        help="Padrão glob de arquivos ou classes a incluir na análise (ex: '*UserDTO*' ou 'com/exemplo/*'). Pode ser repetido.",
    )
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
        "--diff-arquivo",
        "--diff-file",
        dest="diff_arquivo",
        help="Gera o diff sob demanda exclusivamente para o arquivo especificado (útil para inspeção em GUIs)",
    )
    parser.add_argument(
        "-s",
        "--silencioso",
        "--quiet",
        "-q",
        action="store_true",
        dest="silencioso",
        help="Suprime mensagens informativas e de progresso no terminal",
    )
    parser.add_argument(
        "--eventos-progresso",
        "--progress-events",
        action="store_true",
        dest="eventos_progresso",
        help="Emite eventos de progresso em formato NDJSON no stderr para integração em tempo real com GUIs",
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
        help="Caminho para exportar relatório estruturado em JSON (use '-' para stdout)",
    )
    parser.add_argument(
        "--json-stdout",
        action="store_true",
        dest="json_stdout",
        help="Exporta o relatório estruturado em JSON diretamente para stdout",
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

    # Conexão remota SSH/SFTP
    parser.add_argument(
        "--chave-ssh",
        "--ssh-key",
        dest="chave_ssh",
        help="Caminho para o arquivo de chave privada SSH (ex: ~/.ssh/id_rsa)",
    )
    parser.add_argument(
        "--porta-ssh",
        "--ssh-port",
        type=int,
        dest="porta_ssh",
        help="Porta do servidor SSH remoto (padrão: 22)",
    )
    parser.add_argument(
        "--senha-ssh",
        "--ssh-password",
        dest="senha_ssh",
        help="Senha para autenticação no servidor SSH (se aplicável)",
    )
    parser.add_argument(
        "--salvar-copia-local",
        "--dir-backup",
        dest="dir_copia_local",
        help="Diretório local para armazenar uma cópia inalterada (backup) do arquivo remoto baixado",
    )

    # Exploração remota e publicação reversa (Passos 2 e 6)
    parser.add_argument(
        "--listar-remoto",
        "--list-remote",
        dest="listar_remoto",
        help="Lista os arquivos e subdiretórios no servidor remoto SSH (suporta saída tabular ou JSON)",
    )
    parser.add_argument(
        "--navegar-remoto",
        "--browse-remote",
        dest="navegar_remoto",
        help="Abre navegação interativa pelo teclado no terminal para selecionar pacote remoto",
    )
    parser.add_argument(
        "--publicar",
        "--deploy",
        nargs=2,
        metavar=("ARQUIVO_LOCAL", "DESTINO_REMOTO"),
        dest="publicar",
        help="Publica o pacote aprovado no servidor remoto com backup automático e validação SHA-256",
    )
    parser.add_argument(
        "--sem-backup",
        "--no-backup",
        action="store_true",
        dest="sem_backup",
        help="Desativa a criação de arquivo de backup (.bak) antes da substituição remota",
    )
    parser.add_argument(
        "--sem-verificacao",
        "--no-verify",
        action="store_true",
        dest="sem_verificacao",
        help="Desativa a verificação de integridade pós-deploy por SHA-256",
    )

    # Auditoria de logs e compliance (Passo 7)
    parser.add_argument(
        "--sem-auditoria",
        "--no-audit",
        action="store_true",
        dest="sem_auditoria",
        help="Desativa a gravação automática no log de auditoria",
    )
    parser.add_argument(
        "--arquivo-auditoria",
        "--audit-file",
        dest="arquivo_auditoria",
        help="Caminho personalizado para o arquivo oculto de auditoria",
    )
    parser.add_argument(
        "--listar-auditoria",
        "--list-audit",
        action="store_true",
        dest="listar_auditoria",
        help="Exibe os registros recentes gravados no arquivo de auditoria",
    )

    return parser


def executar_cli(argv: Optional[Sequence[str]] = None) -> int:
    """Executa o ciclo da CLI e retorna o código de saída apropriado (0, 1 ou 2)."""
    parser = criar_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as err:
        return err.code if isinstance(err.code, int) else 0

    eh_stdout_json = args.json_stdout or (args.caminho_json and str(args.caminho_json).strip() == "-")

    # Configuração do canal de notificação textual
    if args.silencioso:
        notificador_texto = lambda msg: None
    elif eh_stdout_json:
        notificador_texto = lambda msg: sys.stderr.write(msg + "\n")
    else:
        notificador_texto = print

    # Configuração de streaming de eventos de progresso (NDJSON no stderr)
    if args.eventos_progresso:
        def notificar_evento(evento: dict) -> None:
            sys.stderr.write(json.dumps(evento, ensure_ascii=False) + "\n")
            sys.stderr.flush()
    else:
        notificar_evento = lambda evt: None

    # 1. Modo de Consulta ao Histórico de Auditoria
    if args.listar_auditoria:
        from safepatch.infrastructure.auditoria.gravador_auditoria import GravadorAuditoriaJSONL
        gravador = GravadorAuditoriaJSONL(caminho_arquivo=args.arquivo_auditoria)
        historico = gravador.ler_historico(limite=args.limite or 50)
        if eh_stdout_json:
            sys.stdout.write(json.dumps(historico, indent=2, ensure_ascii=False) + "\n")
        else:
            if not historico:
                print("Nenhum registro de auditoria encontrado.")
            else:
                print(f"=== HISTÓRICO DE AUDITORIA ({len(historico)} registros) ===")
                for reg in historico:
                    status = "OK" if reg.get("sucesso") else "FALHA"
                    print(f"[{reg.get('timestamp')}] {reg.get('usuario')}@{reg.get('maquina')} - {reg.get('operacao').upper()} ({status})")
                    detalhes = reg.get("detalhes", {})
                    if "pacote_base" in detalhes:
                        print(f"    Base: {detalhes['pacote_base']} | Alvo: {detalhes.get('pacote_alvo')}")
                    if "total_modificados" in detalhes:
                        print(f"    Modificados: {detalhes['total_modificados']} | Conflitos: {detalhes.get('tem_conflitos')}")
                    if "origem_local" in detalhes:
                        print(f"    Origem: {detalhes['origem_local']} -> Remoto: {detalhes.get('destino_remoto')}")
        return 0

    # 2. Modo de Exploração de Diretório Remoto SSH
    if args.listar_remoto:
        from safepatch.infrastructure.remoto.resolvedor_ssh import ResolvedorCaminhoRemoto
        from safepatch.presentation.navegador_cli import NavegadorRemotoTerminal

        resolvedor = ResolvedorCaminhoRemoto(
            notificador=notificador_texto,
            notificador_evento=notificar_evento,
        )
        try:
            itens = resolvedor.listar_remoto(
                destino_uri=args.listar_remoto,
                chave_ssh=args.chave_ssh,
                porta_ssh=args.porta_ssh,
                senha_ssh=args.senha_ssh,
            )
            if eh_stdout_json:
                resultado = {
                    "status": "sucesso",
                    "destino": args.listar_remoto,
                    "total": len(itens),
                    "itens": [item.to_dict() for item in itens],
                }
                sys.stdout.write(json.dumps(resultado, indent=2, ensure_ascii=False) + "\n")
            else:
                navegador = NavegadorRemotoTerminal(resolvedor)
                navegador.exibir_listagem(
                    destino_uri=args.listar_remoto,
                    chave_ssh=args.chave_ssh,
                    porta_ssh=args.porta_ssh,
                    senha_ssh=args.senha_ssh,
                )
            return 0
        except Exception as err:
            if eh_stdout_json:
                sys.stdout.write(
                    json.dumps(
                        {"status": "erro", "tipo": type(err).__name__, "mensagem": str(err)},
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            else:
                print(f"Erro ao listar destino remoto: {err}")
            return 1

    # 3. Modo de Navegação Interativa no Terminal
    if args.navegar_remoto:
        from safepatch.infrastructure.remoto.resolvedor_ssh import ResolvedorCaminhoRemoto
        from safepatch.presentation.navegador_cli import NavegadorRemotoTerminal

        resolvedor = ResolvedorCaminhoRemoto(
            notificador=notificador_texto,
            notificador_evento=notificar_evento,
        )
        navegador = NavegadorRemotoTerminal(resolvedor)
        try:
            selecionado = navegador.navegar_interativo(
                destino_uri=args.navegar_remoto,
                chave_ssh=args.chave_ssh,
                porta_ssh=args.porta_ssh,
                senha_ssh=args.senha_ssh,
            )
            if selecionado:
                if eh_stdout_json:
                    sys.stdout.write(
                        json.dumps({"status": "sucesso", "selecionado": selecionado}, ensure_ascii=False)
                        + "\n"
                    )
            return 0
        except Exception as err:
            print(f"Erro na navegação remota: {err}")
            return 1

    # 4. Modo de Publicação / Deploy Reverso Seguro (Passo 6)
    if args.publicar:
        from safepatch.infrastructure.auditoria.gravador_auditoria import GravadorAuditoriaJSONL
        from safepatch.infrastructure.remoto.resolvedor_ssh import ResolvedorCaminhoRemoto

        arquivo_local, destino_remoto = args.publicar[0], args.publicar[1]
        auditor = None
        if not args.sem_auditoria:
            auditor = GravadorAuditoriaJSONL(caminho_arquivo=args.arquivo_auditoria)

        resolvedor = ResolvedorCaminhoRemoto(
            notificador=notificador_texto,
            notificador_evento=notificar_evento,
        )
        try:
            resultado_deploy = resolvedor.publicar_remoto(
                caminho_origem_local=arquivo_local,
                destino_uri=destino_remoto,
                chave_ssh=args.chave_ssh,
                porta_ssh=args.porta_ssh,
                senha_ssh=args.senha_ssh,
                criar_backup=not args.sem_backup,
                verificar_integridade=not args.sem_verificacao,
                auditor=auditor,
            )
            if eh_stdout_json:
                sys.stdout.write(json.dumps(resultado_deploy, indent=2, ensure_ascii=False) + "\n")
            else:
                print("\n[OK] Publicação remota concluída com sucesso!")
                print(f"    Origem:   {resultado_deploy['origem_local']}")
                print(f"    Destino:  {resultado_deploy['destino_remoto']}")
                if resultado_deploy.get("backup_remoto"):
                    print(f"    Backup:   {resultado_deploy['backup_remoto']}")
                print(f"    SHA-256:  {resultado_deploy['sha256']}")
            return 0
        except Exception as err:
            if eh_stdout_json:
                sys.stdout.write(
                    json.dumps(
                        {"status": "erro", "tipo": type(err).__name__, "mensagem": str(err)},
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            else:
                print(f"Erro na publicação remota: {err}")
            return 1

    # Validação dos caminhos obrigatórios quando não for nenhum modo especial
    if not args.base or not args.alvo:
        try:
            parser.error("os seguintes argumentos são obrigatórios: --base, --alvo")
        except SystemExit as err:
            return err.code if isinstance(err.code, int) else 2

    caso_de_uso = CompararPacotesCasoDeUso(
        notificador=notificador_texto,
        notificador_evento=notificar_evento,
    )

    # 2. Modo Diff Sob Demanda para Arquivo Único
    if args.diff_arquivo:
        try:
            resultado_diff = caso_de_uso.obter_diff_arquivo(
                caminho_base=args.base,
                caminho_alvo=args.alvo,
                caminho_interno=args.diff_arquivo,
                chave_ssh=args.chave_ssh,
                porta_ssh=args.porta_ssh,
                senha_ssh=args.senha_ssh,
                desativar_auditoria=args.sem_auditoria,
            )
        except SafePatchError as err:
            if eh_stdout_json:
                sys.stdout.write(
                    json.dumps(
                        {"status": "erro", "tipo": type(err).__name__, "mensagem": str(err)},
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            else:
                print(f"Erro: {err}")
            return 1
        except Exception as err:
            if eh_stdout_json:
                sys.stdout.write(
                    json.dumps(
                        {"status": "erro", "tipo": "ErroInesperado", "mensagem": str(err)},
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            else:
                print(f"Erro inesperado: {err}")
            return 1

        if eh_stdout_json:
            sys.stdout.write(json.dumps(resultado_diff, indent=2, ensure_ascii=False) + "\n")
            return 0
        elif args.caminho_json:
            escrever_arquivo_atomico(args.caminho_json, json.dumps(resultado_diff, indent=2, ensure_ascii=False))
            notificador_texto(f"[OK] Diff exportado para: {args.caminho_json}")
            return 0
        else:
            if resultado_diff["status"] == "inalterado":
                print(f"Arquivo '{resultado_diff['caminho']}' está inalterado.")
            else:
                from safepatch.shared.formatacao import formatar_diff_colorido
                is_tty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty() and not args.no_color
                for linha in resultado_diff["linhas"]:
                    print(formatar_diff_colorido(linha) if is_tty else linha, end="")
            return 0

    # 3. Modo Comparação Completa de Pacotes
    caminho_json_efetivo = "-" if args.json_stdout else args.caminho_json
    parametros = ParametrosComparacao(
        caminho_base=args.base,
        caminho_alvo=args.alvo,
        padroes_ignorar=args.ignorar,
        padroes_filtro=args.filtro,
        incluir_diff=args.diff,
        caminho_json=caminho_json_efetivo,
        caminho_md=args.caminho_md,
        caminho_html=args.caminho_html,
        diff_arquivo=None,
        chave_ssh=args.chave_ssh,
        porta_ssh=args.porta_ssh,
        senha_ssh=args.senha_ssh,
        dir_copia_local=args.dir_copia_local,
        desativar_auditoria=args.sem_auditoria,
        caminho_auditoria=args.arquivo_auditoria,
    )

    try:
        relatorio = caso_de_uso.executar(parametros)
    except PacoteInvalidoError as err:
        if eh_stdout_json:
            sys.stdout.write(
                json.dumps(
                    {"status": "erro", "tipo": type(err).__name__, "mensagem": str(err)},
                    ensure_ascii=False,
                )
                + "\n"
            )
        else:
            print(f"Erro: {err}")
        return 1
    except SafePatchError as err:
        if eh_stdout_json:
            sys.stdout.write(
                json.dumps(
                    {"status": "erro", "tipo": type(err).__name__, "mensagem": str(err)},
                    ensure_ascii=False,
                )
                + "\n"
            )
        else:
            print(f"Erro operacional: {err}")
        return 1
    except Exception as err:
        if eh_stdout_json:
            sys.stdout.write(
                json.dumps(
                    {"status": "erro", "tipo": "ErroInesperado", "mensagem": str(err)},
                    ensure_ascii=False,
                )
                + "\n"
            )
        else:
            print(f"Erro inesperado: {err}")
        return 1

    # Renderiza o resultado no console se não estiver em modo JSON stdout
    if not eh_stdout_json and not args.silencioso:
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
        if not eh_stdout_json and not args.silencioso:
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
