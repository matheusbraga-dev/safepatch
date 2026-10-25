"""Testes unitários para os modelos de domínio do SafePatch."""

import unittest
from tests.helpers import SRC_PATH

from safepatch.domain.modelos import (
    ArquivoInfo,
    ArquivoModificadoInfo,
    RelatorioComparacao,
)


class TestModels(unittest.TestCase):
    def test_arquivo_info_propriedades_e_imutabilidade(self):
        info = ArquivoInfo(caminho="com/app/Main.class", hash_sha256="abc12345", tamanho_bytes=2048)
        self.assertEqual(info.caminho, "com/app/Main.class")
        self.assertEqual(info.hash_sha256, "abc12345")
        self.assertEqual(info.tamanho_bytes, 2048)
        self.assertEqual(info.tamanho_formatado, "2.00 KB")

        with self.assertRaises(Exception):
            info.tamanho_bytes = 4096  # Dataclass frozen

    def test_arquivo_modificado_info_deltas(self):
        base = ArquivoInfo(caminho="config.properties", hash_sha256="h1", tamanho_bytes=100)
        alvo = ArquivoInfo(caminho="config.properties", hash_sha256="h2", tamanho_bytes=150)
        mod = ArquivoModificadoInfo(caminho="config.properties", base=base, alvo=alvo)

        self.assertEqual(mod.caminho, "config.properties")
        self.assertEqual(mod.delta_bytes, 50)
        self.assertEqual(mod.delta_formatado, "+50 B")

    def test_relatorio_comparacao_totais_e_conflitos(self):
        base = ArquivoInfo("a.txt", "h1", 10)
        alvo = ArquivoInfo("a.txt", "h2", 20)
        relatorio = RelatorioComparacao(
            pacote_base="base.jar",
            pacote_alvo="alvo.jar",
            adicionados=[ArquivoInfo("add.txt", "h3", 5)],
            removidos=[ArquivoInfo("rem.txt", "h4", 8)],
            inalterados=[ArquivoInfo("same.txt", "h5", 15)],
            modificados=[ArquivoModificadoInfo("a.txt", base, alvo)],
            ignorados=["META-INF/MANIFEST.MF"],
        )

        self.assertTrue(relatorio.tem_conflitos)
        self.assertEqual(relatorio.total_adicionados, 1)
        self.assertEqual(relatorio.total_removidos, 1)
        self.assertEqual(relatorio.total_modificados, 1)
        self.assertEqual(relatorio.total_inalterados, 1)
        self.assertEqual(relatorio.total_ignorados, 1)


if __name__ == "__main__":
    unittest.main()
