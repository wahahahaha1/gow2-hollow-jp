"""UE3 (package version 575) の読み取り。

- Package  … 名前表・インポート表・エクスポート表。PC(LE) と Xbox360(BE) の両対応
- walk_props … タグ付きプロパティ列の走査
- waves    … SoundNodeWave の音声ペイロード取り出し

単体でも動く:
    python ue3.py info    <パッケージ>...            概要とクラス内訳
    python ue3.py props   <パッケージ>...            最初の SoundNodeWave を分解
    python ue3.py extract <パッケージ> <出力先>      音声ペイロードを書き出す
"""
import struct, os, sys


class Ar:
    def __init__(s, d, be, p=0): s.d=d; s.e='>' if be else '<'; s.p=p
    def u32(s): v=struct.unpack_from(s.e+'I',s.d,s.p)[0]; s.p+=4; return v
    def i32(s): v=struct.unpack_from(s.e+'i',s.d,s.p)[0]; s.p+=4; return v
    def u64(s): v=struct.unpack_from(s.e+'Q',s.d,s.p)[0]; s.p+=8; return v
    def raw(s,n): v=s.d[s.p:s.p+n]; s.p+=n; return v
    def fstr(s):
        n=s.i32()
        if n==0: return ''
        if n<0:
            b=s.raw(-2*n); return b.decode('utf-16-be' if s.e=='>' else 'utf-16-le',errors='replace').rstrip('\0')
        return s.raw(n).decode('latin-1').rstrip('\0')


class Package:
    def __init__(self, path):
        self.path=path
        self.d=open(path,'rb').read()
        tag=struct.unpack_from('<I',self.d,0)[0]
        self.be = (tag != 0x9E2A83C1)
        a=Ar(self.d,self.be); a.u32()
        v=a.u32(); self.ver=v&0xFFFF; self.lic=v>>16
        self.hdrsize=a.i32(); self.folder=a.fstr(); self.flags=a.u32()
        self.namec=a.i32(); self.nameo=a.i32()
        self.expc=a.i32(); self.expo=a.i32()
        self.impc=a.i32(); self.impo=a.i32()
        self.dependso=a.i32()
        self._names(); self._imports(); self._exports()

    def _names(self):
        a=Ar(self.d,self.be,self.nameo); self.names=[]
        for _ in range(self.namec):
            s=a.fstr(); a.u64(); self.names.append(s)

    def name(self, idx, num=0):
        s = self.names[idx] if 0<=idx<len(self.names) else f"<bad:{idx}>"
        return f"{s}_{num-1}" if num else s

    def _imports(self):
        a=Ar(self.d,self.be,self.impo); self.imports=[]
        for _ in range(self.impc):
            cp=a.i32(); cpn=a.i32(); cn=a.i32(); cnn=a.i32()
            outer=a.i32(); on=a.i32(); onn=a.i32()
            self.imports.append(dict(cls=self.name(cn,cnn), outer=outer, name=self.name(on,onn)))

    def _exports(self):
        a=Ar(self.d,self.be,self.expo); self.exports=[]
        for i in range(self.expc):
            entry=a.p
            cls=a.i32(); sup=a.i32(); outer=a.i32()
            nm=a.i32(); nmn=a.i32(); arch=a.i32()
            flags=a.u64(); size=a.i32(); off=a.i32(); expflags=a.u32()
            n=a.i32(); a.raw(4*n)             # GenerationNetObjectCount
            a.raw(16); a.u32()                # PackageGuid, PackageFlags
            self.exports.append(dict(idx=i, cls=cls, outer=outer, name=self.name(nm,nmn),
                                     size=size, off=off, flags=flags, entry=entry))
        self.export_end = a.p

    def resolve(self, pkgindex):
        """UE3 package index: >0 export (1-based), <0 import (-1-based), 0 = None"""
        if pkgindex>0:  return self.exports[pkgindex-1]['name']
        if pkgindex<0:  return self.imports[-pkgindex-1]['name']
        return None

    def classname(self, exp): return self.resolve(exp['cls']) or 'Class'

    def path_of(self, exp):
        parts=[exp['name']]; o=exp['outer']
        while o:
            if o>0: e=self.exports[o-1]; parts.append(e['name']); o=e['outer']
            else:   parts.append(self.imports[-o-1]['name']); o=self.imports[-o-1]['outer']
        return '.'.join(reversed(parts))


