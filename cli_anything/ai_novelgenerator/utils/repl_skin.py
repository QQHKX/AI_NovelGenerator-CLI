"""cli-anything REPL Skin — Unified terminal interface for all CLI harnesses.

Copy this file into your CLI package at:
    cli_anything/<software>/utils/repl_skin.py
"""

import os
import sys
from pathlib import Path

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_CYAN = "\033[38;5;80m"
_GRAY = "\033[38;5;245m"
_DARK_GRAY = "\033[38;5;240m"
_LIGHT_GRAY = "\033[38;5;250m"
_DEFAULT_ACCENT = "\033[38;5;75m"
_GREEN = "\033[38;5;78m"
_YELLOW = "\033[38;5;220m"
_RED = "\033[38;5;196m"
_BLUE = "\033[38;5;75m"
_MAGENTA = "\033[38;5;176m"
_H_LINE = "─"
_V_LINE = "│"
_TL = "╭"
_TR = "╮"
_BL = "╰"
_BR = "╯"
_ACCENT_COLORS = {
    "ai_novelgenerator": "\033[38;5;141m",
}
_SKILL_SOURCE_REPO = os.environ.get("CLI_ANYTHING_SKILL_REPO", "HKUDS/CLI-Anything")


def _strip_ansi(text: str) -> str:
    import re

    return re.sub(r"\033\[[^m]*m", "", text)


def _visible_len(text: str) -> int:
    return len(_strip_ansi(text))


def _display_home_path(path: str) -> str:
    expanded = Path(path).expanduser().resolve()
    home = Path.home().resolve()
    try:
        relative = expanded.relative_to(home)
        return f"~/{relative.as_posix()}"
    except ValueError:
        return str(expanded)


