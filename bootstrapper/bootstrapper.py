import glob
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from argparse import ArgumentParser
from pathlib import Path
from subprocess import PIPE


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
        os.makedirs(self.translation_repo, exist_ok=True)
        os.makedirs(self.cpython_repo, exist_ok=True)

    def setup_cpython_repo(self) -> None:
        if not os.path.exists(f"{self.cpython_repo}/.git") and not os.path.isdir(
            f"{self.cpython_repo}/.git"
        ):
            subprocess.run(
                [
                    "git",
                    "clone",
                    "https://github.com/python/cpython.git",
                    self.cpython_repo,
                ]
            )
        subprocess.run(["git", "-C", self.cpython_repo, "checkout", self.branch])
        subprocess.run(["git", "-C", self.cpython_repo, "pull", "--ff-only"])
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
        )

    def setup_translation_repo(self) -> None:
        subprocess.run(["git", "init"], cwd=self.translation_repo)
        subprocess.run(["git", "branch", "-m", self.branch], cwd=self.translation_repo)

        files = glob.glob(f"{self.cpython_repo}/pot/**/*.pot") + glob.glob(
            f"{self.cpython_repo}/pot/*.pot"
        )

        files = [path.replace("\\", "/") for path in files]

        for file in files:
            dest_path = (
                f"{self.translation_repo}/{'/'.join(file.split('/')[4:])}".replace(
                    ".pot", ".po"
                )
            )

            if len(file.split("/")) > 5:
                os.makedirs("/".join(dest_path.split("/")[:2]), exist_ok=True)

            shutil.copyfile(file, dest_path)
            files[files.index(file)] = dest_path

        for file in files:
            with open(file, "r", encoding="utf-8") as f:
                contents = f.read()
                contents = re.sub("^#: .*Doc/", "#: ", contents, flags=re.M)
            with open(file, "w", encoding="utf-8") as f:
                f.write(contents)

    def create_readme(self) -> None:
        try:
            readme = self._request(self.readme_url)
        except (urllib.error.HTTPError, urllib.error.URLError):
            readme = Path(f"{os.path.dirname(__file__)}/data/README.md").read_text(
                encoding="utf-8"
            )

        readme = readme.replace("{{translation.language}}", self.language)

        with open(f"{self.translation_repo}/README.md", "w", encoding="utf-8") as f:
            f.write(readme)

    def create_gitignore(self) -> None:
        try:
            gitignore = self._request(self.gitignore_url)
        except (urllib.error.HTTPError, urllib.error.URLError):
            gitignore = Path(f"{os.path.dirname(__file__)}/data/.gitignore").read_text(
                encoding="utf-8"
            )

        with open(f"{self.translation_repo}/.gitignore", "w", encoding="utf-8") as f:
            f.write(gitignore)

    def create_makefile(self) -> None:
        try:
            makefile = self._request(self.makefile_url)
        except (urllib.error.HTTPError, urllib.error.URLError):
            makefile = Path(f"{os.path.dirname(__file__)}/data/Makefile").read_text(
                encoding="utf-8"
            )

        head = (
            subprocess.run(
                ["git", "-C", self.cpython_repo, "rev-parse", "HEAD"], stdout=PIPE
            )
            .stdout.strip()
            .decode()
        )

        makefile = makefile.replace("{{translation.language}}", self.language)
        makefile = makefile.replace("{{translation.branch}}", self.branch)
        makefile = makefile.replace("{{translation.head}}", head)

        with open(f"{self.translation_repo}/Makefile", "w", encoding="utf-8") as f:
            f.write(makefile)

    def run(self) -> None:
        self.create_dirs()
        self.setup_cpython_repo()
        self.setup_translation_repo()
        self.create_readme()
        self.create_gitignore()
        self.create_makefile()


def main() -> None:
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
    Bootstrapper(args.language.lower(), args.branch).run()


if __name__ == "__main__":
    main()
