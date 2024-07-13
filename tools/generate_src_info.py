#!/usr/bin/env python3

___doc__ = """
This script creates several RPM include files for the swift-lang
RPM package. Swift is a large project with multiple repositories,
so it's important to keep the dependencies in sync.
The script clones the Swift repository to a temporary directory,
reads the config file to get the repositories and branches to update,
fetches the commit hashes for the specified branches, and generates
the several include files. The RPM spec file uses these files
to download the sources and generate the RPM package.
"""

import argparse
import collections
import datetime
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile

from pathlib import Path
from dataclasses import dataclass

# third_party
import requests

ROOT_DIR = Path(os.path.dirname(os.path.realpath(__file__))).parent.resolve()

REPOSITORY_URL = "https://github.com/swiftlang/swift"
CONFIG_FILE = "utils/update_checkout/update-checkout-config.json"

# Structure of the CONFIG_FILE:
"""
{
  "repos": {
    "swift": {
      "remote": { "id": "swiftlang/swift" } },
  },
  "branch-schemes": {
    "release/6.0": {
      "repos": {
        "llvm-project": "swift/release/6.0",
        "swift": "swift/release/6.0",
        ...

      },
    },
  },
}
"""


class PushPopDir:
  """
  Context manager to change the current working directory.
  It is similar to pushd/popd in bash.
  """

  def __init__(self, new_dir):
    self.new_dir = new_dir
    self.old_dir = None

  def __enter__(self):
    self.old_dir = os.getcwd()
    os.chdir(self.new_dir)

  def __exit__(self, exc_type, exc_value, traceback):
    os.chdir(self.old_dir)


@dataclass
class Repo:
  name: str
  remote: str
  commit: str


SCHEME_VERSION_MAP = {
    "release/6.0": "6.0",
    # Provisional
    "main": "6.1",
}


def fetch_github_repo_commit(username, repo, branch, token=None):
  if token:
    return fetch_github_repo_commit_with_token(username, repo, branch, token)
  return fetch_github_repo_commit_with_clone(username, repo, branch)


def fetch_github_repo_commit_with_token(username, repo, branch, token):
  url = f"https://api.github.com/repos/{username}/{repo}/commits/{branch}"
  headers = {}
  if token:
    headers["Authorization"] = f"token {token}"
  response = requests.get(url, headers=headers)
  response.raise_for_status()
  return response.json()["sha"]


