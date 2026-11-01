"""Build, package and publish a release to GitHub in one go.

usage: release.py [--date YYMMDD] [--rev N] [--no-upload] [--dry-run]
  --date        override the date part of the release name (default: today)
  --rev N       another build on the same day and Steam build: name it ...-rN
  --no-upload   do everything locally (files, RELEASES.md, commit, tag) but don't push or touch GitHub
  --dry-run     only print what would happen

Steps: release/<name>/{game files, 설치방법.txt, zip} -> RELEASES.md entry -> commit + tag -> push -> GitHub release.
GitHub credentials come from Git Credential Manager (`git credential fill`); nothing is stored.
"""
import base64
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile

from common import GAME_ROOT, ROOT, TRANSLATIONS, WORK

APP_ID = "1737870"
PATCHED_FILES = ["Reka_Data/resources.assets"]
DRY = "--dry-run" in sys.argv
NO_UPLOAD = "--no-upload" in sys.argv
REPO = "game-patch-ko/reka-ko"
API = f"https://api.github.com/repos/{REPO}"
UPLOADS = f"https://uploads.github.com/repos/{REPO}"


def arg(name):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None


def run(*cmd, capture=False, input=None):
    if DRY and not capture:
        print("[dry-run]", " ".join(cmd))
        return ""
    r = subprocess.run(cmd, cwd=ROOT, check=True, text=True, input=input,
                       capture_output=capture, env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
    return r.stdout if capture else ""


def steam_build_id():
    with open(os.path.join(GAME_ROOT, "..", "..", f"appmanifest_{APP_ID}.acf"), encoding="utf-8") as f:
        return re.search(r'"buildid"\s+"(\d+)"', f.read()).group(1)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


INSTALL_NOTE = """REKA 한국어 패치 - {date} / Steam build {build} / 게임 버전 {version}

[설치]
1. 게임을 종료합니다.
2. 이 압축 파일 안의 Reka_Data 폴더를 게임 설치 폴더에 그대로 덮어씁니다.
   기본 위치 예: C:\\Program Files (x86)\\Steam\\steamapps\\common\\Reka\\
   Steam 라이브러리에서 게임 우클릭 → 관리 → 로컬 파일 보기로 찾을 수 있습니다.
3. 게임을 실행합니다. Steam 언어가 한국어이면 자동으로 한국어가 선택됩니다.
   아니면 설정 → LANGUAGE → Language에서 "한국어"를 고르세요.

[특징]
- 다른 언어는 그대로 남아 있으며, 언어 메뉴에 한국어가 추가됩니다.
- 키보드 키 이름(Space, Left Shift 등)은 입력 라이브러리의 고정 문자열이라 영어로 나옵니다.

[제거]
Steam 라이브러리 → 게임 우클릭 → 속성 → 설치된 파일 → "게임 파일 무결성 검사"

[주의]
- 이 패치는 위 Steam 빌드용입니다. 게임이 업데이트되면 파일이 덮어써져 영어로 돌아가거나, 맞지 않는
  패치를 덮으면 게임이 실행되지 않을 수 있습니다. 이때는 무결성 검사 후 새 패치를 기다려 주세요.

[권리와 안내]
- 이 패치는 REKA를 좋아하는 한국 팬들을 위해 순수한 팬의 입장에서 만들었습니다.
  상업적 목적이 없으며 무료로 제공합니다.
- 원작의 모든 권리는 Emberstorm Entertainment에 있습니다. 이 패치는 비공식이며 제작사의 승인을 받지 않았습니다.
  제작자는 이 패치에 대해 어떠한 배타적 권리도 주장하지 않습니다.
- 원 게임 제작사가 요구할 경우 패치 제공을 중단할 수 있습니다.
- 제작자는 직장을 다니는 평범한 직장인입니다. 게임 업데이트 등으로 패치가 작동하지 않을 때
  대응이 늦을 수 있으니 양해 부탁드립니다.
- 포함된 한글 폰트는 Noto Sans CJK KR을 기반으로 하며 SIL Open Font License 1.1이 적용됩니다(전문: OFL.txt).
"""


def game_version():
    return "1.0.25"


def package(name, date_iso, build):
    rel = os.path.join(ROOT, "release", name)
    if DRY:
        print(f"[dry-run] build into {rel}")
        return None, {}
    subprocess.run([sys.executable, "-X", "utf8", os.path.join(ROOT, "tools", "patch.py")], check=True)
    if os.path.exists(rel):
        shutil.rmtree(rel)
    os.makedirs(rel)
    note = os.path.join(rel, "설치방법.txt")
    with open(note, "w", encoding="utf-8-sig", newline="\r\n") as f:
        f.write(INSTALL_NOTE.format(date=date_iso, build=build, version=game_version()))
    zpath = os.path.join(rel, f"{name}.zip")
    hashes = {}
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for relpath in PATCHED_FILES:
            src = os.path.join(WORK, "out", relpath)
            z.write(src, relpath)
            hashes[relpath] = sha256(src)
        z.write(note, "설치방법.txt")
        z.write(os.path.join(ROOT, "licenses", "OFL.txt"), "OFL.txt")
    return zpath, hashes


def releases_entry(name, date_iso, build, zpath, hashes, count):
    rows = "\n".join(f"| `{p}` | `{h}` |" for p, h in hashes.items())
    size = os.path.getsize(zpath) / (1 << 20)
    return (f"\n## {name}\n- 날짜: {date_iso}\n"
            f"- 게임: REKA (Steam app {APP_ID}), Steam build `{build}`, 게임 버전 `{game_version()}`\n"
            f"- 태그: `{name}`\n- 첨부: `{os.path.basename(zpath)}` ({size:.1f} MB)\n  - SHA256 `{sha256(zpath)}`\n"
            f"- 내용: 잠긴 Korean 언어 슬롯 활성화, 번역 {count:,}개 항목, 한글 동적 폰트(Noto Sans KR)\n\n"
            f"| 파일 (게임 폴더 기준) | SHA256 |\n|---|---|\n{rows}\n")


def github_auth():
    out = run("git", "credential", "fill", capture=True, input="protocol=https\nhost=github.com\n\n")
    cred = dict(line.split("=", 1) for line in out.splitlines() if "=" in line)
    return f"Bearer {cred['password']}"


def api(auth, method, path, body=None):
    req = urllib.request.Request(API + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Authorization", auth)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read() or b"null")


def upload(auth, release_id, zpath):
    fname = urllib.parse.quote(os.path.basename(zpath))
    with open(zpath, "rb") as f:
        req = urllib.request.Request(f"{UPLOADS}/releases/{release_id}/assets?name={fname}", method="POST", data=f.read())
    req.add_header("Authorization", auth)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/zip")
    with urllib.request.urlopen(req, timeout=600) as r:
        r.read()


def publish(name, title, notes, zpath):
    if DRY:
        print(f"[dry-run] POST {API}/releases tag={name}; upload {zpath}")
        return
    auth = github_auth()
    try:
        rel = api(auth, "GET", f"/releases/tags/{urllib.parse.quote(name)}")
        print("GitHub release already exists:", rel["html_url"])
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        rel = api(auth, "POST", "/releases", {"tag_name": name, "name": title, "body": notes,
                                              "draft": False, "prerelease": False})
        print("created GitHub release:", rel["html_url"])
    fname = os.path.basename(zpath)
    if any(a["name"] == fname for a in rel.get("assets", [])):
        print("asset already attached:", fname)
        return
    upload(auth, rel["id"], zpath)
    print("uploaded", fname)


def main():
    date_part = arg("--date") or datetime.date.today().strftime("%y%m%d")
    date_iso = datetime.datetime.strptime(date_part, "%y%m%d").date().isoformat()
    build = steam_build_id()
    name = f"reka-ko_{date_part}_build{build}" + (f"-r{arg('--rev')}" if arg("--rev") else "")
    tags = run("git", "tag", "--list", name, capture=True).strip()
    print("release:", name, "(tag exists)" if tags else "")
    existing_zip = os.path.join(ROOT, "release", name, f"{name}.zip")
    if tags:
        if not os.path.exists(existing_zip):
            sys.exit(f"tag {name} exists but {existing_zip} is missing")
        zpath, hashes = existing_zip, {}
    else:
        zpath, hashes = package(name, date_iso, build)
    with open(os.path.join(TRANSLATIONS, "ko.json"), encoding="utf-8") as f:
        count = len(json.load(f))
    title = f"REKA 한국어 패치 {date_part} (Steam build {build})"
    notes = (f"Steam build {build}, 게임 버전 {game_version()} ({date_iso})용 빌드.\n"
             f"- 번역 {count:,}개 항목, 언어 메뉴에 한국어 추가(다른 언어 유지), 한글 폰트\n"
             f"설치: zip의 Reka_Data 폴더를 게임 폴더에 덮어쓰기. 자세한 내용은 zip 안의 설치방법.txt, 파일 해시는 RELEASES.md 참고.\n"
             f"원작의 권리는 Emberstorm Entertainment에 있습니다.")
    if not tags and not DRY:
        path = os.path.join(ROOT, "RELEASES.md")
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write("# 릴리스 기록\n\n빌드 결과물은 게임 원본 에셋을 수정한 파일이라 저장소에 커밋하지 않습니다. "
                        "Release 첨부로 보관합니다.\n각 릴리스는 같은 이름의 git 태그를 가리킵니다.\n")
        with open(path, "a", encoding="utf-8", newline="\n") as f:
            f.write(releases_entry(name, date_iso, build, zpath, hashes, count))
        run("git", "add", "-A")
        run("git", "commit", "-m", f"Add release record for {name}")
        run("git", "tag", name)
    if NO_UPLOAD:
        return
    run("git", "push", "origin", "HEAD:main", f"refs/tags/{name}")  # never --tags: only this tag goes public
    publish(name, title, notes, zpath or existing_zip)


if __name__ == "__main__":
    main()
