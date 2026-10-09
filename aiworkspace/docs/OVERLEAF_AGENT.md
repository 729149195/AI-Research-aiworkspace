# Overleaf：Agent 执行与真实验收手册

用户说明见 [OVERLEAF.md](OVERLEAF.md)。本页接管旧 AGENT_PLAYBOOK 中的 Overleaf 片段及旧引擎生成的命令式 setup guide；不要将旧说明作为终端任务交给用户。本页的命令、路径与请求 ID 由 Agent 操作，不能作为用户作业。当前用户指定 **Overleaf-Workshop** 为标准接入通道，禁止 computer use 网页下载、认证 HTTP 下载、读取浏览器 cookie 数据库或自动回退 Git。既有 Git 用户的源码保留，但不能未经确认更换其连接。

## 1. 先复用实际环境

读取当前明确选择的项目与已有非秘密连接配置。已有工作目录和绑定优先，不扫描用户家目录，不自动迁移旧论文。缺少目标时只问论文链接或名称；从常规 HTTPS `/project/ID` 链接解析服务器和 ID，拒绝带密码、查询 token 和共享密钥的链接。默认自建服务器为 https://nankaivisoverleaf.asia/。

检查宿主实际是否支持本地文件、进程、编辑器命令、插件窗口及 URL handler。纯网页聊天和只连接远程 SSH 的进程不能控制本机 VS Code。必要时让用户只打开正确的本地窗口／完成授权，不让用户输入命令来弥补工具缺口。

通过编辑器 API或 `code --list-extensions --show-versions` 读取插件版本，复用已安装且可用的 `iamhyc.overleaf-workshop`。只有确实缺失才集中申请安装；不要默认强制安装老的 0.15.10、降级可用版本或使用 --force。实际版本与范围写入结果。安装插件与安装本地验收助手分别需权限，均不触及模型或账号配置。

## 2. 通过插件建立本地 Replica

核查当前版本的实际插件入口。上游注册了 `overleaf-workshop.projectManager.addServer`、login／项目选择及 `overleaf-workshop.projectManager.openProjectLocalReplica` 等命令；部分命令要求真实的项目树项，不能编造对象。所核对版本的 Add Server 会打开输入框，没有稳定的“传 URL 即无头添加”公共 API。宿主可操作编辑器控件时由 Agent 填写非秘密信息；否则只引导一个必要的本机原生对话框，不宣称后台自动完成。

登录只在插件 UI 里完成，复用现有会话。SSO／CAPTCHA 所需本人浏览器登录不授权 Agent 抽取会话秘密。新建／绑定 Replica 要先检查实际版本对目标目录的行为；不预建会导致插件自动追加项目名的错误路径，不覆盖旧稿。插件当前对单文件夹 Replica 窗口有依赖；需要时在独立窗口打开真实 manuscript 副本，Agent 对完整研究根目录仍保有明确的文件权限。

读取插件实际生成的 `.overleaf/settings.json`，核对 host、project ID 和路径。这个文件是连接定位元数据，不是登录凭据，也不是网络连通证据。不能伪造该文件来跳过登录。内容不同就保留差异，不执行旧的 flatten/adopt 来凑成一致。单工作区／原样导入迁移尚未落地的用户，应继续使用已有可用绑定，报告缺口。

## 3. 可执行的一次性连通验收

若宿主已经提供可信、可审查的插件测量工具，可直接用其工具回执。否则，本仓库新增 `integrations/overleaf-assistant/` 辅助扩展（本地 ID：`aiworkspace-local.overleaf-assistant`）。它通过标准 VS Code 文件系统调用 `iamhyc.overleaf-workshop`，不实现另一套 Overleaf 登录或同步服务。源码无 npm 运行依赖，只有 Node 内置模块与 VS Code API。

Agent 在源码根目录、经许可后执行以下步骤；用真实路径替换参数，不让用户填写占位符。

```bash
python aiworkspace/scripts/overleaf_agent.py build --output /本地新目录/overleaf-assistant.vsix
code --install-extension /本地新目录/overleaf-assistant.vsix
python aiworkspace/scripts/overleaf_agent.py --project /实际论文根目录 prepare https://真实服务器/project/真实ID --mode roundtrip
```

先查看插件安装情况；本地 VSIX 与 Marketplace 发布无关，不存在已上架的同名保证。构建只生成安装包，不会自行安装。真实 VS Code 接受与加载仍须看执行结果；插件首次信任提示由用户处理，不跳过安全限制。

prepare 自动使用当前非秘密 Workshop 绑定，否则选择 manuscript。主文件从项目元数据或实际源文件识别；多主文件时 Agent 根据 Overleaf 编译设置传 `--main`，无法判断再问一次。该命令只保存请求，不运行远端动作。返回 `launch_uri` 后，Agent 使用当前宿主已授权的 URL opener／VS Code URI handler 调用它；支持直接编辑器命令的宿主可调用 `aiworkspace.overleaf.check` 并传实际 request_id。不要臆造通用的 `code --execute-command` 参数。

