# Skill: dir_filetype_stats

## Description
统计目录下不同文件类型的数量

## When to Use
- 查看目录中有哪些类型的文件
- 统计各种文件扩展名的数量
- 快速了解文件分布情况

## When NOT to Use
- 不支持递归统计子目录（当前版本）
- 不需要文件内容分析

## Inputs
- dir: 要统计的目录路径

## Outputs
- filetype_counts: 各文件类型及其数量

## Execution
- type: shell
- entry: scripts/count_filetypes.sh

## Safety
- side_effects: none
- requires_confirmation: false
