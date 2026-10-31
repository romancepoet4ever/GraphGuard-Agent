# 第三方声明

本文件依据各依赖许可证的通知义务条款编制，覆盖本项目分发的全部第三方组件。

> 生成方式：`pip-licenses --with-license-file`（服务端）与 `license-checker`（前端）自动提取，
> 版权声明与许可证全文均直接取自各组件自身的 LICENSE 文件，未经改写。
> 组件清单与 `DEPENDENCIES.md` 一一对应。

---

## 一、随仓库分发的第三方代码

以下组件不在包管理器内，由本仓库直接分发。

### vis-network 9.1.2

- 来源：https://github.com/visjs/vis-network （tag v9.1.2）
- 许可证：Apache-2.0 或 MIT（双许可，本项目选择 Apache-2.0）
- 分发文件：`lib/vis-9.1.2/vis-network.min.js`、`lib/vis-9.1.2/vis-network.css`
- 版权声明（原文保留）：

> Copyright (c) 2011-2017 Almende B.V, http://almende.com
> Copyright (c) 2017-2019 visjs contributors, https://github.com/visjs

- 许可证全文位置：`LICENSE.txt`（Apache-2.0 全文）；上游抬头见 `licenses/vendored/vis-network-9.1.2-header.txt`
- 本项目是否修改：否。`vis-network.css` 为上游构建产物，注释被压缩剔除，内容未改动

### vis-network 示例辅助脚本（bindings/utils.js）

- 版本：随 vis-network 9.1.2
- 来源：https://github.com/visjs/vis-network 的 examples 目录
- 许可证：Apache-2.0 或 MIT（随 vis-network，本项目选择 Apache-2.0）
- 分发文件：`lib/bindings/utils.js`
- 版权声明（原文保留）：

> Copyright (c) 2017-2019 visjs contributors, https://github.com/visjs

- 许可证全文位置：`LICENSE.txt`（Apache-2.0 全文）
- 本项目是否修改：否（文件本身不含许可证头，归属依上游项目）

### Tom Select 2.0.0-rc.4

- 来源：https://github.com/tom-select/tom-select （v2.0.0-rc.4）
- 许可证：Apache-2.0
- 分发文件：`lib/tom-select/tom-select.complete.min.js`、`lib/tom-select/tom-select.css`
- 版权声明（原文保留）：

> Copyright (c) contributors

- 许可证全文位置：`LICENSE.txt`（Apache-2.0 全文）；上游抬头见 `licenses/vendored/tom-select-2.0.0-rc.4-header.txt`
- 本项目是否修改：否

---

## 二、服务端依赖（Python，124 个）

