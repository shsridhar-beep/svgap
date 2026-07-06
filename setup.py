"""Build hook that places frozen research assets inside installed wheels."""

from pathlib import Path
import shutil

from setuptools import setup
from setuptools.command.build_py import build_py


ROOT = Path(__file__).parent


class BuildPyWithResearchAssets(build_py):
    def run(self) -> None:
        super().run()
        targets = (
            (
                ROOT / "taskpacks/reset-replication-v0.2",
                Path(self.build_lib) / "svgap/resources/taskpacks/reset-replication-v0.2",
            ),
            (
                ROOT / "challenges/v0.1",
                Path(self.build_lib) / "svgap/resources/challenges/v0.1",
            ),
        )
        for source, destination in targets:
            shutil.copytree(source, destination, dirs_exist_ok=True)


setup(cmdclass={"build_py": BuildPyWithResearchAssets})
