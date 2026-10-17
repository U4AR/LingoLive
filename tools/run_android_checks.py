from pathlib import Path
import time,sys,json,xml.etree.ElementTree as ET,re,hashlib
import argparse
from adb_shell.adb_device import AdbDeviceTcp
from adb_shell.auth.sign_pythonrsa import PythonRSASigner
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--class-name');parser.add_argument('--count',type=int,default=7);args=parser.parse_args()
d=AdbDeviceTcp('127.0.0.1',5555,default_transport_timeout_s=60)
for attempt in range(90):
 try:
  d.connect(rsa_keys=[PythonRSASigner.FromRSAKeyPath('/workspace/.android-tools/adbkey')],auth_timeout_s=15,read_timeout_s=30);break
 except Exception as e:
  print('Waiting for Android transport',type(e).__name__,flush=True);time.sleep(5)
else:raise RuntimeError('Emulator transport unavailable')
def shell(cmd):return d.shell(cmd,transport_timeout_s=180,read_timeout_s=300,timeout_s=400)

if shell('getprop ro.hw_timeout_multiplier').strip()!='10':print(shell('su 0 setprop ro.hw_timeout_multiplier 10'),flush=True)
for attempt in range(150):
 if shell('getprop sys.boot_completed').strip()=='1' and 'mBooted=true' in shell('dumpsys activity processes'):break
 print('Waiting for Android boot',attempt,flush=True);time.sleep(5)
else:raise RuntimeError('Android did not become ready')
print(shell('settings put secure anr_show_background 1'),flush=True)
for name in ['window_animation_scale','transition_animation_scale','animator_duration_scale']:shell('settings put global '+name+' 0')
# Dismiss only the emulator platform's stale Wait dialogs, never app failures.
for attempt in range(8):
 shell('uiautomator dump /data/local/tmp/lingolive-windows.xml')
 xml=shell('cat /data/local/tmp/lingolive-windows.xml')
 try:root=ET.fromstring(xml)
 except ET.ParseError:break
 wait=next((n for n in root.iter('node') if n.get('text','').strip().casefold()=='wait'),None)
 if wait is None:break
 labels=' '.join(n.get('text','') for n in root.iter('node'))
 if not any(name in labels for name in ['Process system','System UI','Network Stack','NetworkStack','Tethering','com.android.networkstack']):raise RuntimeError('Unexpected ANR dialog; not dismissing it')
 coords=list(map(int,re.findall(r'\d+',wait.get('bounds'))));shell(f'input tap {(coords[0]+coords[2])//2} {(coords[1]+coords[3])//2}');time.sleep(2)
for source,target in [('android/app/build/outputs/apk/debug/app-debug.apk','/data/local/tmp/lingolive.apk'),('android/app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk','/data/local/tmp/lingolive-tests.apk')]:
 print('Installing',source,flush=True)
 expected=hashlib.sha256((ROOT/source).read_bytes()).hexdigest()
 remote=shell('sha256sum '+target).split()
 if not remote or remote[0]!=expected:d.push(str(ROOT/source),target,transport_timeout_s=180,read_timeout_s=300)
 else:print('Reusing byte-verified transferred APK',flush=True)
 result=shell('pm install -r -t '+target);print(result,flush=True)
 if 'Success' not in result:raise RuntimeError('APK installation failed')
print(shell('pm clear com.u4ar.lingolive'),flush=True)
output=[]
selection=(' -e class '+args.class_name) if args.class_name else ''
for part in d.streaming_shell('am instrument -w -r'+selection+' com.u4ar.lingolive.test/androidx.test.runner.AndroidJUnitRunner',transport_timeout_s=180,read_timeout_s=300):
 print(part,end='',flush=True);output.append(part)
text=''.join(output);(ROOT/('validation/android-targeted.txt' if args.class_name else 'validation/android-tests.txt')).write_text(text)
if 'FAILURES!!!' in text or 'INSTRUMENTATION_FAILED' in text or f'OK ({args.count} test'+('s' if args.count!=1 else '')+')' not in text:raise RuntimeError('Android checks did not pass')
if args.class_name:sys.exit(0)
for name in ['example.png','live-lesson.png']:
 print(shell('run-as com.u4ar.lingolive cat cache/'+name+' > /data/local/tmp/'+name),flush=True)
 d.pull('/data/local/tmp/'+name,str(ROOT/'validation'/name),transport_timeout_s=60,read_timeout_s=120)
print('Android checks and screenshot complete',flush=True)
