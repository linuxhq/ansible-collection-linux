# Makefile

all: venv galaxy

clean:
	$(RM) -r venv

galaxy:
	venv/bin/ansible-galaxy install -r requirements.yml

venv:
	test -d venv || python3 -m venv venv
	. venv/bin/activate
	PYTHONWARNINGS='ignore:DEPRECATION' venv/bin/pip install -r requirements.txt
