all:
	python3.7 setup.py install --user --record files.txt

install: all

clean:
	cat files.txt | xargs rm -f
	rm -rf build
	find . -name __pycache__ | xargs rm -rf
