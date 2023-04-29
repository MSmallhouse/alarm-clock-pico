# mount_sd
import board, busio, sdcardio, storage
sck = board.GP10
si = board.GP11
so = board.GP12
cs = board.GP13
spi = busio.SPI(sck, si, so)
sdcard = sdcardio.SDCard(spi, cs)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")
