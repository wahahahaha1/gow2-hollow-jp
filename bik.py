"""カットシーン (.bik) の組み替えと検査。

日本語版 ISO の .bik は「共通の 5.1ch ベッド 6 トラック + 日本語セリフ 3 トラック」
の 9 トラック構成。Hollow の音量振り分けはトラックID 0〜4 を決め打ちで各スピーカーへ
割り当て、5 以上をすべてセンターへ潰す。つまり日本語トラック (6,7,8) を指定させると
セリフ 3 本が 1 つのスピーカーに重なって潰れる。

そこでファイル側を組み替え、日本語セリフを英語が使っていた 0・1・5 番の席へ移す。
音声データ自体は再エンコードせずそのまま運ぶので劣化しない。

  new 0 <- old 6 (JP)      new 3 <- old 3 (共通)
  new 1 <- old 7 (JP)      new 4 <- old 4 (LFE)
  new 2 <- old 2 (共通)    new 5 <- old 8 (JP)

    python bik.py remux    <入力.bik> <出力.bik>      組み替え
    python bik.py validate <.bik>...                  構造の整合性
    python bik.py demux    <.bik>...                  トラック別のデータ量
    python bik.py verify   <元フォルダ> <出力フォルダ>  組み替え結果の照合

※ Hollow は現状ムービー音声を一切鳴らさないため、組み替えても聞こえる音は変わらない。
"""
import struct, sys, os

MAP = [6, 7, 2, 3, 4, 8]


# ---------------------------------------------------------------- 組み替え

def remux(src, dst):
    if os.path.abspath(src) == os.path.abspath(dst):
        raise SystemExit("入力と出力が同じです")
    fi = open(src, 'rb')
    head = fi.read(64)
    if head[:3] != b'BIK':
        raise SystemExit(f"{src}: Bink ファイルではありません")
    (size, nframes, largest, nframes2, w, h,
     fpsd, fpsdiv, vflags, ntracks) = struct.unpack_from('<10I', head, 4)
    if ntracks != 9:
        raise SystemExit(f"{src}: 9 トラックを想定していますが {ntracks} でした")

    fi.seek(0)
    hdr = fi.read(44 + 12*ntracks + 4*(nframes+1))
    maxbuf = list(struct.unpack_from(f'<{ntracks}I', hdr, 44))
    rates  = list(struct.unpack_from(f'<{ntracks}I', hdr, 44 + 4*ntracks))
    offs   = list(struct.unpack_from(f'<{nframes+1}I', hdr, 44 + 12*ntracks))

    nt = len(MAP)
    new_tbl_end = 44 + 12*nt
    new_hdr_end = new_tbl_end + 4*(nframes+1)

    fo = open(dst, 'wb')
    out = bytearray(head[:44])
    struct.pack_into('<I', out, 40, nt)                       # トラック数
    out += struct.pack(f'<{nt}I', *[maxbuf[t] for t in MAP])  # 最大バッファ
    out += struct.pack(f'<{nt}I', *[rates[t]  for t in MAP])  # レート + フラグ
    out += struct.pack(f'<{nt}I', *range(nt))                 # トラックID → 0..5
    assert len(out) == new_tbl_end
    fo.write(out)
    fo.write(b'\0' * (4*(nframes+1)))                         # オフセット表（後で埋める）

    new_offs = []
    biggest = 0
    for i in range(nframes):
        a, b = offs[i] & ~1, offs[i+1] & ~1
        fi.seek(a)
        frame = fi.read(b - a)
        # フレームをトラック別の音声パケットと末尾の映像データに分解する
        pkts, p = [], 0
        for _ in range(ntracks):
            n = struct.unpack_from('<I', frame, p)[0]; p += 4
            pkts.append(frame[p:p+n]); p += n
        video = frame[p:]

        new_offs.append(fo.tell() | (offs[i] & 1))            # キーフレーム印を維持
        buf = bytearray()
        for t in MAP:
            buf += struct.pack('<I', len(pkts[t])) + pkts[t]
        buf += video
        fo.write(buf)
        biggest = max(biggest, len(buf))

    new_offs.append(fo.tell())
    total = fo.tell()
    fo.seek(new_tbl_end)
    fo.write(struct.pack(f'<{nframes+1}I', *new_offs))
    fo.seek(4);  fo.write(struct.pack('<I', total - 8))       # サイズ欄
    fo.seek(12); fo.write(struct.pack('<I', biggest))         # 最大フレーム長
    fo.close(); fi.close()
    assert (new_offs[0] & ~1) == new_hdr_end, "ヘッダ長が合いません"
    print(f"  {os.path.basename(src)}: {os.path.getsize(src):,} -> {total:,} bytes, "
          f"{nframes} frames, largest {biggest:,}")


# ---------------------------------------------------------------- 検査