| 组件 | 版本 | 许可证 | 许可证全文 | 本项目是否修改 |
|-|-|-|-|-|
| altair | 6.0.0 | BSD License | `licenses/python/altair-6.0.0.txt` | 否 |
| annotated-doc | 0.0.4 | MIT | `licenses/python/annotated-doc-0.0.4.txt` | 否 |
| annotated-types | 0.6.0 | MIT License | `licenses/python/annotated-types-0.6.0.txt` | 否 |
| anthropic | 2.3.0 | Apache Software License | `licenses/python/anthropic-2.3.0.txt` | 否 |
| anyio | 4.13.0 | MIT | `licenses/python/anyio-4.13.0.txt` | 否 |
| asttokens | 3.0.1 | Apache 2.0 | `licenses/python/asttokens-3.0.1.txt` | 否 |
| attrs | 23.1.0 | MIT | `licenses/python/attrs-23.1.0.txt` | 否 |
| beautifulsoup4 | 4.14.3 | MIT License | `licenses/python/beautifulsoup4-4.14.3.txt` | 否 |
| certifi | 2025.8.3 | Mozilla Public License 2.0 (MPL 2.0) | `licenses/python/certifi-2025.8.3.txt` | 否 |
| charset-normalizer | 3.3.2 | MIT License | `licenses/python/charset-normalizer-3.3.2.txt` | 否 |
| click | 8.5.0 | BSD License | `licenses/python/click-8.5.0.txt` | 否 |
| colorama | 0.4.6 | BSD License | `licenses/python/colorama-0.4.6.txt` | 否 |
| distro | 1.9.0 | Apache Software License | `licenses/python/distro-1.9.0.txt` | 否 |
| docstring_parser | 0.18.0 | MIT License | `licenses/python/docstring_parser-0.18.0.txt` | 否 |
| executing | 2.2.1 | MIT License | `licenses/python/executing-2.2.1.txt` | 否 |
| fastapi | 0.115.12 | MIT License | `licenses/python/fastapi-0.115.12.txt` | 否 |
| filelock | 3.25.2 | Unlicense | `licenses/python/filelock-3.25.2.txt` | 否 |
| fsspec | 2024.6.1 | BSD License | `licenses/python/fsspec-2024.6.1.txt` | 否 |
| h11 | 0.16.0 | MIT License | `licenses/python/h11-0.16.0.txt` | 否 |
| hf-xet | 1.6.0 | Apache-2.0 | `licenses/python/hf-xet-1.6.0.txt` | 否 |
| httpcore | 1.0.9 | BSD-3-Clause | `licenses/python/httpcore-1.0.9.txt` | 否 |
| httpcore2 | 2.13.1 | BSD-3-Clause | `licenses/python/httpcore2-2.13.1.txt` | 否 |
| httptools | 0.7.1 | MIT | `licenses/python/httptools-0.7.1.txt` | 否 |
| httpx | 0.28.1 | BSD-3-Clause | `licenses/python/httpx-0.28.1.txt` | 否 |
| httpx2 | 2.13.1 | BSD-3-Clause | `licenses/python/httpx2-2.13.1.txt` | 否 |
| huggingface_hub | 1.33.0 | Apache Software License | `licenses/python/huggingface_hub-1.33.0.txt` | 否 |
| idna | 3.20 | BSD-3-Clause | `licenses/python/idna-3.20.txt` | 否 |
| iniconfig | 1.1.1 | MIT License | `licenses/python/iniconfig-1.1.1.txt` | 是 |
| ipython | 9.11.0 | BSD License | `licenses/python/ipython-9.11.0.txt` | 否 |
| ipython_pygments_lexers | 1.1.1 | BSD License | `licenses/python/ipython_pygments_lexers-1.1.1.txt` | 否 |
| itsdangerous | 2.2.0 | BSD License | `licenses/python/itsdangerous-2.2.0.txt` | 否 |
| jedi | 0.19.2 | MIT License | `licenses/python/jedi-0.19.2.txt` | 否 |
| Jinja2 | 3.1.6 | BSD License | `licenses/python/Jinja2-3.1.6.txt` | 否 |
| jiter | 0.17.0 | MIT | `licenses/python/jiter-0.17.0.txt` | 否 |
| jsonpatch | 1.33 | BSD License | `licenses/python/jsonpatch-1.33.txt` | 否 |
| jsonpickle | 4.1.4 | BSD-3-Clause | `licenses/python/jsonpickle-4.1.4.txt` | 否 |
| jsonpointer | 2.1 | BSD License | `licenses/python/jsonpointer-2.1.txt` | 否 |
| jsonschema | 4.26.0 | MIT License | `licenses/python/jsonschema-4.26.0.txt` | 否 |
| jsonschema-specifications | 2025.9.1 | MIT License | `licenses/python/jsonschema-specifications-2025.9.1.txt` | 否 |
| langchain | 1.4.7 | MIT License | `licenses/python/langchain-1.4.7.txt` | 否 |
| langchain-core | 1.7.0 | MIT License | `licenses/python/langchain-core-1.7.0.txt` | 否 |
| langchain-openai | 1.7.2 | MIT License | `licenses/python/langchain-openai-1.7.2.txt` | 否 |
| langchain-protocol | 0.0.20 | MIT License | `licenses/python/langchain-protocol-0.0.20.txt` | 否 |
| langgraph | 1.2.17 | MIT | `licenses/python/langgraph-1.2.17.txt` | 否 |
| langgraph-checkpoint | 4.3.0 | MIT | `licenses/python/langgraph-checkpoint-4.3.0.txt` | 否 |
| langgraph-prebuilt | 1.1.1 | MIT | `licenses/python/langgraph-prebuilt-1.1.1.txt` | 否 |
| langgraph-sdk | 0.4.9 | MIT | `licenses/python/langgraph-sdk-0.4.9.txt` | 否 |
| langsmith | 0.14.12 | MIT License | `licenses/python/langsmith-0.14.12.txt` | 否 |
| loguru | 0.7.3 | MIT License | `licenses/python/loguru-0.7.3.txt` | 否 |
| lxml | 6.1.1 | BSD License | `licenses/python/lxml-6.1.1.txt` | 否 |
| markdown-it-py | 4.0.0 | MIT License | `licenses/python/markdown-it-py-4.0.0.txt` | 否 |
| MarkupSafe | 3.0.3 | BSD License | `licenses/python/MarkupSafe-3.0.3.txt` | 否 |
| matplotlib-inline | 0.2.1 | BSD-3-Clause | `licenses/python/matplotlib-inline-0.2.1.txt` | 否 |
| mdurl | 0.1.2 | MIT License | `licenses/python/mdurl-0.1.2.txt` | 否 |
| mpmath | 1.3.0 | BSD License | `licenses/python/mpmath-1.3.0.txt` | 否 |
| narwhals | 2.18.1 | MIT License | `licenses/python/narwhals-2.18.1.txt` | 否 |
| networkx | 3.6.1 | BSD License | `licenses/python/networkx-3.6.1.txt` | 否 |
| numpy | 2.5.3 | BSD License | `licenses/python/numpy-2.5.3.txt` | 否 |
| openai | 3.24.0 | Apache-2.0 | `licenses/python/openai-3.24.0.txt` | 否 |
| opentelemetry-api | 1.40.0 | Apache-2.0 | `licenses/python/opentelemetry-api-1.40.0.txt` | 否 |
| orjson | 3.11.8 | MPL-2.0 AND (Apache-2.0 OR MIT) | `licenses/python/orjson-3.11.8.txt` | 否 |
| ormsgpack | 1.12.2 | Apache-2.0 OR MIT | `licenses/python/ormsgpack-1.12.2.txt` | 否 |
| packaging | 24.1 | Apache Software License; BSD License | `licenses/python/packaging-24.1.txt` | 否 |
| pandas | 3.0.5 | BSD License | `licenses/python/pandas-3.0.5.txt` | 否 |
| parso | 0.8.6 | MIT License | `licenses/python/parso-0.8.6.txt` | 否 |
| pillow | 12.2.0 | Historical Permission Notice and Disclaimer (HPND) | `licenses/python/pillow-12.2.0.txt` | 否 |
| pluggy | 1.0.0 | MIT License | `licenses/python/pluggy-1.0.0.txt` | 是 |
| prompt_toolkit | 3.0.52 | BSD License | `licenses/python/prompt_toolkit-3.0.52.txt` | 否 |
| protobuf | 3.19.6 | 3-Clause BSD License | `licenses/python/protobuf-3.19.6.txt` | 否 |
| psutil | 7.2.2 | BSD License | `licenses/python/psutil-7.2.2.txt` | 否 |
| pure_eval | 0.2.3 | MIT License | `licenses/python/pure_eval-0.2.3.txt` | 否 |
| pyarrow | 23.0.1 | Apache Software License | `licenses/python/pyarrow-23.0.1.txt` | 否 |
| pydantic | 2.13.4 | MIT | `licenses/python/pydantic-2.13.4.txt` | 否 |
| pydantic-settings | 2.13.1 | MIT | `licenses/python/pydantic-settings-2.13.1.txt` | 否 |
| pydantic_core | 2.46.4 | MIT License | `licenses/python/pydantic_core-2.46.4.txt` | 否 |
| pydeck | 0.9.1 | Apache License 2.0 | `licenses/python/pydeck-0.9.1.txt` | 否 |
| Pygments | 2.21.0 | BSD License | `licenses/python/Pygments-2.21.0.txt` | 否 |
| pypdf | 6.7.5 | BSD-3-Clause | `licenses/python/pypdf-6.7.5.txt` | 否 |
| pytest | 7.4.4 | MIT License | `licenses/python/pytest-7.4.4.txt` | 是 |
| python-dateutil | 2.9.0.post0 | Apache Software License; BSD License | `licenses/python/python-dateutil-2.9.0.post0.txt` | 否 |
| python-docx | 1.2.0 | MIT License | `licenses/python/python-docx-1.2.0.txt` | 否 |
| python-dotenv | 0.21.0 | BSD License | `licenses/python/python-dotenv-0.21.0.txt` | 否 |
| python-multipart | 0.0.20 | Apache-2.0 | `licenses/python/python-multipart-0.0.20.txt` | 否 |
| pyvis | 0.3.2 | BSD | `licenses/python/pyvis-0.3.2.txt` | 否 |
| PyYAML | 6.0.1 | MIT License | `licenses/python/PyYAML-6.0.1.txt` | 否 |
| referencing | 0.37.0 | MIT License | `licenses/python/referencing-0.37.0.txt` | 否 |
| regex | 2026.9.10 | Apache Software License | `licenses/python/regex-2026.9.10.txt` | 否 |
| reportlab | 4.5.1 | BSD License | `licenses/python/reportlab-4.5.1.txt` | 否 |
| requests | 2.34.2 | Apache Software License | `licenses/python/requests-2.34.2.txt` | 否 |
| requests-toolbelt | 1.0.0 | Apache Software License | `licenses/python/requests-toolbelt-1.0.0.txt` | 否 |
| rich | 14.3.3 | MIT License | `licenses/python/rich-14.3.3.txt` | 否 |
| rpds-py | 0.30.0 | MIT License | `licenses/python/rpds-py-0.30.0.txt` | 否 |
| safetensors | 0.8.0 | Apache Software License | `licenses/python/safetensors-0.8.0.txt` | 否 |
| shellingham | 1.5.4 | ISC License (ISCL) | `licenses/python/shellingham-1.5.4.txt` | 否 |
| six | 1.17.0 | MIT License | `licenses/python/six-1.17.0.txt` | 否 |
| sniffio | 1.3.0 | Apache Software License; MIT License | `licenses/python/sniffio-1.3.0.txt` | 否 |
| soupsieve | 2.8.3 | MIT | `licenses/python/soupsieve-2.8.3.txt` | 否 |
| stack-data | 0.6.3 | MIT License | `licenses/python/stack-data-0.6.3.txt` | 否 |
| starlette | 0.46.2 | BSD-3-Clause | `licenses/python/starlette-0.46.2.txt` | 否 |
| streamlit | 1.56.0 | Apache Software License | `licenses/python/streamlit-1.56.0.txt` | 否 |
| sympy | 1.14.0 | BSD License | `licenses/python/sympy-1.14.0.txt` | 否 |
| tenacity | 8.2.3 | Apache Software License | `licenses/python/tenacity-8.2.3.txt` | 否 |
| tiktoken | 0.14.0 | MIT License | `licenses/python/tiktoken-0.14.0.txt` | 否 |
 
 Copyright (c) 2022 OpenAI, Shantanu Jain
 
 Permission is hereby  | `licenses/python/tiktoken-0.14.0.txt` | 否 |
