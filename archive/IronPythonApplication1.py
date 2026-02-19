import sys
import clr
sys.path.append(r"C:/Users/SiliconProphet/Documents/GitHub/StarDate/StarLib.Dynamic/obj/Debug/netstandard2.0/")
clr.AddReference(r"StarLibDynamic.dll")


print("loltest")

from StarLib.Dynamic import StarDateDynamic

dt = StarDateDynamic();

print(dt.ToLongString());