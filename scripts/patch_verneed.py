import struct

def patch_elf_verneed(filepath, outpath):
    with open(filepath, 'rb') as f:
        data = bytearray(f.read())
    
    e_type, e_machine, e_version, e_entry, e_phoff, e_shoff, e_flags, e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx = struct.unpack_from('<HHIIIIIHHHHHH', data, 16)
    sections = []
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size, sh_link = struct.unpack_from('<IIIIIII', data, off)
        sections.append({'name_idx': sh_name, 'type': sh_type, 'addr': sh_addr, 'offset': sh_offset, 'size': sh_size, 'link': sh_link})

    shstr = data[sections[e_shstrndx]['offset'] : sections[e_shstrndx]['offset'] + sections[e_shstrndx]['size']]
    verneed_sec, dynstr_sec = None, None
    for s in sections:
        name = shstr[s['name_idx']:].split(b'\x00')[0].decode('latin1')
        if name == '.gnu.version_r': verneed_sec = s
        if name == '.dynstr': dynstr_sec = s

    if not verneed_sec or not dynstr_sec:
        print(f"No verneed in {filepath}")
        return

    dynstr_off = dynstr_sec['offset']
    off = verneed_sec['offset']
    vn_cnt = verneed_sec['size']
    
    # We want to replace any GLIBC_2.1x (e.g. 2.16, 2.17, 2.18) with GLIBC_2.4
    # and its hash with 0x0d696914 (gnu hash for GLIBC_2.4)
    # gnu_hash("GLIBC_2.4") = 0x0d696914
    hash_2_4 = 0x0d696914
    
    # Let's inspect each vn_aux
    curr_vn = off
    patched_count = 0
    while curr_vn < off + verneed_sec['size']:
        vn_version, vn_cnt_aux, vn_file, vn_aux, vn_next = struct.unpack_from('<HHIII', data, curr_vn)
        curr_vna = curr_vn + vn_aux
        for j in range(vn_cnt_aux):
            vna_hash, vna_flags, vna_other, vna_name, vna_next = struct.unpack_from('<IHHII', data, curr_vna)
            vname = data[dynstr_off + vna_name :].split(b'\x00')[0].decode('latin1')
            if vname.startswith('GLIBC_2.1'):
                print(f"Patching {vname} (hash {hex(vna_hash)}) -> GLIBC_2.4 in {filepath}")
                # Overwrite vname in dynstr with GLIBC_2.4\x00
                vname_bytes = b'GLIBC_2.4\x00'
                data[dynstr_off + vna_name : dynstr_off + vna_name + len(vname_bytes)] = vname_bytes
                # Overwrite hash with hash_2_4
                struct.pack_into('<I', data, curr_vna, hash_2_4)
                patched_count += 1
            if vna_next == 0: break
            curr_vna += vna_next
        if vn_next == 0: break
        curr_vn += vn_next
    
    with open(outpath, 'wb') as f:
        f.write(data)
    print(f"Wrote {outpath} with {patched_count} patches.")

# Patch clean_desmume.so -> desmume2015_libretro.so and melonds_libretro.so
patch_elf_verneed('build_release/temp/cores/clean_desmume.so', 'build_release/temp/cores/desmume2015_libretro.so')
patch_elf_verneed('build_release/temp/cores/clean_desmume.so', 'build_release/temp/cores/melonds_libretro.so')

# Patch libstdc++.so.6
patch_elf_verneed('build_release/temp/libstdc++.so.6', 'build_release/temp/libstdc++.so.6')
