# 🛡️ SafePatch (.jar / .war / .zip)

[![PyPI version](https://img.shields.io/pypi/v/safepatch.svg)](https://pypi.org/project/safepatch/)
[![Python Versions](https://img.shields.io/pypi/pyversions/safepatch.svg)](https://pypi.org/project/safepatch/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Uma ferramenta de linha de comando (CLI) em Python de alta performance para inspeção, auditoria e comparação de pacotes compactados (`.jar`, `.war`, `.zip`). Desenvolvida para detectar conflitos, arquivos alterados, adições e remoções entre versões de artefatos de release, patches e bibliotecas.

Zero dependências externas: construída exclusivamente com a **biblioteca padrão do Python**.

---

## 🚀 Funcionalidades

* ⚡ **Leitura Otimizada em Streaming**: Processa pacotes lendo blocos de 64KB sob demanda, permitindo analisar arquivos pesados com consumo mínimo de memória RAM.
* 🌐 **Conexão Remota SSH/SFTP Híbrida**: Audite pacotes diretamente no servidor remoto do cliente sem depender de download manual via WinSCP. Suporta sintaxe SCP clássica (`usuario@servidor:/caminho/app.jar`) e URIs SSH (`ssh://usuario:senha@servidor:porta/caminho/app.jar`).
  * **Zero Dependências**: Utiliza automaticamente o cliente OpenSSH nativo do sistema operacional (`scp`/`ssh`).
  * **Modo Paramiko Opcional**: Suporte a SFTP de alta performance via `pip install safepatch[ssh]`.
* 🧭 **Navegação e Exploração Remota de Diretórios**:
  * **CLI Interativa**: Explore pastas do servidor remoto diretamente no terminal usando as **setas do teclado** (`↑`/`↓`), <kbd>Enter</kbd> para navegar ou selecionar arquivos `.jar`/`.war`, e <kbd>Backspace</kbd> para subir de pasta (`--navegar-remoto`).
  * **Saída Tabular ou JSON**: Exibe os itens no terminal ou emite JSON estruturado sob demanda para alimentar árvores de navegação em GUIs externas (`--listar-remoto`).
* 🚀 **Publicação Reversa e Deploy Seguro com Rollback Automático**:
  * Envia o pacote corrigido e aprovado de volta para o servidor do cliente (`--publicar`).
  * **Backup Remoto Automático**: Cria uma cópia com timestamp (`app.jar.bak_YYYYMMDD_HHMMSS`) antes de substituir o arquivo original.
  * **Validação de Integridade Pós-Deploy**: Valida o hash SHA-256 local contra o hash gerado no servidor remoto.
  * **Rollback Automático Imediato**: Restaura o arquivo original instantaneamente caso seja detectada divergência de integridade.
* 🖥️ **Pronto para Integração com GUIs Externas (Java Desktop, Flutter, C#/.NET)**:
  * **JSON no stdout (`--json -` / `--json-stdout`)**: Roteia o relatório estruturado puramente no `stdout`, enviando mensagens informativas para o `stderr`.
  * **Streaming de Progresso NDJSON (`--eventos-progresso`)**: Emite eventos JSON linha a linha no `stderr` para alimentar barras de progresso no frontend em tempo real.
  * **Diff Sob Demanda em Milissegundos (`--diff-arquivo`)**: Gera o diff descompilado exclusivamente para o arquivo inspecionado no momento pelo usuário na GUI (*Lazy Loading*).
* 🛡️ **Auditoria de Compliance em Arquivo Oculto**:
  * Registra operações de auditoria, diff e deploy em log imutável append-only JSONL (`~/.safepatch/.auditoria.jsonl`) com timestamp UTC, usuário, máquina e hashes.
  * No Windows, define automaticamente o atributo de sistema de arquivo oculto. Consulta rápida via `--listar-auditoria`.
* 💡 **Comparação Direta com Código-Fonte (`.java` vs `.class`)**: Audite alterações feitas na sua IDE diretamente contra o `.jar` de produção **sem precisar compilar ou rodar build** (`mvn package`, `gradle build`). O SafePatch mapeia os pacotes Java, normaliza comentários/espaçamento e gera o diff do que você alterou.
* 📁 **Suporte Híbrido a Pacotes, Pastas e Fontes**: Aceita arquivos `.jar`, `.war`, `.zip`, **pastas compiladas** (`target/classes`), **pastas de código-fonte** (`src/main/java`, `.`) ou arquivos `.java` individuais.
* 🔒 **Verificação de Integridade (SHA-256)**: Compara o hash SHA-256 de cada arquivo interno para garantir a detecção exata de modificações lógicas, mesmo quando as datas de modificação ou atributos forem alterados.
* 📊 **Cálculo de Variação (Delta)**: Exibe a diferença de tamanho (em bytes, KB, MB) para cada arquivo modificado (ex: `1.81 KB → 2.39 KB | +602 B`).
* ☕ **Diff Descompilado no Estilo Git (`-d / --diff`)**:
  * Mostra as linhas adicionadas (`+`) e removidas (`-`) em arquivos modificados, novos e deletados.
  * Suporta arquivos de texto puro (XML, JSON, properties, YAML, SQL, código-fonte, etc.).
  * **Descompilação Automática de Bytecode Java (.class)**: Descompila arquivos `.class` em **código-fonte Java real e limpo** (via CFR Decompiler integrado), permitindo ler métodos e classes sem ter que decifrar instruções de bytecode.
* 🎯 **Filtros Flexíveis por Padrões Glob**:
  * **Inclusão (`-f / --filtro`)**: Concentre a auditoria em classes ou pacotes específicos (ex: `-f "*UserDTO*"`, `-f "com/exemplo/servico/*"`).
  * **Exclusão (`-i / --ignorar`)**: Ignore metadados voláteis como `META-INF/*`, arquivos de documentação (`*.md`) ou logs.
* 📄 **Múltiplos Formatos de Relatório**:
  * **Console (Terminal)**: Colorido via ANSI com modo compacto ou verboso (`--verbose`).
  * **JSON (`--json`)**: Estruturado com metadados e totais, ideal para integrações e APIs.
  * **Markdown (`--markdown / --md`)**: Tabelas e diffs prontas para documentação ou Pull Requests.
  * **HTML Interativo (`--html`)**: Dashboard visual moderno e responsivo com **campo de busca instantânea**, filtros rápidos por categoria (Modificados, Adicionados, Removidos) e diffs embutidos, 100% offline (zero CDNs externas).
* 🤖 **Pronto para CI/CD (`--fail-on-conflict`)**: Retorna código de saída `2` se detectar arquivos conflitantes/modificados, permitindo travar esteiras de deploy indesejadas.

---

## 📋 Requisitos

* **Python 3.8+** (compatível com Linux, macOS e Windows).
* Java JRE/JDK 8+ instalado no sistema (para descompilação de arquivos `.class`).

---

## 🛠️ Instalação

### Via PyPI (Recomendado)

```bash
# Instalação padrão (Zero dependências externas, utiliza OpenSSH nativo)
pip install safepatch

# Opcional: com suporte à biblioteca Paramiko para transporte SFTP programático
pip install "safepatch[ssh]"
```

### Via Código-Fonte (Desenvolvimento)

```bash
git clone https://github.com/matheusbraga-dev/safepatch.git
cd safepatch
pip install -e .
```

Para validar a integridade da instalação, execute a suíte de testes:

```bash
python -m unittest discover tests
```

---

## 💻 Guia de Uso

### 1. Comparação Básica

Para comparar dois pacotes `.jar`, `.war` ou `.zip`:

```bash
safepatch --base "app-v1.0.jar" --alvo "app-v1.1.jar"
```

**Exemplo de saída no terminal:**
```text
Iniciando varredura dos pacotes...
Lendo pacote base: app-v1.0.jar...
Lendo pacote alvo: app-v1.1.jar...
Analisando diferenças e detectando conflitos...

=== RELATÓRIO DE COMPARAÇÃO DE PACOTES ===
Pacote Base: app-v1.0.jar
Pacote Alvo: app-v1.1.jar
==========================================

Total Adicionados: 0
Total Removidos:   0
Total Modificados: 1
Total Inalterados: 7
------------------------------------------

[~] ARQUIVOS MODIFICADOS (Atenção - Possíveis Conflitos):
    com/example/dto/UserDTO.class (875 B → 1.08 KB | +227 B)
```

---

### 2. Visualizando Diferenças Detalhadas Estilo Git (`--diff / -d`)

Para inspecionar o código exato das alterações (linhas adicionadas `+` e removidas `-`), utilize a flag `-d` ou `--diff`:

```bash
safepatch --base "app-v1.0.jar" --alvo "app-v1.1.jar" --diff
```

**Exemplo de saída com diff Java descompilado e colorido:**
```diff
[~] ARQUIVOS MODIFICADOS (Atenção - Possíveis Conflitos):
    com/example/dto/UserDTO.class (875 B → 1.08 KB | +227 B)
diff --git a/com/example/dto/UserDTO.class b/com/example/dto/UserDTO.class
--- a/com/example/dto/UserDTO.class
+++ b/com/example/dto/UserDTO.class
@@ -40,4 +40,8 @@
     public void setEmail(String string) {
         this.email = string;
     }
+
+    public String getDisplayName() {
+        return this.name + " (" + this.email + ")";
+    }
 }
```

> **Dica:** O diff também é automaticamente incorporado aos relatórios exportados em Markdown e HTML quando a flag `--diff` for utilizada junto com `--md` ou `--html`.
> No PowerShell (Windows), para quebrar linhas em comandos utilize o caractere de acento grave (`` ` ``) em vez da barra invertida (`\`).

---

### 3. Exportando Relatórios (JSON, Markdown e HTML)

Você pode gerar relatórios em um ou mais formatos simultaneamente:

```bash
safepatch --base "app-v1.0.jar" \
          --alvo "app-v1.1.jar" \
          --diff \
          --json relatorio.json \
          --md relatorio.md \
          --html relatorio.html
```

---

### 4. Filtrando Classes ou Pacotes Específicos (`-f / --filtro`)

Para focar a auditoria apenas nas classes ou pacotes relevantes para o seu patch:

```bash
# Audita apenas a classe UserDTO e arquivos do pacote financeiro
safepatch --base "app-v1.0.jar" \
          --alvo "app-v1.1.jar" \
          -f "*UserDTO*" \
          -f "com/empresa/financeiro/*"
```

---

### 5. Comparando Diretórios Locais e Pacotes (`pasta vs jar` ou `pasta vs pasta`)

O SafePatch aceita pastas descompactadas diretamente (como o diretório de saída do Maven `target/classes` ou Gradle `build/classes/java/main`), dispensando a necessidade de empacotar em JAR antes de analisar:

```bash
# Compara a pasta compilada local contra o JAR de produção do cliente
safepatch --base "cliente-producao.jar" \
          --alvo "target/classes" \
          --diff

# Ou compara duas pastas compiladas diretamente
safepatch --base "workspace-v1/target/classes" \
          --alvo "workspace-v2/target/classes"
```

---

### 6. Comparação Direta com Código-Fonte da IDE (`.java` vs `.class` sem Build!)

Você pode comparar o `.jar` de produção do cliente diretamente contra os arquivos `.java` que você está editando na sua IDE, **sem precisar rodar `mvn package` ou `gradle build`**:

```bash
# Compara o JAR do cliente diretamente contra a pasta de fontes da IDE
safepatch --base "cliente-producao.jar" \
          --alvo "src/main/java" \
          --diff

# Ou compare um arquivo Java específico que você acabou de alterar
safepatch --base "cliente-producao.jar" \
          --alvo "src/main/java/com/empresa/dto/UserDTO.java" \
          --diff

# Ou aponte para a raiz do projeto (ignora .git, target, build etc. automaticamente)
safepatch --base "cliente-producao.jar" \
          --alvo "." \
          -f "*Service*" \
          --diff
```

---

### 7. Ignorando Metadados ou Padrões Específicos (`-i / --ignorar`)

Para evitar falsos positivos gerados por manifests de build ou documentação:

```bash
safepatch --base "pacote_v1.jar" \
          --alvo "pacote_v2.jar" \
          -i "META-INF/*" \
          -i "*.properties"
```

---

### 8. Modo Verboso e Controle de Limite de Exibição

Por padrão, a CLI exibe no máximo 10 arquivos por categoria no console para evitar poluição. Para ver todos os arquivos:

```bash
# Exibe todos os arquivos no terminal sem paginação
safepatch --base "base.jar" --alvo "alvo.jar" --verbose

# Ou configure um limite personalizado (ex: 25 itens)
safepatch --base "base.jar" --alvo "alvo.jar" --limite 25
```

---

### 9. Integração Contínua (CI/CD)

Use a flag `--fail-on-conflict` para interromper scripts de automação se houver alterações inesperadas:

```bash
safepatch --base "base.jar" --alvo "alvo.jar" --fail-on-conflict
```

#### Códigos de Saída (Exit Codes):
| Código | Significado |
| :---: | :--- |
| `0` | Sucesso (análise concluída sem conflitos críticos). |
| `1` | Erro de execução (arquivo não encontrado, ZIP corrompido, argumentos inválidos). |
| `2` | Conflito detectado (quando executado com a flag `--fail-on-conflict`). |

---

### 10. Conexão e Auditoria Remota via SSH / SFTP (Passo 2 do Fluxo Automatizado)

Você pode apontar diretamente para pacotes hospedados no servidor remoto do cliente sem precisar baixá-los manualmente com WinSCP:

```bash
# Sintaxe SCP clássica
safepatch --base "deploy@servidor.empresa.com:/opt/app/app-producao.jar" \
          --alvo "target/classes" \
          --chave-ssh "~/.ssh/id_rsa" \
          --diff

# Ou usando formato de URI SSH (com porta e senha se aplicável)
safepatch --base "ssh://deploy:senha123@servidor.empresa.com:2222/opt/app/app-producao.jar" \
          --alvo "app-novo.jar" \
          --salvar-copia-local "./backups" \
          --diff
```

* `--salvar-copia-local <pasta>`: Preserva uma cópia local inalterada do arquivo original baixado para histórico ou auditoria.
* **Segurança e Caching**: O arquivo remoto é baixado para um diretório temporário isolado e removido automaticamente ao término da execução.

---

### 11. Navegação e Exploração de Diretórios Remotos

Não precisa decorar o caminho exato do arquivo no servidor do cliente. O SafePatch oferece navegação interativa pelo terminal e saída estruturada para interfaces gráficas:

#### A) Navegação Interativa pelo Teclado no Terminal:
```bash
safepatch --navegar-remoto "deploy@servidor.empresa.com:/opt/app"
```
* Use as setas <kbd>↑</kbd> e <kbd>↓</kbd> do teclado para navegar entre pastas e arquivos (ou digite o número).
* Pressione <kbd>Enter</kbd> para entrar em subdiretórios ou selecionar um `.jar`/`.war`.
* Selecione `..` ou pressione <kbd>Backspace</kbd> para subir de pasta.
* Pressione <kbd>q</kbd> ou <kbd>Esc</kbd> para cancelar.

#### B) Listagem Tabular ou JSON:
```bash
# Exibição tabular no terminal
safepatch --listar-remoto "deploy@servidor.empresa.com:/opt/app"

# Emissão em JSON puro (ideal para árvores de arquivos e modais em GUIs externas)
safepatch --listar-remoto "deploy@servidor.empresa.com:/opt/app" --json -
```

---

### 12. Publicação Reversa e Deploy Seguro com Rollback (Passo 6 do Fluxo Automatizado)

Após comparar, auditar e aprovar a alteração, substitua o JAR no servidor remoto com segurança total:

```bash
safepatch --publicar "./dist/app-corrigido.jar" "deploy@servidor.empresa.com:/opt/app/app.jar"
```

#### Protocolo de Segurança em 4 Etapas:
1. **Backup Remoto Pré-Deploy**: Gera uma cópia preservada com timestamp no servidor (ex: `/opt/app/app.jar.bak_20261028_220000`).
2. **Transferência Segura**: Transfere o arquivo aprovado via SCP ou SFTP.
3. **Validação de Integridade Pós-Transferência (SHA-256)**: Compara o hash SHA-256 calculado localmente contra o hash gerado no arquivo do servidor.
4. **Mecanismo de Rollback Automático**: Se os hashes divergirem (corrupção na rede ou falha de escrita), o backup original é restaurado imediatamente no servidor e a operação é abortada com alerta.

Flags de ajuste:
* `--sem-backup`: Desativa a criação da cópia `.bak`.
* `--sem-verificacao`: Desativa a validação SHA-256 pós-transferência.

---

### 13. Integração com GUIs Externas e Streaming em Tempo Real

O SafePatch foi construído para atuar como motor de comparação para qualquer aplicação externa (JavaFX/WebView, Flutter Desktop, C#/.NET, Electron, etc.):

* **JSON Puro no `stdout` (`--json -` ou `--json-stdout`)**:
  ```bash
  safepatch --base "v1.jar" --alvo "v2.jar" --json -
  ```
  Garante que 100% da saída do `stdout` seja JSON parseável pela interface gráfica, redirecionando logs informativos para o `stderr`.

* **Streaming de Progresso NDJSON (`--eventos-progresso`)**:
  ```bash
  safepatch --base "ssh://servidor/app.jar" --alvo "." --eventos-progresso --json -
  ```
  Emite eventos estruturados linha a linha no `stderr` em formato NDJSON:
  ```json
  {"evento": "progresso", "etapa": "download_ssh_progresso", "percentual": 45.0, "mensagem": "Baixando pacote via SSH (45.0%)..."}
  ```

* **Carregamento sob Demanda de Diff (*Lazy Loading* em Milissegundos)**:
  ```bash
  safepatch --base "v1.jar" --alvo "v2.jar" --diff-arquivo "com/empresa/UserDTO.class" --json -
  ```
  Permite que a interface gráfica abra o comparador instantaneamente apenas para o arquivo em que o usuário clicou.

* **Modo Silencioso (`-s / --silencioso`)**:
  Suprime saídas de texto no console, ideal para rotinas automatizadas.

---

### 14. Histórico de Auditoria e Compliance (Passo 7 do Fluxo Automatizado)

Todas as operações de comparação, inspeção sob demanda e deploy são registradas automaticamente em um log append-only imutável no arquivo oculto `~/.safepatch/.auditoria.jsonl`.

Cada entrada registra:
* Data/hora UTC (ISO 8601)
* Usuário logado e nome da máquina (hostname)
* Tipo de operação (`comparacao`, `diff_arquivo`, `deploy`)
* Status de sucesso/falha e detalhes dos artefatos (hashes, totais, caminhos)

Para consultar o histórico recente:
```bash
# Visualização resumida no terminal
safepatch --listar-auditoria

# Ou em JSON para exibir na aba de compliance da GUI
safepatch --listar-auditoria --json -
```

---

## 📖 Referência de Parâmetros da CLI

| Parâmetro em Português | Alias em Inglês | Tipo | Descrição |
| :--- | :--- | :---: | :--- |
| `--base` | - | `string` | Caminho base local ou remoto (`.jar`, `.war`, `.zip`, pasta, `.java` ou `ssh://...`). |
| `--alvo` | - | `string` | Caminho alvo local ou remoto (`.jar`, `.war`, `.zip`, pasta, `.java` ou `ssh://...`). |
| `-f`, `--filtro` | - | `string` | Padrão glob de arquivos ou classes a incluir na análise (ex: `'*UserDTO*'`). Pode ser repetido. |
| `-i`, `--ignorar` | - | `string` | Padrão glob de arquivos a ignorar (ex: `'META-INF/*'`). Pode ser repetido. |
| `-d`, `--diff` | - | `flag` | Exibe a diferença detalhada do conteúdo estilo Git em código Java legível. |
| `--diff-arquivo` | `--diff-file` | `string` | Gera o diff sob demanda exclusivamente para o arquivo especificado (ideal para GUIs). |
| `-s`, `--silencioso` | `-q`, `--quiet` | `flag` | Suprime mensagens informativas no console. |
| `--eventos-progresso` | `--progress-events` | `flag` | Emite eventos de progresso em tempo real em NDJSON no `stderr`. |
| `-v`, `--verbose` | - | `flag` | Exibe a lista completa de arquivos no terminal sem limites. |
| `--limite` | - | `int` | Quantidade máxima de itens por categoria exibidos no terminal (padrão: `10`). |
| `--no-color` | - | `flag` | Desativa a coloração ANSI na saída do console. |
| `--json` | - | `string` | Salva o relatório estruturado em arquivo JSON (ou use `-` para stdout). |
| `--json-stdout` | - | `flag` | Exporta o relatório estruturado em JSON diretamente no stdout. |
| `--md`, `--markdown` | - | `string` | Caminho do arquivo para salvar o relatório em formato Markdown. |
| `--html` | - | `string` | Caminho do arquivo para salvar o dashboard interativo em HTML. |
| `--fail-on-conflict` | - | `flag` | Encerra com código de saída `2` caso haja arquivos modificados. |
| `--chave-ssh` | `--ssh-key` | `string` | Caminho para a chave privada SSH (`~/.ssh/id_rsa`, `.pem`). |
| `--porta-ssh` | `--ssh-port` | `int` | Porta do servidor SSH remoto (padrão: `22`). |
| `--senha-ssh` | `--ssh-password` | `string` | Senha para autenticação no servidor SSH (se aplicável). |
| `--salvar-copia-local` | `--dir-backup` | `string` | Salva uma cópia de backup do arquivo remoto baixado na máquina local. |
| `--listar-remoto` | `--list-remote` | `string` | Lista arquivos e pastas no servidor remoto (tabular ou JSON). |
| `--navegar-remoto` | `--browse-remote` | `string` | Abre navegador interativo pelo teclado no terminal. |
| `--publicar` | `--deploy` | `nargs=2` | Publica o pacote aprovado no servidor remoto (`local` `remoto`). |
| `--sem-backup` | `--no-backup` | `flag` | Desativa a criação de backup remoto `.bak` antes do deploy. |
| `--sem-verificacao` | `--no-verify` | `flag` | Desativa a verificação pós-deploy por SHA-256. |
| `--listar-auditoria` | `--list-audit` | `flag` | Exibe os registros recentes gravados no log de auditoria. |
| `--arquivo-auditoria`| `--audit-file` | `string` | Caminho personalizado para o arquivo de log de auditoria. |
| `--sem-auditoria` | `--no-audit` | `flag` | Desativa temporariamente a gravação no log de auditoria. |
| `-V`, `--version` | - | `flag` | Exibe a versão instalada do SafePatch e encerra. |
| `-h`, `--help` | - | `flag` | Exibe a mensagem de ajuda com todos os comandos disponíveis. |

---

## 📁 Estrutura do Projeto (Clean Architecture)

```text
cli/
├── pyproject.toml                     # Metadados e configuração de build (setuptools)
├── README.md                          # Documentação da ferramenta
├── CHANGELOG.md                       # Histórico de lançamentos e versões
├── LICENSE                            # Termos da licença de código aberto MIT
├── main.py                            # Ponto de entrada raiz
│
├── src/
│   └── safepatch/                     # Pacote principal
│       ├── __init__.py                # Exportação da API do pacote
│       ├── __main__.py                # Ponto de entrada (python -m safepatch)
│       │
│       ├── config/                    # Configurações centrais
│       │   ├── __init__.py
│       │   └── configuracoes.py       # Buffers de streaming, timeouts e limites
│       │
│       ├── domain/                    # Núcleo de domínio (regras puras, zero I/O)
│       │   ├── __init__.py
│       │   ├── modelos.py             # ArquivoInfo, ArquivoModificadoInfo, RelatorioComparacao
│       │   ├── protocolos.py          # Interfaces: ProtocoloAuditoria, ProtocoloTransporteSSH, etc.
│       │   └── excecoes.py            # Hierarquia de exceções de domínio
│       │
│       ├── application/               # Casos de uso e DTOs
│       │   ├── __init__.py
│       │   ├── dtos.py                # ParametrosComparacao
│       │   └── casos_de_uso.py        # CompararPacotesCasoDeUso (orquestrador de auditoria)
│       │
│       ├── infrastructure/            # Implementações concretas de I/O
│       │   ├── __init__.py
│       │   ├── auditoria/             # Auditoria oculta e compliance (gravador_auditoria.py)
│       │   ├── remoto/                # Conectividade SSH/SFTP, navegação e deploy seguro
│       │   │   ├── uri_ssh.py         # Parser e identificador de URIs SSH
│       │   │   ├── transporte.py      # ProtocoloTransporteSSH e ItemRemotoInfo
│       │   │   ├── transporte_nativo.py # Transporte OpenSSH nativo (zero dependências)
│       │   │   ├── transporte_paramiko.py # Transporte SFTP de alta performance (Paramiko)
│       │   │   └── resolvedor_ssh.py  # Orquestrador de downloads, exploração e rollback
│       │   ├── sistema_arquivos/      # Escrita atômica segura no disco (escritor_atomico.py)
│       │   ├── leitores/              # Leitores streaming (zip, diretorio, fonte Java, universal)
│       │   ├── comparacao/            # Comparação por conjuntos e filtros glob
│       │   ├── descompilador/         # Descompilador CFR com subprocess seguro e timeout
│       │   ├── diff/                  # Motor de unified diff Git (motor_diff.py)
│       │   └── exportadores/          # Exportadores isolados (json, markdown, html)
│       │
│       ├── presentation/              # Camada de apresentação e CLI
│       │   ├── __init__.py
│       │   ├── cli.py                 # Parser argparse, streaming NDJSON e códigos de saída
│       │   ├── console.py             # Renderizador de terminal com cores ANSI
│       │   └── navegador_cli.py       # File explorer interativo por teclado e tabela remota
│       │
│       ├── shared/                    # Utilitários compartilhados
│       │   ├── __init__.py
│       │   ├── formatacao.py          # Formatação de bytes, deltas e diff colorido
│       │   ├── normalizador_java.py   # Normalização e extração semântica de código Java
│       │   └── sanitizacao.py         # Sanitização e escape HTML contra XSS
│       │
│       └── bin/                       # Binários embutidos
│           └── cfr.jar                # Descompilador CFR
│
└── tests/                             # Suíte de testes automatizados (127 testes)
    ├── __init__.py
    ├── helpers.py                     # Fixtures e geradores temporários
    ├── unit/                          # Testes unitários (auditoria, remoto, navegador, etc.)
    ├── integration/                   # Testes de integração (Use Cases)
    └── cli/                           # Testes funcionais da interface de linha de comando
```

---

## 🧪 Executando os Testes

Para rodar todos os testes automatizados:

```bash
python -m unittest discover tests
```

Para rodar em modo detalhado (verbose):

```bash
python -m unittest discover tests -v
```

---

## 📄 Licença

Este projeto é disponibilizado sob a licença [MIT](LICENSE). Consulte o arquivo [LICENSE](LICENSE) para mais detalhes.
