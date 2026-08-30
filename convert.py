"""XMA → WAV (vgmstream) → Ogg Vorbis (ffmpeg)。

対応表 (plan.json) が必要とする音声だけを変換し、注入時に書き戻す
再生時間と PCM データ量を manifest に記録する。
変換済みは飛ばすので、中断しても再実行でよい。

    python convert.py
"""
import sys, os, json, struct, subprocess, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CFG

VGM = CFG.vgmstream
FFM = CFG.ffmpeg
QUALITY = CFG.quality
RATE = CFG.rate


def wav_info(path):
    """WAV のヘッダから (サンプルレート, チャンネル数, ビット数, データ長) を取る。"""
    d = open(path, 'rb').read(1024)
    assert d[:4] == b'RIFF' and d[8:12] == b'WAVE'
    p = 12; rate = ch = bits = None
    while p + 8 <= len(d):
        cid = d[p:p+4]; sz = struct.unpack_from('<I', d, p+4)[0]
        if cid == b'fmt ':
            ch, rate = struct.unpack_from('<HI', d, p+10)
            bits = struct.unpack_from('<H', d, p+22)[0]
        elif cid == b'data':
            return rate, ch, bits, sz
        p += 8 + sz + (sz & 1)
    raise ValueError("no data chunk")


def xma_to_ogg(src, ogg, tmp):
    """1本ぶん変換する。成功したら (再生時間, チャンネル数, レート) を返す。
    失敗したら理由の文字列を返す。vgmstream は -i を付けないとループする。"""
    if os.path.exists(tmp): os.remove(tmp)
    r = subprocess.run([VGM, '-i', '-o', tmp, src], capture_output=True)
    if r.returncode or not os.path.exists(tmp):
        return 'vgmstream'
    rate, ch, bits, dbytes = wav_info(tmp)
    dur = (dbytes // (ch * bits // 8)) / rate
    r = subprocess.run([FFM, '-y', '-hide_banner', '-loglevel', 'error', '-i', tmp,
                        '-c:a', 'libvorbis', '-q:a', QUALITY, '-ar', str(RATE), '-ac', '1', ogg],
                       capture_output=True)
    if r.returncode or not os.path.exists(ogg):
        return 'ffmpeg'
    return (dur, ch, rate)


def main():
    CFG.need_tool(VGM, "vgmstream-cli")
    CFG.need_tool(FFM, "ffmpeg")
    CFG.need_dir(CFG.snd, "書き出した XMA のフォルダ（手順4「音声を取り出す」を先に実行してください）")
    if not os.path.exists(CFG.plan):
        raise SystemExit(f"対応表がありません。\n  {CFG.plan}\n手順5（05_対応表を作る.bat）を先に実行してください。")

    CFG.ensure(CFG.ogg)
    plan = json.load(open(CFG.plan))
    need = {}
    for pcpkg, items in plan.items():
        for key, (jpfile, wave) in items.items():
            need[(jpfile[:-4], wave)] = None
    print(f"to convert: {len(need):,}", flush=True)

    manifest = json.load(open(CFG.manifest)) if os.path.exists(CFG.manifest) else {}
    # 同時に2つ走らせても衝突しないよう、プロセスごとに別名にする。
    tmp = os.path.join(tempfile.gettempdir(), f"gow2_{os.getpid()}.wav")
    done = skip = 0; fails = []

    for i, (folder, wave) in enumerate(sorted(need)):
        tag = f"{folder}__{wave}"
        ogg = os.path.join(CFG.ogg, tag + ".ogg")
        if tag in manifest and os.path.exists(ogg):
            skip += 1; continue
        src = os.path.join(CFG.snd, folder, "SoundNodeWave", wave + ".xma")
        res = xma_to_ogg(src, ogg, tmp)
        if isinstance(res, str):
            fails.append((tag, res)); continue
        dur, ch, rate = res
        manifest[tag] = dict(duration=dur, sample_data_size=int(round(dur*RATE))*2,
                             ogg_size=os.path.getsize(ogg), src_channels=ch, src_rate=rate)
        done += 1
        if done % 500 == 0:
            json.dump(manifest, open(CFG.manifest, 'w'))
            print(f"  {i+1}/{len(need)}  converted={done} skipped={skip} failed={len(fails)}", flush=True)

    json.dump(manifest, open(CFG.manifest, 'w'))
    if os.path.exists(tmp): os.remove(tmp)      # 一時 WAV を残さない
    print(f"\nDONE converted={done} skipped={skip} failed={len(fails)}  manifest={len(manifest):,}")
    for f in fails[:15]: print("   FAIL", f)


if __name__ == '__main__':
    main()
