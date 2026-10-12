"""The pistol lane's delta GIF tool (..\\..\\tools\\dgif.py, used as a library) on the rifle lane's runs
(ADS_RUNS = G:/mohaa-adsanim2/runs). Same arguments:

    python rgif.py <session> <tag substring> <out.gif> --frames a:b:step [--w 400] [--ms 48] [--crop x0,y0,x1,y1] [--box]
                   [--labels f0=txt,f58=txt] [--hold 12]
"""
import sys, os
os.environ['ADS_RUNS'] = 'G:/mohaa-adsanim2/runs'
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools'))
import dgif

if __name__ == '__main__':
    dgif.main()
