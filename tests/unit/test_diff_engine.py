"""Testes unitários para o motor de diff (MotorDiff)."""

import os
import unittest
from tests.helpers import SRC_PATH, criar_jar_temporario

from safepatch.infrastructure.diff.motor_diff import MotorDiff


class TestMotorDiff(unittest.TestCase):
    def setUp(self):
        self.diff_engine = MotorDiff()

    def test_diff_modificado_texto(self):
        jar_base = criar_jar_temporario({
            "config.properties": "timeout=10\nthreads=2\n",
        })
        jar_alvo = criar_jar_temporario({
            "config.properties": "timeout=20\nthreads=2\nnovachave=true\n",
        })
        self.addCleanup(lambda: os.path.exists(jar_base) and os.remove(jar_base))
        self.addCleanup(lambda: os.path.exists(jar_alvo) and os.remove(jar_alvo))

        linhas = self.diff_engine.diff_modificado(jar_base, jar_alvo, "config.properties")
        texto_diff = "".join(linhas)

        self.assertIn("diff --git a/config.properties b/config.properties", texto_diff)
        self.assertIn("-timeout=10", texto_diff)
        self.assertIn("+timeout=20", texto_diff)
        self.assertIn("+novachave=true", texto_diff)

    def test_diff_modificado_binario(self):
        jar_base = criar_jar_temporario({
            "imagem.png": b"\x00\x01\x02\x03\x04",
        })
        jar_alvo = criar_jar_temporario({
            "imagem.png": b"\x00\x01\x02\x03\x05",
        })
        self.addCleanup(lambda: os.path.exists(jar_base) and os.remove(jar_base))
        self.addCleanup(lambda: os.path.exists(jar_alvo) and os.remove(jar_alvo))

        linhas = self.diff_engine.diff_modificado(jar_base, jar_alvo, "imagem.png")
        texto_diff = "".join(linhas)

        self.assertIn("Binary files a/imagem.png and b/imagem.png differ", texto_diff)

    def test_diff_adicionado_e_removido(self):
        jar = criar_jar_temporario({
            "novo.txt": "primeira linha\n",
        })
        self.addCleanup(lambda: os.path.exists(jar) and os.remove(jar))

        diff_add = "".join(self.diff_engine.diff_adicionado(jar, "novo.txt"))
        self.assertIn("new file mode 100644", diff_add)
        self.assertIn("+primeira linha", diff_add)

        diff_rem = "".join(self.diff_engine.diff_removido(jar, "novo.txt"))
        self.assertIn("deleted file mode 100644", diff_rem)
        self.assertIn("-primeira linha", diff_rem)


if __name__ == "__main__":
    unittest.main()
