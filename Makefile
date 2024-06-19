clean:
	rm -rf work
	mn -c

cli:
	python network.py --cli

run:
	python network.py

plot:
	python -m plotter --switch-log-path work/log/p4s.s1.log --plot-dir work/plot

eval: run plot

.PHONY: clean cli run plot
