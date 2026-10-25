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


if __name__ == "__main__":
    unittest.main()