def validate(path):
    f = open(path, 'rb'); d = f.read(64)
    magic = d[:4]
    (size, nframes, largest, nframes2, w, h, fpsd, fpsdiv, vflags, ntracks) = struct.unpack_from('<10I', d, 4)
    fsize = os.path.getsize(path)
    print(f"{os.path.basename(path)}")
    print(f"  magic={magic.decode()} size_field={size:,} (file-8={fsize-8:,}) {'OK' if size==fsize-8 else 'MISMATCH'}")
    print(f"  frames={nframes} nframes2={nframes2} {w}x{h} largest_frame={largest:,} tracks={ntracks} vflags=0x{vflags:08x}")
    tbl = 44 + 12*ntracks
    f.seek(0); d = f.read(tbl + 4*(nframes+1))
    ids = struct.unpack_from(f'<{ntracks}I', d, 44 + 8*ntracks)
    print(f"  track table ends at {tbl}, ids={ids}")
    offs = list(struct.unpack_from(f'<{nframes+1}I', d, tbl))
    first = offs[0] & ~1
    expect = tbl + 4*(nframes+1)
    print(f"  offsets[0]={first} expected_hdr_end={expect} {'OK' if first==expect else 'MISMATCH'}")
    print(f"  offsets[last]={offs[-1]&~1:,} filesize={fsize:,} {'OK' if (offs[-1]&~1)==fsize else 'MISMATCH'}")
    kf = sum(1 for o in offs[:-1] if o & 1)
    noncontig = 0; maxframe = 0
    for i in range(nframes):
        a = offs[i] & ~1; b = offs[i+1] & ~1
        if a > b: noncontig += 1
        maxframe = max(maxframe, b - a)
    print(f"  keyframes={kf}  max actual frame len={maxframe:,} (header says {largest:,})")
    print(f"  offsets monotonic: {'OK' if noncontig==0 else 'FAIL'}")
    f.close()


def parse(path, maxframes=None):
    """トラック別のデータ量を測る。映像データには触れずパケット長だけ数える。"""
    f = open(path, 'rb')
    h = f.read(4096)
    (size, nframes, largest, nframes2, w, hgt, fpsd, fpsdiv, vflags, ntracks) = struct.unpack_from('<10I', h, 4)
    off = 44 + 4*ntracks
    rates = []
    for i in range(ntracks):
        sr, fl = struct.unpack_from('<HH', h, off); off += 4
        rates.append((sr, fl))
    off += 4*ntracks
    need = off + 4*(nframes+1)
    while len(h) < need:
        h += f.read(need - len(h))
    offsets = [o & ~1 for o in struct.unpack_from('<%dI' % (nframes+1), h, off)]

    totals = [0]*ntracks; nonzero = [0]*ntracks
    firstframe = [None]*ntracks; vtotal = 0
    n = nframes if maxframes is None else min(nframes, maxframes)
    for fi in range(n):
        f.seek(offsets[fi])
        data = f.read(offsets[fi+1] - offsets[fi])
        p = 0
        for t in range(ntracks):
            if p + 4 > len(data): break
            psize = struct.unpack_from('<I', data, p)[0]; p += 4
            if psize:
                totals[t] += psize; nonzero[t] += 1
                if firstframe[t] is None: firstframe[t] = fi
                p += psize
        vtotal += max(0, len(data) - p)
    f.close()
    return dict(path=path, ntracks=ntracks, nframes=nframes, n=n, totals=totals,
                nonzero=nonzero, firstframe=firstframe, vtotal=vtotal, rates=rates,
                fps=fpsd/fpsdiv if fpsdiv else 0)


def demux(path, maxframes=None):
    r = parse(path, maxframes)
    print(f"{os.path.basename(path)}  tracks={r['ntracks']} frames={r['nframes']} "
          f"scanned={r['n']} video_bytes={r['vtotal']}")
    for t in range(r['ntracks']):
        kbps = r['totals'][t]*8/1000/(r['n']/r['fps']) if r['fps'] else 0
        print(f"   t{t:02d} rate={r['rates'][t][0]} bytes={r['totals'][t]:>12,} "
              f"pkts={r['nonzero'][t]:>6} first={r['firstframe'][t]} {kbps:7.1f} kbps")


def verify(src_dir, out_dir, n=600):
    """組み替え後のファイルが、元の該当トラックをそのまま運んでいるか照合する。"""
    allok = True
    for name in sorted(os.listdir(out_dir)):
        if not name.lower().endswith('.bik'): continue
        s = parse(os.path.join(src_dir, name), n)
        o = parse(os.path.join(out_dir, name), n)
        vok = s['vtotal'] == o['vtotal']
        tok = all(o['totals'][i]  == s['totals'][MAP[i]]  for i in range(6))
        rok = all(o['rates'][i]   == s['rates'][MAP[i]]   for i in range(6))
        pok = all(o['nonzero'][i] == s['nonzero'][MAP[i]] for i in range(6))
        ok = vok and tok and rok and pok
        allok &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
        print(f"      video bytes  {s['vtotal']:>12,} -> {o['vtotal']:>12,}  {'OK' if vok else 'MISMATCH'}")
        print(f"      audio map    {'OK' if tok else 'MISMATCH'}   rates {'OK' if rok else 'MISMATCH'}   packets {'OK' if pok else 'MISMATCH'}")
        print(f"      new t0={o['totals'][0]:,} (src t6={s['totals'][6]:,}) | "
              f"new t1={o['totals'][1]:,} (src t7={s['totals'][7]:,}) | "
              f"new t5={o['totals'][5]:,} (src t8={s['totals'][8]:,})")
    print("\n=== ALL PASS ===" if allok else "\n=== FAILURES PRESENT ===")
    return allok


if __name__ == '__main__':
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    cmd, args = sys.argv[1], sys.argv[2:]
    mf = int(os.environ.get('MAXFRAMES', '0')) or None
    if   cmd == 'remux':    remux(args[0], args[1])
    elif cmd == 'validate': [ (validate(p), print()) for p in args ]
    elif cmd == 'demux':    [ (demux(p, mf), print()) for p in args ]
    elif cmd == 'verify':   verify(args[0], args[1])
    else: raise SystemExit(f"不明なコマンド: {cmd}\n{__doc__}")
