# 独立仓库交付与验收记录

版本 0.1.0；Schema 1；验证日期 2026-09-23。

正式仓库为 [729149195/AI-Research-aiworkspace](https://github.com/729149195/AI-Research-aiworkspace)。用户创建空仓库后，框架以独立提交历史发布；当前文件树仅有 `aiworkspace/`、`update_aiworkspace.py`、`README.md` 和隐藏的 Git/CI 配置。没有其他应用文件，不依赖旧仓库运行。本次未修改或删除旧仓库。

## 本次实际验收

环境：Linux / Python 3.13.5；下列记录来自修正新仓库地址后的本地执行。

| 检查 | 结果 | 记录 |
|---|---|---|
| 单元与回归测试 | 77 项通过，0 失败、0 错误、0 跳过 | [unit-tests.json](verification/unit-tests.json) |
| 现有项目更新／回滚 | 当前目录、旧目录迁移两种场景均通过；真实 Git fetch、快进和 editable 安装 | [root-update.json](verification/root-update.json) |
| 全新 wheel 安装 | 全新虚拟环境，在源码目录外运行 doctor，9 个 Skill 契约通过 | [installed-doctor.json](verification/installed-doctor.json) |
| 完整合成演示 | 实际计算、图表、证据链、双向同步、质量门、更新／回滚和演示导出通过 | [installed-demo.json](verification/installed-demo.json) |
| 文档与分发结构 | 相对链接、17 项受管资产、14 个行为场景定义、无 PPT 二进制 | [docs.json](verification/docs.json) |

更新演练确认：研究状态、稿件、已填写 Idea Evaluation 和用户规则的文件哈希保持不变。本地非重叠 Skill 修改与上游合并，重叠冲突须显式解决；脏目录、预览提交变化、未知 Schema 和回滚时的新编辑均被保护。

合成演示实际计算 12 组人工配对数据，baseline mean 22.5、candidate mean 18.0、candidate-minus-baseline -4.5。来源、数据与人工核验／审核声明都明确为模拟，不用于真实投稿。

## GitHub CI 与模型边界

云端导入尝试 [35885436101](https://github.com/729149195/AI-Research-aiworkspace/actions/runs/35885436101) 失败，最终通过仓库内容接口直接提交源码。该次运行不计为测试通过。正式 CI 配置保留，云端状态必须以对应提交的 [Actions](https://github.com/729149195/AI-Research-aiworkspace/actions) 为准；本地通过和云端通过分别记录。

模型适配器测试使用 mock，14 个 Skill 行为场景仍标记 `not_run`。没有真实付费模型／完整宿主效果基准。原生同步支持带稳定章节标记的 Markdown；Word/LaTeX/Overleaf 无损往返、身份认证、多人实时数据库和无界自主研究未实现。

## 复测

从仓库根目录、已安装本包的专用虚拟环境执行：

```bash
python aiworkspace/scripts/run_tests.py
python aiworkspace/scripts/check_docs.py
python aiworkspace/scripts/smoke_root_update.py
rw demo ../a-new-synthetic-demo
```

研究选择、原文核验与最终独立审核由实际责任人完成。资产备份不能替代完整研究数据备份。