| tokenizers | 0.22.2 | Apache Software License | `licenses/python/tokenizers-0.22.2.txt` | 否 |
| torch | 2.8.0+cu126 | BSD License | `licenses/python/torch-2.8.0_cu126.txt` | 否 |
| tqdm | 4.70.0 | MIT（个别历史贡献为 MPL-2.0） | `licenses/python/tqdm-4.70.0.txt` | 否 |
| traitlets | 5.14.3 | BSD License | `licenses/python/traitlets-5.14.3.txt` | 否 |
| transformers | 5.5.0 | Apache 2.0 License | `licenses/python/transformers-5.5.0.txt` | 否 |
| truststore | 0.10.4 | MIT | `licenses/python/truststore-0.10.4.txt` | 否 |
| typer | 0.24.1 | MIT | `licenses/python/typer-0.24.1.txt` | 否 |
| typing-inspection | 0.4.2 | MIT | `licenses/python/typing-inspection-0.4.2.txt` | 否 |
| typing_extensions | 4.15.0 | Python Software Foundation License | `licenses/python/typing_extensions-4.15.0.txt` | 否 |
| tzdata | 2023.3 | Apache Software License | `licenses/python/tzdata-2023.3.txt` | 否 |
| urllib3 | 2.2.3 | MIT License | `licenses/python/urllib3-2.2.3.txt` | 否 |
| uuid_utils | 0.15.0 | BSD-3-Clause | `licenses/python/uuid_utils-0.15.0.txt` | 否 |
| uvicorn | 0.34.2 | BSD-3-Clause | `licenses/python/uvicorn-0.34.2.txt` | 否 |
| watchdog | 6.0.0 | Apache Software License | `licenses/python/watchdog-6.0.0.txt` | 否 |
| watchfiles | 1.1.1 | MIT License | `licenses/python/watchfiles-1.1.1.txt` | 否 |
| websockets | 15.0.1 | BSD License | `licenses/python/websockets-15.0.1.txt` | 否 |
| win32_setctime | 1.2.0 | MIT License | `licenses/python/win32_setctime-1.2.0.txt` | 否 |
| xxhash | 3.5.0 | BSD License | `licenses/python/xxhash-3.5.0.txt` | 否 |
| zstandard | 0.23.0 | BSD License | `licenses/python/zstandard-0.23.0.txt` | 否 |
| setuptools | 78.1.0 | MIT | `licenses/python/setuptools-78.1.0.txt` | 否 |
| wcwidth | 0.6.0 | MIT | `licenses/python/wcwidth-0.6.0.txt` | 否 |

