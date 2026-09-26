# Publication integration — original interface references

核查日期：2026-09-26。以下用于工具适配与边界判断，不能代替用户实际目标期刊／会议当届投稿说明。未镜像第三方完整代码或模板。

- [Overleaf Server Pro Git integration](https://docs.overleaf.com/on-premises/configuration/overleaf-toolkit/server-pro-only-configuration/git-integration)：管理员开启 Git Bridge；原生 Git token。
- [Overleaf Toolkit settings](https://docs.overleaf.com/on-premises/configuration/overleaf-toolkit/toolkit-settings)：GIT_BRIDGE_ENABLED 为 Server Pro 功能，默认关闭。
- [Overleaf Git authentication tokens](https://docs.overleaf.com/integrations-and-add-ons/git-integration-and-github-synchronization/git-integration/git-integration-authentication-tokens)：Git 用户名 git、专用 token；不将普通密码作为 token。
- [Overleaf Workshop package](https://github.com/overleaf-workshop/Overleaf-Workshop/blob/master/package.json)：本次核查版本 0.15.10，publisher iamhyc，扩展 id iamhyc.overleaf-workshop，addServer 等真实命令。
- [Overleaf Workshop Wiki](https://github.com/overleaf-workshop/Overleaf-Workshop/blob/master/docs/wiki.md)：自建 CE/Pro、email/password/cookie 登录、Open Project Locally、Replica 元数据、已有路径覆盖风险、网络不稳定时的功能限制。它属于社区扩展。
- [VGTC journal-track templates](https://tc.computer.org/vgtc/publications/journal/)：TVCG 特刊与普通投稿／短文的范围区分。
- [VGTC June 2026 release](https://github.com/ieeevgtc/tvcg-journal-latex/releases/tag/2026.06.26)：真实官方发布；无独立 asset，GitHub 提供源码 zipball。获取失败时不能伪称已下载。
- [VIS 2026 paper guidelines](https://ieeevis.org/year/2026/info/call-participation/paper-submission-guidelines/)：仅作为该届官方发现入口，后续届次需重新搜索，不复制截止日期。
- [ACM proceedings templates](https://www.acm.org/publications/proceedings-template) 与 [Overleaf ACM Gallery](https://www.overleaf.com/latex/templates/acm-conference-proceedings-primary-article-template/wbvnghjbzwpc)：模板来源仍需结合实际会议、稿件类型和阶段。

安全设计采用显式网络／执行／远端写入权限、限定稿件子树、精确主机、校验哈希及冲突保留。原始说明中的可选明文凭据保存方式没有作为推荐接入；默认使用 OS 管理器或不回显的进程内 token。仅在本机可信模板上进行 TeX 编译；禁用 shell escape 不等于 OS 沙箱。
