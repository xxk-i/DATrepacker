#!/usr/local/bin/python3



import os

import sys

import binascii



MAGIC = bytes([0x44, 0x41, 0x54, 0x00])



def padded_bytes(num):

    """

    returns int in little endian format, padded to 4 bytes

    """

    return num.to_bytes(4, byteorder='little')



def padded_bytes_normal(num):

    return num.to_bytes(4)



def write_stuff_padded_to_16(stuff, fp):

    """

    The way this is written right now is that you have to pass in the right

    bytes...

    """

    if stuff is not None:

        fp.write(stuff)



    partial_line = fp.tell() % 16

    # Data happens to lay on 16-byte boundary, no padding needed

    if partial_line == 0:

        return



    # Write padding until we hit 16 byte alignment

    fp.write(b'\00' * (16 - partial_line))



def write_header(fp, directory):

    filecount = get_filecount(directory)

    fp.write(MAGIC)

    fp.write(padded_bytes(filecount))



    #==== File Offsets ====

    # always comes directly after header (32 bytes)

    fileTableOffset = (32)

    fp.write(padded_bytes(fileTableOffset))



    #==== File extension table ====

    # 4 bytes of info per file

    fileTableSize = 4 * filecount

    extensionTableOffset = fileTableOffset + fileTableSize

    fp.write(padded_bytes(extensionTableOffset))



    #==== file name table ====

    extensionTableSize = fileTableSize # they are the same size, bro

    nameTableOffset = extensionTableOffset + extensionTableSize

    fp.write(padded_bytes(nameTableOffset))



    #==== file size table ====

    #nameTableBlockSize = get_longest_filename(directory) + 1

    nameTableTotalSize = name_table_total_size(directory)

    # (nameTableBlockSize * filecount) + 4

    sizeTableOffset = nameTableOffset + nameTableTotalSize

    fp.write(padded_bytes(sizeTableOffset))





    #==== Unknown offset 1c??? ====

    sizeTableSize = 4 * filecount

    unknownOffset1C = sizeTableOffset + sizeTableSize

    fp.write(padded_bytes(unknownOffset1C))



    #==== Unknown20???? ====

    # apparently we just put 4 bytes of nul lul

    fp.write(padded_bytes(0x00000000))



    #=== Write Nuls to the file offset table for now ===

    fp.write(b'\00' * fileTableSize)  #works?

    

    #=== Generate extension table ====

    extensionList = gen_extension_list(directory)

    write_extension_table(extensionList,fp)



    #=== Generate name table =====

    namelist = gen_name_list(directory)

    longestName = get_longest_filename(directory)

    write_name_table(namelist, fp, longestName)



    #=== Generate size table =====

    sizelist = gen_size_list(directory)

    write_size_table(sizelist,fp)



    #=== Generate the sorted CRC table ====

    #FIXME: apparently we can get away without doing anything here :)

    #crctable = gen_crc_table(directory)

    #write_crc_table(crctable,fp)

    # Write a 16-byte nul CRC table (16-byte lul)

    fp.write(b'\00' * 16)

    write_stuff_padded_to_16(None, fp)





    # draw the rest of the fucking owl

    # 1. FileCount -

    # 2. FileTableOffset - 4 bytes per file

    # 3. ExtensionTableOffset - 4 bytes per file

    # 4. NameTableOffset - longest file name + 1 per file, plus 4 bytes

    # 5. SizeTableOffest - 4 bytes per file

    # 6. UnknownOffset1C

    # 7 Unknown20 ?



def glom_on_files(fp, directory):

    """

    IMPORTANT: fp offset must be at the start of the file area.

    """

    for index, listing in enumerate(os.listdir(directory)):

        abs_file = os.path.join(directory, listing)

        infile = open(abs_file, "rb")

        offset_of_file = fp.tell()

        populate_file_offset(fp, index, offset_of_file)

        #TODO: update file offset table right now

        write_stuff_padded_to_16(infile.read(), fp)



