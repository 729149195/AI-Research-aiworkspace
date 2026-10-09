# 本地 Overleaf 验收助手

此目录是由 Agent 构建与安装的可选 VS Code 辅助扩展。用户入口见 [自然语言接入](../../docs/OVERLEAF.md)，技术操作见 [Agent 手册](../../docs/OVERLEAF_AGENT.md)。

它按次复用 **Overleaf-Workshop** 的 VS Code 文件系统提供者检查项目身份、主文件匹配、一个临时二进制文件的双向传播、清理与原稿完整性。它不持有账号、不调用 Overleaf HTTP API、不承担持续同步、不启动后台服务器、不绕过原生登录或授权。只读检查也会单独提示，且不报告写入通过。

`probe.js` 是独立探针，`extension.js` 是 VS Code 适配层，`package.json` 声明 URI handler 和一个命令。`probe.test.js` 使用模拟插件传输与真实临时文件系统；不是 VS Code／Overleaf 认证联调。Python 构建助手仅将明确的运行文件与 MIT 许可打包，测试或本机配置不会进入 VSIX。

本地扩展 ID 为 `aiworkspace-local.overleaf-assistant`；没有在 Marketplace 发布，也没有假定各 VS Code 分支、SSH／WSL／多根目录或所有版本均可用。使用者仍需已有可访问的 Workshop Replica。初次添加服务器与 Replica 可能要求原生插件弹窗，因为上游没有稳定通用的无头配置接口。编辑器界面操作由有能力的 Agent 处理，缺失能力时仅请用户处理必要本机提示，不让用户写代码。

成功只代表记录时间内、指定项目和文件范围的一次检查。测试文件未被论文引用，但创建与清理可能出现在 Overleaf 历史。失败保留不确定状态和文件名；不盲删出现第三方修改的文件。 `.tex` 缓存、OT 协作、所有附件及长期网络稳定性不由一次二进制探针证明。
