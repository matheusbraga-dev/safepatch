"""Testes unitários para o módulo de auditoria e compliance em arquivo oculto (Passo 7)."""

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tests.helpers import SAMPLE_ALVO, SAMPLE_BASE

from safepatch.application.casos_de_uso import CompararPacotesCasoDeUso
from safepatch.application.dtos import ParametrosComparacao
from safepatch.infrastructure.auditoria.gravador_auditoria import GravadorAuditoriaJSONL
from safepatch.presentation.cli import executar_cli


class TestGravadorAuditoriaJSONL(unittest.TestCase):
    def test_gravacao_e_leitura_historico(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            caminho_log = Path(tmp_dir) / ".auditoria.jsonl"
            gravador = GravadorAuditoriaJSONL(caminho_arquivo=caminho_log)

            gravador.registrar(
                operacao="comparacao",
                detalhes={"pacote_base": "app-v1.jar", "pacote_alvo": "app-v2.jar", "modificados": 2},
                sucesso=True,
            )
            gravador.registrar(
                operacao="diff_arquivo",
                detalhes={"caminho_interno": "UserDTO.class"},
                sucesso=True,
            )

            self.assertTrue(caminho_log.exists())

            # Lê histórico
            historico = gravador.ler_historico()
            self.assertEqual(len(historico), 2)
            # O mais recente deve vir primeiro (diff_arquivo)
            self.assertEqual(historico[0]["operacao"], "diff_arquivo")
            self.assertEqual(historico[1]["operacao"], "comparacao")
            self.assertEqual(historico[1]["detalhes"]["modificados"], 2)

            # Verifica presença de usuário e máquina
            self.assertTrue(len(historico[0]["usuario"]) > 0)
            self.assertTrue(len(historico[0]["maquina"]) > 0)
            self.assertIn("T", historico[0]["timestamp"])

    def test_leitura_com_limite(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            caminho_log = Path(tmp_dir) / ".auditoria.jsonl"
            gravador = GravadorAuditoriaJSONL(caminho_arquivo=caminho_log)

            for i in range(5):
                gravador.registrar("operacao", {"indice": i})

            historico = gravador.ler_historico(limite=2)
            self.assertEqual(len(historico), 2)
            self.assertEqual(historico[0]["detalhes"]["indice"], 4)

    def test_auditoria_desativada_nao_cria_arquivo(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            caminho_log = Path(tmp_dir) / ".auditoria.jsonl"
            gravador = GravadorAuditoriaJSONL(caminho_arquivo=caminho_log, ativado=False)

            gravador.registrar("operacao", {})
            self.assertFalse(caminho_log.exists())
            self.assertEqual(gravador.ler_historico(), [])


class TestIntegracaoAuditoriaCasoDeUso(unittest.TestCase):
    def test_caso_de_uso_registra_auditoria_automaticamente(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            caminho_log = Path(tmp_dir) / ".auditoria.jsonl"
            gravador = GravadorAuditoriaJSONL(caminho_arquivo=caminho_log)
            caso_de_uso = CompararPacotesCasoDeUso(auditor=gravador)

            parametros = ParametrosComparacao(
                caminho_base=SAMPLE_BASE,
                caminho_alvo=SAMPLE_ALVO,
            )

            relatorio = caso_de_uso.executar(parametros)
            self.assertIsNotNone(relatorio)

            historico = gravador.ler_historico()
            self.assertEqual(len(historico), 1)
            registro = historico[0]
            self.assertEqual(registro["operacao"], "comparacao")
            self.assertTrue(registro["sucesso"])
            self.assertEqual(registro["detalhes"]["total_modificados"], 1)

    def test_caso_de_uso_diff_arquivo_registra_auditoria(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            caminho_log = Path(tmp_dir) / ".auditoria.jsonl"
            gravador = GravadorAuditoriaJSONL(caminho_arquivo=caminho_log)
            caso_de_uso = CompararPacotesCasoDeUso(auditor=gravador)

            res = caso_de_uso.obter_diff_arquivo(
                caminho_base=SAMPLE_BASE,
                caminho_alvo=SAMPLE_ALVO,
                caminho_interno="com/example/dto/UserDTO.class",
            )
            self.assertEqual(res["status"], "modificado")

            historico = gravador.ler_historico()
            self.assertEqual(len(historico), 1)
            self.assertEqual(historico[0]["operacao"], "diff_arquivo")
            self.assertEqual(historico[0]["detalhes"]["status"], "modificado")


class TestCLIAuditoria(unittest.TestCase):
    def test_cli_listar_auditoria_vazio(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            caminho_log = Path(tmp_dir) / ".auditoria.jsonl"
            with patch("sys.stdout") as mock_stdout:
                codigo = executar_cli(["--listar-auditoria", "--arquivo-auditoria", str(caminho_log)])
                self.assertEqual(codigo, 0)

    def test_cli_listar_auditoria_json(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            caminho_log = Path(tmp_dir) / ".auditoria.jsonl"
            gravador = GravadorAuditoriaJSONL(caminho_arquivo=caminho_log)
            gravador.registrar("teste_cli", {"chave": "valor"})

            with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                codigo = executar_cli([
                    "--listar-auditoria",
                    "--arquivo-auditoria", str(caminho_log),
                    "--json", "-",
                ])
                self.assertEqual(codigo, 0)
                dados = json.loads(mock_stdout.getvalue())
                self.assertEqual(len(dados), 1)
                self.assertEqual(dados[0]["operacao"], "teste_cli")

    def test_cli_listar_auditoria_console_com_dados(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            caminho_log = Path(tmp_dir) / ".auditoria.jsonl"
            gravador = GravadorAuditoriaJSONL(caminho_arquivo=caminho_log)
            gravador.registrar(
                "comparacao",
                {
                    "pacote_base": "app-base.jar",
                    "pacote_alvo": "app-alvo.jar",
                    "total_modificados": 3,
                    "tem_conflitos": True,
                },
                sucesso=True,
            )
            gravador.registrar(
                "deploy",
                {
                    "origem_local": "app.jar",
                    "destino_remoto": "deploy@server:/app.jar",
                },
                sucesso=False,
            )

            import io
            with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                codigo = executar_cli([
                    "--listar-auditoria",
                    "--arquivo-auditoria", str(caminho_log),
                ])
                self.assertEqual(codigo, 0)
                saida = mock_stdout.getvalue()
                self.assertIn("HISTÓRICO DE AUDITORIA", saida)
                self.assertIn("app-base.jar", saida)
                self.assertIn("Modificados: 3", saida)
                self.assertIn("Origem: app.jar", saida)

    def test_leitura_ignora_linhas_corrompidas(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            caminho_log = Path(tmp_dir) / ".auditoria.jsonl"
            caminho_log.write_text("linha de texto corrompida\n{\"operacao\": \"valida\", \"sucesso\": true}\n", encoding="utf-8")

            gravador = GravadorAuditoriaJSONL(caminho_arquivo=caminho_log)
            historico = gravador.ler_historico()
            self.assertEqual(len(historico), 1)
            self.assertEqual(historico[0]["operacao"], "valida")

    def test_falha_de_escrita_nao_lanca_excecao(self):
        gravador = GravadorAuditoriaJSONL(caminho_arquivo=Path("C:/caminho/impossivel/sem_permissao/.log"))
        with patch("sys.stderr", new_callable=io.StringIO):
            # Não deve lançar exceção devido ao failsafe
            gravador.registrar("operacao", {"teste": 1})


if __name__ == "__main__":
    unittest.main()
