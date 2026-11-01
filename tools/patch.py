"""Build the patched game files into work/out/ (laid out like the game folder).

What it does, all inside Reka_Data/resources.assets:
  - I2Languages: enable the dormant Korean language slot and fill it from translations/ko.json
  - Roboto-Bold SDF (an unused TMP sample font): becomes a dynamic Noto Sans KR font asset
  - TMP Settings: that font becomes the global fallback, modern Hangul line breaking on

usage: patch.py [--pseudo]   --pseudo marks every line instead of translating, to find hardcoded text
"""
import json
import os
import shutil
import sys

import build_font
import i2format
from common import DATA, GAME_ROOT, ROOT, TRANSLATIONS, WORK, load_env, typetree_generator
from fontTools.ttLib import TTFont

KO_SLOT_NAME = "Korean"
FONT_ASSET_ID = 2105  # "Roboto-Bold SDF", referenced by nothing in the game
FONT_FILE_ID = 264  # "Roboto-Bold"
TMP_SETTINGS_IDS = (2113, 2117)
I2_ID = 2115
# The language dropdown takes its labels from a fixed list in a prefab: the 10th row, which Korean
# lands on, is labelled by this developer-only term, so it reads 한국어 in every language.
MENU_LABEL_TERM = "UI/MainMenu/Settings/Language/DisplayLocalizationKeys"

POINT_SIZE = 64
PADDING = 6
ATLAS = 2048
RENDER_MODE = 4169  # GlyphRenderMode.SDFAA
FACE_SCALE = 1.0


def load_translations():
    path = os.path.join(TRANSLATIONS, "ko.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def patch_i2(obj, pseudo):
    src = i2format.parse(obj.get_raw_data())
    slot = next(i for i, l in enumerate(src["languages"]) if l["Name"] == KO_SLOT_NAME)
    src["languages"][slot]["Flags"] = 0
    tr = load_translations()
    missing = 0
    for t in src["terms"]:
        en = t["Languages"][0]
        if pseudo:
            ko = "한글" + en if en else ""
        elif t["Term"] in tr:
            ko = tr[t["Term"]]
        else:
            missing += bool(en)
            ko = en
        t["Languages"][slot] = ko
        if t["Term"] == MENU_LABEL_TERM:
            t["Languages"][:9] = ["한국어"] * 9
            t["Languages"][slot] = "한국어"
    obj.set_raw_data(i2format.build(src))
    print(f"I2: slot {slot}, {len(src['terms'])} terms, {missing} left in English")
    return "".join(t["Languages"][slot] for t in src["terms"])


def face_info(path):
    f = TTFont(path)
    upm = f["head"].unitsPerEm
    hhea, os2 = f["hhea"], f["OS/2"]
    px = POINT_SIZE / upm
    asc, desc = hhea.ascent * px, hhea.descent * px
    return {
        "m_FaceIndex": 0, "m_FamilyName": "Noto Sans KR", "m_StyleName": "Regular",
        "m_PointSize": float(POINT_SIZE), "m_Scale": FACE_SCALE, "m_UnitsPerEM": upm,
        "m_LineHeight": asc - desc, "m_AscentLine": asc,
        "m_CapLine": os2.sCapHeight * px, "m_MeanLine": os2.sxHeight * px, "m_Baseline": 0.0,
        "m_DescentLine": desc, "m_SuperscriptOffset": asc, "m_SuperscriptSize": 0.5,
        "m_SubscriptOffset": desc, "m_SubscriptSize": 0.5,
        "m_UnderlineOffset": -0.1 * POINT_SIZE, "m_UnderlineThickness": 0.05 * POINT_SIZE,
        "m_StrikethroughOffset": 0.28 * POINT_SIZE, "m_StrikethroughThickness": 0.05 * POINT_SIZE,
        "m_TabWidth": 0.25 * POINT_SIZE,
    }


def patch_font(objs, fa_nodes, otf):
    font = objs[FONT_FILE_ID]
    tree = font.read_typetree()
    with open(otf, "rb") as f:
        tree["m_FontData"] = list(f.read())
    tree["m_Name"] = "NotoSansKR-Regular"
    font.save_typetree(tree)

    asset = objs[FONT_ASSET_ID]
    t = asset.read_typetree(fa_nodes)
    t["m_Name"] = "NotoSansKR SDF"
    t["m_FaceInfo"] = face_info(otf)
    cs = t["m_CreationSettings"]
    cs.update(pointSize=POINT_SIZE, padding=PADDING, atlasWidth=ATLAS, atlasHeight=ATLAS, renderMode=RENDER_MODE,
              pointSizeSamplingMode=0, characterSetSelectionMode=7, characterSequence="", referencedFontAssetGUID="")
    t["m_AtlasWidth"] = t["m_AtlasHeight"] = ATLAS
    t["m_AtlasPadding"] = PADDING
    t["m_AtlasRenderMode"] = RENDER_MODE
    t["m_IsMultiAtlasTexturesEnabled"] = 1
    t["m_UsedGlyphRects"] = []
    t["m_FreeGlyphRects"] = [{"m_X": 0, "m_Y": 0, "m_Width": ATLAS - 1, "m_Height": ATLAS - 1}]
    asset.save_typetree(t, fa_nodes)

    mat = objs[t["m_Material"]["m_PathID"]]
    m = mat.read_typetree()
    m["m_Name"] = "NotoSansKR SDF Material"
    floats = dict((k, v) for k, v in m["m_SavedProperties"]["m_Floats"])
    floats.update(_GradientScale=float(PADDING + 1), _TextureWidth=float(ATLAS), _TextureHeight=float(ATLAS))
    m["m_SavedProperties"]["m_Floats"] = list(floats.items())
    mat.save_typetree(m)


def patch_settings(objs, st_nodes):
    for pid in TMP_SETTINGS_IDS:
        o = objs[pid]
        t = o.read_typetree(st_nodes)
        t["m_fallbackFontAssets"] = [{"m_FileID": 0, "m_PathID": FONT_ASSET_ID}]
        t["m_UseModernHangulLineBreakingRules"] = 1
        o.save_typetree(t, st_nodes)


def main():
    pseudo = "--pseudo" in sys.argv
    gen = typetree_generator()
    fa_nodes = json.loads(gen.get_nodes_as_json("Unity.TextMeshPro", "TMPro.TMP_FontAsset"))
    st_nodes = json.loads(gen.get_nodes_as_json("Unity.TextMeshPro", "TMPro.TMP_Settings"))

    # Always start from the untouched original, also when the patch is currently installed.
    backup = os.path.join(WORK, "backup", "Reka_Data", "resources.assets")
    env = load_env(backup if os.path.exists(backup) else os.path.join(DATA, "resources.assets"))
    objs = {o.path_id: o for o in env.objects}
    text = patch_i2(objs[I2_ID], pseudo)
    otf = build_font.build(text)
    print("font subset", os.path.getsize(otf))
    patch_font(objs, fa_nodes, otf)
    patch_settings(objs, st_nodes)

    out = os.path.join(WORK, "out", "Reka_Data")
    os.makedirs(out, exist_ok=True)
    sf = list(env.files.values())[0]
    with open(os.path.join(out, "resources.assets"), "wb") as f:
        f.write(sf.save())
    print("written", os.path.getsize(os.path.join(out, "resources.assets")))


if __name__ == "__main__":
    main()