def walk_props(pk, exp, verbose=False):
    """Walk the tagged property list of an export. Returns offset (relative to
    export start) just past the terminating 'None', and the list of properties."""
    a = Ar(pk.d, pk.be, exp['off'])
    net = a.i32()                       # UObject NetIndex
    props = []
    while True:
        ni = a.i32(); nn = a.i32()
        nm = pk.name(ni, nn)
        if nm == 'None':
            break
        ti = a.i32(); tn = a.i32(); ty = pk.name(ti, tn)
        size = a.i32(); arr = a.i32()
        extra = None
        if ty == 'StructProperty':  extra = pk.name(a.i32(), a.i32())
        elif ty == 'ByteProperty':  extra = pk.name(a.i32(), a.i32())
        elif ty == 'BoolProperty':  extra = a.i32()
        val = a.raw(size)
        props.append((nm, ty, size, arr, extra, val))
        if verbose:
            show = extra if extra is not None else ''
            print(f"     {nm:<28} {ty:<16} size={size:<7} {show}")
    return a.p - exp['off'], props, net


def waves(pk):
    """yield dict(name, slot, data, props) for each SoundNodeWave"""
    for e in pk.exports:
        if pk.classname(e) != 'SoundNodeWave': continue
        end, props, net = walk_props(pk, e)
        a = Ar(pk.d, pk.be, e['off'] + end)
        blocks = []
        for i in range(4):
            hdr = a.p
            fl = a.u32(); c = a.i32(); sz = a.i32(); off = a.i32()
            blocks.append(dict(slot=i, hdr=hdr, flags=fl, cnt=c, size=sz, off=off, data_at=a.p))
            a.p += sz
        assert a.p == e['off'] + e['size'], f"{e['name']}: {a.p} != {e['off']+e['size']}"
        nz = [b for b in blocks if b['size']]
        pr = {p[0]: p[5] for p in props}
        yield dict(exp=e, name=e['name'], props=props, pr=pr, blocks=blocks,
                   slot=nz[0]['slot'] if nz else None,
                   data=pk.d[nz[0]['data_at']:nz[0]['data_at']+nz[0]['size']] if nz else b'',
                   prop_end=end, net=net)


# ---------------------------------------------------------------- 単体実行

def _cmd_info(paths):
    import collections
    for p in paths:
        pk=Package(p)
        print(f"{os.path.basename(p)}  {'BE' if pk.be else 'LE'} ver={pk.ver} names={pk.namec} imports={pk.impc} exports={pk.expc}")
        print(f"  export table {pk.expo}..{pk.export_end} (header says {pk.hdrsize})  {'OK' if pk.export_end<=pk.hdrsize else 'OVERRUN!'}")
        c=collections.Counter(pk.classname(e) for e in pk.exports)
        for k,v in c.most_common(10): print(f"    {v:>6}  {k}")
        snw=[e for e in pk.exports if pk.classname(e)=='SoundNodeWave']
        if snw:
            lo=min(e['off'] for e in snw); hi=max(e['off']+e['size'] for e in snw)
            print(f"  SoundNodeWave: {len(snw)}  data range {lo:,}..{hi:,}  filesize {len(pk.d):,}")
            for e in snw[:3]:
                print(f"    {e['name']:<45} off={e['off']:>10,} size={e['size']:>9,}")


def _cmd_props(paths):
    for path in paths:
        pk = Package(path)
        snw = [e for e in pk.exports if pk.classname(e) == 'SoundNodeWave']
        if not snw:
            print(f"{os.path.basename(path)}: SoundNodeWave なし"); continue
        e = snw[0]
        print(f"########## {os.path.basename(path)}: {e['name']}  (serial {e['size']:,}) ##########")
        end, props, net = walk_props(pk, e, verbose=True)
        print(f"   NetIndex={net}  properties end at +{end} (0x{end:x}) of {e['size']}")
        rest = pk.d[e['off']+end : e['off']+e['size']]
        print(f"   remaining after props: {len(rest):,} bytes")
        for i in range(0, min(96, len(rest)), 16):
            print(f"     +{i:04x}  {rest[i:i+16].hex(' ')}")
        for magic in (b'OggS', b'RIFF', b'XMA2'):
            j = rest.find(magic)
            if j >= 0: print(f"     '{magic.decode()}' at +{j} of remainder")
        print()


def _cmd_extract(path, out):
    pk = Package(path)
    os.makedirs(out, exist_ok=True)
    ext = {0:'raw',1:'ogg',2:'xma',3:'ps3'}
    n=0
    for w in waves(pk):
        if not w['data']: continue
        open(os.path.join(out, w['name']+'.'+ext[w['slot']]), 'wb').write(w['data'])
        n+=1
    print(f"extracted {n} payloads to {out}")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    cmd, args = sys.argv[1], sys.argv[2:]
    if   cmd == 'info':    _cmd_info(args)
    elif cmd == 'props':   _cmd_props(args)
    elif cmd == 'extract': _cmd_extract(args[0], args[1])
    else: raise SystemExit(f"不明なコマンド: {cmd}\n{__doc__}")