URI handler 由当前前台本地单目录窗口处理。请求与报告必须处于同一根目录，不能在错误窗口反复重试。普通 VS Code 的 scheme 是 vscode；其他变体按其真实 `vscode.env.uriScheme` 选择，不假定通用兼容。插件端要求 Workshop 已在该窗口激活，不会为了检查自动激活一个闲置的同步引擎。每次仍会展示目标项目和测试范围，确认后才读远端或写测试文件。只读限定验收助手，不能停止已经授权运行的 Workshop 自身同步。

Agent 读取实际报告：

```bash
python aiworkspace/scripts/overleaf_agent.py --project /实际论文根目录 status 实际request_id
```

只有满足以下全部条件才能汇报本轮文件级双向检查通过：目标 metadata_matched、主文件哈希匹配、local_to_remote、remote_to_local、cleanup 均为 true，检查范围内原稿前后哈希一致，记录指向当前 host、project、directory，且没有过期／后续变更。

**缓存边界：** Workshop 的 `.tex` 文档读取可能命中 remoteCache，读取它与本地一致不能单独证明新鲜网络通信。助手使用随机命名、含随机值的 1×1 透明 PNG 测试文件；所核对的插件二进制路径通过 getFile 访问服务器。上传由本地 Replica watcher 执行，随后从远端侧更新并观察本地，期间不人为复制文件伪造同步。这个探针只验证一次二进制文件收发；`.tex` 的 OT、每种忽略规则和长期稳定性要分别验证。源码与用户说明都保留此边界。

## 4. 失败处理与授权

测试文件不被正文引用。其创建和删除仍可能留在 Overleaf 历史，授权提示要讲清楚。拒绝远端测试时改用 `--mode read`，结果只能是 readable_via_plugin 或未完成，不能冒充可写／可同步。

每个新请求都有随机 ID 与 10 分钟启动时限，重复调用已经有报告的请求不会重复写入。出现登录、权限、超时、路径、源文件变化等问题时保存失败状态，不能把 FileNotFound 以外的网络错误当成“文件不存在”。中断可能留下明确命名的测试文件；保留现场，由 Agent 核对其内容及双方状态后申请有范围的清理，禁止盲删或覆盖第三人的新改动。

报告是本机观察记录，不是服务器签名证明。主文件、其他稿件或 Replica 绑定变化后，status 标记 historical／changed_since_check；成功不保证插件仍在运行。结束语给用户实际项目、时间、收发范围与唯一必要的阻塞项，不展示命令、内部 ID 和错误堆栈。

## 5. 与现有框架的边界

本次不迁移旧的 workspace/ 路径，也不更改研究 Schema、稿件或 Git 连接算法。辅助请求与检查报告暂存当前已忽略的 `.rw/overleaf-agent/`，将来只由正式迁移器移入单工作区运行区。不要用“配置已应用”或旧生成说明替代这个验收流程，也不要修改 `live_connection_verified` 的布尔字段来伪造验证。

纯 wheel 安装不一定包含 integrations 与 scripts；应从同版本源码 checkout 构建助手，或明确报告缺少配套材料，不搜索并安装来历不明的扩展。后续通过 Git 增量更新源码、升级已登记的 Skill；本地助手更新需要重新构建并经授权安装，不自动覆盖用户插件设置。

## 上游依据

核查时间 2026-10-09。仅复用已有接口，不复制上游登录实现：

- [Workshop Wiki：自建服务器与 Local Replica](https://github.com/overleaf-workshop/Overleaf-Workshop/blob/master/docs/wiki.md)
- [项目管理命令与原生弹窗](https://github.com/overleaf-workshop/Overleaf-Workshop/blob/master/src/core/projectManagerProvider.ts)
- [文件系统：openFile 的缓存／二进制路径与写入行为](https://github.com/overleaf-workshop/Overleaf-Workshop/blob/master/src/core/remoteFileSystemProvider.ts)
- [VS Code 命令 API](https://code.visualstudio.com/api/extension-guides/command)
- [VS Code API：registerUriHandler 与 workspace.fs](https://code.visualstudio.com/api/references/vscode-api)
- [VS Code 本地 VSIX 安装](https://code.visualstudio.com/docs/configure/extensions/extension-marketplace)

检查的源码 blob：projectManagerProvider 与 remoteFileSystemProvider 以本轮连接读取为准；实际运行必须记录已安装扩展版本，不以 GitHub master 代替用户环境。完整限制见 [验证记录](../verification/overleaf-onboarding/README.md)。
