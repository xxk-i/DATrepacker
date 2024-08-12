import os
import sys
import zlib
import ioUtils

"""
god bless us all
"""
class HashInfo:
    def __init__(self, in_files, dupe):
        self.in_files = in_files
        self.dupe = dupe
        self.filenames = []
        self.hashes = []
        self.indices = []
        self.bucket_offsets = []
        self.pre_hash_shift = 0
        self.generate_info()

    # We sort, determine names to dupe, then dupe them in the *original* file list
    def get_duped_names(self):
        ordered_files = []

        for file in self.in_files:
            ordered_files.append((file, (zlib.crc32(file.lower().encode('ascii')) & ~0x80000000) >> self.pre_hash_shift)) 
        
        #Sort by search index
        ordered_files.sort(key=lambda x: x[1])

        #If search index increments more than 1, we dupe
        dupes = []

        search_index = ordered_files[0][1]
        for file in ordered_files:
            if file[1] > search_index + 1:
                dupes.append(file[0])
            
            search_index = file[1]

        #rebuild original list with dupes
        duped_names = []
        for name in self.in_files:
            if name in dupes:
                #hah
                duped_names.append(name)
                duped_names.append(name)

            else:
                duped_names.append(name) 

        return duped_names

    #thanks raiderb!
    def calculate_shift(self):
        count = len(self.in_files)
        if count <= 1:
            count += 1
        return max(24, 32 - count.bit_length())

    #thanks petrarca :)
    def generate_info(self):
        self.pre_hash_shift = self.calculate_shift()

        if self.dupe:
            self.filenames = self.get_duped_names()
        
        else:
            self.filenames = self.in_files

        for i in range(1 << 31 - self.pre_hash_shift):
            self.bucket_offsets.append(-1)

        if self.pre_hash_shift == 0:
            print("Hash shift is 0; does directory have more than 1 << 31 files?")

        names_indices_hashes = []
        for i in range(len(self.filenames)):
            names_indices_hashes.append((self.filenames[i], i, (zlib.crc32(self.filenames[i].lower().encode('ascii')) & ~0x80000000)))
        
        names_indices_hashes.sort(key=lambda x: x[2] >> self.pre_hash_shift)
        
        for entry in names_indices_hashes:
            self.hashes.append(entry[2])
        
        self.hashes.sort(key=lambda x: x >> self.pre_hash_shift)

        for i in range(len(names_indices_hashes)):
            if self.bucket_offsets[names_indices_hashes[i][2] >> self.pre_hash_shift] == -1:
                self.bucket_offsets[names_indices_hashes[i][2] >> self.pre_hash_shift] = i
            self.indices.append(names_indices_hashes[i][1])

    def get_table_size(self):
        self.buckets_size = len(self.bucket_offsets) * 2 #these are only shorts (uint16)
        self.hashes_size = len(self.hashes) * 4 #uint32
        self.indices_size = len(self.indices) * 2 #shorts again (uint16)

        size = 16 + self.buckets_size + self.hashes_size + self.indices_size #16 for pre_hash_shift and 3 table offsets (all uint32)

        return size

