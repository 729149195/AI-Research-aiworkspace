# 独立仓库与接续已有论文

正式仓库为 **729149195/AI-Research-aiworkspace**。代码、安装说明与增量更新均使用此仓库；它有独立的 Git 历史，不依赖原有其他应用。

## 新用户

直接按根目录 [README](../../README.md) 克隆并安装。无需创建第二个仓库，也无需运行 create_github_repo.py。

## 已经使用旧框架的论文如何接续

**论文目录、已填写的内容和 `.rw/framework.json` 保持原样。** 先停止正在编辑论文的 AI／编辑器并备份整个论文项目。将新仓库克隆到新目录，建立新的虚拟环境：

```bash
git clone https://github.com/729149195/AI-Research-aiworkspace.git
cd AI-Research-aiworkspace
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install --no-deps --no-build-isolation -e ./aiworkspace

# 将 /absolute/path/to/my-paper 替换为原有论文的真实目录。
rw --project /absolute/path/to/my-paper upgrade check
rw --project /absolute/path/to/my-paper upgrade apply --actor "作者姓名" --approve
rw --project /absolute/path/to/my-paper sync status
rw --project /absolute/path/to/my-paper review
```

Windows 用 `.venv\Scripts\python.exe -m research_workspace` 替代 `rw`，不必修改系统脚本执行策略。

新仓库拥有独立提交历史。保留旧 clone 供追溯，直接使用新的 clone；不要把无关历史强行合并，也不要用空模板整目录覆盖论文。新引擎根据论文原有的基线做受管资产三方更新，稿件、数据、代码、证据和研究状态不会作为模板覆盖目标。

迁移后的日常更新在**新框架仓库根目录**执行：

```bash
python update_aiworkspace.py --project /absolute/path/to/my-paper --check
python update_aiworkspace.py --project /absolute/path/to/my-paper --apply --actor "作者姓名"
```

检查和应用之间可用 `--expected-commit` 锁定预览 SHA。出现本地 Skill 冲突时按 [增量更新说明](UPDATING.md) 显式解决。无需重新初始化论文。

## 保留的创建脚本

`aiworkspace/scripts/create_github_repo.py` 是先前源码分发时的维护工具，默认只做离线预览。其固定目标已更新到本仓库，目标已经存在时会拒绝创建；正常安装和更新均不使用它。该工具的测试采用 mock，不产生真实远程写入。
