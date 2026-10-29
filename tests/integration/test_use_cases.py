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


if __name__ == "__main__":
    unittest.main()
