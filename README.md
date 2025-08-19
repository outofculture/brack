# brack

A command-line tool that applies black formatting to Python files while maintaining clean feature branch diffs. Creates separate PRs for formatting changes, allowing reviewers to see pure formatting changes in isolation while keeping your feature branch clean and formatted.

## Overview

`brack` intelligently handles Python file formatting by:

- **Isolating formatting changes**: Creates separate branches and PRs for black formatting
- **Maintaining clean diffs**: Your feature branch stays focused on logic changes
- **Fast local operations**: Completes in under 1 second for immediate IDE integration
- **Background GitHub operations**: Push and PR creation happen asynchronously
- **Smart file categorization**: Handles existing files differently from new files

## Installation

1. Clone this repository
2. Make the script executable:
   ```bash
   chmod +x brack
   ```
3. Add to your PATH or create a symlink:
   ```bash
   ln -s /path/to/brack/brack /usr/local/bin/brack
   ```

## Dependencies

- `git` - Git version control
- `black` - Python code formatter (`pip install black`)
- `gh` - GitHub CLI (for PR creation)

## Usage

```bash
# Format specific files
brack file1.py file2.py

# Format with quiet output (for IDE integration)
brack --quiet file1.py file2.py

# Show help
brack --help
```

## How It Works

### File Categorization

`brack` categorizes files into two types:

- **Existing files**: Files that existed at your branch's merge-base with main
  - Formatted in a separate `{branch}-auto-black-formatting` branch
  - Creates/updates a separate PR for formatting changes
  
- **New files**: Files created in your current branch
  - Formatted directly in your current branch
  - No separate PR needed

### Workflow

1. **Local Operations** (< 1 second):
   - Stashes any uncommitted changes
   - Creates formatting branch from merge-base commit
   - Applies black formatting to existing files
   - Merges formatting changes back to your branch
   - Formats new files directly in your branch
   - Restores your stashed changes

2. **Background Operations** (asynchronous):
   - Pushes formatting branch to GitHub
   - Creates or updates PR for formatting changes

## IDE Integration

### VS Code

Add to your `settings.json`:

```json
{
  "python.formatting.provider": "none",
  "python.defaultInterpreterPath": "/home/martin/.miniforge3/envs/acq4-torch/bin/python",
  "[python]": {
    "editor.formatOnSave": false,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

Create a task in `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Format with brack",
      "type": "shell",
      "command": "brack",
      "args": ["--quiet", "${file}"],
      "group": "build",
      "presentation": {
        "echo": false,
        "reveal": "silent",
        "focus": false,
        "panel": "shared"
      },
      "problemMatcher": []
    }
  ]
}
```

Add a keybinding in `keybindings.json`:

```json
[
  {
    "key": "ctrl+shift+b",
    "command": "workbench.action.tasks.runTask",
    "args": "Format with brack"
  }
]
```

### Vim/Neovim

Add to your `.vimrc` or `init.vim`:

```vim
" Format current file with brack
nnoremap <leader>b :!brack --quiet %<CR>

" Format selection (write to temp file first)
vnoremap <leader>b :w !brack --quiet /dev/stdin<CR>
```

For Neovim with Lua configuration:

```lua
vim.keymap.set('n', '<leader>b', ':!brack --quiet %<CR>', { desc = 'Format with brack' })
```

### PyCharm/IntelliJ

1. Go to `File > Settings > Tools > External Tools`
2. Click `+` to add a new tool
3. Configure:
   - **Name**: `brack`
   - **Program**: `/path/to/brack/brack`
   - **Arguments**: `--quiet $FilePath$`
   - **Working directory**: `$ProjectFileDir$`

4. Assign a keyboard shortcut:
   - Go to `File > Settings > Keymap`
   - Find `External Tools > brack`
   - Right-click and assign shortcut

### Emacs

Add to your `.emacs` or `init.el`:

```elisp
(defun brack-format-buffer ()
  "Format current buffer with brack."
  (interactive)
  (when (eq major-mode 'python-mode)
    (shell-command (format "brack --quiet %s" (buffer-file-name)))))

(global-set-key (kbd "C-c b") 'brack-format-buffer)
```

## Error Handling

If `brack` encounters an error, it creates an `AUTO-BLACK-FORMATTING-ERROR` file in your repository root with details about what went wrong. Review the error and delete this file to continue using the tool.

Common error scenarios:
- Merge conflicts during formatting merge
- Black syntax errors in Python files  
- GitHub authentication issues
- Network failures during push/PR operations

## Performance

- **Local operations**: Complete in under 1 second
- **Background operations**: Push and PR creation happen asynchronously
- **Safe operations**: All git operations are reversible with proper cleanup

## Branch Management

- **Formatting branches**: Named `{your-branch}-auto-black-formatting`
- **Reuse existing branches**: Updates existing formatting branches rather than creating duplicates
- **Automatic cleanup**: Formatting branches are cleaned up after successful merge
- **Force-with-lease**: Safe force pushes prevent overwriting others' work

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly with various scenarios
5. Submit a pull request

## License

[Add your license here]