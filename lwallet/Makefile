all:
	python3.7 setup.py install --user

install: all

clean:
	rm -rf build ~/.local/lib/python3.7/site-packages/lwallet ~/.local/lib/python3.7/site-packages/coinapi \
	  ~/.local/lib/python3.7/site-packages/lwallet-0.0.1.egg-info ~/.local/bin/{mnb,send_nrg,rescan}.py
	find . -name "*.pyc" -o -name "__pycache__" | xargs rm -rf
