"""日本語音声を PC パッケージへ注入する。

対応表 (plan.json) の鍵は <グループ>.<音声名>。360 の cooked パッケージが
保持している出身パスから作られる。名前だけで照合すると同名の別テイクに
誤爆するので、必ずこの鍵を使う。

差し替えた音声だけでなく、パッケージ内の全 SoundNodeWave を再出力して
バルクデータのオフセットを新しい位置に書き直す。これを怠るとゲームが
起動時に BulkDataOffsetInFile == Ar.Tell() で落ちる。

    python inject.py                        全パッケージ
    python inject.py Human_Marcus_Chatter    個別
    python inject.py --selftest <.upk>       置換ゼロで再構築し元と一致するか確認
"""
import sys, os, json, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ue3 import Package, Ar
from config import CFG

PC_SLOT = 1   # CompressedPCData


def _prop_spans(pk, exp):
    """Return {propname: (abs_value_offset, size, type)} for this export."""
    a = Ar(pk.d, pk.be, exp['off']); a.i32()
    spans = {}
    while True:
        ni = a.i32(); nn = a.i32()
        if pk.name(ni, nn) == 'None': break
        nm = pk.name(ni, nn)
        ti = a.i32(); tn = a.i32(); ty = pk.name(ti, tn)
        size = a.i32(); a.i32()
        if ty in ('StructProperty', 'ByteProperty'): a.i32(); a.i32()
        elif ty == 'BoolProperty': a.i32()
        spans[nm] = (a.p, size, ty)
        a.p += size
    return spans, a.p - exp['off']


def rebuild_wave(pk, exp, new_ogg, duration, sample_data_size, new_start):
    """Return the new serial blob for one SoundNodeWave, with every bulk-data
    offset rewritten for its new position in the file.  Pass new_ogg=None to
    relocate an untouched wave without altering its audio."""
    E = '>' if pk.be else '<'
    spans, prop_end = _prop_spans(pk, exp)
    head = bytearray(pk.d[exp['off']:exp['off']+prop_end])
    for nm, val, fmt in (('Duration', duration, 'f'), ('SampleDataSize', sample_data_size, 'i')):
        if nm in spans and val is not None:
            off, size, ty = spans[nm]
            assert size == 4, f"{nm} size {size}"
            struct.pack_into(E+fmt, head, off - exp['off'], val)
    # read existing bulk blocks
    a = Ar(pk.d, pk.be, exp['off'] + prop_end)
    blocks = []
    for i in range(4):
        fl = a.u32(); c = a.i32(); sz = a.i32(); off = a.i32()
        blocks.append([fl, c, sz, off, pk.d[a.p:a.p+sz]])
        a.p += sz
    assert a.p == exp['off'] + exp['size']
    if new_ogg is not None:
        blocks[PC_SLOT][1] = len(new_ogg)
        blocks[PC_SLOT][2] = len(new_ogg)
        blocks[PC_SLOT][4] = new_ogg
    # re-emit with corrected absolute payload offsets
    out = bytearray(head)
    pos = new_start + len(head)
    for b in blocks:
        payload_at = pos + 16
        out += struct.pack(E+'IiiI', b[0], b[1], b[2], payload_at) + b[4]
        pos = payload_at + len(b[4])
    return bytes(out)


def _check_layout(pk, label):
    """エクスポートがデータ領域を隙間なく埋めていることを確かめる。"""
    exps = sorted(pk.exports, key=lambda e: e['off'])
    p = exps[0]['off']
    for e in exps:
        assert e['off'] == p, f"{label}: layout gap at {e['name']}"
        p += e['size']
    assert p == len(pk.d), f"{label}: trailing bytes"
    return exps, exps[0]['off']


