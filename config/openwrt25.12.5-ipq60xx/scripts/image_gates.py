import gzip
import hashlib
import struct
import zlib

PEB = 131072
LEB = 126976
MTD_BYTES = 101187584
VOLUMES = {0: ('kernel', 45), 1: ('rootfs', 189), 2: ('rootfs_data', 514)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def parse_fdt(data):
    require(len(data) >= 40, 'Short FDT')
    h = struct.unpack_from('>10I', data)
    magic, total, start, strings, _, _, _, _, slen, tree_len = h
    require(magic == 0xd00dfeed and total <= len(data), 'Invalid FDT header')
    require(strings + slen <= total and start + tree_len <= total, 'FDT outside bounds')
    table = data[strings:strings + slen]
    nodes, stack, pos = {}, [], start
    while pos < start + tree_len:
        token = struct.unpack_from('>I', data, pos)[0]
        pos += 4
        if token == 1:
            end = data.index(b'\0', pos, start + tree_len)
            stack.append(data[pos:end].decode('ascii'))
            pos = (end + 4) & ~3
            nodes['/' + '/'.join(stack[1:])] = {}
        elif token == 2:
            require(bool(stack), 'Unbalanced FDT')
            stack.pop()
        elif token == 3:
            size, off = struct.unpack_from('>II', data, pos)
            pos += 8
            require(pos + size <= start + tree_len, 'FDT property outside bounds')
            end = table.index(b'\0', off)
            name = table[off:end].decode('ascii')
            nodes['/' + '/'.join(stack[1:])][name] = data[pos:pos + size]
            pos = (pos + size + 3) & ~3
        elif token == 4:
            continue
        elif token == 9:
            require(not stack, 'Unclosed FDT nodes')
            return nodes
        else:
            raise ValueError('Unknown FDT token')
    raise ValueError('FDT end token missing')


def text(data):
    require(data.endswith(b'\0'), 'Expected terminated FDT string')
    return data[:-1].decode('ascii')


def check_fit(data):
    require(len(data) <= VOLUMES[0][1] * LEB, 'FIT exceeds existing kernel volume')
    nodes = parse_fdt(data)
    conf = text(nodes['/configurations']['default'])
    require(conf == 'config@cp03-c1', 'Wrong FIT default configuration')
    props = nodes['/configurations/' + conf]
    kpath, fpath = '/images/' + text(props['kernel']), '/images/' + text(props['fdt'])
    kernel, fdt = nodes[kpath], nodes[fpath]
    require(text(kernel['arch']) == 'arm64', 'Wrong kernel architecture')
    require(text(kernel['compression']) == 'gzip', 'Wrong kernel compression')
    for key in ('load', 'entry'):
        require(struct.unpack('>I', kernel[key])[0] == 0x41000000, 'Wrong kernel ' + key)
    image = gzip.decompress(kernel['data'])
    require(image[56:60] == b'ARM\x64', 'Missing ARM64 Image header')
    for path, image_props in ((kpath, kernel), (fpath, fdt)):
        hashes = 0
        for hp, fields in nodes.items():
            if hp.startswith(path + '/') and hp.count('/') == path.count('/') + 1 and 'algo' in fields:
                algo = text(fields['algo'])
                if algo == 'crc32':
                    value = struct.pack('>I', zlib.crc32(image_props['data']))
                else:
                    require(algo in ('sha1', 'sha256'), 'Unsupported FIT hash')
                    value = hashlib.new(algo, image_props['data']).digest()
                require(value == fields['value'], 'FIT image hash mismatch')
                hashes += 1
        require(hashes > 0, 'Missing FIT image hashes')
    board = parse_fdt(fdt['data'])
    require(text(board['/']['model']) == 'ZN M2', 'Wrong DTB model')
    require(board['/']['compatible'] == b'zn,m2\0qcom,ipq6018\0', 'Wrong DTB compatible')
    return {'configuration': conf, 'load': '0x41000000', 'entry': '0x41000000',
            'compression': 'gzip', 'fit_bytes': len(data), 'dtb_bytes': len(fdt['data']),
            'runtime_boot_verified': False}


def crc(data):
    return zlib.crc32(data) ^ 0xffffffff


def check_ubi(data, expected=None):
    require(0 < len(data) <= MTD_BYTES and len(data) % PEB == 0, 'UBI outside existing MTD bounds')
    tables, mapping = [], {}
    for offset in range(0, len(data), PEB):
        peb = data[offset:offset + PEB]
        require(peb[:4] == b'UBI#' and peb[4] == 1, 'Wrong UBI EC header')
        require(crc(peb[:60]) == struct.unpack_from('>I', peb, 60)[0], 'UBI EC CRC mismatch')
        vid_offset, data_offset = struct.unpack_from('>II', peb, 16)
        require(vid_offset == 2048 and data_offset == 4096, 'Wrong UBI header/page geometry')
        vid = peb[vid_offset:vid_offset + 64]
        if vid == b'\xff' * 64:
            require(peb[data_offset:] == b'\xff' * LEB, 'Unmapped PEB contains unexpected payload')
            continue
        require(vid[:4] == b'UBI!' and vid[4] == 1, 'Wrong UBI VID header')
        require(crc(vid[:60]) == struct.unpack_from('>I', vid, 60)[0], 'UBI VID CRC mismatch')
        volume, lnum = struct.unpack_from('>II', vid, 8)
        require(volume in VOLUMES or volume == 0x7fffefff, 'Unexpected UBI volume')
        require((volume, lnum) not in mapping, 'Duplicate UBI LEB')
        content = peb[data_offset:]
        mapping[volume, lnum] = content
        if volume in VOLUMES:
            require(lnum < VOLUMES[volume][1], 'UBI logical block outside fixed volume')
        else:
            require(lnum in (0, 1), 'Unexpected layout volume LEB')
            table = content[:128 * 172]
            active = {}
            for i in range(128):
                rec = table[i * 172:(i + 1) * 172]
                require(crc(rec[:168]) == struct.unpack_from('>I', rec, 168)[0], 'Volume table CRC mismatch')
                reserved, alignment, padding = struct.unpack_from('>III', rec)
                if reserved:
                    name_len = struct.unpack_from('>H', rec, 14)[0]
                    require(name_len <= 127, 'Invalid UBI name length')
                    name = rec[16:16 + name_len].decode('ascii')
                    require(alignment == 1 and padding == 0 and rec[12] == 1, 'Unexpected UBI volume type/alignment')
                    require(rec[13] == 0 and rec[144] == 0, 'Update/autoresize flag changes existing layout')
                    active[i] = (name, reserved)
            require(active == VOLUMES, 'UBI IDs, names or capacities differ from current layout')
            tables.append(table)
    require(len(tables) == 2 and tables[0] == tables[1], 'Missing/conflicting UBI volume tables')
    require(mapping[1, 0][:4] == b'hsqs', 'Rootfs is not SquashFS')
    sb = mapping[2, 0]
    require(struct.unpack_from('<I', sb)[0] == 0x06101831 and sb[20] == 6, 'Missing UBIFS superblock')
    node_length = struct.unpack_from('<I', sb, 16)[0]
    require(24 <= node_length <= LEB, 'Invalid UBIFS superblock length')
    require(crc(sb[8:node_length]) == struct.unpack_from('<I', sb, 4)[0], 'UBIFS superblock CRC mismatch')
    minimum_io, leb_size, count, maximum = struct.unpack_from('<IIII', sb, 32)
    require(minimum_io == 2048 and leb_size == LEB and maximum == 514 and count <= maximum,
            'UBIFS geometry differs from existing rootfs_data volume')
    if expected is not None:
        for volume, original in expected.items():
            blocks = sorted(n for v, n in mapping if v == volume)
            require(blocks == list(range(len(blocks))), 'Non-contiguous image payload')
            restored = b''.join(mapping[volume, n] for n in blocks)
            require(restored[:len(original)] == original, 'UBI component payload differs from input')
    return {'image_bytes': len(data), 'image_pebs': len(data) // PEB,
            'container_pebs': MTD_BYTES // PEB, 'bad_block_reserve_pebs': 20,
            'volumes': [{'id': i, 'name': n, 'reserved_lebs': r, 'bytes': r * LEB}
                        for i, (n, r) in VOLUMES.items()], 'static_checks': 'passed',
            'runtime_boot_verified': False, 'recovery_flash_verified': False}