def fetch_github_repo_commit_with_clone(username, repo, branch):
  with tempfile.TemporaryDirectory() as tmp_dir:
    cmd = [
        "git", "clone", "-b", branch,
        f"https://github.com/{username}/{repo}.git", tmp_dir
    ]
    print(f"Running {shlex.join(cmd)}")
    subprocess.run(cmd, check=True)
    with PushPopDir(tmp_dir):
      cmd = ["git", "rev-parse", "HEAD"]
      print(f"Running {shlex.join(cmd)}")
      result = subprocess.check_output(cmd, text=True).strip()
      # Check if the result is a valid commit hash
      if len(result) != 40 or not all(c in "0123456789abcdef" for c in result):
        raise ValueError(f"Invalid commit hash: {result}")
      return result


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("--src-dir", help="source directory")
  parser.add_argument("--scheme", required=True, help="scheme to generate")
  parser.add_argument(
      "--no-write", action="store_true", help="do not write to file")
  parser.add_argument("--github-token", help="GitHub token")

  args = parser.parse_args()

  src_dir = args.src_dir
  scheme = args.scheme
  token = args.github_token
  write_to_file = not args.no_write
  if not token:
    token = os.getenv("GITHUB_TOKEN")

  if not scheme:
    print("No scheme specified.")
    return 1

  scheme_to_version = SCHEME_VERSION_MAP.get(scheme)
  if not scheme_to_version:
    print(f"Scheme {scheme} not found in the version map.")
    return 1

  use_temp_dir = False
  if not src_dir:
    print("No source directory specified. Use temporary directory to"
          " clone the repository.")
    src_dir = Path(tempfile.mkdtemp())
    use_temp_dir = True
  else:
    src_dir = Path(src_dir)
    if not src_dir.exists():
      print(f"Source directory {src_dir} does not exist.")
      return 1

  try:
    if use_temp_dir:
      cmd = ["git", "clone", "-b", scheme, REPOSITORY_URL, str(src_dir)]
      print(f"Running {shlex.join(cmd)}")
      subprocess.run(cmd, check=True)
    else:
      cmd = ["git", "-C", str(src_dir), "fetch", "origin"]
      print(f"Running {shlex.join(cmd)}")
      subprocess.run(cmd, check=True)

      cmd = ["git", "-C", str(src_dir), "checkout", scheme]
      print(f"Running {shlex.join(cmd)}")
      subprocess.run(cmd, check=True)

      cmd = ["git", "-C", str(src_dir), "reset", "--hard", f"origin/{scheme}"]
      print(f"Running {shlex.join(cmd)}")
      subprocess.run(cmd, check=True)

    config_file = src_dir / CONFIG_FILE
    if not config_file.exists():
      print(f"Config file {config_file} does not exist.")
      return 1

    with open(config_file, "r") as f:
      config = json.load(f, object_pairs_hook=collections.OrderedDict)

    if "repos" not in config:
      print("No repositories found in the config file.")
      return 1

    repos = config["repos"]

    if "branch-schemes" not in config:
      print("No branch-schemes found in the config file.")
      return 1

    schemes = config["branch-schemes"]
    if scheme not in schemes:
      print(f"Scheme {scheme} not found in the config file.")
      return 1

    scheme_repos = schemes[scheme]["repos"]
    # TODO(bc-lee): Use system's cmake and ninja to speed up the build
    # remove cmake and ninja
    # if "cmake" in scheme_repos:
    #   scheme_repos.pop("cmake")
    # if "ninja" in scheme_repos:
    #   scheme_repos.pop("ninja")

    repo_map = dict()
    for repo, branch in scheme_repos.items():
      if repo not in repos:
        print(f"Repository {repo} not found in the config file.")
        return 1

      remote = repos[repo]["remote"]["id"]
      git_username, git_repo = remote.split("/", maxsplit=1)
      commit = fetch_github_repo_commit(git_username, git_repo, branch, token)
      repo_map[repo] = Repo(repo, remote, commit)

    if not write_to_file:
      print(json.dumps([repo.__dict__ for repo in repo_map.values()], indent=2))
      return 0

    swift_commit = repo_map["swift"].commit
    # Sort the repositories by name, to ensure consistent output
    result = []
    for repo_name in sorted(repo_map.keys()):
      result.append(repo_map[repo_name])

    utcnow = datetime.datetime.now(datetime.UTC)
    date = utcnow.strftime("%Y%m%d")

    # Version format: <version>~pre^<date>git<commit>
    version = f"{scheme_to_version}~pre^{date}git{swift_commit[:7]}"

    versio_inc = f"""%global swift_version {version}
%global package_version {scheme_to_version}

"""
    for item in result:
      versio_inc += f"%global {item.name.replace('-', '_')}_commit {item.commit}\n"

    with open(ROOT_DIR / "version.inc", "w") as f:
      f.write(versio_inc)

    source_inc = ""
    for index, item in enumerate(result):
      # Source index starts from 3 since first 3 sources are already defined
      # for .inc files
      source_inc += f"Source{index+3}: https://github.com/{item.remote}/archive/"
      source_inc += "%{" + item.name.replace('-', '_') + "_commit}.tar.gz#/"
      source_inc += item.name + "-%{" + item.name.replace(
          '-', '_') + "_commit}.tar.gz\n"

    with open(ROOT_DIR / "source.inc", "w") as f:
      f.write(source_inc)

    rename_inc = ""
    for item in result:
      git_repo = item.remote.split("/", maxsplit=1)[1]
      rename_inc += "mv " + git_repo + "-%{" + item.name.replace(
          '-', '_') + "_commit} "
      rename_inc += item.name + "\n"

    with open(ROOT_DIR / "rename.inc", "w") as f:
      f.write(rename_inc)

    print("All files generated successfully.")

  finally:
    if use_temp_dir:
      shutil.rmtree(src_dir, ignore_errors=True)


if __name__ == "__main__":
  sys.exit(main())
