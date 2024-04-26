clean:
	rm -rf work
	mn -c

run:
	python3 network.py

plot:
	python3 -m plotter --switch-log-path work/log/p4s.s1.log --plot-dir work/plot

eval: run plot

.PHONY: clean run plot