各组件版权声明原文见对应全文文件的开头。

---

## 三、前端依赖（npm，104 个）

| 组件 | 版本 | 许可证 | 许可证全文 | 本项目是否修改 |
|-|-|-|-|-|
| @ant-design/colors | 7.2.1 | MIT | `licenses/npm/_ant-design__colors-7.2.1.txt` | 否 |
| @ant-design/cssinjs-utils | 1.1.3 | MIT | `licenses/npm/_ant-design__cssinjs-utils-1.1.3.txt` | 否 |
| @ant-design/cssinjs | 1.24.0 | MIT | `licenses/npm/_ant-design__cssinjs-1.24.0.txt` | 否 |
| @ant-design/fast-color | 2.0.6 | MIT | `licenses/npm/_ant-design__fast-color-2.0.6.txt` | 否 |
| @ant-design/icons-svg | 4.5.0 | MIT | （上游包未随附 LICENSE 文件） | 否 |
| @ant-design/icons | 5.6.1 | MIT | `licenses/npm/_ant-design__icons-5.6.1.txt` | 否 |
| @ant-design/react-slick | 1.1.2 | MIT | `licenses/npm/_ant-design__react-slick-1.1.2.txt` | 否 |
| @babel/runtime | 7.29.7 | MIT | `licenses/npm/_babel__runtime-7.29.7.txt` | 否 |
| @emotion/hash | 0.8.0 | MIT | `licenses/npm/_emotion__hash-0.8.0.txt` | 否 |
| @emotion/unitless | 0.7.5 | MIT | `licenses/npm/_emotion__unitless-0.7.5.txt` | 否 |
| @rc-component/async-validator | 5.1.2 | MIT | `licenses/npm/_rc-component__async-validator-5.1.2.txt` | 否 |
| @rc-component/color-picker | 2.0.1 | MIT | `licenses/npm/_rc-component__color-picker-2.0.1.txt` | 否 |
| @rc-component/context | 1.4.0 | MIT | `licenses/npm/_rc-component__context-1.4.0.txt` | 否 |
| @rc-component/mini-decimal | 1.1.4 | MIT | `licenses/npm/_rc-component__mini-decimal-1.1.4.txt` | 否 |
| @rc-component/mutate-observer | 1.1.0 | MIT | `licenses/npm/_rc-component__mutate-observer-1.1.0.txt` | 否 |
| @rc-component/portal | 1.1.2 | MIT | `licenses/npm/_rc-component__portal-1.1.2.txt` | 否 |
| @rc-component/qrcode | 1.1.3 | MIT | `licenses/npm/_rc-component__qrcode-1.1.3.txt` | 否 |
| @rc-component/tour | 1.15.1 | MIT | `licenses/npm/_rc-component__tour-1.15.1.txt` | 否 |
| @rc-component/trigger | 2.3.1 | MIT | `licenses/npm/_rc-component__trigger-2.3.1.txt` | 否 |
| @tanstack/query-core | 5.101.2 | MIT | `licenses/npm/_tanstack__query-core-5.101.2.txt` | 否 |
| @tanstack/react-query | 5.101.2 | MIT | `licenses/npm/_tanstack__react-query-5.101.2.txt` | 否 |
| @types/d3-color | 3.1.3 | MIT | `licenses/npm/_types__d3-color-3.1.3.txt` | 否 |
| @types/d3-drag | 3.0.7 | MIT | `licenses/npm/_types__d3-drag-3.0.7.txt` | 否 |
| @types/d3-interpolate | 3.0.4 | MIT | `licenses/npm/_types__d3-interpolate-3.0.4.txt` | 否 |
| @types/d3-selection | 3.0.11 | MIT | `licenses/npm/_types__d3-selection-3.0.11.txt` | 否 |
| @types/d3-transition | 3.0.9 | MIT | `licenses/npm/_types__d3-transition-3.0.9.txt` | 否 |
| @types/d3-zoom | 3.0.8 | MIT | `licenses/npm/_types__d3-zoom-3.0.8.txt` | 否 |
| @types/prop-types | 15.7.15 | MIT | `licenses/npm/_types__prop-types-15.7.15.txt` | 否 |
| @types/react-dom | 18.3.7 | MIT | `licenses/npm/_types__react-dom-18.3.7.txt` | 否 |
| @types/react | 18.3.31 | MIT | `licenses/npm/_types__react-18.3.31.txt` | 否 |
| @xyflow/react | 12.11.1 | MIT | `licenses/npm/_xyflow__react-12.11.1.txt` | 否 |
| @xyflow/system | 0.0.78 | MIT | `licenses/npm/_xyflow__system-0.0.78.txt` | 否 |
| antd | 5.29.3 | MIT | `licenses/npm/antd-5.29.3.txt` | 否 |
| classcat | 5.0.5 | MIT | `licenses/npm/classcat-5.0.5.txt` | 否 |
| classnames | 2.5.1 | MIT | `licenses/npm/classnames-2.5.1.txt` | 否 |
| compute-scroll-into-view | 3.1.1 | MIT | `licenses/npm/compute-scroll-into-view-3.1.1.txt` | 否 |
| cookie | 1.1.1 | MIT | `licenses/npm/cookie-1.1.1.txt` | 否 |
| copy-to-clipboard | 3.3.3 | MIT | `licenses/npm/copy-to-clipboard-3.3.3.txt` | 否 |
| csstype | 3.2.3 | MIT | `licenses/npm/csstype-3.2.3.txt` | 否 |
| d3-color | 3.1.0 | ISC | `licenses/npm/d3-color-3.1.0.txt` | 否 |
| d3-dispatch | 3.0.1 | ISC | `licenses/npm/d3-dispatch-3.0.1.txt` | 否 |
| d3-drag | 3.0.0 | ISC | `licenses/npm/d3-drag-3.0.0.txt` | 否 |
| d3-ease | 3.0.1 | BSD-3-Clause | `licenses/npm/d3-ease-3.0.1.txt` | 否 |
| d3-interpolate | 3.0.1 | ISC | `licenses/npm/d3-interpolate-3.0.1.txt` | 否 |
| d3-selection | 3.0.0 | ISC | `licenses/npm/d3-selection-3.0.0.txt` | 否 |
| d3-timer | 3.0.1 | ISC | `licenses/npm/d3-timer-3.0.1.txt` | 否 |
| d3-transition | 3.0.1 | ISC | `licenses/npm/d3-transition-3.0.1.txt` | 否 |
| d3-zoom | 3.0.0 | ISC | `licenses/npm/d3-zoom-3.0.0.txt` | 否 |
| dagre | 0.8.5 | MIT | `licenses/npm/dagre-0.8.5.txt` | 否 |
| dayjs | 1.11.21 | MIT | `licenses/npm/dayjs-1.11.21.txt` | 否 |
| graphlib | 2.1.8 | MIT | `licenses/npm/graphlib-2.1.8.txt` | 否 |
| js-tokens | 4.0.0 | MIT | `licenses/npm/js-tokens-4.0.0.txt` | 否 |
| json2mq | 0.2.0 | MIT | `licenses/npm/json2mq-0.2.0.txt` | 否 |
| lodash | 4.18.1 | MIT | `licenses/npm/lodash-4.18.1.txt` | 否 |
| loose-envify | 1.4.0 | MIT | `licenses/npm/loose-envify-1.4.0.txt` | 否 |
| rc-cascader | 3.34.0 | MIT | `licenses/npm/rc-cascader-3.34.0.txt` | 否 |
| rc-checkbox | 3.5.0 | MIT | `licenses/npm/rc-checkbox-3.5.0.txt` | 否 |
| rc-collapse | 3.9.0 | MIT | `licenses/npm/rc-collapse-3.9.0.txt` | 否 |
| rc-dialog | 9.6.0 | MIT | `licenses/npm/rc-dialog-9.6.0.txt` | 否 |
| rc-drawer | 7.3.0 | MIT | `licenses/npm/rc-drawer-7.3.0.txt` | 否 |
| rc-dropdown | 4.2.1 | MIT | `licenses/npm/rc-dropdown-4.2.1.txt` | 否 |
| rc-field-form | 2.7.1 | MIT | `licenses/npm/rc-field-form-2.7.1.txt` | 否 |
| rc-image | 7.12.0 | MIT | `licenses/npm/rc-image-7.12.0.txt` | 否 |
| rc-input-number | 9.5.0 | MIT | `licenses/npm/rc-input-number-9.5.0.txt` | 否 |
| rc-input | 1.8.0 | MIT | `licenses/npm/rc-input-1.8.0.txt` | 否 |
| rc-mentions | 2.20.0 | MIT | `licenses/npm/rc-mentions-2.20.0.txt` | 否 |
| rc-menu | 9.16.1 | MIT | `licenses/npm/rc-menu-9.16.1.txt` | 否 |
| rc-motion | 2.9.5 | MIT | `licenses/npm/rc-motion-2.9.5.txt` | 否 |
| rc-notification | 5.6.4 | MIT | `licenses/npm/rc-notification-5.6.4.txt` | 否 |
| rc-overflow | 1.5.0 | MIT | `licenses/npm/rc-overflow-1.5.0.txt` | 否 |
| rc-pagination | 5.1.0 | MIT | `licenses/npm/rc-pagination-5.1.0.txt` | 否 |
| rc-picker | 4.11.3 | MIT | `licenses/npm/rc-picker-4.11.3.txt` | 否 |
| rc-progress | 4.0.0 | MIT | `licenses/npm/rc-progress-4.0.0.txt` | 否 |
| rc-rate | 2.13.1 | MIT | `licenses/npm/rc-rate-2.13.1.txt` | 否 |
| rc-resize-observer | 1.4.3 | MIT | `licenses/npm/rc-resize-observer-1.4.3.txt` | 否 |
| rc-segmented | 2.7.1 | MIT | `licenses/npm/rc-segmented-2.7.1.txt` | 否 |
| rc-select | 14.16.8 | MIT | `licenses/npm/rc-select-14.16.8.txt` | 否 |
| rc-slider | 11.1.9 | MIT | `licenses/npm/rc-slider-11.1.9.txt` | 否 |
| rc-steps | 6.0.1 | MIT | `licenses/npm/rc-steps-6.0.1.txt` | 否 |
| rc-switch | 4.1.0 | MIT | `licenses/npm/rc-switch-4.1.0.txt` | 否 |
| rc-table | 7.54.0 | MIT | `licenses/npm/rc-table-7.54.0.txt` | 否 |
| rc-tabs | 15.7.0 | MIT | `licenses/npm/rc-tabs-15.7.0.txt` | 否 |
| rc-textarea | 1.10.2 | MIT | `licenses/npm/rc-textarea-1.10.2.txt` | 否 |
| rc-tooltip | 6.4.0 | MIT | `licenses/npm/rc-tooltip-6.4.0.txt` | 否 |
| rc-tree-select | 5.27.0 | MIT | `licenses/npm/rc-tree-select-5.27.0.txt` | 否 |
| rc-tree | 5.13.1 | MIT | `licenses/npm/rc-tree-5.13.1.txt` | 否 |
| rc-upload | 4.11.0 | MIT | `licenses/npm/rc-upload-4.11.0.txt` | 否 |
| rc-util | 5.44.4 | MIT | `licenses/npm/rc-util-5.44.4.txt` | 否 |
| rc-virtual-list | 3.19.2 | MIT | `licenses/npm/rc-virtual-list-3.19.2.txt` | 否 |
| react-dom | 18.3.1 | MIT | `licenses/npm/react-dom-18.3.1.txt` | 否 |
| react-is | 18.3.1 | MIT | `licenses/npm/react-is-18.3.1.txt` | 否 |
| react-router-dom | 7.18.1 | MIT | `licenses/npm/react-router-dom-7.18.1.txt` | 否 |
| react-router | 7.18.1 | MIT | `licenses/npm/react-router-7.18.1.txt` | 否 |
| react | 18.3.1 | MIT | `licenses/npm/react-18.3.1.txt` | 否 |
| resize-observer-polyfill | 1.5.1 | MIT | `licenses/npm/resize-observer-polyfill-1.5.1.txt` | 否 |
| scheduler | 0.23.2 | MIT | `licenses/npm/scheduler-0.23.2.txt` | 否 |
| scroll-into-view-if-needed | 3.1.0 | MIT | `licenses/npm/scroll-into-view-if-needed-3.1.0.txt` | 否 |
| set-cookie-parser | 2.7.2 | MIT | `licenses/npm/set-cookie-parser-2.7.2.txt` | 否 |
| string-convert | 0.2.1 | MIT | `licenses/npm/string-convert-0.2.1.txt` | 否 |
| stylis | 4.4.0 | MIT | `licenses/npm/stylis-4.4.0.txt` | 否 |
| throttle-debounce | 5.0.2 | MIT | `licenses/npm/throttle-debounce-5.0.2.txt` | 否 |
| toggle-selection | 1.0.6 | MIT | （上游包未随附 LICENSE 文件） | 否 |
| use-sync-external-store | 1.6.0 | MIT | `licenses/npm/use-sync-external-store-1.6.0.txt` | 否 |
| zustand | 4.5.7 | MIT | `licenses/npm/zustand-4.5.7.txt` | 否 |

---

## 四、说明

- 本文件不改变任何组件的原有许可证；各组件的授权条款以其自身 LICENSE 文件为准。
- 本项目自身代码以 Apache-2.0 授权，见仓库根目录 `LICENSE.txt`。
- `CHANGELOG`/版本升级后需重新生成本文件，避免与 `DEPENDENCIES.md` 脱节。
