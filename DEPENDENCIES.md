## 一、服务端依赖（Python）


| #  | 依赖              | 版本约束  | 实测版本    | 许可证          | 用途                                                       | 发行包             |
| ---- | ------------------- | ----------- | ------------- | ----------------- | ------------------------------------------------------------ | -------------------- |
| 1  | fastapi           | >=0.104.0 | 0.115.12    | MIT             | API 服务框架，`api/main.py` 与 4 个 router                 | 主路径             |
| 2  | uvicorn[standard] | >=0.24.0  | 0.34.2      | BSD-3-Clause    | ASGI 服务器，启动脚本使用                                  | 主路径             |
| 3  | streamlit         | >=1.29.0  | 1.56.0      | Apache-2.0      | legacy 控制台（`frontend/`，19 个文件引用）                | 主路径（可选组件） |
| 4  | requests          | >=2.31.0  | 2.34.2      | Apache-2.0      | Streamlit 控制台、SDK 示例与演示脚本调用 API               | 主路径             |
| 5  | python-dotenv     | >=0.21.0  | 0.21.0      | BSD-3-Clause    | 读取 `.env`（`scripts/`）                                  | 主路径（仅脚本）   |
| 6  | python-multipart  | >=0.0.6   | 0.0.20      | Apache-2.0      | 读取trace文件和HTML表单                                    | 主路径（可选）     |
| 7  | langchain         | >=0.1.0   | 1.4.7       | MIT             | 无直接引用；由 `langchain-openai` 传递引入                 | 传递               |
| 8  | langchain-openai  | >=0.0.5   | 1.7.2       | MIT             | 仅 `scripts/debug_openrouter.py` 使用                      | 仅调试             |
| 9  | langgraph         | >=0.0.10  | 1.2.17      | MIT             | 检测 Agent 工作流（`src/agents/detection_agent.py`）       | 主路径（可选）     |
| 10 | openai            | >=1.10.0  | 3.24.0      | Apache-2.0      | 模型调用客户端（`src/agents/model_clients.py`）            | 主路径             |
| 11 | anthropic         | >=0.10.0  | 2.3.0       | Apache-2.0      | **零引用**（源码、测试、评测均未导入）                     | 主路径（可选）     |
| 12 | networkx          | >=3.2.1   | 3.6.1       | BSD-3-Clause    | 安全执行图核心（11 个文件引用）                            | 主路径             |
| 13 | pyvis             | >=0.3.2   | 0.3.2       | BSD             | 将Python图渲染为HTML（预留，当前使用内置 `lib/vis-9.1.2`） | 主路径（可选）     |
| 14 | pydantic          | >=2.5.0   | 2.13.4      | MIT             | 数据模型与校验                                             | 主路径             |
| 15 | pydantic-settings | >=2.1.0   | 2.13.1      | MIT             | 配置加载（`config/settings.py`）                           | 主路径             |
| 16 | numpy             | >=1.26.0  | 2.5.3       | BSD-3-Clause 等 | 无直接引用；由 torch / transformers 传递引入               | 传递               |
| 17 | transformers      | >=4.36.0  | 5.5.0       | Apache-2.0      | 节点嵌入检测（`src/detection/node_embedding.py`）          | 可选（ML 能力）    |
| 18 | torch             | >=2.1.0   | 2.8.0+cu126 | BSD-3-Clause    | GNN 风险传播与嵌入检测模型                                 | 可选（ML 能力）    |
| 19 | loguru            | >=0.7.2   | 0.7.3       | MIT             | 日志（`src/utils/logger.py`）                              | 主路径             |
| 20 | pyyaml            | >=6.0.1   | 6.0.1       | MIT             | Policy Pack 与规则加载                                     | 主路径             |
| 21 | beautifulsoup4    | >=4.12.0  | 4.14.3      | MIT             | HTML 解析（`frontend/pages/10_手动输入检测.py`）           | 主路径（仅页面）   |
| 22 | pypdf             | >=3.9.0   | 6.7.5       | BSD-3-Clause    | PDF 解析（同上页面）                                       | 主路径（仅页面）   |
| 23 | python-docx       | >=1.0.0   | 1.2.0       | MIT             | docx 解析（同上页面）                                      | 主路径（仅页面）   |
| 24 | reportlab         | >=4.0.0   | 4.5.1       | BSD             | PDF 报告导出（`src/utils/report_exporter.py`）             | 主路径             |
| 25 | pytest            | >=7.4.0   | 7.4.4       | MIT             | 测试框架（`tests/`，不在运行时路径）                       | 开发/测试          |

