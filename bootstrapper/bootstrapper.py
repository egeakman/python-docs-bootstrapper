import glob
import logging
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from argparse import ArgumentParser
from pathlib import Path
from subprocess import PIPE


class _NoNewLine(logging.StreamHandler):
    def emit(self, record):
        msg = self.format(record)
        stream = self.stream
        terminator = "\n" if msg.endswith("\n") else ""
        stream.write(msg + terminator)
        self.flush()


logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = _NoNewLine()
handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(handler)


class Bootstrapper:
    def __init__(self, language: str, branch: str = "3.12") -> None:
        self.language = language
        self.branch = branch
        self.translation_repo = f"python-docs-{self.language}"
        self.cpython_repo = f"{self.translation_repo}/venv/cpython"
        self.readme_url = "https://raw.githubusercontent.com/egeakman/python-docs-bootstrapper/master/bootstrapper/data/README.md"
        self.gitignore_url = "https://raw.githubusercontent.com/egeakman/python-docs-bootstrapper/master/bootstrapper/data/.gitignore"
        self.makefile_url = "https://raw.githubusercontent.com/egeakman/python-docs-bootstrapper/master/bootstrapper/data/Makefile"

    def _request(self, url: str) -> str:
        with urllib.request.urlopen(url) as response:
            return response.read().decode()

    def create_dirs(self) -> None:
        logger.info("Creating directories...")
        os.makedirs(self.translation_repo, exist_ok=True)
        os.makedirs(self.cpython_repo, exist_ok=True)
        logger.info("✅\n")

    def setup_cpython_repo(self) -> None:
        if not os.path.exists(f"{self.cpython_repo}/.git") and not os.path.isdir(
            f"{self.cpython_repo}/.git"
        ):
            logger.info("Cloning CPython repo...")
            subprocess.run(
                [
                    "git",
                    "clone",
                    "https://github.com/python/cpython.git",
                    self.cpython_repo,
                    f"--branch={self.branch}",
                    "-q",
                ],
                check=True,
            )
            logger.info("✅\n")

        logger.info("Updating CPython repo...")
        subprocess.run(
            ["git", "-C", self.cpython_repo, "pull", "--ff-only", "-q"], check=True
        )
        logger.info("✅\n")

        logger.info("Building gettext files...")
        subprocess.run(
            [
                "sphinx-build",
                "-jauto",
                "-QDgettext_compact=0",
                "-bgettext",
                "Doc",
                "pot",
            ],
            cwd=self.cpython_repo,
            check=True,
        )
        logger.info("✅\n")

    def setup_translation_repo(self) -> None:
        logger.info("Initializing translation repo...")
        subprocess.run(["git", "init", "-q"], cwd=self.translation_repo, check=True)
        subprocess.run(
            ["git", "branch", "-m", self.branch], cwd=self.translation_repo, check=True
        )
        logger.info("✅\n")

        logger.info("Copying gettext files...")
        files = glob.glob(f"{self.cpython_repo}/pot/**/*.pot", recursive=True)
        files = [path.replace("\\", "/") for path in files]

        for file in files:
            dest_path = (
                f"{self.translation_repo}/{'/'.join(file.split('/')[4:])}".replace(
                    ".pot", ".po"
                )
            )
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copyfile(file, dest_path)
            files[files.index(file)] = dest_path
        logger.info("✅\n")

        logger.info("Cleaning up gettext files...")
        for file in files:
            with open(file, "r", encoding="utf-8") as f:
                contents = f.read()
                contents = re.sub("^#: .*Doc/", "#: ", contents, flags=re.M)
            with open(file, "w", encoding="utf-8") as f:
                f.write(contents)
        logger.info("✅\n")

    def create_readme(self) -> None:
        logger.info("Creating README.md...")
        try:
            readme = self._request(self.readme_url)
        except (urllib.error.HTTPError, urllib.error.URLError):
            logger.warning(
                "\n ⚠️ Failed to fetch README.md from GitHub, using local copy..."
            )
            readme = Path(f"{os.path.dirname(__file__)}/data/README.md").read_text(
                encoding="utf-8"
            )

        readme = readme.replace("{{translation.language}}", self.language)

        with open(f"{self.translation_repo}/README.md", "w", encoding="utf-8") as f:
            f.write(readme)
        logger.info("✅\n")

    def create_gitignore(self) -> None:
        logger.info("Creating .gitignore...")
        try:
            gitignore = self._request(self.gitignore_url)
        except (urllib.error.HTTPError, urllib.error.URLError):
            logger.warning(
                "\n ⚠️ Failed to fetch .gitignore from GitHub, using local copy..."
            )
            gitignore = Path(f"{os.path.dirname(__file__)}/data/.gitignore").read_text(
                encoding="utf-8"
            )

        with open(f"{self.translation_repo}/.gitignore", "w", encoding="utf-8") as f:
            f.write(gitignore)
        logger.info("✅\n")

    def create_makefile(self) -> None:
        logging.info("Creating Makefile...")
        try:
            makefile = self._request(self.makefile_url)
        except (urllib.error.HTTPError, urllib.error.URLError):
            logger.warning(
                "\n ⚠️ Failed to fetch Makefile from GitHub, using local copy..."
            )
            makefile = Path(f"{os.path.dirname(__file__)}/data/Makefile").read_text(
                encoding="utf-8"
            )

        head = (
            subprocess.run(
                ["git", "-C", self.cpython_repo, "rev-parse", "HEAD"],
                stdout=PIPE,
                check=True,
            )
            .stdout.strip()
            .decode()
        )

        makefile = makefile.replace("{{translation.language}}", self.language)
        makefile = makefile.replace("{{translation.branch}}", self.branch)
        makefile = makefile.replace("{{translation.head}}", head)

        with open(f"{self.translation_repo}/Makefile", "w", encoding="utf-8") as f:
            f.write(makefile)
        logger.info("✅\n")

    def run(self) -> None:
        try:
            self.create_dirs()
            self.setup_cpython_repo()
            self.setup_translation_repo()
            self.create_readme()
            self.create_gitignore()
            self.create_makefile()
            logger.info(f"🎉 Done bootstrapping the {self.language} translation ✅\n")
        except Exception as e:
            logger.critical(
                f"❌ Bootstrapping of the {self.language} translation failed: {e}\n"
            )
            sys.exit(1)


def main() -> None:
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    parser = ArgumentParser()
    parser.add_argument(
        "language",
        type=str,
        help="IETF language tag (e.g. tr, pt-br)",
    )
    parser.add_argument(
        "-b", "--branch", type=str, default="3.12", help="CPython branch (e.g. 3.12)"
    )
    args = parser.parse_args()
    Bootstrapper(args.language.lower().replace("_", "-"), args.branch).run()


if __name__ == "__main__":
    main()
