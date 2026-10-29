"""Testes de integração para a camada de aplicação (CompararPacotesCasoDeUso)."""

import tempfile
import unittest
from pathlib import Path
from tests.helpers import SAMPLE_ALVO, SAMPLE_BASE, SRC_PATH

from safepatch.application.casos_de_uso import CompararPacotesCasoDeUso
from safepatch.application.dtos import ParametrosComparacao


class TestCompararPacotesCasoDeUso(unittest.TestCase):
    def test_execucao_completa_com_pacotes_reais(self):
        mensagens = []
        caso_de_uso = CompararPacotesCasoDeUso(notificador=mensagens.append)

        with tempfile.TemporaryDirectory() as tmp_dir:
            caminho_json = Path(tmp_dir) / "relatorio.json"
            caminho_md = Path(tmp_dir) / "relatorio.md"
            caminho_html = Path(tmp_dir) / "relatorio.html"

            parametros = ParametrosComparacao(
                caminho_base=SAMPLE_BASE,
                caminho_alvo=SAMPLE_ALVO,
                padroes_ignorar=("*.md",),
                incluir_diff=True,
                caminho_json=caminho_json,
                caminho_md=caminho_md,
                caminho_html=caminho_html,
            )

            relatorio = caso_de_uso.executar(parametros)

            self.assertEqual(relatorio.total_modificados, 1)
            self.assertEqual(relatorio.total_adicionados, 0)
            self.assertEqual(relatorio.total_removidos, 0)
            self.assertEqual(relatorio.total_inalterados, 7)

            # Verifica se os arquivos foram exportados
            self.assertTrue(caminho_json.exists())
            self.assertTrue(caminho_md.exists())
            self.assertTrue(caminho_html.exists())

            # Verifica mensagens de notificação
            self.assertTrue(any("Lendo pacote base" in m for m in mensagens))
            self.assertTrue(any("Lendo pacote alvo" in m for m in mensagens))
            self.assertTrue(any("exportado para" in m for m in mensagens))

    def test_execucao_jar_contra_workspace_fonte_java(self):
        caso_de_uso = CompararPacotesCasoDeUso()

        with tempfile.TemporaryDirectory() as tmp_dir:
            dir_workspace = Path(tmp_dir) / "meu_projeto"
            dir_java = dir_workspace / "src" / "main" / "java" / "com" / "example" / "dto"
            dir_java.mkdir(parents=True)

            # UserDTO modificado
            (dir_java / "UserDTO.java").write_text(
                "package com.example.dto;\n\n"
                "public class UserDTO {\n"
                "    private Long id;\n"
                "    public String campoCustom() { return \"custom\"; }\n"
                "}\n",
                encoding="utf-8",
            )

            # Nova classe adicionada no workspace
            (dir_java / "NovoDTO.java").write_text(
                "package com.example.dto;\n\n"
                "public class NovoDTO {}\n",
                encoding="utf-8",
            )

            parametros = ParametrosComparacao(
                caminho_base=SAMPLE_BASE,
                caminho_alvo=dir_workspace,
                padroes_filtro=("*DTO*",),
                incluir_diff=True,
            )

            relatorio = caso_de_uso.executar(parametros)

            # UserDTO.class deve ser modificado
            self.assertEqual(relatorio.total_modificados, 1)
            self.assertEqual(relatorio.modificados[0].caminho, "com/example/dto/UserDTO.class")

            # NovoDTO.class deve ser adicionado
            self.assertEqual(relatorio.total_adicionados, 1)
            self.assertEqual(relatorio.adicionados[0].caminho, "com/example/dto/NovoDTO.class")

    def test_execucao_com_pacote_remoto_ssh(self):
        from unittest.mock import MagicMock
        from safepatch.infrastructure.remoto.resolvedor_ssh import ResolvedorCaminhoRemoto

        transporte_mock = MagicMock()
        def simular_download(destino, caminho_destino_local, notificador_progresso=None):
            caminho_destino_local.write_bytes(SAMPLE_BASE.read_bytes())
            return caminho_destino_local

        transporte_mock.baixar_arquivo.side_effect = simular_download

        resolvedor = ResolvedorCaminhoRemoto(transporte=transporte_mock)
        caso_de_uso = CompararPacotesCasoDeUso(resolvedor_remoto=resolvedor)

        with tempfile.TemporaryDirectory() as dir_backup:
            parametros = ParametrosComparacao(
                caminho_base="deploy@servidor.cliente.com:/opt/producao/app.jar",
                caminho_alvo=SAMPLE_ALVO,
                dir_copia_local=dir_backup,
            )

            relatorio = caso_de_uso.executar(parametros)

            self.assertEqual(relatorio.total_modificados, 1)
            self.assertEqual(relatorio.total_inalterados, 7)

            # Valida que o transporte remoto foi chamado com a URI correta
            transporte_mock.baixar_arquivo.assert_called_once()
            destino_chamado = transporte_mock.baixar_arquivo.call_args[1]["destino"]
            self.assertEqual(destino_chamado.host, "servidor.cliente.com")
            self.assertEqual(destino_chamado.usuario, "deploy")
            self.assertEqual(destino_chamado.caminho_remoto, "/opt/producao/app.jar")

            # Valida cópia de backup do original (Passo 6)
            copia_backup = Path(dir_backup) / "app.jar"
            self.assertTrue(copia_backup.exists())
            self.assertEqual(copia_backup.stat().st_size, SAMPLE_BASE.stat().st_size)

    def test_obter_diff_arquivo_variacoes_status(self):
        from tests.helpers import criar_jar_temporario
        import os

        jar_base = criar_jar_temporario({
            "mesmo.txt": "conteudo igual\n",
            "apenas_base.txt": "linha antiga\n",
        })
        jar_alvo = criar_jar_temporario({
            "mesmo.txt": "conteudo igual\n",
            "apenas_alvo.txt": "linha nova\n",
        })
        self.addCleanup(lambda: os.path.exists(jar_base) and os.remove(jar_base))
        self.addCleanup(lambda: os.path.exists(jar_alvo) and os.remove(jar_alvo))

        caso_de_uso = CompararPacotesCasoDeUso()

        # Inalterado
        res_inalterado = caso_de_uso.obter_diff_arquivo(jar_base, jar_alvo, "mesmo.txt")
        self.assertEqual(res_inalterado["status"], "inalterado")

        # Adicionado
        res_add = caso_de_uso.obter_diff_arquivo(jar_base, jar_alvo, "apenas_alvo.txt")
        self.assertEqual(res_add["status"], "adicionado")
        self.assertIn("+linha nova", res_add["diff"])

        # Removido
        res_rem = caso_de_uso.obter_diff_arquivo(jar_base, jar_alvo, "apenas_base.txt")
        self.assertEqual(res_rem["status"], "removido")
        self.assertIn("-linha antiga", res_rem["diff"])

    def test_obter_diff_arquivo_busca_tolerante_e_inexistente(self):
        from safepatch.domain.excecoes import ArquivoNaoEncontradoError

        caso_de_uso = CompararPacotesCasoDeUso()

        # Busca tolerante (pelo sufixo do caminho da classe)
        res_tolerante = caso_de_uso.obter_diff_arquivo(
            SAMPLE_BASE, SAMPLE_ALVO, "UserDTO.class"
        )
        self.assertEqual(res_tolerante["caminho"], "com/example/dto/UserDTO.class")
        self.assertEqual(res_tolerante["status"], "modificado")

        # Arquivo inexistente em ambos
        with self.assertRaises(ArquivoNaoEncontradoError):
            caso_de_uso.obter_diff_arquivo(SAMPLE_BASE, SAMPLE_ALVO, "nao_existe.txt")

    def test_executar_com_erro_registra_auditoria_falha(self):
        from unittest.mock import MagicMock
        from safepatch.domain.excecoes import PacoteInvalidoError

        auditor_mock = MagicMock()
        caso_de_uso = CompararPacotesCasoDeUso(auditor=auditor_mock)

        parametros = ParametrosComparacao(
            caminho_base="inexistente_123.jar",
            caminho_alvo=SAMPLE_ALVO,
        )

        with self.assertRaises(PacoteInvalidoError):
            caso_de_uso.executar(parametros)

        auditor_mock.registrar.assert_called_once()
        args = auditor_mock.registrar.call_args[1]
        self.assertEqual(args["operacao"], "comparacao")
        self.assertFalse(args["sucesso"])
        self.assertIsNotNone(args.get("erro"))


if __name__ == "__main__":
    unittest.main()
