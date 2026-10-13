"""wavstats.py - loudness of the two .30 cal firing samples (read-only on the GOG paks)."""
import zipfile, io, wave, struct, math, os
GOG = "G:/GOG/Medal of Honor - Allied Assault War Chest"


def stats(pak, name):
    d = zipfile.ZipFile(os.path.join(GOG, pak)).read(name)
    w = wave.open(io.BytesIO(d))
    n, ch, sw, fr = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
    raw = w.readframes(n)
    if sw == 2:
        s = [x / 32768.0 for x in struct.unpack("<%dh" % (len(raw) // 2), raw)]
    else:
        s = [(b - 128) / 128.0 for b in raw]
    peak = max(abs(x) for x in s)
    win = int(fr * 0.08) * ch
    best = 0
    for i in range(0, max(1, len(s) - win), max(1, win // 4)):
        seg = s[i:i + win]
        best = max(best, math.sqrt(sum(x * x for x in seg) / len(seg)))
    rms = math.sqrt(sum(x * x for x in s) / len(s))
    print("%-22s %-34s %5.2fs %dHz ch=%d bits=%d peak=%.2f rms=%.3f loudest80ms=%.3f" % (
        os.path.basename(name), pak, n / fr, fr, ch, sw * 8, peak, rms, best))
    return best


a = stats("maintt/zzzzz_xw_weapons.pk3", "sound/weapons/fire/WaW30cal.wav")
b = stats("maintt/zzzzzz-HRRTM_Pak4_Weapons.pk3", "sound/weapons/fire/50CalFire2.wav")
c = stats("main/Pak3.pk3", "sound/weapons/fire/50CalFire2.wav")
print("WaW30cal volume to match the jeep alias (1.37 x shipped 50cal sample): %.2f ; against the retail sample: %.2f" % (1.37 * b / a, 1.37 * c / a))
