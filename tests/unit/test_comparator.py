"""Testes unitários para o comparador de pacotes (ComparadorPacotesConjuntos)."""

import unittest
from tests.helpers import SRC_PATH

from safepatch.domain.modelos import ArquivoInfo
from safepatch.infrastructure.comparacao.comparador_conjuntos import (
    ComparadorPacotesConjuntos,
)


class TestComparadorPacotesConjuntos(unittest.TestCase):
    def setUp(self):
        self.comparador = ComparadorPacotesConjuntos()

    def test_classificacao_adicionados_removidos_inalterados_modificados(self):
        inv_base = {
            "removido.txt": ArquivoInfo(caminho="removido.txt", hash_sha256="hash1", tamanho_bytes=10),
            "inalterado.txt": ArquivoInfo(caminho="inalterado.txt", hash_sha256="hash2", tamanho_bytes=20),
            "modificado.txt": ArquivoInfo(caminho="modificado.txt", hash_sha256="hash3_base", tamanho_bytes=30),
        }
        inv_alvo = {
            "adicionado.txt": ArquivoInfo(caminho="adicionado.txt", hash_sha256="hash4", tamanho_bytes=40),
            "inalterado.txt": ArquivoInfo(caminho="inalterado.txt", hash_sha256="hash2", tamanho_bytes=20),
            "modificado.txt": ArquivoInfo(caminho="modificado.txt", hash_sha256="hash3_alvo", tamanho_bytes=55),
        }

        relatorio = self.comparador.comparar("base.jar", inv_base, "alvo.jar", inv_alvo)

        self.assertEqual([a.caminho for a in relatorio.adicionados], ["adicionado.txt"])
        self.assertEqual([a.caminho for a in relatorio.removidos], ["removido.txt"])
        self.assertEqual([a.caminho for a in relatorio.inalterados], ["inalterado.txt"])
        self.assertEqual([m.caminho for m in relatorio.modificados], ["modificado.txt"])

        mod = relatorio.modificados[0]
        self.assertEqual(mod.delta_bytes, 25)
        self.assertEqual(mod.delta_formatado, "+25 B")

    def test_filtro_glob_ignorar(self):
        comparador_com_filtro = ComparadorPacotesConjuntos(padroes_ignorar=["META-INF/*", "*.md"])
        inv_base = {
            "META-INF/MANIFEST.MF": ArquivoInfo("META-INF/MANIFEST.MF", "hash_base", 100),
            "README.md": ArquivoInfo("README.md", "hash_base_md", 50),
            "app.class": ArquivoInfo("app.class", "hash_base_app", 500),
        }
        inv_alvo = {
            "META-INF/MANIFEST.MF": ArquivoInfo("META-INF/MANIFEST.MF", "hash_alvo", 120),
            "README.md": ArquivoInfo("README.md", "hash_alvo_md", 70),
            "app.class": ArquivoInfo("app.class", "hash_alvo_app", 600),
        }

        relatorio = comparador_com_filtro.comparar("base.jar", inv_base, "alvo.jar", inv_alvo)

        self.assertIn("META-INF/MANIFEST.MF", relatorio.ignorados)
        self.assertIn("README.md", relatorio.ignorados)
        self.assertEqual(len(relatorio.modificados), 1)
        self.assertEqual(relatorio.modificados[0].caminho, "app.class")


if __name__ == "__main__":
    unittest.main()
