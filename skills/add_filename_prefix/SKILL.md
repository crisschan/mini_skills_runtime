apiVersion: skills.claude.compat/v1
kind: Skill
metadata:
  name: add_filename_prefix
  version: 1.0.0
  description: Add a prefix to all files in a directory
  author: local
  tags:
    - filesystem
    - batch-rename
routing:
  triggers:
    - batch rename files
    - add file prefix
    - standardize file naming
    - 批量重命名文件
    - 添加文件前缀
    - 统一文件命名规范
  embedding_hint: Batch add prefix strings to files, supporting version numbers and date prefixes
io:
  inputs:
    - name: prefix
      type: string
      required: true
    - name: target_dir
      type: string
      required: true
  outputs:
    - name: renamed_count
      type: integer
prompt:
  system: |
    You are a file management assistant that helps users batch rename files.
    You must strictly follow these steps:
  steps:
    - Receive prefix and target directory parameters
    - Iterate through all files in the directory
    - Add the specified prefix to each file (skip files that already have the prefix)
    - Return the number of renamed files
  constraints:
    - Do not modify files that already conform to naming standards
    - Ensure file operation safety
    - Provide accurate rename counts
tools:
  - name: filesystem
    description: Read and write file system
    allowed_commands:
      - os.listdir
      - os.rename
      - os.path.isfile
      - os.path.join
execution:
  mode: python
  allow_tool_chain: false
  max_steps: 10
  timeout_ms: 30000
