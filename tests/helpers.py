"""Helpers e utilitários compartilhados para testes."""

import atexit
import base64
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

# Garante que 'src' esteja disponível no sys.path para os testes
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = WORKSPACE_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

# Bytecode Java real compilado (Target Java 8) para testes de descompilação e diff
_USER_DTO_V1 = base64.b64decode(
    "yv66vgAAADQAIwoAAgADBwAEDAAFAAYBABBqYXZhL2xhbmcvT2JqZWN0AQAGPGluaXQ+AQADKClWCQA"
    "IAAkHAAoMAAsADAEAF2NvbS9leGFtcGxlL2R0by9Vc2VyRFRPAQACaWQBABBMamF2YS9sYW5nL0xv"
    "bmc7CQAIAA4MAA8AEAEABG5hbWUBABJMamF2YS9sYW5nL1N0cmluZzsJAAgAEgwAEwAQAQAFZW1ha"
    "WwBAARDb2RlAQAPTGluZU51bWJlclRhYmxlAQA3KExqYXZhL2xhbmcvTG9uZztMamF2YS9sYW5nL1"
    "N0cmluZztMamF2YS9sYW5nL1N0cmluZzspVgEABWdldElkAQASKClMamF2YS9sYW5nL0xvbmc7AQAF"
    "c2V0SWQBABMoTGphdmEvbGFuZy9Mb25nOylWAQAHZ2V0TmFtZQEAFCgpTGphdmEvbGFuZy9TdHJpbm"
    "c7AQAHc2V0TmFtZQEAFShMamF2YS9sYW5nL1N0cmluZzspVgEACGdldEVtYWlsAQAIc2V0RW1haWwB"
    "AApTb3VyY2VGaWxlAQAMVXNlckRUTy5qYXZhACEACAACAAAAAwACAAsADAAAAAIADwAQAAAAAgATAB"
    "AAAAAIAAEABQAGAAEAFAAAACEAAQABAAAABSq3AAGxAAAAAQAVAAAACgACAAAACAAEAAkAAQAFABYA"
    "AQAUAAAAPAACAAQAAAAUKrcAASortQAHKiy1AA0qLbUAEbEAAAABABUAAAAWAAUAAAALAAQADAAJAA"
    "0ADgAOABMADwABABcAGAABABQAAAAdAAEAAQAAAAUqtAAHsAAAAAEAFQAAAAYAAQAAABIAAQAZABoA"
    "AQAUAAAAIgACAAIAAAAGKiu1AAexAAAAAQAVAAAACgACAAAAFgAFABcAAQAbABwAAQAUAAAAHQABAA"
    "EAAAAFKrQADbAAAAABABUAAAAGAAEAAAAaAAEAHQAeAAEAFAAAACIAAgACAAAABiortQANsQAAAAEA"
    "FQAAAAoAAgAAAB4ABQAfAAEAHwAcAAEAFAAAAB0AAQABAAAABSq0ABGwAAAAAQAVAAAABgABAAAAIg"
    "ABACAAHgABABQAAAAiAAIAAgAAAAYqK7UAEbEAAAABABUAAAAKAAIAAAAmAAUAJwABACEAAAACACI="
)

