import sys, zlib
raw = sys.stdin.buffer.read()
print('Environment partition bytes:', len(raw))
valid = []
for start in (0, 0x10000, 0x20000):
    for size in (0x10000, 0x20000, 0x40000):
        if start + size > len(raw): continue
        expected = int.from_bytes(raw[start:start+4], 'little')
        for header in (4, 5):
            data = raw[start+header:start+size]
            if zlib.crc32(data) & 0xffffffff == expected:
                valid.append((start,size,header,data))
allowed = {'bootcmd','bootargs','bootdelay','ipaddr','serverip','loadaddr','bootfile',
           'stdin','stdout','stderr','ncip','preboot','bootcount','bootlimit',
           'altbootcmd','bootmenu_0','bootmenu_1','bootmenu_2','ethact','ethprime'}
for start,size,header,data in valid:
    print(f'Valid CRC: offset={start:#x} size={size:#x} header={header}')
    for record in data.split(b'\0'):
        key,sep,value=record.partition(b'=')
        if sep and key.decode('ascii','ignore') in allowed:
            print(key.decode('ascii','replace')+'='+value.decode('ascii','replace'))
if not valid:
    print('No standard CRC-valid environment layout found; no settings modified.')
