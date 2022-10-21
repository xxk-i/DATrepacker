# DATrepacker
DAT file repacker for NIER:AUTOMATA

This is currently the closest attempt at a 1:1 DAT file packer by including the ability to use the special "-d" flag which enables ✨ *file duping* ✨. 

Note: this does *not* generate a true 1:1 file every time, as the file order (and duping order) seems to be dependent on the order in which PlatinumGames polled files from the filesystem which (seems to be) impossible to recreate organically.

This project was rewritten to match (or at least be similar-ish) to the file parsers in [NieR2Blender2NieR](https://github.com/WoefulWolf/NieR2Blender2NieR/).

Q: Why bother, is file duping really that important?

A: Nope! Doesn't matter at all! The file duping PlatinumGames does is *completely useless* and probably a bug! It exists only for the purpose of padding out the hashmap and *shouldn't have ever* actually duplicated the data of the contained files themselves -- ESPECIALLY when the file format supports just reusing data offsets. Don't care about arbitrary file accuracy? Then use [🤌 mamma mia 🤌](https://github.com/Petrarca181/YAMMR).

Usage: `python dat.py <directory> (-d)`

Thanks to:
 - My Brother (Helped me write the original 5 years ago)
 - Petrarca (YAMMR)
 - Kerilk (Incredibly useful DAT format documentation)
 - WoefulWolf (NieR2Blender2NieR & ioUtils.py that this repo shamelessly yoinks)
 - 💖RaiderB💖