def build(pcname, plan, man, pcin, out_dir, report=True):
    """1パッケージを再構築して out_dir へ書き出す。"""
    src = os.path.join(pcin, pcname + '.upk')
    pk = Package(src); E = '>' if pk.be else '<'
    want = plan[pcname]                     # key(lower) -> [jpfile, wavename]
    exps, data_start = _check_layout(pk, pcname)

    body = bytearray(); newpos = {}; hit = 0; miss = []
    for e in exps:
        cur = data_start + len(body)
        key = pk.path_of(e).lower()
        if pk.classname(e) == 'SoundNodeWave':
            ogg = dur = sds = None
            if key in want:
                jpfile, wave = want[key]
                tag = f"{jpfile[:-4]}__{wave}"
                m = man.get(tag); ogg_path = os.path.join(CFG.ogg, tag + '.ogg')
                if not m or not os.path.exists(ogg_path):
                    miss.append(tag)
                else:
                    ogg = open(ogg_path, 'rb').read()
                    dur, sds = m['duration'], m['sample_data_size']
                    hit += 1
            # 差し替えの有無によらず再出力する（オフセットを追従させるため）
            blob = rebuild_wave(pk, e, ogg, dur, sds, cur)
        else:
            blob = pk.d[e['off']:e['off']+e['size']]
        newpos[e['idx']] = (cur, len(blob)); body += blob

    newd = bytearray(pk.d[:data_start]) + body
    for e in pk.exports:
        off, size = newpos[e['idx']]
        struct.pack_into(E+'ii', newd, e['entry']+32, size, off)
    CFG.ensure(out_dir)
    dst = os.path.join(out_dir, pcname + '.upk')
    open(dst, 'wb').write(newd)
    if report:
        print(f"  {pcname:<32} {hit:>5}/{len(want):<5} {len(pk.d):>12,} -> {len(newd):>12,} "
              f"({len(newd)-len(pk.d):+,})" + (f"  MISSING {len(miss)}" if miss else ""))
    return hit, len(want), miss


def rebuild(pc_path, out_path, replacements):
    """置換を指定して1本を再構築する。replacements は {音声名: (ogg, 秒, PCM量)}。
    空の辞書を渡すと純粋な再構築になり、元ファイルと一致するはず。"""
    pk = Package(pc_path)
    E = '>' if pk.be else '<'
    exps, data_start = _check_layout(pk, os.path.basename(pc_path))

    body = bytearray(); newpos = {}; hit = 0
    for e in exps:
        cur = data_start + len(body)
        if pk.classname(e) == 'SoundNodeWave' and e['name'] in replacements:
            ogg, dur, sds = replacements[e['name']]
            blob = rebuild_wave(pk, e, ogg, dur, sds, cur); hit += 1
        else:
            blob = pk.d[e['off']:e['off']+e['size']]
        newpos[e['idx']] = (cur, len(blob)); body += blob

    newd = bytearray(pk.d[:data_start]) + body
    for e in pk.exports:
        off, size = newpos[e['idx']]
        struct.pack_into(E+'ii', newd, e['entry']+32, size, off)
    open(out_path, 'wb').write(newd)
    return hit, len(pk.d), len(newd)


def main():
    if sys.argv[1:2] == ['--selftest']:
        src = sys.argv[2]
        dst = os.path.join(CFG.ensure(CFG.work), '_selftest.upk')
        hit, a, b = rebuild(src, dst, {})
        same = open(src, 'rb').read() == open(dst, 'rb').read()
        os.remove(dst)
        print(f"{a:,} -> {b:,} bytes   元ファイルと一致: {'YES' if same else 'NO'}")
        return

    pcin = CFG.original
    if not os.path.isdir(pcin):
        raise SystemExit(
            "\n[エラー] 無改造のオリジナルが見つかりません。\n"
            f"  {pcin}\n"
            "手順2（02_バックアップを取る.bat）を先に実行してください。\n")
    if not os.path.exists(CFG.plan):
        raise SystemExit(f"対応表がありません。\n  {CFG.plan}\n手順5（05_対応表を作る.bat）を先に実行してください。")
    if not os.path.exists(CFG.manifest):
        raise SystemExit(f"変換結果がありません。\n  {CFG.manifest}\n手順6（06_Oggにする.bat）を先に実行してください。")

    plan = json.load(open(CFG.plan)); man = json.load(open(CFG.manifest))
    targets = sys.argv[1:] or sorted(plan)
    th = tw = 0; allmiss = []
    for t in targets:
        h, w, m = build(t, plan, man, pcin, CFG.upk_out); th += h; tw += w; allmiss += m
    print(f"\ntotal injected {th:,}/{tw:,}   missing {len(allmiss)}")


if __name__ == '__main__':
    main()
