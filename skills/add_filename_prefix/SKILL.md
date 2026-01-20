# Skill: add_filename_prefix

## Description
为目录下的文件统一添加前缀

## When to Use
- 批量重命名文件
- 给文件添加版本号或日期前缀
- 统一文件命名规范

## When NOT to Use
- 目录下没有文件
- 不需要修改文件名

## Inputs
- prefix: 要添加的前缀字符串
- target_dir: 目标目录路径

## Outputs
- renamed_count: 被重命名的文件数量

## Execution
- type: python
- entry: scripts/add_prefix.py

## Safety
- side_effects: filesystem
- requires_confirmation: true
