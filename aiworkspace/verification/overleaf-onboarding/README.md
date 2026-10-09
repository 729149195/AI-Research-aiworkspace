# 自然语言 Overleaf 接入与本地验收助手：验证记录

基于仓库 main 提交 `1889d4d4572c8ea918fb2f0c6bfcf38cb125514f`，本轮日期 2026-10-09。核心引擎仍为 0.6.1，研究 Schema、15 个 Skills 和菜单编号不变。

## 实际完成

用户文档改为自然语言办理，技术命令移至 Agent 手册；overleaf-sync 明确复用 Workshop、已登录状态、实际项目与目录，并禁止网页 computer use、认证 HTTP 下载和自动 Git 回退。已有用户的未迁移路径与稿件保持不动。

新增按次运行的本地 VS Code 验收助手和 Agent 包装脚本。通过 Workshop 文件系统提供者核对项目身份与主文件，验证一个临时非研究 PNG 文件的本地→远端、远端→本地、清理及原稿哈希。程序不读取账号存储、不自行连接 HTTP、不承担持续同步，也不因配置存在就标记 verified。

本轮 **44 项测试通过，0 失败、0 错误、0 跳过**：20 项 Python 请求／状态／原稿保护／VSIX／文档测试，24 项 Node 探针／故障注入／路径／项目身份测试。Node 使用真实临时文件系统和模拟的插件传播，部分 VS Code API 为明确的测试替身；这些测试不代表运行过真实编辑器或认证过 Overleaf。

另实际调用独立 Python 进程生成本地 VSIX，检查 ZIP 清单、XML 和运行文件；执行 Node syntax check 与 Python compile check。VSIX 未提交到 Marketplace，交付环境也没有实际安装 VS Code。GitHub 配置了独立工作流，但其结果必须读取对应提交的真实 Actions，不能由本地测试推断。

## 明确保留的限制

- 没有用户的自建站登录，没有执行实际 VS Code 安装、URI 分发、Workshop 认证或双向服务器联调。
- 上游部分配置命令仍使用原生弹窗，没有稳定的通用无头服务器／Replica 初始化 API。Agent 有编辑器操作能力时处理非秘密步骤；否则用户只完成必要原生提示，不操作代码。
- 主文件读取可能来自插件缓存。探针走二进制文件路径，结果只代表一次文件级往返，不证明所有正文 OT、附件过滤和长期稳定性。
- 完整 core 科研回归、模型效果、单工作区路径迁移、旧 ZIP 接入补丁合并均不在本轮范围。
- `.rw/overleaf-agent/` 记录是本机观察记录，无服务器签名；文件或绑定变化、时间过久会被标记为历史记录。不要将手填布尔值冒充工具运行结果。

## 维护者复测

```bash
python -m unittest discover -s aiworkspace/tests -p test_overleaf_agent.py -v
node --test aiworkspace/integrations/overleaf-assistant/probe.test.js
python aiworkspace/scripts/overleaf_agent.py build --output /新路径/overleaf-assistant.vsix
```

普通用户只看 [自然语言入口](../../docs/OVERLEAF.md)，安装和上述操作由 Agent 在授权后完成。具体版本与源文件哈希见 tests.json。
