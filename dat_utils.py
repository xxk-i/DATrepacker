import os

class FilePackInfo:
    """
    Class to go and figure out all of the relevant info for the Header given a 
    directory
    """

    def __init__(self, inDirectory):
        self.directory = inDirectory
        self.fileNames = []

        self._calculateInfo()

    def _calculateInfo(self):
        self.fileNames = os.listdir(self.directory)
        self.fileCount = len(self.fileNames)
        self.fileExtensions = self._getFileExtensionList()

        # These 2 are both 4 bytes per file
        self.fileOffsetTableSize = 4 * self.fileCount
        self.extensionTableSize = self.fileOffsetTableSize
        (self.nameTableSize, self.namesBlockSize) = self._calculateNameTableSize()
        self.sizeTableSize = 4 * self.fileCount

        # This section is always 4 null bytes apparently
        self.unknownSectionSize = 4

        self._calculateTableOffsets()

        # The CRC section is maybe unnecessary, we just fill 16 bytes and pad out to 16
        self.crcTableSize = self._calculateCrcTableSize()

        self.fileSizes = self._buildFileSizeDict()

    def _calculateTableOffsets(self):
        # Always true
        self.fileOffsetTableOffset = 32
        self.extensionTableOffset = self.fileOffsetTableOffset + self.fileOffsetTableSize
        self.nameTableOffset = self.extensionTableOffset + self.extensionTableSize
        self.sizeTableOffset = self.nameTableOffset + self.nameTableSize
        self.crcTableOffset = self.sizeTableOffset + self.sizeTableSize

    def _getLongestFilename(self):
        if self.fileNames is None: return None

        longest = 0
        for name in self.fileNames:
            if len(name) > longest:
                longest = len(name)

        return longest

    def _calculateNameTableSize(self):
        """
        The name table is tricky. First 4 bytes is one entry dictating the size of each 
        individual entry, where each individual entry is a NUL terminated filename. Then
        we have the NUL terminated filenames (padded to max length). Finally, the entire 
        table is padded out to 4 bytes.
        """
        longest = self._getLongestFilename()
        blockSize = longest + 1 # for the NUL byte
        namesSize = blockSize * self.fileCount

        # first 4 bytes are where we encode the blockSize
        tableSize = 4 + namesSize
        # BUT, totalSize has to be aligned to 4 bytes
        overflow = tableSize % 4
        if overflow != 0:
            tableSize += 4 - overflow

        return (tableSize, blockSize)

    def _calculateCrcTableSize(self):
        """
        I'm just faking crc table as 16 NUL bytes and then padded to 16 total bytes
        """
        crcSize = 16
        overflow = (self.crcTableOffset + crcSize) % 16
        if overflow != 0:
            crcSize += 16 - overflow

        return crcSize

    def _getFileExtensionList(self):
        # try this:
        extensionList = []
        for file in self.fileNames:
            _, ext = os.path.splitext(file)
            extensionList.append(ext.strip('.'))
        return extensionList

    def _buildFileSizeDict(self):
        fileSizes = {}
        for file in self.fileNames:
            fullPath = os.path.join(self.directory, file)
            fileSize = os.path.getsize(fullPath)
            fileSizes[file] = fileSize
        return fileSizes

    def getHeaderTableOffsets(self):
        return [
            self.fileOffsetTableOffset,
            self.extensionTableOffset,
            self.nameTableOffset,
            self.sizeTableOffset,
            self.crcTableOffset,
        ]

    def totalMetaDataSize(self):
        """
        Calculate the total size of all meta data (header + tables). Equal to
        the offset of the first file
        """
        offset = 32  # end of file header
        offset += self.fileOffsetTableSize
        offset += self.extensionTableSize
        offset += self.nameTableSize
        offset += self.sizeTableSize
        offset += self.crcTableSize

        return offset


def paddedBytes(num, width=4):
    return num.to_bytes(width, byteorder='little')

def padTo16Underflow(num):
    overflow = num % 16
    if overflow == 0:
        return 0
    return (16 - overflow)

class Writer:
    # Starts off the file
    MAGIC = bytes([0x44, 0x41, 0x54, 0x00])
    DEBUG = True

    def __init__(self, packInfo: FilePackInfo):
        self.packInfo = packInfo

    def setOutFile(self, outFile: str):
        """
        This is where we put the packed file. Must be set
        """
        self.outFile = outFile

    def write(self):
        if self.outFile is None:
            print("Error: must set outFile")
            return

        if self.packInfo is None:
            print("Error: need valid FilePackInfo to write file")

        pi = self.packInfo
        with open(self.outFile, "wb") as fp:
            fp.write(Writer.MAGIC)
            fp.write(paddedBytes(pi.fileCount))

            # There are 5 tables
            for offset in pi.getHeaderTableOffsets():
                fp.write(paddedBytes(offset))

            # pad to 32 bytes
            fp.write(paddedBytes(0x00))
            if self.DEBUG:
                if fp.tell() != 32:
                    print("File header should be exactly 32 bytes. Uh oh.")

            # File offset table
            fileOffset = pi.totalMetaDataSize()
            for file in pi.fileNames:
                size = pi.fileSizes[file]
                fp.write(paddedBytes(fileOffset))
                fileOffset += size
                fileOffset += padTo16Underflow(fileOffset)

            # Extension table
            for ext in pi.fileExtensions:
                fp.write(ext.encode('utf8'))
                fp.write(b'\x00')

            # Name table
            fp.write(paddedBytes(pi.namesBlockSize))
            for file in pi.fileNames:
                # not in little-endian
                padLength = pi.namesBlockSize - len(file)
                fp.write(file.encode('utf8'))
                fp.write(b'\x00' * (padLength))
            overflow = fp.tell() % 4
            if overflow != 0:
                fp.write(b'\x00' * (4 - overflow))

            # Size table
            for file in pi.fileNames:
                fp.write(paddedBytes(pi.fileSizes[file]))

            # CRC table (first byte must not be NUL (or crash), rest doesn't matter)
            fp.write(b'\x99')
            fp.write(b'\x00' * pi.crcTableSize)

            for file in pi.fileNames:
                fullPath = os.path.join(pi.directory, file)
                size = pi.fileSizes[file]
                underflow = padTo16Underflow(size)
                with open(fullPath, 'rb') as infile:
                    fp.write(infile.read())
                    if underflow != 0:
                        fp.write(b'\x00' * underflow)