def populate_file_offset(fp, index, offset):

    # Turns out, offset of file-offset table is always 32. howneatisthat

    fp.seek(32 + (4 * index))

    fp.write(padded_bytes(offset))

    fp.seek(offset)





def get_filecount(directory):

   return len(os.listdir(directory))



def get_longest_filename(directory):

    """

    Name table block size = longest name + 1 (for null padding)

    """

    files = os.listdir(directory)

    longestName = 0

    for f in files:

        if len(f) > longestName: longestName = len(f)



    # if this is 0, everything is probably broken, FYI

    return longestName



def gen_extension_list(directory):

    files = os.listdir(directory)

    extensionList = ()

    for i in files:

        ext = i[-3:]

        extensionList += (ext,)

    return extensionList



def gen_name_list(directory):

    namelist = ()

    files = os.listdir(directory)

    for i in files:

        namelist += (i,)

    return(namelist)



def gen_size_list(directory):

    sizelist = ()

    files = os.listdir(directory)

    for i in files:

        currentFile = os.path.join(directory, i)

        sizelist += (os.path.getsize(currentFile),)

    print(sizelist)

    return sizelist

    

def gen_string_crc(name):

    return hex(binascii.crc32(name.encode()) % (1<<32))



def gen_crc_table(directory):

    crclist = ()

    files = os.listdir(directory)

    for i in files:

    #for i in range(len(files)):

        crc = gen_string_crc(i.lower())[2:]

        

        if crcbit >= 8:

            crc = str((crcbit % 8)) + str(crc[-7:])

        littlecrc = padded_bytes(int(crc, 16)).hex()

        crclist = crclist + (littlecrc,)

    crclist = list(crclist)

    sortedlist = sorted(crclist, key=lambda x: x[-2:])

    return sortedlist



def name_table_total_size(directory):

    """

    Figure out how big the name table actually will be lol

    """

    longestName = get_longest_filename(directory)

    count = get_filecount(directory)

    bytes_per_file = longestName + 1 # for nul

    # Assume that name table always beings aligned to 4 bytes

    blocksize_info = 4

    total_bytes_written = blocksize_info + bytes_per_file * count

    overflow = total_bytes_written % 4

    if overflow == 0:

        return total_bytes_written

    else:

        total_bytes_written = total_bytes_written + (4 - overflow)

        return total_bytes_written





       

def write_crc_table(crcs, fp):

    for crc in crcs:

        fp.write(binascii.unhexlify(''.join(crc.split())))



def write_name_table(names, fp, longestName):

    fp.write(padded_bytes(longestName + 1))



    for name in names:

        padLength = longestName - len(name)

        fp.write(name.encode('utf8'))

        fp.write(b'\x00' * (padLength + 1))



    overflow = fp.tell() % 4

    if overflow == 0:

        return

    else:

        fp.write(b'\00' * (4 - overflow))



def write_extension_table(extensions, fp):

    for ext in extensions:

        fp.write(ext.encode('utf8'))

        fp.write(b'\x00')

        

def write_size_table(list, fp):

    for i in list:

        fp.write(padded_bytes(int(i)))

    

#process

#FileTableOffset = 0x0 # actually will be right after header

#Size(FileTableOffset) == 4 (bytes per file) * (num files)

#ExtensionTableOffset = FileTableOffset + Size(FileTableOffset)

# size(ETO) == size(FTO) !!

# NameTableOffset = ExtensionTableOffset + Size(fileTableOffset)

# SizeTableOffset = NameTableOffset + size(NTO)

# BUT

#       size(NTO) = numFiles * largestFileNameLength + 1

#

#Append file, append file...





def main():

    if len(sys.argv) < 2:

        print("need input dir")

        sys.exit(1)



    in_dir = sys.argv[1].rstrip("/")

    outfile = os.path.basename(in_dir).lstrip(".") + ".dat"



    fp = open(outfile, "wb")



    write_header(fp, in_dir)

    glom_on_files(fp, in_dir)

    #print("suck my ass")



#=========

if __name__ == '__main__':

    main()