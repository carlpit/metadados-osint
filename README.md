# metascan

Analisador de metadados para imagens e documentos. Serve a dois propósitos complementares:

1. **OSINT ético** — inspecionar arquivos que você tem autorização para analisar e entender o que eles revelam (câmera, software, autor, datas, GPS).
2. **Revisão de privacidade** — conferir o que uma foto ou um documento pode vazar antes de publicar, e gerar uma cópia sem EXIF quando quiser.

O programa não faz chamadas de rede. Links do Google Maps e do OpenStreetMap são apenas URLs montadas a partir das coordenadas encontradas no arquivo.

---

## Recursos

- Leitura de **JPEG, PNG, TIFF, WebP** (e **HEIC/HEIF** se o extra `pillow-heif` estiver instalado)
- Extração de EXIF: câmera, software, datas, número de série e **GPS em coordenadas decimais** com links de mapa
- Metadados de **PDF** (`Author`, `Creator`, `Producer`, título, datas)
- Propriedades de **DOCX, XLSX e PPTX** (`dc:creator`, `lastModifiedBy`, datas, aplicativo)
- Detecção do tipo por **extensão e magic bytes**
- **Níveis de risco de privacidade**: nenhum, baixo, médio e alto
- Relatórios em **tabela** (usa [Rich](https://github.com/Textualize/rich) se disponível), **JSON**, **CSV** e **Markdown**
- `--strip` cria uma **cópia** da imagem sem EXIF; o original nunca é alterado
- Uso opcional do binário `exiftool` para campos extras, com fallback automático
- `--fail-on-risk` para integrar a uma pipeline de CI antes de publicar arquivos

## Instalação

Requer Python 3.10 ou superior.

```bash
git clone https://github.com/carlpit/metadados-osint.git
cd metadados-osint
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Dependências de execução: `pillow`, `piexif` e `pypdf`. Opcional:

```bash
pip install -e ".[rich]"   # tabela colorida no terminal
pip install -e ".[heic]"   # suporte a HEIC/HEIF
```

Se o [ExifTool](https://exiftool.org/) estiver no `PATH`, o `metascan` o utiliza para campos adicionais. Desative com `--no-exiftool`.

## Uso

```bash
metascan foto.jpg
metascan pasta/ --recursive
metascan foto.jpg documento.pdf --format json
metascan pasta/ -r --format markdown -o relatorio.md
metascan foto.jpg --strip --strip-dir saida/
metascan pasta/ --fail-on-risk high --format json
```

Também é possível executar com `python -m metascan`.

### Exemplo de saída

Amostra gerada pelos próprios testes (JPEG sintético com EXIF e GPS fictícios):

```text
metascan 0.1.0  |  arquivos: 1  |  falhas: 0  |  risco mais alto: ALTO

==============================================================================
foto_gps.jpg  [ALTO]
------------------------------------------------------------------------------
  Tipo                   jpeg
  Tamanho                1224 bytes
  GPS                    -7.1195, -34.845
  Google Maps            https://www.google.com/maps?q=-7.1195,-34.845
  OpenStreetMap          https://www.openstreetmap.org/?mlat=-7.1195&mlon=-34.845#map=16/-7.1195/-34.845
  Make                   TestCam
  Model                  Model X
  Software               MetaScan Test Suite
  DateTime               2024:06:15 14:30:00
  Copyright              Ana Silva
  Artist                 Ana Silva
  HostComputer           NOTEBOOK-ANA
  BodySerialNumber       SN12345678
  DateTimeOriginal       2024:06:15 14:30:00
  LensModel              TestLens 35mm
  GPSAltitude            1200
------------------------------------------------------------------------------
Alertas de privacidade:
  - [ALTO] DEVICE_SERIAL: número de série de dispositivo encontrado (SN12345678)
  - [ALTO] GPS_COORDINATES: coordenadas de geolocalização presentes; podem revelar onde o arquivo foi criado (-7.1195,-34.845)
  - [MÉDIO] AUTHOR_NAME: nome de autor, artista ou usuário encontrado (Ana Silva)
  - [MÉDIO] HOST_COMPUTER: nome de computador ou host encontrado (NOTEBOOK-ANA)
  - [BAIXO] DEVICE_MODEL: fabricante ou modelo de dispositivo identificável (TestCam)
  - [BAIXO] DEVICE_MODEL: fabricante ou modelo de dispositivo identificável (Model X)
  - [BAIXO] DEVICE_MODEL: fabricante ou modelo de dispositivo identificável (TestLens 35mm)
  - [BAIXO] SOFTWARE_VERSION: software ou versão identificável (pode auxiliar em fingerprinting) (MetaScan Test Suite)
```

Para gerar uma cópia sem metadados:

```bash
metascan foto_gps.jpg --strip --strip-dir limpo/
# Cria limpo/foto_gps_clean.jpg — o original permanece intacto.
```

Na cópia limpa, o risco cai para **NENHUM**: GPS, serial, autor e software deixam de aparecer.

## Níveis de risco

| Nível  | O que dispara |
| ------ | ------------- |
| Alto   | Coordenadas GPS ou número de série de dispositivo |
| Médio  | Nome de autor, artista, usuário ou host |
| Baixo  | Software, versão, fabricante ou modelo |
| Nenhum | Sem campos sensíveis |

## Testes e qualidade

```bash
ruff check src tests
ruff format --check src tests
pytest
```

Os testes **geram os próprios arquivos de amostra** (JPEG com EXIF/GPS, PDF com document-info e documentos Office). Nada confidencial entra no repositório. O workflow de CI em `.github/workflows/ci.yml` executa Ruff e Pytest no Python 3.10 a 3.13.

## Aviso ético e legal (LGPD)

Este projeto é uma ferramenta **defensiva e de estudo**. Use-o somente:

- em arquivos de sua autoria ou dos quais você é o titular;
- em arquivos que você tenha **autorização expressa** para examinar (por exemplo, um pentest ou uma auditoria com escopo escrito);
- para revisar o que você mesmo está prestes a publicar.

Metadados podem conter **dados pessoais** na forma da [Lei Geral de Proteção de Dados (Lei nº 13.709/2018)](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm) — nomes, identificadores de dispositivo e, sobretudo, **geolocalização**. Tratar esses dados sem base legal, para vigilância, assédio ou qualquer outra finalidade não autorizada, é ilícito.

O `metascan` **não envia arquivos à internet**. Ainda assim, o responsável pelo uso é quem executa a ferramenta. O autor não se responsabiliza por usos indevidos.

## Roadmap

- Remoção de metadados também em PDF e documentos Office (hoje o `--strip` vale para imagens)
- Extração mais completa de IPTC e XMP
- Áudio e vídeo (quando houver metadados embutidos)
- Relatório HTML navegável
- Comparação lado a lado entre o original e a cópia limpa

## Licença

[MIT](LICENSE) © 2026 Carlos Vinicius

---

## English

`metascan` is a local metadata analyzer for images and documents. It helps with **ethical OSINT** (examining files you are allowed to inspect) and with **privacy review** (seeing what a file would leak before you publish it).

**Features.** JPEG/PNG/TIFF/WebP (optional HEIC), PDF document info, and Office OOXML core/app properties. GPS values are converted to decimal coordinates with Google Maps and OpenStreetMap links. Findings are classified as high (GPS, device serial), medium (author, username, host) or low (software and device model). Output formats: terminal table, JSON, CSV and Markdown. `--strip` writes a cleaned image copy and never overwrites the original. No network calls are made.

**Install.** Python 3.10+: `pip install -e ".[dev]"`. Optional extras: `.[rich]`, `.[heic]`. A local ExifTool binary is used when present (`--no-exiftool` disables it).

**Usage.**

```bash
metascan photo.jpg
metascan folder/ --recursive
metascan photo.jpg report.pdf --format json
metascan photo.jpg --strip --strip-dir cleaned/
```

**Ethics.** Only analyze files you own or are explicitly authorized to examine. Metadata may include personal data under Brazil’s LGPD (Law 13.709/2018), including names and location. Do not use this tool for unauthorized surveillance or any other unlawful purpose.
