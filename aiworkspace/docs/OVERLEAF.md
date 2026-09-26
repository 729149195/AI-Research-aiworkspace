# 自建 Overleaf 与本地同步（0.3.0）

默认服务器：`https://nankaivisoverleaf.asia/`。可以改为自己的 HTTPS 根网址、项目 ID 和稿件相对目录。账号、token、cookie 不写入 Workspace、Git 仓库或聊天。配置保存在论文项目 `.rw/overleaf.json`，只包含主机、路径、模式和身份来源说明。

## 先选一种同步通道

| 模式 | 条件 | 连接与同步 |
|---|---|---|
| `workshop`（默认） | 安装第三方 Overleaf Workshop，服务器允许其登录／API／WebSocket | 由扩展管理账号和本地 Replica，同步由活跃编辑器负责 |
| `git` | 自建 Server Pro 已由管理员启用 Git Bridge，项目菜单有 Git 入口 | Git 专用 token／OS 凭据管理器，框架执行显式同步或前台短周期同步 |

Overleaf 原生 Git Bridge 的部署和认证依据 [官方部署文档](https://docs.overleaf.com/on-premises/configuration/overleaf-toolkit/server-pro-only-configuration/git-integration) 与 [Git token 文档](https://docs.overleaf.com/integrations-and-add-ons/git-integration-and-github-synchronization/git-integration/git-integration-authentication-tokens)。不能假定任意 Community Edition 实例自带 Git；管理员许可与开启状态无法由填写网址推断。

Overleaf Workshop 是独立社区扩展，实际 ID `iamhyc.overleaf-workshop`；本集成核查版本 0.15.10。它支持自建 Community Edition／Server Pro，登录和 Replica 接口参见 [上游 Wiki](https://github.com/overleaf-workshop/Overleaf-Workshop/blob/master/docs/wiki.md)。上游对不稳定网络中的 Local Replica 有明确稳定性警告，请保留独立版本备份。同一稿件目录只选一个同步引擎，避免插件和 Git 互相覆盖。

## A. VS Code / Overleaf Workshop

以下在**论文项目根目录**、已安装框架的虚拟环境运行：

```bash
rw overleaf install-plugin
rw overleaf install-plugin --approve
rw overleaf configure --server https://nankaivisoverleaf.asia/ --project-id 实际项目ID --directory manuscript/latex/实际目录 --mode workshop --approve
```

第一行只显示安装命令；第二行通过 VS Code CLI 安装指定版本，不读取账号或自动登录。VSCodium 可加 `--editor codium`，扩展源可用性由本机环境决定。没有编辑器 CLI 时，在扩展面板按 ID 搜索并安装。第三行只保存局部配置和 `workspace/reports/overleaf-setup.md`，不会宣称连接成功。

在编辑器中完成一次性登录：

1. Overleaf Workshop 面板选择 **Add New Server**，填写 `https://nankaivisoverleaf.asia/`，不要追加 `/project`。
2. 选择服务器登录。普通账号通过扩展的 email/password 界面输入；启用 SSO／CAPTCHA 时先在自己的浏览器登录，再使用扩展 **Login with Cookies**。仅将当前自建服务器的登录 cookie 粘贴到本机扩展登录框；不要发给 AI。Git 专用 token 不能替代浏览器会话 cookie。
3. 可在网页或扩展中创建 **Upload Project**，上传由下面命令生成的 ZIP；也可选择已有远端项目。项目 ID 从浏览器 `/project/<id>` 取得。
4. 右键远端项目选 **Open Project Locally...**，选择新的空父目录，例如 `my-paper/manuscript/replicas/`。扩展会在其下创建以远端项目命名的目录。**上游明确说明：同路径已存在时会覆盖。务必避开唯一原稿副本。**
5. 在本地 Replica 中打开编辑器并确认 Source Control 已启用。首次分别做一个小改动，检查本地→网页、网页→本地，再开始正式协作。不要用 Invisible Mode 代替实时协作。

```bash
rw latex pack --directory manuscript/latex/实际目录 --output ../paper-for-overleaf.zip
# 上传后，Replica 与当前活跃稿件字节一致时：
rw overleaf bind-replica --directory manuscript/replicas/实际项目名称
rw overleaf bind-replica --directory manuscript/replicas/实际项目名称 --approve
```

bind-replica 会核对扩展生成的 `.overleaf/settings.json` 中服务器、项目 ID，以及源码内容一致性，不伪造该文件或写入扩展私有登录数据库。存在差异时先人工／Skill 核对，不直接覆盖。尚未绑定研究章节的普通 Replica，可先执行 `rw latex adopt --directory ... --main main.tex --approve --actor ai:session`。

编辑器运行期间，扩展负责云端协作；auto-route 在本轮操作和后续捕获中记录 `.tex` 差异并维护研究图。扩展关闭后没有来自它的实时同步。普通网页聊天也不能监听本地文件。登录完成与稳定双向通信须在用户环境验证。

## B. 原生 Git Bridge

先在项目菜单复制真实 Git URL，并确认服务器管理员已启用该功能。框架可生成默认路径，但界面提供的地址优先：

```bash
rw overleaf configure --server https://nankaivisoverleaf.asia/ --project-id 实际项目ID --directory manuscript/latex/实际目录 --mode git --git-url https://nankaivisoverleaf.asia/git/实际项目ID --approve
rw overleaf sync --online --token-prompt
rw overleaf sync --online --token-prompt --approve --actor ai:session
```

token 在 Overleaf 的 Account Settings → Git authentication tokens 中生成。用户名为 `git`；普通账号密码和浏览器 cookie 均不用于该通道。`--token-prompt` 使用不回显输入，只存活于当前进程。长期使用可在本机配置系统钥匙串支持的 Git credential helper；避免明文 `credential.helper store`。环境变量 `RW_OVERLEAF_TOKEN` 也仅供进程读取，不应写进脚本、命令参数、.env 或公开配置。

不加 `--approve` 只获取远端对象并预览本地／远端／基线差异，不改正文或远端。初次两边存在不同的同名文件时会停下，不猜覆盖方向。确认后显式选择：

```bash
rw overleaf sync --online --approve --resolve main.tex=local --actor ai:session
# 或 --resolve main.tex=remote；删除还需要 --allow-deletions
```

持续同步在前台运行，默认每 5 秒检查，按 Ctrl+C 停止：

```bash
rw overleaf watch --online --token-prompt --approve --actor ai:session --interval 5
```

这是近实时轮询，具有文件级三方合并和冲突暂停；它不提供网页编辑器的逐字符协同协议。无变化不重复提交；从不 force-push。仅上传配置选中的 manuscript 子目录，其他研究原文、状态、记录与 `.rw` 保持本地。仍需由用户检查该子目录中是否含敏感附件或可识别信息。

网络中断后远端是否接受推送不明确时，保留 pending 记录：

```bash
rw overleaf recover --online
```

恢复先核对实际远端和本地字节，不覆盖中断之后的新编辑。无法自动恢复时保留两边和 `.rw/overleaf`，依照错误提示人工核对；不要删除基线或强制推送。转投后活跃目录改变，会拒绝沿用旧远端绑定。确认备份和 pending 已处理后，`rw overleaf disconnect --approve` 归档本地同步历史，再配置新的项目。该命令不删除远端项目或正文。

## 验证范围

已测试配置、凭据边界、冲突／恢复逻辑及真实本地 Git bare-repository 收发。未提供自建服务器账号，交付环境也没有完整 VS Code 登录会话，因此未声称已经在 nankaivisoverleaf.asia 完成真实登录和实时联调。无需将账号发给 AI；按上述本地登录步骤完成最后一段连接验收。