class ReplSkin:
    def __init__(self, software: str, version: str = "1.0.0", history_file: str | None = None, skill_path: str | None = None):
        self.software = software.lower().replace("-", "_")
        self.display_name = software.replace("_", " ").title()
        self.version = version
        self.skill_slug = self.software.replace("_", "-")
        self.skill_id = f"cli-anything-{self.skill_slug}"
        self.skill_install_cmd = f"npx skills add {_SKILL_SOURCE_REPO} --skill {self.skill_id} -g -y"
        global_skill_root = Path(os.environ.get("CLI_ANYTHING_GLOBAL_SKILLS_DIR", str(Path.home() / ".agents" / "skills"))).expanduser()
        self.global_skill_path = str(global_skill_root / self.skill_id / "SKILL.md")
        if skill_path is None:
            package_skill = Path(__file__).resolve().parent.parent / "skills" / "SKILL.md"
            repo_skill = None
            for parent in Path(__file__).resolve().parents:
                candidate = parent / "skills" / self.skill_id / "SKILL.md"
                if candidate.is_file():
                    repo_skill = candidate
                    break
            if repo_skill and repo_skill.is_file():
                skill_path = str(repo_skill)
            elif package_skill.is_file():
                skill_path = str(package_skill)
        self.skill_path = skill_path
        self.accent = _ACCENT_COLORS.get(self.software, _DEFAULT_ACCENT)
        if history_file is None:
            hist_dir = Path.home() / f".cli-anything-{self.software}"
            hist_dir.mkdir(parents=True, exist_ok=True)
            self.history_file = str(hist_dir / "history")
        else:
            self.history_file = history_file
        self._color = self._detect_color_support()

    def _detect_color_support(self) -> bool:
        if os.environ.get("NO_COLOR") or os.environ.get("CLI_ANYTHING_NO_COLOR"):
            return False
        return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

    def _c(self, code: str, text: str) -> str:
        if not self._color:
            return text
        return f"{code}{text}{_RESET}"

    def print_banner(self):
        inner = 72

        def _box_line(content: str) -> str:
            pad = inner - _visible_len(content)
            vl = self._c(_DARK_GRAY, _V_LINE)
            return f"{vl}{content}{' ' * max(0, pad)}{vl}"

        top = self._c(_DARK_GRAY, f"{_TL}{_H_LINE * inner}{_TR}")
        bot = self._c(_DARK_GRAY, f"{_BL}{_H_LINE * inner}{_BR}")
        title = f" {self._c(_CYAN + _BOLD, '◆')}  {self._c(_CYAN + _BOLD, 'cli-anything')} {self._c(_DARK_GRAY, '·')} {self._c(self.accent + _BOLD, self.display_name)}"
        ver = f" {self._c(_DARK_GRAY, f'   v{self.version}') }"
        install = f" {self._c(_MAGENTA, '◇')} {self._c(_DARK_GRAY, 'Install:')} {self._c(_LIGHT_GRAY, self.skill_install_cmd)}"
        global_skill = f" {self._c(_MAGENTA, '◇')} {self._c(_DARK_GRAY, 'Global skill:')} {self._c(_LIGHT_GRAY, _display_home_path(self.global_skill_path))}"
        print(top)
        print(_box_line(title))
        print(_box_line(ver))
        print(_box_line(install))
        print(_box_line(global_skill))
        print(_box_line(" "))
        print(_box_line(f" {self._c(_DARK_GRAY, 'Type help for commands, quit to exit')}"))
        print(bot)
        print()

    def prompt(self, project_name: str = "", modified: bool = False, context: str = "") -> str:
        parts = []
        parts.append(f"{self._c(_CYAN, '◆')} ")
        parts.append(self._c(self.accent + _BOLD, self.software))
        if project_name or context:
            ctx = context or project_name
            mod = "*" if modified else ""
            parts.append(f" {self._c(_DARK_GRAY, '[')}{self._c(_LIGHT_GRAY, f'{ctx}{mod}')}{self._c(_DARK_GRAY, ']')}")
        parts.append(self._c(_GRAY, " ❯ "))
        return "".join(parts)

    def prompt_tokens(self, project_name: str = "", modified: bool = False, context: str = ""):
        tokens = []
        tokens.append(("class:icon", "◆ "))
        tokens.append(("class:software", self.software))
        if project_name or context:
            ctx = context or project_name
            mod = "*" if modified else ""
            tokens.append(("class:bracket", " ["))
            tokens.append(("class:context", f"{ctx}{mod}"))
            tokens.append(("class:bracket", "]"))
        tokens.append(("class:arrow", " ❯ "))
        return tokens

    def get_prompt_style(self):
        try:
            from prompt_toolkit.styles import Style
        except ImportError:
            return None
        return Style.from_dict(
            {
                "icon": "#5fdfdf bold",
                "software": "#af87ff bold",
                "bracket": "#585858",
                "context": "#bcbcbc",
                "arrow": "#808080",
                "completion-menu.completion": "bg:#303030 #bcbcbc",
                "completion-menu.completion.current": "bg:#af87ff #000000",
                "completion-menu.meta.completion": "bg:#303030 #808080",
                "completion-menu.meta.completion.current": "bg:#af87ff #000000",
                "auto-suggest": "#585858",
                "bottom-toolbar": "bg:#1c1c1c #808080",
                "bottom-toolbar.text": "#808080",
            }
        )

    def success(self, message: str):
        print(f"  {self._c(_GREEN + _BOLD, '✓')} {self._c(_GREEN, message)}")

    def error(self, message: str):
        print(f"  {self._c(_RED + _BOLD, '✗')} {self._c(_RED, message)}", file=sys.stderr)

    def warning(self, message: str):
        print(f"  {self._c(_YELLOW + _BOLD, '⚠')} {self._c(_YELLOW, message)}")

    def info(self, message: str):
        print(f"  {self._c(_BLUE, '●')} {self._c(_LIGHT_GRAY, message)}")

    def status(self, label: str, value: str):
        print(f"{self._c(_GRAY, f'  {label}:')}{self._c(_LIGHT_GRAY, f' {value}')}")

    def table(self, headers: list[str], rows: list[list[str]], max_col_width: int = 40):
        if not headers:
            return
        widths = [min(len(h), max_col_width) for h in headers]
        for row in rows:
            for idx, cell in enumerate(row):
                widths[idx] = min(max(widths[idx], len(str(cell))), max_col_width)

        def pad(text: str, width: int):
            text = str(text)[:width]
            return text + " " * (width - len(text))

        header = "  " + f" {self._c(_DARK_GRAY, _V_LINE)} ".join(self._c(_CYAN + _BOLD, pad(h, widths[i])) for i, h in enumerate(headers))
        print(header)
        print(self._c(_DARK_GRAY, "  " + "───".join(_H_LINE * width for width in widths)))
        for row in rows:
            print("  " + f" {self._c(_DARK_GRAY, _V_LINE)} ".join(self._c(_LIGHT_GRAY, pad(cell, widths[i])) for i, cell in enumerate(row)))

    def help(self, commands: dict[str, str]):
        max_cmd = max(len(cmd) for cmd in commands) if commands else 0
        print()
        print(f"  {self._c(self.accent + _BOLD, 'Commands')}")
        print(f"  {self._c(_DARK_GRAY, _H_LINE * 8)}")
        for cmd, desc in commands.items():
            print(f"{self._c(self.accent, f'  {cmd:<{max_cmd}}')}{self._c(_GRAY, f'  {desc}')}")
        print()

    def print_goodbye(self):
        print(f"\n  {self._c(_CYAN, '▸')} {self._c(_GRAY, 'Goodbye!')}\n")

    def create_prompt_session(self):
        try:
            from prompt_toolkit import PromptSession
            from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
            from prompt_toolkit.history import FileHistory

            return PromptSession(
                history=FileHistory(self.history_file),
                auto_suggest=AutoSuggestFromHistory(),
                style=self.get_prompt_style(),
                enable_history_search=True,
            )
        except ImportError:
            return None

    def get_input(self, pt_session, project_name: str = "", modified: bool = False, context: str = "") -> str:
        if pt_session is not None:
            from prompt_toolkit.formatted_text import FormattedText

            return pt_session.prompt(FormattedText(self.prompt_tokens(project_name, modified, context))).strip()
        return input(self.prompt(project_name, modified, context)).strip()
