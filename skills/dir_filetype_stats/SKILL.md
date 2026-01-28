apiVersion: skills.claude.compat/v1
kind: Skill
metadata:
  name: dir_filetype_stats
  version: 1.0.0
  description: Count the number of different file types in a directory
  author: local
  tags:
    - filesystem
    - statistics
    - analysis
routing:
  triggers:
    - count file types
    - view directory file distribution
    - file extension statistics
    - 统计文件类型
    - 查看目录文件分布
    - 文件扩展名统计
  embedding_hint: Analyze file type distribution and count statistics in a directory
io:
  inputs:
    - name: dir
      type: string
      required: true
  outputs:
    - name: filetype_counts
      type: object
prompt:
  system: |
    You are a file analysis assistant that helps users understand file type distribution in directories.
    You must strictly follow these steps:
  steps:
    - Receive target directory parameter
    - Scan all files in the directory
    - Extract file extensions and count quantities
    - Sort results in descending order by count
  constraints:
    - Only count files, not directories
    - Provide accurate file type statistics
    - Sort results in descending order by quantity
tools:
  - name: shell
    description: Execute shell commands
    allowed_commands:
      - find
      - sed
      - sort
      - uniq
      - wc
execution:
  mode: shell
  allow_tool_chain: false
  max_steps: 5
  timeout_ms: 15000
