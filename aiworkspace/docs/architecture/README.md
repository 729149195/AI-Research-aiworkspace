# README 架构图的源文件与显示产物

这三张图随仓库提交，根 README 使用相对路径直接引用 SVG。读者无需安装 Mermaid，也不依赖在线绘图服务或聊天附件。

| 文件名 | 图的职责 |
|---|---|
| `architecture` | 唯一 aiworkspace、八类研究内容、稿件与 Overleaf-Workshop 的目标关系 |
| `workflow` | 改前检查、执行、捕获、影响分析、审查与交接 |
| `maintenance` | 可更新工具与受保护论文数据的边界 |

每图包含 `.mmd` 可编辑源和 `.svg` 显示产物。`manifest.json` 记录两者哈希及导出环境，防止只改源码却忘记更新首页图片。总架构是确定采用的目标；当前引擎的旧路径与迁移差异见根 README，不能依据图片移动真实论文。

## 修改与导出

先修改 Mermaid 源，再在本机授权的 Mermaid 工具中导出。当前使用 Mermaid 11.12.2、neutral 主题、16px 字号；全局及 flowchart 的 `htmlLabels` 均为 false。SVG 使用实际 text/tspan，不使用 foreignObject、脚本、外部资源、内嵌字体或远端渲染服务。保留白色底板，避免深色页面透底。

导出后检查浏览器以 img 方式显示的实际 SVG：中文、标签、箭头、留白和最终显示尺寸均应核对。查看矢量源时正常，不代表作为图片嵌入也正常。更新 manifest 中源文件与图片的 SHA-256；新布局还应同步更新 README 的替代文字和说明。

维护者运行 `python aiworkspace/scripts/check_readme_images.py` 检查三张图片是否被首页实际引用、文件是否存在、是否使用可移植 SVG、源码与产物哈希是否一致。检查只读、不联网；它不证明 GitHub 浏览器已加载图片，也不检查研究代码是否实现图中的目标架构。

发布时将 README、图文件、源文件和清单放在同一个提交里，并重新读取远端 main 核对。不得使用 sandbox 路径、临时文件地址、仅本机存在的图片或单纯把架构图链接写成普通文字链接。

## GitHub 格式依据

- [仓库内图片与相对链接](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax)
- [Mermaid 图表支持](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams)

本次发布前实际完成三图本地 Mermaid 解析和导出、以 img 嵌入的浏览器检查以及 390px 页面宽度检查。未执行真实 GitHub 浏览器会话或完整科研回归；不据此声称研究目录迁移、Overleaf 认证或云端 CI 已完成。
