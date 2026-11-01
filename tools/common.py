"""Shared paths and helpers for the Reka Korean patch tools."""
import os

import UnityPy
from TypeTreeGeneratorAPI import TypeTreeGenerator

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GAME_ROOT = os.environ.get("REKA_GAME", r"F:\SteamLibrary\steamapps\common\Reka")
DATA = os.path.join(GAME_ROOT, "Reka_Data")
AA = os.path.join(DATA, "StreamingAssets", "aa", "StandaloneWindows64")
WORK = os.path.join(ROOT, "work")
TRANSLATIONS = os.path.join(ROOT, "translations")
UNITY_VERSION = "6000.1.17f1"


def typetree_generator():
    gen = TypeTreeGenerator(UNITY_VERSION)
    with open(os.path.join(GAME_ROOT, "GameAssembly.dll"), "rb") as f:
        dll = f.read()
    with open(os.path.join(DATA, "il2cpp_data", "Metadata", "global-metadata.dat"), "rb") as f:
        meta = f.read()
    gen.load_il2cpp(dll, meta)
    return gen


def load_env(path):
    env = UnityPy.load(path)
    return env


def attach_generator(env, gen):
    env.typetree_generator = gen
    return env
