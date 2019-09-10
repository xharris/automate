do:
	py ui.py

freeze:
	cxfreeze auto.py --target-dir=auto_dist --include-modules=pexpect,sys,json,subprocess,os