---

## 二、前端依赖（`web-console/`）

### 2.1 直接依赖


| # | 依赖                  | 版本约束 | 实测版本 | 许可证 | 用途                  |
| --- | ----------------------- | ---------- | ---------- | -------- | ----------------------- |
| 1 | react                 | ^18.3.1  | 18.3.1   | MIT    | UI 框架               |
| 2 | react-dom             | ^18.3.1  | 18.3.1   | MIT    | React DOM 渲染        |
| 3 | react-router-dom      | ^7.1.1   | 7.18.1   | MIT    | 路由（12 个页面路由） |
| 4 | antd                  | ^5.22.6  | 5.29.3   | MIT    | 组件库                |
| 5 | @ant-design/icons     | ^5.5.2   | 5.6.1    | MIT    | 图标                  |
| 6 | @tanstack/react-query | ^5.62.8  | 5.101.2  | MIT    | 服务端状态管理与轮询  |
| 7 | @xyflow/react         | ^12.3.5  | 12.11.1  | MIT    | 执行图可视化          |
| 8 | dagre                 | ^0.8.5   | 0.8.5    | MIT    | 图自动布局算法        |
| 9 | dayjs                 | ^1.11.13 | 1.11.21  | MIT    | 时间格式化            |

### 2.2 传递依赖

第三方生产依赖合计 **104 个**，许可证分布：MIT 95、ISC 8、BSD-3-Clause 1。

---

## 三、随仓库分发的第三方代码

以下组件**不在任何包管理器内**，已进行手工登记：


| 组件                     | 版本       | 许可证                                                | 位置                                                          |
| -------------------------- | ------------ | ------------------------------------------------------- | --------------------------------------------------------------- |
| vis-network              | 9.1.2      | Apache-2.0 或 MIT（双许可，本项目按 Apache-2.0 使用） | `lib/vis-9.1.2/vis-network.min.js`、`vis-network.css`         |
| vis-network 示例辅助脚本 | 随 9.1.2   | 同上                                                  | `lib/bindings/utils.js`                                       |
| Tom Select               | 2.0.0-rc.4 | Apache-2.0                                            | `lib/tom-select/tom-select.complete.min.js`、`tom-select.css` |

> 依 Apache-2.0 第 4(b) 条，若上述文件被修改，必须显著标注"已修改"。当前三个组件均未修改，归属声明统一写在 `THIRD_PARTY_NOTICES.md`。

---

## 四、特殊条款依赖（LGPL / MPL / AGPL）

**直接依赖：无。** 24 条服务端直接依赖与 9 条前端直接依赖的许可证全部为 MIT / BSD / Apache-2.0 / ISC，与 Apache-2.0 项目完全兼容。

**传递依赖**：本项目依赖共 **228 个包**——服务端 **124** 个（由 `requirements.txt` 全新解析），前端 **104** 个（`license-checker --production`，已排除项目自身的私有包）。

逐包核查这两个闭包的结论：

- 前端 104 个全部为 MIT / ISC / BSD-3-Clause；
- 服务端 124 个中**无 GPL / AGPL / LGPL**，但有 **2 个 MPL-2.0 相关包**，须单独披露：


| 包      | 实测版本 | 许可证                          | 引入方                             |
| --------- | ---------- | --------------------------------- | ------------------------------------ |
| certifi | 2025.8.3 | MPL-2.0                         | `requests` 的硬依赖                |
| orjson  | 3.11.8   | MPL-2.0 AND (Apache-2.0 OR MIT) | `langsmith`（观测链路）            |

以上均已在 `THIRD_PARTY_NOTICES.md` 中披露。逐项说明：

- **`certifi`（MPL-2.0）**：纯 MPL-2.0。本项目仅将其作为 TLS 根证书包原样分发，未修改任何文件，不触发 MPL 的文件级公开义务。
- **`orjson`（MPL-2.0 AND (Apache-2.0 OR MIT)）**：**不是三选一，而是"同时适用"**。该包随附 `LICENSE-APACHE`、`LICENSE-MIT`、`LICENSE-MPL-2.0` 三份文件，不同代码部分适用不同许可。本项目未修改该包。
- **`tqdm`（MIT，个别历史贡献为 MPL-2.0）**：其 LICENSE 原文注明"除下列例外外，所有作者均按 MIT 许可发布"，MPL 仅覆盖个别历史贡献；本项目未修改该包，按 MIT 使用。