class DAT:
    def __init__(self, in_dir, dupe):
        self.in_dir = in_dir
        self.extensions = []
        in_files = os.listdir(in_dir)
        
        if len(in_files) == 0:
            print("Input directory is empty, exiting")
            sys.exit(1)

        self.hash_info = HashInfo(in_files, dupe)
        self.longest_name_length = self.get_longest_name_length()

    def pack(self):
        outfile = self.in_dir + ".dat"

        f = open(outfile, "wb+")

        offset_table_size = self.get_offset_table_size()
        extension_table_size = self.get_extension_table_size()
        filename_table_size = self.get_filename_table_size()
        filesize_table_size = self.get_filesize_table_size()
        hashmap_table_size = self.hash_info.get_table_size()

        #Header
        f.write(b"DAT\0")   # Magic (DAT)
        ioUtils.write_Int32(f, len(self.hash_info.filenames)) # Filecount
        ioUtils.write_Int32(f, 32) # Offset table offset (size of DAT header, always 32)
        ioUtils.write_Int32(f, 32 + offset_table_size)   # Extension table offset
        ioUtils.write_Int32(f, 32 + offset_table_size + extension_table_size)   # Filename table offset
        ioUtils.write_Int32(f, 32 + offset_table_size + extension_table_size + filename_table_size) # File sizes table offset
        ioUtils.write_Int32(f, 32 + offset_table_size + extension_table_size + filename_table_size + filesize_table_size) # File sizes table offset
        ioUtils.write_Int32(f, 0) # Pad to 16bit alignment

        total_info_size = 32 + offset_table_size + extension_table_size + filename_table_size + filesize_table_size + hashmap_table_size

        #Padding
        total_info_size = ioUtils.padTo16(total_info_size)

        # Table time

        # File offsets
        for offset in self.get_file_offsets_list(total_info_size):
            ioUtils.write_Int32(f, offset)

        # Extensions
        for extension in self.extensions:
            ioUtils.write_string(f, extension)
        
        # Names
        ioUtils.write_Int32(f, self.longest_name_length)
        for name in self.hash_info.filenames:
            ioUtils.write_string(f, name)
            f.write(b"\0" * (self.longest_name_length - len(name) - 1)) # -1 because write_string adds a null terminator
        
        # Sizes
        for name in self.hash_info.filenames:
            size = os.path.getsize(self.in_dir + "/" + name)
            ioUtils.write_Int32(f, size)
        
        # Hashmap
        ioUtils.write_Int32(f, self.hash_info.pre_hash_shift)
        ioUtils.write_Int32(f, 16) # bucket_offsets offset
        ioUtils.write_Int32(f, 16 + self.hash_info.buckets_size) # hashes offset
        ioUtils.write_Int32(f, 16 + self.hash_info.buckets_size + self.hash_info.hashes_size) # file indices offset
        for bucket in self.hash_info.bucket_offsets:
            ioUtils.write_Int16(f, bucket)
        for hash in self.hash_info.hashes:
            ioUtils.write_Int32(f, hash)
        for index in self.hash_info.indices:
            ioUtils.write_Int16(f, index)

        # Padding
        ioUtils.write_padding16(f, f.tell())

        # Open files, write files
        for name in self.hash_info.filenames:
            current_file = open(self.in_dir + "/" + name, "rb")
            data = current_file.read()
            f.write(data)
            ioUtils.write_padding16(f, f.tell())

        print(f"Wrote {outfile}")

        # Uncomment for sick hashmap debug info
        # for i in range(len(self.hash_info.filenames)):
        #     search = (zlib.crc32(self.hash_info.filenames[i].lower().encode('ascii')) & ~0x80000000) >> self.hash_info.pre_hash_shift
        #     print(f"Expected filename: {self.hash_info.filenames[i]}\t Output filename: {self.hash_info.filenames[self.hash_info.indices[self.hash_info.bucket_offsets[search]]]}")

    def get_extension_table_size(self):
        split_names = []
        size = 0

        # os.path.splitext keeps the ".", and I want it to be clear that we add 1 later because
        # of the null terminator - NOT the ".", so we use rsplit instead
        for filename in self.hash_info.filenames:
            split_names.append(filename.rsplit('.', 1))
        
        # Count these because extensions can be variable length (.z), thanks Raider!
        for split in split_names:
            self.extensions.append(split[1])
            size += len(split[1].split('.')[0]) + 1 # add one for the null terminator we are adding later

        return size

    def get_longest_name_length(self):
        longest = 0
        for name in self.hash_info.filenames:
            if len(name) > longest:
                longest = len(name)

        return longest + 1 #null terminator
    
    def get_offset_table_size(self):
        return len(self.hash_info.filenames * 4)
    
    def get_filesize_table_size(self):
        return len(self.hash_info.filenames * 4)
    
    def get_filename_table_size(self):
        return self.longest_name_length * len(self.hash_info.filenames) + 4 #first 4 bytes are the longest_name_length
    
    def get_file_offsets_list(self, start):
        offset = 0
        file_offsets = []

        for name in self.hash_info.filenames:
            file_offsets.append(start + offset)
            offset += ioUtils.padTo16(os.path.getsize(self.in_dir + "/" + name))
        
        return file_offsets

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: py dat.py in_dir")

    in_dir = sys.argv[1]
    dupe = False

    if len(sys.argv) == 3:
        flag = sys.argv[2]
        if flag == "-d":
            dupe = True
        
        else:
            print("Unknown 3rd arg, ignoring")

    DAT_file = DAT(in_dir, dupe)
    DAT_file.pack()