_USER_DTO_V2 = base64.b64decode(
    "yv66vgAAADQAMgoAAgADBwAEDAAFAAYBABBqYXZhL2xhbmcvT2JqZWN0AQAGPGluaXQ+AQADKClWCQA"
    "IAAkHAAoMAAsADAEAF2NvbS9leGFtcGxlL2R0by9Vc2VyRFRPAQACaWQBABBMamF2YS9sYW5nL0xv"
    "bmc7CQAIAA4MAA8AEAEABG5hbWUBABJMamF2YS9sYW5nL1N0cmluZzsJAAgAEgwAEwAQAQAFZW1ha"
    "WwHABUBABdqYXZhL2xhbmcvU3RyaW5nQnVpbGRlcgoAFAADCgAUABgMABkAGgEABmFwcGVuZAEALSh"
    "MamF2YS9sYW5nL1N0cmluZzspTGphdmEvbGFuZy9TdHJpbmdCdWlsZGVyOwgAHAEAAiAoCAAeAQAB"
    "KQoAFAAgDAAhACIBAAh0b1N0cmluZwEAFCgpTGphdmEvbGFuZy9TdHJpbmc7AQAEQ29kZQEAD0xpbm"
    "VOdW1iZXJUYWJsZQEANyhMamF2YS9sYW5nL0xvbmc7TGphdmEvbGFuZy9TdHJpbmc7TGphdmEvbGFu"
    "Zy9TdHJpbmc7KVYBAAVnZXRJZAEAEigpTGphdmEvbGFuZy9Mb25nOwEABXNldElkAQATKExqYXZhL2"
    "xhbmcvTG9uZzspVgEAB2dldE5hbWUBAAdzZXROYW1lAQAVKExqYXZhL2xhbmcvU3RyaW5nOylWAQAI"
    "Z2V0RW1haWwBAAhzZXRFbWFpbAEADmdldERpc3BsYXlOYW1lAQAKU291cmNlRmlsZQEADFVzZXJEVE"
    "8uamF2YQAhAAgAAgAAAAMAAgALAAwAAAACAA8AEAAAAAIAEwAQAAAACQABAAUABgABACMAAAAhAAEA"
    "AQAAAAUqtwABsQAAAAEAJAAAAAoAAgAAAAgABAAJAAEABQAlAAEAIwAAADwAAgAEAAAAFCq3AAEqK7"
    "UAByostQANKi21ABGxAAAAAQAkAAAAFgAFAAAACwAEAAwACQANAA4ADgATAA8AAQAmACcAAQAjAAAA"
    "HQABAAEAAAAFKrQAB7AAAAABACQAAAAGAAEAAAASAAEAKAApAAEAIwAAACIAAgACAAAABiortQAHsQ"
    "AAAAEAJAAAAAoAAgAAABYABQAXAAEAKgAiAAEAIwAAAB0AAQABAAAABSq0AA2wAAAAAQAkAAAABgAB"
    "AAAAGgABACsALAABACMAAAAiAAIAAgAAAAYqK7UADbEAAAABACQAAAAKAAIAAAAeAAUAHwABAC0AIg"
    "ABACMAAAAdAAEAAQAAAAUqtAARsAAAAAEAJAAAAAYAAQAAACIAAQAuACwAAQAjAAAAIgACAAIAAAAG"
    "Kiu1ABGxAAAAAQAkAAAACgACAAAAJgAFACcAAQAvACIAAQAjAAAAOwACAAEAAAAjuwAUWbcAFiq0AA"
    "22ABcSG7YAFyq0ABG2ABcSHbYAF7YAH7AAAAABACQAAAAGAAEAAAAqAAEAMAAAAAIAMQ=="
)


def criar_jar_temporario(arquivos_dict):
    """Cria um arquivo .jar temporário contendo os arquivos e conteúdos informados."""
    temp_file = tempfile.NamedTemporaryFile(suffix=".jar", delete=False)
    temp_name = temp_file.name
    temp_file.close()

    with zipfile.ZipFile(temp_name, "w") as zf:
        for nome_arq, conteudo in arquivos_dict.items():
            if isinstance(conteudo, str):
                conteudo = conteudo.encode("utf-8")
            zf.writestr(nome_arq, conteudo)

    return temp_name


# Cria dinamicamente pacotes base e alvo para os testes automatizados
_DIR_FIXTURES = tempfile.mkdtemp(prefix="safepatch_test_")
atexit.register(lambda: shutil.rmtree(_DIR_FIXTURES, ignore_errors=True))


def _gerar_pacotes_teste():
    arquivos_comuns = {
        "META-INF/MANIFEST.MF": "Manifest-Version: 1.0\nCreated-By: SafePatch Test\n",
        "com/example/config/DatabaseConfig.class": b"\xca\xfe\xba\xbe\x00\x00\x004\x00\x01\x01",
        "com/example/dto/OrderDTO.class": b"\xca\xfe\xba\xbe\x00\x00\x004\x00\x01\x02",
        "com/example/model/UserRole.class": b"\xca\xfe\xba\xbe\x00\x00\x004\x00\x01\x03",
        "com/example/service/OrderService.class": b"\xca\xfe\xba\xbe\x00\x00\x004\x00\x01\x04",
        "com/example/service/UserService.class": b"\xca\xfe\xba\xbe\x00\x00\x004\x00\x01\x05",
        "com/example/util/ValidationUtils.class": b"\xca\xfe\xba\xbe\x00\x00\x004\x00\x01\x06",
    }

    base_dict = dict(arquivos_comuns)
    base_dict["com/example/dto/UserDTO.class"] = _USER_DTO_V1

    alvo_dict = dict(arquivos_comuns)
    alvo_dict["com/example/dto/UserDTO.class"] = _USER_DTO_V2

    p_base = Path(_DIR_FIXTURES) / "app-v1.jar"
    p_alvo = Path(_DIR_FIXTURES) / "app-v2.jar"

    with zipfile.ZipFile(p_base, "w") as zf:
        for k, v in base_dict.items():
            zf.writestr(k, v)

    with zipfile.ZipFile(p_alvo, "w") as zf:
        for k, v in alvo_dict.items():
            zf.writestr(k, v)

    return p_base, p_alvo


SAMPLE_BASE, SAMPLE_ALVO = _gerar_pacotes_teste()
